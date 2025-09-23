"""
Comprehensive API key management system with scopes, permissions, and rate limiting.

Provides secure API key authentication for service-to-service communication
with proper scope-based authorization and audit logging.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from ..core.config import get_settings
from ..core.logging import logger
from ..database.service import get_database_service
from .schemas import APIKeyScope, APIKeyCreateRequest, APIKeyResponse
from .encryption import encrypt_sensitive_data, decrypt_sensitive_data


class APIKeyMetadata(BaseModel):
    """API key metadata model."""

    id: str
    name: str
    description: Optional[str]
    scopes: List[APIKeyScope]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    rate_limit_per_minute: int
    is_active: bool
    created_by: str
    usage_count: int = 0


class APIKeyManager:
    """Comprehensive API key management with database persistence."""

    def __init__(self):
        self.settings = get_settings()
        self.db = get_database_service()
        self.logger = logger.bind(component="APIKeyManager")

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage."""
        salt = self.settings.SECRET_KEY.encode()
        return hashlib.pbkdf2_hmac('sha256', api_key.encode(), salt, 100000).hex()

    def _generate_api_key(self) -> str:
        """Generate a secure API key."""
        return f"amvs_{secrets.token_urlsafe(32)}"

    async def create_api_key(
        self,
        request: APIKeyCreateRequest,
        created_by: str
    ) -> tuple[str, APIKeyMetadata]:
        """Create a new API key with metadata."""
        try:
            # Generate API key
            api_key = self._generate_api_key()
            api_key_id = secrets.token_urlsafe(16)

            # Hash for storage
            hashed_key = self._hash_api_key(api_key)

            # Create metadata
            metadata = APIKeyMetadata(
                id=api_key_id,
                name=request.name,
                description=request.description,
                scopes=request.scopes,
                created_at=datetime.utcnow(),
                expires_at=request.expires_at,
                last_used_at=None,
                rate_limit_per_minute=request.rate_limit_per_minute,
                is_active=True,
                created_by=created_by
            )

            # Store in database
            await self.db.store_api_key(
                api_key_id=api_key_id,
                hashed_key=hashed_key,
                metadata=metadata.dict()
            )

            self.logger.info(
                "API key created",
                api_key_id=api_key_id,
                name=request.name,
                scopes=request.scopes,
                created_by=created_by
            )

            return api_key, metadata

        except Exception as e:
            self.logger.error("Failed to create API key", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create API key"
            )

    async def validate_api_key(self, api_key: str) -> APIKeyMetadata:
        """Validate API key and return metadata."""
        try:
            if not api_key or not api_key.startswith("amvs_"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key format"
                )

            # Hash the provided key
            hashed_key = self._hash_api_key(api_key)

            # Retrieve from database
            stored_data = await self.db.get_api_key_by_hash(hashed_key)
            if not stored_data:
                self.logger.warning("Invalid API key provided")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )

            metadata = APIKeyMetadata(**stored_data['metadata'])

            # Check if key is active
            if not metadata.is_active:
                self.logger.warning("Inactive API key used", api_key_id=metadata.id)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key is inactive"
                )

            # Check expiration
            if metadata.expires_at and datetime.utcnow() > metadata.expires_at:
                self.logger.warning("Expired API key used", api_key_id=metadata.id)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key has expired"
                )

            # Update last used timestamp
            await self._update_last_used(metadata.id)

            return metadata

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error("API key validation failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API key validation failed"
            )

    async def _update_last_used(self, api_key_id: str):
        """Update last used timestamp for API key."""
        try:
            await self.db.update_api_key_last_used(api_key_id, datetime.utcnow())
        except Exception as e:
            self.logger.warning("Failed to update API key last used", error=str(e))

    async def revoke_api_key(self, api_key_id: str, revoked_by: str) -> bool:
        """Revoke an API key."""
        try:
            success = await self.db.deactivate_api_key(api_key_id)
            if success:
                self.logger.info(
                    "API key revoked",
                    api_key_id=api_key_id,
                    revoked_by=revoked_by
                )
            return success
        except Exception as e:
            self.logger.error("Failed to revoke API key", error=str(e))
            return False

    async def list_api_keys(self, created_by: Optional[str] = None) -> List[APIKeyResponse]:
        """List API keys with optional filtering."""
        try:
            api_keys_data = await self.db.list_api_keys(created_by=created_by)

            api_keys = []
            for data in api_keys_data:
                metadata = APIKeyMetadata(**data['metadata'])
                api_keys.append(APIKeyResponse(
                    id=metadata.id,
                    name=metadata.name,
                    description=metadata.description,
                    scopes=metadata.scopes,
                    created_at=metadata.created_at,
                    expires_at=metadata.expires_at,
                    last_used_at=metadata.last_used_at,
                    rate_limit_per_minute=metadata.rate_limit_per_minute,
                    is_active=metadata.is_active
                ))

            return api_keys

        except Exception as e:
            self.logger.error("Failed to list API keys", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list API keys"
            )

    async def check_scope_permission(self, api_key_metadata: APIKeyMetadata, required_scope: APIKeyScope) -> bool:
        """Check if API key has required scope permission."""
        return required_scope in api_key_metadata.scopes or APIKeyScope.ADMIN in api_key_metadata.scopes


