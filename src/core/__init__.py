"""
Core package for AI-Powered Migration Validation System.
"""

from .models import (
    TechnologyType,
    ValidationScope,
    InputType,
    SeverityLevel,
    TechnologyContext,
    InputData,
    UIElement,
    BackendFunction,
    DataField,
    AbstractRepresentation,
    ValidationDiscrepancy,
    ValidationResult,
    MigrationValidationRequest,
    ValidationSession,
)

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