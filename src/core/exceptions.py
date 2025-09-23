"""Production-ready exception handling for AI Migration Validation System.

Provides structured exception hierarchy with proper logging, context preservation,
and recovery mechanisms following SOLID principles.
"""

import asyncio
import sys
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

import structlog

logger = structlog.get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for prioritized handling."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for systematic classification."""

    VALIDATION = "validation"
    PROCESSING = "processing"
    CONFIGURATION = "configuration"
    EXTERNAL_SERVICE = "external_service"
    SECURITY = "security"
    RESOURCE = "resource"
    NETWORK = "network"
    DATA_INTEGRITY = "data_integrity"


class BaseValidationError(Exception):
    """Base exception for all migration validation errors.

    Provides structured error handling with context preservation,
    logging integration, and recovery guidance.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.PROCESSING,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        recoverable: bool = True,
        user_message: Optional[str] = None,
        **kwargs,
    ):
        """Initialize structured validation error.

        Args:
            message: Technical error message for developers
            error_code: Unique error identifier for tracking
            severity: Error severity for prioritization
            category: Error category for classification
            context: Additional context data
            cause: Root cause exception if available
            recoverable: Whether error allows retry/recovery
            user_message: User-friendly error message
            **kwargs: Additional error metadata

        """
        super().__init__(message)

        self.message = message
        self.error_code = error_code or self._generate_error_code()
        self.severity = severity
        self.category = category
        self.context = context or {}
        self.cause = cause
        self.recoverable = recoverable
        self.user_message = user_message or self._generate_user_message()
        self.metadata = kwargs
        self.timestamp = datetime.utcnow()
        self.traceback_info = self._capture_traceback()

        # Log error with full context
        self._log_error()

    def _generate_error_code(self) -> str:
        """Generate unique error code for tracking."""
        class_name = self.__class__.__name__
        timestamp = int(self.timestamp.timestamp() * 1000)
        return f"{class_name}_{timestamp}"

    def _generate_user_message(self) -> str:
        """Generate user-friendly error message."""
        return "An error occurred during migration validation. Please check your inputs and try again."

    def _capture_traceback(self) -> Dict[str, Any]:
        """Capture structured traceback information."""
        exc_type, exc_value, exc_traceback = sys.exc_info()

        if exc_traceback:
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            return {
                "formatted": "".join(tb_lines),
                "frames": [
                    {
                        "filename": frame.filename,
                        "function": frame.name,
                        "line_number": frame.lineno,
                        "code": frame.line,
                    }
                    for frame in traceback.extract_tb(exc_traceback)
                ],
            }
        return {}

    def _log_error(self) -> None:
        """Log error with structured context."""
        log_data = {
            "error_code": self.error_code,
            "error_class": self.__class__.__name__,
            "severity": self.severity.value,
            "category": self.category.value,
            "recoverable": self.recoverable,
            "context": self.context,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

        if self.cause:
            log_data["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause),
            }

        if self.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.error("Validation error occurred", **log_data)
        else:
            logger.warning("Validation warning", **log_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "recoverable": self.recoverable,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }

    def add_context(self, key: str, value: Any) -> None:
        """Add additional context to error."""
        self.context[key] = value

    def __str__(self) -> str:
        """String representation including error code."""
        return f"[{self.error_code}] {self.message}"


class ValidationInputError(BaseValidationError):
    """Error in validation request input data."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        self.field = field
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
            context={"field": field} if field else {},
            **kwargs,
        )

    def _generate_user_message(self) -> str:
        field_info = f" in field '{self.field}'" if self.field else ""
        return f"Invalid input{field_info}. Please check your data and try again."


class ConfigurationError(BaseValidationError):
    """System configuration error."""

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        self.config_key = config_key
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.CONFIGURATION,
            context={"config_key": config_key} if config_key else {},
            recoverable=False,
            **kwargs,
        )

    def _generate_user_message(self) -> str:
        return "System configuration error. Please contact support."


class ExternalServiceError(BaseValidationError):
    """Error communicating with external service."""

    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs,
    ):
        self.service = service
        self.status_code = status_code
        context = {}
        if service:
            context["service"] = service
        if status_code:
            context["status_code"] = status_code

        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.EXTERNAL_SERVICE,
            context=context,
            recoverable=True,
            **kwargs,
        )

    def _generate_user_message(self) -> str:
        service_info = f" ({self.service})" if self.service else ""
        return f"External service error{service_info}. Please try again later."


class SecurityError(BaseValidationError):
    """Security-related error."""

    def __init__(self, message: str, security_check: Optional[str] = None, **kwargs):
        self.security_check = security_check
        super().__init__(
            message,
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.SECURITY,
            context={"security_check": security_check} if security_check else {},
            recoverable=False,
            **kwargs,
        )

    def _generate_user_message(self) -> str:
        return "Security validation failed. Access denied."


