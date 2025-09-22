"""
Security module for AI-Powered Migration Validation System.

Provides authentication, authorization, input validation, and security middleware.
"""

from .auth import AuthManager, JWTAuthenticator, require_auth, require_role
from .middleware import SecurityMiddleware
from .rate_limiter import RateLimiter, rate_limit
from .validation import InputValidator, SecurityValidator
from .encryption import EncryptionManager
from .headers import SecurityHeaders

__all__ = [
    "AuthManager",
    "JWTAuthenticator",
    "require_auth",
    "require_role",
    "SecurityMiddleware",
    "RateLimiter",
    "rate_limit",
    "InputValidator",
    "SecurityValidator",
    "EncryptionManager",
    "SecurityHeaders",
]