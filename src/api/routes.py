"""
FastAPI routes for AI-Powered Migration Validation System.

Provides REST API endpoints for migration validation functionality:
- Technology options and validation
- File upload handling
- Migration validation execution
- Report generation and retrieval
"""

import os
import tempfile
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncio
from datetime import datetime

from ..core.migration_validator import MigrationValidator
from ..core.input_processor import InputProcessor
from ..core.models import ValidationSession


# Pydantic models for API requests/responses
class TechnologyOption(BaseModel):
    value: str
    label: str


class ValidationScopeOption(BaseModel):
    value: str
    label: str


class InputTypeOption(BaseModel):
    value: str
    label: str


class TechnologyOptionsResponse(BaseModel):
    source_technologies: List[TechnologyOption]
    target_technologies: List[TechnologyOption]
    validation_scopes: List[ValidationScopeOption]
    input_types: List[InputTypeOption]


class ValidationRequest(BaseModel):
    source_technology: str = Field(..., description="Source technology type")
    target_technology: str = Field(..., description="Target technology type")
    validation_scope: str = Field(..., description="Validation scope")
    source_tech_version: Optional[str] = Field(None, description="Source technology version")
    target_tech_version: Optional[str] = Field(None, description="Target technology version")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ValidationStatusResponse(BaseModel):
    request_id: str
    status: str  # pending, processing, completed, error
    progress: Optional[str] = None
    message: Optional[str] = None
    result_available: bool = False


class ValidationResultResponse(BaseModel):
    request_id: str
    overall_status: str
    fidelity_score: float
    fidelity_percentage: str
    summary: str
    discrepancy_counts: Dict[str, int]
    execution_time: Optional[float]
    timestamp: str


class CompatibilityCheckRequest(BaseModel):
    source_technology: str
    target_technology: str
    validation_scope: str


class CompatibilityCheckResponse(BaseModel):
    compatible: bool
    issues: List[str]
    warnings: List[str]