class ResourceError(BaseValidationError):
    """Resource-related error (memory, disk, etc.)."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        current_usage: Optional[float] = None,
        limit: Optional[float] = None,
        **kwargs,
    ):
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.limit = limit

        context = {}
        if resource_type:
            context["resource_type"] = resource_type
        if current_usage is not None:
            context["current_usage"] = current_usage
        if limit is not None:
            context["limit"] = limit

        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.RESOURCE,
            context=context,
            recoverable=True,
            **kwargs,
        )

    def _generate_user_message(self) -> str:
        return "Resource limit exceeded. Please reduce input size or try again later."


class ProcessingError(BaseValidationError):
    """Error during migration validation processing."""

    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs,
    ):
        self.stage = stage
        self.operation = operation

        context = {}
        if stage:
            context["stage"] = stage
        if operation:
            context["operation"] = operation

        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.PROCESSING,
            context=context,
            recoverable=True,
            **kwargs,
        )

    def _generate_user_message(self) -> str:
        stage_info = f" during {self.stage}" if self.stage else ""
        return f"Processing error{stage_info}. Please try again."


class NetworkError(BaseValidationError):
    """Network connectivity error."""

    def __init__(
        self,
        message: str,
        endpoint: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        self.endpoint = endpoint
        self.timeout = timeout

        context = {}
        if endpoint:
            context["endpoint"] = endpoint
        if timeout:
            context["timeout"] = timeout

        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.NETWORK,
            context=context,
            recoverable=True,
            **kwargs,
        )

    def _generate_user_message(self) -> str:
        return "Network connectivity error. Please check your connection and try again."


class DataIntegrityError(BaseValidationError):
    """Data integrity or corruption error."""

    def __init__(
        self,
        message: str,
        data_source: Optional[str] = None,
        checksum: Optional[str] = None,
        **kwargs,
    ):
        self.data_source = data_source
        self.checksum = checksum

        context = {}
        if data_source:
            context["data_source"] = data_source
        if checksum:
            context["checksum"] = checksum

        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATA_INTEGRITY,
            context=context,
            recoverable=False,
            **kwargs,
        )

    def _generate_user_message(self) -> str:
        return "Data integrity error. Please verify your input files and try again."


# Convenience functions for common error scenarios
def validation_input_error(
    message: str,
    field: Optional[str] = None,
    **kwargs,
) -> ValidationInputError:
    """Create validation input error with proper context."""
    return ValidationInputError(message, field=field, **kwargs)


def configuration_error(
    message: str,
    config_key: Optional[str] = None,
    **kwargs,
) -> ConfigurationError:
    """Create configuration error with proper context."""
    return ConfigurationError(message, config_key=config_key, **kwargs)


def external_service_error(
    message: str,
    service: Optional[str] = None,
    status_code: Optional[int] = None,
    **kwargs,
) -> ExternalServiceError:
    """Create external service error with proper context."""
    return ExternalServiceError(
        message, service=service, status_code=status_code, **kwargs
    )


def security_error(
    message: str, security_check: Optional[str] = None, **kwargs
) -> SecurityError:
    """Create security error with proper context."""
    return SecurityError(message, security_check=security_check, **kwargs)


def resource_error(
    message: str,
    resource_type: Optional[str] = None,
    current_usage: Optional[float] = None,
    limit: Optional[float] = None,
    **kwargs,
) -> ResourceError:
    """Create resource error with proper context."""
    return ResourceError(
        message,
        resource_type=resource_type,
        current_usage=current_usage,
        limit=limit,
        **kwargs,
    )


def processing_error(
    message: str,
    stage: Optional[str] = None,
    operation: Optional[str] = None,
    **kwargs,
) -> ProcessingError:
    """Create processing error with proper context."""
    return ProcessingError(message, stage=stage, operation=operation, **kwargs)


def network_error(
    message: str,
    endpoint: Optional[str] = None,
    timeout: Optional[float] = None,
    **kwargs,
) -> NetworkError:
    """Create network error with proper context."""
    return NetworkError(message, endpoint=endpoint, timeout=timeout, **kwargs)


def data_integrity_error(
    message: str,
    data_source: Optional[str] = None,
    checksum: Optional[str] = None,
    **kwargs,
) -> DataIntegrityError:
    """Create data integrity error with proper context."""
    return DataIntegrityError(
        message, data_source=data_source, checksum=checksum, **kwargs
    )


# Error recovery utilities
class ErrorRecoveryManager:
    """Manages error recovery strategies and retry logic."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.logger = structlog.get_logger(__name__)

    async def execute_with_retry(
        self,
        operation,
        operation_name: str,
        recoverable_exceptions: List[Type[Exception]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Execute operation with retry logic for recoverable errors.

        Args:
            operation: Async operation to execute
            operation_name: Human-readable operation name
            recoverable_exceptions: List of exception types that allow retry
            context: Additional context for logging

        Returns:
            Operation result

        Raises:
            Last exception if all retries exhausted

        """
        if recoverable_exceptions is None:
            recoverable_exceptions = [
                ExternalServiceError,
                NetworkError,
                ResourceError,
                ProcessingError,
            ]

        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self.base_delay * (
                        2 ** (attempt - 1)
                    )  # Exponential backoff
                    await asyncio.sleep(delay)
                    self.logger.info(
                        "Retrying operation",
                        operation=operation_name,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        context=context or {},
                    )

                result = await operation()

                if attempt > 0:
                    self.logger.info(
                        "Operation succeeded after retry",
                        operation=operation_name,
                        successful_attempt=attempt + 1,
                        context=context or {},
                    )

                return result

            except Exception as e:
                last_exception = e

                # Check if error is recoverable
                is_recoverable = (
                    isinstance(e, BaseValidationError) and e.recoverable
                ) or any(isinstance(e, exc_type) for exc_type in recoverable_exceptions)

                if not is_recoverable or attempt == self.max_retries:
                    self.logger.error(
                        "Operation failed permanently",
                        operation=operation_name,
                        attempt=attempt + 1,
                        error=str(e),
                        recoverable=is_recoverable,
                        context=context or {},
                    )
                    break

                self.logger.warning(
                    "Operation failed, will retry",
                    operation=operation_name,
                    attempt=attempt + 1,
                    error=str(e),
                    context=context or {},
                )

        # Re-raise the last exception
        if last_exception:
            raise last_exception
