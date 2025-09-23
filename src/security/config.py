"""
Security configuration module for production-grade security settings.

Centralizes all security-related configuration including authentication,
encryption, rate limiting, and monitoring settings.
"""

import os
import secrets
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator

from ..core.config import get_settings


class SecurityLevel(Enum):
    """Security levels for different environments."""

    LOW = "low"  # Development, testing
    MEDIUM = "medium"  # Staging, internal
    HIGH = "high"  # Production, public-facing
    CRITICAL = "critical"  # High-value, sensitive data


class AuthenticationMethod(Enum):
    """Supported authentication methods."""

    JWT = "jwt"
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC = "basic"


@dataclass
class SecurityPolicy:
    """Security policy configuration."""

    # Password requirements
    min_password_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_numbers: bool = True
    require_special_chars: bool = True
    password_history_count: int = 5

    # Session management
    session_timeout_minutes: int = 30
    idle_timeout_minutes: int = 15
    max_concurrent_sessions: int = 5

    # Account security
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    require_email_verification: bool = True
    require_mfa: bool = False

    # API security
    require_https: bool = True
    allow_http_dev_only: bool = True
    strict_transport_security: bool = True

    # File upload security
    max_file_size_mb: int = 10
    max_total_upload_mb: int = 100
    scan_for_malware: bool = True
    quarantine_suspicious_files: bool = True

    # Rate limiting
    enable_rate_limiting: bool = True
    global_rate_limit_per_minute: int = 1000
    user_rate_limit_per_minute: int = 100
    burst_multiplier: float = 1.5

    # Security headers
    enable_security_headers: bool = True
    strict_csp: bool = True
    enable_hsts: bool = True
    hsts_max_age_seconds: int = 31536000

    # Monitoring and logging
    log_security_events: bool = True
    log_failed_attempts: bool = True
    monitor_suspicious_activity: bool = True
    alert_on_multiple_failures: bool = True


