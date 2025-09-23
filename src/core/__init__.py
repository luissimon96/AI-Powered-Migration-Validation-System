"""Core package for AI-Powered Migration Validation System.
"""

from .models import AbstractRepresentation
from .models import BackendFunction
from .models import DataField
from .models import InputData
from .models import InputType
from .models import MigrationValidationRequest
from .models import SeverityLevel
from .models import TechnologyContext
from .models import TechnologyType
from .models import UIElement
from .models import ValidationDiscrepancy
from .models import ValidationResult
from .models import ValidationScope
from .models import ValidationSession

__all__ = [
    "AbstractRepresentation",
    "BackendFunction",
    "DataField",
    "InputData",
    "InputType",
    "MigrationValidationRequest",
    "SeverityLevel",
    "TechnologyContext",
    "TechnologyType",
    "UIElement",
    "ValidationDiscrepancy",
    "ValidationResult",
    "ValidationScope",
    "ValidationSession",
]
