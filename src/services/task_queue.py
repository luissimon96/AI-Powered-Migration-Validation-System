"""
Async processing and task queue implementation for P001.
Redis-based Celery task queue with progress tracking.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import uuid4

import redis
from celery import Celery
from celery.result import AsyncResult
from celery.signals import task_prerun, task_postrun, task_failure
from kombu import Queue

from src.core.models import ValidationRequest, ValidationSession, ValidationStatus
from src.core.migration_validator import MigrationValidator
from src.services.llm_service import LLMService
from src.core.config import get_validation_config


# Celery app configuration
config = get_validation_config()
celery_app = Celery(
    'migration_validator',
    broker=f'redis://{config.redis_host}:{config.redis_port}/{config.redis_db}',
    backend=f'redis://{config.redis_host}:{config.redis_port}/{config.redis_db}'
)

# Task routing configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes
    task_soft_time_limit=1500,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_default_queue='default',
    task_routes={
        'src.services.task_queue.validate_migration_async': {'queue': 'validation'},
        'src.services.task_queue.analyze_code_async': {'queue': 'analysis'},
        'src.services.task_queue.compare_semantics_async': {'queue': 'comparison'},
    },
    task_queues=(
        Queue('default', routing_key='default'),
        Queue('validation', routing_key='validation'),
        Queue('analysis', routing_key='analysis'),  
        Queue('comparison', routing_key='comparison'),
        Queue('priority', routing_key='priority'),
    ),
)


class TaskProgressManager:
    """Manage task progress tracking via Redis."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            decode_responses=True
        )

    def update_progress(
        self, 
        task_id: str, 
        progress: int, 
        stage: str, 
        message: str = "",
        metadata: Dict[str, Any] = None
    ) -> None:
        """Update task progress."""
        progress_data = {
            'task_id': task_id,
            'progress': min(100, max(0, progress)),
            'stage': stage,
            'message': message,
            'updated_at': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        # Store in Redis with 1 hour expiry
        self.redis.setex(
            f"task_progress:{task_id}",
            3600,
            json.dumps(progress_data)
        )

    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task progress."""
        data = self.redis.get(f"task_progress:{task_id}")
        return json.loads(data) if data else None

    def clear_progress(self, task_id: str) -> None:
        """Clear task progress data."""
        self.redis.delete(f"task_progress:{task_id}")


class TaskResultCache:
    """Cache task results to reduce redundant processing."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db + 1,  # Use different DB for cache
            decode_responses=True
        )

    def get_cache_key(self, request: ValidationRequest) -> str:
        """Generate cache key for validation request."""
        import hashlib
        
        # Create deterministic hash from request data
        request_str = json.dumps(request.dict(), sort_keys=True)
        return f"validation_cache:{hashlib.md5(request_str.encode()).hexdigest()}"

    def get_cached_result(self, request: ValidationRequest) -> Optional[ValidationSession]:
        """Get cached validation result."""
        cache_key = self.get_cache_key(request)
        cached_data = self.redis.get(cache_key)
        
        if cached_data:
            try:
                data = json.loads(cached_data)
                # Convert back to ValidationSession object
                return ValidationSession.from_dict(data)
            except (json.JSONDecodeError, AttributeError):
                self.redis.delete(cache_key)
        
        return None

    def cache_result(
        self, 
        request: ValidationRequest, 
        session: ValidationSession,
        ttl: int = 3600  # 1 hour default
    ) -> None:
        """Cache validation result."""
        cache_key = self.get_cache_key(request)
        
        try:
            # Convert session to dict for JSON serialization
            session_data = session.to_dict()
            self.redis.setex(cache_key, ttl, json.dumps(session_data))
        except Exception as e:
            # Log error but don't fail the request
            print(f"Cache error: {e}")

    def invalidate_cache(self, pattern: str = "validation_cache:*") -> int:
        """Invalidate cache entries matching pattern."""
        keys = self.redis.keys(pattern)
        return self.redis.delete(*keys) if keys else 0


# Global instances
progress_manager = TaskProgressManager()
result_cache = TaskResultCache()


