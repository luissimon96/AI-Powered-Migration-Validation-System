"""
Enhanced end-to-end pipeline tests for T002 completion.
Comprehensive validation pipeline testing with error scenarios.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.analyzers.code_analyzer import CodeAnalyzer
from src.analyzers.visual_analyzer import VisualAnalyzer
from src.comparators.semantic_comparator import SemanticComparator
from src.core.migration_validator import MigrationValidator
from src.core.models import (ValidationRequest, ValidationScope,
                             ValidationStatus)
from src.services.llm_service import LLMService


@pytest.mark.integration
@pytest.mark.asyncio
class TestEnhancedE2EPipeline:
    """Enhanced end-to-end pipeline tests."""

    async def test_complete_migration_validation_workflow(self, sample_files, mock_llm_service):
        """Test complete migration validation workflow with real components."""
        validator = MigrationValidator(llm_client=mock_llm_service)
        
        # Create comprehensive validation request
        request = ValidationRequest(
            source_technology="python-flask",
            target_technology="java-spring",
            validation_scope=ValidationScope.FULL_SYSTEM,
            source_tech_version="2.0",
            target_tech_version="3.0",
            source_files=sample_files["python"],
            target_files=sample_files["java"],
            screenshots=sample_files.get("screenshots", [])
        )
        
        # Execute full pipeline
        session = await validator.validate_migration(request)
        
        # Verify session structure
        assert session.request == request
        assert session.result is not None
        assert session.source_representation is not None
        assert session.target_representation is not None
        assert len(session.processing_log) > 0
        
        # Verify analysis results
        assert session.result.overall_status in [
            ValidationStatus.APPROVED,
            ValidationStatus.APPROVED_WITH_WARNINGS,
            ValidationStatus.REJECTED
        ]
        assert 0.0 <= session.result.fidelity_score <= 1.0
        assert isinstance(session.result.differences_found, list)
        
        # Verify processing stages completed
        log_messages = [log.message for log in session.processing_log]
        expected_stages = [
            "code_analysis_started",
            "visual_analysis_started", 
            "semantic_comparison_started",
            "validation_completed"
        ]
        
        for stage in expected_stages:
            assert any(stage in msg for msg in log_messages)

    async def test_multi_technology_validation_pipeline(self, mock_llm_service):
        """Test pipeline with multiple technology combinations."""
        validator = MigrationValidator(llm_client=mock_llm_service)
        
        technology_pairs = [
            ("python-django", "java-spring"),
            ("javascript-react", "typescript-angular"),
            ("php-laravel", "python-django"),
            ("java-spring", "nodejs-express")
        ]
        
        for source_tech, target_tech in technology_pairs:
            request = ValidationRequest(
                source_technology=source_tech,
                target_technology=target_tech,
                validation_scope=ValidationScope.BUSINESS_LOGIC,
                source_files=[{"name": "test.py", "content": "def test(): pass"}],
                target_files=[{"name": "Test.java", "content": "public void test() {}"}]
            )
            
            session = await validator.validate_migration(request)
            
            assert session.result is not None
            assert session.result.overall_status is not None
            assert len(session.processing_log) > 0

    async def test_pipeline_with_large_file_sets(self, mock_llm_service):
        """Test pipeline with large sets of files."""
        validator = MigrationValidator(llm_client=mock_llm_service)
        
        # Create large file sets
        source_files = []
        target_files = []
        
        for i in range(20):
            source_files.append({
                "name": f"module_{i}.py",
                "content": f"def function_{i}(): return {i}"
            })
            target_files.append({
                "name": f"Module{i}.java", 
                "content": f"public int function{i}() {{ return {i}; }}"
            })
        
        request = ValidationRequest(
            source_technology="python-flask",
            target_technology="java-spring",
            validation_scope=ValidationScope.FULL_SYSTEM,
            source_files=source_files,
            target_files=target_files
        )
        
        # Execute pipeline
        start_time = datetime.utcnow()
        session = await validator.validate_migration(request)
        end_time = datetime.utcnow()
        
        # Verify performance
        duration = (end_time - start_time).total_seconds()
        assert duration < 30.0  # Should complete within 30 seconds
        
        # Verify results
        assert session.result is not None
        assert len(session.source_representation.analyzed_files) == 20
        assert len(session.target_representation.analyzed_files) == 20

    async def test_pipeline_error_recovery(self):
        """Test pipeline error recovery mechanisms."""
        # Test with failing LLM service
        failing_llm = Mock()
        failing_llm.generate_response = AsyncMock(side_effect=Exception("LLM service unavailable"))
        
        validator = MigrationValidator(llm_client=failing_llm)
        
        request = ValidationRequest(
            source_technology="python-flask",
            target_technology="java-spring",
            validation_scope=ValidationScope.BUSINESS_LOGIC,
            source_files=[{"name": "test.py", "content": "def test(): pass"}],
            target_files=[{"name": "Test.java", "content": "public void test() {}"}]
        )
        
        # Should complete with fallback mechanisms
        session = await validator.validate_migration(request)
        
        assert session.result is not None
        assert session.result.overall_status in [
            ValidationStatus.REJECTED,
            ValidationStatus.ERROR
        ]
        
        # Verify error logged
        error_logs = [log for log in session.processing_log if log.level == "ERROR"]
        assert len(error_logs) > 0

    async def test_concurrent_validation_requests(self, mock_llm_service):
        """Test concurrent validation requests."""
        validator = MigrationValidator(llm_client=mock_llm_service)
        
        # Create multiple validation requests
        requests = []
        for i in range(5):
            request = ValidationRequest(
                source_technology="python-flask",
                target_technology="java-spring",
                validation_scope=ValidationScope.BUSINESS_LOGIC,
                source_files=[{"name": f"test{i}.py", "content": f"def test{i}(): return {i}"}],
                target_files=[{"name": f"Test{i}.java", "content": f"public int test{i}() {{ return {i}; }}"}]
            )
            requests.append(request)
        
        # Execute concurrently
        tasks = [validator.validate_migration(req) for req in requests]
        sessions = await asyncio.gather(*tasks)
        
        # Verify all completed successfully
        assert len(sessions) == 5
        for session in sessions:
            assert session.result is not None
            assert session.result.overall_status is not None

    async def test_visual_analysis_integration(self, mock_llm_service):
        """Test visual analysis integration in pipeline."""
        validator = MigrationValidator(llm_client=mock_llm_service)
        
        # Mock screenshot files
        screenshot_files = [
            {"name": "source_ui.png", "content": b"fake_png_data", "type": "image/png"},
            {"name": "target_ui.png", "content": b"fake_png_data", "type": "image/png"}
        ]
        
        request = ValidationRequest(
            source_technology="javascript-react",
            target_technology="typescript-angular", 
            validation_scope=ValidationScope.USER_INTERFACE,
            source_files=[{"name": "App.jsx", "content": "function App() { return <div>Hello</div>; }"}],
            target_files=[{"name": "app.component.ts", "content": "export class AppComponent { }"}],
            screenshots=screenshot_files
        )
        
        with patch('src.analyzers.visual_analyzer.VisualAnalyzer.analyze_screenshots') as mock_visual:
            mock_visual.return_value = {
                "ui_elements": ["button", "form", "navigation"],
                "layout_similarity": 0.85,
                "accessibility_score": 0.9
            }
            
            session = await validator.validate_migration(request)
            
            # Verify visual analysis was called
            mock_visual.assert_called_once()
            
            # Verify visual results included
            assert session.target_representation.visual_analysis is not None
            assert "ui_elements" in session.target_representation.visual_analysis

    async def test_behavioral_validation_integration(self, mock_llm_service):
        """Test behavioral validation integration."""
        validator = MigrationValidator(llm_client=mock_llm_service)
        
        request = ValidationRequest(
            source_technology="python-flask",
            target_technology="java-spring",
            validation_scope=ValidationScope.BEHAVIORAL_VALIDATION,
            source_files=[{"name": "api.py", "content": "def get_users(): return users"}],
            target_files=[{"name": "UserController.java", "content": "public List<User> getUsers() { return users; }"}]
        )
        
        with patch('src.services.crew_service.CrewService.execute_behavioral_validation') as mock_crew:
            mock_crew.return_value = {
                "behavioral_match": True,
                "confidence": 0.92,
                "issues": []
            }
            
            session = await validator.validate_migration(request)
            
            # Verify behavioral validation was executed
            mock_crew.assert_called_once()
            
            # Verify results include behavioral analysis
            assert hasattr(session.result, 'behavioral_analysis')

    async def test_memory_usage_optimization(self, mock_llm_service):
        """Test memory usage optimization for large validations."""
        validator = MigrationValidator(llm_client=mock_llm_service)
        
        # Create memory-intensive request
        large_files = []
        for i in range(100):
            large_content = "# Large file content\n" + "def function(): pass\n" * 1000
            large_files.append({
                "name": f"large_file_{i}.py",
                "content": large_content
            })
        
        request = ValidationRequest(
            source_technology="python-flask",
            target_technology="java-spring",
            validation_scope=ValidationScope.CODE_STRUCTURE,
            source_files=large_files[:50],
            target_files=large_files[50:]
        )
        
        # Monitor memory usage during validation
        import os

        import psutil
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        session = await validator.validate_migration(request)
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB
        
        # Memory increase should be reasonable (< 500MB)
        assert memory_increase < 500
        assert session.result is not None


@pytest.mark.integration
class TestPipelineErrorScenarios:
    """Test comprehensive error scenarios."""

    async def test_malformed_file_handling(self, mock_llm_service):
        """Test handling of malformed files."""
        validator = MigrationValidator(llm_client=mock_llm_service)
        
        request = ValidationRequest(
            source_technology="python-flask",
            target_technology="java-spring",
            validation_scope=ValidationScope.BUSINESS_LOGIC,
            source_files=[{"name": "malformed.py", "content": "def incomplete_function("}],  # Malformed
            target_files=[{"name": "Valid.java", "content": "public void valid() {}"}]
        )
        
        session = await validator.validate_migration(request)
        
        # Should handle gracefully
        assert session.result is not None
        assert session.result.overall_status in [ValidationStatus.REJECTED, ValidationStatus.APPROVED_WITH_WARNINGS]
        
        # Should have error logs
        error_logs = [log for log in session.processing_log if "malformed" in log.message.lower()]
        assert len(error_logs) > 0

    async def test_timeout_handling(self, mock_llm_service):
        """Test timeout handling for long-running operations."""
        # Mock slow LLM service
        slow_llm = Mock()
        slow_llm.generate_response = AsyncMock(side_effect=asyncio.TimeoutError("Operation timed out"))
        
        validator = MigrationValidator(llm_client=slow_llm)
        
        request = ValidationRequest(
            source_technology="python-flask",
            target_technology="java-spring",
            validation_scope=ValidationScope.BUSINESS_LOGIC,
            source_files=[{"name": "test.py", "content": "def test(): pass"}],
            target_files=[{"name": "Test.java", "content": "public void test() {}"}]
        )
        
        session = await validator.validate_migration(request)
        
        # Should complete with timeout handling
        assert session.result is not None
        timeout_logs = [log for log in session.processing_log if "timeout" in log.message.lower()]
        assert len(timeout_logs) > 0

    async def test_resource_exhaustion_recovery(self, mock_llm_service):
        """Test recovery from resource exhaustion."""
        validator = MigrationValidator(llm_client=mock_llm_service)
        
        # Mock memory error
        with patch('src.analyzers.code_analyzer.CodeAnalyzer.analyze') as mock_analyze:
            mock_analyze.side_effect = MemoryError("Out of memory")
            
            request = ValidationRequest(
                source_technology="python-flask",
                target_technology="java-spring",
                validation_scope=ValidationScope.BUSINESS_LOGIC,
                source_files=[{"name": "test.py", "content": "def test(): pass"}],
                target_files=[{"name": "Test.java", "content": "public void test() {}"}]
            )
            
            session = await validator.validate_migration(request)
            
            # Should handle gracefully
            assert session.result is not None
            assert session.result.overall_status == ValidationStatus.ERROR
            
            memory_logs = [log for log in session.processing_log if "memory" in log.message.lower()]
            assert len(memory_logs) > 0