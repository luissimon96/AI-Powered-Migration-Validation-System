"""Integration tests for behavioral validation pipeline.

Tests the complete workflow from behavioral validation request to final results.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.behavioral.crews import (
    BehavioralValidationCrew,
    BehavioralValidationRequest,
    BehavioralValidationResult,
    create_behavioral_validation_crew,
)
from src.core.models import SeverityLevel, ValidationDiscrepancy


@pytest.mark.integration
@pytest.mark.behavioral
@pytest.mark.asyncio
class TestBehavioralValidationPipeline:
    """Test complete behavioral validation pipeline."""

    @pytest.fixture
    def mock_browser_automation(self):
        """Mock browser automation for testing."""
        with patch("src.behavioral.crews.BrowserTool") as mock_tool_class:
            mock_tool = MagicMock()
            mock_tool_class.return_value = mock_tool

            # Mock browser tool responses
            mock_tool._run.side_effect = [
                "SESSION START session_123",  # Start session
                "NAVIGATE SUCCESS - https://source.test",  # Navigate source
                "CAPTURE_STATE SUCCESS - {'forms': 2, 'inputs': 5}",  # Capture state
                "SCENARIO LOGIN SUCCESS - 3/3 actions successful",  # Login scenario
                "SESSION END session_123",  # End session
                "SESSION START session_456",  # Start target session
                "NAVIGATE SUCCESS - https://target.test",  # Navigate target
                # Capture state (different)
                "CAPTURE_STATE SUCCESS - {'forms': 2, 'inputs': 4}",
                "SCENARIO LOGIN SUCCESS - 3/3 actions successful",  # Login scenario
                "SESSION END session_456",  # End target session
            ]

            yield mock_tool

    @pytest.fixture
    def sample_behavioral_request(self):
        """Sample behavioral validation request."""
        return BehavioralValidationRequest(
            source_url="https://source-app.test/login",
            target_url="https://target-app.test/login",
            validation_scenarios=[
                "User login with valid credentials",
                "User login with invalid email",
                "Password reset flow",
            ],
            credentials={"username": "testuser", "password": "testpass123"},
            timeout=300,
            metadata={"environment": "test"},
        )

    async def test_behavioral_validation_pipeline_success(
        self, mock_llm_service, sample_behavioral_request, mock_browser_automation,
    ):
        """Test successful behavioral validation pipeline."""
        # Mock CrewAI crew execution results
        with patch("src.behavioral.crews.Crew") as mock_crew_class:
            mock_crew_instance = MagicMock()
            mock_crew_class.return_value = mock_crew_instance

            # Mock progressive crew execution results
            mock_crew_instance.kickoff.side_effect = [
                # Source exploration result
                """{
                    "source_exploration": "completed",
                    "scenarios_tested": 3,
                    "pages_visited": 5,
                    "interactions_performed": 12,
                    "screenshots_captured": 6
                }""",
                # Target execution result
                """{
                    "target_execution": "completed",
                    "scenarios_replicated": 3,
                    "pages_visited": 5,
                    "interactions_performed": 12,
                    "behavioral_differences": 1
                }""",
                # Behavioral comparison result
                """{
                    "behavioral_comparison": "completed",
                    "similarity_score": 0.85,
                    "functional_equivalence": 0.92,
                    "user_experience": 0.78,
                    "discrepancies": [
                        {
                            "type": "response_time_difference",
                            "severity": "warning",
                            "description": "Target system login is 200ms slower than source",
                            "recommendation": "Consider performance optimization for login endpoint"
                        }
                    ]
                }""",
                # Final report result
                """{
                    "overall_status": "approved_with_warnings",
                    "fidelity_score": 0.85,
                    "migration_readiness": "approved_with_warnings",
                    "discrepancies": [
                        {
                            "type": "performance_difference",
                            "severity": "warning",
                            "description": "Target system shows slower response times in login workflow",
                            "recommendation": "Optimize login endpoint performance before production deployment",
                            "confidence": 0.9
                        }
                    ],
                    "validation_metadata": {
                        "scenarios_tested": 3,
                        "total_interactions": 12,
                        "execution_time": 180.5
                    }
                }""",
            ]

            # Execute behavioral validation
            crew = BehavioralValidationCrew(mock_llm_service)
            result = await crew.validate_migration(sample_behavioral_request)

            # Verify result structure
            assert isinstance(result, BehavioralValidationResult)
            assert result.overall_status == "approved_with_warnings"
            assert result.fidelity_score == 0.85
            assert len(result.discrepancies) == 1
            assert result.execution_time > 0
            assert isinstance(result.timestamp, datetime)

            # Verify discrepancy details
            discrepancy = result.discrepancies[0]
            assert discrepancy.type == "performance_difference"
            assert discrepancy.severity == SeverityLevel.WARNING
            assert "login endpoint performance" in discrepancy.recommendation

            # Verify execution log
            assert len(result.execution_log) > 0
            assert any(
                "Source system exploration" in log for log in result.execution_log)
            assert any("Target system execution" in log for log in result.execution_log)
            assert any("Behavioral comparison" in log for log in result.execution_log)

            # Verify crew was executed 4 times (source, target, comparison, report)
            assert mock_crew_instance.kickoff.call_count == 4

    async def test_behavioral_validation_pipeline_with_critical_issues(
        self, mock_llm_service, sample_behavioral_request, mock_browser_automation,
    ):
        """Test behavioral validation pipeline with critical issues."""
        with patch("src.behavioral.crews.Crew") as mock_crew_class:
            mock_crew_instance = MagicMock()
            mock_crew_class.return_value = mock_crew_instance

            # Mock results with critical issues
            mock_crew_instance.kickoff.side_effect = [
                # Source exploration - success
                '{"source_exploration": "completed"}',
                # Target execution - success
                '{"target_execution": "completed"}',
                # Comparison - critical issues found
                """{
                    "behavioral_comparison": "completed_with_critical_issues",
                    "discrepancies": [
                        {
                            "type": "login_failure",
                            "severity": "critical",
                            "description": "Login functionality completely broken in target system",
                            "recommendation": "Fix login authentication before migration"
                        },
                        {
                            "type": "data_corruption",
                            "severity": "critical",
                            "description": "User data is corrupted during form submission",
                            "recommendation": "Investigate data handling in target system"
                        }
                    ]
                }""",
                # Final report - rejected due to critical issues
                """{
                    "overall_status": "rejected",
                    "fidelity_score": 0.3,
                    "migration_readiness": "rejected",
                    "discrepancies": [
                        {
                            "type": "critical_functionality_failure",
                            "severity": "critical",
                            "description": "Multiple critical system failures prevent migration approval",
                            "recommendation": "Address all critical issues before retrying migration validation",
                            "confidence": 0.95
                        }
                    ]
                }""",
            ]

            crew = BehavioralValidationCrew(mock_llm_service)
            result = await crew.validate_migration(sample_behavioral_request)

            # Verify result indicates rejection
            assert result.overall_status == "rejected"
            assert result.fidelity_score == 0.3
            assert len(result.discrepancies) == 1
            assert result.discrepancies[0].severity == SeverityLevel.CRITICAL

    async def test_behavioral_validation_pipeline_browser_failure(
        self, mock_llm_service, sample_behavioral_request,
    ):
        """Test behavioral validation pipeline when browser automation fails."""
        with patch("src.behavioral.crews.Crew") as mock_crew_class:
            mock_crew_instance = MagicMock()
            mock_crew_class.return_value = mock_crew_instance

            # Mock browser initialization failure
            mock_crew_instance.kickoff.side_effect = Exception(
                "Browser automation failed: Could not launch browser",
            )

            crew = BehavioralValidationCrew(mock_llm_service)
            result = await crew.validate_migration(sample_behavioral_request)

            # Verify error handling
            assert result.overall_status == "error"
            assert result.fidelity_score == 0.0
            assert len(result.discrepancies) == 1

            error_discrepancy = result.discrepancies[0]
            assert error_discrepancy.severity == SeverityLevel.CRITICAL
            assert "Browser automation failed" in error_discrepancy.description

    async def test_behavioral_validation_pipeline_partial_success(
        self, mock_llm_service, sample_behavioral_request, mock_browser_automation,
    ):
        """Test behavioral validation pipeline with partial success."""
        with patch("src.behavioral.crews.Crew") as mock_crew_class:
            mock_crew_instance = MagicMock()
            mock_crew_class.return_value = mock_crew_instance

            mock_crew_instance.kickoff.side_effect = [
                # Source exploration - success
                '{"source_exploration": "completed", "scenarios_tested": 3}',
                # Target execution - partial failure
                """{
                    "target_execution": "completed_with_issues",
                    "scenarios_replicated": 2,
                    "failed_scenarios": ["Password reset flow"],
                    "error_details": "Password reset endpoint not found"
                }""",
                # Comparison - mixed results
                """{
                    "behavioral_comparison": "completed",
                    "discrepancies": [
                        {
                            "type": "missing_functionality",
                            "severity": "warning",
                            "description": "Password reset functionality not available in target",
                            "recommendation": "Implement password reset feature"
                        }
                    ]
                }""",
                # Final report
                """{
                    "overall_status": "approved_with_warnings",
                    "fidelity_score": 0.75,
                    "discrepancies": [
                        {
                            "type": "feature_gap",
                            "severity": "warning",
                            "description": "Some features from source system not implemented in target",
                            "recommendation": "Complete feature migration before production deployment"
                        }
                    ]
                }""",
            ]

            crew = BehavioralValidationCrew(mock_llm_service)
            result = await crew.validate_migration(sample_behavioral_request)

            assert result.overall_status == "approved_with_warnings"
            assert result.fidelity_score == 0.75
            assert len(result.discrepancies) == 1
            assert result.discrepancies[0].severity == SeverityLevel.WARNING

    async def test_behavioral_validation_cleanup_on_success(
        self, mock_llm_service, sample_behavioral_request, mock_browser_automation,
    ):
        """Test that browser resources are cleaned up after successful validation."""
        with patch("src.behavioral.crews.Crew") as mock_crew_class:
            mock_crew_instance = MagicMock()
            mock_crew_class.return_value = mock_crew_instance
            mock_crew_instance.kickoff.return_value = (
                '{"overall_status": "approved", "fidelity_score": 0.9, "discrepancies": []}'
            )

            crew = BehavioralValidationCrew(mock_llm_service)

            # Mock cleanup method
            with patch.object(
                crew, "cleanup_browser_resources", new_callable=AsyncMock,
            ) as mock_cleanup:
                result = await crew.validate_migration(sample_behavioral_request)

                # Verify cleanup was called
                mock_cleanup.assert_called_once()

            assert result.overall_status == "approved"

    async def test_behavioral_validation_cleanup_on_error(
        self, mock_llm_service, sample_behavioral_request,
    ):
        """Test that browser resources are cleaned up even when validation fails."""
        with patch("src.behavioral.crews.Crew") as mock_crew_class:
            mock_crew_instance = MagicMock()
            mock_crew_class.return_value = mock_crew_instance
            mock_crew_instance.kickoff.side_effect = Exception("Validation error")

            crew = BehavioralValidationCrew(mock_llm_service)

            # Mock cleanup method
            with patch.object(
                crew, "cleanup_browser_resources", new_callable=AsyncMock,
            ) as mock_cleanup:
                result = await crew.validate_migration(sample_behavioral_request)

                # Verify cleanup was called even on error
                mock_cleanup.assert_called_once()

            assert result.overall_status == "error"

    def test_behavioral_validation_factory_function(self, mock_llm_service):
        """Test behavioral validation crew factory function."""
        crew = create_behavioral_validation_crew(mock_llm_service)

        assert isinstance(crew, BehavioralValidationCrew)
        assert crew.llm_service == mock_llm_service
        assert crew.source_explorer is not None
        assert crew.target_executor is not None
        assert crew.comparison_judge is not None
        assert crew.report_manager is not None

    def test_behavioral_validation_factory_function_no_llm(self):
        """Test behavioral validation crew factory function without LLM."""
        crew = create_behavioral_validation_crew()

        assert isinstance(crew, BehavioralValidationCrew)
        assert crew.llm_service is None

    async def test_behavioral_validation_request_validation(self):
        """Test behavioral validation request parameter validation."""
        # Valid request
        valid_request = BehavioralValidationRequest(
            source_url="https://valid-source.test",
            target_url="https://valid-target.test",
            validation_scenarios=["login", "signup"],
        )

        assert valid_request.source_url == "https://valid-source.test"
        assert valid_request.target_url == "https://valid-target.test"
        assert len(valid_request.validation_scenarios) == 2
        assert valid_request.timeout == 300  # Default
        assert valid_request.credentials is None  # Default
        assert valid_request.metadata is None  # Default

    async def test_behavioral_validation_result_serialization(self):
        """Test behavioral validation result can be serialized."""
        discrepancy = ValidationDiscrepancy(
            type="test_issue",
            severity=SeverityLevel.INFO,
            description="Test discrepancy",
        )

        result = BehavioralValidationResult(
            overall_status="approved",
            fidelity_score=0.9,
            discrepancies=[discrepancy],
            execution_log=["Step 1", "Step 2"],
            execution_time=120.0,
            timestamp=datetime.now(),
        )

        # Test that result attributes are accessible
        assert result.overall_status == "approved"
        assert result.fidelity_score == 0.9
        assert len(result.discrepancies) == 1
        assert len(result.execution_log) == 2
        assert result.execution_time == 120.0
        assert isinstance(result.timestamp, datetime)


@pytest.mark.integration
@pytest.mark.behavioral
class TestBehavioralValidationPerformance:
    """Test behavioral validation performance characteristics."""

    @pytest.mark.slow
    async def test_behavioral_validation_timeout_handling(self, mock_llm_service):
        """Test behavioral validation handles timeouts gracefully."""
        request = BehavioralValidationRequest(
            source_url="https://slow-source.test",
            target_url="https://slow-target.test",
            validation_scenarios=["slow_operation"],
            timeout=1,  # Very short timeout
        )

        with patch("src.behavioral.crews.Crew") as mock_crew_class:
            mock_crew_instance = MagicMock()
            mock_crew_class.return_value = mock_crew_instance

            # Simulate slow operation that exceeds timeout
            async def slow_kickoff():
                await asyncio.sleep(2)  # Longer than timeout
                return '{"status": "completed"}'

            mock_crew_instance.kickoff.side_effect = slow_kickoff

            crew = BehavioralValidationCrew(mock_llm_service)

            # This should complete quickly due to timeout/error handling
            start_time = datetime.now()
            result = await crew.validate_migration(request)
            end_time = datetime.now()

            # Should complete within reasonable time even with slow operation
            execution_duration = (end_time - start_time).total_seconds()
            assert execution_duration < 30  # Should not hang

            # Result should indicate error or timeout
            assert result.overall_status in ["error", "timeout", "rejected"]

    async def test_behavioral_validation_concurrent_requests(self, mock_llm_service):
        """Test multiple concurrent behavioral validation requests."""
        requests = [
            BehavioralValidationRequest(
                source_url=f"https://source-{i}.test",
                target_url=f"https://target-{i}.test",
                validation_scenarios=[f"scenario_{i}"],
            )
            for i in range(3)
        ]

        with patch("src.behavioral.crews.Crew") as mock_crew_class:
            mock_crew_instance = MagicMock()
            mock_crew_class.return_value = mock_crew_instance
            mock_crew_instance.kickoff.return_value = (
                '{"overall_status": "approved", "fidelity_score": 0.9, "discrepancies": []}'
            )

            # Create multiple crews
            crews = [BehavioralValidationCrew(mock_llm_service) for _ in range(3)]

            # Mock cleanup for all crews
            for crew in crews:
                crew.cleanup_browser_resources = AsyncMock()

            # Execute concurrent validations
            start_time = datetime.now()
            results = await asyncio.gather(
                *[crew.validate_migration(request) for crew, request in zip(crews, requests)],
            )
            end_time = datetime.now()

            # All should complete successfully
            assert len(results) == 3
            for result in results:
                assert result.overall_status == "approved"
                assert result.fidelity_score == 0.9

            # Should complete faster than sequential execution
            execution_duration = (end_time - start_time).total_seconds()
            assert execution_duration < 60  # Reasonable concurrent execution time
