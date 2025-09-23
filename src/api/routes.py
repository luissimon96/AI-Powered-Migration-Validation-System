"""FastAPI routes for AI-Powered Migration Validation System.

Provides REST API endpoints for migration validation functionality:
- Technology options and validation
- File upload handling
- Migration validation execution
- Report generation and retrieval
"""

from src.api.async_routes import router as async_router
import json
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel


class UserRole(str, Enum):
    ADMIN = "admin"
    VALIDATOR = "validator"
    VIEWER = "viewer"


# Pydantic models for API requests/responses
class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TechnologyOption(BaseModel):
    value: str
    label: str


# Global storage for validation sessions (in production, use Redis or database)
validation_sessions: Dict[str, ValidationSession] = {}
behavioral_validation_sessions: Dict[str, Dict[str, Any]] = {}


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="AI-Powered Migration Validation System",
        description="Validates code migrations between different technologies using AI-powered analysis",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
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
    input_processor = InputProcessor()

    # Hardcoded user for demonstration (replace with database lookup in production)
    HARDCODED_USER = {
        "username": "admin",
        "password": "password",  # In production, store hashed passwords
        "role": UserRole.ADMIN,
    }

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    async def get_current_user(token: str = Depends(oauth2_scheme)):
        payload = decode_access_token(token)
        if payload is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        username = payload.get("sub")
        user_role = payload.get("role")
        if username is None or user_role is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return {"username": username, "role": user_role}

    def has_role(required_role: UserRole):
        def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
            if current_user["role"] != required_role:
                raise HTTPException(status_code=403, detail="Operation not permitted")
            return current_user

        return role_checker

    @app.post("/token", response_model=Token, tags=["Authentication"])
    async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
        user = HARDCODED_USER  # In production, fetch user from DB
        if not user or not verify_password(form_data.password, user["password"]):
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = create_access_token(
            data={"sub": user["username"], "role": user["role"]})
        return {"access_token": access_token, "token_type": "bearer"}

    @app.get("/users/me", tags=["Authentication"])
    async def read_users_me(current_user: Dict[str, Any] = Depends(get_current_user)):
        return current_user

    @app.get("/", tags=["Health"])
    async def root():
        """Health check endpoint."""
        return {
            "message": "AI-Powered Migration Validation System",
            "status": "running",
            "version": "1.0.0",
        }

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Detailed health check."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {"validator": "operational", "input_processor": "operational"},
        }

    @app.get(
        "/api/technologies",
        response_model=TechnologyOptionsResponse,
        tags=["Configuration"],
    )
    async def get_technology_options():
        """Get available technology options for validation."""
        try:
            options = input_processor.get_technology_options()
            return TechnologyOptionsResponse(**options)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get technology options: {e!s}",
            )

    @app.post(
        "/api/compatibility/check",
        response_model=CompatibilityCheckResponse,
        tags=["Configuration"],
    )
    async def check_compatibility(request: CompatibilityCheckRequest):
        """Check compatibility between source and target technologies."""
        try:
            result = input_processor.validate_technology_compatibility(
                request.source_technology,
                request.target_technology,
                request.validation_scope,
            )
            return CompatibilityCheckResponse(**result)
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Compatibility check failed: {e!s}")

    @app.get(
        "/api/capabilities",
        tags=["Configuration"],
        dependencies=[Depends(has_role(UserRole.ADMIN))],
    )
    async def get_system_capabilities():
        """Get system capabilities and supported features."""
        try:
            capabilities = validator.get_supported_technologies()
            return capabilities
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Failed to get capabilities: {e!s}")

    @app.post("/api/upload/source", tags=["File Management"])
    async def upload_source_files(files: List[UploadFile] = File(...)):
        """Upload source system files for validation."""
        try:
            uploaded_files = []
            for file in files:
                if not file.filename:
                    continue

                contents = await file.read()
                uploaded_files.append((file.filename, contents))

            if not uploaded_files:
                raise HTTPException(status_code=400, detail="No valid files uploaded")

            saved_paths = input_processor.upload_files(uploaded_files, "source")

            return {
                "message": f"Successfully uploaded {len(saved_paths)} source files",
                "files": [
                    {"filename": os.path.basename(path), "path": path} for path in saved_paths
                ],
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {e!s}")

    @app.post("/api/upload/target", tags=["File Management"])
    async def upload_target_files(files: List[UploadFile] = File(...)):
        """Upload target system files for validation."""
        try:
            uploaded_files = []
            for file in files:
                if not file.filename:
                    continue

                contents = await file.read()
                uploaded_files.append((file.filename, contents))

            if not uploaded_files:
                raise HTTPException(status_code=400, detail="No valid files uploaded")

            saved_paths = input_processor.upload_files(uploaded_files, "target")

            return {
                "message": f"Successfully uploaded {len(saved_paths)} target files",
                "files": [
                    {"filename": os.path.basename(path), "path": path} for path in saved_paths
                ],
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {e!s}")

    @app.post("/api/validate", tags=["Validation"])
    async def validate_migration(
        background_tasks: BackgroundTasks,
        request_data: str = Form(...),
        source_files: List[UploadFile] = File(default=[]),
        source_screenshots: List[UploadFile] = File(default=[]),
        target_files: List[UploadFile] = File(default=[]),
        target_screenshots: List[UploadFile] = File(default=[]),
    ):
        """Execute migration validation with uploaded files.

        This endpoint handles file uploads and starts validation process in background.
        """
        try:
            # Parse request data
            import json

            validation_req = ValidationRequest(**json.loads(request_data))

            # Process uploaded files
            source_file_paths = []
            source_screenshot_paths = []
            target_file_paths = []
            target_screenshot_paths = []

            # Handle source files
            if source_files:
                source_uploaded = []
                for file in source_files:
                    if file.filename:
                        contents = await file.read()
                        source_uploaded.append((file.filename, contents))

                if source_uploaded:
                    source_file_paths = input_processor.upload_files(
                        source_uploaded, "source_validation",
                    )

            # Handle source screenshots
            if source_screenshots:
                source_screenshot_uploaded = []
                for file in source_screenshots:
                    if file.filename:
                        contents = await file.read()
                        source_screenshot_uploaded.append((file.filename, contents))

                if source_screenshot_uploaded:
                    source_screenshot_paths = input_processor.upload_files(
                        source_screenshot_uploaded, "source_screenshots",
                    )

            # Handle target files
            if target_files:
                target_uploaded = []
                for file in target_files:
                    if file.filename:
                        contents = await file.read()
                        target_uploaded.append((file.filename, contents))

                if target_uploaded:
                    target_file_paths = input_processor.upload_files(
                        target_uploaded, "target_validation",
                    )

            # Handle target screenshots
            if target_screenshots:
                target_screenshot_uploaded = []
                for file in target_screenshots:
                    if file.filename:
                        contents = await file.read()
                        target_screenshot_uploaded.append((file.filename, contents))

                if target_screenshot_uploaded:
                    target_screenshot_paths = input_processor.upload_files(
                        target_screenshot_uploaded, "target_screenshots",
                    )

            # Create validation request
            migration_request = input_processor.create_validation_request(
                source_technology=validation_req.source_technology,
                target_technology=validation_req.target_technology,
                validation_scope=validation_req.validation_scope,
                source_files=source_file_paths,
                source_screenshots=source_screenshot_paths,
                target_files=target_file_paths,
                target_screenshots=target_screenshot_paths,
                source_tech_version=validation_req.source_tech_version,
                target_tech_version=validation_req.target_tech_version,
                metadata=validation_req.metadata,
            )

            # Validate request
            validation_check = await validator.validate_request(migration_request)
            if not validation_check["valid"]:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Validation request is invalid",
                        "issues": validation_check["issues"],
                        "warnings": validation_check["warnings"],
                    },
                )

            # Start validation in background
            background_tasks.add_task(
                run_validation_background,
                migration_request.request_id,
                migration_request,
                validator,
            )

            # Store initial session
            session = ValidationSession(request=migration_request)
            session.add_log("Validation request received and queued for processing")
            validation_sessions[migration_request.request_id] = session

            return {
                "request_id": migration_request.request_id,
                "status": "accepted",
                "message": "Validation request accepted and processing started",
                "warnings": validation_check.get("warnings", []),
            }

        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in request data")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Validation failed: {e!s}")

    @app.get(
        "/api/validate/{request_id}/status",
        response_model=ValidationStatusResponse,
        tags=["Validation"],
    )
    async def get_validation_status(request_id: str):
        """Get validation status and progress."""
        if request_id not in validation_sessions:
            raise HTTPException(status_code=404, detail="Validation request not found")

        session = validation_sessions[request_id]

        # Determine status
        if session.result is None:
            status = "processing"
            progress = f"Processing step: {len(session.processing_log)}"
        elif session.result.overall_status == "error":
            status = "error"
            progress = None
        else:
            status = "completed"
            progress = "Validation completed"

        return ValidationStatusResponse(
            request_id=request_id,
            status=status,
            progress=progress,
            message=session.processing_log[-1] if session.processing_log else None,
            result_available=session.result is not None,
        )

    @app.get(
        "/api/validate/{request_id}/result",
        response_model=ValidationResultResponse,
        tags=["Validation"],
    )
    async def get_validation_result(request_id: str):
        """Get validation results."""
        if request_id not in validation_sessions:
            raise HTTPException(status_code=404, detail="Validation request not found")

        session = validation_sessions[request_id]

        if session.result is None:
            raise HTTPException(status_code=202, detail="Validation still in progress")

        if session.result.overall_status == "error":
            raise HTTPException(status_code=500, detail=session.result.summary)

        # Count discrepancies
        discrepancy_counts = {"critical": 0, "warning": 0, "info": 0}
        for discrepancy in session.result.discrepancies:
            discrepancy_counts[discrepancy.severity.value] += 1

        return ValidationResultResponse(
            request_id=request_id,
            overall_status=session.result.overall_status,
            fidelity_score=session.result.fidelity_score,
            fidelity_percentage=f"{session.result.fidelity_score * 100:.1f}%",
            summary=session.result.summary,
            discrepancy_counts=discrepancy_counts,
            execution_time=session.result.execution_time,
            timestamp=session.result.timestamp.isoformat(),
        )

    @app.get("/api/validate/{request_id}/report", tags=["Reports"])
    async def get_validation_report(request_id: str, format: str = "json"):
        """Get detailed validation report.

        Args:
            request_id: Validation request ID
            format: Report format (json, html, markdown)

        """
        if request_id not in validation_sessions:
            raise HTTPException(status_code=404, detail="Validation request not found")

        session = validation_sessions[request_id]

        if session.result is None:
            raise HTTPException(status_code=202, detail="Validation still in progress")

        try:
            report_content = await validator.generate_report(session, format)

            if format.lower() == "html":
                return PlainTextResponse(
                    content=report_content,
                    media_type="text/html",
                    headers={
                        "Content-Disposition": f"attachment; filename=validation_report_{request_id}.html",
                    },
                )
            if format.lower() == "markdown":
                return PlainTextResponse(
                    content=report_content,
                    media_type="text/markdown",
                    headers={
                        "Content-Disposition": f"attachment; filename=validation_report_{request_id}.md",
                    },
                )
            # JSON
            return JSONResponse(
                content=json.loads(report_content), headers={
                    "Content-Disposition": f"attachment; filename=validation_report_{request_id}.json", }, )

        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Report generation failed: {e!s}")

    @app.get("/api/validate/{request_id}/logs", tags=["Validation"])
    async def get_validation_logs(request_id: str):
        """Get validation processing logs."""
        if request_id not in validation_sessions:
            raise HTTPException(status_code=404, detail="Validation request not found")

        session = validation_sessions[request_id]

        return {
            "request_id": request_id,
            "logs": session.processing_log,
            "log_count": len(session.processing_log),
        }

    @app.delete("/api/validate/{request_id}", tags=["Validation"])
    async def delete_validation_session(request_id: str):
        """Delete validation session and clean up files."""
        if request_id not in validation_sessions:
            raise HTTPException(status_code=404, detail="Validation request not found")

        session = validation_sessions[request_id]

        # Clean up uploaded files
        all_files = (
            session.request.source_input.files
            + session.request.source_input.screenshots
            + session.request.target_input.files
            + session.request.target_input.screenshots
        )

        input_processor.cleanup_uploads(all_files)

        # Remove session
        del validation_sessions[request_id]

        return {"message": f"Validation session {request_id} deleted successfully"}

    @app.get("/api/validate", tags=["Validation"])
    async def list_validation_sessions():
        """List all validation sessions."""
        sessions_info = []

        for request_id, session in validation_sessions.items():
            status = "completed" if session.result else "processing"
            if session.result and session.result.overall_status == "error":
                status = "error"

            sessions_info.append(
                {
                    "request_id": request_id,
                    "status": status,
                    "created_at": session.request.created_at.isoformat(),
                    "source_technology": session.request.source_technology.type.value,
                    "target_technology": session.request.target_technology.type.value,
                    "validation_scope": session.request.validation_scope.value,
                    "fidelity_score": (
                        session.result.fidelity_score if session.result else None),
                },
            )

        return {"sessions": sessions_info, "total_count": len(sessions_info)}

    @app.post("/api/behavioral/validate", tags=["Behavioral Validation"])
    async def start_behavioral_validation(
        background_tasks: BackgroundTasks, request: BehavioralValidationRequestModel,
    ):
        """Start behavioral validation with source and target URLs.

        This endpoint initiates behavioral testing using browser automation
        to compare user interactions between source and target systems.
        """
        try:
            # Generate unique request ID
            request_id = f"behavioral_{
                datetime.now().strftime('%Y%m%d_%H%M%S')}_{
                hash(
                    request.source_url
                    + request.target_url) %
                10000:04d}"

            # Create behavioral validation request
            behavioral_request = BehavioralValidationRequest(
                source_url=request.source_url,
                target_url=request.target_url,
                validation_scenarios=request.validation_scenarios,
                credentials=request.credentials,
                timeout=request.timeout,
                metadata=request.metadata or {},
            )

            # Initialize session tracking
            behavioral_validation_sessions[request_id] = {
                "request": behavioral_request,
                "status": "pending",
                "created_at": datetime.now(),
                "progress": "Behavioral validation queued for processing",
                "result": None,
                "logs": ["Behavioral validation request received and queued"],
            }

            # Start validation in background
            background_tasks.add_task(
                run_behavioral_validation_background, request_id, behavioral_request,
            )

            return {
                "request_id": request_id,
                "status": "accepted",
                "message": "Behavioral validation request accepted and processing started",
                "estimated_time": f"{
                    request.timeout}s maximum",
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start behavioral validation: {e!s}",
            )

    @app.get(
        "/api/behavioral/{request_id}/status",
        response_model=BehavioralValidationStatusResponse,
        tags=["Behavioral Validation"],
    )
    async def get_behavioral_validation_status(request_id: str):
        """Get behavioral validation status and progress."""
        if request_id not in behavioral_validation_sessions:
            raise HTTPException(status_code=404,
                                detail="Behavioral validation request not found")

        session = behavioral_validation_sessions[request_id]

        return BehavioralValidationStatusResponse(
            request_id=request_id,
            status=session["status"],
            progress=session.get("progress"),
            message=session["logs"][-1] if session["logs"] else None,
            result_available=session["result"] is not None,
        )

    @app.get(
        "/api/behavioral/{request_id}/result",
        response_model=BehavioralValidationResultResponse,
        tags=["Behavioral Validation"],
    )
    async def get_behavioral_validation_result(request_id: str):
        """Get behavioral validation results."""
        if request_id not in behavioral_validation_sessions:
            raise HTTPException(status_code=404,
                                detail="Behavioral validation request not found")

        session = behavioral_validation_sessions[request_id]

        if session["result"] is None:
            raise HTTPException(status_code=202,
                                detail="Behavioral validation still in progress")

        result = session["result"]

        if result.overall_status == "error":
            raise HTTPException(status_code=500, detail="Behavioral validation failed")

        # Convert discrepancies to dictionary format for JSON serialization
        discrepancies_dict = []
        for discrepancy in result.discrepancies:
            discrepancies_dict.append(
                {
                    "type": discrepancy.type,
                    "severity": discrepancy.severity.value,
                    "description": discrepancy.description,
                    "source_element": discrepancy.source_element,
                    "target_element": discrepancy.target_element,
                    "recommendation": discrepancy.recommendation,
                    "confidence": discrepancy.confidence,
                },
            )

        return BehavioralValidationResultResponse(
            request_id=request_id,
            overall_status=result.overall_status,
            fidelity_score=result.fidelity_score,
            fidelity_percentage=f"{result.fidelity_score * 100:.1f}%",
            discrepancies=discrepancies_dict,
            execution_time=result.execution_time,
            timestamp=result.timestamp.isoformat(),
        )

    @app.post("/api/validate/hybrid", tags=["Validation"])
    async def validate_migration_hybrid(
        background_tasks: BackgroundTasks,
        request_data: str = Form(...),
        source_files: List[UploadFile] = File(default=[]),
        source_screenshots: List[UploadFile] = File(default=[]),
        target_files: List[UploadFile] = File(default=[]),
        target_screenshots: List[UploadFile] = File(default=[]),
    ):
        """Execute hybrid validation combining static analysis and behavioral testing.

        This endpoint handles both file-based static analysis and URL-based behavioral
        validation, providing a comprehensive migration assessment.
        """
        try:
            # Parse request data
            import json

            hybrid_request = HybridValidationRequest(**json.loads(request_data))

            # Generate unique request ID for hybrid validation
            request_id = f"hybrid_{
                datetime.now().strftime('%Y%m%d_%H%M%S')}_{
                hash(
                    str(
                        hybrid_request.dict())) %
                10000:04d}"

            # Determine validation types to perform
            perform_static = bool(
                source_files or target_files or source_screenshots or target_screenshots, )
            perform_behavioral = bool(
                hybrid_request.source_url and hybrid_request.target_url)

            if not perform_static and not perform_behavioral:
                raise HTTPException(
                    status_code=400,
                    detail="Either static files/screenshots or behavioral URLs must be provided",
                )

            # Initialize hybrid session tracking
            validation_sessions[request_id] = ValidationSession(
                request=None,  # Will be populated during processing
                processing_log=[
                    f"Hybrid validation started - Static: {perform_static}, Behavioral: {perform_behavioral}",
                ],
            )

            # Start hybrid validation in background
            background_tasks.add_task(
                run_hybrid_validation_background,
                request_id,
                hybrid_request,
                {
                    "source_files": source_files,
                    "source_screenshots": source_screenshots,
                    "target_files": target_files,
                    "target_screenshots": target_screenshots,
                },
                perform_static,
                perform_behavioral,
                validator,
                input_processor,
            )

            return {
                "request_id": request_id,
                "status": "accepted",
                "message": "Hybrid validation request accepted and processing started",
                "validation_types": {
                    "static_analysis": perform_static,
                    "behavioral_testing": perform_behavioral,
                },
            }

        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in request data")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Hybrid validation failed: {e!s}")

    @app.get("/api/behavioral/{request_id}/logs", tags=["Behavioral Validation"])
    async def get_behavioral_validation_logs(request_id: str):
        """Get behavioral validation processing logs."""
        if request_id not in behavioral_validation_sessions:
            raise HTTPException(status_code=404,
                                detail="Behavioral validation request not found")

        session = behavioral_validation_sessions[request_id]

        return {
            "request_id": request_id,
            "logs": session["logs"],
            "log_count": len(session["logs"]),
        }

    @app.delete("/api/behavioral/{request_id}", tags=["Behavioral Validation"])
    async def delete_behavioral_validation_session(request_id: str):
        """Delete behavioral validation session and clean up resources."""
        if request_id not in behavioral_validation_sessions:
            raise HTTPException(status_code=404,
                                detail="Behavioral validation request not found")

        # Remove session
        del behavioral_validation_sessions[request_id]

        return {"message": f"Behavioral validation session {request_id} deleted successfully"}

    @app.get("/api/behavioral", tags=["Behavioral Validation"])
    async def list_behavioral_validation_sessions():
        """List all behavioral validation sessions."""
        sessions_info = []

        for request_id, session in behavioral_validation_sessions.items():
            sessions_info.append(
                {
                    "request_id": request_id,
                    "status": session["status"],
                    "created_at": session["created_at"].isoformat(),
                    "source_url": session["request"].source_url,
                    "target_url": session["request"].target_url,
                    "scenarios_count": len(session["request"].validation_scenarios),
                    "fidelity_score": (
                        session["result"].fidelity_score if session["result"] else None
                    ),
                },
            )

        return {"sessions": sessions_info, "total_count": len(sessions_info)}

    # Include async processing routes
    app.include_router(async_router)

    return app


