"""Comprehensive unit tests for core data models.

Tests all model classes, validation logic, serialization/deserialization,
and edge cases for the core data structures.
"""

from datetime import datetime

import pytest
from src.core.models import (
    AbstractRepresentation,
    BackendFunction,
    DataField,
    InputData,
    InputType,
    MigrationValidationRequest,
    SeverityLevel,
    TechnologyContext,
    TechnologyType,
    UIElement,
    ValidationDiscrepancy,
    ValidationResult,
    ValidationScope,
    ValidationSession,
)


@pytest.mark.unit
class TestTechnologyType:
    """Test TechnologyType enum."""

    def test_technology_type_values(self):
        """Test all technology type enum values."""
        assert TechnologyType.PYTHON_FLASK.value == "python-flask"
        assert TechnologyType.PYTHON_DJANGO.value == "python-django"
        assert TechnologyType.JAVA_SPRING.value == "java-spring"
        assert TechnologyType.CSHARP_DOTNET.value == "csharp-dotnet"
        assert TechnologyType.PHP_LARAVEL.value == "php-laravel"
        assert TechnologyType.JAVASCRIPT_REACT.value == "javascript-react"
        assert TechnologyType.JAVASCRIPT_VUE.value == "javascript-vue"
        assert TechnologyType.JAVASCRIPT_ANGULAR.value == "javascript-angular"
        assert TechnologyType.TYPESCRIPT_REACT.value == "typescript-react"
        assert TechnologyType.TYPESCRIPT_VUE.value == "typescript-vue"
        assert TechnologyType.TYPESCRIPT_ANGULAR.value == "typescript-angular"

    def test_technology_type_count(self):
        """Test that all expected technology types are present."""
        expected_count = 11
        assert len(list(TechnologyType)) == expected_count

    def test_technology_type_string_representation(self):
        """Test string representation of technology types."""
        tech_type = TechnologyType.PYTHON_FLASK
        assert str(tech_type) == "TechnologyType.PYTHON_FLASK"


@pytest.mark.unit
class TestValidationScope:
    """Test ValidationScope enum."""

    def test_validation_scope_values(self):
        """Test all validation scope enum values."""
        assert ValidationScope.UI_LAYOUT.value == "ui_layout"
        assert ValidationScope.BACKEND_FUNCTIONALITY.value == "backend_functionality"
        assert ValidationScope.DATA_STRUCTURE.value == "data_structure"
        assert ValidationScope.API_ENDPOINTS.value == "api_endpoints"
        assert ValidationScope.BUSINESS_LOGIC.value == "business_logic"
        assert ValidationScope.BEHAVIORAL_VALIDATION.value == "behavioral_validation"
        assert ValidationScope.FULL_SYSTEM.value == "full_system"

    def test_validation_scope_count(self):
        """Test that all expected validation scopes are present."""
        expected_count = 7
        assert len(list(ValidationScope)) == expected_count


@pytest.mark.unit
class TestInputType:
    """Test InputType enum."""

    def test_input_type_values(self):
        """Test all input type enum values."""
        assert InputType.CODE_FILES.value == "code_files"
        assert InputType.SCREENSHOTS.value == "screenshots"
        assert InputType.HYBRID.value == "hybrid"

    def test_input_type_count(self):
        """Test that all expected input types are present."""
        expected_count = 3
        assert len(list(InputType)) == expected_count


@pytest.mark.unit
class TestSeverityLevel:
    """Test SeverityLevel enum."""

    def test_severity_level_values(self):
        """Test all severity level enum values."""
        assert SeverityLevel.CRITICAL.value == "critical"
        assert SeverityLevel.WARNING.value == "warning"
        assert SeverityLevel.INFO.value == "info"

    def test_severity_level_count(self):
        """Test that all expected severity levels are present."""
        expected_count = 3
        assert len(list(SeverityLevel)) == expected_count


