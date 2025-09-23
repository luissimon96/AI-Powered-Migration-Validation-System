"""Security validation module for input sanitization and validation.

Provides comprehensive input validation, sanitization, and security checks
to prevent injection attacks, malicious file uploads, and other security threats.
"""

import mimetypes
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import magic
from fastapi import UploadFile
from pydantic import BaseModel, EmailStr


class SecurityValidationError(Exception):
    """Security validation error."""



class FileValidationResult(BaseModel):
    """File validation result."""

    is_valid: bool
    detected_type: str
    file_size: int
    security_issues: List[str] = []
    warnings: List[str] = []


class InputValidationRules(BaseModel):
    """Input validation rules configuration."""

    max_string_length: int = 10000
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_files_per_request: int = 20
    allowed_file_types: List[str] = [
        "text/plain",
        "application/json",
        "image/png",
        "image/jpeg",
        "text/html",
        "text/css",
        "application/javascript",
    ]
    allowed_file_extensions: List[str] = [
        ".txt",
        ".json",
        ".png",
        ".jpg",
        ".jpeg",
        ".html",
        ".css",
        ".js",
        ".py",
        ".java",
        ".cpp",
        ".c",
        ".ts",
        ".jsx",
        ".tsx",
        ".php",
        ".rb",
    ]
    blocked_file_types: List[str] = [
        "application/x-executable",
        "application/x-msdos-program",
        "application/vnd.microsoft.portable-executable",
        "application/x-msdownload",
        "application/x-sh",
    ]
    url_schemes: List[str] = ["http", "https"]
    max_url_length: int = 2048