async def run_validation_background(
    request_id: str, migration_request, validator: MigrationValidator,
):
    """Run validation in background task."""
    try:
        session = await validator.validate_migration(migration_request)
        validation_sessions[request_id] = session
    except Exception as e:
        # Update session with error
        if request_id in validation_sessions:
            session = validation_sessions[request_id]
            session.add_log(f"Validation failed: {e!s}")
            # Create error result
            from ..core.models import ValidationResult

            session.result = ValidationResult(
                overall_status="error",
                fidelity_score=0.0,
                summary=f"Validation failed: {e!s}",
                discrepancies=[],
            )


async def run_behavioral_validation_background(
    request_id: str, behavioral_request: BehavioralValidationRequest,
):
    """Run behavioral validation in background task."""
    try:
        # Update session status
        if request_id in behavioral_validation_sessions:
            behavioral_validation_sessions[request_id]["status"] = "processing"
            behavioral_validation_sessions[request_id][
                "progress"
            ] = "Initializing behavioral validation crew"
            behavioral_validation_sessions[request_id]["logs"].append(
                "Starting behavioral validation crew",
            )

        # Create behavioral validation crew
        crew = create_behavioral_validation_crew()

        # Update progress
        if request_id in behavioral_validation_sessions:
            behavioral_validation_sessions[request_id][
                "progress"
            ] = "Executing behavioral validation scenarios"
            behavioral_validation_sessions[request_id]["logs"].append(
                "Behavioral validation crew initialized, starting validation",
            )

        # Execute behavioral validation
        result = await crew.validate_migration(behavioral_request)

        # Update session with results
        if request_id in behavioral_validation_sessions:
            behavioral_validation_sessions[request_id]["status"] = "completed"
            behavioral_validation_sessions[request_id][
                "progress"
            ] = "Behavioral validation completed"
            behavioral_validation_sessions[request_id]["result"] = result
            behavioral_validation_sessions[request_id]["logs"].append(
                f"Behavioral validation completed with fidelity score: {
                    result.fidelity_score:.2f}", )

    except Exception as e:
        # Update session with error
        if request_id in behavioral_validation_sessions:
            behavioral_validation_sessions[request_id]["status"] = "error"
            behavioral_validation_sessions[request_id][
                "progress"
            ] = f"Behavioral validation failed: {e!s}"
            behavioral_validation_sessions[request_id]["logs"].append(
                f"Behavioral validation error: {e!s}",
            )

            # Create error result
            from ..behavioral.crews import BehavioralValidationResult

            error_result = BehavioralValidationResult(
                overall_status="error",
                fidelity_score=0.0,
                discrepancies=[
                    ValidationDiscrepancy(
                        type="behavioral_validation_error",
                        severity=SeverityLevel.CRITICAL,
                        description=f"Behavioral validation failed: {
                            e!s}",
                        recommendation="Review system configuration and retry validation",
                    ),
                ],
                execution_log=[
                    f"Error: {
                        e!s}"],
                execution_time=0.0,
                timestamp=datetime.now(),
            )
            behavioral_validation_sessions[request_id]["result"] = error_result


