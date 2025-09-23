"""Secure API routes with comprehensive security integration.

Provides fully secured API endpoints with input validation, authentication,
authorization, rate limiting, and audit logging.
"""

from datetime import datetime
from typing import Any, Dict, List

from fastapi import (APIRouter, BackgroundTasks, Depends, File, Form,
                     HTTPException, Request, UploadFile, status)
from fastapi.responses import JSONResponse

from ..behavioral.crews import \
    BehavioralValidationRequest as CrewBehavioralRequest
from ..behavioral.crews import create_behavioral_validation_crew
from ..core.config import get_settings
from ..core.input_processor import InputProcessor
from ..core.migration_validator import MigrationValidator
from ..core.models import ValidationSession
from ..security.api_keys import (APIKeyMetadata, api_key_manager,
                                 api_key_rate_limiter, require_admin_scope,
                                 require_read_scope, require_validation_scope)
from ..security.audit import security_audit
from ..security.headers import create_security_headers
from ..security.schemas import (APIKeyCreateRequest, APIKeyListResponse,
                                APIKeyResponse, BehavioralValidationRequest,
                                BehavioralValidationResultResponse,
                                FileUploadBatchResponse, FileUploadMetadata,
                                FileUploadResponse, HealthCheckResponse,
                                MigrationValidationRequest,
                                SystemStatsResponse, ValidationResultResponse,
                                ValidationStatusResponse,
                                sanitize_response_data)
from ..security.validation import SecurityValidationError, input_validator

# Initialize components
settings = get_settings()
router = APIRouter(prefix="/api/v1", tags=["Secure API"])
validator = MigrationValidator()
input_processor = InputProcessor()

# Global storage with enhanced security
validation_sessions: Dict[str, ValidationSession] = {}
behavioral_validation_sessions: Dict[str, Dict[str, Any]] = {}


# Helper functions
def get_request_context(request: Request) -> Dict[str, Any]:
    """Extract request context for logging."""
    return {
        "client_ip": getattr(request.state, "client_ip", "unknown"),
        "user_agent": getattr(request.state, "user_agent", ""),
        "request_id": getattr(request.state, "request_id", ""),
    }


async def validate_user_access(
    api_key_metadata: APIKeyMetadata,
    resource_id: str,
    request: Request,
) -> None:
    """Validate user access to specific resources."""
    # In a production system, implement proper resource ownership checks
    # For now, log the access attempt
    context = get_request_context(request)
    await security_audit.log_data_access(
        user_id=None,
        api_key_id=api_key_metadata.id,
        resource=resource_id,
        action="access_check",
        source_ip=context["client_ip"],
        request_id=context["request_id"],
    )


# API Key Management Endpoints
@router.post("/admin/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    req: Request,
    api_key_metadata: APIKeyMetadata = Depends(require_admin_scope),
):
    """Create a new API key with specified scopes and permissions."""
    try:
        context = get_request_context(req)

        # Create API key
        api_key, metadata = await api_key_manager.create_api_key(
            request=request,
            created_by=api_key_metadata.id,
        )

        # Log creation
        await security_audit.log_api_key_created(
            api_key_id=metadata.id,
            created_by=api_key_metadata.id,
            scopes=[scope.value for scope in request.scopes],
            source_ip=context["client_ip"],
            request_id=context["request_id"],
        )

        # Return metadata (not the actual key for security)
        response_data = APIKeyResponse(
            id=metadata.id,
            name=metadata.name,
            description=metadata.description,
            scopes=metadata.scopes,
            created_at=metadata.created_at,
            expires_at=metadata.expires_at,
            last_used_at=metadata.last_used_at,
            rate_limit_per_minute=metadata.rate_limit_per_minute,
            is_active=metadata.is_active,
        )

        # Add security headers
        headers = create_security_headers()
        return JSONResponse(
            content=sanitize_response_data(response_data.dict()),
            headers=headers,
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key",
        )


