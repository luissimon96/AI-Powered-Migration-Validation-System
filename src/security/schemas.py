"""
Comprehensive input validation schemas for API endpoints.

Provides Pydantic schemas with security-focused validation for all API inputs,
including file uploads, request payloads, and query parameters.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator, root_validator
from pydantic.networks import EmailStr, HttpUrl

from ..core.models import TechnologyType, ValidationScope, InputType
from .validation import SecurityValidator, SecurityValidationError


class APIKeyScope(str, Enum):
    """API key access scopes."""

    READ_ONLY = "read_only"
    VALIDATION = "validation"
    ADMIN = "admin"
    SERVICE = "service"


class FileUploadType(str, Enum):
    """Allowed file upload types."""

    SOURCE_CODE = "source_code"
    SCREENSHOT = "screenshot"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"


class RequestPriority(str, Enum):
    """Request priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# Authentication schemas
class APIKeyCreateRequest(BaseModel):
    """Request to create a new API key."""

    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    description: Optional[str] = Field(None, max_length=500, description="API key description")
    scopes: List[APIKeyScope] = Field(..., min_items=1, description="API key access scopes")
    expires_at: Optional[datetime] = Field(None, description="API key expiration date")
    rate_limit_per_minute: int = Field(60, ge=1, le=1000, description="Rate limit per minute")

    @validator('name')
    def validate_name(cls, v):
        """Validate API key name."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('API key name can only contain alphanumeric characters, hyphens, and underscores')
        return v.strip()

    @validator('description')
    def validate_description(cls, v):
        """Validate API key description."""
        if v is not None:
            security_validator = SecurityValidator()
            return security_validator.validate_string_input(v, "description")
        return v


class APIKeyResponse(BaseModel):
    """Response containing API key information."""

    id: str
    name: str
    description: Optional[str]
    scopes: List[APIKeyScope]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    rate_limit_per_minute: int
    is_active: bool


class APIKeyListResponse(BaseModel):
    """Response containing list of API keys."""

    api_keys: List[APIKeyResponse]
    total: int


# File upload schemas
class FileUploadMetadata(BaseModel):
    """Metadata for file uploads."""

    upload_type: FileUploadType = Field(..., description="Type of file being uploaded")
    description: Optional[str] = Field(None, max_length=500, description="File description")
    technology_context: Optional[str] = Field(None, max_length=50, description="Technology context")

    @validator('description')
    def validate_description(cls, v):
        """Validate file description."""
        if v is not None:
            security_validator = SecurityValidator()
            return security_validator.validate_string_input(v, "description")
        return v


class FileUploadResponse(BaseModel):
    """Response for file upload operations."""

    file_id: str
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    upload_type: FileUploadType
    uploaded_at: datetime
    validation_result: Dict[str, Any]


class FileUploadBatchResponse(BaseModel):
    """Response for batch file upload operations."""

    uploaded_files: List[FileUploadResponse]
    failed_uploads: List[Dict[str, str]]
    total_files: int
    successful_uploads: int
    total_size: int


# Migration validation schemas
class MigrationValidationRequest(BaseModel):
    """Comprehensive migration validation request schema."""

    source_technology: str = Field(..., min_length=1, max_length=50, description="Source technology")
    target_technology: str = Field(..., min_length=1, max_length=50, description="Target technology")
    validation_scope: str = Field(..., min_length=1, max_length=50, description="Validation scope")
    source_tech_version: Optional[str] = Field(None, max_length=20, description="Source technology version")
    target_tech_version: Optional[str] = Field(None, max_length=20, description="Target technology version")
    priority: RequestPriority = Field(RequestPriority.NORMAL, description="Request priority")
    timeout_seconds: int = Field(300, ge=30, le=3600, description="Request timeout in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @validator('source_technology', 'target_technology')
    def validate_technology(cls, v):
        """Validate technology values."""
        security_validator = SecurityValidator()
        validated = security_validator.validate_string_input(v, "technology")

        # Check against allowed technology types
        valid_technologies = [tech.value for tech in TechnologyType]
        if validated not in valid_technologies:
            raise ValueError(f'Technology must be one of: {valid_technologies}')

        return validated

    @validator('validation_scope')
    def validate_scope(cls, v):
        """Validate validation scope."""
        security_validator = SecurityValidator()
        validated = security_validator.validate_string_input(v, "validation_scope")

        # Check against allowed scopes
        valid_scopes = [scope.value for scope in ValidationScope]
        if validated not in valid_scopes:
            raise ValueError(f'Validation scope must be one of: {valid_scopes}')

        return validated

    @validator('source_tech_version', 'target_tech_version')
    def validate_version(cls, v):
        """Validate technology version."""
        if v is not None:
            security_validator = SecurityValidator()
            validated = security_validator.validate_string_input(v, "version")

            # Version format validation
            if not re.match(r'^[a-zA-Z0-9._-]+$', validated):
                raise ValueError('Version can only contain alphanumeric characters, dots, hyphens, and underscores')

            return validated
        return v

    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata."""
        if v is not None:
            security_validator = SecurityValidator()
            return security_validator.validate_json_input(v)
        return v


