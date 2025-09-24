"""Core data models for AI-Powered Migration Validation System.

Defines the fundamental data structures for representing migration contexts,
validation results, and system operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TechnologyType(Enum):
    """Supported technology types for migration validation."""

    PYTHON_FLASK = "python-flask"
    PYTHON_DJANGO = "python-django"
    JAVA_SPRING = "java-spring"
    CSHARP_DOTNET = "csharp-dotnet"
    PHP_LARAVEL = "php-laravel"
    JAVASCRIPT_REACT = "javascript-react"
    JAVASCRIPT_VUE = "javascript-vue"
    JAVASCRIPT_ANGULAR = "javascript-angular"
    TYPESCRIPT_REACT = "typescript-react"
    TYPESCRIPT_VUE = "typescript-vue"
    TYPESCRIPT_ANGULAR = "typescript-angular"


class ValidationScope(Enum):
    """Defines what aspects of the migration to validate."""

    UI_LAYOUT = "ui_layout"
    BACKEND_FUNCTIONALITY = "backend_functionality"
    DATA_STRUCTURE = "data_structure"
    API_ENDPOINTS = "api_endpoints"
    BUSINESS_LOGIC = "business_logic"
    BEHAVIORAL_VALIDATION = "behavioral_validation"
    FULL_SYSTEM = "full_system"


class InputType(Enum):
    """Types of input that can be provided for validation."""

    CODE_FILES = "code_files"
    SCREENSHOTS = "screenshots"
    HYBRID = "hybrid"


class SeverityLevel(Enum):
    """Severity levels for validation discrepancies."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class TechnologyContext:
    """Represents a technology context (source or target)."""

    type: TechnologyType
    version: Optional[str] = None
    framework_details: dict[str, Any] = field(default_factory=dict)


@dataclass
class InputData:
    """Represents input data for validation."""

    type: InputType
    files: list[str] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)  # For behavioral validation
    credentials: Optional[dict[str, str]] = None  # For authenticated systems
    validation_scenarios: list[str] = field(
        default_factory=list
    )  # Behavioral test scenarios
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UIElement:
    """Represents a UI element extracted from code or screenshots."""

    type: str  # label, input, button, table, etc.
    id: Optional[str] = None
    text: Optional[str] = None
    position: Optional[dict[str, int]] = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class BackendFunction:
    """Represents a backend function or method."""

    name: str
    parameters: list[str] = field(default_factory=list)
    return_type: Optional[str] = None
    logic_summary: Optional[str] = None
    validation_rules: list[str] = field(default_factory=list)
    endpoint: Optional[str] = None
    http_method: Optional[str] = None


@dataclass
class DataField:
    """Represents a data field or property."""

    name: str
    type: str
    required: bool = False
    constraints: list[str] = field(default_factory=list)
    default_value: Optional[Any] = None


@dataclass
class AbstractRepresentation:
    """Abstract representation of a system component."""

    screen_name: Optional[str] = None
    ui_elements: list[UIElement] = field(default_factory=list)
    backend_functions: list[BackendFunction] = field(default_factory=list)
    data_fields: list[DataField] = field(default_factory=list)
    api_endpoints: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationDiscrepancy:
    """Represents a discrepancy found during validation."""

    type: str  # missing_field, additional_field, type_mismatch, logic_divergence
    severity: SeverityLevel
    description: str
    source_element: Optional[str] = None
    target_element: Optional[str] = None
    recommendation: Optional[str] = None
    confidence: float = 1.0


@dataclass
class ValidationResult:
    """Complete validation result for a migration."""

    overall_status: str  # approved, approved_with_warnings, rejected
    fidelity_score: float  # 0.0 to 1.0
    summary: str
    discrepancies: list[ValidationDiscrepancy] = field(default_factory=list)
    execution_time: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ValidationRequest:
    """Basic validation request structure."""

    source_technology: str
    target_technology: str
    validation_scope: str = "full_system"
    source_technology_version: Optional[str] = None
    target_technology_version: Optional[str] = None
    source_framework_details: dict[str, Any] = field(default_factory=dict)
    target_framework_details: dict[str, Any] = field(default_factory=dict)
    source_urls: list[str] = field(default_factory=list)
    target_urls: list[str] = field(default_factory=list)
    validation_scenarios: list[str] = field(default_factory=list)
    behavioral_timeout: int = 300
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationValidationRequest:
    """Complete request for migration validation."""

    source_technology: TechnologyContext
    target_technology: TechnologyContext
    validation_scope: ValidationScope
    source_input: InputData
    target_input: InputData
    request_id: str = field(default_factory=lambda: f"req_{datetime.now().isoformat()}")
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ValidationSession:
    """Represents a complete validation session."""

    request: MigrationValidationRequest
    source_representation: Optional[AbstractRepresentation] = None
    target_representation: Optional[AbstractRepresentation] = None
    result: Optional[ValidationResult] = None
    processing_log: list[str] = field(default_factory=list)

    def add_log(self, message: str):
        """Add a log entry with timestamp."""
        timestamp = datetime.now().isoformat()
        self.processing_log.append(f"[{timestamp}] {message}")
