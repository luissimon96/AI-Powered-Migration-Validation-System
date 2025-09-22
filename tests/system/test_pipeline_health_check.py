"""
System health check tests for the complete AI Migration Validation pipeline.

Tests system dependencies, configuration, and overall health of the pipeline.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.core.migration_validator import MigrationValidator
from src.behavioral.crews import create_behavioral_validation_crew
from src.services.llm_service import LLMService
from src.reporters.validation_reporter import ValidationReporter


@pytest.mark.system
class TestSystemHealthCheck:
    """Test overall system health and configuration."""

    def test_system_dependencies_availability(self):
        """Test that all required system dependencies are available."""
        # Test core dependencies
        try:
            import fastapi
            import pydantic
            import structlog
            import crewai
            assert True, "Core dependencies available"
        except ImportError as e:
            pytest.fail(f"Core dependency missing: {e}")

        # Test optional behavioral dependencies
        try:
            from playwright.async_api import async_playwright
            playwright_available = True
        except ImportError:
            playwright_available = False

        try:
            from browser_use.browser import Browser as BrowserUseAgent
            browser_use_available = True
        except ImportError:
            browser_use_available = False

        # Log availability status
        print(f"Playwright available: {playwright_available}")
        print(f"Browser-use available: {browser_use_available}")

        # At least one browser automation should be available for behavioral validation
        if not (playwright_available or browser_use_available):
            pytest.skip("No browser automation dependencies available")

    def test_llm_service_configuration(self):
        """Test LLM service configuration and initialization."""
        from src.services.llm_service import LLMConfig, LLMProvider

        # Test basic configuration
        config = LLMConfig()
        assert config.provider is not None
        assert config.model is not None
        assert config.max_tokens > 0
        assert config.temperature >= 0.0

        # Test service initialization
        llm_service = LLMService(config)
        assert llm_service.config == config

        # Test provider validation
        valid_providers = [provider.value for provider in LLMProvider]
        assert config.provider in valid_providers

    def test_migration_validator_initialization(self):
        """Test migration validator can be initialized properly."""
        mock_llm_service = MagicMock()
        validator = MigrationValidator(llm_client=mock_llm_service)

        assert validator.llm_client == mock_llm_service
        assert hasattr(validator, 'validate_migration')
        assert hasattr(validator, 'validate_request')

    def test_behavioral_crew_initialization(self):
        """Test behavioral validation crew can be initialized."""
        mock_llm_service = MagicMock()
        crew = create_behavioral_validation_crew(mock_llm_service)

        assert crew is not None
        assert crew.llm_service == mock_llm_service
        assert hasattr(crew, 'validate_migration')
        assert hasattr(crew, 'source_explorer')
        assert hasattr(crew, 'target_executor')
        assert hasattr(crew, 'comparison_judge')
        assert hasattr(crew, 'report_manager')

    def test_validation_reporter_initialization(self):
        """Test validation reporter can be initialized."""
        reporter = ValidationReporter()

        assert reporter is not None
        assert hasattr(reporter, 'generate_report')
        assert hasattr(reporter, 'generate_unified_report')
        assert hasattr(reporter, 'generate_json_report')
        assert hasattr(reporter, 'generate_html_report')
        assert hasattr(reporter, 'generate_markdown_report')

    @pytest.mark.asyncio
    async def test_browser_automation_availability(self):
        """Test browser automation system availability."""
        try:
            from src.behavioral.browser_automation import BrowserAutomationEngine

            engine = BrowserAutomationEngine(headless=True)
            initialization_success = await engine.initialize()

            if initialization_success:
                assert engine.playwright is not None
                assert engine.browser is not None
                assert engine.context is not None
                await engine.cleanup()
                print("Browser automation fully functional")
            else:
                print("Browser automation not available in this environment")
                pytest.skip("Browser automation not available")

        except ImportError:
            pytest.skip("Browser automation dependencies not installed")

    def test_api_application_creation(self):
        """Test API application can be created successfully."""
        from src.api.routes import create_app

        app = create_app()
        assert app is not None
        assert hasattr(app, 'router')

        # Check that key endpoints are registered
        routes = [route.path for route in app.routes]
        expected_endpoints = [
            "/",
            "/health",
            "/api/technologies",
            "/api/validate",
            "/api/behavioral/validate"
        ]

        for endpoint in expected_endpoints:
            assert any(endpoint in route for route in routes), f"Missing endpoint: {endpoint}"


@pytest.mark.system
@pytest.mark.asyncio
class TestSystemIntegrationHealth:
    """Test system integration health across components."""

    async def test_static_validation_pipeline_health(self):
        """Test static validation pipeline health."""
        from src.core.models import (
            MigrationValidationRequest,
            TechnologyContext,
            TechnologyType,
            ValidationScope,
            InputData,
            InputType
        )

        mock_llm_service = AsyncMock()
        mock_llm_service.analyze_code_semantic_similarity.return_value = {
            "similarity_score": 0.9,
            "functionally_equivalent": True
        }

        validator = MigrationValidator(llm_client=mock_llm_service)

        # Create minimal test request
        request = MigrationValidationRequest(
            source_technology=TechnologyContext(
                type=TechnologyType.PYTHON_FLASK,
                version="2.0"
            ),
            target_technology=TechnologyContext(
                type=TechnologyType.JAVA_SPRING,
                version="3.0"
            ),
            validation_scope=ValidationScope.BUSINESS_LOGIC,
            source_input=InputData(
                type=InputType.CODE_FILES,
                files=[]
            ),
            target_input=InputData(
                type=InputType.CODE_FILES,
                files=[]
            )
        )

        # Test validation request validation
        validation_check = await validator.validate_request(request)
        assert validation_check is not None
        assert "valid" in validation_check

    async def test_behavioral_validation_pipeline_health(self):
        """Test behavioral validation pipeline health."""
        from src.behavioral.crews import BehavioralValidationRequest

        mock_llm_service = AsyncMock()
        crew = create_behavioral_validation_crew(mock_llm_service)

        request = BehavioralValidationRequest(
            source_url="https://test-source.example.com",
            target_url="https://test-target.example.com",
            validation_scenarios=["health_check_scenario"]
        )

        # Test that crew can handle request validation
        assert request.source_url == "https://test-source.example.com"
        assert request.target_url == "https://test-target.example.com"
        assert len(request.validation_scenarios) == 1

        # Test crew components are properly initialized
        assert crew.source_explorer is not None
        assert crew.target_executor is not None
        assert crew.comparison_judge is not None
        assert crew.report_manager is not None

    def test_unified_reporting_pipeline_health(self):
        """Test unified reporting pipeline health."""
        from src.core.models import ValidationResult, ValidationDiscrepancy, SeverityLevel
        from src.behavioral.crews import BehavioralValidationResult

        reporter = ValidationReporter()

        # Create test results
        static_result = ValidationResult(
            overall_status="approved",
            fidelity_score=0.85,
            summary="Static test completed",
            discrepancies=[
                ValidationDiscrepancy(
                    type="test_discrepancy",
                    severity=SeverityLevel.INFO,
                    description="Test discrepancy for health check"
                )
            ]
        )

        behavioral_result = BehavioralValidationResult(
            overall_status="approved",
            fidelity_score=0.80,
            discrepancies=[
                ValidationDiscrepancy(
                    type="behavioral_test_discrepancy",
                    severity=SeverityLevel.WARNING,
                    description="Behavioral test discrepancy for health check"
                )
            ],
            execution_log=["Health check executed"],
            execution_time=10.0,
            timestamp=datetime.now()
        )

        # Test unified report generation
        unified_report = reporter.generate_unified_report(
            static_result=static_result,
            behavioral_result=behavioral_result
        )

        assert "metadata" in unified_report
        assert "executive_summary" in unified_report
        assert "fidelity_assessment" in unified_report
        assert unified_report["metadata"]["validation_types"]["static_analysis"] is True
        assert unified_report["metadata"]["validation_types"]["behavioral_testing"] is True

        # Test different report formats
        json_report = reporter.generate_unified_json_report(
            static_result=static_result,
            behavioral_result=behavioral_result
        )
        assert json_report is not None
        assert len(json_report) > 0

        html_report = reporter.generate_unified_html_report(
            static_result=static_result,
            behavioral_result=behavioral_result
        )
        assert html_report is not None
        assert html_report.startswith("<!DOCTYPE html>")

        markdown_report = reporter.generate_unified_markdown_report(
            static_result=static_result,
            behavioral_result=behavioral_result
        )
        assert markdown_report is not None
        assert markdown_report.startswith("#")


@pytest.mark.system
class TestSystemPerformanceHealth:
    """Test system performance characteristics."""

    @pytest.mark.slow
    def test_concurrent_request_handling(self):
        """Test system can handle concurrent requests."""
        import threading
        import time

        mock_llm_service = MagicMock()
        mock_llm_service.analyze_code_semantic_similarity.return_value = {
            "similarity_score": 0.9,
            "functionally_equivalent": True
        }

        def create_validator_instance():
            return MigrationValidator(llm_client=mock_llm_service)

        # Test creating multiple validator instances concurrently
        validators = []
        threads = []

        def create_validator_thread():
            validator = create_validator_instance()
            validators.append(validator)

        # Create 5 concurrent validator instances
        for _ in range(5):
            thread = threading.Thread(target=create_validator_thread)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all validators were created successfully
        assert len(validators) == 5
        for validator in validators:
            assert validator.llm_client == mock_llm_service

    def test_memory_usage_reasonable(self):
        """Test that system components don't use excessive memory."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create multiple system components
        mock_llm_service = MagicMock()
        validators = [MigrationValidator(llm_client=mock_llm_service) for _ in range(10)]
        crews = [create_behavioral_validation_crew(mock_llm_service) for _ in range(5)]
        reporters = [ValidationReporter() for _ in range(5)]

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB for test objects)
        max_acceptable_increase = 100 * 1024 * 1024  # 100MB
        assert memory_increase < max_acceptable_increase, f"Memory increase too high: {memory_increase / 1024 / 1024:.2f}MB"

        # Clean up references
        del validators, crews, reporters

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_async_operation_timeout_handling(self):
        """Test that async operations handle timeouts gracefully."""
        from src.behavioral.browser_automation import BrowserAutomationEngine

        engine = BrowserAutomationEngine(headless=True)

        # Test with very short timeout
        start_time = datetime.now()

        try:
            # This should either succeed quickly or fail gracefully
            success = await asyncio.wait_for(engine.initialize(), timeout=5.0)
            if success:
                await engine.cleanup()
        except asyncio.TimeoutError:
            # Timeout is acceptable for this test
            pass
        except Exception as e:
            # Other exceptions should be handled gracefully
            print(f"Browser initialization failed gracefully: {e}")

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        # Should complete within reasonable time (either success or graceful failure)
        assert execution_time < 10.0, f"Operation took too long: {execution_time}s"


