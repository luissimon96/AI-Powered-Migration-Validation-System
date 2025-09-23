"""Unit tests for ValidationReporter - unified reporting functionality.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.behavioral.crews import BehavioralValidationResult
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


@pytest.mark.unit
class TestValidationReporter:
    """Test ValidationReporter core functionality."""

    def test_reporter_initialization(self):
        """Test reporter initialization with default settings."""
        reporter = ValidationReporter()

        assert reporter.severity_colors[SeverityLevel.CRITICAL] == "#FF4444"
        assert reporter.severity_colors[SeverityLevel.WARNING] == "#FFA500"
        assert reporter.severity_colors[SeverityLevel.INFO] == "#4444FF"

        assert reporter.severity_icons[SeverityLevel.CRITICAL] == "🔴"
        assert reporter.severity_icons[SeverityLevel.WARNING] == "🟡"
        assert reporter.severity_icons[SeverityLevel.INFO] == "🔵"

        assert reporter.default_weights["static"] == 0.6
        assert reporter.default_weights["behavioral"] == 0.4

    def test_count_discrepancies_by_severity(self):
        """Test discrepancy counting by severity."""
        reporter = ValidationReporter()

        discrepancies = [
            ValidationDiscrepancy(
                type="critical_issue",
                severity=SeverityLevel.CRITICAL,
                description="Critical error",
            ),
            ValidationDiscrepancy(
                type="warning_issue",
                severity=SeverityLevel.WARNING,
                description="Warning error",
            ),
            ValidationDiscrepancy(
                type="info_issue", severity=SeverityLevel.INFO, description="Info note",
            ),
            ValidationDiscrepancy(
                type="another_critical",
                severity=SeverityLevel.CRITICAL,
                description="Another critical",
            ),
        ]

        counts = reporter._count_discrepancies_by_severity(discrepancies)

        assert counts["critical"] == 2
        assert counts["warning"] == 1
        assert counts["info"] == 1

    def test_extract_key_findings(self):
        """Test extracting key findings from discrepancies."""
        reporter = ValidationReporter()

        discrepancies = [
            ValidationDiscrepancy(
                type="issue1",
                severity=SeverityLevel.CRITICAL,
                description="First critical issue",
            ),
            ValidationDiscrepancy(
                type="issue2",
                severity=SeverityLevel.WARNING,
                description="Second warning issue",
            ),
            ValidationDiscrepancy(
                type="issue3",
                severity=SeverityLevel.INFO,
                description="Third info issue",
            ),
        ]

        key_findings = reporter._extract_key_findings(discrepancies[:2])

        assert len(key_findings) == 2
        assert "First critical issue" in key_findings
        assert "Second warning issue" in key_findings

    def test_generate_general_recommendations_critical_issues(self):
        """Test generating recommendations for critical issues."""
        reporter = ValidationReporter()

        discrepancies = [
            ValidationDiscrepancy(
                type="critical_issue",
                severity=SeverityLevel.CRITICAL,
                description="Critical error",
            ),
        ]

        recommendations = reporter._generate_general_recommendations(discrepancies)

        assert any("Address all critical issues" in rec for rec in recommendations)

    def test_generate_general_recommendations_many_warnings(self):
        """Test generating recommendations for many warnings."""
        reporter = ValidationReporter()

        discrepancies = [
            ValidationDiscrepancy(
                type=f"warning_{i}",
                severity=SeverityLevel.WARNING,
                description=f"Warning {i}",
            )
            for i in range(5)  # Create 5 warnings
        ]

        recommendations = reporter._generate_general_recommendations(discrepancies)

        assert any("additional testing" in rec for rec in recommendations)

    def test_generate_general_recommendations_pattern_based(self):
        """Test pattern-based recommendations."""
        reporter = ValidationReporter()

        discrepancies = [
            ValidationDiscrepancy(
                type="missing_field",
                severity=SeverityLevel.WARNING,
                description="Missing field 1",
            ),
            ValidationDiscrepancy(
                type="missing_field",
                severity=SeverityLevel.WARNING,
                description="Missing field 2",
            ),
            ValidationDiscrepancy(
                type="missing_field",
                severity=SeverityLevel.WARNING,
                description="Missing field 3",
            ),
        ]

        recommendations = reporter._generate_general_recommendations(discrepancies)

        assert any("data mapping" in rec for rec in recommendations)

    def test_calculate_unified_fidelity_score_both_results(self):
        """Test calculating unified fidelity score with both static and behavioral results."""
        reporter = ValidationReporter()

        static_result = MagicMock()
        static_result.fidelity_score = 0.8

        behavioral_result = MagicMock()
        behavioral_result.fidelity_score = 0.9

        weights = {"static": 0.6, "behavioral": 0.4}

        unified_score = reporter._calculate_unified_fidelity_score(
            static_result, behavioral_result, weights,
        )

        # Expected: (0.8 * 0.6) + (0.9 * 0.4) = 0.48 + 0.36 = 0.84
        assert abs(unified_score - 0.84) < 0.001

    def test_calculate_unified_fidelity_score_static_only(self):
        """Test calculating unified fidelity score with static result only."""
        reporter = ValidationReporter()

        static_result = MagicMock()
        static_result.fidelity_score = 0.75

        weights = {"static": 0.6, "behavioral": 0.4}

        unified_score = reporter._calculate_unified_fidelity_score(
            static_result, None, weights)

        assert unified_score == 0.75

    def test_calculate_unified_fidelity_score_behavioral_only(self):
        """Test calculating unified fidelity score with behavioral result only."""
        reporter = ValidationReporter()

        behavioral_result = MagicMock()
        behavioral_result.fidelity_score = 0.85

        weights = {"static": 0.6, "behavioral": 0.4}

        unified_score = reporter._calculate_unified_fidelity_score(
            None, behavioral_result, weights,
        )

        assert unified_score == 0.85

    def test_calculate_unified_fidelity_score_no_results(self):
        """Test calculating unified fidelity score with no results."""
        reporter = ValidationReporter()

        weights = {"static": 0.6, "behavioral": 0.4}

        unified_score = reporter._calculate_unified_fidelity_score(None, None, weights)

        assert unified_score == 0.0

    def test_determine_unified_status_approved(self):
        """Test determining unified status for approved migration."""
        reporter = ValidationReporter()

        static_result = MagicMock()
        static_result.overall_status = "approved"

        behavioral_result = MagicMock()
        behavioral_result.overall_status = "approved"

        status = reporter._determine_unified_status(
            static_result, behavioral_result, 0.9)

        assert status == "approved"

    def test_determine_unified_status_rejected_due_to_error(self):
        """Test determining unified status when one result has error."""
        reporter = ValidationReporter()

        static_result = MagicMock()
        static_result.overall_status = "approved"

        behavioral_result = MagicMock()
        behavioral_result.overall_status = "error"

        status = reporter._determine_unified_status(
            static_result, behavioral_result, 0.9)

        assert status == "rejected"

    def test_determine_unified_status_warnings(self):
        """Test determining unified status with warnings."""
        reporter = ValidationReporter()

        static_result = MagicMock()
        static_result.overall_status = "approved_with_warnings"

        behavioral_result = MagicMock()
        behavioral_result.overall_status = "approved"

        status = reporter._determine_unified_status(
            static_result, behavioral_result, 0.8)

        assert status == "approved_with_warnings"

    def test_determine_unified_status_low_fidelity(self):
        """Test determining unified status with low fidelity score."""
        reporter = ValidationReporter()

        static_result = MagicMock()
        static_result.overall_status = "approved"

        behavioral_result = MagicMock()
        behavioral_result.overall_status = "approved"

        status = reporter._determine_unified_status(
            static_result, behavioral_result, 0.5,  # Low fidelity
        )

        assert status == "rejected"

    def test_merge_discrepancies(self):
        """Test merging discrepancies from static and behavioral results."""
        reporter = ValidationReporter()

        static_discrepancy = ValidationDiscrepancy(
            type="static_issue",
            severity=SeverityLevel.WARNING,
            description="Static analysis found this",
        )

        behavioral_discrepancy = ValidationDiscrepancy(
            type="behavioral_issue",
            severity=SeverityLevel.CRITICAL,
            description="Behavioral test found this",
        )

        static_result = MagicMock()
        static_result.discrepancies = [static_discrepancy]

        behavioral_result = MagicMock()
        behavioral_result.discrepancies = [behavioral_discrepancy]

        merged = reporter._merge_discrepancies(static_result, behavioral_result)

        assert len(merged) == 2

        # Check that critical comes first (sorted by severity)
        assert merged[0].severity == SeverityLevel.CRITICAL
        assert merged[0].type == "behavioral_behavioral_issue"
        assert "[Behavioral Testing]" in merged[0].description

        assert merged[1].severity == SeverityLevel.WARNING
        assert merged[1].type == "static_static_issue"
        assert "[Static Analysis]" in merged[1].description

    def test_merge_discrepancies_static_only(self):
        """Test merging discrepancies with static result only."""
        reporter = ValidationReporter()

        static_discrepancy = ValidationDiscrepancy(
            type="static_issue",
            severity=SeverityLevel.INFO,
            description="Static analysis found this",
        )

        static_result = MagicMock()
        static_result.discrepancies = [static_discrepancy]

        merged = reporter._merge_discrepancies(static_result, None)

        assert len(merged) == 1
        assert merged[0].type == "static_static_issue"
        assert "[Static Analysis]" in merged[0].description

    def test_merge_discrepancies_behavioral_only(self):
        """Test merging discrepancies with behavioral result only."""
        reporter = ValidationReporter()

        behavioral_discrepancy = ValidationDiscrepancy(
            type="behavioral_issue",
            severity=SeverityLevel.WARNING,
            description="Behavioral test found this",
        )

        behavioral_result = MagicMock()
        behavioral_result.discrepancies = [behavioral_discrepancy]

        merged = reporter._merge_discrepancies(None, behavioral_result)

        assert len(merged) == 1
        assert merged[0].type == "behavioral_behavioral_issue"
        assert "[Behavioral Testing]" in merged[0].description

    def test_merge_discrepancies_none(self):
        """Test merging discrepancies with no results."""
        reporter = ValidationReporter()

        merged = reporter._merge_discrepancies(None, None)

        assert merged == []


@pytest.mark.unit
class TestUnifiedReportGeneration:
    """Test unified report generation functionality."""

    @pytest.fixture
    def sample_static_result(self):
        """Create sample static validation result."""
        return ValidationResult(
            overall_status="approved",
            fidelity_score=0.85,
            summary="Static analysis completed successfully",
            discrepancies=[
                ValidationDiscrepancy(
                    type="minor_difference",
                    severity=SeverityLevel.INFO,
                    description="Minor naming difference found",
                    recommendation="Consider standardizing names",
                ),
            ],
            execution_time=45.2,
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def sample_behavioral_result(self):
        """Create sample behavioral validation result."""
        return BehavioralValidationResult(
            overall_status="approved_with_warnings",
            fidelity_score=0.78,
            discrepancies=[
                ValidationDiscrepancy(
                    type="performance_difference",
                    severity=SeverityLevel.WARNING,
                    description="Response time difference detected",
                    recommendation="Optimize target system performance",
                ),
            ],
            execution_log=["Step 1", "Step 2", "Step 3"],
            execution_time=120.5,
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def sample_request(self):
        """Create sample migration validation request."""
        return MigrationValidationRequest(
            source_technology=TechnologyContext(
                type=TechnologyType.PYTHON_FLASK,
                version="2.0"),
            target_technology=TechnologyContext(
                type=TechnologyType.JAVA_SPRING,
                version="3.0"),
            validation_scope=ValidationScope.FULL_SYSTEM,
            source_input=InputData(
                type=InputType.CODE_FILES,
                files=["source.py"]),
            target_input=InputData(
                type=InputType.CODE_FILES,
                files=["target.java"]),
        )

    def test_generate_unified_report_both_results(
        self, sample_static_result, sample_behavioral_result,
    ):
        """Test generating unified report with both static and behavioral results."""
        reporter = ValidationReporter()

        report = reporter.generate_unified_report(
            static_result=sample_static_result,
            behavioral_result=sample_behavioral_result,
        )

        assert "metadata" in report
        assert "executive_summary" in report
        assert "fidelity_assessment" in report
        assert "detailed_findings" in report
        assert "recommendations" in report
        assert "validation_breakdown" in report
        assert "technical_details" in report
        assert "appendix" in report

        # Check unified fidelity score calculation
        assert report["fidelity_assessment"]["unified_score"] > 0
        assert "component_scores" in report["fidelity_assessment"]

        # Check validation types
        assert report["metadata"]["validation_types"]["static_analysis"] is True
        assert report["metadata"]["validation_types"]["behavioral_testing"] is True

        # Check discrepancies are merged
        assert len(report["detailed_findings"]["by_severity"]["info"]) == 1
        assert len(report["detailed_findings"]["by_severity"]["warning"]) == 1

    def test_generate_unified_report_static_only(self, sample_static_result):
        """Test generating unified report with static result only."""
        reporter = ValidationReporter()

        report = reporter.generate_unified_report(
            static_result=sample_static_result, behavioral_result=None,
        )

        assert report["metadata"]["validation_types"]["static_analysis"] is True
        assert report["metadata"]["validation_types"]["behavioral_testing"] is False

        # Should have only static component score
        assert "static_analysis" in report["fidelity_assessment"]["component_scores"]
        assert "behavioral_testing" not in report["fidelity_assessment"]["component_scores"]

        # Fidelity score should equal static score
        assert (report["fidelity_assessment"]["unified_score"]
                == sample_static_result.fidelity_score)

    def test_generate_unified_report_behavioral_only(self, sample_behavioral_result):
        """Test generating unified report with behavioral result only."""
        reporter = ValidationReporter()

        report = reporter.generate_unified_report(
            static_result=None, behavioral_result=sample_behavioral_result,
        )

        assert report["metadata"]["validation_types"]["static_analysis"] is False
        assert report["metadata"]["validation_types"]["behavioral_testing"] is True

        # Should have only behavioral component score
        assert "behavioral_testing" in report["fidelity_assessment"]["component_scores"]
        assert "static_analysis" not in report["fidelity_assessment"]["component_scores"]

        # Fidelity score should equal behavioral score
        assert (
            report["fidelity_assessment"]["unified_score"]
            == sample_behavioral_result.fidelity_score
        )

    def test_generate_unified_report_no_results(self):
        """Test generating unified report with no results raises error."""
        reporter = ValidationReporter()

        with pytest.raises(ValueError, match="At least one validation result"):
            reporter.generate_unified_report(static_result=None, behavioral_result=None)

    def test_generate_unified_report_custom_weights(
        self, sample_static_result, sample_behavioral_result,
    ):
        """Test generating unified report with custom weights."""
        reporter = ValidationReporter()

        custom_weights = {"static": 0.3, "behavioral": 0.7}

        report = reporter.generate_unified_report(
            static_result=sample_static_result,
            behavioral_result=sample_behavioral_result,
            weights=custom_weights,
        )

        assert report["metadata"]["scoring_weights"] == custom_weights
        assert (report["fidelity_assessment"]["component_scores"]
                ["static_analysis"]["weight"] == 0.3)
        assert (report["fidelity_assessment"]["component_scores"]
                ["behavioral_testing"]["weight"] == 0.7)

        # Calculate expected score: (0.85 * 0.3) + (0.78 * 0.7) = 0.255 + 0.546 = 0.801
        expected_score = (0.85 * 0.3) + (0.78 * 0.7)
        assert abs(
            report["fidelity_assessment"]["unified_score"]
            - expected_score) < 0.001

    def test_generate_unified_json_report(
            self,
            sample_static_result,
            sample_behavioral_result):
        """Test generating unified JSON report."""
        reporter = ValidationReporter()

        json_report = reporter.generate_unified_json_report(
            static_result=sample_static_result,
            behavioral_result=sample_behavioral_result,
        )

        # Should be valid JSON
        parsed_report = json.loads(json_report)
        assert "metadata" in parsed_report
        assert "executive_summary" in parsed_report

    def test_generate_unified_html_report(
            self,
            sample_static_result,
            sample_behavioral_result):
        """Test generating unified HTML report."""
        reporter = ValidationReporter()

        html_report = reporter.generate_unified_html_report(
            static_result=sample_static_result,
            behavioral_result=sample_behavioral_result,
        )

        # Should be HTML
        assert html_report.startswith("<!DOCTYPE html>")
        assert "<title>Unified Migration Validation Report</title>" in html_report
        assert "Validation Breakdown" in html_report

    def test_generate_unified_markdown_report(
        self, sample_static_result, sample_behavioral_result,
    ):
        """Test generating unified Markdown report."""
        reporter = ValidationReporter()

        markdown_report = reporter.generate_unified_markdown_report(
            static_result=sample_static_result,
            behavioral_result=sample_behavioral_result,
        )

        # Should be Markdown
        assert markdown_report.startswith("# 🔄 Unified Migration Validation Report")
        assert "## Executive Summary" in markdown_report
        assert "## Validation Breakdown" in markdown_report


@pytest.mark.unit
class TestReportTemplateRendering:
    """Test report template rendering functionality."""

    def test_render_component_scores_markdown(self):
        """Test rendering component scores in Markdown."""
        reporter = ValidationReporter()

        component_scores = {
            "static_analysis": {"percentage": "85.0%", "weight": 0.6},
            "behavioral_testing": {"percentage": "78.0%", "weight": 0.4},
        }

        markdown = reporter._render_component_scores_markdown(component_scores)

        assert "**Static Analysis:** 85.0% (weight: 60.0%)" in markdown
        assert "**Behavioral Testing:** 78.0% (weight: 40.0%)" in markdown

    def test_render_unified_findings_markdown(self):
        """Test rendering unified findings in Markdown."""
        reporter = ValidationReporter()

        findings = {
            "by_severity": {
                "critical": [
                    {
                        "description": "Critical issue found",
                        "recommendation": "Fix immediately",
                        "validation_source": "static",
                    },
                ],
                "warning": [
                    {
                        "description": "Warning issue found",
                        "recommendation": "Review and fix",
                        "validation_source": "behavioral",
                    },
                ],
                "info": [],
            },
        }

        markdown = reporter._render_unified_findings_markdown(findings)

        assert "### 🔴 Critical Issues (1)" in markdown
        assert "**[STATIC]** Critical issue found" in markdown
        assert "### 🟡 Warning Issues (1)" in markdown
        assert "**[BEHAVIORAL]** Warning issue found" in markdown

    def test_render_unified_recommendations_markdown(self):
        """Test rendering unified recommendations in Markdown."""
        reporter = ValidationReporter()

        recommendations = {
            "immediate_actions": [
                {"description": "Fix critical issue", "validation_source": "static"},
            ],
            "review_items": [{"description": "Review warning", "validation_source": "behavioral"}],
            "static_specific": [{"description": "Static-specific recommendation"}],
            "behavioral_specific": [{"description": "Behavioral-specific recommendation"}],
            "unified": ["Consider additional validation cycles"],
        }

        markdown = reporter._render_unified_recommendations_markdown(recommendations)

        assert "### 🔴 Immediate Actions Required" in markdown
        assert "**[STATIC]** Fix critical issue" in markdown
        assert "### 🟡 Items for Review" in markdown
        assert "**[BEHAVIORAL]** Review warning" in markdown
        assert "### 🔧 Static Analysis Specific" in markdown
        assert "### 🧪 Behavioral Testing Specific" in markdown
        assert "### 🔄 Unified Recommendations" in markdown
        assert "Consider additional validation cycles" in markdown
