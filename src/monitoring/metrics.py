"""Prometheus metrics collection for I002 implementation.
Comprehensive system and business metrics monitoring.
"""

import time
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

from src.core.logging import logger


class MetricsCollector:
    """Central metrics collector for system monitoring."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self._initialize_metrics()

    def _initialize_metrics(self):
        """Initialize all system metrics."""
        # System Performance Metrics
        self.request_duration = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint", "status_code"],
            registry=self.registry,
        )

        self.request_count = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status_code"],
            registry=self.registry,
        )

        self.active_requests = Gauge(
            "http_requests_active",
            "Number of active HTTP requests",
            registry=self.registry,
        )

        # Validation Pipeline Metrics
        self.validation_requests = Counter(
            "validation_requests_total",
            "Total validation requests",
            ["source_tech", "target_tech", "scope", "status"],
            registry=self.registry,
        )

        self.validation_duration = Histogram(
            "validation_duration_seconds",
            "Validation processing duration",
            ["source_tech", "target_tech", "scope"],
            registry=self.registry,
        )

        self.validation_fidelity_score = Histogram(
            "validation_fidelity_score",
            "Validation fidelity scores",
            ["source_tech", "target_tech"],
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry,
        )

        # LLM Service Metrics
        self.llm_requests = Counter(
            "llm_requests_total",
            "Total LLM API requests",
            ["provider", "model", "status"],
            registry=self.registry,
        )

        self.llm_duration = Histogram(
            "llm_request_duration_seconds",
            "LLM API request duration",
            ["provider", "model"],
            registry=self.registry,
        )

        self.llm_tokens = Counter(
            "llm_tokens_total",
            "Total LLM tokens used",
            ["provider", "model", "type"],  # type: input/output
            registry=self.registry,
        )

        self.llm_cost = Counter(
            "llm_cost_usd_total",
            "Total LLM cost in USD",
            ["provider", "model"],
            registry=self.registry,
        )

        # Async Processing Metrics
        self.task_queue_size = Gauge(
            "celery_queue_size",
            "Number of tasks in queue",
            ["queue_name"],
            registry=self.registry,
        )

        self.task_processing_time = Histogram(
            "celery_task_duration_seconds",
            "Task processing duration",
            ["task_name", "status"],
            registry=self.registry,
        )

        self.worker_active_tasks = Gauge(
            "celery_worker_active_tasks",
            "Number of active tasks per worker",
            ["worker_name"],
            registry=self.registry,
        )

        # Cache Metrics
        self.cache_operations = Counter(
            "cache_operations_total",
            "Cache operations",
            ["operation", "result"],  # operation: get/set/delete, result: hit/miss/success
            registry=self.registry,
        )

        self.cache_size = Gauge(
            "cache_size_bytes",
            "Cache size in bytes",
            registry=self.registry,
        )

        # Database Metrics
        self.db_connections = Gauge(
            "database_connections_active",
            "Active database connections",
            registry=self.registry,
        )

        self.db_query_duration = Histogram(
            "database_query_duration_seconds",
            "Database query duration",
            ["operation", "table"],
            registry=self.registry,
        )

        # Error Metrics
        self.error_count = Counter(
            "errors_total",
            "Total errors",
            ["component", "error_type", "severity"],
            registry=self.registry,
        )

        # Business Metrics
        self.file_uploads = Counter(
            "file_uploads_total",
            "Total file uploads",
            ["file_type", "status"],
            registry=self.registry,
        )

        self.user_sessions = Counter(
            "user_sessions_total",
            "Total user sessions",
            ["auth_type", "status"],
            registry=self.registry,
        )

        # System Resource Metrics
        self.memory_usage = Gauge(
            "system_memory_usage_bytes",
            "System memory usage",
            registry=self.registry,
        )

        self.cpu_usage = Gauge(
            "system_cpu_usage_percent",
            "System CPU usage percentage",
            registry=self.registry,
        )

        # Application Info
        self.app_info = Info(
            "application_info",
            "Application information",
            registry=self.registry,
        )
        self.app_info.info({
            "version": "1.0.0",
            "environment": "production",
            "build_date": datetime.utcnow().isoformat(),
        })

    def track_request(self, method: str, endpoint: str):
        """Decorator to track HTTP request metrics."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                self.active_requests.inc()
                start_time = time.time()

                try:
                    result = func(*args, **kwargs)
                    status_code = getattr(result, "status_code", "200")

                    # Record success metrics
                    duration = time.time() - start_time
                    self.request_duration.labels(
                        method=method,
                        endpoint=endpoint,
                        status_code=status_code,
                    ).observe(duration)

                    self.request_count.labels(
                        method=method,
                        endpoint=endpoint,
                        status_code=status_code,
                    ).inc()

                    return result

                except Exception as e:
                    # Record error metrics
                    duration = time.time() - start_time
                    self.request_duration.labels(
                        method=method,
                        endpoint=endpoint,
                        status_code="500",
                    ).observe(duration)

                    self.request_count.labels(
                        method=method,
                        endpoint=endpoint,
                        status_code="500",
                    ).inc()

                    self.error_count.labels(
                        component="api",
                        error_type=type(e).__name__,
                        severity="error",
                    ).inc()

                    raise

                finally:
                    self.active_requests.dec()

            return wrapper
        return decorator

    def track_validation(self, source_tech: str, target_tech: str, scope: str):
        """Track validation request metrics."""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"

                try:
                    result = await func(*args, **kwargs)

                    # Track fidelity score if available
                    if hasattr(result, "result") and hasattr(result.result, "fidelity_score"):
                        self.validation_fidelity_score.labels(
                            source_tech=source_tech,
                            target_tech=target_tech,
                        ).observe(result.result.fidelity_score)

                    return result

                except Exception as e:
                    status = "error"
                    self.error_count.labels(
                        component="validation",
                        error_type=type(e).__name__,
                        severity="error",
                    ).inc()
                    raise

                finally:
                    duration = time.time() - start_time
                    self.validation_duration.labels(
                        source_tech=source_tech,
                        target_tech=target_tech,
                        scope=scope,
                    ).observe(duration)

                    self.validation_requests.labels(
                        source_tech=source_tech,
                        target_tech=target_tech,
                        scope=scope,
                        status=status,
                    ).inc()

            return async_wrapper
        return decorator

    def track_llm_request(self, provider: str, model: str):
        """Track LLM API request metrics."""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"

                try:
                    result = await func(*args, **kwargs)

                    # Track token usage if available
                    if hasattr(result, "usage"):
                        self.llm_tokens.labels(
                            provider=provider,
                            model=model,
                            type="input",
                        ).inc(result.usage.get("prompt_tokens", 0))

                        self.llm_tokens.labels(
                            provider=provider,
                            model=model,
                            type="output",
                        ).inc(result.usage.get("completion_tokens", 0))

                    # Estimate cost (simplified)
                    estimated_cost = self._estimate_llm_cost(provider, model, result)
                    if estimated_cost > 0:
                        self.llm_cost.labels(
                            provider=provider,
                            model=model,
                        ).inc(estimated_cost)

                    return result

                except Exception as e:
                    status = "error"
                    self.error_count.labels(
                        component="llm",
                        error_type=type(e).__name__,
                        severity="error",
                    ).inc()
                    raise

                finally:
                    duration = time.time() - start_time
                    self.llm_duration.labels(
                        provider=provider,
                        model=model,
                    ).observe(duration)

                    self.llm_requests.labels(
                        provider=provider,
                        model=model,
                        status=status,
                    ).inc()

            return async_wrapper
        return decorator

    def track_cache_operation(self, operation: str, result: str):
        """Track cache operation metrics."""
        self.cache_operations.labels(
            operation=operation,
            result=result,
        ).inc()

    def track_task_execution(self, task_name: str):
        """Track Celery task execution metrics."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "error"
                    self.error_count.labels(
                        component="celery",
                        error_type=type(e).__name__,
                        severity="error",
                    ).inc()
                    raise
                finally:
                    duration = time.time() - start_time
                    self.task_processing_time.labels(
                        task_name=task_name,
                        status=status,
                    ).observe(duration)

            return wrapper
        return decorator

    def update_system_metrics(self):
        """Update system resource metrics."""
        try:
            import psutil

            # Memory usage
            memory = psutil.virtual_memory()
            self.memory_usage.set(memory.used)

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.cpu_usage.set(cpu_percent)

        except ImportError:
            logger.warning("psutil not available for system metrics")

    def update_queue_metrics(self, queue_stats: Dict[str, Any]):
        """Update Celery queue metrics."""
        for queue_name, size in queue_stats.get("queue_sizes", {}).items():
            self.task_queue_size.labels(queue_name=queue_name).set(size)

        for worker_name, active_count in queue_stats.get("worker_tasks", {}).items():
            self.worker_active_tasks.labels(worker_name=worker_name).set(active_count)

    def update_cache_metrics(self, cache_stats: Dict[str, Any]):
        """Update cache metrics."""
        self.cache_size.set(cache_stats.get("memory_used_bytes", 0))

    def generate_metrics(self) -> str:
        """Generate Prometheus metrics output."""
        return generate_latest(self.registry)

    def _estimate_llm_cost(self, provider: str, model: str, result: Any) -> float:
        """Estimate LLM API cost (simplified calculation)."""
        if not hasattr(result, "usage"):
            return 0.0

        # Simplified cost estimation per 1K tokens
        cost_per_1k_tokens = {
            ("openai", "gpt-4"): 0.03,
            ("openai", "gpt-3.5-turbo"): 0.002,
            ("anthropic", "claude-3-sonnet"): 0.015,
            ("google", "gemini-pro"): 0.001,
        }

        rate = cost_per_1k_tokens.get((provider, model), 0.01)  # Default rate
        total_tokens = result.usage.get("total_tokens", 0)

        return (total_tokens / 1000) * rate


# Global metrics collector instance
metrics_collector = MetricsCollector()