# Behavioral validation schemas
class BehavioralValidationRequest(BaseModel):
    """Comprehensive behavioral validation request schema."""

    source_url: HttpUrl = Field(..., description="Source application URL")
    target_url: HttpUrl = Field(..., description="Target application URL")
    validation_scenarios: List[str] = Field(..., min_items=1, max_items=10, description="Validation scenarios")
    credentials: Optional[Dict[str, str]] = Field(None, description="Authentication credentials")
    timeout_seconds: int = Field(300, ge=30, le=1800, description="Timeout in seconds")
    browser_options: Optional[Dict[str, Any]] = Field(None, description="Browser configuration options")
    priority: RequestPriority = Field(RequestPriority.NORMAL, description="Request priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @validator('validation_scenarios')
    def validate_scenarios(cls, v):
        """Validate validation scenarios."""
        security_validator = SecurityValidator()
        validated_scenarios = []

        for scenario in v:
            if not isinstance(scenario, str):
                raise ValueError('Each scenario must be a string')

            validated = security_validator.validate_string_input(scenario, "scenario")
            validated_scenarios.append(validated)

        return validated_scenarios

    @validator('credentials')
    def validate_credentials(cls, v):
        """Validate credentials."""
        if v is not None:
            security_validator = SecurityValidator()

            # Validate structure
            if not isinstance(v, dict):
                raise ValueError('Credentials must be a dictionary')

            # Validate each credential field
            for key, value in v.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ValueError('Credential keys and values must be strings')

                security_validator.validate_string_input(key, f"credential_key_{key}")
                security_validator.validate_string_input(value, f"credential_value_{key}")

            return v
        return v

    @validator('browser_options')
    def validate_browser_options(cls, v):
        """Validate browser options."""
        if v is not None:
            security_validator = SecurityValidator()
            return security_validator.validate_json_input(v)
        return v

    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata."""
        if v is not None:
            security_validator = SecurityValidator()
            return security_validator.validate_json_input(v)
        return v


# Response schemas
class ValidationStatusResponse(BaseModel):
    """Validation status response schema."""

    request_id: str
    status: str
    progress: Optional[str] = None
    message: Optional[str] = None
    result_available: bool = False
    user_id: str
    created_at: datetime
    updated_at: datetime


class ValidationResultResponse(BaseModel):
    """Comprehensive validation result response schema."""

    request_id: str
    overall_status: str
    fidelity_score: float
    fidelity_percentage: str
    summary: str
    discrepancy_counts: Dict[str, int]
    discrepancies: List[Dict[str, Any]]
    execution_time: Optional[float]
    timestamp: datetime
    user_id: str
    metadata: Optional[Dict[str, Any]] = None


class BehavioralValidationResultResponse(BaseModel):
    """Behavioral validation result response schema."""

    request_id: str
    status: str
    scenarios_tested: List[str]
    scenarios_passed: List[str]
    scenarios_failed: List[str]
    execution_time: float
    screenshot_urls: List[str]
    detailed_results: List[Dict[str, Any]]
    timestamp: datetime
    user_id: str


# Query parameter schemas
class ValidationListQuery(BaseModel):
    """Query parameters for validation list endpoints."""

    page: int = Field(1, ge=1, le=1000, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    status: Optional[str] = Field(None, max_length=20, description="Filter by status")
    user_id: Optional[str] = Field(None, max_length=50, description="Filter by user ID")
    start_date: Optional[datetime] = Field(None, description="Filter from date")
    end_date: Optional[datetime] = Field(None, description="Filter to date")

    @validator('status')
    def validate_status(cls, v):
        """Validate status filter."""
        if v is not None:
            security_validator = SecurityValidator()
            validated = security_validator.validate_string_input(v, "status")

            # Check against allowed statuses
            allowed_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']
            if validated not in allowed_statuses:
                raise ValueError(f'Status must be one of: {allowed_statuses}')

            return validated
        return v

    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user ID filter."""
        if v is not None:
            security_validator = SecurityValidator()
            return security_validator.validate_string_input(v, "user_id")
        return v

    @root_validator
    def validate_date_range(cls, values):
        """Validate date range."""
        start_date = values.get('start_date')
        end_date = values.get('end_date')

        if start_date and end_date:
            if start_date >= end_date:
                raise ValueError('start_date must be before end_date')

            # Limit date range to prevent excessive queries
            if (end_date - start_date).days > 365:
                raise ValueError('Date range cannot exceed 365 days')

        return values


# Health check schemas
class HealthCheckResponse(BaseModel):
    """Health check response schema."""

    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]
    uptime_seconds: float


class SystemStatsResponse(BaseModel):
    """System statistics response schema."""

    active_validations: int
    total_validations_today: int
    total_users: int
    system_load: float
    memory_usage_mb: float
    disk_usage_mb: float
    timestamp: datetime


# Error response schemas
class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response schema."""

    error: str = "validation_error"
    message: str
    field_errors: Dict[str, List[str]]
    timestamp: datetime
    request_id: Optional[str] = None


# Utility functions for schema validation
def validate_request_schema(data: Dict[str, Any], schema_class: BaseModel) -> BaseModel:
    """Validate request data against schema."""
    try:
        return schema_class(**data)
    except Exception as e:
        raise SecurityValidationError(f"Schema validation failed: {str(e)}")


def sanitize_response_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize response data to prevent information leakage."""
    # Remove sensitive fields from response
    sensitive_fields = ['password', 'secret', 'token', 'key', 'credentials']

    def recursive_sanitize(obj):
        if isinstance(obj, dict):
            return {
                key: recursive_sanitize(value)
                for key, value in obj.items()
                if not any(sensitive in key.lower() for sensitive in sensitive_fields)
            }
        elif isinstance(obj, list):
            return [recursive_sanitize(item) for item in obj]
        return obj

    return recursive_sanitize(data)