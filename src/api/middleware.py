"""Comprehensive security middleware for input validation, authentication, and audit logging.

Integrates all security components including input validation, API key authentication,
rate limiting, and comprehensive audit logging.
"""

import json
import uuid
from datetime import datetime

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..core.config import get_settings
from ..core.logging import logger
from ..security.audit import AuditEventType, AuditSeverity, security_audit
from ..security.validation import SecurityValidationError, SecurityValidator


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware with integrated validation and audit logging."""

    def __init__(
        self,
        app: ASGIApp,
        enable_input_validation: bool = True,
        enable_audit_logging: bool = True,
        enable_attack_detection: bool = True,
    ):
        super().__init__(app)
        self.settings = get_settings()
        self.security_validator = SecurityValidator()
        self.enable_input_validation = enable_input_validation
        self.enable_audit_logging = enable_audit_logging
        self.enable_attack_detection = enable_attack_detection
        self.logger = logger.bind(middleware="SecurityMiddleware")

        # Attack detection patterns
        self.attack_patterns = {
            "sql_injection": [
                r"('|(\\'))|(;|--|\s+or\s+|\s+and\s+)",
                r"(union\s+select|insert\s+into|delete\s+from|drop\s+table)",
            ],
            "xss": [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
            ],
            "path_traversal": [
                r"\.\.[\\/]",
                r"[\\/]\.\.[\\/]",
            ],
            "command_injection": [
                r"[;&|`$\(\){}]",
                r"(rm\s|del\s|format\s|mkfs\s)",
            ],
        }

    async def dispatch(self, request: Request, call_next):
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        request.state.client_ip = client_ip
        request.state.user_agent = user_agent

        start_time = datetime.utcnow()

        try:
            # Security validation pipeline
            if self.enable_input_validation:
                await self._comprehensive_input_validation(request)

            # Attack detection
            if self.enable_attack_detection:
                await self._detect_attacks(request)

            # Process request
            response = await call_next(request)

            # Log successful request
            if self.enable_audit_logging:
                await self._log_successful_request(request, response, start_time)

            return response

        except HTTPException as e:
            # Log security violation
            if self.enable_audit_logging:
                await self._log_security_violation(request, e, start_time)
            raise

        except Exception as e:
            # Log system error
            if self.enable_audit_logging:
                await self._log_system_error(request, e, start_time)

            self.logger.error(
                "Unhandled error in security middleware",
                error=str(e),
                request_id=request_id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address handling proxy headers."""
        # Check for forwarded headers (from load balancers/proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct connection
        return request.client.host if request.client else "unknown"

    async def _comprehensive_input_validation(self, request: Request):
        """Comprehensive input validation for all request components."""
        try:
            # Validate URL path
            await self._validate_url_path(request)

            # Validate query parameters
            await self._validate_query_parameters(request)

            # Validate headers
            await self._validate_headers(request)

            # Validate request body based on content type
            content_type = request.headers.get("content-type", "")

            if "application/json" in content_type:
                await self._validate_json_payload(request)
            elif "multipart/form-data" in content_type:
                await self._validate_multipart_data(request)
            elif "application/x-www-form-urlencoded" in content_type:
                await self._validate_form_data(request)

        except SecurityValidationError as e:
            await self._log_validation_failure(request, str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input validation failed: {e!s}",
            )

    async def _validate_url_path(self, request: Request):
        """Validate URL path for security threats."""
        path = request.url.path

        # Path traversal check
        if ".." in path or "%2e%2e" in path.lower():
            raise SecurityValidationError("Path traversal attempt detected")

        # Length check
        if len(path) > 2048:
            raise SecurityValidationError("URL path too long")

        # Character validation
        try:
            self.security_validator.validate_string_input(path, "url_path")
        except SecurityValidationError:
            raise SecurityValidationError("URL path contains invalid characters")

    async def _validate_query_parameters(self, request: Request):
        """Validate query parameters."""
        for param, value in request.query_params.items():
            try:
                self.security_validator.validate_string_input(
                    param, f"query_param_{param}")
                if isinstance(value, str):
                    self.security_validator.validate_string_input(
                        value, f"query_value_{param}")
            except SecurityValidationError as e:
                raise SecurityValidationError(
                    f"Query parameter validation failed: {e!s}")

    async def _validate_headers(self, request: Request):
        """Validate request headers."""
        # Check for excessively long headers
        for header_name, header_value in request.headers.items():
            if len(header_value) > 8192:  # 8KB limit
                raise SecurityValidationError(f"Header {header_name} too long")

            # Validate critical headers
            if header_name.lower() in ["authorization", "x-api-key", "cookie"]:
                try:
                    self.security_validator.validate_string_input(
                        header_value,
                        f"header_{header_name}",
                    )
                except SecurityValidationError as e:
                    raise SecurityValidationError(f"Header validation failed: {e!s}")

    async def _validate_json_payload(self, request: Request):
        """Validate JSON payload."""
        try:
            # Check content length
            content_length = int(request.headers.get("content-length", 0))
            if content_length > 10 * 1024 * 1024:  # 10MB limit
                raise SecurityValidationError("Request payload too large")

            # Parse and validate JSON
            body = await request.body()
            if body:
                try:
                    json_data = json.loads(body)
                    self.security_validator.validate_json_input(json_data)
                except json.JSONDecodeError:
                    raise SecurityValidationError("Invalid JSON format")
                except SecurityValidationError as e:
                    raise SecurityValidationError(f"JSON validation failed: {e!s}")

        except Exception as e:
            if isinstance(e, SecurityValidationError):
                raise
            raise SecurityValidationError(f"JSON payload validation error: {e!s}")

    async def _validate_multipart_data(self, request: Request):
        """Validate multipart form data."""
        try:
            form = await request.form()
            file_count = 0
            total_size = 0

            for field_name, field_value in form.items():
                # Validate field name
                self.security_validator.validate_string_input(
                    field_name, f"form_field_{field_name}")

                # Handle file uploads
                if hasattr(field_value, "filename") and field_value.filename:
                    file_count += 1
                    if file_count > self.settings.MAX_UPLOAD_FILES_PER_REQUEST:
                        raise SecurityValidationError("Too many files in upload")

                    # Validate filename
                    self.security_validator.validate_filename(field_value.filename)

                    # Check file size
                    content = await field_value.read()
                    file_size = len(content)
                    total_size += file_size

                    if file_size > self.settings.MAX_UPLOAD_FILE_SIZE:
                        raise SecurityValidationError(
                            f"File {field_value.filename} too large")

                    if total_size > self.settings.MAX_UPLOAD_FILE_SIZE * 5:
                        raise SecurityValidationError("Total upload size too large")

                    # Validate file content
                    validation_result = await self.security_validator.validate_file_upload(field_value)
                    if not validation_result.is_valid:
                        raise SecurityValidationError(
                            f"File validation failed: {
                                ', '.join(
                                    validation_result.security_issues)}", )

                # Handle text fields
                elif isinstance(field_value, str):
                    self.security_validator.validate_string_input(
                        field_value,
                        f"form_value_{field_name}",
                    )

        except Exception as e:
            if isinstance(e, SecurityValidationError):
                raise
            raise SecurityValidationError(f"Multipart data validation error: {e!s}")

    async def _validate_form_data(self, request: Request):
        """Validate URL-encoded form data."""
        try:
            form = await request.form()
            for field_name, field_value in form.items():
                self.security_validator.validate_string_input(
                    field_name, f"form_field_{field_name}")
                if isinstance(field_value, str):
                    self.security_validator.validate_string_input(
                        field_value,
                        f"form_value_{field_name}",
                    )
        except Exception as e:
            if isinstance(e, SecurityValidationError):
                raise
            raise SecurityValidationError(f"Form data validation error: {e!s}")

    async def _detect_attacks(self, request: Request):
        """Detect potential attack patterns."""
        # Combine all request data for analysis
        analysis_data = []

        # URL and query parameters
        analysis_data.append(str(request.url))

        # Headers (excluding sensitive ones)
        for header_name, header_value in request.headers.items():
            if header_name.lower() not in ["authorization", "x-api-key", "cookie"]:
                analysis_data.append(header_value)

        # Request body (if JSON)
        try:
            if "application/json" in request.headers.get("content-type", ""):
                body = await request.body()
                if body:
                    analysis_data.append(body.decode("utf-8", errors="ignore"))
        except BaseException:
            pass  # Skip body analysis if it fails

        # Analyze for attack patterns
        for data_item in analysis_data:
            for attack_type, patterns in self.attack_patterns.items():
                for pattern in patterns:
                    import re
                    if re.search(pattern, data_item, re.IGNORECASE):
                        await security_audit.log_attack_attempt(
                            attack_type=attack_type,
                            source_ip=request.state.client_ip,
                            user_agent=request.state.user_agent,
                            details={
                                "pattern_matched": pattern,
                                "data_sample": data_item[:100],
                            },
                            request_id=request.state.request_id,
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Potential {attack_type} detected",
                        )

    async def _log_successful_request(
        self,
        request: Request,
        response: Response,
        start_time: datetime,
    ):
        """Log successful request."""
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        # Extract user/API key information if available
        user_id = getattr(request.state, "user_id", None)
        api_key_id = getattr(request.state, "api_key_id", None)

        await security_audit.log_data_access(
            user_id=user_id,
            api_key_id=api_key_id,
            resource=request.url.path,
            action=request.method,
            source_ip=request.state.client_ip,
            request_id=request.state.request_id,
        )

    async def _log_security_violation(
        self,
        request: Request,
        exception: HTTPException,
        start_time: datetime,
    ):
        """Log security violation."""
        user_id = getattr(request.state, "user_id", None)
        api_key_id = getattr(request.state, "api_key_id", None)

        await security_audit.log_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=AuditSeverity.HIGH,
            action="request_validation",
            result="blocked",
            user_id=user_id,
            api_key_id=api_key_id,
            source_ip=request.state.client_ip,
            user_agent=request.state.user_agent,
            resource=request.url.path,
            details={
                "method": request.method,
                "status_code": exception.status_code,
                "detail": exception.detail,
                "execution_time": (datetime.utcnow() - start_time).total_seconds(),
            },
            request_id=request.state.request_id,
        )

    async def _log_validation_failure(
        self,
        request: Request,
        error_message: str,
    ):
        """Log input validation failure."""
        user_id = getattr(request.state, "user_id", None)
        api_key_id = getattr(request.state, "api_key_id", None)

        await security_audit.log_input_validation_failure(
            user_id=user_id,
            api_key_id=api_key_id,
            field_name="request_data",
            violation_type="input_validation",
            value_sample=error_message,
            source_ip=request.state.client_ip,
            request_id=request.state.request_id,
        )

    async def _log_system_error(
        self,
        request: Request,
        exception: Exception,
        start_time: datetime,
    ):
        """Log system error."""
        user_id = getattr(request.state, "user_id", None)
        api_key_id = getattr(request.state, "api_key_id", None)

        await security_audit.log_event(
            event_type=AuditEventType.SYSTEM_ERROR,
            severity=AuditSeverity.HIGH,
            action="request_processing",
            result="error",
            user_id=user_id,
            api_key_id=api_key_id,
            source_ip=request.state.client_ip,
            user_agent=request.state.user_agent,
            resource=request.url.path,
            details={
                "method": request.method,
                "error": str(exception),
                "execution_time": (datetime.utcnow() - start_time).total_seconds(),
            },
            request_id=request.state.request_id,
        )


# Legacy middleware for backward compatibility
class InputValidationMiddleware(BaseHTTPMiddleware):
    """Legacy input validation middleware - use SecurityMiddleware instead."""

    def __init__(self, app: ASGIApp, enable_path_traversal_prevention: bool = True):
        super().__init__(app)
        self.security_middleware = SecurityMiddleware(
            app,
            enable_input_validation=True,
            enable_audit_logging=False,
            enable_attack_detection=enable_path_traversal_prevention,
        )

    async def dispatch(self, request: Request, call_next):
        return await self.security_middleware.dispatch(request, call_next)