class SecurityValidator:
    """Security validator for comprehensive input validation."""

    def __init__(self, rules: Optional[InputValidationRules] = None):
        self.rules = rules or InputValidationRules()

        # Compile regex patterns for efficiency
        self.sql_injection_patterns = [
            re.compile(r"('|(\\'))|(;|--|\s+or\s+|\s+and\s+)", re.IGNORECASE),
            re.compile(
                r"(union\s+select|insert\s+into|delete\s+from|drop\s+table)", re.IGNORECASE,
            ),
            re.compile(r"(exec\s*\(|execute\s*\(|sp_|xp_)", re.IGNORECASE),
        ]

        self.xss_patterns = [
            re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"on\w+\s*=", re.IGNORECASE),
            re.compile(r"<iframe[^>]*>", re.IGNORECASE),
        ]

        self.path_traversal_patterns = [
            re.compile(r"\.\.[\\/]"),
            re.compile(r"[\\/]\.\.[\\/]"),
            re.compile(r"^\.\.[\\/]"),
        ]

        self.command_injection_patterns = [
            re.compile(r"[;&|`$\(\){}]", re.IGNORECASE),
            re.compile(r"(rm\s|del\s|format\s|mkfs\s)", re.IGNORECASE),
            re.compile(r"(>|<|>>|<<|\|)", re.IGNORECASE),
        ]

    def validate_string_input(self, value: str, field_name: str = "input") -> str:
        """Validate and sanitize string input."""
        if not isinstance(value, str):
            raise SecurityValidationError(f"{field_name} must be a string")

        # Length check
        if len(value) > self.rules.max_string_length:
            raise SecurityValidationError(
                f"{field_name} exceeds maximum length of {self.rules.max_string_length}",
            )

        # Check for SQL injection patterns
        for pattern in self.sql_injection_patterns:
            if pattern.search(value):
                raise SecurityValidationError(
                    f"{field_name} contains potential SQL injection pattern",
                )

        # Check for XSS patterns
        for pattern in self.xss_patterns:
            if pattern.search(value):
                raise SecurityValidationError(f"{field_name} contains potential XSS pattern")

        # Check for path traversal
        for pattern in self.path_traversal_patterns:
            if pattern.search(value):
                raise SecurityValidationError(
                    f"{field_name} contains potential path traversal pattern",
                )

        # Check for command injection
        for pattern in self.command_injection_patterns:
            if pattern.search(value):
                raise SecurityValidationError(
                    f"{field_name} contains potential command injection pattern",
                )

        return value.strip()

    def validate_email(self, email: str) -> EmailStr:
        """Validate email address."""
        try:
            return EmailStr(email)
        except ValueError:
            raise SecurityValidationError("Invalid email format")

    def validate_url(self, url: str, field_name: str = "URL") -> str:
        """Validate URL input."""
        if len(url) > self.rules.max_url_length:
            raise SecurityValidationError(
                f"{field_name} exceeds maximum length of {self.rules.max_url_length}",
            )

        try:
            parsed = urlparse(url)
        except Exception:
            raise SecurityValidationError(f"Invalid {field_name} format")

        if parsed.scheme not in self.rules.url_schemes:
            raise SecurityValidationError(
                f"{field_name} scheme must be one of: {self.rules.url_schemes}",
            )

        if not parsed.netloc:
            raise SecurityValidationError(f"{field_name} must have a valid domain")

        # Check for suspicious patterns
        if any(pattern.search(url) for pattern in self.xss_patterns):
            raise SecurityValidationError(f"{field_name} contains suspicious patterns")

        return url

    def validate_filename(self, filename: str) -> str:
        """Validate filename for security."""
        if not filename:
            raise SecurityValidationError("Filename cannot be empty")

        # Check for path traversal
        if any(pattern.search(filename) for pattern in self.path_traversal_patterns):
            raise SecurityValidationError("Filename contains path traversal patterns")

        # Check for invalid characters
        invalid_chars = ["<", ">", ":", '"', "|", "?", "*", "\0"]
        if any(char in filename for char in invalid_chars):
            raise SecurityValidationError("Filename contains invalid characters")

        # Check extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.rules.allowed_file_extensions:
            raise SecurityValidationError(f"File extension {file_ext} not allowed")

        return filename

    async def validate_file_upload(self, file: UploadFile) -> FileValidationResult:
        """Comprehensive file upload validation."""
        issues = []
        warnings = []

        # Basic checks
        if not file.filename:
            raise SecurityValidationError("File must have a filename")

        # Validate filename
        try:
            self.validate_filename(file.filename)
        except SecurityValidationError as e:
            issues.append(str(e))

        # Read file content for analysis
        content = await file.read()
        file_size = len(content)
        await file.seek(0)  # Reset file pointer

        # Size check
        if file_size > self.rules.max_file_size:
            issues.append(f"File size {file_size} exceeds limit {self.rules.max_file_size}")

        # Empty file check
        if file_size == 0:
            issues.append("File is empty")

        # MIME type detection using python-magic
        try:
            detected_type = magic.from_buffer(content, mime=True)
        except Exception:
            detected_type = mimetypes.guess_type(file.filename)[0] or "unknown"
            warnings.append("Could not detect MIME type reliably")

        # Check against blocked types
        if detected_type in self.rules.blocked_file_types:
            issues.append(f"File type {detected_type} is blocked for security")

        # Check against allowed types
        if detected_type not in self.rules.allowed_file_types:
            warnings.append(f"File type {detected_type} is not in allowed list")

        # Check for file type mismatch
        declared_type = file.content_type
        if declared_type and declared_type != detected_type:
            warnings.append(
                f"Declared type {declared_type} differs from detected type {detected_type}",
            )

        # Scan for suspicious content patterns
        content_str = content.decode("utf-8", errors="ignore")

        # Check for embedded scripts in text files
        if detected_type.startswith("text/"):
            for pattern in self.xss_patterns:
                if pattern.search(content_str):
                    issues.append("File contains potential XSS content")
                    break

        # Check for executable signatures
        executable_signatures = [
            b"\x4d\x5a",  # PE executable
            b"\x7f\x45\x4c\x46",  # ELF executable
            b"\xfe\xed\xfa",  # Mach-O
            b"\xca\xfe\xba\xbe",  # Java class file
        ]

        for sig in executable_signatures:
            if content.startswith(sig):
                issues.append("File appears to be executable")
                break

        return FileValidationResult(
            is_valid=len(issues) == 0,
            detected_type=detected_type,
            file_size=file_size,
            security_issues=issues,
            warnings=warnings,
        )

    def validate_json_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JSON input recursively."""
        if not isinstance(data, dict):
            raise SecurityValidationError("Input must be a dictionary")

        def validate_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    key_path = f"{path}.{key}" if path else key
                    # Validate key
                    self.validate_string_input(str(key), f"key at {key_path}")
                    # Validate value recursively
                    validate_recursive(value, key_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    validate_recursive(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                self.validate_string_input(obj, f"value at {path}")

        validate_recursive(data)
        return data

    def sanitize_html_input(self, html: str) -> str:
        """Sanitize HTML input by removing dangerous elements."""
        # This is a basic implementation - consider using libraries like bleach
        # for production-grade HTML sanitization

        # Remove script tags
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)

        # Remove event handlers
        html = re.sub(r'\s*on\w+\s*=\s*[\'"][^\'"]*[\'"]', "", html, flags=re.IGNORECASE)

        # Remove javascript: links
        html = re.sub(r"javascript:", "", html, flags=re.IGNORECASE)

        # Remove dangerous tags
        dangerous_tags = ["iframe", "object", "embed", "form"]
        for tag in dangerous_tags:
            html = re.sub(f"<{tag}[^>]*>.*?</{tag}>", "", html, flags=re.IGNORECASE | re.DOTALL)
            html = re.sub(f"<{tag}[^>]*/?>", "", html, flags=re.IGNORECASE)

        return html


class InputValidator:
    """High-level input validator for common use cases."""

    def __init__(self):
        self.security_validator = SecurityValidator()

    async def validate_migration_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate migration validation request."""
        # Validate JSON structure
        validated_data = self.security_validator.validate_json_input(request_data)

        # Validate specific fields
        if "source_technology" in validated_data:
            validated_data["source_technology"] = self.security_validator.validate_string_input(
                validated_data["source_technology"], "source_technology",
            )

        if "target_technology" in validated_data:
            validated_data["target_technology"] = self.security_validator.validate_string_input(
                validated_data["target_technology"], "target_technology",
            )

        if "validation_scope" in validated_data:
            validated_data["validation_scope"] = self.security_validator.validate_string_input(
                validated_data["validation_scope"], "validation_scope",
            )

        return validated_data

    async def validate_behavioral_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate behavioral validation request."""
        # Validate JSON structure
        validated_data = self.security_validator.validate_json_input(request_data)

        # Validate URLs
        if "source_url" in validated_data:
            validated_data["source_url"] = self.security_validator.validate_url(
                validated_data["source_url"], "source_url",
            )

        if "target_url" in validated_data:
            validated_data["target_url"] = self.security_validator.validate_url(
                validated_data["target_url"], "target_url",
            )

        # Validate scenarios
        if "validation_scenarios" in validated_data:
            scenarios = validated_data["validation_scenarios"]
            if isinstance(scenarios, list):
                validated_scenarios = []
                for scenario in scenarios:
                    validated_scenarios.append(
                        self.security_validator.validate_string_input(scenario, "scenario"),
                    )
                validated_data["validation_scenarios"] = validated_scenarios

        return validated_data

    async def validate_file_uploads(
        self, files: List[UploadFile], max_files: Optional[int] = None,
    ) -> List[Tuple[UploadFile, FileValidationResult]]:
        """Validate multiple file uploads."""
        max_files = max_files or self.security_validator.rules.max_files_per_request

        if len(files) > max_files:
            raise SecurityValidationError(f"Too many files: {len(files)} > {max_files}")

        results = []
        total_size = 0

        for file in files:
            validation_result = await self.security_validator.validate_file_upload(file)
            total_size += validation_result.file_size

            # Check total size limit
            if total_size > self.security_validator.rules.max_file_size * max_files:
                raise SecurityValidationError("Total file size exceeds limit")

            results.append((file, validation_result))

        return results


# Global validator instance
input_validator = InputValidator()
security_validator = SecurityValidator()
