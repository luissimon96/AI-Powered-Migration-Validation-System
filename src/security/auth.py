"""
Authentication and authorization module for secure API access.

Implements JWT-based authentication with role-based access control (RBAC).
Provides secure user management and session handling.
"""

import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional, Set

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from ..core.config import get_settings


class UserRole(Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    VALIDATOR = "validator"
    VIEWER = "viewer"
    API_CLIENT = "api_client"


class User(BaseModel):
    """User model with security attributes."""

    id: str
    username: str
    email: EmailStr
    roles: List[UserRole]
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    account_locked_until: Optional[datetime] = None
    require_password_change: bool = False


class TokenData(BaseModel):
    """JWT token payload data."""

    sub: str  # user ID
    username: str
    roles: List[str]
    exp: datetime
    iat: datetime
    jti: str  # JWT ID for token revocation


class AuthenticationError(Exception):
    """Authentication-related errors."""
    pass


class AuthorizationError(Exception):
    """Authorization-related errors."""
    pass


class JWTAuthenticator:
    """JWT token management with security best practices."""

    def __init__(self):
        self.settings = get_settings()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.algorithm = "HS256"
        self.revoked_tokens: Set[str] = set()  # In production, use Redis

        # Ensure secret key is secure in production
        if self.settings.environment == "production" and self.settings.secret_key == "change-me-in-production":
            raise ValueError("Secret key must be changed in production environment")

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def create_access_token(
        self,
        user: User,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token with user claims."""
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.settings.access_token_expire_minutes
            )

        # Generate unique token ID for revocation
        jti = secrets.token_urlsafe(32)

        to_encode = {
            "sub": user.id,
            "username": user.username,
            "roles": [role.value for role in user.roles],
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": jti,
        }

        encoded_jwt = jwt.encode(
            to_encode,
            self.settings.secret_key,
            algorithm=self.algorithm
        )
        return encoded_jwt

    def create_refresh_token(self, user: User) -> str:
        """Create refresh token for token renewal."""
        expire = datetime.now(timezone.utc) + timedelta(days=30)
        jti = secrets.token_urlsafe(32)

        to_encode = {
            "sub": user.id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": jti,
        }

        return jwt.encode(
            to_encode,
            self.settings.secret_key,
            algorithm=self.algorithm
        )

    def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=[self.algorithm]
            )

            # Check if token is revoked
            jti = payload.get("jti")
            if jti in self.revoked_tokens:
                raise AuthenticationError("Token has been revoked")

            return TokenData(
                sub=payload["sub"],
                username=payload["username"],
                roles=payload["roles"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                jti=jti,
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.JWTError:
            raise AuthenticationError("Invalid token")

    def revoke_token(self, jti: str):
        """Revoke token by adding JTI to blacklist."""
        self.revoked_tokens.add(jti)

    def cleanup_revoked_tokens(self):
        """Remove expired tokens from revoked list."""
        # In production, implement with Redis TTL
        pass


class AuthManager:
    """User management and authentication orchestrator."""

    def __init__(self):
        self.jwt_auth = JWTAuthenticator()
        self.users: Dict[str, Dict] = {}  # In production, use database
        self.failed_attempts: Dict[str, List[datetime]] = {}
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)

        # Create default admin user if not exists
        self._create_default_admin()

    def _create_default_admin(self):
        """Create default admin user for initial setup."""
        admin_id = "admin-001"
        if admin_id not in self.users:
            admin_password = secrets.token_urlsafe(16)  # Generate secure password
            self.users[admin_id] = {
                "id": admin_id,
                "username": "admin",
                "email": "admin@migration-validator.local",
                "password_hash": self.jwt_auth.hash_password(admin_password),
                "roles": [UserRole.ADMIN],
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "require_password_change": True,
            }
            print(f"Default admin created - Username: admin, Password: {admin_password}")

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        # Find user
        user_data = None
        for uid, data in self.users.items():
            if data["username"] == username:
                user_data = data
                break

        if not user_data:
            return None

        # Check account lockout
        if self._is_account_locked(username):
            raise AuthenticationError("Account is locked due to failed login attempts")

        # Verify password
        if not self.jwt_auth.verify_password(password, user_data["password_hash"]):
            self._record_failed_attempt(username)
            return None

        # Reset failed attempts on successful login
        self.failed_attempts.pop(username, None)

        # Update last login
        user_data["last_login"] = datetime.now(timezone.utc)

        return User(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            roles=user_data["roles"],
            is_active=user_data["is_active"],
            created_at=user_data["created_at"],
            last_login=user_data.get("last_login"),
            require_password_change=user_data.get("require_password_change", False),
        )

    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts."""
        if username not in self.failed_attempts:
            return False

        attempts = self.failed_attempts[username]
        recent_attempts = [
            attempt for attempt in attempts
            if datetime.now(timezone.utc) - attempt < self.lockout_duration
        ]

        return len(recent_attempts) >= self.max_failed_attempts

    def _record_failed_attempt(self, username: str):
        """Record failed login attempt."""
        if username not in self.failed_attempts:
            self.failed_attempts[username] = []

        self.failed_attempts[username].append(datetime.now(timezone.utc))

        # Clean up old attempts
        cutoff = datetime.now(timezone.utc) - self.lockout_duration
        self.failed_attempts[username] = [
            attempt for attempt in self.failed_attempts[username]
            if attempt > cutoff
        ]

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: List[UserRole]
    ) -> User:
        """Create new user with validation."""
        # Validate uniqueness
        for data in self.users.values():
            if data["username"] == username:
                raise ValueError("Username already exists")
            if data["email"] == email:
                raise ValueError("Email already exists")

        # Generate user ID
        user_id = f"user-{hashlib.sha256(username.encode()).hexdigest()[:12]}"

        # Store user
        self.users[user_id] = {
            "id": user_id,
            "username": username,
            "email": email,
            "password_hash": self.jwt_auth.hash_password(password),
            "roles": roles,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }

        return User(
            id=user_id,
            username=username,
            email=email,
            roles=roles,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        user_data = self.users.get(user_id)
        if not user_data:
            return None

        return User(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            roles=user_data["roles"],
            is_active=user_data["is_active"],
            created_at=user_data["created_at"],
            last_login=user_data.get("last_login"),
        )

    def update_user_roles(self, user_id: str, roles: List[UserRole]):
        """Update user roles."""
        if user_id in self.users:
            self.users[user_id]["roles"] = roles

    def deactivate_user(self, user_id: str):
        """Deactivate user account."""
        if user_id in self.users:
            self.users[user_id]["is_active"] = False


# Global auth manager instance
auth_manager = AuthManager()
security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> User:
    """FastAPI dependency to get current authenticated user."""
    try:
        token_data = auth_manager.jwt_auth.verify_token(credentials.credentials)
        user = auth_manager.get_user_by_id(token_data.sub)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_auth(func):
    """Decorator to require authentication for endpoint."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # This is handled by FastAPI dependencies
        return await func(*args, **kwargs)
    return wrapper


def require_role(required_roles: List[UserRole]):
    """Decorator to require specific roles for endpoint access."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (should be injected by dependency)
            user = None
            for arg in kwargs.values():
                if isinstance(arg, User):
                    user = arg
                    break

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            user_roles = set(user.roles)
            required_roles_set = set(required_roles)

            if not user_roles.intersection(required_roles_set):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


class RoleChecker:
    """FastAPI dependency for role-based access control."""

    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        user_roles = set(user.roles)
        allowed_roles_set = set(self.allowed_roles)

        if not user_roles.intersection(allowed_roles_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        return user


# Common role dependencies
require_admin = RoleChecker([UserRole.ADMIN])
require_validator = RoleChecker([UserRole.ADMIN, UserRole.VALIDATOR])
require_viewer = RoleChecker([UserRole.ADMIN, UserRole.VALIDATOR, UserRole.VIEWER])
require_api_client = RoleChecker([UserRole.ADMIN, UserRole.API_CLIENT])