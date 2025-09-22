"""
Core package for AI-Powered Migration Validation System.
"""

from .models import (AbstractRepresentation, BackendFunction, DataField,
                     InputData, InputType, MigrationValidationRequest,
                     SeverityLevel, TechnologyContext, TechnologyType,
                     UIElement, ValidationDiscrepancy, ValidationResult,
                     ValidationScope, ValidationSession)

__all__ = [
    "TechnologyType",
    "ValidationScope",
    "InputType",
    "SeverityLevel",
    "TechnologyContext",
    "InputData",
    "UIElement",
    "BackendFunction",
    "DataField",
    "AbstractRepresentation",
    "ValidationDiscrepancy",
    "ValidationResult",
    "MigrationValidationRequest",
    "ValidationSession",
]