@pytest.mark.unit
class TestTechnologyContext:
    """Test TechnologyContext dataclass."""

    def test_technology_context_creation(self):
        """Test creating a technology context."""
        tech_context = TechnologyContext(
            type=TechnologyType.PYTHON_FLASK,
            version="2.0",
            framework_details={"variant": "Flask-RESTful"},
        )

        assert tech_context.type == TechnologyType.PYTHON_FLASK
        assert tech_context.version == "2.0"
        assert tech_context.framework_details["variant"] == "Flask-RESTful"

    def test_technology_context_minimal(self):
        """Test creating a minimal technology context."""
        tech_context = TechnologyContext(type=TechnologyType.JAVA_SPRING)

        assert tech_context.type == TechnologyType.JAVA_SPRING
        assert tech_context.version is None
        assert tech_context.framework_details == {}

    def test_technology_context_equality(self):
        """Test technology context equality comparison."""
        tech1 = TechnologyContext(type=TechnologyType.PYTHON_FLASK, version="2.0")
        tech2 = TechnologyContext(type=TechnologyType.PYTHON_FLASK, version="2.0")
        tech3 = TechnologyContext(type=TechnologyType.JAVA_SPRING, version="3.0")

        assert tech1 == tech2
        assert tech1 != tech3

    def test_technology_context_with_complex_framework_details(self):
        """Test technology context with complex framework details."""
        complex_details = {
            "variant": "Flask-RESTful",
            "extensions": ["Flask-SQLAlchemy", "Flask-Migrate"],
            "config": {
                "database": "PostgreSQL",
                "cache": "Redis",
            },
        }

        tech_context = TechnologyContext(
            type=TechnologyType.PYTHON_FLASK,
            version="2.2",
            framework_details=complex_details,
        )

        assert tech_context.framework_details["variant"] == "Flask-RESTful"
        assert len(tech_context.framework_details["extensions"]) == 2
        assert tech_context.framework_details["config"]["database"] == "PostgreSQL"


@pytest.mark.unit
class TestInputData:
    """Test InputData dataclass."""

    def test_input_data_creation(self):
        """Test creating input data."""
        input_data = InputData(
            type=InputType.CODE_FILES,
            files=["/path/to/file1.py", "/path/to/file2.py"],
            metadata={"language": "python", "file_count": 2},
        )

        assert input_data.type == InputType.CODE_FILES
        assert len(input_data.files) == 2
        assert input_data.files[0] == "/path/to/file1.py"
        assert input_data.metadata["language"] == "python"
        assert input_data.metadata["file_count"] == 2

    def test_input_data_defaults(self):
        """Test input data with default values."""
        input_data = InputData(type=InputType.SCREENSHOTS)

        assert input_data.type == InputType.SCREENSHOTS
        assert input_data.files == []
        assert input_data.screenshots == []
        assert input_data.urls == []
        assert input_data.credentials is None
        assert input_data.validation_scenarios == []
        assert input_data.metadata == {}

    def test_input_data_hybrid(self):
        """Test hybrid input data."""
        input_data = InputData(
            type=InputType.HYBRID,
            files=["/path/to/code.py"],
            screenshots=["/path/to/screen.png"],
            urls=["http://example.com"],
            credentials={"username": "test", "password": "secret"},
            validation_scenarios=["Login test", "Dashboard test"],
            metadata={"mixed_type": True},
        )

        assert input_data.type == InputType.HYBRID
        assert len(input_data.files) == 1
        assert len(input_data.screenshots) == 1
        assert len(input_data.urls) == 1
        assert input_data.credentials["username"] == "test"
        assert len(input_data.validation_scenarios) == 2
        assert input_data.metadata["mixed_type"] is True

    def test_input_data_behavioral(self):
        """Test behavioral validation input data."""
        input_data = InputData(
            type=InputType.HYBRID,
            urls=["http://source.com", "http://target.com"],
            validation_scenarios=[
                "User login with valid credentials",
                "User login with invalid credentials",
                "Password reset flow",
            ],
            credentials={"test_user": "test_pass"},
            metadata={"timeout": 300, "browser": "chromium"},
        )

        assert len(input_data.urls) == 2
        assert len(input_data.validation_scenarios) == 3
        assert "User login with valid credentials" in input_data.validation_scenarios
        assert input_data.credentials["test_user"] == "test_pass"
        assert input_data.metadata["timeout"] == 300