@celery_app.task(bind=True, name='validate_migration_async')
def validate_migration_async(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Async validation task with progress tracking."""
    task_id = self.request.id
    
    try:
        # Parse request
        request = ValidationRequest.from_dict(request_data)
        
        # Check cache first
        progress_manager.update_progress(task_id, 5, 'cache_check', 'Checking cache')
        cached_result = result_cache.get_cached_result(request)
        if cached_result:
            progress_manager.update_progress(task_id, 100, 'completed', 'Retrieved from cache')
            return cached_result.to_dict()

        # Initialize validator
        progress_manager.update_progress(task_id, 10, 'initialization', 'Initializing validator')
        llm_service = LLMService()
        validator = MigrationValidator(llm_client=llm_service)

        # Execute validation with progress updates
        progress_manager.update_progress(task_id, 20, 'code_analysis', 'Analyzing source code')
        
        # Run validation (this will be broken down into sub-tasks)
        session = asyncio.run(validator.validate_migration(request))
        
        progress_manager.update_progress(task_id, 90, 'finalizing', 'Finalizing results')
        
        # Cache result
        result_cache.cache_result(request, session)
        
        progress_manager.update_progress(task_id, 100, 'completed', 'Validation completed')
        
        return session.to_dict()
        
    except Exception as exc:
        progress_manager.update_progress(
            task_id, 0, 'error', f'Validation failed: {str(exc)}'
        )
        raise


@celery_app.task(bind=True, name='analyze_code_async')
def analyze_code_async(self, files: List[Dict], technology: str, task_id: str = None) -> Dict[str, Any]:
    """Async code analysis sub-task."""
    parent_task_id = task_id or self.request.id
    
    try:
        from src.analyzers.code_analyzer import CodeAnalyzer
        
        progress_manager.update_progress(
            parent_task_id, 30, 'code_analysis', f'Analyzing {technology} code'
        )
        
        analyzer = CodeAnalyzer()
        results = {}
        
        for i, file_data in enumerate(files):
            file_progress = 30 + (30 * (i + 1) / len(files))  # 30-60%
            progress_manager.update_progress(
                parent_task_id, int(file_progress), 'code_analysis', 
                f'Analyzing {file_data.get("name", "file")}'
            )
            
            # Analyze individual file
            analysis = asyncio.run(analyzer.analyze(file_data['content'], technology))
            results[file_data['name']] = analysis
        
        return results
        
    except Exception as exc:
        progress_manager.update_progress(
            parent_task_id, 0, 'error', f'Code analysis failed: {str(exc)}'
        )
        raise


@celery_app.task(bind=True, name='compare_semantics_async')  
def compare_semantics_async(
    self, 
    source_analysis: Dict, 
    target_analysis: Dict, 
    task_id: str = None
) -> Dict[str, Any]:
    """Async semantic comparison sub-task."""
    parent_task_id = task_id or self.request.id
    
    try:
        from src.comparators.semantic_comparator import SemanticComparator
        
        progress_manager.update_progress(
            parent_task_id, 60, 'semantic_comparison', 'Comparing semantic structures'
        )
        
        comparator = SemanticComparator()
        
        # Perform semantic comparison
        comparison_result = asyncio.run(comparator.compare_representations(
            source_analysis, target_analysis
        ))
        
        progress_manager.update_progress(
            parent_task_id, 80, 'semantic_comparison', 'Semantic comparison completed'
        )
        
        return comparison_result
        
    except Exception as exc:
        progress_manager.update_progress(
            parent_task_id, 0, 'error', f'Semantic comparison failed: {str(exc)}'
        )
        raise


class AsyncValidationService:
    """High-level async validation service."""

    def __init__(self):
        self.progress_manager = progress_manager
        self.result_cache = result_cache

    def submit_validation_task(self, request: ValidationRequest) -> str:
        """Submit validation task to queue."""
        # Check cache first for immediate response
        cached_result = self.result_cache.get_cached_result(request)
        if cached_result:
            # Return special task ID for cached results
            cache_task_id = f"cached_{uuid4().hex[:8]}"
            self.progress_manager.update_progress(
                cache_task_id, 100, 'completed', 'Retrieved from cache',
                metadata={'cached': True, 'result': cached_result.to_dict()}
            )
            return cache_task_id

        # Submit to queue
        task = validate_migration_async.delay(request.dict())
        return task.id

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status and progress."""
        # Check if it's a cached result
        if task_id.startswith('cached_'):
            progress_data = self.progress_manager.get_progress(task_id)
            if progress_data:
                return {
                    'task_id': task_id,
                    'status': 'SUCCESS',
                    'progress': 100,
                    'stage': 'completed',
                    'message': 'Retrieved from cache',
                    'result': progress_data.get('metadata', {}).get('result'),
                    'cached': True
                }

        # Get Celery task result
        result = AsyncResult(task_id, app=celery_app)
        progress_data = self.progress_manager.get_progress(task_id)
        
        status_info = {
            'task_id': task_id,
            'status': result.state,
            'progress': 0,
            'stage': 'pending',
            'message': '',
            'cached': False
        }

        if progress_data:
            status_info.update({
                'progress': progress_data['progress'],
                'stage': progress_data['stage'],
                'message': progress_data['message'],
                'updated_at': progress_data['updated_at']
            })

        if result.ready():
            if result.successful():
                status_info['result'] = result.result
            else:
                status_info['error'] = str(result.info)

        return status_info

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        if task_id.startswith('cached_'):
            return True
            
        celery_app.control.revoke(task_id, terminate=True)
        self.progress_manager.clear_progress(task_id)
        return True

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        inspect = celery_app.control.inspect()
        
        stats = {
            'active_tasks': 0,
            'scheduled_tasks': 0,
            'reserved_tasks': 0,
            'workers': []
        }

        try:
            active = inspect.active()
            scheduled = inspect.scheduled() 
            reserved = inspect.reserved()
            
            if active:
                stats['active_tasks'] = sum(len(tasks) for tasks in active.values())
                
            if scheduled:
                stats['scheduled_tasks'] = sum(len(tasks) for tasks in scheduled.values())
                
            if reserved:
                stats['reserved_tasks'] = sum(len(tasks) for tasks in reserved.values())
                
            stats['workers'] = list(active.keys()) if active else []
            
        except Exception:
            pass  # Return default stats if inspection fails

        return stats


# Task signal handlers for monitoring
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task start."""
    progress_manager.update_progress(task_id, 0, 'started', f'Task {task.name} started')


@task_postrun.connect  
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handle task completion."""
    if state == 'SUCCESS':
        progress_manager.update_progress(task_id, 100, 'completed', f'Task {task.name} completed')


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, **kwds):
    """Handle task failure."""
    progress_manager.update_progress(
        task_id, 0, 'failed', f'Task failed: {str(exception)}'
    )


# Global service instance
async_validation_service = AsyncValidationService()