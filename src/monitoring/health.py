"""System health checks and monitoring for I002.
Comprehensive health monitoring with dependency checks.
"""

import asyncio
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict

import redis

from src.core.config import get_validation_config
from src.monitoring.logging import structured_logger
from src.services.llm_service import LLMService


class HealthStatus(str, Enum):
    """Health check status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """Individual health check definition."""

    def __init__(self, name: str, check_func, timeout: float = 30.0,
                 critical: bool = True):
        self.name = name
        self.check_func = check_func
        self.timeout = timeout
        self.critical = critical
        self.last_result = None
        self.last_check_time = None

    async def execute(self) -> Dict[str, Any]:
        """Execute health check with timeout."""
        start_time = time.time()

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self.check_func(),
                timeout=self.timeout,
            )

            duration = time.time() - start_time

            self.last_result = {
                "status": HealthStatus.HEALTHY,
                "message": result.get("message", "OK"),
                "duration_ms": round(duration * 1000, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "details": result.get("details", {}),
                "critical": self.critical,
            }

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            self.last_result = {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Health check timed out after {self.timeout}s",
                "duration_ms": round(duration * 1000, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "details": {},
                "critical": self.critical,
            }

        except Exception as e:
            duration = time.time() - start_time
            self.last_result = {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Health check failed: {e!s}",
                "duration_ms": round(duration * 1000, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"error": str(e), "error_type": type(e).__name__},
                "critical": self.critical,
            }

        self.last_check_time = datetime.utcnow()
        return self.last_result


class SystemHealthMonitor:
    """Comprehensive system health monitoring."""

    def __init__(self):
        self.config = get_validation_config()
        self.health_checks: Dict[str, HealthCheck] = {}
        self._register_default_checks()

    def _register_default_checks(self):
        """Register default health checks."""
        # Redis connectivity
        self.register_check(
            "redis_connectivity",
            self._check_redis_connectivity,
            timeout=10.0,
            critical=True,
        )

        # Database connectivity
        self.register_check(
            "database_connectivity",
            self._check_database_connectivity,
            timeout=15.0,
            critical=True,
        )

        # LLM service availability
        self.register_check(
            "llm_service_availability",
            self._check_llm_service_availability,
            timeout=30.0,
            critical=False,  # LLM can be down temporarily
        )

        # Celery workers
        self.register_check(
            "celery_workers",
            self._check_celery_workers,
            timeout=10.0,
            critical=False,
        )

        # File system
        self.register_check(
            "file_system",
            self._check_file_system,
            timeout=5.0,
            critical=True,
        )

        # System resources
        self.register_check(
            "system_resources",
            self._check_system_resources,
            timeout=5.0,
            critical=False,
        )

        # Application configuration
        self.register_check(
            "configuration",
            self._check_configuration,
            timeout=2.0,
            critical=True,
        )

    def register_check(self, name: str, check_func, timeout: float = 30.0,
                       critical: bool = True):
        """Register a new health check."""
        self.health_checks[name] = HealthCheck(
            name=name,
            check_func=check_func,
            timeout=timeout,
            critical=critical,
        )

    async def check_health(self, include_details: bool = True) -> Dict[str, Any]:
        """Execute all health checks and return system status."""
        start_time = time.time()

        # Execute all health checks concurrently
        tasks = []
        for check in self.health_checks.values():
            tasks.append(check.execute())

        await asyncio.gather(*tasks, return_exceptions=True)

        # Compile results
        results = {}
        overall_status = HealthStatus.HEALTHY
        critical_failures = 0
        total_failures = 0

        for name, check in self.health_checks.items():
            results[name] = check.last_result

            if check.last_result["status"] != HealthStatus.HEALTHY:
                total_failures += 1
                if check.critical:
                    critical_failures += 1

        # Determine overall status
        if critical_failures > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif total_failures > 0:
            overall_status = HealthStatus.DEGRADED

        duration = time.time() - start_time

        health_report = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": round(duration * 1000, 2),
            "summary": {
                "total_checks": len(self.health_checks),
                "healthy_checks": len(self.health_checks) - total_failures,
                "failed_checks": total_failures,
                "critical_failures": critical_failures,
            },
        }

        if include_details:
            health_report["checks"] = results

        # Log health check results
        structured_logger.info(
            "Health check completed",
            event_type="health_check",
            overall_status=overall_status,
            total_checks=len(self.health_checks),
            failed_checks=total_failures,
            critical_failures=critical_failures,
            duration_ms=round(duration * 1000, 2),
        )

        return health_report

    async def _check_redis_connectivity(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                decode_responses=True,
                socket_timeout=5.0,
            )

            # Test connection
            await asyncio.get_event_loop().run_in_executor(
                None, redis_client.ping,
            )

            # Get info
            info = await asyncio.get_event_loop().run_in_executor(
                None, redis_client.info,
            )

            return {
                "message": "Redis connection healthy",
                "details": {
                    "redis_version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                },
            }

        except Exception as e:
            raise Exception(f"Redis connectivity failed: {e!s}")

    async def _check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            from src.database.integration import get_database_session

            # Test database connection
            async with get_database_session() as session:
                # Execute simple query
                result = await session.execute("SELECT 1 as test")
                row = result.fetchone()

                if row and row[0] == 1:
                    return {
                        "message": "Database connection healthy",
                        "details": {
                            "database_url": "***masked***",
                            "connection_test": "passed",
                        },
                    }
                raise Exception("Database query test failed")

        except Exception as e:
            raise Exception(f"Database connectivity failed: {e!s}")

    async def _check_llm_service_availability(self) -> Dict[str, Any]:
        """Check LLM service availability."""
        try:
            llm_service = LLMService()

            # Test simple LLM request
            test_prompt = "Test connectivity. Respond with 'OK'."
            response = await llm_service.generate_response(test_prompt)

            if response and len(response.strip()) > 0:
                return {
                    "message": "LLM service available",
                    "details": {
                        "provider": llm_service.current_provider,
                        "response_length": len(response),
                        "test_successful": True,
                    },
                }
            raise Exception("LLM service returned empty response")

        except Exception as e:
            raise Exception(f"LLM service check failed: {e!s}")

    async def _check_celery_workers(self) -> Dict[str, Any]:
        """Check Celery workers status."""
        try:
            from src.services.task_queue import celery_app

            # Get worker stats
            inspect = celery_app.control.inspect()
            active = await asyncio.get_event_loop().run_in_executor(
                None, inspect.active,
            )

            if active:
                worker_count = len(active.keys())
                total_active_tasks = sum(len(tasks) for tasks in active.values())

                return {
                    "message": f"{worker_count} Celery workers active",
                    "details": {
                        "worker_count": worker_count,
                        "active_tasks": total_active_tasks,
                        "workers": list(active.keys()),
                    },
                }
            raise Exception("No Celery workers found")

        except Exception as e:
            raise Exception(f"Celery workers check failed: {e!s}")

    async def _check_file_system(self) -> Dict[str, Any]:
        """Check file system health."""
        try:
            import os
            import shutil

            # Check upload directory
            upload_dir = self.config.settings.upload_dir
            os.makedirs(upload_dir, exist_ok=True)

            # Check disk space
            total, used, free = shutil.disk_usage(upload_dir)
            free_percent = (free / total) * 100

            if free_percent < 10:  # Less than 10% free space
                raise Exception(f"Low disk space: {free_percent:.1f}% free")

            return {
                "message": "File system healthy",
                "details": {
                    "upload_directory": upload_dir,
                    "free_space_percent": round(free_percent, 1),
                    "free_space_gb": round(free / (1024**3), 1),
                    "total_space_gb": round(total / (1024**3), 1),
                },
            }

        except Exception as e:
            raise Exception(f"File system check failed: {e!s}")

    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            import psutil

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Check thresholds
            alerts = []
            if memory_percent > 90:
                alerts.append(f"High memory usage: {memory_percent}%")
            if cpu_percent > 90:
                alerts.append(f"High CPU usage: {cpu_percent}%")

            status_message = "System resources healthy"
            if alerts:
                status_message = f"Resource alerts: {'; '.join(alerts)}"

            return {
                "message": status_message,
                "details": {
                    "memory_percent": memory_percent,
                    "memory_available_gb": round(memory.available / (1024**3), 1),
                    "cpu_percent": cpu_percent,
                    "alerts": alerts,
                },
            }

        except ImportError:
            return {
                "message": "System resource monitoring unavailable (psutil not installed)",
                "details": {},
            }
        except Exception as e:
            raise Exception(f"System resources check failed: {e!s}")

    async def _check_configuration(self) -> Dict[str, Any]:
        """Check application configuration."""
        try:
            config_status = []

            # Check required configuration
            if not self.config.get_default_llm_config():
                config_status.append("No LLM provider configured")

            if not self.config.settings.secret_key or self.config.settings.secret_key == "change-me-in-production":
                config_status.append("Default secret key in use")

            if self.config.settings.environment == "production" and self.config.settings.debug:
                config_status.append("Debug mode enabled in production")

            message = "Configuration healthy"
            if config_status:
                message = f"Configuration issues: {'; '.join(config_status)}"

            return {
                "message": message,
                "details": {
                    "environment": self.config.settings.environment,
                    "debug_mode": self.config.settings.debug,
                    "llm_providers_configured": len(
                        self.config.list_available_providers()),
                    "issues": config_status,
                },
            }

        except Exception as e:
            raise Exception(f"Configuration check failed: {e!s}")


# Global health monitor instance
health_monitor = SystemHealthMonitor()