@pytest.mark.unit
class TestUIElement:
    """Test UIElement dataclass."""

    def test_ui_element_creation(self):
        """Test creating a UI element."""
        ui_element = UIElement(
            type="button",
            id="submit-btn",
            text="Submit",
            position={"x": 100, "y": 200},
            attributes={"class": "btn-primary", "disabled": False},
        )

        assert ui_element.type == "button"
        assert ui_element.id == "submit-btn"
        assert ui_element.text == "Submit"
        assert ui_element.position["x"] == 100
        assert ui_element.attributes["class"] == "btn-primary"

    def test_ui_element_minimal(self):
        """Test creating a minimal UI element."""
        ui_element = UIElement(type="input")

        assert ui_element.type == "input"
        assert ui_element.id is None
        assert ui_element.text is None
        assert ui_element.position is None
        assert ui_element.attributes == {}

    def test_ui_element_complex_attributes(self):
        """Test UI element with complex attributes."""
        complex_attributes = {
            "data-validation": "required",
            "aria-label": "User email input",
            "styles": {
                "width": "300px",
                "border": "1px solid #ccc",
            },
            "events": ["click", "focus", "blur"],
        }

        ui_element = UIElement(
            type="input",
            id="email-input",
            attributes=complex_attributes,
        )

        assert ui_element.attributes["data-validation"] == "required"
        assert ui_element.attributes["aria-label"] == "User email input"
        assert ui_element.attributes["styles"]["width"] == "300px"
        assert "click" in ui_element.attributes["events"]


@pytest.mark.unit
class TestBackendFunction:
    """Test BackendFunction dataclass."""

    def test_backend_function_creation(self):
        """Test creating a backend function."""
        backend_func = BackendFunction(
            name="validate_user",
            parameters=["email", "password"],
            return_type="bool",
            logic_summary="Validates user credentials and returns authentication status",
            validation_rules=["email_format", "password_strength"],
            endpoint="/api/auth/validate",
            http_method="POST",
        )

        assert backend_func.name == "validate_user"
        assert len(backend_func.parameters) == 2
        assert "email" in backend_func.parameters
        assert backend_func.return_type == "bool"
        assert "credentials" in backend_func.logic_summary
        assert "email_format" in backend_func.validation_rules
        assert backend_func.endpoint == "/api/auth/validate"
        assert backend_func.http_method == "POST"

    def test_backend_function_minimal(self):
        """Test creating a minimal backend function."""
        backend_func = BackendFunction(name="helper_function")

        assert backend_func.name == "helper_function"
        assert backend_func.parameters == []
        assert backend_func.return_type is None
        assert backend_func.logic_summary is None
        assert backend_func.validation_rules == []
        assert backend_func.endpoint is None
        assert backend_func.http_method is None

    def test_backend_function_with_complex_parameters(self):
        """Test backend function with complex parameter types."""
        backend_func = BackendFunction(
            name="process_data",
            parameters=["data: List[Dict[str, Any]]", "config: Optional[Config]"],
            return_type="ProcessingResult",
            logic_summary="Processes complex data structures with configuration",
            validation_rules=["data_not_empty", "valid_config_format"],
        )

        assert len(backend_func.parameters) == 2
        assert "List[Dict[str, Any]]" in backend_func.parameters[0]
        assert "Optional[Config]" in backend_func.parameters[1]
        assert backend_func.return_type == "ProcessingResult"


