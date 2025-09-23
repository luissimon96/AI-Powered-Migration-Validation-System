"""
Production-ready structured logging configuration for AI Migration Validation System.

Implements comprehensive logging with structured output, context preservation,
security filtering, and performance monitoring.
"""

import asyncio
import logging
import logging.config
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import structlog
from structlog.types import FilteringBoundLogger, WrappedLogger

# Security: Sensitive fields to filter from logs
SENSITIVE_FIELDS = {
    "password",
    "token",
    "api_key",
    "secret",
    "key",
    "authorization",
    "auth",
    "credential",
    "session_id",
    "cookie",
    "csrf_token",
}


class SecurityFilter:
    """Filter sensitive information from log records."""

    def __init__(self, sensitive_fields: Optional[set] = None):
        self.sensitive_fields = sensitive_fields or SENSITIVE_FIELDS

    def __call__(
        self, logger: WrappedLogger, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Filter sensitive data from event dictionary."""
        return self._filter_sensitive_data(event_dict)

    def _filter_sensitive_data(self, data: Any) -> Any:
        """Recursively filter sensitive data from nested structures."""
        if isinstance(data, dict):
            return {key: self._filter_value(key, value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._filter_sensitive_data(item) for item in data]
        return data

    def _filter_value(self, key: str, value: Any) -> Any:
        """Filter individual value based on key name."""
        if isinstance(key, str) and any(
            sensitive in key.lower() for sensitive in self.sensitive_fields
        ):
            if isinstance(value, str):
                return "*" * min(len(value), 8) if value else ""
            return "***FILTERED***"

        if isinstance(value, (dict, list)):
            return self._filter_sensitive_data(value)

        return value


class PerformanceMonitor:
    """Monitor and log performance metrics."""

    def __call__(
        self, logger: WrappedLogger, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add performance context to log events."""
        if "duration" in event_dict or "execution_time" in event_dict:
            # Add performance category for analytics
            event_dict["category"] = "performance"

            # Add performance thresholds
            duration = event_dict.get("duration") or event_dict.get("execution_time")
            if duration:
                if duration > 10.0:
                    event_dict["performance_alert"] = "slow_operation"
                elif duration > 30.0:
                    event_dict["performance_alert"] = "very_slow_operation"

        return event_dict


class RequestTracker:
    """Track request context across async operations."""

    def __init__(self):
        self._context: Dict[str, Any] = {}

    def __call__(
        self, logger: WrappedLogger, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add request context to log events."""
        # Add request context if available
        try:
            task = asyncio.current_task()
            if task and hasattr(task, "request_id"):
                event_dict["request_id"] = task.request_id
            if task and hasattr(task, "user_id"):
                event_dict["user_id"] = task.user_id
        except RuntimeError:
            # No event loop running
            pass

        return event_dict


def configure_structlog(
    log_level: Union[str, int] = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    enable_colors: bool = True,
    include_stdlib: bool = True,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format ("json", "console", "human")
        log_file: Optional log file path
        enable_colors: Enable colored output for console
        include_stdlib: Include standard library logging
    """
    # Convert string level to int
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper())

    # Configure processors
    processors: List[Any] = [
        # Add timestamp
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Custom processors
        SecurityFilter(),
        PerformanceMonitor(),
        RequestTracker(),
        # Context processors
        structlog.contextvars.merge_contextvars,
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    # Add format-specific processors
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    elif log_format == "console":
        processors.extend(
            [
                structlog.processors.add_log_level,
                structlog.dev.ConsoleRenderer(colors=enable_colors),
            ]
        )
    else:  # human-readable
        processors.extend(
            [
                structlog.processors.add_log_level,
                structlog.dev.ConsoleRenderer(colors=enable_colors),
            ]
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging if requested
    if include_stdlib:
        configure_stdlib_logging(log_level, log_file)


def configure_stdlib_logging(log_level: int, log_file: Optional[str] = None) -> None:
    """Configure standard library logging integration."""
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    handlers.append(console_handler)

    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        format="%(message)s",  # structlog handles formatting
    )

    # Set levels for noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


class LoggerMixin:
    """Mixin class to add structured logging to any class."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.logger = structlog.get_logger(cls.__module__ + "." + cls.__name__)

    @property
    def logger(self) -> FilteringBoundLogger:
        """Get logger instance for this class."""
        if not hasattr(self, "_logger"):
            self._logger = structlog.get_logger(
                self.__class__.__module__ + "." + self.__class__.__name__
            )
        return self._logger


class OperationLogger:
    """Context manager for logging operations with timing and error handling."""

    def __init__(
        self,
        logger: FilteringBoundLogger,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        log_args: bool = False,
        log_result: bool = False,
    ):
        self.logger = logger
        self.operation = operation
        self.context = context or {}
        self.log_args = log_args
        self.log_result = log_result
        self.start_time: Optional[float] = None

    def __enter__(self):
        """Start operation logging."""
        self.start_time = time.time()
        self.logger.info("Operation started", operation=self.operation, **self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Complete operation logging."""
        duration = time.time() - (self.start_time or 0)

        if exc_type is None:
            self.logger.info(
                "Operation completed successfully",
                operation=self.operation,
                duration=duration,
                **self.context,
            )
        else:
            self.logger.error(
                "Operation failed",
                operation=self.operation,
                duration=duration,
                error=str(exc_val),
                error_type=exc_type.__name__,
                **self.context,
            )

    async def __aenter__(self):
        """Async context manager entry."""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        return self.__exit__(exc_type, exc_val, exc_tb)

    def add_context(self, **kwargs) -> None:
        """Add additional context to the operation."""
        self.context.update(kwargs)


def get_logger(name: str) -> FilteringBoundLogger:
    """Get configured logger instance."""
    return structlog.get_logger(name)


def log_operation(
    operation: str,
    context: Optional[Dict[str, Any]] = None,
    log_args: bool = False,
    log_result: bool = False,
):
    """
    Decorator for automatic operation logging.

    Args:
        operation: Operation name for logging
        context: Additional context to include
        log_args: Whether to log function arguments
        log_result: Whether to log function result
    """

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            async def async_wrapper(*args, **kwargs):
                logger = get_logger(func.__module__)
                log_context = dict(context or {})

                if log_args:
                    log_context["args"] = args
                    log_context["kwargs"] = kwargs

                async with OperationLogger(
                    logger, operation, log_context, log_args, log_result
                ) as op_logger:
                    result = await func(*args, **kwargs)

                    if log_result:
                        op_logger.add_context(result=result)

                    return result

            return async_wrapper
        else:

            def sync_wrapper(*args, **kwargs):
                logger = get_logger(func.__module__)
                log_context = dict(context or {})

                if log_args:
                    log_context["args"] = args
                    log_context["kwargs"] = kwargs

                with OperationLogger(
                    logger, operation, log_context, log_args, log_result
                ) as op_logger:
                    result = func(*args, **kwargs)

                    if log_result:
                        op_logger.add_context(result=result)

                    return result

            return sync_wrapper

    return decorator


# Performance monitoring utilities
class PerformanceTimer:
    """Context manager for measuring execution time."""

    def __init__(self, name: str, logger: Optional[FilteringBoundLogger] = None):
        self.name = name
        self.logger = logger or get_logger(__name__)
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - (self.start_time or 0)
        self.logger.info(
            "Performance measurement",
            operation=self.name,
            duration=duration,
            duration_ms=duration * 1000,
        )


def measure_performance(name: str):
    """Decorator for automatic performance measurement."""

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            async def async_wrapper(*args, **kwargs):
                with PerformanceTimer(name):
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            def sync_wrapper(*args, **kwargs):
                with PerformanceTimer(name):
                    return func(*args, **kwargs)

            return sync_wrapper

    return decorator


# Initialize logging on module import
def initialize_logging():
    """Initialize logging with environment-based configuration."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_format = os.getenv("LOG_FORMAT", "json")
    log_file = os.getenv("LOG_FILE")
    enable_colors = os.getenv("LOG_COLORS", "true").lower() == "true"

    configure_structlog(
        log_level=log_level,
        log_format=log_format,
        log_file=log_file,
        enable_colors=enable_colors,
    )


# Auto-initialize if not in test environment
if "pytest" not in sys.modules and not os.getenv("TESTING"):
    initialize_logging()
