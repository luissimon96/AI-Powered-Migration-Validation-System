"""Core data models for AI-Powered Migration Validation System.

Defines the fundamental data structures for representing migration contexts,
validation results, and system operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


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
    framework_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InputData:
    """Represents input data for validation."""

    type: InputType
    files: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)  # For behavioral validation
    credentials: Optional[Dict[str, str]] = None  # For authenticated systems
    validation_scenarios: List[str] = field(default_factory=list)  # Behavioral test scenarios
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UIElement:
    """Represents a UI element extracted from code or screenshots."""

    type: str  # label, input, button, table, etc.
    id: Optional[str] = None
    text: Optional[str] = None
    position: Optional[Dict[str, int]] = None
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackendFunction:
    """Represents a backend function or method."""

    name: str
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    logic_summary: Optional[str] = None
    validation_rules: List[str] = field(default_factory=list)
    endpoint: Optional[str] = None
    http_method: Optional[str] = None


@dataclass
class DataField:
    """Represents a data field or property."""

    name: str
    type: str
    required: bool = False
    constraints: List[str] = field(default_factory=list)
    default_value: Optional[Any] = None


@dataclass
class AbstractRepresentation:
    """Abstract representation of a system component."""

    screen_name: Optional[str] = None
    ui_elements: List[UIElement] = field(default_factory=list)
    backend_functions: List[BackendFunction] = field(default_factory=list)
    data_fields: List[DataField] = field(default_factory=list)
    api_endpoints: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


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
    discrepancies: List[ValidationDiscrepancy] = field(default_factory=list)
    execution_time: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


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
    processing_log: List[str] = field(default_factory=list)

    def add_log(self, message: str):
        """Add a log entry with timestamp."""
        timestamp = datetime.now().isoformat()
        self.processing_log.append(f"[{timestamp}] {message}")