@pytest.mark.unit
class TestDataField:
    """Test DataField dataclass."""

    def test_data_field_creation(self):
        """Test creating a data field."""
        data_field = DataField(
            name="email",
            type="string",
            required=True,
            constraints=["email_format", "max_length_255"],
            default_value=None,
        )

        assert data_field.name == "email"
        assert data_field.type == "string"
        assert data_field.required is True
        assert "email_format" in data_field.constraints
        assert data_field.default_value is None

    def test_data_field_with_default(self):
        """Test creating a data field with default value."""
        data_field = DataField(
            name="status",
            type="string",
            required=False,
            constraints=["valid_status"],
            default_value="active",
        )

        assert data_field.name == "status"
        assert data_field.required is False
        assert data_field.default_value == "active"

    def test_data_field_complex_type(self):
        """Test data field with complex type."""
        data_field = DataField(
            name="metadata",
            type="Dict[str, Any]",
            required=False,
            constraints=["valid_json"],
            default_value={},
        )

        assert data_field.type == "Dict[str, Any]"
        assert data_field.default_value == {}

    def test_data_field_minimal(self):
        """Test creating a minimal data field."""
        data_field = DataField(name="id", type="int")

        assert data_field.name == "id"
        assert data_field.type == "int"
        assert data_field.required is False
        assert data_field.constraints == []
        assert data_field.default_value is None


@pytest.mark.unit
class TestAbstractRepresentation:
    """Test AbstractRepresentation dataclass."""

    def test_abstract_representation_creation(self):
        """Test creating an abstract representation."""
        ui_elements = [
            UIElement(type="input", id="email"),
            UIElement(type="button", id="submit"),
        ]

        backend_functions = [
            BackendFunction(name="validate_user"),
            BackendFunction(name="create_session"),
        ]

        data_fields = [
            DataField(name="email", type="string", required=True),
            DataField(name="password", type="string", required=True),
        ]

        api_endpoints = [
            {"path": "/api/auth", "method": "POST"},
            {"path": "/api/users", "method": "GET"},
        ]

        representation = AbstractRepresentation(
            screen_name="Login Screen",
            ui_elements=ui_elements,
            backend_functions=backend_functions,
            data_fields=data_fields,
            api_endpoints=api_endpoints,
            metadata={"complexity": "medium", "security_level": "high"},
        )

        assert representation.screen_name == "Login Screen"
        assert len(representation.ui_elements) == 2
        assert len(representation.backend_functions) == 2
        assert len(representation.data_fields) == 2
        assert len(representation.api_endpoints) == 2
        assert representation.metadata["complexity"] == "medium"

    def test_abstract_representation_empty(self):
        """Test creating an empty abstract representation."""
        representation = AbstractRepresentation()

        assert representation.screen_name is None
        assert representation.ui_elements == []
        assert representation.backend_functions == []
        assert representation.data_fields == []
        assert representation.api_endpoints == []
        assert representation.metadata == {}

    def test_abstract_representation_partial(self):
        """Test creating a partial abstract representation."""
        representation = AbstractRepresentation(
            screen_name="Dashboard",
            ui_elements=[UIElement(type="chart", id="sales-chart")],
            metadata={"type": "dashboard", "widgets": 5},
        )

        assert representation.screen_name == "Dashboard"
        assert len(representation.ui_elements) == 1
        assert representation.ui_elements[0].type == "chart"
        assert representation.backend_functions == []
        assert representation.metadata["widgets"] == 5


