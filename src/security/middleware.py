"""
Security middleware for comprehensive request/response security.

Implements security headers, request validation, logging, and monitoring
for production-grade API security.
"""

import json
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException, Request, Response, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint

from ..core.config import get_settings
from .rate_limiter import RateLimitExceeded, rate_limiter
from .validation import SecurityValidationError


class SecurityHeaders:
    """Security headers configuration and management."""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get comprehensive security headers."""
        return {
            # Prevent XSS attacks
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",

            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "frame-ancestors 'none';"
            ),

            # HTTPS enforcement
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",

            # Prevent information leakage
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Feature policy
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=()"
            ),

            # Hide server information
            "Server": "AI-Migration-Validator",

            # API versioning
            "API-Version": "1.0.0",

            # CORS headers will be handled by CORS middleware
        }


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware."""

    def __init__(
        self,
        app,
        enable_request_logging: bool = True,
        enable_rate_limiting: bool = True,
        enable_input_validation: bool = True,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        blocked_user_agents: Optional[List[str]] = None,
        blocked_ips: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.settings = get_settings()
        self.enable_request_logging = enable_request_logging
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_input_validation = enable_input_validation
        self.max_request_size = max_request_size
        self.blocked_user_agents = blocked_user_agents or []
        self.blocked_ips = blocked_ips or []

        # Security headers
        self.security_headers = SecurityHeaders.get_security_headers()

        # Request tracking
        self.active_requests: Dict[str, Dict] = {}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Main security middleware dispatch."""
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()

        try:
            # Pre-request security checks
            await self._pre_request_checks(request)

            # Track active request
            if self.enable_request_logging:
                self._track_request_start(request_id, request)

            # Process request
            response = await call_next(request)

            # Post-request processing
            await self._post_request_processing(request, response, start_time)

            return response

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Handle unexpected errors securely
            return await self._handle_security_error(request, e, start_time)
        finally:
            # Cleanup request tracking
            if request_id in self.active_requests:
                del self.active_requests[request_id]

    async def _pre_request_checks(self, request: Request):
        """Perform pre-request security checks."""
        # Check request size
        if hasattr(request, 'headers'):
            content_length = request.headers.get('content-length')
            if content_length and int(content_length) > self.max_request_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Request too large"
                )

        # Check blocked IPs
        client_ip = self._get_client_ip(request)
        if client_ip in self.blocked_ips:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # Check blocked user agents
        user_agent = request.headers.get('user-agent', '').lower()
        for blocked_agent in self.blocked_user_agents:
            if blocked_agent.lower() in user_agent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User agent not allowed"
                )

        # Rate limiting check
        if self.enable_rate_limiting:
            await self._check_rate_limits(request)

    async def _check_rate_limits(self, request: Request):
        """Check rate limits for the request."""
        try:
            # Determine rate limit type based on path
            path = request.url.path
            if path.startswith('/api/auth'):
                limit_type = 'auth'
            elif path.startswith('/api/upload'):
                limit_type = 'upload'
            elif path.startswith('/api/validate'):
                limit_type = 'validation'
            elif path.startswith('/api/'):
                limit_type = 'api_general'
            else:
                return  # No rate limiting for non-API endpoints

            # Extract user ID if available
            user_id = getattr(request.state, 'user_id', None)

            await rate_limiter.check_rate_limit(request, limit_type, user_id)

        except RateLimitExceeded as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=e.message,
                headers={"Retry-After": str(e.retry_after)} if e.retry_after else {}
            )

    async def _post_request_processing(
        self, request: Request, response: Response, start_time: float
    ):
        """Post-request security processing."""
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value

        # Add request tracking headers
        response.headers["X-Request-ID"] = request.state.request_id

        # Calculate and add processing time
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # Log request if enabled
        if self.enable_request_logging:
            self._log_request_completion(request, response, process_time)

    async def _handle_security_error(
        self, request: Request, error: Exception, start_time: float
    ) -> Response:
        """Handle security errors securely."""
        process_time = time.time() - start_time

        if isinstance(error, SecurityValidationError):
            response = JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid input", "error_type": "validation_error"}
            )
        elif isinstance(error, RateLimitExceeded):
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": error.message, "error_type": "rate_limit_exceeded"},
                headers={"Retry-After": str(error.retry_after)} if error.retry_after else {}
            )
        else:
            # Generic error - don't leak information
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error", "error_type": "server_error"}
            )

        # Add security headers to error response
        for header, value in self.security_headers.items():
            response.headers[header] = value

        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Process-Time"] = str(process_time)

        # Log security error
        self._log_security_error(request, error, process_time)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP considering proxies."""
        # Check X-Forwarded-For header (from load balancers/proxies)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Get the first IP in the chain
            return forwarded_for.split(',')[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip.strip()

        # Fall back to direct connection IP
        return request.client.host if request.client else 'unknown'

    def _track_request_start(self, request_id: str, request: Request):
        """Track request start for monitoring."""
        self.active_requests[request_id] = {
            'start_time': time.time(),
            'method': request.method,
            'path': str(request.url.path),
            'client_ip': self._get_client_ip(request),
            'user_agent': request.headers.get('user-agent', ''),
            'content_length': request.headers.get('content-length', 0),
        }

    def _log_request_completion(
        self, request: Request, response: Response, process_time: float
    ):
        """Log request completion."""
        log_data = {
            'request_id': request.state.request_id,
            'method': request.method,
            'path': str(request.url.path),
            'status_code': response.status_code,
            'process_time': process_time,
            'client_ip': self._get_client_ip(request),
            'user_agent': request.headers.get('user-agent', ''),
            'content_length': request.headers.get('content-length', 0),
            'response_size': response.headers.get('content-length', 0),
        }

        # In production, send to structured logging system
        if self.settings.environment == 'development':
            print(f"REQUEST: {json.dumps(log_data)}")

    def _log_security_error(self, request: Request, error: Exception, process_time: float):
        """Log security errors for monitoring."""
        log_data = {
            'request_id': request.state.request_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'method': request.method,
            'path': str(request.url.path),
            'process_time': process_time,
            'client_ip': self._get_client_ip(request),
            'user_agent': request.headers.get('user-agent', ''),
            'severity': 'high' if isinstance(error, SecurityValidationError) else 'medium',
        }

        # In production, send to security monitoring system
        if self.settings.environment == 'development':
            print(f"SECURITY_ERROR: {json.dumps(log_data)}")

    def get_active_requests_count(self) -> int:
        """Get count of active requests."""
        return len(self.active_requests)

    def get_request_metrics(self) -> Dict[str, Any]:
        """Get request metrics for monitoring."""
        return {
            'active_requests': len(self.active_requests),
            'requests_by_path': {},  # Implement path-based counting
            'average_process_time': 0.0,  # Implement average calculation
        }