# Global API key manager instance
api_key_manager = APIKeyManager()

# FastAPI security dependency
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key_metadata(api_key: str = Security(api_key_header)) -> APIKeyMetadata:
    """FastAPI dependency to get and validate API key."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing"
        )

    return await api_key_manager.validate_api_key(api_key)


def require_api_scope(required_scope: APIKeyScope):
    """Dependency factory for scope-based API authorization."""

    async def scope_checker(api_key_metadata: APIKeyMetadata = Security(get_api_key_metadata)):
        if not await api_key_manager.check_scope_permission(api_key_metadata, required_scope):
            logger.warning(
                "Insufficient API key permissions",
                api_key_id=api_key_metadata.id,
                required_scope=required_scope,
                available_scopes=api_key_metadata.scopes
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key does not have required scope: {required_scope}"
            )

        return api_key_metadata

    return scope_checker


# Common scope dependencies
require_read_scope = require_api_scope(APIKeyScope.READ_ONLY)
require_validation_scope = require_api_scope(APIKeyScope.VALIDATION)
require_admin_scope = require_api_scope(APIKeyScope.ADMIN)
require_service_scope = require_api_scope(APIKeyScope.SERVICE)


# Rate limiting integration
class APIKeyRateLimiter:
    """Rate limiter integrated with API key permissions."""

    def __init__(self):
        self.usage_tracker: Dict[str, Dict[str, any]] = {}
        self.logger = logger.bind(component="APIKeyRateLimiter")

    async def check_rate_limit(self, api_key_metadata: APIKeyMetadata) -> bool:
        """Check if API key is within rate limits."""
        current_minute = datetime.utcnow().replace(second=0, microsecond=0)
        key_id = api_key_metadata.id

        if key_id not in self.usage_tracker:
            self.usage_tracker[key_id] = {
                'minute': current_minute,
                'count': 0
            }

        tracker = self.usage_tracker[key_id]

        # Reset counter if minute has changed
        if tracker['minute'] != current_minute:
            tracker['minute'] = current_minute
            tracker['count'] = 0

        # Check rate limit
        if tracker['count'] >= api_key_metadata.rate_limit_per_minute:
            self.logger.warning(
                "API key rate limit exceeded",
                api_key_id=key_id,
                limit=api_key_metadata.rate_limit_per_minute,
                current_count=tracker['count']
            )
            return False

        # Increment counter
        tracker['count'] += 1
        return True

    async def require_rate_limit_check(self, api_key_metadata: APIKeyMetadata = Security(get_api_key_metadata)):
        """FastAPI dependency for rate limit checking."""
        if not await self.check_rate_limit(api_key_metadata):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="API key rate limit exceeded"
            )
        return api_key_metadata


# Global rate limiter instance
api_key_rate_limiter = APIKeyRateLimiter()


# Legacy compatibility functions (for backward compatibility)
async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """Legacy API key validation function."""
    metadata = await get_api_key_metadata(api_key)
    return api_key


async def get_api_key_name(api_key: str = Security(api_key_header)) -> Optional[str]:
    """Legacy API key name retrieval function."""
    try:
        metadata = await get_api_key_metadata(api_key)
        return metadata.name
    except HTTPException:
        return None