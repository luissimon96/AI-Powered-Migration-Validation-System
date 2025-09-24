"""Monitoring API endpoints for I002 implementation.
Prometheus metrics, health checks, and observability endpoints.
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import PlainTextResponse
from src.monitoring.health import HealthStatus, health_monitor
from src.monitoring.logging import structured_logger
from src.monitoring.metrics import metrics_collector
from src.services.task_queue import async_validation_service

# Create router
router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health", response_model=dict[str, Any])
async def health_check(
    include_details: bool = Query(
        True, description="Include detailed health check results"
    ),
):
    """System health check endpoint.
    Returns overall system health status and individual component checks.
    """
    try:
        health_result = await health_monitor.check_health(
            include_details=include_details
        )

        # Determine HTTP status code based on health
        if health_result["status"] == HealthStatus.UNHEALTHY:
            status_code = 503  # Service Unavailable
        elif health_result["status"] == HealthStatus.DEGRADED:
            status_code = 200  # OK but with warnings
        else:
            status_code = 200  # OK

        return Response(
            content=health_result,
            status_code=status_code,
            media_type="application/json",
        )

    except Exception as e:
        structured_logger.log_error(
            error=e,
            component="health_endpoint",
            operation="health_check",
        )
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe endpoint.
    Simple check that the application is running.
    """
    return {"status": "alive", "timestamp": "now"}


