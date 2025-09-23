"""Base analyzer interface for feature extraction.

Defines the common interface for all analyzer implementations in the
migration validation system.
"""

from abc import ABC
from abc import abstractmethod
from typing import List

from ..core.models import AbstractRepresentation
from ..core.models import InputData
from ..core.models import TechnologyContext
from ..core.models import ValidationScope


class BaseAnalyzer(ABC):
    """Base class for all analyzers."""

    def __init__(self, technology_context: TechnologyContext):
        """Initialize analyzer with technology context."""
        self.technology_context = technology_context
        self.supported_scopes: List[ValidationScope] = []

    @abstractmethod
    async def analyze(
        self, input_data: InputData, scope: ValidationScope,
    ) -> AbstractRepresentation:
        """Analyze input data and extract abstract representation.

        Args:
            input_data: Input data to analyze
            scope: Validation scope to focus on

        Returns:
            Abstract representation of the analyzed system

        """

    @abstractmethod
    def supports_scope(self, scope: ValidationScope) -> bool:
        """Check if analyzer supports the given validation scope."""

    def get_supported_scopes(self) -> List[ValidationScope]:
        """Get list of supported validation scopes."""
        return self.supported_scopes.copy()


class AnalyzerError(Exception):
    """Base exception for analyzer errors."""


class UnsupportedScopeError(AnalyzerError):
    """Raised when analyzer doesn't support requested scope."""


class InvalidInputError(AnalyzerError):
    """Raised when input data is invalid or cannot be processed."""


class ExtractionError(AnalyzerError):
    """Raised when feature extraction fails."""