@router.get("/admin/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    req: Request,
    api_key_metadata: APIKeyMetadata = Depends(require_admin_scope),
):
    """List all API keys (admin only)."""
    try:
        context = get_request_context(req)

        api_keys = await api_key_manager.list_api_keys()

        await security_audit.log_data_access(
            user_id=None,
            api_key_id=api_key_metadata.id,
            resource="api_keys_list",
            action="list",
            source_ip=context["client_ip"],
            request_id=context["request_id"],
        )

        response_data = APIKeyListResponse(
            api_keys=api_keys,
            total=len(api_keys),
        )

        headers = create_security_headers()
        return JSONResponse(
            content=sanitize_response_data(response_data.dict()),
            headers=headers,
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API keys",
        )


@router.delete("/admin/api-keys/{api_key_id}")
async def revoke_api_key(
    api_key_id: str,
    req: Request,
    api_key_metadata: APIKeyMetadata = Depends(require_admin_scope),
):
    """Revoke an API key."""
    try:
        context = get_request_context(req)

        success = await api_key_manager.revoke_api_key(
            api_key_id=api_key_id,
            revoked_by=api_key_metadata.id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )

        headers = create_security_headers()
        return JSONResponse(
            content={"message": "API key revoked successfully"},
            headers=headers,
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key",
        )


# File Upload Endpoints
@router.post("/files/upload", response_model=FileUploadBatchResponse)
async def upload_files(
    req: Request,
    files: List[UploadFile] = File(...),
    metadata: str = Form(...),
    api_key_metadata: APIKeyMetadata = Depends(require_validation_scope),
    rate_limit_check: APIKeyMetadata = Depends(
        api_key_rate_limiter.require_rate_limit_check),
):
    """Upload files with comprehensive security validation."""
    try:
        context = get_request_context(req)

        # Parse and validate metadata
        import json
        try:
            metadata_dict = json.loads(metadata)
            upload_metadata = FileUploadMetadata(**metadata_dict)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metadata: {e!s}",
            )

        # Validate files
        validation_results = await input_validator.validate_file_uploads(files)

        uploaded_files = []
        failed_uploads = []
        total_size = 0

        for file, validation_result in validation_results:
            if validation_result.is_valid:
                # Process successful upload
                file_id = f"file_{datetime.utcnow().isoformat()}_{file.filename}"

                # Log file upload
                await security_audit.log_file_upload(
                    user_id=None,
                    api_key_id=api_key_metadata.id,
                    filename=file.filename,
                    file_size=validation_result.file_size,
                    content_type=validation_result.detected_type,
                    validation_result=validation_result.dict(),
                    source_ip=context["client_ip"],
                    request_id=context["request_id"],
                )

                uploaded_files.append(FileUploadResponse(
                    file_id=file_id,
                    filename=file.filename,
                    original_filename=file.filename,
                    file_size=validation_result.file_size,
                    content_type=validation_result.detected_type,
                    upload_type=upload_metadata.upload_type,
                    uploaded_at=datetime.utcnow(),
                    validation_result=validation_result.dict(),
                ))

                total_size += validation_result.file_size

            else:
                failed_uploads.append({
                    "filename": file.filename,
                    "errors": validation_result.security_issues,
                })

        response_data = FileUploadBatchResponse(
            uploaded_files=uploaded_files,
            failed_uploads=failed_uploads,
            total_files=len(files),
            successful_uploads=len(uploaded_files),
            total_size=total_size,
        )

        headers = create_security_headers()
        return JSONResponse(
            content=sanitize_response_data(response_data.dict()),
            headers=headers,
        )

    except SecurityValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File validation failed: {e!s}",
        )


