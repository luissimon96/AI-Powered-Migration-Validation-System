"""
Input processor for handling structured migration validation requests.

Implements the input interface described in the proposal:
- Technology selection (source/target)
- Validation scope definition
- File/screenshot upload handling
- Request validation and preprocessing
"""

import mimetypes
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import (InputData, InputType, MigrationValidationRequest,
                     TechnologyContext, TechnologyType, ValidationScope)


class InputProcessor:
    """Processes and validates migration validation inputs."""

    def __init__(self, upload_dir: Optional[str] = None):
        """
        Initialize input processor.

        Args:
            upload_dir: Directory for storing uploaded files. If None, uses temp directory.
        """
        self.upload_dir = upload_dir or tempfile.mkdtemp(prefix="migration_validation_")
        self.max_file_size = 10 * 1024 * 1024  # 10MB per file
        self.max_total_size = 100 * 1024 * 1024  # 100MB total
        self.allowed_code_extensions = {
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".java",
            ".cs",
            ".php",
            ".html",
            ".htm",
            ".css",
            ".scss",
            ".sass",
            ".less",
            ".vue",
            ".rb",
            ".go",
            ".rs",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
        }
        self.allowed_image_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".tiff",
            ".webp",
        }

        # Ensure upload directory exists
        os.makedirs(self.upload_dir, exist_ok=True)

    def create_validation_request(
        self,
        source_technology: str,
        target_technology: str,
        validation_scope: str,
        source_files: List[str] = None,
        source_screenshots: List[str] = None,
        target_files: List[str] = None,
        target_screenshots: List[str] = None,
        source_tech_version: Optional[str] = None,
        target_tech_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MigrationValidationRequest:
        """
        Create a structured validation request from user inputs.

        Args:
            source_technology: Source technology string (e.g., "python-flask")
            target_technology: Target technology string (e.g., "java-spring")
            validation_scope: Validation scope string (e.g., "full_system")
            source_files: List of source code file paths
            source_screenshots: List of source screenshot paths
            target_files: List of target code file paths
            target_screenshots: List of target screenshot paths
            source_tech_version: Optional source technology version
            target_tech_version: Optional target technology version
            metadata: Optional additional metadata

        Returns:
            Validated migration request

        Raises:
            ValueError: If input parameters are invalid
        """
        # Parse and validate technology types
        try:
            source_tech_type = TechnologyType(source_technology)
        except ValueError:
            raise ValueError(
                f"Unsupported source technology: {source_technology}. "
                f"Supported: {[t.value for t in TechnologyType]}"
            )

        try:
            target_tech_type = TechnologyType(target_technology)
        except ValueError:
            raise ValueError(
                f"Unsupported target technology: {target_technology}. "
                f"Supported: {[t.value for t in TechnologyType]}"
            )

        # Parse and validate validation scope
        try:
            scope = ValidationScope(validation_scope)
        except ValueError:
            raise ValueError(
                f"Unsupported validation scope: {validation_scope}. "
                f"Supported: {[s.value for s in ValidationScope]}"
            )

        # Validate and process input files
        source_input = self._process_input_data(
            source_files or [], source_screenshots or [], "source"
        )

        target_input = self._process_input_data(
            target_files or [], target_screenshots or [], "target"
        )

        # Create technology contexts
        source_context = TechnologyContext(
            type=source_tech_type,
            version=source_tech_version,
            framework_details=(
                metadata.get("source_framework_details", {}) if metadata else {}
            ),
        )

        target_context = TechnologyContext(
            type=target_tech_type,
            version=target_tech_version,
            framework_details=(
                metadata.get("target_framework_details", {}) if metadata else {}
            ),
        )

        # Create and return request
        request = MigrationValidationRequest(
            source_technology=source_context,
            target_technology=target_context,
            validation_scope=scope,
            source_input=source_input,
            target_input=target_input,
        )

        return request

    def _process_input_data(
        self, files: List[str], screenshots: List[str], context: str
    ) -> InputData:
        """
        Process and validate input data.

        Args:
            files: List of file paths
            screenshots: List of screenshot paths
            context: Context string for error messages ("source" or "target")

        Returns:
            Processed input data

        Raises:
            ValueError: If input data is invalid
        """
        # Validate files exist and are readable
        validated_files = []
        for file_path in files:
            if not file_path or not file_path.strip():
                continue

            if not os.path.exists(file_path):
                raise ValueError(f"{context.title()} file not found: {file_path}")

            if not os.path.isfile(file_path):
                raise ValueError(f"{context.title()} path is not a file: {file_path}")

            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                raise ValueError(
                    f"{context.title()} file too large: {file_path} "
                    f"({file_size} bytes, max {self.max_file_size})"
                )

            # Check file extension
            _, ext = os.path.splitext(file_path.lower())
            if ext not in self.allowed_code_extensions:
                raise ValueError(
                    f"{context.title()} file has unsupported extension: {file_path} "
                    f"(supported: {self.allowed_code_extensions})"
                )

            validated_files.append(file_path)

        # Validate screenshots exist and are readable
        validated_screenshots = []
        for screenshot_path in screenshots:
            if not screenshot_path or not screenshot_path.strip():
                continue

            if not os.path.exists(screenshot_path):
                raise ValueError(
                    f"{context.title()} screenshot not found: {screenshot_path}"
                )

            if not os.path.isfile(screenshot_path):
                raise ValueError(
                    f"{context.title()} screenshot path is not a file: {screenshot_path}"
                )

            # Check file size
            file_size = os.path.getsize(screenshot_path)
            if file_size > self.max_file_size:
                raise ValueError(
                    f"{context.title()} screenshot too large: {screenshot_path} "
                    f"({file_size} bytes, max {self.max_file_size})"
                )

            # Check file extension
            _, ext = os.path.splitext(screenshot_path.lower())
            if ext not in self.allowed_image_extensions:
                raise ValueError(
                    f"{context.title()} screenshot has unsupported extension: {screenshot_path} "
                    f"(supported: {self.allowed_image_extensions})"
                )

            validated_screenshots.append(screenshot_path)

        # Check total size
        total_size = sum(
            os.path.getsize(f) for f in validated_files + validated_screenshots
        )
        if total_size > self.max_total_size:
            raise ValueError(
                f"{context.title()} total file size too large: {total_size} bytes "
                f"(max {self.max_total_size})"
            )

        # Determine input type
        if validated_files and validated_screenshots:
            input_type = InputType.HYBRID
        elif validated_files:
            input_type = InputType.CODE_FILES
        elif validated_screenshots:
            input_type = InputType.SCREENSHOTS
        else:
            raise ValueError(
                f"{context.title()} input is empty - provide files or screenshots"
            )

        return InputData(
            type=input_type,
            files=validated_files,
            screenshots=validated_screenshots,
            metadata={
                "total_files": len(validated_files),
                "total_screenshots": len(validated_screenshots),
                "total_size_bytes": total_size,
            },
        )

    def upload_files(
        self, uploaded_files: List[Tuple[str, bytes]], context: str = "upload"
    ) -> List[str]:
        """
        Handle file uploads and save them to upload directory.

        Args:
            uploaded_files: List of (filename, file_content) tuples
            context: Context for organizing files

        Returns:
            List of saved file paths

        Raises:
            ValueError: If upload fails validation
        """
        saved_paths = []
        context_dir = os.path.join(self.upload_dir, context)
        os.makedirs(context_dir, exist_ok=True)

        for filename, content in uploaded_files:
            # Validate filename
            if not filename or ".." in filename or "/" in filename or "\\" in filename:
                raise ValueError(f"Invalid filename: {filename}")

            # Check file size
            if len(content) > self.max_file_size:
                raise ValueError(f"File too large: {filename} ({len(content)} bytes)")

            # Check extension
            _, ext = os.path.splitext(filename.lower())
            if ext not in (
                self.allowed_code_extensions | self.allowed_image_extensions
            ):
                raise ValueError(f"Unsupported file type: {filename}")

            # Save file
            file_path = os.path.join(context_dir, filename)

            # Handle filename conflicts
            counter = 1
            original_path = file_path
            while os.path.exists(file_path):
                name, ext = os.path.splitext(original_path)
                file_path = f"{name}_{counter}{ext}"
                counter += 1

            with open(file_path, "wb") as f:
                f.write(content)

            saved_paths.append(file_path)

        return saved_paths

    def cleanup_uploads(self, file_paths: List[str]):
        """
        Clean up uploaded files.

        Args:
            file_paths: List of file paths to clean up
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Warning: Failed to clean up file {file_path}: {e}")

    def get_technology_options(self) -> Dict[str, Any]:
        """Get available technology options for UI."""
        return {
            "source_technologies": [
                {"value": tech.value, "label": self._format_tech_label(tech.value)}
                for tech in TechnologyType
            ],
            "target_technologies": [
                {"value": tech.value, "label": self._format_tech_label(tech.value)}
                for tech in TechnologyType
            ],
            "validation_scopes": [
                {"value": scope.value, "label": self._format_scope_label(scope.value)}
                for scope in ValidationScope
            ],
            "input_types": [
                {
                    "value": input_type.value,
                    "label": self._format_input_type_label(input_type.value),
                }
                for input_type in InputType
            ],
        }

    def _format_tech_label(self, tech_value: str) -> str:
        """Format technology value for display."""
        return tech_value.replace("-", " ").replace("_", " ").title()

    def _format_scope_label(self, scope_value: str) -> str:
        """Format validation scope for display."""
        labels = {
            "ui_layout": "UI Layout & Design",
            "backend_functionality": "Backend Functionality",
            "data_structure": "Data Structure & Models",
            "api_endpoints": "API Endpoints",
            "business_logic": "Business Logic",
            "full_system": "Full System Validation",
        }
        return labels.get(scope_value, scope_value.replace("_", " ").title())

    def _format_input_type_label(self, input_type_value: str) -> str:
        """Format input type for display."""
        labels = {
            "code_files": "Code Files Only",
            "screenshots": "Screenshots Only",
            "hybrid": "Code Files + Screenshots",
        }
        return labels.get(input_type_value, input_type_value.replace("_", " ").title())

    def validate_technology_compatibility(
        self, source_tech: str, target_tech: str, scope: str
    ) -> Dict[str, Any]:
        """
        Validate that technology combination is supported for the given scope.

        Args:
            source_tech: Source technology value
            target_tech: Target technology value
            scope: Validation scope value

        Returns:
            Compatibility assessment
        """
        warnings = []
        issues = []

        # Check for known problematic combinations
        problematic_combinations = [
            # Add known issues here, e.g.:
            # (("python-flask", "java-spring"), "Complex framework differences may affect validation accuracy"),
        ]

        for (source, target), warning in problematic_combinations:
            if source_tech == source and target_tech == target:
                warnings.append(warning)

        # Check scope compatibility
        frontend_techs = [
            "javascript-react",
            "javascript-vue",
            "javascript-angular",
            "typescript-react",
            "typescript-vue",
            "typescript-angular",
        ]
        backend_techs = [
            "python-flask",
            "python-django",
            "java-spring",
            "csharp-dotnet",
            "php-laravel",
        ]

        if scope == "ui_layout":
            if source_tech not in frontend_techs and target_tech not in frontend_techs:
                warnings.append("UI validation works best with frontend technologies")

        if scope == "backend_functionality":
            if source_tech not in backend_techs and target_tech not in backend_techs:
                warnings.append(
                    "Backend validation works best with backend technologies"
                )

        return {"compatible": len(issues) == 0, "issues": issues, "warnings": warnings}
