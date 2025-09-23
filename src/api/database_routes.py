"""Database-backed FastAPI routes for AI-Powered Migration Validation System.

Replaces in-memory session storage with database persistence while maintaining
API compatibility with existing clients.
"""

import json
import os
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import FastAPI
from fastapi import File
from fastapi import HTTPException
from fastapi import Query
from fastapi import UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from pydantic import Field

from ..behavioral.crews import BehavioralValidationRequest
from ..behavioral.crews import create_behavioral_validation_crew
from ..core.config import get_settings
from ..core.input_processor import InputProcessor
from ..core.migration_validator import MigrationValidator
from ..core.models import InputData
from ..core.models import InputType
from ..core.models import MigrationValidationRequest
from ..core.models import TechnologyContext
from ..core.models import TechnologyType
from ..core.models import ValidationScope
from ..core.models import ValidationSession
from ..database.integration import DatabaseIntegration
from ..database.integration import HybridSessionManager
from ..database.integration import database_lifespan
from ..database.integration import get_database_integration
from ..database.integration import get_db_service
from ..database.integration import get_hybrid_session_manager
from ..database.service import ValidationDatabaseService
from ..reporters.validation_reporter import ValidationReporter


# Pydantic models for API requests/responses
class ValidationRequest(BaseModel):
    source_technology: str
    target_technology: str
    source_technology_version: Optional[str] = None
    target_technology_version: Optional[str] = None
    validation_scope: str = "full_system"
    source_framework_details: Dict[str, Any] = Field(default_factory=dict)
    target_framework_details: Dict[str, Any] = Field(default_factory=dict)
    source_urls: List[str] = Field(default_factory=list)
    target_urls: List[str] = Field(default_factory=list)
    validation_scenarios: List[str] = Field(default_factory=list)
    behavioral_timeout: int = 300
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BehavioralValidationRequestAPI(BaseModel):
    source_url: str
    target_url: str
    validation_scenarios: List[str] = Field(default_factory=list)
    timeout: int = 300
    credentials: Optional[Dict[str, str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionStatusUpdate(BaseModel):
    status: str
    message: Optional[str] = None


class TechnologyOption(BaseModel):
    value: str
    label: str


class ValidationResponse(BaseModel):
    request_id: str
    status: str
    message: str
    session_url: Optional[str] = None


class SessionListResponse(BaseModel):
    sessions: List[Dict[str, Any]]
    total_count: int
    has_more: bool
    offset: int
    limit: int


def create_database_app() -> FastAPI:
    """Create FastAPI application with database integration."""
    app = FastAPI(
        title="AI-Powered Migration Validation System",
        description="Validates code migrations between different technologies using AI-powered analysis with database persistence",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=database_lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize components
    validator = MigrationValidator()
    # input_processor = InputProcessor()  # Unused variable removed
    reporter = ValidationReporter()

    @app.get("/")
    async def root():
        """Root endpoint with system information."""
        db_integration = get_database_integration()
        db_available = await db_integration.is_database_available()

        return {
            "message": "AI-Powered Migration Validation System",
            "version": "2.0.0",
            "database_enabled": db_integration.enabled,
            "database_available": db_available,
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health")
    async def health_check(
        db_service: ValidationDatabaseService = Depends(get_db_service),
    ):
        """System health check including database connectivity."""
        db_integration = get_database_integration()

        try:
            # Test database connection
            db_available = await db_integration.is_database_available()
            db_stats = await db_integration.get_statistics() if db_available else {}

            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database": {
                    "enabled": db_integration.enabled,
                    "available": db_available,
                    "statistics": db_stats,
                },
                "components": {
                    "validator": "operational",
                    "input_processor": "operational",
                    "reporter": "operational",
                },
            }
        except Exception as e:
            return {
                "status": "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "database": {
                    "enabled": db_integration.enabled,
                    "available": False,
                },
            }

    @app.get("/api/technologies", response_model=List[TechnologyOption])
    async def get_technology_options():
        """Get available technology options."""
        technologies = []
        for tech in TechnologyType:
            label = tech.value.replace("_", " ").replace("-", " ").title()
            technologies.append(TechnologyOption(value=tech.value, label=label))
        return technologies

    @app.get("/api/validation-scopes", response_model=List[TechnologyOption])
    async def get_validation_scope_options():
        """Get available validation scope options."""
        scopes = []
        for scope in ValidationScope:
            label = scope.value.replace("_", " ").title()
            scopes.append(TechnologyOption(value=scope.value, label=label))
        return scopes

    @app.post("/api/validate-migration", response_model=ValidationResponse)
    async def validate_migration(
        request: ValidationRequest,
        source_files: List[UploadFile] = File(default=[]),
        target_files: List[UploadFile] = File(default=[]),
        source_screenshots: List[UploadFile] = File(default=[]),
        target_screenshots: List[UploadFile] = File(default=[]),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        hybrid_manager: HybridSessionManager = Depends(get_hybrid_session_manager),
    ):
        """Start migration validation with database persistence."""
        try:
            # Convert string enums
            source_tech = TechnologyType(request.source_technology)
            target_tech = TechnologyType(request.target_technology)
            scope = ValidationScope(request.validation_scope)

            # Process uploaded files
            settings = get_settings()
            upload_dir = settings.upload_dir
            os.makedirs(upload_dir, exist_ok=True)

            source_file_paths = []
            target_file_paths = []
            source_screenshot_paths = []
            target_screenshot_paths = []

            # Save source files
            for file in source_files:
                if file.filename:
                    file_path = os.path.join(upload_dir, f"source_{file.filename}")
                    with open(file_path, "wb") as f:
                        content = await file.read()
                        f.write(content)
                    source_file_paths.append(file_path)

            # Save target files
            for file in target_files:
                if file.filename:
                    file_path = os.path.join(upload_dir, f"target_{file.filename}")
                    with open(file_path, "wb") as f:
                        content = await file.read()
                        f.write(content)
                    target_file_paths.append(file_path)

            # Save source screenshots
            for file in source_screenshots:
                if file.filename:
                    file_path = os.path.join(
                        upload_dir, f"source_screenshot_{file.filename}"
                    )
                    with open(file_path, "wb") as f:
                        content = await file.read()
                        f.write(content)
                    source_screenshot_paths.append(file_path)

            # Save target screenshots
            for file in target_screenshots:
                if file.filename:
                    file_path = os.path.join(
                        upload_dir, f"target_screenshot_{file.filename}"
                    )
                    with open(file_path, "wb") as f:
                        content = await file.read()
                        f.write(content)
                    target_screenshot_paths.append(file_path)

            # Determine input types
            source_input_type = (
                InputType.HYBRID
                if source_file_paths and source_screenshot_paths
                else (
                    InputType.CODE_FILES if source_file_paths else InputType.SCREENSHOTS
                )
            )
            target_input_type = (
                InputType.HYBRID
                if target_file_paths and target_screenshot_paths
                else (
                    InputType.CODE_FILES if target_file_paths else InputType.SCREENSHOTS
                )
            )

            # Create validation request
            validation_request = MigrationValidationRequest(
                source_technology=TechnologyContext(
                    type=source_tech,
                    version=request.source_technology_version,
                    framework_details=request.source_framework_details,
                ),
                target_technology=TechnologyContext(
                    type=target_tech,
                    version=request.target_technology_version,
                    framework_details=request.target_framework_details,
                ),
                validation_scope=scope,
                source_input=InputData(
                    type=source_input_type,
                    files=source_file_paths,
                    screenshots=source_screenshot_paths,
                    urls=request.source_urls,
                    metadata=request.metadata,
                ),
                target_input=InputData(
                    type=target_input_type,
                    files=target_file_paths,
                    screenshots=target_screenshot_paths,
                    urls=request.target_urls,
                    validation_scenarios=request.validation_scenarios,
                    metadata=request.metadata,
                ),
            )

            # Start validation in background
            async def run_validation():
                try:
                    # Update status to processing
                    await hybrid_manager.update_session_status(
                        validation_request.request_id,
                        "processing",
                    )
                    await hybrid_manager.add_session_log(
                        validation_request.request_id,
                        "Starting migration validation",
                    )

                    # Run validation
                    session = await validator.validate_migration(validation_request)

                    # Store session with results
                    await hybrid_manager.store_session(
                        validation_request.request_id, session
                    )

                    # Update status to completed
                    await hybrid_manager.update_session_status(
                        validation_request.request_id,
                        "completed",
                    )
                    await hybrid_manager.add_session_log(
                        validation_request.request_id,
                        "Migration validation completed",
                    )

                except Exception as e:
                    # Update status to error
                    await hybrid_manager.update_session_status(
                        validation_request.request_id,
                        "error",
                    )
                    await hybrid_manager.add_session_log(
                        validation_request.request_id,
                        f"Validation failed: {e!s}",
                    )

            # Create initial session
            initial_session = ValidationSession(request=validation_request)
            await hybrid_manager.store_session(
                validation_request.request_id, initial_session
            )

            # Start background task
            background_tasks.add_task(run_validation)

            return ValidationResponse(
                request_id=validation_request.request_id,
                status="accepted",
                message="Migration validation started",
                session_url=f"/api/sessions/{validation_request.request_id}",
            )

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/validate-behavioral", response_model=ValidationResponse)
    async def validate_behavioral(
        request: BehavioralValidationRequestAPI,
        background_tasks: BackgroundTasks = BackgroundTasks(),
        hybrid_manager: HybridSessionManager = Depends(get_hybrid_session_manager),
    ):
        """Start behavioral validation with database persistence."""
        try:
            # Create behavioral validation request
            behavioral_request = BehavioralValidationRequest(
                source_url=request.source_url,
                target_url=request.target_url,
                validation_scenarios=request.validation_scenarios
                or [
                    "User login flow",
                    "Form submission and validation",
                    "Error handling scenarios",
                ],
                timeout=request.timeout,
                credentials=request.credentials,
                metadata=request.metadata,
            )

            # Generate request ID for behavioral validation
            request_id = f"behavioral_{datetime.now().isoformat()}"

            # Start validation in background
            async def run_behavioral_validation():
                try:
                    # Update status to processing
                    await hybrid_manager.update_session_status(request_id, "processing")
                    await hybrid_manager.add_session_log(
                        request_id, "Starting behavioral validation"
                    )

                    # Run behavioral validation
                    crew = create_behavioral_validation_crew()
                    result = await crew.validate_migration(behavioral_request)

                    # Create a validation session with the result
                    # For behavioral validation, we create a simplified request
                    migration_request = MigrationValidationRequest(
                        source_technology=TechnologyContext(
                            type=TechnologyType.JAVASCRIPT_REACT
                        ),
                        target_technology=TechnologyContext(
                            type=TechnologyType.JAVASCRIPT_REACT
                        ),
                        validation_scope=ValidationScope.BEHAVIORAL_VALIDATION,
                        source_input=InputData(
                            type=InputType.SCREENSHOTS,
                            urls=[request.source_url],
                            validation_scenarios=request.validation_scenarios,
                        ),
                        target_input=InputData(
                            type=InputType.SCREENSHOTS,
                            urls=[request.target_url],
                            validation_scenarios=request.validation_scenarios,
                        ),
                        request_id=request_id,
                    )

                    session = ValidationSession(request=migration_request)
                    session.result = result

                    # Store session with results
                    await hybrid_manager.store_session(request_id, session)

                    # Update status to completed
                    await hybrid_manager.update_session_status(request_id, "completed")
                    await hybrid_manager.add_session_log(
                        request_id, "Behavioral validation completed"
                    )

                except Exception as e:
                    # Update status to error
                    await hybrid_manager.update_session_status(request_id, "error")
                    await hybrid_manager.add_session_log(
                        request_id, f"Behavioral validation failed: {e!s}"
                    )

            # Start background task
            background_tasks.add_task(run_behavioral_validation)

            return ValidationResponse(
                request_id=request_id,
                status="accepted",
                message="Behavioral validation started",
                session_url=f"/api/sessions/{request_id}",
            )

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/sessions", response_model=SessionListResponse)
    async def list_sessions(
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        status: Optional[str] = Query(None),
        source_technology: Optional[str] = Query(None),
        target_technology: Optional[str] = Query(None),
        hybrid_manager: HybridSessionManager = Depends(get_hybrid_session_manager),
    ):
        """List validation sessions with database persistence."""
        try:
            sessions = await hybrid_manager.list_sessions(
                include_memory=True,
                include_database=True,
            )

            # Apply filters
            if status:
                sessions = [s for s in sessions if s.get("status") == status]
            if source_technology:
                sessions = [
                    s
                    for s in sessions
                    if s.get("source_technology") == source_technology
                ]
            if target_technology:
                sessions = [
                    s
                    for s in sessions
                    if s.get("target_technology") == target_technology
                ]

            total_count = len(sessions)

            # Apply pagination
            paginated_sessions = sessions[offset : offset + limit]

            return SessionListResponse(
                sessions=paginated_sessions,
                total_count=total_count,
                has_more=offset + limit < total_count,
                offset=offset,
                limit=limit,
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/sessions/{request_id}")
    async def get_session(
        request_id: str,
        hybrid_manager: HybridSessionManager = Depends(get_hybrid_session_manager),
    ):
        """Get validation session details."""
        session = await hybrid_manager.get_session(request_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Convert to API response format
        response = {
            "request_id": request_id,
            "status": "completed" if session.result else "processing",
            "source_technology": session.request.source_technology.type.value,
            "target_technology": session.request.target_technology.type.value,
            "validation_scope": session.request.validation_scope.value,
            "created_at": session.request.created_at.isoformat(),
            "processing_log": session.processing_log,
        }

        if session.result:
            response.update(
                {
                    "result": {
                        "overall_status": session.result.overall_status,
                        "fidelity_score": session.result.fidelity_score,
                        "summary": session.result.summary,
                        "execution_time": session.result.execution_time,
                        "timestamp": session.result.timestamp.isoformat(),
                        "discrepancies": [
                            {
                                "type": d.type,
                                "severity": d.severity.value,
                                "description": d.description,
                                "source_element": d.source_element,
                                "target_element": d.target_element,
                                "recommendation": d.recommendation,
                                "confidence": d.confidence,
                            }
                            for d in session.result.discrepancies
                        ],
                    },
                }
            )

        return response

    @app.put("/api/sessions/{request_id}/status")
    async def update_session_status(
        request_id: str,
        status_update: SessionStatusUpdate,
        hybrid_manager: HybridSessionManager = Depends(get_hybrid_session_manager),
    ):
        """Update session status."""
        await hybrid_manager.update_session_status(request_id, status_update.status)

        if status_update.message:
            await hybrid_manager.add_session_log(request_id, status_update.message)

        return {"message": "Status updated successfully"}

    @app.delete("/api/sessions/{request_id}")
    async def delete_session(
        request_id: str,
        hybrid_manager: HybridSessionManager = Depends(get_hybrid_session_manager),
    ):
        """Delete validation session."""
        deleted = await hybrid_manager.delete_session(request_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"message": "Session deleted successfully"}

    @app.get("/api/sessions/{request_id}/report")
    async def get_session_report(
        request_id: str,
        format: str = Query("json", regex="^(json|html|pdf)$"),
        hybrid_manager: HybridSessionManager = Depends(get_hybrid_session_manager),
    ):
        """Generate and download session report."""
        session = await hybrid_manager.get_session(request_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if not session.result:
            raise HTTPException(status_code=400, detail="Session not completed")

        try:
            report_content = await reporter.generate_report(session, format)

            if format == "json":
                return JSONResponse(content=json.loads(report_content))
            if format == "html":
                return PlainTextResponse(content=report_content, media_type="text/html")
            if format == "pdf":
                # For PDF, we'd need to implement PDF generation
                # For now, return HTML
                return PlainTextResponse(content=report_content, media_type="text/html")

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Report generation failed: {e!s}"
            )

    @app.get("/api/statistics")
    async def get_statistics(
        db_integration: DatabaseIntegration = Depends(get_database_integration),
    ):
        """Get system statistics."""
        try:
            stats = await db_integration.get_statistics()
            stats["timestamp"] = datetime.utcnow().isoformat()
            return stats
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/admin/cleanup")
    async def cleanup_old_sessions(
        days_old: int = Query(30, ge=1, le=365),
        db_service: ValidationDatabaseService = Depends(get_db_service),
    ):
        """Admin endpoint to cleanup old sessions."""
        try:
            deleted_count = await db_service.cleanup_old_sessions(days_old)
            return {
                "message": f"Cleaned up {deleted_count} old sessions",
                "deleted_count": deleted_count,
                "days_old": days_old,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/admin/migrate-memory-sessions")
    async def migrate_memory_sessions(
        hybrid_manager: HybridSessionManager = Depends(get_hybrid_session_manager),
    ):
        """Admin endpoint to migrate in-memory sessions to database."""
        try:
            # This would need access to the old memory sessions
            # For now, we'll just clear the memory cache
            hybrid_manager.clear_memory_cache()
            return {
                "message": "Memory cache cleared successfully",
                "note": "To migrate specific sessions, use the appropriate endpoints",
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


# Create the application instance
app = create_database_app()