class SecurityConfig(BaseModel):
    """Main security configuration."""

    # Environment and level
    security_level: SecurityLevel = SecurityLevel.HIGH
    environment: str = Field(default_factory=lambda: get_settings().environment)

    # Authentication configuration
    auth_methods: List[AuthenticationMethod] = [AuthenticationMethod.JWT]
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30

    # Encryption configuration
    encryption_algorithm: str = "AES-256-GCM"
    key_rotation_days: int = 90
    encrypt_sensitive_data: bool = True
    encrypt_at_rest: bool = True

    # Rate limiting configuration
    rate_limit_storage: str = "memory"  # "memory", "redis"
    rate_limit_algorithm: str = "sliding_window"
    rate_limits: Dict[str, Dict[str, int]] = {
        "auth": {"requests": 5, "window": 60},
        "upload": {"requests": 10, "window": 300},
        "validation": {"requests": 20, "window": 3600},
        "api_general": {"requests": 100, "window": 60},
    }

    # Input validation configuration
    max_request_size_mb: int = 10
    max_json_depth: int = 10
    max_string_length: int = 10000
    enable_input_sanitization: bool = True
    strict_validation: bool = True

    # File security configuration
    allowed_mime_types: List[str] = [
        "text/plain",
        "application/json",
        "image/png",
        "image/jpeg",
        "text/html",
        "text/css",
        "application/javascript",
        "text/csv",
    ]
    blocked_mime_types: List[str] = [
        "application/x-executable",
        "application/x-msdos-program",
        "application/vnd.microsoft.portable-executable",
    ]
    scan_uploaded_files: bool = True
    quarantine_malicious_files: bool = True

    # Security headers configuration
    security_headers: Dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }

    # CORS configuration
    cors_allow_origins: List[str] = ["https://localhost:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: List[str] = ["Accept", "Authorization", "Content-Type"]

    # Monitoring configuration
    enable_security_monitoring: bool = True
    log_security_events: bool = True
    alert_on_security_violations: bool = True
    security_log_level: str = "INFO"

    # Compliance configuration
    gdpr_compliance: bool = True
    data_retention_days: int = 365
    audit_log_retention_days: int = 2555  # 7 years
    enable_data_anonymization: bool = True

    @validator("jwt_secret_key")
    def validate_jwt_secret(cls, v, values):
        """Validate JWT secret key strength."""
        environment = values.get("environment", "development")
        if environment == "production" and len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters in production")
        return v

    @validator("cors_allow_origins")
    def validate_cors_origins(cls, v, values):
        """Validate CORS origins for security."""
        environment = values.get("environment", "development")
        if environment == "production" and "*" in v:
            raise ValueError("Wildcard CORS origins not allowed in production")
        return v

    def get_policy_for_level(self) -> SecurityPolicy:
        """Get security policy based on security level."""
        if self.security_level == SecurityLevel.LOW:
            return SecurityPolicy(
                min_password_length=6,
                require_uppercase=False,
                require_special_chars=False,
                max_login_attempts=10,
                require_https=False,
                enable_rate_limiting=False,
                strict_csp=False,
            )
        elif self.security_level == SecurityLevel.MEDIUM:
            return SecurityPolicy(
                min_password_length=8,
                max_login_attempts=7,
                lockout_duration_minutes=10,
                require_https=True,
                allow_http_dev_only=True,
            )
        elif self.security_level == SecurityLevel.HIGH:
            return SecurityPolicy(
                min_password_length=10,
                require_mfa=False,  # Optional for high
                max_login_attempts=5,
                lockout_duration_minutes=15,
                require_https=True,
                allow_http_dev_only=False,
                scan_for_malware=True,
            )
        else:  # CRITICAL
            return SecurityPolicy(
                min_password_length=12,
                require_mfa=True,
                max_login_attempts=3,
                lockout_duration_minutes=30,
                require_https=True,
                allow_http_dev_only=False,
                scan_for_malware=True,
                quarantine_suspicious_files=True,
                strict_csp=True,
                enable_hsts=True,
            )

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def get_rate_limit_config(self, limit_type: str) -> Dict[str, int]:
        """Get rate limit configuration for specific type."""
        return self.rate_limits.get(limit_type, self.rate_limits["api_general"])

    def should_enforce_https(self) -> bool:
        """Determine if HTTPS should be enforced."""
        policy = self.get_policy_for_level()
        if self.is_development() and policy.allow_http_dev_only:
            return False
        return policy.require_https

    def get_content_security_policy(self) -> str:
        """Get Content Security Policy based on security level."""
        policy = self.get_policy_for_level()

        if policy.strict_csp or self.is_production():
            return (
                "default-src 'none'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
        else:
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https:; "
                "object-src 'none';"
            )


class SecurityConstants:
    """Security-related constants."""

    # Token types
    ACCESS_TOKEN = "access"
    REFRESH_TOKEN = "refresh"
    API_TOKEN = "api"

    # User roles
    ADMIN_ROLE = "admin"
    VALIDATOR_ROLE = "validator"
    VIEWER_ROLE = "viewer"
    API_CLIENT_ROLE = "api_client"

    # Security events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_EXPIRED = "token_expired"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    FILE_UPLOAD_BLOCKED = "file_upload_blocked"
    SECURITY_VIOLATION = "security_violation"

    # Error codes
    AUTH_REQUIRED = "AUTH_001"
    INVALID_CREDENTIALS = "AUTH_002"
    ACCOUNT_LOCKED = "AUTH_003"
    TOKEN_INVALID = "AUTH_004"
    INSUFFICIENT_PERMISSIONS = "AUTH_005"
    RATE_LIMIT_ERROR = "RATE_001"
    VALIDATION_ERROR = "VAL_001"
    FILE_SECURITY_ERROR = "FILE_001"


def create_security_config(
    environment: Optional[str] = None, security_level: Optional[SecurityLevel] = None
) -> SecurityConfig:
    """Factory function to create security configuration."""
    settings = get_settings()

    config = SecurityConfig(
        environment=environment or settings.environment,
        security_level=security_level
        or (
            SecurityLevel.HIGH
            if settings.environment == "production"
            else SecurityLevel.MEDIUM
            if settings.environment == "staging"
            else SecurityLevel.LOW
        ),
    )

    # Override with environment-specific settings
    if settings.environment == "production":
        config.cors_allow_origins = [
            "https://migration-validator.com",
            "https://api.migration-validator.com",
        ]
        config.enable_security_monitoring = True
        config.alert_on_security_violations = True

    elif settings.environment == "development":
        config.cors_allow_origins = ["*"]
        config.cors_allow_credentials = False
        config.enable_security_monitoring = False

    # Load secrets from environment
    if jwt_secret := os.getenv("JWT_SECRET_KEY"):
        config.jwt_secret_key = jwt_secret

    return config


# Global security configuration
_security_config: Optional[SecurityConfig] = None


def get_security_config() -> SecurityConfig:
    """Get global security configuration."""
    global _security_config
    if _security_config is None:
        _security_config = create_security_config()
    return _security_config


def reload_security_config():
    """Reload security configuration."""
    global _security_config
    _security_config = None
    return get_security_config()