@pytest.mark.system
class TestSystemConfigurationHealth:
    """Test system configuration and environment setup."""

    def test_environment_variables_handling(self):
        """Test system handles environment variables properly."""
        import os

        # Test with minimal environment
        old_env = os.environ.copy()

        try:
            # Clear LLM API keys to test fallback behavior
            for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
                if key in os.environ:
                    del os.environ[key]

            from src.services.llm_service import LLMService, LLMConfig

            # Should still initialize with default configuration
            config = LLMConfig()
            service = LLMService(config)
            assert service is not None

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(old_env)

    def test_logging_configuration(self):
        """Test logging system is properly configured."""
        import structlog
        import logging

        # Test that structlog is configured
        logger = structlog.get_logger("test_logger")
        assert logger is not None

        # Test logging doesn't raise exceptions
        try:
            logger.info("Health check log message")
            logger.warning("Health check warning message")
            logger.error("Health check error message")
        except Exception as e:
            pytest.fail(f"Logging failed: {e}")

    def test_file_system_permissions(self):
        """Test system has necessary file system permissions."""
        import tempfile
        import os

        # Test temporary directory creation
        temp_dir = tempfile.mkdtemp()
        assert os.path.exists(temp_dir)
        assert os.access(temp_dir, os.W_OK)

        # Test file creation and deletion
        test_file = os.path.join(temp_dir, "test_file.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        assert os.path.exists(test_file)

        # Clean up
        os.remove(test_file)
        os.rmdir(temp_dir)

    def test_json_serialization_compatibility(self):
        """Test that system objects can be JSON serialized."""
        import json
        from src.core.models import ValidationDiscrepancy, SeverityLevel

        # Test ValidationDiscrepancy serialization
        discrepancy = ValidationDiscrepancy(
            type="test_type",
            severity=SeverityLevel.INFO,
            description="Test description",
            recommendation="Test recommendation"
        )

        # Should be able to convert to dict for JSON serialization
        discrepancy_dict = {
            "type": discrepancy.type,
            "severity": discrepancy.severity.value,
            "description": discrepancy.description,
            "recommendation": discrepancy.recommendation
        }

        # Should serialize to JSON without errors
        json_str = json.dumps(discrepancy_dict)
        assert json_str is not None
        assert len(json_str) > 0

        # Should deserialize properly
        parsed = json.loads(json_str)
        assert parsed["type"] == "test_type"
        assert parsed["severity"] == "info"


@pytest.mark.system
@pytest.mark.external
class TestExternalDependencyHealth:
    """Test external dependency health (requires network/external services)."""

    @pytest.mark.skip(reason="Requires actual LLM API access")
    async def test_llm_service_connectivity(self):
        """Test LLM service connectivity (skip unless testing with real API)."""
        from src.services.llm_service import LLMService, LLMConfig

        config = LLMConfig()
        service = LLMService(config)

        try:
            response = await service.generate_response("Hello, this is a connectivity test.")
            assert response is not None
            assert hasattr(response, 'content')
        except Exception as e:
            pytest.skip(f"LLM service not accessible: {e}")

    @pytest.mark.skip(reason="Requires browser installation")
    async def test_browser_automation_full_stack(self):
        """Test full browser automation stack (skip unless testing with browsers)."""
        from src.behavioral.browser_automation import BrowserAutomationEngine

        engine = BrowserAutomationEngine(headless=True)

        try:
            success = await engine.initialize()
            if not success:
                pytest.skip("Browser automation not available")

            # Test basic navigation to a real site
            session_id = await engine.start_session("https://httpbin.org/")

            from src.behavioral.browser_automation import BrowserAction
            action = BrowserAction(
                action_type="navigate",
                target="https://httpbin.org/",
                description="Test navigation"
            )

            result = await engine.execute_action(action)
            assert result is not None

            await engine.end_session()

        except Exception as e:
            pytest.skip(f"Browser automation full stack not available: {e}")
        finally:
            await engine.cleanup()