@router.get("/health/ready")
async def readiness_probe():
    """Kubernetes readiness probe endpoint.
    Checks if the application is ready to serve traffic.
    """
    try:
        # Quick health check for critical components only
        critical_checks = ["redis_connectivity", "configuration"]

        for check_name in critical_checks:
            if check_name in health_monitor.health_checks:
                check = health_monitor.health_checks[check_name]
                result = await check.execute()

                if result["status"] != HealthStatus.HEALTHY:
                    return Response(
                        content={
                            "status": "not_ready",
                            "reason": f"{check_name} unhealthy",
                        },
                        status_code=503,
                    )

        return {"status": "ready", "timestamp": "now"}

    except Exception as e:
        return Response(
            content={"status": "not_ready", "reason": str(e)},
            status_code=503,
        )


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus metrics endpoint.
    Returns metrics in Prometheus format.
    """
    try:
        # Update dynamic metrics before returning
        metrics_collector.update_system_metrics()

        # Get queue stats and update metrics
        queue_stats = async_validation_service.get_queue_stats()
        metrics_collector.update_queue_metrics(queue_stats)

        # Get cache stats and update metrics
        cache_stats = (
            async_validation_service.result_cache._get_cache_stats()
            if hasattr(async_validation_service.result_cache, "_get_cache_stats")
            else {}
        )
        metrics_collector.update_cache_metrics(cache_stats)

        # Generate Prometheus metrics
        metrics_output = metrics_collector.generate_metrics()

        return Response(
            content=metrics_output,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    except Exception as e:
        structured_logger.log_error(
            error=e,
            component="metrics_endpoint",
            operation="generate_metrics",
        )
        raise HTTPException(status_code=500, detail="Metrics generation failed")


@router.get("/metrics/custom")
async def custom_metrics(
    metric_names: Optional[list[str]] = Query(
        None, description="Specific metrics to return"
    ),
):
    """Custom metrics endpoint for specific metric queries.
    Returns structured JSON metrics data.
    """
    try:
        # This would be implemented to return specific metrics in JSON format
        # for custom dashboards or integrations

        custom_data = {
            "timestamp": "now",
            "metrics": {
                "validation_stats": {
                    "total_validations": "Counter data would go here",
                    "avg_fidelity_score": "Average calculation",
                    "popular_tech_pairs": "Top technology pairs",
                },
                "performance_stats": {
                    "avg_response_time": "Response time metrics",
                    "error_rate": "Error rate calculation",
                    "throughput": "Requests per second",
                },
                "resource_usage": {
                    "cpu_percent": "CPU usage percentage",
                    "memory_usage": "Memory usage metrics",
                    "disk_usage": "Disk usage metrics",
                },
            },
        }

        return custom_data

    except Exception as e:
        structured_logger.log_error(
            error=e,
            component="custom_metrics_endpoint",
            operation="generate_custom_metrics",
        )
        raise HTTPException(status_code=500, detail="Custom metrics generation failed")


@router.get("/status")
async def system_status():
    """Comprehensive system status endpoint.
    Returns detailed system information for dashboards.
    """
    try:
        # Get health status
        health_result = await health_monitor.check_health(include_details=False)

        # Get queue statistics
        queue_stats = async_validation_service.get_queue_stats()

        # Compile comprehensive status
        status = {
            "system": {
                "status": health_result["status"],
                "uptime": "Would calculate uptime here",
                "version": "1.0.0",
                "environment": health_monitor.config.settings.environment,
            },
            "health": {
                "overall_status": health_result["status"],
                "healthy_checks": health_result["summary"]["healthy_checks"],
                "total_checks": health_result["summary"]["total_checks"],
                "critical_failures": health_result["summary"]["critical_failures"],
            },
            "performance": {
                "active_requests": "Would get from metrics",
                "avg_response_time": "Would calculate from metrics",
                "error_rate": "Would calculate from metrics",
            },
            "queue": {
                "active_tasks": queue_stats["active_tasks"],
                "scheduled_tasks": queue_stats["scheduled_tasks"],
                "worker_count": len(queue_stats["workers"]),
                "queue_health": "healthy"
                if queue_stats["active_tasks"] < 50
                else "busy",
            },
            "resources": {
                "memory_usage": "Would get from system metrics",
                "cpu_usage": "Would get from system metrics",
                "disk_usage": "Would get from system metrics",
            },
        }

        return status

    except Exception as e:
        structured_logger.log_error(
            error=e,
            component="status_endpoint",
            operation="get_system_status",
        )
        raise HTTPException(status_code=500, detail="Status retrieval failed")


@router.post("/health/check/{check_name}")
async def run_individual_health_check(check_name: str):
    """Run a specific health check on demand.
    Useful for debugging and manual verification.
    """
    try:
        if check_name not in health_monitor.health_checks:
            raise HTTPException(
                status_code=404,
                detail=f"Health check '{check_name}' not found",
            )

        check = health_monitor.health_checks[check_name]
        result = await check.execute()

        return {
            "check_name": check_name,
            "result": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        structured_logger.log_error(
            error=e,
            component="individual_health_check",
            operation=f"check_{check_name}",
        )
        raise HTTPException(
            status_code=500, detail=f"Health check '{check_name}' failed"
        )


@router.get("/alerts")
async def get_active_alerts(
    severity: Optional[str] = Query(
        None, description="Filter by severity: warning, critical"
    ),
):
    """Get active system alerts.
    Returns current alerts and warnings from monitoring systems.
    """
    try:
        # This would integrate with actual alerting system
        # For now, return example structure

        alerts = {
            "active_alerts": [],
            "total_count": 0,
            "by_severity": {
                "critical": 0,
                "warning": 0,
                "info": 0,
            },
            "timestamp": "now",
        }

        # Example alerts would be populated here based on metrics thresholds
        # and health check results

        return alerts

    except Exception as e:
        structured_logger.log_error(
            error=e,
            component="alerts_endpoint",
            operation="get_active_alerts",
        )
        raise HTTPException(status_code=500, detail="Alert retrieval failed")


@router.post("/alerts/acknowledge/{alert_id}")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an active alert.
    Marks the alert as acknowledged to prevent duplicate notifications.
    """
    try:
        # This would integrate with alerting system to acknowledge alerts

        structured_logger.log_business_event(
            event_type="alert_acknowledged",
            alert_id=alert_id,
            acknowledged_by="system",  # Would get from auth context
        )

        return {
            "alert_id": alert_id,
            "status": "acknowledged",
            "timestamp": "now",
        }

    except Exception as e:
        structured_logger.log_error(
            error=e,
            component="alerts_endpoint",
            operation="acknowledge_alert",
            alert_id=alert_id,
        )
        raise HTTPException(status_code=500, detail="Alert acknowledgment failed")


@router.get("/logs/recent")
async def get_recent_logs(
    limit: int = Query(100, description="Number of recent log entries to return"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    component: Optional[str] = Query(None, description="Filter by component"),
):
    """Get recent log entries.
    Useful for real-time log viewing and debugging.
    """
    try:
        # This would integrate with log aggregation system
        # For now, return example structure

        logs = {
            "entries": [],
            "total_count": 0,
            "filters": {
                "level": level,
                "component": component,
                "limit": limit,
            },
            "timestamp": "now",
        }

        # Recent log entries would be populated here from log storage

        return logs

    except Exception as e:
        structured_logger.log_error(
            error=e,
            component="logs_endpoint",
            operation="get_recent_logs",
        )
        raise HTTPException(status_code=500, detail="Log retrieval failed")