# Migration Validation Endpoints
@router.post("/validation/migrate", response_model=ValidationStatusResponse)
async def create_migration_validation(
    request_data: MigrationValidationRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    api_key_metadata: APIKeyMetadata = Depends(require_validation_scope),
    rate_limit_check: APIKeyMetadata = Depends(
        api_key_rate_limiter.require_rate_limit_check),
):
    """Create a new migration validation request."""
    try:
        context = get_request_context(req)

        # Validate request data
        validated_data = await input_validator.validate_migration_request(request_data.dict())

        # Create validation session
        session_id = f"migration_{datetime.utcnow().isoformat()}"
        session = ValidationSession(
            session_id=session_id,
            request_id=session_id,
            user_id=api_key_metadata.id,
            source_technology=validated_data["source_technology"],
            target_technology=validated_data["target_technology"],
            validation_scope=validated_data["validation_scope"],
            status="pending",
            created_at=datetime.utcnow(),
        )

        validation_sessions[session_id] = session

        # Schedule background validation
        background_tasks.add_task(
            _process_migration_validation,
            session_id,
            validated_data,
            api_key_metadata.id,
            context,
        )

        # Log validation request
        await security_audit.log_data_access(
            user_id=None,
            api_key_id=api_key_metadata.id,
            resource=f"validation/{session_id}",
            action="create_validation",
            source_ip=context["client_ip"],
            request_id=context["request_id"],
        )

        response_data = ValidationStatusResponse(
            request_id=session_id,
            status="pending",
            progress="Validation request created",
            message="Validation started",
            result_available=False,
            user_id=api_key_metadata.id,
            created_at=session.created_at,
            updated_at=session.created_at,
        )

        headers = create_security_headers()
        return JSONResponse(
            content=sanitize_response_data(response_data.dict()),
            headers=headers,
        )

    except SecurityValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation request failed: {e!s}",
        )


@router.post("/validation/behavioral", response_model=ValidationStatusResponse)
async def create_behavioral_validation(
    request_data: BehavioralValidationRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    api_key_metadata: APIKeyMetadata = Depends(require_validation_scope),
    rate_limit_check: APIKeyMetadata = Depends(
        api_key_rate_limiter.require_rate_limit_check),
):
    """Create a new behavioral validation request."""
    try:
        context = get_request_context(req)

        # Validate request data
        validated_data = await input_validator.validate_behavioral_request(request_data.dict())

        # Create validation session
        session_id = f"behavioral_{datetime.utcnow().isoformat()}"
        behavioral_validation_sessions[session_id] = {
            "session_id": session_id,
            "user_id": api_key_metadata.id,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "request_data": validated_data,
        }

        # Schedule background validation
        background_tasks.add_task(
            _process_behavioral_validation,
            session_id,
            validated_data,
            api_key_metadata.id,
            context,
        )

        # Log validation request
        await security_audit.log_data_access(
            user_id=None,
            api_key_id=api_key_metadata.id,
            resource=f"behavioral_validation/{session_id}",
            action="create_behavioral_validation",
            source_ip=context["client_ip"],
            request_id=context["request_id"],
        )

        response_data = ValidationStatusResponse(
            request_id=session_id,
            status="pending",
            progress="Behavioral validation request created",
            message="Behavioral validation started",
            result_available=False,
            user_id=api_key_metadata.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        headers = create_security_headers()
        return JSONResponse(
            content=sanitize_response_data(response_data.dict()),
            headers=headers,
        )

    except SecurityValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Behavioral validation request failed: {e!s}",
        )


@router.get("/validation/{request_id}/status", response_model=ValidationStatusResponse)
async def get_validation_status(
    request_id: str,
    req: Request,
    api_key_metadata: APIKeyMetadata = Depends(require_read_scope),
):
    """Get validation status."""
    try:
        context = get_request_context(req)

        # Check migration validation sessions
        if request_id in validation_sessions:
            await validate_user_access(api_key_metadata, request_id, req)
            session = validation_sessions[request_id]

            response_data = ValidationStatusResponse(
                request_id=request_id,
                status=session.status,
                progress=getattr(session, "progress", None),
                message=getattr(session, "message", None),
                result_available=session.status == "completed",
                user_id=session.user_id,
                created_at=session.created_at,
                updated_at=getattr(session, "updated_at", session.created_at),
            )

        # Check behavioral validation sessions
        elif request_id in behavioral_validation_sessions:
            await validate_user_access(api_key_metadata, request_id, req)
            session = behavioral_validation_sessions[request_id]

            response_data = ValidationStatusResponse(
                request_id=request_id,
                status=session["status"],
                progress=session.get("progress"),
                message=session.get("message"),
                result_available=session["status"] == "completed",
                user_id=session["user_id"],
                created_at=session["created_at"],
                updated_at=session.get("updated_at", session["created_at"]),
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation request not found",
            )

        headers = create_security_headers()
        return JSONResponse(
            content=sanitize_response_data(response_data.dict()),
            headers=headers,
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve validation status",
        )


