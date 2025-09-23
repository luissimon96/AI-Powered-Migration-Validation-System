"""
Unit tests for core data models.
"""

from datetime import datetime

import pytest

from src.core.models import (
    InputData,
    InputType,
    MigrationValidationRequest,
    SeverityLevel,
    TechnologyContext,
    TechnologyType,
    ValidationDiscrepancy,
    ValidationResult,
    ValidationScope,
)


class TestValidationDiscrepancy:
    """Test ValidationDiscrepancy model."""

    def test_discrepancy_creation(self):
        """Test creating a validation discrepancy."""
        discrepancy = ValidationDiscrepancy(
            type="missing_field",
            severity=SeverityLevel.CRITICAL,
            description="Required field 'email' is missing in target system",
            source_element="user_form.email",
            target_element=None,
            recommendation="Add email field to target form",
            confidence=0.95,
        )

        assert discrepancy.type == "missing_field"
        assert discrepancy.severity == SeverityLevel.CRITICAL
        assert discrepancy.confidence == 0.95
        assert "email" in discrepancy.description

    def test_severity_enum_values(self):
        """Test severity level enum values."""
        assert SeverityLevel.CRITICAL.value == "critical"
        assert SeverityLevel.WARNING.value == "warning"
        assert SeverityLevel.INFO.value == "info"


class TestValidationResult:
    """Test ValidationResult model."""

    def test_result_creation(self):
        """Test creating a validation result."""
        discrepancies = [
            ValidationDiscrepancy(
                type="type_mismatch",
                severity=SeverityLevel.WARNING,
                description="Field type changed from string to integer",
            )
        ]

        result = ValidationResult(
            overall_status="approved_with_warnings",
            fidelity_score=0.92,
            summary="Migration validation passed with minor warnings",
            discrepancies=discrepancies,
            execution_time=45.7,
        )

        assert result.overall_status == "approved_with_warnings"
        assert result.fidelity_score == 0.92
        assert len(result.discrepancies) == 1
        assert result.execution_time == 45.7
        assert isinstance(result.timestamp, datetime)

    def test_fidelity_score_bounds(self):
        """Test fidelity score is within valid bounds."""
        result = ValidationResult(
            overall_status="approved", fidelity_score=0.85, summary="Test result"
        )

        assert 0.0 <= result.fidelity_score <= 1.0


class TestTechnologyContext:
    """Test TechnologyContext model."""

    def test_technology_context_creation(self):
        """Test creating technology context."""
        context = TechnologyContext(
            type=TechnologyType.PYTHON_FLASK,
            version="2.1.0",
            framework_details={"orm": "SQLAlchemy", "template_engine": "Jinja2"},
        )

        assert context.type == TechnologyType.PYTHON_FLASK
        assert context.version == "2.1.0"
        assert context.framework_details["orm"] == "SQLAlchemy"


class TestInputData:
    """Test InputData model."""

    def test_input_data_creation(self):
        """Test creating input data."""
        input_data = InputData(
            type=InputType.HYBRID,
            files=["app.py", "models.py"],
            screenshots=["login.png", "dashboard.png"],
            urls=["http://system.test"],
            validation_scenarios=["login_flow", "data_entry"],
            metadata={"environment": "staging"},
        )

        assert input_data.type == InputType.HYBRID
        assert len(input_data.files) == 2
        assert len(input_data.screenshots) == 2
        assert len(input_data.urls) == 1
        assert len(input_data.validation_scenarios) == 2
        assert input_data.metadata["environment"] == "staging"


class TestMigrationValidationRequest:
    """Test MigrationValidationRequest model."""

    def test_validation_request_creation(self):
        """Test creating a migration validation request."""
        source_tech = TechnologyContext(type=TechnologyType.PYTHON_DJANGO)
        target_tech = TechnologyContext(type=TechnologyType.JAVA_SPRING)

        source_input = InputData(type=InputType.CODE_FILES, files=["views.py", "models.py"])

        target_input = InputData(
            type=InputType.CODE_FILES, files=["Controller.java", "Entity.java"]
        )

        request = MigrationValidationRequest(
            source_technology=source_tech,
            target_technology=target_tech,
            validation_scope=ValidationScope.FULL_SYSTEM,
            source_input=source_input,
            target_input=target_input,
        )

        assert request.source_technology.type == TechnologyType.PYTHON_DJANGO
        assert request.target_technology.type == TechnologyType.JAVA_SPRING
        assert request.validation_scope == ValidationScope.FULL_SYSTEM
        assert len(request.source_input.files) == 2
        assert len(request.target_input.files) == 2
        assert request.request_id.startswith("req_")
        assert isinstance(request.created_at, datetime)