@pytest.mark.unit
class TestValidationDiscrepancy:
    """Test ValidationDiscrepancy dataclass."""

    def test_validation_discrepancy_creation(self):
        """Test creating a validation discrepancy."""
        discrepancy = ValidationDiscrepancy(
            type="missing_field",
            severity=SeverityLevel.CRITICAL,
            description="Required email field is missing in target implementation",
            source_element="email_input",
            target_element=None,
            recommendation="Add email input field to target form",
            confidence=0.95,
        )

        assert discrepancy.type == "missing_field"
        assert discrepancy.severity == SeverityLevel.CRITICAL
        assert "Required email field" in discrepancy.description
        assert discrepancy.source_element == "email_input"
        assert discrepancy.target_element is None
        assert "Add email input" in discrepancy.recommendation
        assert discrepancy.confidence == 0.95

    def test_validation_discrepancy_minimal(self):
        """Test creating a minimal validation discrepancy."""
        discrepancy = ValidationDiscrepancy(
            type="type_mismatch",
            severity=SeverityLevel.WARNING,
            description="Type mismatch detected",
        )

        assert discrepancy.type == "type_mismatch"
        assert discrepancy.severity == SeverityLevel.WARNING
        assert discrepancy.description == "Type mismatch detected"
        assert discrepancy.source_element is None
        assert discrepancy.target_element is None
        assert discrepancy.recommendation is None
        assert discrepancy.confidence == 1.0

    def test_validation_discrepancy_severity_levels(self):
        """Test different severity levels."""
        critical = ValidationDiscrepancy(
            type="critical_error",
            severity=SeverityLevel.CRITICAL,
            description="Critical issue",
        )

        warning = ValidationDiscrepancy(
            type="warning_issue",
            severity=SeverityLevel.WARNING,
            description="Warning issue",
        )

        info = ValidationDiscrepancy(
            type="info_note",
            severity=SeverityLevel.INFO,
            description="Info note",
        )

        assert critical.severity == SeverityLevel.CRITICAL
        assert warning.severity == SeverityLevel.WARNING
        assert info.severity == SeverityLevel.INFO