async def run_hybrid_validation_background(
    request_id: str,
    hybrid_request: HybridValidationRequest,
    uploaded_files: Dict[str, List],
    perform_static: bool,
    perform_behavioral: bool,
    validator: MigrationValidator,
    input_processor: InputProcessor,
):
    """Run hybrid validation combining static and behavioral validation."""
    try:
        session = validation_sessions[request_id]
        session.add_log("Starting hybrid validation process")

        static_result = None
        behavioral_result = None

        # Perform static validation if files were provided
        if perform_static:
            session.add_log("Starting static validation component")

            # Process uploaded files similar to the main validation endpoint
            source_file_paths = []
            source_screenshot_paths = []
            target_file_paths = []
            target_screenshot_paths = []

            # Handle source files
            if uploaded_files["source_files"]:
                source_uploaded = []
                for file in uploaded_files["source_files"]:
                    if file.filename:
                        contents = await file.read()
                        source_uploaded.append((file.filename, contents))

                if source_uploaded:
                    source_file_paths = input_processor.upload_files(
                        source_uploaded, "hybrid_source",
                    )

            # Handle source screenshots
            if uploaded_files["source_screenshots"]:
                source_screenshot_uploaded = []
                for file in uploaded_files["source_screenshots"]:
                    if file.filename:
                        contents = await file.read()
                        source_screenshot_uploaded.append((file.filename, contents))

                if source_screenshot_uploaded:
                    source_screenshot_paths = input_processor.upload_files(
                        source_screenshot_uploaded, "hybrid_source_screenshots",
                    )

            # Handle target files
            if uploaded_files["target_files"]:
                target_uploaded = []
                for file in uploaded_files["target_files"]:
                    if file.filename:
                        contents = await file.read()
                        target_uploaded.append((file.filename, contents))

                if target_uploaded:
                    target_file_paths = input_processor.upload_files(
                        target_uploaded, "hybrid_target",
                    )

            # Handle target screenshots
            if uploaded_files["target_screenshots"]:
                target_screenshot_uploaded = []
                for file in uploaded_files["target_screenshots"]:
                    if file.filename:
                        contents = await file.read()
                        target_screenshot_uploaded.append((file.filename, contents))

                if target_screenshot_uploaded:
                    target_screenshot_paths = input_processor.upload_files(
                        target_screenshot_uploaded, "hybrid_target_screenshots",
                    )

            # Create static validation request
            migration_request = input_processor.create_validation_request(
                source_technology=hybrid_request.source_technology,
                target_technology=hybrid_request.target_technology,
                validation_scope=hybrid_request.validation_scope,
                source_files=source_file_paths,
                source_screenshots=source_screenshot_paths,
                target_files=target_file_paths,
                target_screenshots=target_screenshot_paths,
                source_tech_version=hybrid_request.source_tech_version,
                target_tech_version=hybrid_request.target_tech_version,
                metadata=hybrid_request.metadata,
            )

            session.request = migration_request
            session.add_log("Static validation request created")

            # Execute static validation
            static_session = await validator.validate_migration(migration_request)
            static_result = static_session.result
            session.add_log(
                f"Static validation completed with fidelity score: {
                    static_result.fidelity_score:.2f}", )

        # Perform behavioral validation if URLs were provided
        if perform_behavioral:
            session.add_log("Starting behavioral validation component")

            # Create behavioral validation request
            behavioral_request = BehavioralValidationRequest(
                source_url=hybrid_request.source_url,
                target_url=hybrid_request.target_url,
                validation_scenarios=hybrid_request.validation_scenarios,
                credentials=hybrid_request.credentials,
                timeout=hybrid_request.behavioral_timeout,
                metadata=hybrid_request.metadata or {},
            )

            # Execute behavioral validation
            crew = create_behavioral_validation_crew()
            behavioral_result = await crew.validate_migration(behavioral_request)
            session.add_log(
                f"Behavioral validation completed with fidelity score: {
                    behavioral_result.fidelity_score:.2f}", )

        # Combine results
        session.add_log("Combining static and behavioral validation results")

        if static_result and behavioral_result:
            # Hybrid result with both components
            combined_fidelity = (
                static_result.fidelity_score + behavioral_result.fidelity_score
            ) / 2
            combined_discrepancies = static_result.discrepancies + behavioral_result.discrepancies
            combined_status = ("approved" if combined_fidelity >= 0.8 else (
                "approved_with_warnings" if combined_fidelity >= 0.6 else "rejected"))

            session.result = ValidationResult(
                overall_status=combined_status,
                fidelity_score=combined_fidelity,
                summary=f"Hybrid validation completed. Static fidelity: {
                    static_result.fidelity_score:.2f}, Behavioral fidelity: {
                    behavioral_result.fidelity_score:.2f}, Combined: {
                    combined_fidelity:.2f}",
                discrepancies=combined_discrepancies,
                execution_time=(
                    static_result.execution_time or 0) + (
                        behavioral_result.execution_time or 0),
            )

        elif static_result:
            # Static-only result
            session.result = static_result
            session.result.summary = (
                f"Static validation completed. Fidelity score: {
                    static_result.fidelity_score:.2f}")

        elif behavioral_result:
            # Behavioral-only result (convert from BehavioralValidationResult to
            # ValidationResult)
            session.result = ValidationResult(
                overall_status=behavioral_result.overall_status,
                fidelity_score=behavioral_result.fidelity_score,
                summary=f"Behavioral validation completed. Fidelity score: {
                    behavioral_result.fidelity_score:.2f}",
                discrepancies=behavioral_result.discrepancies,
                execution_time=behavioral_result.execution_time,
            )

        session.add_log("Hybrid validation completed successfully")

    except Exception as e:
        # Update session with error
        if request_id in validation_sessions:
            session = validation_sessions[request_id]
            session.add_log(f"Hybrid validation failed: {e!s}")

            session.result = ValidationResult(
                overall_status="error",
                fidelity_score=0.0,
                summary=f"Hybrid validation failed: {
                    e!s}",
                discrepancies=[
                    ValidationDiscrepancy(
                        type="hybrid_validation_error",
                        severity=SeverityLevel.CRITICAL,
                        description=f"Hybrid validation failed: {
                            e!s}",
                        recommendation="Review system configuration and retry validation",
                    ),
                ],
            )


# Create the FastAPI application instance
app = create_app()
