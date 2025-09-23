"""Security headers module for HTTP security headers management.

Provides comprehensive security headers configuration for API protection
against common web vulnerabilities.
"""

from typing import Dict
from typing import List
from typing import Optional

from fastapi import Request
from fastapi import Response


class SecurityHeaders:
    """Security headers manager for HTTP responses."""

    def __init__(
        self,
        custom_csp: Optional[str] = None,
        additional_headers: Optional[Dict[str, str]] = None,
        remove_server_header: bool = True,
        strict_mode: bool = False,
    ):
        """Initialize security headers manager.

        Args:
            custom_csp: Custom Content Security Policy
            additional_headers: Additional custom headers
            remove_server_header: Whether to remove/replace server header
            strict_mode: Enable strict security mode

        """
        self.custom_csp = custom_csp
        self.additional_headers = additional_headers or {}
        self.remove_server_header = remove_server_header
        self.strict_mode = strict_mode

    def get_base_security_headers(self) -> Dict[str, str]:
        """Get base security headers."""
        headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # XSS protection (legacy but still used)
            "X-XSS-Protection": "1; mode=block",
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Prevent information disclosure
            "X-Powered-By": "",  # Remove this header
        }

        if self.remove_server_header:
            headers["Server"] = "AI-Migration-Validator/1.0"

        return headers

    def get_content_security_policy(self) -> str:
        """Get Content Security Policy header."""
        if self.custom_csp:
            return self.custom_csp

        if self.strict_mode:
            # Strict CSP for maximum security
            return (
                "default-src 'none'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "media-src 'none'; "
                "object-src 'none'; "
                "child-src 'none'; "
                "frame-src 'none'; "
                "worker-src 'none'; "
                "form-action 'self'; "
                "upgrade-insecure-requests; "
                "block-all-mixed-content;"
            )
        # Balanced CSP for functionality and security
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:; "
            "media-src 'self'; "
            "object-src 'none'; "
            "child-src 'none'; "
            "frame-src 'none'; "
            "form-action 'self'; "
            "base-uri 'self';"
        )

    def get_hsts_header(
            self,
            max_age: int = 31536000,
            include_subdomains: bool = True) -> str:
        """Get HTTP Strict Transport Security header."""
        hsts = f"max-age={max_age}"
        if include_subdomains:
            hsts += "; includeSubDomains"
        if self.strict_mode:
            hsts += "; preload"
        return hsts

    def get_permissions_policy(self) -> str:
        """Get Permissions Policy header (formerly Feature Policy)."""
        if self.strict_mode:
            # Strict permissions - disable most features
            return (
                "accelerometer=(), "
                "ambient-light-sensor=(), "
                "autoplay=(), "
                "battery=(), "
                "camera=(), "
                "cross-origin-isolated=(), "
                "display-capture=(), "
                "document-domain=(), "
                "encrypted-media=(), "
                "execution-while-not-rendered=(), "
                "execution-while-out-of-viewport=(), "
                "fullscreen=(), "
                "geolocation=(), "
                "gyroscope=(), "
                "keyboard-map=(), "
                "magnetometer=(), "
                "microphone=(), "
                "midi=(), "
                "navigation-override=(), "
                "payment=(), "
                "picture-in-picture=(), "
                "publickey-credentials-get=(), "
                "screen-wake-lock=(), "
                "sync-xhr=(), "
                "usb=(), "
                "web-share=(), "
                "xr-spatial-tracking=()"
            )
        # Basic permissions for API
        return (
            "camera=(), "
            "microphone=(), "
            "geolocation=(), "
            "interest-cohort=(), "
            "payment=(), "
            "usb=()"
        )

    def get_all_security_headers(self, request: Request) -> Dict[str, str]:
        """Get all security headers for response."""
        headers = self.get_base_security_headers()

        # Content Security Policy
        headers["Content-Security-Policy"] = self.get_content_security_policy()

        # HSTS (only for HTTPS)
        if request.url.scheme == "https":
            headers["Strict-Transport-Security"] = self.get_hsts_header()

        # Permissions Policy
        headers["Permissions-Policy"] = self.get_permissions_policy()

        # Additional security headers for APIs
        headers.update(
            {
                "Cache-Control": "no-store, no-cache, must-revalidate, private",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

        # Add custom headers
        headers.update(self.additional_headers)

        return headers

    def apply_headers(self, response: Response, request: Request):
        """Apply security headers to response."""
        security_headers = self.get_all_security_headers(request)

        for header, value in security_headers.items():
            if value:  # Only add non-empty headers
                response.headers[header] = value

    def get_cors_headers(
        self,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        expose_headers: List[str] = None,
        max_age: int = 86400,
        allow_credentials: bool = False,
    ) -> Dict[str, str]:
        """Get CORS headers for cross-origin requests."""
        if allow_origins is None:
            allow_origins = ["https://localhost:3000"]  # Default to secure origins

        if allow_methods is None:
            allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]

        if allow_headers is None:
            allow_headers = [
                "Accept",
                "Accept-Language",
                "Content-Language",
                "Content-Type",
                "Authorization",
                "X-Requested-With",
            ]

        if expose_headers is None:
            expose_headers = [
                "X-Request-ID",
                "X-Process-Time",
                "X-Rate-Limit-Remaining",
                "X-Rate-Limit-Reset",
            ]

        cors_headers = {
            "Access-Control-Allow-Origin": ", ".join(allow_origins)
            if len(allow_origins) > 1
            else allow_origins[0],
            "Access-Control-Allow-Methods": ", ".join(allow_methods),
            "Access-Control-Allow-Headers": ", ".join(allow_headers),
            "Access-Control-Expose-Headers": ", ".join(expose_headers),
            "Access-Control-Max-Age": str(max_age),
        }

        if allow_credentials:
            cors_headers["Access-Control-Allow-Credentials"] = "true"

        return cors_headers


class APISecurityHeaders(SecurityHeaders):
    """Specialized security headers for API endpoints."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_api_specific_headers(self) -> Dict[str, str]:
        """Get API-specific security headers."""
        return {
            # API versioning
            "API-Version": "1.0.0",
            # Rate limiting info (to be filled by rate limiter)
            "X-RateLimit-Limit": "",
            "X-RateLimit-Remaining": "",
            "X-RateLimit-Reset": "",
            # Security info
            "X-Content-Security-Policy": "API endpoint - no client-side execution",
            # Prevent caching of sensitive data
            "Cache-Control": "no-store, no-cache, must-revalidate, private, max-age=0",
            "Pragma": "no-cache",
            "Expires": "-1",
            # Additional API security
            "X-Download-Options": "noopen",
            "X-Permitted-Cross-Domain-Policies": "none",
        }

    def get_all_security_headers(self, request: Request) -> Dict[str, str]:
        """Get all security headers including API-specific ones."""
        headers = super().get_all_security_headers(request)
        headers.update(self.get_api_specific_headers())
        return headers


class DevelopmentSecurityHeaders(SecurityHeaders):
    """Relaxed security headers for development environment."""

    def __init__(self, **kwargs):
        kwargs.setdefault("strict_mode", False)
        super().__init__(**kwargs)

    def get_content_security_policy(self) -> str:
        """Get relaxed CSP for development."""
        return (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' ws: wss: https: http:; "
            "media-src 'self' blob: https:; "
            "object-src 'none'; "
            "base-uri 'self';"
        )

    def get_cors_headers(self, **kwargs) -> Dict[str, str]:
        """Get permissive CORS headers for development."""
        kwargs.setdefault("allow_origins", ["*"])
        kwargs.setdefault("allow_credentials", False)
        return super().get_cors_headers(**kwargs)


class ProductionSecurityHeaders(SecurityHeaders):
    """Strict security headers for production environment."""

    def __init__(self, **kwargs):
        kwargs.setdefault("strict_mode", True)
        super().__init__(**kwargs)

    def get_content_security_policy(self) -> str:
        """Get strict CSP for production."""
        return (
            "default-src 'none'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "media-src 'none'; "
            "object-src 'none'; "
            "child-src 'none'; "
            "frame-src 'none'; "
            "worker-src 'none'; "
            "form-action 'self'; "
            "upgrade-insecure-requests; "
            "block-all-mixed-content; "
            "base-uri 'none';"
        )

    def get_cors_headers(self, **kwargs) -> Dict[str, str]:
        """Get restricted CORS headers for production."""
        # Override with secure defaults for production
        kwargs.setdefault("allow_origins", ["https://migration-validator.com"])
        kwargs.setdefault("allow_credentials", True)
        return super().get_cors_headers(**kwargs)


def create_security_headers(environment: str = "development") -> SecurityHeaders:
    """Factory function to create appropriate security headers for environment."""
    if environment == "production":
        return ProductionSecurityHeaders()
    if environment == "development":
        return DevelopmentSecurityHeaders()
    return APISecurityHeaders()
