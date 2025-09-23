"""Integration tests for hybrid validation pipeline.

Tests the complete workflow combining static analysis and behavioral testing.
"""

from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from src.behavioral.crews import BehavioralValidationCrew
from src.behavioral.crews import BehavioralValidationRequest
from src.behavioral.crews import BehavioralValidationResult
from src.core.migration_validator import MigrationValidator
from src.core.models import InputData
from src.core.models import InputType
from src.core.models import MigrationValidationRequest
from src.core.models import SeverityLevel
from src.core.models import TechnologyContext
from src.core.models import TechnologyType
from src.core.models import ValidationDiscrepancy
from src.core.models import ValidationResult
from src.core.models import ValidationScope
from src.reporters.validation_reporter import ValidationReporter


@pytest.mark.integration
@pytest.mark.asyncio
class TestHybridValidationPipeline:
    """Test complete hybrid validation pipeline combining static and behavioral validation."""

    @pytest.fixture
    def sample_static_result(self):
        """Sample static validation result."""
        return ValidationResult(
            overall_status="approved",
            fidelity_score=0.85,
            summary="Static analysis completed - high code similarity with minor differences",
            discrepancies=[
                ValidationDiscrepancy(
                    type="function_signature_difference",
                    severity=SeverityLevel.INFO,
                    description="Parameter naming differs between source and target methods",
                    recommendation="Consider standardizing parameter names for consistency",
                ),
                ValidationDiscrepancy(
                    type="missing_error_handling",
                    severity=SeverityLevel.WARNING,
                    description="Target system lacks error handling for edge case in user validation",
                    recommendation="Add appropriate error handling to match source system behavior",
                ),
            ],
            execution_time=45.2,
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def sample_behavioral_result(self):
        """Sample behavioral validation result."""
        return BehavioralValidationResult(
            overall_status="approved_with_warnings",
            fidelity_score=0.78,
            discrepancies=[
                ValidationDiscrepancy(
                    type="response_time_difference",
                    severity=SeverityLevel.WARNING,
                    description="Login endpoint in target system is 300ms slower than source",
                    recommendation="Optimize login performance to match source system responsiveness",
                ),
                ValidationDiscrepancy(
                    type="error_message_inconsistency",
                    severity=SeverityLevel.INFO,
                    description="Error messages use different wording between systems",
                    recommendation="Standardize error messages for consistent user experience",
                ),
            ],
            execution_log=[
                "Source system exploration completed",
                "Target system execution completed",
                "Behavioral comparison analysis completed",
                "Performance metrics collected",
                "User experience validation completed",
            ],
            execution_time=180.5,
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def sample_migration_request(self):
        """Sample migration validation request for static analysis."""
        return MigrationValidationRequest(
            source_technology=TechnologyContext(
                type=TechnologyType.PYTHON_FLASK, version="2.0"
            ),
            target_technology=TechnologyContext(
                type=TechnologyType.JAVA_SPRING, version="3.0"
            ),
            validation_scope=ValidationScope.FULL_SYSTEM,
            source_input=InputData(
                type=InputType.CODE_FILES,
                files=["src/auth.py", "src/models.py"],
            ),
            target_input=InputData(
                type=InputType.CODE_FILES,
                files=["src/main/java/Auth.java", "src/main/java/Models.java"],
            ),
        )

    async def test_hybrid_validation_pipeline_full_success(
        self,
        mock_llm_service,
        sample_static_result,
        sample_behavioral_result,
        sample_migration_request,
    ):
        """Test complete hybrid validation pipeline with both static and behavioral validation."""
        # Mock static validation
        with patch.object(
            MigrationValidator, "validate_migration"
        ) as mock_static_validation:
            mock_session = MagicMock()
            mock_session.result = sample_static_result
            mock_static_validation.return_value = mock_session

            # Mock behavioral validation
            with patch.object(
                BehavioralValidationCrew,
                "validate_migration",
            ) as mock_behavioral_validation:
                mock_behavioral_validation.return_value = sample_behavioral_result

                # Create validation components
                static_validator = MigrationValidator(llm_client=mock_llm_service)
                behavioral_crew = BehavioralValidationCrew(mock_llm_service)
                reporter = ValidationReporter()

                # Execute static validation
                static_session = await static_validator.validate_migration(
                    sample_migration_request,
                )
                static_result = static_session.result

                # Execute behavioral validation
                behavioral_request = BehavioralValidationRequest(
                    source_url="https://source-app.test",
                    target_url="https://target-app.test",
                    validation_scenarios=[
                        "login_flow",
                        "user_registration",
                        "data_validation",
                    ],
                )
                behavioral_result = await behavioral_crew.validate_migration(
                    behavioral_request
                )

                # Generate unified report
                unified_report = reporter.generate_unified_report(
                    static_result=static_result,
                    behavioral_result=behavioral_result,
                    request=sample_migration_request,
                )

                # Verify unified report structure
                assert "metadata" in unified_report
                assert "executive_summary" in unified_report
                assert "fidelity_assessment" in unified_report
                assert "detailed_findings" in unified_report
                assert "recommendations" in unified_report
                assert "validation_breakdown" in unified_report

                # Verify metadata shows both validation types
                assert (
                    unified_report["metadata"]["validation_types"]["static_analysis"]
                    is True
                )
                assert (
                    unified_report["metadata"]["validation_types"]["behavioral_testing"]
                    is True
                )

                # Verify unified fidelity score calculation
                unified_fidelity = unified_report["fidelity_assessment"][
                    "unified_score"
                ]
                expected_fidelity = (0.85 * 0.6) + (0.78 * 0.4)  # Default weights
                assert abs(unified_fidelity - expected_fidelity) < 0.01

                # Verify combined discrepancies
                total_findings = unified_report["detailed_findings"]["total_findings"]
                assert total_findings == 4  # 2 static + 2 behavioral

                # Verify discrepancies are properly tagged
                all_findings = (
                    unified_report["detailed_findings"]["by_severity"]["critical"]
                    + unified_report["detailed_findings"]["by_severity"]["warning"]
                    + unified_report["detailed_findings"]["by_severity"]["info"]
                )

                static_findings = [
                    f for f in all_findings if f["validation_source"] == "static"
                ]
                behavioral_findings = [
                    f for f in all_findings if f["validation_source"] == "behavioral"
                ]

                assert len(static_findings) == 2
                assert len(behavioral_findings) == 2

                # Verify executive summary reflects both validations
                summary = unified_report["executive_summary"]["summary"]
                assert "Static analysis:" in summary
                assert "Behavioral testing:" in summary

    async def test_hybrid_validation_pipeline_static_only(
        self,
        mock_llm_service,
        sample_static_result,
        sample_migration_request,
    ):
        """Test hybrid validation pipeline with static validation only."""
        with patch.object(
            MigrationValidator, "validate_migration"
        ) as mock_static_validation:
            mock_session = MagicMock()
            mock_session.result = sample_static_result
            mock_static_validation.return_value = mock_session

            # Create components
            static_validator = MigrationValidator(llm_client=mock_llm_service)
            reporter = ValidationReporter()

            # Execute static validation only
            static_session = await static_validator.validate_migration(
                sample_migration_request
            )
            static_result = static_session.result

            # Generate unified report with static only
            unified_report = reporter.generate_unified_report(
                static_result=static_result,
                behavioral_result=None,
                request=sample_migration_request,
            )

            # Verify report structure
            assert (
                unified_report["metadata"]["validation_types"]["static_analysis"]
                is True
            )
            assert (
                unified_report["metadata"]["validation_types"]["behavioral_testing"]
                is False
            )

            # Verify fidelity score equals static score
            assert (
                unified_report["fidelity_assessment"]["unified_score"]
                == sample_static_result.fidelity_score
            )

            # Verify only static findings
            assert unified_report["detailed_findings"]["total_findings"] == 2
            all_findings = (
                unified_report["detailed_findings"]["by_severity"]["critical"]
                + unified_report["detailed_findings"]["by_severity"]["warning"]
                + unified_report["detailed_findings"]["by_severity"]["info"]
            )
            assert all(f["validation_source"] == "static" for f in all_findings)

    async def test_hybrid_validation_pipeline_behavioral_only(
        self,
        mock_llm_service,
        sample_behavioral_result,
    ):
        """Test hybrid validation pipeline with behavioral validation only."""
        with patch.object(
            BehavioralValidationCrew,
            "validate_migration",
        ) as mock_behavioral_validation:
            mock_behavioral_validation.return_value = sample_behavioral_result

            # Create components
            behavioral_crew = BehavioralValidationCrew(mock_llm_service)
            reporter = ValidationReporter()

            # Execute behavioral validation
            behavioral_request = BehavioralValidationRequest(
                source_url="https://source-app.test",
                target_url="https://target-app.test",
                validation_scenarios=["core_workflows"],
            )
            behavioral_result = await behavioral_crew.validate_migration(
                behavioral_request
            )

            # Generate unified report with behavioral only
            unified_report = reporter.generate_unified_report(
                static_result=None,
                behavioral_result=behavioral_result,
            )

            # Verify report structure
            assert (
                unified_report["metadata"]["validation_types"]["static_analysis"]
                is False
            )
            assert (
                unified_report["metadata"]["validation_types"]["behavioral_testing"]
                is True
            )

            # Verify fidelity score equals behavioral score
            assert (
                unified_report["fidelity_assessment"]["unified_score"]
                == sample_behavioral_result.fidelity_score
            )

            # Verify only behavioral findings
            assert unified_report["detailed_findings"]["total_findings"] == 2
            all_findings = (
                unified_report["detailed_findings"]["by_severity"]["critical"]
                + unified_report["detailed_findings"]["by_severity"]["warning"]
                + unified_report["detailed_findings"]["by_severity"]["info"]
            )
            assert all(f["validation_source"] == "behavioral" for f in all_findings)

    async def test_hybrid_validation_pipeline_with_errors(
        self,
        mock_llm_service,
        sample_static_result,
        sample_migration_request,
    ):
        """Test hybrid validation pipeline when behavioral validation fails."""
        # Mock successful static validation
        with patch.object(
            MigrationValidator, "validate_migration"
        ) as mock_static_validation:
            mock_session = MagicMock()
            mock_session.result = sample_static_result
            mock_static_validation.return_value = mock_session

            # Mock failed behavioral validation
            with patch.object(
                BehavioralValidationCrew,
                "validate_migration",
            ) as mock_behavioral_validation:
                error_result = BehavioralValidationResult(
                    overall_status="error",
                    fidelity_score=0.0,
                    discrepancies=[
                        ValidationDiscrepancy(
                            type="browser_automation_failure",
                            severity=SeverityLevel.CRITICAL,
                            description="Browser automation failed to initialize",
                            recommendation="Check browser installation and configuration",
                        ),
                    ],
                    execution_log=["Browser initialization failed"],
                    execution_time=5.0,
                    timestamp=datetime.now(),
                )
                mock_behavioral_validation.return_value = error_result

                # Create components
                static_validator = MigrationValidator(llm_client=mock_llm_service)
                behavioral_crew = BehavioralValidationCrew(mock_llm_service)
                reporter = ValidationReporter()

                # Execute validations
                static_session = await static_validator.validate_migration(
                    sample_migration_request,
                )
                static_result = static_session.result

                behavioral_request = BehavioralValidationRequest(
                    source_url="https://source-app.test",
                    target_url="https://target-app.test",
                    validation_scenarios=["login_flow"],
                )
                behavioral_result = await behavioral_crew.validate_migration(
                    behavioral_request
                )

                # Generate unified report
                unified_report = reporter.generate_unified_report(
                    static_result=static_result,
                    behavioral_result=behavioral_result,
                )

                # Verify report reflects mixed results
                assert (
                    unified_report["executive_summary"]["overall_status"] == "rejected"
                )

                # Should have findings from both validations
                total_findings = unified_report["detailed_findings"]["total_findings"]
                assert total_findings == 3  # 2 static + 1 behavioral error

                # Should have critical issue from behavioral failure
                critical_findings = unified_report["detailed_findings"]["by_severity"][
                    "critical"
                ]
                assert len(critical_findings) == 1
                assert "browser_automation_failure" in critical_findings[0]["type"]

    async def test_hybrid_validation_pipeline_custom_weights(
        self,
        mock_llm_service,
        sample_static_result,
        sample_behavioral_result,
        sample_migration_request,
    ):
        """Test hybrid validation pipeline with custom scoring weights."""
        with patch.object(
            MigrationValidator, "validate_migration"
        ) as mock_static_validation:
            mock_session = MagicMock()
            mock_session.result = sample_static_result
            mock_static_validation.return_value = mock_session

            with patch.object(
                BehavioralValidationCrew,
                "validate_migration",
            ) as mock_behavioral_validation:
                mock_behavioral_validation.return_value = sample_behavioral_result

                # Create components
                static_validator = MigrationValidator(llm_client=mock_llm_service)
                behavioral_crew = BehavioralValidationCrew(mock_llm_service)
                reporter = ValidationReporter()

                # Execute validations
                static_session = await static_validator.validate_migration(
                    sample_migration_request,
                )
                static_result = static_session.result

                behavioral_request = BehavioralValidationRequest(
                    source_url="https://source-app.test",
                    target_url="https://target-app.test",
                    validation_scenarios=["critical_workflows"],
                )
                behavioral_result = await behavioral_crew.validate_migration(
                    behavioral_request
                )

                # Generate unified report with custom weights (emphasize behavioral)
                custom_weights = {"static": 0.3, "behavioral": 0.7}
                unified_report = reporter.generate_unified_report(
                    static_result=static_result,
                    behavioral_result=behavioral_result,
                    weights=custom_weights,
                )

                # Verify custom weights are applied
                assert unified_report["metadata"]["scoring_weights"] == custom_weights

                # Verify component scores show custom weights
                component_scores = unified_report["fidelity_assessment"][
                    "component_scores"
                ]
                assert component_scores["static_analysis"]["weight"] == 0.3
                assert component_scores["behavioral_testing"]["weight"] == 0.7

                # Verify unified score calculation with custom weights
                expected_score = (0.85 * 0.3) + (0.78 * 0.7)
                actual_score = unified_report["fidelity_assessment"]["unified_score"]
                assert abs(actual_score - expected_score) < 0.01

    async def test_hybrid_validation_pipeline_performance_tracking(
        self,
        mock_llm_service,
        sample_static_result,
        sample_behavioral_result,
        sample_migration_request,
    ):
        """Test hybrid validation pipeline tracks performance metrics."""
        with patch.object(
            MigrationValidator, "validate_migration"
        ) as mock_static_validation:
            mock_session = MagicMock()
            mock_session.result = sample_static_result
            mock_static_validation.return_value = mock_session

            with patch.object(
                BehavioralValidationCrew,
                "validate_migration",
            ) as mock_behavioral_validation:
                mock_behavioral_validation.return_value = sample_behavioral_result

                # Create components
                static_validator = MigrationValidator(llm_client=mock_llm_service)
                behavioral_crew = BehavioralValidationCrew(mock_llm_service)
                reporter = ValidationReporter()

                # Track execution timing
                start_time = datetime.now()

                # Execute validations
                static_session = await static_validator.validate_migration(
                    sample_migration_request,
                )
                static_result = static_session.result

                behavioral_request = BehavioralValidationRequest(
                    source_url="https://source-app.test",
                    target_url="https://target-app.test",
                    validation_scenarios=["performance_test"],
                )
                behavioral_result = await behavioral_crew.validate_migration(
                    behavioral_request
                )

                # Generate unified report
                unified_report = reporter.generate_unified_report(
                    static_result=static_result,
                    behavioral_result=behavioral_result,
                )

                end_time = datetime.now()
                total_pipeline_time = (end_time - start_time).total_seconds()

                # Verify performance metrics in validation breakdown
                validation_breakdown = unified_report["validation_breakdown"]

                assert "performance_metrics" in validation_breakdown
                performance_metrics = validation_breakdown["performance_metrics"]

                assert "static_execution_time" in performance_metrics
                assert "behavioral_execution_time" in performance_metrics
                assert "total_execution_time" in performance_metrics

                # Verify execution times are reasonable
                assert (
                    performance_metrics["static_execution_time"]
                    == sample_static_result.execution_time
                )
                assert (
                    performance_metrics["behavioral_execution_time"]
                    == sample_behavioral_result.execution_time
                )
                assert performance_metrics["total_execution_time"] > 0

                # Verify total pipeline execution was tracked
                expected_total = (
                    sample_static_result.execution_time
                    + sample_behavioral_result.execution_time
                )
                assert (
                    abs(performance_metrics["total_execution_time"] - expected_total)
                    < 1.0
                )

    async def test_hybrid_validation_pipeline_report_formats(
        self,
        mock_llm_service,
        sample_static_result,
        sample_behavioral_result,
    ):
        """Test hybrid validation pipeline supports multiple report formats."""
        with patch.object(
            MigrationValidator, "validate_migration"
        ) as mock_static_validation:
            mock_session = MagicMock()
            mock_session.result = sample_static_result
            mock_static_validation.return_value = mock_session

            with patch.object(
                BehavioralValidationCrew,
                "validate_migration",
            ) as mock_behavioral_validation:
                mock_behavioral_validation.return_value = sample_behavioral_result

                # Create components
                reporter = ValidationReporter()

                # Generate different report formats
                json_report = reporter.generate_unified_json_report(
                    static_result=sample_static_result,
                    behavioral_result=sample_behavioral_result,
                )

                html_report = reporter.generate_unified_html_report(
                    static_result=sample_static_result,
                    behavioral_result=sample_behavioral_result,
                )

                markdown_report = reporter.generate_unified_markdown_report(
                    static_result=sample_static_result,
                    behavioral_result=sample_behavioral_result,
                )

                # Verify JSON report
                import json

                parsed_json = json.loads(json_report)
                assert "metadata" in parsed_json
                assert "executive_summary" in parsed_json

                # Verify HTML report structure
                assert html_report.startswith("<!DOCTYPE html>")
                assert "Unified Migration Validation Report" in html_report
                assert "STATIC" in html_report  # Should have static badge
                assert "BEHAVIORAL" in html_report  # Should have behavioral badge

                # Verify Markdown report structure
                assert markdown_report.startswith(
                    "# 🔄 Unified Migration Validation Report"
                )
                assert "## Validation Breakdown" in markdown_report
                assert "### 🔧 Static Analysis" in markdown_report
                assert "### 🧪 Behavioral Testing" in markdown_report

    async def test_hybrid_validation_pipeline_error_recovery(
        self,
        mock_llm_service,
        sample_migration_request,
    ):
        """Test hybrid validation pipeline graceful error recovery."""
        # Mock both validations failing
        with patch.object(
            MigrationValidator, "validate_migration"
        ) as mock_static_validation:
            mock_static_validation.side_effect = Exception(
                "Static validation infrastructure failure",
            )

            with patch.object(
                BehavioralValidationCrew,
                "validate_migration",
            ) as mock_behavioral_validation:
                mock_behavioral_validation.side_effect = Exception(
                    "Behavioral validation infrastructure failure",
                )

                # Create components
                static_validator = MigrationValidator(llm_client=mock_llm_service)
                behavioral_crew = BehavioralValidationCrew(mock_llm_service)
                reporter = ValidationReporter()

                # Attempt validations with error handling
                static_result = None
                behavioral_result = None

                try:
                    static_session = await static_validator.validate_migration(
                        sample_migration_request,
                    )
                    static_result = static_session.result
                except Exception:
                    # Create error result for static validation
                    static_result = ValidationResult(
                        overall_status="error",
                        fidelity_score=0.0,
                        summary="Static validation failed due to infrastructure error",
                        discrepancies=[
                            ValidationDiscrepancy(
                                type="validation_infrastructure_error",
                                severity=SeverityLevel.CRITICAL,
                                description="Static validation infrastructure failure",
                                recommendation="Check static validation system configuration",
                            ),
                        ],
                    )

                try:
                    behavioral_request = BehavioralValidationRequest(
                        source_url="https://source-app.test",
                        target_url="https://target-app.test",
                        validation_scenarios=["basic_test"],
                    )
                    behavioral_result = await behavioral_crew.validate_migration(
                        behavioral_request,
                    )
                except Exception:
                    # Create error result for behavioral validation
                    behavioral_result = BehavioralValidationResult(
                        overall_status="error",
                        fidelity_score=0.0,
                        discrepancies=[
                            ValidationDiscrepancy(
                                type="behavioral_validation_infrastructure_error",
                                severity=SeverityLevel.CRITICAL,
                                description="Behavioral validation infrastructure failure",
                                recommendation="Check behavioral validation system configuration",
                            ),
                        ],
                        execution_log=["Infrastructure failure occurred"],
                        execution_time=0.0,
                        timestamp=datetime.now(),
                    )

                # Generate unified report even with errors
                unified_report = reporter.generate_unified_report(
                    static_result=static_result,
                    behavioral_result=behavioral_result,
                )

                # Verify error handling in unified report
                assert (
                    unified_report["executive_summary"]["overall_status"] == "rejected"
                )
                assert unified_report["fidelity_assessment"]["unified_score"] == 0.0

                # Should have critical findings from both validation failures
                critical_findings = unified_report["detailed_findings"]["by_severity"][
                    "critical"
                ]
                assert len(critical_findings) == 2  # One from each validation type

                # Verify error recommendations are included
                immediate_actions = unified_report["recommendations"][
                    "immediate_actions"
                ]
                assert len(immediate_actions) == 2
                assert any(
                    "infrastructure" in action["description"].lower()
                    for action in immediate_actions
                )
