"""
Structured logging implementation for I002.
JSON-formatted logging with comprehensive context tracking.
"""

import json
import logging
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional, Union

import structlog

from src.core.config import get_validation_config


class StructuredLogger:
    """Structured logging with JSON output and context management."""

    def __init__(self, name: str = "migration_validator"):
        self.config = get_validation_config()
        self.logger_name = name
        self._configure_structlog()

    def _configure_structlog(self):
        """Configure structlog for JSON output."""
        
        # Configure stdlib logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, self.config.settings.log_level.upper())
        )

        # Configure structlog
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                self._add_service_context,
                self._add_request_id,
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, self.config.settings.log_level.upper())
            ),
            logger_factory=structlog.WriteLoggerFactory(),
            cache_logger_on_first_use=True,
        )

        self.logger = structlog.get_logger(self.logger_name)

    def _add_service_context(self, _, __, event_dict):
        """Add service-level context to all log entries."""
        event_dict.update({
            "service": "migration-validator",
            "version": "1.0.0",
            "environment": self.config.settings.environment,
            "hostname": self._get_hostname()
        })
        return event_dict

    def _add_request_id(self, _, __, event_dict):
        """Add request ID from context if available."""
        request_id = self._get_current_request_id()
        if request_id:
            event_dict["request_id"] = request_id
        return event_dict

    def _get_hostname(self) -> str:
        """Get system hostname."""
        import socket
        try:
            return socket.gethostname()
        except:
            return "unknown"

    def _get_current_request_id(self) -> Optional[str]:
        """Get current request ID from context."""
        try:
            import contextvars
            return getattr(contextvars, 'request_id', {}).get()
        except:
            return None

    @contextmanager
    def request_context(self, request_id: Optional[str] = None):
        """Context manager for request-scoped logging."""
        if request_id is None:
            request_id = str(uuid.uuid4())

        try:
            import contextvars
            token = contextvars.request_id.set(request_id) if hasattr(contextvars, 'request_id') else None
            yield request_id
        finally:
            if token:
                contextvars.request_id.reset(token)

    def info(self, message: str, **kwargs):
        """Log info level message."""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning level message."""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error level message."""
        self.logger.error(message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug level message."""
        self.logger.debug(message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical level message."""
        self.logger.critical(message, **kwargs)

    def log_request(self, method: str, path: str, status_code: int, 
                   duration: float, **kwargs):
        """Log HTTP request with structured format."""
        self.info(
            "HTTP request completed",
            http_method=method,
            http_path=path,
            http_status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )

    def log_validation_start(self, source_tech: str, target_tech: str, 
                           scope: str, file_count: int, **kwargs):
        """Log validation start."""
        self.info(
            "Validation started",
            event_type="validation_start",
            source_technology=source_tech,
            target_technology=target_tech,
            validation_scope=scope,
            file_count=file_count,
            **kwargs
        )

    def log_validation_complete(self, source_tech: str, target_tech: str,
                              fidelity_score: float, duration: float,
                              status: str, **kwargs):
        """Log validation completion."""
        self.info(
            "Validation completed",
            event_type="validation_complete",
            source_technology=source_tech,
            target_technology=target_tech,
            fidelity_score=fidelity_score,
            duration_seconds=duration,
            validation_status=status,
            **kwargs
        )

    def log_llm_request(self, provider: str, model: str, tokens_used: int,
                       duration: float, cost: float, **kwargs):
        """Log LLM API request."""
        self.info(
            "LLM request completed",
            event_type="llm_request",
            llm_provider=provider,
            llm_model=model,
            tokens_used=tokens_used,
            duration_seconds=duration,
            estimated_cost_usd=cost,
            **kwargs
        )

    def log_error(self, error: Exception, component: str, 
                 operation: str, **kwargs):
        """Log error with comprehensive context."""
        self.error(
            "Error occurred",
            event_type="error",
            error_type=type(error).__name__,
            error_message=str(error),
            component=component,
            operation=operation,
            **kwargs
        )

    def log_security_event(self, event_type: str, user_id: str,
                          ip_address: str, **kwargs):
        """Log security-related events."""
        self.warning(
            "Security event",
            event_type="security",
            security_event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            **kwargs
        )

    def log_performance_alert(self, metric_name: str, current_value: float,
                            threshold: float, **kwargs):
        """Log performance alerts."""
        self.warning(
            "Performance alert",
            event_type="performance_alert",
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            **kwargs
        )

    def log_business_event(self, event_type: str, **kwargs):
        """Log business-related events."""
        self.info(
            "Business event",
            event_type="business",
            business_event_type=event_type,
            **kwargs
        )


class LoggingMiddleware:
    """FastAPI middleware for request logging."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    async def __call__(self, request, call_next):
        """Process request with logging."""
        import time
        
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Add request ID to headers
        request.state.request_id = request_id

        try:
            with self.logger.request_context(request_id):
                self.logger.info(
                    "HTTP request started",
                    http_method=request.method,
                    http_path=request.url.path,
                    http_query=str(request.url.query) if request.url.query else None,
                    user_agent=request.headers.get('user-agent'),
                    client_ip=request.client.host if request.client else None
                )

                response = await call_next(request)
                
                duration = time.time() - start_time
                self.logger.log_request(
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration=duration
                )

                return response

        except Exception as e:
            duration = time.time() - start_time
            
            self.logger.log_error(
                error=e,
                component="http_middleware",
                operation="request_processing",
                http_method=request.method,
                http_path=request.url.path,
                duration_seconds=duration
            )
            
            # Re-raise to let FastAPI handle the error
            raise


class AlertManager:
    """Manage alerts and notifications."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.alert_thresholds = self._load_alert_thresholds()

    def _load_alert_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Load alert thresholds configuration."""
        return {
            "response_time": {
                "warning": 5.0,  # 5 seconds
                "critical": 10.0  # 10 seconds
            },
            "error_rate": {
                "warning": 0.05,  # 5%
                "critical": 0.10   # 10%
            },
            "queue_size": {
                "warning": 50,
                "critical": 100
            },
            "memory_usage": {
                "warning": 0.80,  # 80%
                "critical": 0.90   # 90%
            },
            "llm_cost": {
                "warning": 100.0,  # $100/day
                "critical": 200.0   # $200/day
            }
        }

    def check_response_time_alert(self, duration: float, endpoint: str):
        """Check for response time alerts."""
        thresholds = self.alert_thresholds["response_time"]
        
        if duration > thresholds["critical"]:
            self.logger.log_performance_alert(
                metric_name="response_time",
                current_value=duration,
                threshold=thresholds["critical"],
                severity="critical",
                endpoint=endpoint
            )
        elif duration > thresholds["warning"]:
            self.logger.log_performance_alert(
                metric_name="response_time",
                current_value=duration,
                threshold=thresholds["warning"],
                severity="warning",
                endpoint=endpoint
            )

    def check_queue_size_alert(self, queue_size: int, queue_name: str):
        """Check for queue size alerts."""
        thresholds = self.alert_thresholds["queue_size"]
        
        if queue_size > thresholds["critical"]:
            self.logger.log_performance_alert(
                metric_name="queue_size",
                current_value=queue_size,
                threshold=thresholds["critical"],
                severity="critical",
                queue_name=queue_name
            )
        elif queue_size > thresholds["warning"]:
            self.logger.log_performance_alert(
                metric_name="queue_size",
                current_value=queue_size,
                threshold=thresholds["warning"],
                severity="warning",
                queue_name=queue_name
            )

    def check_error_rate_alert(self, error_rate: float, component: str):
        """Check for error rate alerts."""
        thresholds = self.alert_thresholds["error_rate"]
        
        if error_rate > thresholds["critical"]:
            self.logger.log_performance_alert(
                metric_name="error_rate",
                current_value=error_rate,
                threshold=thresholds["critical"],
                severity="critical",
                component=component
            )
        elif error_rate > thresholds["warning"]:
            self.logger.log_performance_alert(
                metric_name="error_rate",
                current_value=error_rate,
                threshold=thresholds["warning"],
                severity="warning",
                component=component
            )


# Global instances
structured_logger = StructuredLogger()
alert_manager = AlertManager(structured_logger)