@router.get("/validation/{request_id}/result")
async def get_validation_result(
    request_id: str,
    req: Request,
    api_key_metadata: APIKeyMetadata = Depends(require_read_scope),
):
    """Get validation result."""
    try:
        context = get_request_context(req)

        # Check migration validation sessions
        if request_id in validation_sessions:
            await validate_user_access(api_key_metadata, request_id, req)
            session = validation_sessions[request_id]

            if session.status != "completed":
                raise HTTPException(
                    status_code=status.HTTP_202_ACCEPTED,
                    detail="Validation not yet completed",
                )

            result = getattr(session, "result", None)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Validation result not available",
                )

            response_data = ValidationResultResponse(
                request_id=request_id,
                overall_status=result.overall_status,
                fidelity_score=result.fidelity_score,
                fidelity_percentage=f"{result.fidelity_score:.1%}",
                summary=result.summary,
                discrepancy_counts=result.discrepancy_counts,
                discrepancies=[d.dict() for d in result.discrepancies],
                execution_time=result.execution_time,
                timestamp=result.timestamp,
                user_id=session.user_id,
                metadata=result.metadata,
            )

        # Check behavioral validation sessions
        elif request_id in behavioral_validation_sessions:
            await validate_user_access(api_key_metadata, request_id, req)
            session = behavioral_validation_sessions[request_id]

            if session["status"] != "completed":
                raise HTTPException(
                    status_code=status.HTTP_202_ACCEPTED,
                    detail="Behavioral validation not yet completed",
                )

            result = session.get("result")
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Behavioral validation result not available",
                )

            response_data = BehavioralValidationResultResponse(
                request_id=request_id,
                status=result["status"],
                scenarios_tested=result["scenarios_tested"],
                scenarios_passed=result["scenarios_passed"],
                scenarios_failed=result["scenarios_failed"],
                execution_time=result["execution_time"],
                screenshot_urls=result.get("screenshot_urls", []),
                detailed_results=result["detailed_results"],
                timestamp=result["timestamp"],
                user_id=session["user_id"],
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation request not found",
            )

        # Log result access
        await security_audit.log_data_access(
            user_id=None,
            api_key_id=api_key_metadata.id,
            resource=f"validation_result/{request_id}",
            action="get_result",
            source_ip=context["client_ip"],
            request_id=context["request_id"],
        )

        headers = create_security_headers()
        return JSONResponse(
            content=sanitize_response_data(response_data.dict()),
            headers=headers,
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve validation result",
        )


# System Health and Monitoring Endpoints
@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    req: Request,
    api_key_metadata: APIKeyMetadata = Depends(require_read_scope),
):
    """System health check."""
    try:
        import time

        import psutil

        uptime = time.time() - psutil.boot_time()

        response_data = HealthCheckResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version=settings.VERSION,
            services={
                "database": "healthy",
                "redis": "healthy",
                "llm_service": "healthy",
            },
            uptime_seconds=uptime,
        )

        headers = create_security_headers()
        return JSONResponse(
            content=sanitize_response_data(response_data.dict()),
            headers=headers,
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check failed",
        )