@pytest.mark.unit
class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating a validation result."""
        discrepancies = [
            ValidationDiscrepancy(
                type="missing_field",
                severity=SeverityLevel.WARNING,
                description="Minor issue",
            ),
            ValidationDiscrepancy(
                type="type_mismatch",
                severity=SeverityLevel.INFO,
                description="Type difference",
            ),
        ]

        result = ValidationResult(
            overall_status="approved_with_warnings",
            fidelity_score=0.85,
            summary="Migration validation completed with minor issues",
            discrepancies=discrepancies,
            execution_time=45.5,
        )

        assert result.overall_status == "approved_with_warnings"
        assert result.fidelity_score == 0.85
        assert "minor issues" in result.summary
        assert len(result.discrepancies) == 2
        assert result.execution_time == 45.5
        assert isinstance(result.timestamp, datetime)

    def test_validation_result_approved(self):
        """Test creating an approved validation result."""
        result = ValidationResult(
            overall_status="approved",
            fidelity_score=0.95,
            summary="Migration validation passed successfully",
        )

        assert result.overall_status == "approved"
        assert result.fidelity_score == 0.95
        assert result.discrepancies == []
        assert result.execution_time is None

    def test_validation_result_rejected(self):
        """Test creating a rejected validation result."""
        critical_discrepancy = ValidationDiscrepancy(
            type="critical_error",
            severity=SeverityLevel.CRITICAL,
            description="Critical security vulnerability detected",
        )

        result = ValidationResult(
            overall_status="rejected",
            fidelity_score=0.45,
            summary="Migration validation failed due to critical issues",
            discrepancies=[critical_discrepancy],
        )

        assert result.overall_status == "rejected"
        assert result.fidelity_score == 0.45
        assert len(result.discrepancies) == 1
        assert result.discrepancies[0].severity == SeverityLevel.CRITICAL

    def test_validation_result_edge_scores(self):
        """Test validation results with edge case scores."""
        perfect_result = ValidationResult(
            overall_status="approved",
            fidelity_score=1.0,
            summary="Perfect migration fidelity",
        )

        zero_result = ValidationResult(
            overall_status="rejected",
            fidelity_score=0.0,
            summary="Complete migration failure",
        )

        assert perfect_result.fidelity_score == 1.0
        assert zero_result.fidelity_score == 0.0


@pytest.mark.unit
class TestMigrationValidationRequest:
    """Test MigrationValidationRequest dataclass."""

    def test_migration_validation_request_creation(self, temp_files):
        """Test creating a migration validation request."""
        source_tech = TechnologyContext(type=TechnologyType.PYTHON_FLASK, version="2.0")
        target_tech = TechnologyContext(type=TechnologyType.JAVA_SPRING, version="3.0")

        source_input = InputData(
            type=InputType.CODE_FILES,
            files=[temp_files["python_simple.py"]],
            metadata={"language": "python"},
        )

        target_input = InputData(
            type=InputType.CODE_FILES,
            files=[temp_files["java_simple.java"]],
            metadata={"language": "java"},
        )

        request = MigrationValidationRequest(
            source_technology=source_tech,
            target_technology=target_tech,
            validation_scope=ValidationScope.BUSINESS_LOGIC,
            source_input=source_input,
            target_input=target_input,
        )

        assert request.source_technology.type == TechnologyType.PYTHON_FLASK
        assert request.target_technology.type == TechnologyType.JAVA_SPRING
        assert request.validation_scope == ValidationScope.BUSINESS_LOGIC
        assert request.source_input.type == InputType.CODE_FILES
        assert request.target_input.type == InputType.CODE_FILES
        assert request.request_id.startswith("req_")
        assert isinstance(request.created_at, datetime)

    def test_migration_validation_request_auto_id(self):
        """Test automatic request ID generation."""
        source_tech = TechnologyContext(type=TechnologyType.PYTHON_FLASK)
        target_tech = TechnologyContext(type=TechnologyType.JAVA_SPRING)
        source_input = InputData(type=InputType.CODE_FILES)
        target_input = InputData(type=InputType.CODE_FILES)

        request1 = MigrationValidationRequest(
            source_technology=source_tech,
            target_technology=target_tech,
            validation_scope=ValidationScope.FULL_SYSTEM,
            source_input=source_input,
            target_input=target_input,
        )

        request2 = MigrationValidationRequest(
            source_technology=source_tech,
            target_technology=target_tech,
            validation_scope=ValidationScope.FULL_SYSTEM,
            source_input=source_input,
            target_input=target_input,
        )

        assert request1.request_id != request2.request_id
        assert request1.request_id.startswith("req_")
        assert request2.request_id.startswith("req_")

    def test_migration_validation_request_different_scopes(self):
        """Test migration validation request with different scopes."""
        source_tech = TechnologyContext(type=TechnologyType.JAVASCRIPT_REACT)
        target_tech = TechnologyContext(type=TechnologyType.TYPESCRIPT_REACT)
        source_input = InputData(type=InputType.HYBRID)
        target_input = InputData(type=InputType.HYBRID)

        scopes_to_test = [
            ValidationScope.UI_LAYOUT,
            ValidationScope.BACKEND_FUNCTIONALITY,
            ValidationScope.DATA_STRUCTURE,
            ValidationScope.API_ENDPOINTS,
            ValidationScope.BUSINESS_LOGIC,
            ValidationScope.BEHAVIORAL_VALIDATION,
            ValidationScope.FULL_SYSTEM,
        ]

        for scope in scopes_to_test:
            request = MigrationValidationRequest(
                source_technology=source_tech,
                target_technology=target_tech,
                validation_scope=scope,
                source_input=source_input,
                target_input=target_input,
            )
            assert request.validation_scope == scope


@pytest.mark.unit
class TestValidationSession:
    """Test ValidationSession dataclass."""

    def test_validation_session_creation(self, sample_validation_request):
        """Test creating a validation session."""
        session = ValidationSession(request=sample_validation_request)

        assert session.request == sample_validation_request
        assert session.source_representation is None
        assert session.target_representation is None
        assert session.result is None
        assert session.processing_log == []

    def test_validation_session_with_data(self, sample_validation_request):
        """Test validation session with all data."""
        source_repr = AbstractRepresentation(screen_name="Source")
        target_repr = AbstractRepresentation(screen_name="Target")
        result = ValidationResult(
            overall_status="approved",
            fidelity_score=0.9,
            summary="Test result",
        )

        session = ValidationSession(
            request=sample_validation_request,
            source_representation=source_repr,
            target_representation=target_repr,
            result=result,
            processing_log=["Initial log entry"],
        )

        assert session.source_representation.screen_name == "Source"
        assert session.target_representation.screen_name == "Target"
        assert session.result.overall_status == "approved"
        assert len(session.processing_log) == 1

    def test_validation_session_add_log(self, sample_validation_request):
        """Test adding log entries to validation session."""
        session = ValidationSession(request=sample_validation_request)

        session.add_log("First log entry")
        session.add_log("Second log entry")
        session.add_log("Third log entry")

        assert len(session.processing_log) == 3
        assert "First log entry" in session.processing_log[0]
        assert "Second log entry" in session.processing_log[1]
        assert "Third log entry" in session.processing_log[2]

        # Check that timestamps are added
        for log_entry in session.processing_log:
            assert log_entry.startswith("[")
            assert "]" in log_entry

    def test_validation_session_log_timestamps(self, sample_validation_request):
        """Test that log entries have proper timestamps."""
        session = ValidationSession(request=sample_validation_request)

        import time

        session.add_log("Log entry 1")
        time.sleep(0.01)  # Small delay to ensure different timestamps
        session.add_log("Log entry 2")

        assert len(session.processing_log) == 2

        # Extract timestamps from log entries
        timestamp1 = session.processing_log[0].split("]")[0][1:]
        timestamp2 = session.processing_log[1].split("]")[0][1:]

        # Verify timestamp format (ISO format)
        assert "T" in timestamp1
        assert "T" in timestamp2
        assert timestamp1 != timestamp2

    def test_validation_session_complex_workflow(self, sample_validation_request):
        """Test complex validation session workflow."""
        session = ValidationSession(request=sample_validation_request)

        # Simulate validation workflow
        session.add_log("Starting validation process")

        # Add source representation
        source_repr = AbstractRepresentation(
            screen_name="Login Form",
            ui_elements=[UIElement(type="input", id="email")],
            backend_functions=[BackendFunction(name="validate_login")],
        )
        session.source_representation = source_repr
        session.add_log("Source representation created")

        # Add target representation
        target_repr = AbstractRepresentation(
            screen_name="Login Form",
            ui_elements=[UIElement(type="input", id="username")],  # Different ID
            backend_functions=[BackendFunction(name="authenticate_user")],
            # Different name
        )
        session.target_representation = target_repr
        session.add_log("Target representation created")

        # Add validation result
        discrepancy = ValidationDiscrepancy(
            type="field_name_mismatch",
            severity=SeverityLevel.WARNING,
            description="Input field ID changed from 'email' to 'username'",
        )

        result = ValidationResult(
            overall_status="approved_with_warnings",
            fidelity_score=0.85,
            summary="Validation completed with minor naming differences",
            discrepancies=[discrepancy],
            execution_time=30.5,
        )
        session.result = result
        session.add_log("Validation completed successfully")

        # Verify final state
        assert len(session.processing_log) == 4
        assert session.source_representation.ui_elements[0].id == "email"
        assert session.target_representation.ui_elements[0].id == "username"
        assert session.result.fidelity_score == 0.85
        assert len(session.result.discrepancies) == 1
        assert session.result.discrepancies[0].type == "field_name_mismatch"


@pytest.mark.unit
class TestModelEdgeCases:
    """Test edge cases and error conditions for models."""

    def test_empty_collections(self):
        """Test models with empty collections."""
        empty_input = InputData(type=InputType.CODE_FILES)
        assert empty_input.files == []
        assert empty_input.screenshots == []
        assert empty_input.validation_scenarios == []

        empty_repr = AbstractRepresentation()
        assert empty_repr.ui_elements == []
        assert empty_repr.backend_functions == []
        assert empty_repr.data_fields == []
        assert empty_repr.api_endpoints == []

    def test_none_values(self):
        """Test models with None values where allowed."""
        ui_element = UIElement(type="button")
        assert ui_element.id is None
        assert ui_element.text is None
        assert ui_element.position is None

        backend_func = BackendFunction(name="test")
        assert backend_func.return_type is None
        assert backend_func.logic_summary is None
        assert backend_func.endpoint is None
        assert backend_func.http_method is None

    def test_large_collections(self):
        """Test models with large collections."""
        # Create large collections
        large_file_list = [f"/path/to/file_{i}.py" for i in range(1000)]
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(100)}

        input_data = InputData(
            type=InputType.CODE_FILES,
            files=large_file_list,
            metadata=large_metadata,
        )

        assert len(input_data.files) == 1000
        assert len(input_data.metadata) == 100
        assert input_data.files[999] == "/path/to/file_999.py"

    def test_unicode_content(self):
        """Test models with Unicode content."""
        ui_element = UIElement(
            type="button",
            id="botón-enviar",
            text="Enviar 📧",
            attributes={"aria-label": "Botón para enviar correo electrónico"},
        )

        assert ui_element.id == "botón-enviar"
        assert "📧" in ui_element.text
        assert "electrónico" in ui_element.attributes["aria-label"]

        backend_func = BackendFunction(
            name="función_validación",
            logic_summary="Validación de datos con caracteres especiales: áéíóú",
        )

        assert backend_func.name == "función_validación"
        assert "áéíóú" in backend_func.logic_summary

    def test_special_characters_in_strings(self):
        """Test models with special characters in strings."""
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"

        ui_element = UIElement(
            type="input",
            id=f"special-{special_chars}",
            text=special_chars,
        )

        assert special_chars in ui_element.id
        assert ui_element.text == special_chars

    def test_extremely_long_strings(self):
        """Test models with very long strings."""
        long_string = "A" * 10000

        backend_func = BackendFunction(
            name="long_function",
            logic_summary=long_string,
        )

        assert len(backend_func.logic_summary) == 10000
        assert backend_func.logic_summary.startswith("AAAA")

    def test_boundary_confidence_values(self):
        """Test confidence values at boundaries."""
        # Test minimum confidence (0.0)
        discrepancy_min = ValidationDiscrepancy(
            type="test",
            severity=SeverityLevel.INFO,
            description="Test",
            confidence=0.0,
        )
        assert discrepancy_min.confidence == 0.0

        # Test maximum confidence (1.0)
        discrepancy_max = ValidationDiscrepancy(
            type="test",
            severity=SeverityLevel.INFO,
            description="Test",
            confidence=1.0,
        )
        assert discrepancy_max.confidence == 1.0

        # Test fidelity score boundaries
        result_min = ValidationResult(
            overall_status="rejected",
            fidelity_score=0.0,
            summary="Minimum fidelity",
        )
        assert result_min.fidelity_score == 0.0

        result_max = ValidationResult(
            overall_status="approved",
            fidelity_score=1.0,
            summary="Maximum fidelity",
        )
        assert result_max.fidelity_score == 1.0

    def test_timestamp_precision(self):
        """Test timestamp precision and consistency."""
        # Create multiple results quickly
        results = []
        for i in range(5):
            result = ValidationResult(
                overall_status="approved",
                fidelity_score=0.9,
                summary=f"Test result {i}",
            )
            results.append(result)

        # Verify all timestamps are datetime objects
        for result in results:
            assert isinstance(result.timestamp, datetime)

        # Check timestamp ordering (should be in chronological order or very close)
        for i in range(1, len(results)):
            time_diff = results[i].timestamp - results[i - 1].timestamp
            assert (
                time_diff.total_seconds() >= 0
            )  # Later timestamp should be >= earlier


# Legacy tests for compatibility
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
            ),
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
            overall_status="approved",
            fidelity_score=0.85,
            summary="Test result",
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

        source_input = InputData(
            type=InputType.CODE_FILES, files=["views.py", "models.py"]
        )

        target_input = InputData(
            type=InputType.CODE_FILES,
            files=["Controller.java", "Entity.java"],
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
