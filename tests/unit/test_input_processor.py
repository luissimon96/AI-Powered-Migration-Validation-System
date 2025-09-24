"""Unit tests for input processor."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from src.core.input_processor import InputProcessor
from src.core.models import InputData, InputType, TechnologyType


@pytest.mark.unit
class TestInputProcessor:
    """Test InputProcessor component."""

    def test_processor_initialization(self):
        """Test processor initialization."""
        processor = InputProcessor()
        assert processor is not None

    def test_process_code_files(self, temp_files):
        """Test processing code files."""
        processor = InputProcessor()

        input_data = InputData(
            type=InputType.CODE_FILES, files=[temp_files["source_file"]]
        )

        result = processor.process_input(input_data)

        assert result is not None
        assert "code_content" in result
        assert len(result["code_content"]) > 0

    def test_process_nonexistent_files(self):
        """Test processing nonexistent files."""
        processor = InputProcessor()

        input_data = InputData(type=InputType.CODE_FILES, files=["nonexistent.py"])

        with pytest.raises(FileNotFoundError):
            processor.process_input(input_data)

    def test_process_screenshots(self):
        """Test processing screenshots."""
        processor = InputProcessor()

        # Create mock screenshot file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"mock image data")
            screenshot_path = f.name

        try:
            input_data = InputData(
                type=InputType.SCREENSHOTS, screenshots=[screenshot_path]
            )

            result = processor.process_input(input_data)

            assert result is not None
            assert "image_data" in result
        finally:
            os.unlink(screenshot_path)

    def test_process_urls(self):
        """Test processing URLs."""
        processor = InputProcessor()

        input_data = InputData(type=InputType.URL, urls=["http://example.com"])

        with patch("src.core.input_processor.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = "<html><body>Test</body></html>"
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = processor.process_input(input_data)

            assert result is not None
            assert "html_content" in result

    def test_process_hybrid_input(self, temp_files):
        """Test processing hybrid input types."""
        processor = InputProcessor()

        input_data = InputData(
            type=InputType.HYBRID,
            files=[temp_files["source_file"]],
            urls=["http://example.com"],
            validation_scenarios=["test_scenario"],
        )

        with patch("src.core.input_processor.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = "<html><body>Test</body></html>"
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = processor.process_input(input_data)

            assert result is not None
            assert "code_content" in result
            assert "html_content" in result
            assert "scenarios" in result

    def test_extract_metadata_from_code(self, sample_python_code):
        """Test extracting metadata from code."""
        processor = InputProcessor()

        metadata = processor.extract_code_metadata(
            sample_python_code, TechnologyType.PYTHON_FLASK
        )

        assert metadata is not None
        assert "functions" in metadata
        assert "classes" in metadata
        assert len(metadata["functions"]) > 0
        assert len(metadata["classes"]) > 0

    def test_validate_file_types(self):
        """Test file type validation."""
        processor = InputProcessor()

        # Valid file types
        assert processor.validate_file_type("test.py", [".py", ".java"])
        assert processor.validate_file_type("test.java", [".py", ".java"])

        # Invalid file types
        assert not processor.validate_file_type("test.txt", [".py", ".java"])
        assert not processor.validate_file_type("test", [".py", ".java"])

    def test_sanitize_input_data(self):
        """Test input data sanitization."""
        processor = InputProcessor()

        malicious_code = """
        import os
        os.system('rm -rf /')
        """

        sanitized = processor.sanitize_code_input(malicious_code)

        # Should detect and flag dangerous operations
        assert "security_warnings" in sanitized
        assert len(sanitized["security_warnings"]) > 0

    def test_process_empty_input(self):
        """Test processing empty input."""
        processor = InputProcessor()

        input_data = InputData(type=InputType.CODE_FILES, files=[])

        with pytest.raises(ValueError, match="No input files provided"):
            processor.process_input(input_data)

    def test_process_large_files(self):
        """Test processing large files with size limits."""
        processor = InputProcessor()

        # Create large temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            # Write 10MB of content
            large_content = "# " + "x" * (10 * 1024 * 1024)
            f.write(large_content)
            large_file_path = f.name

        try:
            input_data = InputData(type=InputType.CODE_FILES, files=[large_file_path])

            # Should handle large files gracefully
            result = processor.process_input(
                input_data,
                max_file_size=5 * 1024 * 1024,
            )  # 5MB limit

            assert "size_warning" in result
        finally:
            os.unlink(large_file_path)


@pytest.mark.unit
class TestInputProcessorUtils:
    """Test InputProcessor utility functions."""

    def test_detect_programming_language(self):
        """Test programming language detection."""
        processor = InputProcessor()

        # Test Python detection
        python_code = "def hello(): print('world')"
        assert processor.detect_language(python_code, "test.py") == "python"

        # Test Java detection
        java_code = "public class Test { public static void main() {} }"
        assert processor.detect_language(java_code, "Test.java") == "java"

        # Test JavaScript detection
        js_code = "function test() { console.log('test'); }"
        assert processor.detect_language(js_code, "test.js") == "javascript"

    def test_extract_imports_and_dependencies(self):
        """Test extracting imports and dependencies."""
        processor = InputProcessor()

        python_code = """
        import os
        from datetime import datetime
        import requests
        """

        dependencies = processor.extract_dependencies(python_code, "python")

        assert "os" in dependencies
        assert "datetime" in dependencies
        assert "requests" in dependencies

    def test_calculate_complexity_metrics(self, sample_python_code):
        """Test calculating code complexity metrics."""
        processor = InputProcessor()

        metrics = processor.calculate_complexity(sample_python_code, "python")

        assert "cyclomatic_complexity" in metrics
        assert "lines_of_code" in metrics
        assert "number_of_functions" in metrics
        assert "number_of_classes" in metrics
        assert metrics["lines_of_code"] > 0
