from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import List, Optional, Any
import os
import re

from ..core.logging import logger
from ..config import security_settings


class InputValidationMiddleware(BaseHTTPMiddleware):
    # Common file signatures (magic bytes) for basic file type detection
    # This list can be expanded as needed
    FILE_SIGNATURES = {
        b"\x89PNG\x0d\x0a\x1a\x0a": "image/png",
        b"\xff\xd8\xff": "image/jpeg",
        b"GIF87a": "image/gif",
        b"GIF89a": "image/gif",
        b"%PDF": "application/pdf",
        b"PK\x03\x04": "application/zip",  # Also for docx, xlsx, pptx
        b"\x50\x4b\x03\x04": "application/zip",  # Alternative for zip
        b"\x49\x49\x2a\x00": "image/tiff",
        b"\x4d\x4d\x00\x2a": "image/tiff",
        b"\x42\x4d": "image/bmp",
    }

    def __init__(
        self,
        app: ASGIApp,
        enable_path_traversal_prevention: bool = True,
    ):
        super().__init__(app)
        self.max_file_size = security_settings.MAX_UPLOAD_FILE_SIZE
        self.max_files_per_request = security_settings.MAX_UPLOAD_FILES_PER_REQUEST
        self.allowed_file_types = []  # Will be determined by magic bytes
        self.enable_path_traversal_prevention = enable_path_traversal_prevention
        self.logger = logger.bind(middleware="InputValidationMiddleware")

    async def dispatch(self, request: Request, call_next):
        try:
            # Path Traversal Prevention
            if self.enable_path_traversal_prevention:
                self._prevent_path_traversal(request.url.path)

            # File Upload Validation (if request is multipart/form-data)
            if "multipart/form-data" in request.headers.get("Content-Type", ""):
                await self._validate_file_uploads(request)

            # Request Payload Sanitization (for JSON/form data)
            if request.method in [
                "POST",
                "PUT",
                "PATCH",
            ] and "application/json" in request.headers.get("Content-Type", ""):
                await self._sanitize_payload(request)

            response = await call_next(request)
            return response
        except HTTPException as e:
            self.logger.warning(
                "Input validation failed", detail=e.detail, status_code=e.status_code
            )
            raise
        except Exception as e:
            self.logger.error("Unhandled error in input validation middleware", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

    def _prevent_path_traversal(self, path: str):
        if ".." in path or "%2e%2e" in path.lower():
            self.logger.warning("Path traversal attempt detected", path=path)
            raise HTTPException(status_code=400, detail="Path traversal detected")
        # Normalize path to prevent hidden traversal attempts
        normalized_path = os.path.normpath(path)
        if (
            normalized_path.startswith("../")
            or normalized_path.startswith("/")
            and ".." in normalized_path
        ):
            self.logger.warning(
                "Normalized path traversal attempt detected",
                path=path,
                normalized_path=normalized_path,
            )
            raise HTTPException(status_code=400, detail="Path traversal detected")

    async def _validate_file_uploads(self, request: Request):
        # This is a basic example. For production, use a dedicated file upload library
        # that handles streaming and temporary storage more robustly.
        uploaded_files_count = 0
        form = await request.form()
        for field_name in form:
            file = form[field_name]
            if not hasattr(file, "filename") or not file.filename:
                continue
            uploaded_files_count += 1

            if uploaded_files_count > self.max_files_per_request:
                self.logger.warning(
                    "Too many files uploaded",
                    count=uploaded_files_count,
                    limit=self.max_files_per_request,
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Maximum {self.max_files_per_request} files allowed per request",
                )

            file_content = await file.read()
            if len(file_content) > self.max_file_size:
                self.logger.warning(
                    "File size limit exceeded",
                    filename=file.filename,
                    size=len(file_content),
                    limit=self.max_file_size,
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} too large. Max size: {self.max_file_size / (1024 * 1024):.1f} MB",
                )

            # Validate file content using magic bytes
            detected_mime_type = self._validate_file_content(file_content, file.filename)
            if not detected_mime_type:
                self.logger.warning("Disallowed file content detected", filename=file.filename)
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} content type not allowed or recognized",
                )

            # Re-assign the file content to the SpooledTemporaryFile to allow downstream processing
            # This is a workaround as request.form() consumes the file stream
            file.file.seek(0)  # Reset pointer
            file.file.write(file_content)  # Write content back
            file.file.seek(0)  # Reset pointer again for next read

            # Malware scanning (placeholder)
            self._scan_for_malware(file_content, file.filename)

    def _validate_file_content(self, content: bytes, filename: str) -> Optional[str]:
        """Validate file content using magic bytes and return detected MIME type."""
        for signature, mime_type in self.FILE_SIGNATURES.items():
            if content.startswith(signature):
                self.logger.info(
                    "File content validated by magic bytes", filename=filename, mime_type=mime_type
                )
                return mime_type
        self.logger.warning("File content magic bytes not recognized", filename=filename)
        return None

    def _scan_for_malware(self, content: bytes, filename: str):
        """
        Placeholder for malware scanning.

        In a real application, this would integrate with a malware scanning service
        (e.g., ClamAV, VirusTotal API).
        """
        # For demonstration, we'll just log a message.
        # In a real scenario, if malware is detected, raise HTTPException.
        self.logger.info(
            "File sent for malware scan (placeholder)", filename=filename, size=len(content)
        )

    async def _sanitize_payload(self, request: Request):
        """Recursively sanitizes string values in JSON payloads to prevent XSS."""
        try:
            body = await request.json()
            sanitized_body = self._recursive_sanitize(body)
            # Re-assign the sanitized body to the request
            # This is a bit tricky with FastAPI/Starlette as request.json() consumes the stream.
            # For a robust solution, consider using a Body parser or modifying request._body directly.
            # For this example, we'll assume the sanitized_body is used downstream.
            request._json = sanitized_body  # This is a private attribute, use with caution
        except Exception as e:
            self.logger.error("Error sanitizing JSON payload", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

    def _recursive_sanitize(self, data: Any) -> Any:
        """Recursively sanitizes strings in dictionaries and lists."""
        if isinstance(data, dict):
            return {k: self._recursive_sanitize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._recursive_sanitize(elem) for elem in data]
        elif isinstance(data, str):
            return self._sanitize_string(data)
        return data

    def _sanitize_string(self, text: str) -> str:
        """Basic XSS sanitization for strings."""
        # Replace HTML special characters
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&#x27;")
        text = text.replace("/", "&#x2F;")
        return text
