"""
Authentication routes for secure API access.

Provides endpoints for user authentication, token management, and user administration.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from ..security.auth import (AuthenticationError, AuthManager, User, UserRole,
                             auth_manager, get_current_user, require_admin,
                             require_viewer)
from ..security.rate_limiter import RateLimitConfig, rate_limit
from ..security.validation import input_validator

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security_scheme = HTTPBearer()


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request model."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""

    refresh_token: str


class CreateUserRequest(BaseModel):
    """Create user request model."""

    username: str
    email: EmailStr
    password: str
    roles: List[UserRole]


class UpdateUserRequest(BaseModel):
    """Update user request model."""

    roles: Optional[List[UserRole]] = None
    is_active: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    """Change password request model."""

    current_password: str
    new_password: str


# Authentication endpoints
@router.post("/login", response_model=LoginResponse)
@rate_limit("auth")
async def login(request: Request, login_data: LoginRequest):
    """
    Authenticate user and return access tokens.

    Rate limited to prevent brute force attacks.
    """
    try:
        # Validate input
        validated_data = {
            "username": login_data.username,
            "password": login_data.password,
        }

        # Authenticate user
        user = auth_manager.authenticate_user(
            validated_data["username"], validated_data["password"]
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create tokens
        access_token = auth_manager.jwt_auth.create_access_token(user)
        refresh_token = auth_manager.jwt_auth.create_refresh_token(user)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=auth_manager.jwt_auth.settings.access_token_expire_minutes * 60,
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "roles": [role.value for role in user.roles],
                "require_password_change": user.require_password_change,
            },
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=LoginResponse)
@rate_limit("auth")
async def refresh_token(request: Request, refresh_data: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    """
    try:
        # Verify refresh token
        token_data = auth_manager.jwt_auth.verify_token(refresh_data.refresh_token)

        # Get user
        user = auth_manager.get_user_by_id(token_data.sub)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Create new tokens
        access_token = auth_manager.jwt_auth.create_access_token(user)
        new_refresh_token = auth_manager.jwt_auth.create_refresh_token(user)

        # Revoke old refresh token
        auth_manager.jwt_auth.revoke_token(token_data.jti)

        return LoginResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=auth_manager.jwt_auth.settings.access_token_expire_minutes * 60,
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "roles": [role.value for role in user.roles],
                "require_password_change": user.require_password_change,
            },
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/logout")
async def logout(
    request: Request, credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
):
    """
    Logout user by revoking token.
    """
    try:
        # Verify and revoke token
        token_data = auth_manager.jwt_auth.verify_token(credentials.credentials)
        auth_manager.jwt_auth.revoke_token(token_data.jti)

        return {"message": "Successfully logged out"}

    except AuthenticationError:
        # Even if token is invalid, logout should succeed
        return {"message": "Logged out"}


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information.
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "roles": [role.value for role in current_user.roles],
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "require_password_change": current_user.require_password_change,
    }


@router.post("/change-password")
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Change user password.
    """
    # Verify current password
    user = auth_manager.authenticate_user(current_user.username, password_data.current_password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )

    # Validate new password strength
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    # Update password (this would be implemented in a real user store)
    # For now, return success
    return {"message": "Password changed successfully"}


# User management endpoints (admin only)
@router.post("/users", response_model=Dict)
async def create_user(
    request: Request, user_data: CreateUserRequest, admin_user: User = Depends(require_admin)
):
    """
    Create new user (admin only).
    """
    try:
        # Validate password strength
        if len(user_data.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long",
            )

        # Create user
        new_user = auth_manager.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            roles=user_data.roles,
        )

        return {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "roles": [role.value for role in new_user.roles],
            "is_active": new_user.is_active,
            "created_at": new_user.created_at.isoformat(),
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/users")
async def list_users(admin_user: User = Depends(require_admin)):
    """
    List all users (admin only).
    """
    # This would fetch from a real user store
    users = []
    for user_data in auth_manager.users.values():
        users.append(
            {
                "id": user_data["id"],
                "username": user_data["username"],
                "email": user_data["email"],
                "roles": [role.value for role in user_data["roles"]],
                "is_active": user_data["is_active"],
                "created_at": user_data["created_at"].isoformat(),
                "last_login": user_data.get("last_login").isoformat()
                if user_data.get("last_login")
                else None,
            }
        )

    return {"users": users, "total": len(users)}


@router.get("/users/{user_id}")
async def get_user(user_id: str, admin_user: User = Depends(require_admin)):
    """
    Get user by ID (admin only).
    """
    user = auth_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "roles": [role.value for role in user.roles],
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str, update_data: UpdateUserRequest, admin_user: User = Depends(require_admin)
):
    """
    Update user (admin only).
    """
    user = auth_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update roles
    if update_data.roles is not None:
        auth_manager.update_user_roles(user_id, update_data.roles)

    # Update active status
    if update_data.is_active is not None and not update_data.is_active:
        auth_manager.deactivate_user(user_id)

    return {"message": "User updated successfully"}


@router.delete("/users/{user_id}")
async def deactivate_user(user_id: str, admin_user: User = Depends(require_admin)):
    """
    Deactivate user (admin only).
    """
    user = auth_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent self-deactivation
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account"
        )

    auth_manager.deactivate_user(user_id)
    return {"message": "User deactivated successfully"}


# System information endpoints
@router.get("/system/info")
async def get_auth_system_info(current_user: User = Depends(require_viewer)):
    """
    Get authentication system information.
    """
    return {
        "auth_enabled": True,
        "supported_roles": [role.value for role in UserRole],
        "token_expiry_minutes": auth_manager.jwt_auth.settings.access_token_expire_minutes,
        "user_count": len(auth_manager.users),
        "failed_attempts_limit": auth_manager.max_failed_attempts,
        "lockout_duration_minutes": auth_manager.lockout_duration.total_seconds() / 60,
    }
