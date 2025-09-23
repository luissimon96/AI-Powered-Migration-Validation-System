"""
Async API routes for P001 implementation.
Real-time validation with progress tracking and WebSocket support.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.core.models import ValidationRequest
from src.services.task_queue import async_validation_service, AsyncValidationService
from src.api.middleware import validate_request
from src.core.logging import logger


# Request/Response models
class AsyncValidationResponse(BaseModel):
    """Response for async validation submission."""
    task_id: str
    status: str = "accepted"
    message: str = "Validation task submitted"
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in seconds")
    progress_url: str
    websocket_url: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """Response for task status queries."""
    task_id: str
    status: str
    progress: int = Field(0, ge=0, le=100)
    stage: str
    message: str
    updated_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cached: bool = False
    estimated_remaining: Optional[int] = Field(None, description="Estimated remaining seconds")


class QueueStatsResponse(BaseModel):
    """Response for queue statistics."""
    active_tasks: int
    scheduled_tasks: int
    reserved_tasks: int
    workers: list
    queue_health: str
    cache_stats: Dict[str, Any]


# Create router
router = APIRouter(prefix="/api/async", tags=["async-validation"])


@router.post("/validate", response_model=AsyncValidationResponse)
async def submit_async_validation(
    request: ValidationRequest,
    validation_service: AsyncValidationService = Depends(lambda: async_validation_service)
):
    """Submit validation request for async processing."""
    try:
        # Validate request
        await validate_request(request.dict())
        
        # Submit to task queue
        task_id = validation_service.submit_validation_task(request)
        
        # Estimate duration based on file count and complexity
        estimated_duration = _estimate_validation_duration(request)
        
        response = AsyncValidationResponse(
            task_id=task_id,
            estimated_duration=estimated_duration,
            progress_url=f"/api/async/validate/{task_id}/status",
            websocket_url=f"/api/async/validate/{task_id}/progress"
        )
        
        logger.info("Async validation submitted", task_id=task_id)
        return response
        
    except Exception as e:
        logger.error("Failed to submit async validation", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to submit validation: {str(e)}")


@router.get("/validate/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    validation_service: AsyncValidationService = Depends(lambda: async_validation_service)
):
    """Get current status of validation task."""
    try:
        status_info = validation_service.get_task_status(task_id)
        
        if not status_info:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Estimate remaining time
        estimated_remaining = None
        if status_info['status'] in ['PENDING', 'STARTED'] and status_info['progress'] > 0:
            estimated_remaining = _estimate_remaining_time(status_info['progress'])
        
        response = TaskStatusResponse(
            **status_info,
            estimated_remaining=estimated_remaining
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.delete("/validate/{task_id}")
async def cancel_task(
    task_id: str,
    validation_service: AsyncValidationService = Depends(lambda: async_validation_service)
):
    """Cancel a running validation task."""
    try:
        success = validation_service.cancel_task(task_id)
        
        if success:
            logger.info("Task cancelled", task_id=task_id)
            return {"message": "Task cancelled successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel task")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel task", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats(
    validation_service: AsyncValidationService = Depends(lambda: async_validation_service)
):
    """Get queue statistics and health information."""
    try:
        queue_stats = validation_service.get_queue_stats()
        
        # Determine queue health
        total_tasks = queue_stats['active_tasks'] + queue_stats['scheduled_tasks']
        if total_tasks > 50:
            queue_health = "overloaded"
        elif total_tasks > 20:
            queue_health = "busy"
        elif len(queue_stats['workers']) == 0:
            queue_health = "no_workers"
        else:
            queue_health = "healthy"
        
        # Get cache statistics
        cache_stats = _get_cache_statistics()
        
        response = QueueStatsResponse(
            **queue_stats,
            queue_health=queue_health,
            cache_stats=cache_stats
        )
        
        return response
        
    except Exception as e:
        logger.error("Failed to get queue stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get queue stats: {str(e)}")


@router.websocket("/validate/{task_id}/progress")
async def websocket_task_progress(
    websocket: WebSocket,
    task_id: str,
    validation_service: AsyncValidationService = Depends(lambda: async_validation_service)
):
    """WebSocket endpoint for real-time task progress."""
    await websocket.accept()
    
    try:
        last_progress = -1
        
        while True:
            try:
                # Get current task status
                status_info = validation_service.get_task_status(task_id)
                
                if not status_info:
                    await websocket.send_json({
                        "error": "Task not found",
                        "code": "TASK_NOT_FOUND"
                    })
                    break
                
                # Only send update if progress changed
                current_progress = status_info.get('progress', 0)
                if current_progress != last_progress:
                    await websocket.send_json({
                        "task_id": task_id,
                        "progress": current_progress,
                        "stage": status_info.get('stage', ''),
                        "message": status_info.get('message', ''),
                        "status": status_info.get('status', ''),
                        "timestamp": datetime.utcnow().isoformat(),
                        "cached": status_info.get('cached', False)
                    })
                    last_progress = current_progress
                
                # Check if task is complete
                if status_info.get('status') in ['SUCCESS', 'FAILURE', 'REVOKED']:
                    if status_info.get('status') == 'SUCCESS':
                        await websocket.send_json({
                            "task_id": task_id,
                            "progress": 100,
                            "stage": "completed",
                            "message": "Validation completed successfully",
                            "status": "SUCCESS",
                            "result": status_info.get('result'),
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    break
                
                # Wait before next check
                await asyncio.sleep(1)
                
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected", task_id=task_id)
                break
            except Exception as e:
                logger.error("WebSocket error", task_id=task_id, error=str(e))
                await websocket.send_json({
                    "error": "Internal error",
                    "message": str(e)
                })
                break
                
    except Exception as e:
        logger.error("WebSocket connection error", task_id=task_id, error=str(e))
    finally:
        try:
            await websocket.close()
        except:
            pass


@router.post("/cache/invalidate")
async def invalidate_cache(
    pattern: str = "validation_cache:*",
    validation_service: AsyncValidationService = Depends(lambda: async_validation_service)
):
    """Invalidate cache entries."""
    try:
        count = validation_service.result_cache.invalidate_cache(pattern)
        logger.info("Cache invalidated", pattern=pattern, count=count)
        return {"message": f"Invalidated {count} cache entries"}
        
    except Exception as e:
        logger.error("Failed to invalidate cache", pattern=pattern, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to invalidate cache: {str(e)}")


# Helper functions
def _estimate_validation_duration(request: ValidationRequest) -> int:
    """Estimate validation duration based on request complexity."""
    base_duration = 30  # Base 30 seconds
    
    # Factor in file count
    file_count = len(request.source_files) + len(request.target_files)
    file_factor = min(file_count * 2, 60)  # Max 60 seconds for files
    
    # Factor in validation scope
    scope_factors = {
        "business_logic": 1.0,
        "code_structure": 0.8,
        "user_interface": 1.2,
        "data_structure": 0.9,
        "full_system": 1.5
    }
    scope_factor = scope_factors.get(request.validation_scope.value, 1.0)
    
    # Factor in technology complexity
    complex_techs = ["java-spring", "dotnet-core", "python-django"]
    complexity_factor = 1.2 if (
        request.source_technology in complex_techs or 
        request.target_technology in complex_techs
    ) else 1.0
    
    total_duration = int(base_duration * scope_factor * complexity_factor) + file_factor
    return min(total_duration, 300)  # Cap at 5 minutes


def _estimate_remaining_time(progress: int) -> int:
    """Estimate remaining time based on current progress."""
    if progress >= 95:
        return 10  # Final processing
    elif progress >= 80:
        return 30
    elif progress >= 50:
        return 60
    elif progress >= 20:
        return 120
    else:
        return 180


def _get_cache_statistics() -> Dict[str, Any]:
    """Get cache statistics."""
    try:
        from src.services.task_queue import result_cache
        redis_client = result_cache.redis
        
        # Get Redis info
        info = redis_client.info('memory')
        keyspace_info = redis_client.info('keyspace')
        
        cache_keys_count = 0
        if 'db1' in keyspace_info:  # Cache uses db1
            db1_info = keyspace_info['db1']
            cache_keys_count = db1_info.get('keys', 0)
        
        return {
            "total_keys": cache_keys_count,
            "memory_used": info.get('used_memory_human', '0B'),
            "hit_rate": "N/A",  # Would need to implement hit rate tracking
            "enabled": True
        }
    except Exception:
        return {
            "total_keys": 0,
            "memory_used": "0B",
            "hit_rate": "N/A",
            "enabled": False
        }


# Import asyncio for sleep
import asyncio