"""Security module for AI-Powered Migration Validation System.

Provides comprehensive security components including authentication, authorization,
input validation, API key management, audit logging, and security middleware.
"""

from .api_keys import APIKeyManager
from .api_keys import APIKeyMetadata
from .api_keys import api_key_manager
from .api_keys import api_key_rate_limiter
from .api_keys import get_api_key_metadata
from .api_keys import require_admin_scope
from .api_keys import require_read_scope
from .api_keys import require_service_scope
from .api_keys import require_validation_scope
from .audit import AuditEventType
from .audit import AuditSeverity
from .audit import SecurityAuditLogger
from .audit import security_audit
from .auth import create_access_token
from .auth import decode_access_token
from .auth import get_password_hash
from .auth import verify_password
from .encryption import EncryptionManager
from .headers import SecurityHeaders
from .headers import create_security_headers
# Middleware imported from api.middleware
# from .middleware import InputValidationMiddleware
# from .middleware import SecurityMiddleware
from .password_policy import PasswordValidator
from .password_policy import password_validator
from .rate_limiter import RateLimiter
from .rate_limiter import rate_limit
from .schemas import APIKeyCreateRequest
from .schemas import APIKeyResponse
from .schemas import APIKeyScope
from .schemas import BehavioralValidationRequest
from .schemas import ErrorResponse
from .schemas import FileUploadMetadata
from .schemas import FileUploadResponse
from .schemas import HealthCheckResponse
from .schemas import MigrationValidationRequest
from .schemas import SystemStatsResponse
from .schemas import ValidationErrorResponse
from .schemas import ValidationListQuery
from .schemas import ValidationResultResponse
from .schemas import ValidationStatusResponse
from .schemas import sanitize_response_data
from .schemas import validate_request_schema
from .session_manager import SessionManager
from .session_manager import session_manager
from .validation import InputValidator
from .validation import SecurityValidationError
from .validation import SecurityValidator
from .validation import input_validator
from .validation import security_validator

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
    "create_access_token",
    "decode_access_token",
    "get_password_hash",
    "verify_password",

    # Encryption
    "EncryptionManager",

    # Security Headers
    "SecurityHeaders",
    "create_security_headers",

    # Middleware - available from api.middleware
    # "SecurityMiddleware",
    # "InputValidationMiddleware",

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
