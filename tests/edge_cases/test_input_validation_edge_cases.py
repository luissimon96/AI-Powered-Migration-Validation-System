"""
Edge case testing for input validation in AI-Powered Migration Validation System.

This module contains comprehensive edge case tests for all input validation scenarios,
focusing on boundary conditions, malformed inputs, and error handling robustness.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, invariant, rule

from src.core.input_processor import InputProcessor
from src.core.models import (InputData, InputType, MigrationValidationRequest,
                             TechnologyContext, TechnologyType,
                             ValidationScope)


@pytest.mark.unit
@pytest.mark.property
class TestInputValidationEdgeCases:
    """Comprehensive edge case testing for input validation."""

    def setup_method(self):
        """Setup test environment."""
        self.processor = InputProcessor()

    # ═══════════════════════════════════════════════════════════════
    # File Input Edge Cases
    # ═══════════════════════════════════════════════════════════════

    def test_empty_file_handling(self):
        """Test handling of empty files."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            # Write empty file
            pass

        try:
            input_data = InputData(type=InputType.CODE_FILES, files=[f.name])
            result = self.processor.process_input(input_data)

            assert result is not None
            assert result.get("content", "") == ""
            assert "metadata" in result
            assert result["metadata"]["file_size"] == 0
        finally:
            os.unlink(f.name)

    def test_extremely_large_file_handling(self):
        """Test handling of extremely large files."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            # Write large content (10MB of text)
            large_content = "# Large file content\n" * 500000
            f.write(large_content)

        try:
            input_data = InputData(type=InputType.CODE_FILES, files=[f.name])

            # Should handle gracefully or raise appropriate error
            with pytest.raises((MemoryError, ValueError)) as exc_info:
                self.processor.process_input(input_data)

            assert (
                "too large" in str(exc_info.value).lower()
                or "memory" in str(exc_info.value).lower()
            )
        finally:
            os.unlink(f.name)

    def test_binary_file_rejection(self):
        """Test rejection of binary files."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".exe") as f:
            # Write binary content
            f.write(b"\x00\x01\x02\x03\xFF\xFE\xFD")

        try:
            input_data = InputData(type=InputType.CODE_FILES, files=[f.name])

            with pytest.raises(ValueError) as exc_info:
                self.processor.process_input(input_data)

            assert (
                "binary" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
            )
        finally:
            os.unlink(f.name)

    def test_corrupted_file_handling(self):
        """Test handling of corrupted or malformed files."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            # Write content with various corrupted elements
            corrupted_content = (
                """
            def incomplete_function(
            # Missing closing parenthesis and body

            class IncompleteClass
            # Missing colon and body

            # Invalid Unicode characters: \uFFFE\uFFFF
            invalid_unicode = "\\uFFFE\\uFFFF"

            # Extremely long line that might break parsers
            """
                + "x" * 10000
                + """

            # Unmatched brackets and braces
            unmatched = [[[{{{(((
            """
            )
            f.write(corrupted_content)

        try:
            input_data = InputData(type=InputType.CODE_FILES, files=[f.name])
            result = self.processor.process_input(input_data)

            # Should handle gracefully and report issues
            assert result is not None
            assert "errors" in result or "warnings" in result
        finally:
            os.unlink(f.name)

    def test_nonexistent_file_handling(self):
        """Test handling of nonexistent files."""
        nonexistent_file = "/path/that/does/not/exist/file.py"
        input_data = InputData(type=InputType.CODE_FILES, files=[nonexistent_file])

        with pytest.raises(FileNotFoundError):
            self.processor.process_input(input_data)

    def test_permission_denied_file_handling(self):
        """Test handling of files without read permission."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write("print('test')")

        try:
            # Remove read permission
            os.chmod(f.name, 0o000)

            input_data = InputData(type=InputType.CODE_FILES, files=[f.name])

            with pytest.raises(PermissionError):
                self.processor.process_input(input_data)
        finally:
            # Restore permission for cleanup
            os.chmod(f.name, 0o644)
            os.unlink(f.name)

    # ═══════════════════════════════════════════════════════════════
    # URL Input Edge Cases
    # ═══════════════════════════════════════════════════════════════

    def test_malformed_url_handling(self):
        """Test handling of malformed URLs."""
        malformed_urls = [
            "not-a-url",
            "http://",
            "https://",
            "ftp://invalid",
            "javascript:alert('xss')",
            "file:///etc/passwd",
            "http://user:pass@[::1]:8080/path?query=value#fragment"
            + "x" * 2000,  # Extremely long URL
            "http://localhost:-1/",  # Invalid port
            "http://[invalid-ipv6]/",
            "http://256.256.256.256/",  # Invalid IP
        ]

        for url in malformed_urls:
            input_data = InputData(type=InputType.URL, url=url)

            with pytest.raises(ValueError) as exc_info:
                self.processor.process_input(input_data)

            assert (
                "invalid" in str(exc_info.value).lower()
                or "malformed" in str(exc_info.value).lower()
            )

    def test_url_timeout_handling(self):
        """Test handling of URL connection timeouts."""
        # Use a non-routable IP to simulate timeout
        timeout_url = "http://10.255.255.1/"
        input_data = InputData(type=InputType.URL, url=timeout_url)

        with pytest.raises((ConnectionError, TimeoutError)) as exc_info:
            self.processor.process_input(input_data, timeout=1)

        assert (
            "timeout" in str(exc_info.value).lower() or "connection" in str(exc_info.value).lower()
        )

    # ═══════════════════════════════════════════════════════════════
    # Text Input Edge Cases
    # ═══════════════════════════════════════════════════════════════

    def test_empty_text_handling(self):
        """Test handling of empty text input."""
        input_data = InputData(type=InputType.TEXT, text="")
        result = self.processor.process_input(input_data)

        assert result is not None
        assert result.get("content", "") == ""

    def test_null_text_handling(self):
        """Test handling of null text input."""
        input_data = InputData(type=InputType.TEXT, text=None)

        with pytest.raises(ValueError) as exc_info:
            self.processor.process_input(input_data)

        assert "text" in str(exc_info.value).lower()

    def test_extremely_long_text_handling(self):
        """Test handling of extremely long text input."""
        # 50MB of text
        extremely_long_text = "x" * (50 * 1024 * 1024)
        input_data = InputData(type=InputType.TEXT, text=extremely_long_text)

        with pytest.raises((MemoryError, ValueError)) as exc_info:
            self.processor.process_input(input_data)

        assert (
            "too large" in str(exc_info.value).lower() or "memory" in str(exc_info.value).lower()
        )

    def test_special_character_handling(self):
        """Test handling of text with special characters."""
        special_text = """
        # Unicode test: 你好 🌍 ñáéíóú àèìòù
        # Zero-width characters: \u200B\u200C\u200D\uFEFF
        # Control characters: \x00\x01\x02\x03\x04\x05
        # Emoji sequences: 👨‍👩‍👧‍👦 🏴󠁧󠁢󠁳󠁣󠁴󠁿
        # Mathematical symbols: ∑∏∆∇∂∀∃∈∉⊂⊃⊆⊇
        # Various quotes: "'"'‛""„‚''‹›«»
        """

        input_data = InputData(type=InputType.TEXT, text=special_text)
        result = self.processor.process_input(input_data)

        assert result is not None
        assert "content" in result

    # ═══════════════════════════════════════════════════════════════
    # Property-Based Testing with Hypothesis
    # ═══════════════════════════════════════════════════════════════

    @given(st.text(min_size=0, max_size=10000))
    @example("")  # Explicit empty string test
    @example(" " * 1000)  # Whitespace-only test
    def test_text_input_property_based(self, text_input):
        """Property-based test for text input handling."""
        # Assume reasonable input size to avoid memory issues
        assume(len(text_input.encode("utf-8")) < 1024 * 1024)  # 1MB limit

        input_data = InputData(type=InputType.TEXT, text=text_input)

        try:
            result = self.processor.process_input(input_data)

            # Properties that should always hold
            assert result is not None
            assert isinstance(result, dict)
            assert "content" in result or "error" in result

            if "content" in result:
                # Content should preserve essential characteristics
                assert isinstance(result["content"], str)
                # Non-empty input should produce non-None content
                if text_input.strip():
                    assert result["content"] is not None

        except (ValueError, MemoryError) as e:
            # These exceptions are acceptable for certain inputs
            assert len(text_input.encode("utf-8")) > 10 * 1024 * 1024 or not text_input.strip()

    @given(
        st.lists(
            st.text(min_size=1, max_size=100).filter(lambda x: "/" in x), min_size=1, max_size=10
        )
    )
    def test_file_list_property_based(self, file_paths):
        """Property-based test for file list handling."""
        # Create temporary files based on generated paths
        temp_files = []

        try:
            for i, path_part in enumerate(file_paths):
                with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=f"_{i}.py") as f:
                    f.write(f"# Generated file {i}\ndef function_{i}(): pass")
                    temp_files.append(f.name)

            input_data = InputData(type=InputType.CODE_FILES, files=temp_files)
            result = self.processor.process_input(input_data)

            # Properties that should always hold
            assert result is not None
            assert isinstance(result, dict)

            if "files" in result:
                assert len(result["files"]) <= len(temp_files)

        finally:
            # Cleanup
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except FileNotFoundError:
                    pass

    # ═══════════════════════════════════════════════════════════════
    # Stateful Testing for Complex Scenarios
    # ═══════════════════════════════════════════════════════════════


class InputProcessorStateMachine(RuleBasedStateMachine):
    """Stateful testing for input processor behavior."""

    files = Bundle("files")

    def __init__(self):
        super().__init__()
        self.processor = InputProcessor()
        self.created_files = []

    @rule(target=files, content=st.text(min_size=0, max_size=1000))
    def create_temp_file(self, content):
        """Create a temporary file with given content."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write(content)
            self.created_files.append(f.name)
            return f.name

    @rule(file_path=files)
    def process_file(self, file_path):
        """Process a file and verify basic properties."""
        if os.path.exists(file_path):
            input_data = InputData(type=InputType.CODE_FILES, files=[file_path])

            try:
                result = self.processor.process_input(input_data)
                assert result is not None
                assert isinstance(result, dict)
            except (ValueError, MemoryError, PermissionError):
                # These are acceptable exceptions
                pass

    @rule(file_path=files)
    def delete_file_and_process(self, file_path):
        """Delete a file and then try to process it."""
        if os.path.exists(file_path):
            os.unlink(file_path)

            input_data = InputData(type=InputType.CODE_FILES, files=[file_path])

            with pytest.raises(FileNotFoundError):
                self.processor.process_input(input_data)

    @invariant()
    def processor_remains_functional(self):
        """Invariant: processor should always remain functional."""
        assert self.processor is not None
        assert hasattr(self.processor, "process_input")

    def teardown(self):
        """Cleanup created files."""
        for file_path in self.created_files:
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass


@pytest.mark.property
@pytest.mark.slow
class TestInputProcessorStateful:
    """Stateful testing for input processor."""

    def test_stateful_behavior(self):
        """Run stateful testing for input processor."""
        # Run the state machine
        InputProcessorStateMachine.TestCase().runTest()


# ═══════════════════════════════════════════════════════════════
# Boundary Value Analysis
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestBoundaryValues:
    """Test boundary values for various input parameters."""

    def setup_method(self):
        """Setup test environment."""
        self.processor = InputProcessor()

    @pytest.mark.parametrize(
        "file_size",
        [
            0,  # Empty file
            1,  # Single byte
            1024,  # 1KB
            1024 * 1024,  # 1MB
            10 * 1024 * 1024,  # 10MB (boundary)
            # 100 * 1024 * 1024,  # 100MB (should fail)
        ],
    )
    def test_file_size_boundaries(self, file_size):
        """Test file size boundary conditions."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            content = "x" * file_size
            f.write(content)

        try:
            input_data = InputData(type=InputType.CODE_FILES, files=[f.name])

            if file_size <= 10 * 1024 * 1024:  # 10MB limit
                result = self.processor.process_input(input_data)
                assert result is not None
            else:
                with pytest.raises((MemoryError, ValueError)):
                    self.processor.process_input(input_data)

        finally:
            os.unlink(f.name)

    @pytest.mark.parametrize("num_files", [0, 1, 10, 100, 1000])
    def test_file_count_boundaries(self, num_files):
        """Test file count boundary conditions."""
        temp_files = []

        try:
            for i in range(num_files):
                with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=f"_{i}.py") as f:
                    f.write(f"# File {i}\n")
                    temp_files.append(f.name)

            if num_files == 0:
                # Empty file list should raise error
                input_data = InputData(type=InputType.CODE_FILES, files=[])
                with pytest.raises(ValueError):
                    self.processor.process_input(input_data)
            elif num_files <= 100:
                input_data = InputData(type=InputType.CODE_FILES, files=temp_files)
                result = self.processor.process_input(input_data)
                assert result is not None
            else:
                # Too many files should be handled gracefully or raise appropriate error
                input_data = InputData(type=InputType.CODE_FILES, files=temp_files)
                with pytest.raises((ValueError, MemoryError)):
                    self.processor.process_input(input_data)

        finally:
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except FileNotFoundError:
                    pass


# ═══════════════════════════════════════════════════════════════
# Concurrency and Race Condition Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
@pytest.mark.slow
class TestConcurrencyEdgeCases:
    """Test concurrent access and race conditions."""

    def setup_method(self):
        """Setup test environment."""
        self.processor = InputProcessor()

    def test_concurrent_file_processing(self):
        """Test concurrent processing of the same file."""
        import threading
        import time

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write("def test_function(): pass")

        results = []
        errors = []

        def process_file():
            try:
                input_data = InputData(type=InputType.CODE_FILES, files=[f.name])
                result = self.processor.process_input(input_data)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=process_file)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        try:
            # All should succeed or fail consistently
            assert len(errors) == 0 or len(results) == 0
            if results:
                # All results should be consistent
                first_result = results[0]
                for result in results[1:]:
                    assert result == first_result

        finally:
            os.unlink(f.name)

    def test_file_modification_during_processing(self):
        """Test file modification while being processed."""
        import threading
        import time

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write("def original_function(): pass")

        result = None
        error = None

        def process_file():
            nonlocal result, error
            try:
                input_data = InputData(type=InputType.CODE_FILES, files=[f.name])
                time.sleep(0.1)  # Allow time for modification
                result = self.processor.process_input(input_data)
            except Exception as e:
                error = e

        def modify_file():
            time.sleep(0.05)  # Start modification after processing begins
            with open(f.name, "w") as file:
                file.write("def modified_function(): pass")

        # Start both threads
        process_thread = threading.Thread(target=process_file)
        modify_thread = threading.Thread(target=modify_file)

        process_thread.start()
        modify_thread.start()

        process_thread.join()
        modify_thread.join()

        try:
            # Should handle gracefully (either succeed or fail with appropriate error)
            assert result is not None or error is not None
            if error:
                assert isinstance(error, (OSError, ValueError))

        finally:
            os.unlink(f.name)
