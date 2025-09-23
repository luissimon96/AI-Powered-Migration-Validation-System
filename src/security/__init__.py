"""Security module for AI-Powered Migration Validation System.

Provides comprehensive security components including authentication, authorization,
input validation, API key management, audit logging, and security middleware.
"""

from .api_keys import (
                       APIKeyManager,
                       APIKeyMetadata,
                       api_key_manager,
                       api_key_rate_limiter,
                       get_api_key_metadata,
                       require_admin_scope,
                       require_read_scope,
                       require_service_scope,
                       require_validation_scope,
)
from .audit import AuditEventType, AuditSeverity, SecurityAuditLogger, security_audit
from .auth import AuthManager, JWTAuthenticator, require_auth, require_role
from .encryption import EncryptionManager
from .headers import SecurityHeaders, create_security_headers
from .middleware import InputValidationMiddleware, SecurityMiddleware
from .password_policy import PasswordValidator, password_validator
from .rate_limiter import RateLimiter, rate_limit
from .schemas import (
                       APIKeyCreateRequest,
                       APIKeyResponse,
                       APIKeyScope,
                       BehavioralValidationRequest,
                       ErrorResponse,
                       FileUploadMetadata,
                       FileUploadResponse,
                       HealthCheckResponse,
                       MigrationValidationRequest,
                       SystemStatsResponse,
                       ValidationErrorResponse,
                       ValidationListQuery,
                       ValidationResultResponse,
                       ValidationStatusResponse,
                       sanitize_response_data,
                       validate_request_schema,
)
from .session_manager import SessionManager, session_manager
from .validation import (
                       InputValidator,
                       SecurityValidationError,
                       SecurityValidator,
                       input_validator,
                       security_validator,
)

__all__ = [
    # API Key Management
    "APIKeyManager",
    "APIKeyMetadata",
    "api_key_manager",
    "api_key_rate_limiter",
    "get_api_key_metadata",
    "require_admin_scope",
    "require_read_scope",
    "require_service_scope",
    "require_validation_scope",

    # Audit Logging
    "AuditEventType",
    "AuditSeverity",
    "SecurityAuditLogger",
    "security_audit",

    # Authentication & Authorization
    "AuthManager",
    "JWTAuthenticator",
    "require_auth",
    "require_role",

    # Encryption
    "EncryptionManager",

    # Security Headers
    "SecurityHeaders",
    "create_security_headers",

    # Middleware
    "SecurityMiddleware",
    "InputValidationMiddleware",

    # Rate Limiting
    "RateLimiter",
    "rate_limit",

    # Input Validation Schemas
    "APIKeyCreateRequest",
    "APIKeyResponse",
    "APIKeyScope",
    "BehavioralValidationRequest",
    "ErrorResponse",
    "FileUploadMetadata",
    "FileUploadResponse",
    "HealthCheckResponse",
    "MigrationValidationRequest",
    "SystemStatsResponse",
    "ValidationErrorResponse",
    "ValidationListQuery",
    "ValidationResultResponse",
    "ValidationStatusResponse",
    "validate_request_schema",
    "sanitize_response_data",

    # Input Validation
    "InputValidator",
    "SecurityValidator",
    "SecurityValidationError",
    "input_validator",
    "security_validator",

    # Password Policy
    "PasswordValidator",
    "password_validator",

    # Session Management
    "SessionManager",
    "session_manager",
]