# Global storage for validation sessions (in production, use Redis or database)
validation_sessions: Dict[str, ValidationSession] = {}


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="AI-Powered Migration Validation System",
        description="Validates code migrations between different technologies using AI-powered analysis",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
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
    
    @app.get("/", tags=["Health"])
    async def root():
        """Health check endpoint."""
        return {
            "message": "AI-Powered Migration Validation System",
            "status": "running",
            "version": "1.0.0"
        }
    
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Detailed health check."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "validator": "operational",
                "input_processor": "operational"
            }
        }
    
    @app.get("/api/technologies", response_model=TechnologyOptionsResponse, tags=["Configuration"])
    async def get_technology_options():
        """Get available technology options for validation."""
        try:
            options = input_processor.get_technology_options()
            return TechnologyOptionsResponse(**options)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get technology options: {str(e)}")
    
    @app.post("/api/compatibility/check", response_model=CompatibilityCheckResponse, tags=["Configuration"])
    async def check_compatibility(request: CompatibilityCheckRequest):
        """Check compatibility between source and target technologies."""
        try:
            result = input_processor.validate_technology_compatibility(
                request.source_technology,
                request.target_technology,
                request.validation_scope
            )
            return CompatibilityCheckResponse(**result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Compatibility check failed: {str(e)}")
    
    @app.get("/api/capabilities", tags=["Configuration"])
    async def get_system_capabilities():
        """Get system capabilities and supported features."""
        try:
            capabilities = validator.get_supported_technologies()
            return capabilities
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get capabilities: {str(e)}")
    
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
                "files": [{"filename": os.path.basename(path), "path": path} for path in saved_paths]
            }
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
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
                "files": [{"filename": os.path.basename(path), "path": path} for path in saved_paths]
            }
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    @app.post("/api/validate", tags=["Validation"])
    async def validate_migration(
        background_tasks: BackgroundTasks,
        request_data: str = Form(...),
        source_files: List[UploadFile] = File(default=[]),
        source_screenshots: List[UploadFile] = File(default=[]),
        target_files: List[UploadFile] = File(default=[]),
        target_screenshots: List[UploadFile] = File(default=[])
    ):
        """
        Execute migration validation with uploaded files.
        
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
                    source_file_paths = input_processor.upload_files(source_uploaded, "source_validation")
            
            # Handle source screenshots
            if source_screenshots:
                source_screenshot_uploaded = []
                for file in source_screenshots:
                    if file.filename:
                        contents = await file.read()
                        source_screenshot_uploaded.append((file.filename, contents))
                
                if source_screenshot_uploaded:
                    source_screenshot_paths = input_processor.upload_files(
                        source_screenshot_uploaded, "source_screenshots"
                    )
            
            # Handle target files
            if target_files:
                target_uploaded = []
                for file in target_files:
                    if file.filename:
                        contents = await file.read()
                        target_uploaded.append((file.filename, contents))
                
                if target_uploaded:
                    target_file_paths = input_processor.upload_files(target_uploaded, "target_validation")
            
            # Handle target screenshots
            if target_screenshots:
                target_screenshot_uploaded = []
                for file in target_screenshots:
                    if file.filename:
                        contents = await file.read()
                        target_screenshot_uploaded.append((file.filename, contents))
                
                if target_screenshot_uploaded:
                    target_screenshot_paths = input_processor.upload_files(
                        target_screenshot_uploaded, "target_screenshots"
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
                metadata=validation_req.metadata
            )
            
            # Validate request
            validation_check = await validator.validate_request(migration_request)
            if not validation_check["valid"]:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Validation request is invalid",
                        "issues": validation_check["issues"],
                        "warnings": validation_check["warnings"]
                    }
                )
            
            # Start validation in background
            background_tasks.add_task(
                run_validation_background,
                migration_request.request_id,
                migration_request,
                validator
            )
            
            # Store initial session
            session = ValidationSession(request=migration_request)
            session.add_log("Validation request received and queued for processing")
            validation_sessions[migration_request.request_id] = session
            
            return {
                "request_id": migration_request.request_id,
                "status": "accepted",
                "message": "Validation request accepted and processing started",
                "warnings": validation_check.get("warnings", [])
            }
            
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in request data")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
    
    @app.get("/api/validate/{request_id}/status", response_model=ValidationStatusResponse, tags=["Validation"])
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
            result_available=session.result is not None
        )
    
    @app.get("/api/validate/{request_id}/result", response_model=ValidationResultResponse, tags=["Validation"])
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
            timestamp=session.result.timestamp.isoformat()
        )
    
    @app.get("/api/validate/{request_id}/report", tags=["Reports"])
    async def get_validation_report(
        request_id: str,
        format: str = "json"
    ):
        """
        Get detailed validation report.
        
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
                    headers={"Content-Disposition": f"attachment; filename=validation_report_{request_id}.html"}
                )
            elif format.lower() == "markdown":
                return PlainTextResponse(
                    content=report_content,
                    media_type="text/markdown",
                    headers={"Content-Disposition": f"attachment; filename=validation_report_{request_id}.md"}
                )
            else:  # JSON
                return JSONResponse(
                    content=json.loads(report_content),
                    headers={"Content-Disposition": f"attachment; filename=validation_report_{request_id}.json"}
                )
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
    
    @app.get("/api/validate/{request_id}/logs", tags=["Validation"])
    async def get_validation_logs(request_id: str):
        """Get validation processing logs."""
        if request_id not in validation_sessions:
            raise HTTPException(status_code=404, detail="Validation request not found")
        
        session = validation_sessions[request_id]
        
        return {
            "request_id": request_id,
            "logs": session.processing_log,
            "log_count": len(session.processing_log)
        }
    
    @app.delete("/api/validate/{request_id}", tags=["Validation"])
    async def delete_validation_session(request_id: str):
        """Delete validation session and clean up files."""
        if request_id not in validation_sessions:
            raise HTTPException(status_code=404, detail="Validation request not found")
        
        session = validation_sessions[request_id]
        
        # Clean up uploaded files
        all_files = (
            session.request.source_input.files +
            session.request.source_input.screenshots +
            session.request.target_input.files +
            session.request.target_input.screenshots
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
            
            sessions_info.append({
                "request_id": request_id,
                "status": status,
                "created_at": session.request.created_at.isoformat(),
                "source_technology": session.request.source_technology.type.value,
                "target_technology": session.request.target_technology.type.value,
                "validation_scope": session.request.validation_scope.value,
                "fidelity_score": session.result.fidelity_score if session.result else None
            })
        
        return {
            "sessions": sessions_info,
            "total_count": len(sessions_info)
        }
    
    return app


async def run_validation_background(request_id: str, migration_request, validator: MigrationValidator):
    """Run validation in background task."""
    try:
        session = await validator.validate_migration(migration_request)
        validation_sessions[request_id] = session
    except Exception as e:
        # Update session with error
        if request_id in validation_sessions:
            session = validation_sessions[request_id]
            session.add_log(f"Validation failed: {str(e)}")
            # Create error result
            from ..core.models import ValidationResult
            session.result = ValidationResult(
                overall_status="error",
                fidelity_score=0.0,
                summary=f"Validation failed: {str(e)}",
                discrepancies=[]
            )


# Create the FastAPI application instance
app = create_app()