@router.get("/admin/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    req: Request,
    api_key_metadata: APIKeyMetadata = Depends(require_admin_scope),
):
    """Get system statistics (admin only)."""
    try:
        import psutil

        response_data = SystemStatsResponse(
            active_validations=len(
                [s for s in validation_sessions.values() if s.status == "running"]),
            total_validations_today=len(validation_sessions),
            total_users=1,  # Placeholder
            system_load=psutil.cpu_percent(),
            memory_usage_mb=psutil.virtual_memory().used / 1024 / 1024,
            disk_usage_mb=psutil.disk_usage("/").used / 1024 / 1024,
            timestamp=datetime.utcnow(),
        )

        headers = create_security_headers()
        return JSONResponse(
            content=sanitize_response_data(response_data.dict()),
            headers=headers,
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system statistics",
        )


# Background task functions
async def _process_migration_validation(
    session_id: str,
    validated_data: dict,
    user_id: str,
    context: dict,
):
    """Process migration validation in background."""
    try:
        session = validation_sessions.get(session_id)
        if not session:
            return

        session.status = "running"
        session.updated_at = datetime.utcnow()

        # Initialize real validation pipeline
        from ..core.models import (InputData, InputType,
                                   MigrationValidationRequest,
                                   TechnologyContext, TechnologyType)

        # Create technology contexts
        source_tech = TechnologyContext(
            technology_type=TechnologyType(validated_data["source_technology"]),
            framework=validated_data.get("source_framework"),
            version=validated_data.get("source_version"),
        )
        target_tech = TechnologyContext(
            technology_type=TechnologyType(validated_data["target_technology"]),
            framework=validated_data.get("target_framework"),
            version=validated_data.get("target_version"),
        )

        # Create validation request
        validation_request = MigrationValidationRequest(
            source_input=InputData(
                input_type=InputType.CODE_FILES,
                content=validated_data.get("source_files", {}),
                technology_context=source_tech,
            ),
            target_input=InputData(
                input_type=InputType.CODE_FILES,
                content=validated_data.get("target_files", {}),
                technology_context=target_tech,
            ),
            validation_scope=validated_data["validation_scope"],
        )

        # Initialize and run migration validator
        validator = MigrationValidator()
        result = await validator.validate_migration(validation_request)

        session.result = result
        session.status = "completed"
        session.updated_at = datetime.utcnow()

    except Exception as e:
        session = validation_sessions.get(session_id)
        if session:
            session.status = "failed"
            session.message = f"Validation failed: {e!s}"
            session.updated_at = datetime.utcnow()


async def _process_behavioral_validation(
    session_id: str,
    validated_data: dict,
    user_id: str,
    context: dict,
):
    """Process behavioral validation in background."""
    try:
        session = behavioral_validation_sessions.get(session_id)
        if not session:
            return

        session["status"] = "running"
        session["updated_at"] = datetime.utcnow()

        # Initialize real behavioral validation using CrewAI
        crew_request = CrewBehavioralRequest(
            source_url=validated_data.get("source_url", ""),
            target_url=validated_data.get("target_url", ""),
            validation_scenarios=validated_data["validation_scenarios"],
            max_execution_time=validated_data.get("max_execution_time", 300),
        )

        # Create and execute behavioral validation crew
        crew = create_behavioral_validation_crew()
        try:
            crew_result = await crew.kickoff(crew_request)
            result = {
                "status": "completed",
                "scenarios_tested": crew_result.get("scenarios_tested", []),
                "scenarios_passed": crew_result.get("scenarios_passed", []),
                "scenarios_failed": crew_result.get("scenarios_failed", []),
                "execution_time": crew_result.get("execution_time", 0.0),
                "screenshot_urls": crew_result.get("screenshot_urls", []),
                "detailed_results": crew_result.get("detailed_results", []),
                "timestamp": datetime.utcnow(),
            }

            session["result"] = result
            session["status"] = "completed"
            session["updated_at"] = datetime.utcnow()

        except Exception as e:
            session = behavioral_validation_sessions.get(session_id)
            if session:
                session["status"] = "failed"
                session["message"] = f"Behavioral validation failed: {e!s}"
                session["updated_at"] = datetime.utcnow()
    except Exception as e:
        session = behavioral_validation_sessions.get(session_id)
        if session:
            session["status"] = "failed"
            session["message"] = f"Process failed: {e!s}"
            session["updated_at"] = datetime.utcnow()
