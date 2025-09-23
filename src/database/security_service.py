"""
Security database service for managing security-related data operations.

Provides high-level methods for API keys, audit logs, and security configurations.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .security_models import (
    APIKeyModel,
    AuditLogModel,
    ComplianceLogModel,
    FileUploadModel,
    RateLimitModel,
    SecurityConfigModel,
    SecurityIncidentModel,
    SecurityMetricsModel,
)

logger = logging.getLogger(__name__)


class SecurityDatabaseService:
    """Database service for security operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize security database service.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    # API Key Management
    async def store_api_key(
        self,
        api_key_id: str,
        hashed_key: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Store API key with metadata."""
        try:
            api_key = APIKeyModel(
                id=api_key_id,
                hashed_key=hashed_key,
                name=metadata['name'],
                description=metadata.get('description'),
                scopes=metadata['scopes'],
                expires_at=metadata.get('expires_at'),
                rate_limit_per_minute=metadata['rate_limit_per_minute'],
                is_active=metadata['is_active'],
                created_by=metadata['created_by']
            )

            self.session.add(api_key)
            await self.session.commit()
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to store API key: {e}")
            return False

    async def get_api_key_by_hash(self, hashed_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve API key by hash."""
        try:
            result = await self.session.execute(
                select(APIKeyModel).where(APIKeyModel.hashed_key == hashed_key)
            )
            api_key = result.scalar_one_or_none()

            if api_key:
                return {
                    'metadata': {
                        'id': api_key.id,
                        'name': api_key.name,
                        'description': api_key.description,
                        'scopes': api_key.scopes,
                        'created_at': api_key.created_at,
                        'expires_at': api_key.expires_at,
                        'last_used_at': api_key.last_used_at,
                        'rate_limit_per_minute': api_key.rate_limit_per_minute,
                        'is_active': api_key.is_active,
                        'created_by': api_key.created_by,
                        'usage_count': api_key.usage_count
                    }
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get API key by hash: {e}")
            return None

    async def update_api_key_last_used(self, api_key_id: str, timestamp: datetime) -> bool:
        """Update API key last used timestamp."""
        try:
            result = await self.session.execute(
                select(APIKeyModel).where(APIKeyModel.id == api_key_id)
            )
            api_key = result.scalar_one_or_none()

            if api_key:
                api_key.last_used_at = timestamp
                api_key.usage_count += 1
                await self.session.commit()
                return True

            return False

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update API key last used: {e}")
            return False

    async def deactivate_api_key(self, api_key_id: str) -> bool:
        """Deactivate API key."""
        try:
            result = await self.session.execute(
                select(APIKeyModel).where(APIKeyModel.id == api_key_id)
            )
            api_key = result.scalar_one_or_none()

            if api_key:
                api_key.is_active = False
                await self.session.commit()
                return True

            return False

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to deactivate API key: {e}")
            return False

    async def list_api_keys(self, created_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """List API keys with optional filtering."""
        try:
            query = select(APIKeyModel).order_by(desc(APIKeyModel.created_at))

            if created_by:
                query = query.where(APIKeyModel.created_by == created_by)

            result = await self.session.execute(query)
            api_keys = result.scalars().all()

            return [
                {
                    'metadata': {
                        'id': api_key.id,
                        'name': api_key.name,
                        'description': api_key.description,
                        'scopes': api_key.scopes,
                        'created_at': api_key.created_at,
                        'expires_at': api_key.expires_at,
                        'last_used_at': api_key.last_used_at,
                        'rate_limit_per_minute': api_key.rate_limit_per_minute,
                        'is_active': api_key.is_active,
                        'created_by': api_key.created_by,
                        'usage_count': api_key.usage_count
                    }
                }
                for api_key in api_keys
            ]

        except Exception as e:
            logger.error(f"Failed to list API keys: {e}")
            return []

    # Audit Logging
    async def store_audit_event(self, event_data: Dict[str, Any]) -> bool:
        """Store audit event."""
        try:
            audit_log = AuditLogModel(
                id=event_data['event_id'],
                event_type=event_data['event_type'],
                severity=event_data['severity'],
                user_id=event_data.get('user_id'),
                api_key_id=event_data.get('api_key_id'),
                source_ip=event_data.get('source_ip'),
                user_agent=event_data.get('user_agent'),
                resource=event_data.get('resource'),
                action=event_data['action'],
                result=event_data['result'],
                details=event_data.get('details'),
                request_id=event_data.get('request_id'),
                session_id=event_data.get('session_id')
            )

            self.session.add(audit_log)
            await self.session.commit()
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to store audit event: {e}")
            return False

    async def query_audit_events(
        self,
        start_date: datetime,
        end_date: datetime,
        event_types: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query audit events with filters."""
        try:
            query = select(AuditLogModel).where(
                and_(
                    AuditLogModel.created_at >= start_date,
                    AuditLogModel.created_at <= end_date
                )
            ).order_by(desc(AuditLogModel.created_at))

            if event_types:
                query = query.where(AuditLogModel.event_type.in_(event_types))

            if user_id:
                query = query.where(AuditLogModel.user_id == user_id)

            if api_key_id:
                query = query.where(AuditLogModel.api_key_id == api_key_id)

            if severity:
                query = query.where(AuditLogModel.severity == severity)

            query = query.limit(limit)

            result = await self.session.execute(query)
            events = result.scalars().all()

            return [
                {
                    'event_id': event.id,
                    'event_type': event.event_type,
                    'severity': event.severity,
                    'timestamp': event.created_at,
                    'user_id': event.user_id,
                    'api_key_id': event.api_key_id,
                    'source_ip': event.source_ip,
                    'user_agent': event.user_agent,
                    'resource': event.resource,
                    'action': event.action,
                    'result': event.result,
                    'details': event.details,
                    'request_id': event.request_id,
                    'session_id': event.session_id
                }
                for event in events
            ]

        except Exception as e:
            logger.error(f"Failed to query audit events: {e}")
            return []

    # File Upload Tracking
    async def store_file_upload(
        self,
        file_id: str,
        filename: str,
        original_filename: str,
        file_size: int,
        content_type: str,
        file_hash: str,
        upload_type: str,
        uploaded_by_user: Optional[str],
        uploaded_by_api_key: Optional[str],
        source_ip: Optional[str],
        validation_result: Dict[str, Any],
        storage_path: Optional[str] = None
    ) -> bool:
        """Store file upload record."""
        try:
            file_upload = FileUploadModel(
                id=file_id,
                filename=filename,
                original_filename=original_filename,
                file_size=file_size,
                content_type=content_type,
                file_hash=file_hash,
                upload_type=upload_type,
                uploaded_by_user=uploaded_by_user,
                uploaded_by_api_key=uploaded_by_api_key,
                source_ip=source_ip,
                validation_result=validation_result,
                storage_path=storage_path
            )

            self.session.add(file_upload)
            await self.session.commit()
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to store file upload: {e}")
            return False

    async def quarantine_file(self, file_id: str, reason: str) -> bool:
        """Quarantine a file upload."""
        try:
            result = await self.session.execute(
                select(FileUploadModel).where(FileUploadModel.id == file_id)
            )
            file_upload = result.scalar_one_or_none()

            if file_upload:
                file_upload.is_quarantined = True
                file_upload.quarantine_reason = reason
                await self.session.commit()
                return True

            return False

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to quarantine file: {e}")
            return False

    # Security Incidents
    async def create_security_incident(
        self,
        incident_id: str,
        incident_type: str,
        severity: str,
        title: str,
        description: str,
        source_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        attack_vectors: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create security incident record."""
        try:
            incident = SecurityIncidentModel(
                id=incident_id,
                incident_type=incident_type,
                severity=severity,
                title=title,
                description=description,
                source_ip=source_ip,
                user_id=user_id,
                api_key_id=api_key_id,
                attack_vectors=attack_vectors
            )

            self.session.add(incident)
            await self.session.commit()
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create security incident: {e}")
            return False

    async def update_incident_status(
        self,
        incident_id: str,
        status: str,
        assigned_to: Optional[str] = None,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """Update security incident status."""
        try:
            result = await self.session.execute(
                select(SecurityIncidentModel).where(SecurityIncidentModel.id == incident_id)
            )
            incident = result.scalar_one_or_none()

            if incident:
                incident.status = status
                if assigned_to:
                    incident.assigned_to = assigned_to
                if resolution_notes:
                    incident.resolution_notes = resolution_notes
                if status == "resolved":
                    incident.resolved_at = datetime.utcnow()

                await self.session.commit()
                return True

            return False

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update incident status: {e}")
            return False

    # Rate Limiting
    async def track_rate_limit(
        self,
        identifier: str,
        identifier_type: str,
        endpoint: Optional[str] = None,
        window_minutes: int = 1
    ) -> Dict[str, Any]:
        """Track rate limiting for identifier."""
        try:
            current_time = datetime.utcnow()
            window_start = current_time.replace(second=0, microsecond=0)
            window_end = window_start + timedelta(minutes=window_minutes)

            # Check existing rate limit record
            result = await self.session.execute(
                select(RateLimitModel).where(
                    and_(
                        RateLimitModel.identifier == identifier,
                        RateLimitModel.identifier_type == identifier_type,
                        RateLimitModel.endpoint == endpoint,
                        RateLimitModel.window_start == window_start
                    )
                )
            )
            rate_limit = result.scalar_one_or_none()

            if rate_limit:
                rate_limit.request_count += 1
            else:
                rate_limit = RateLimitModel(
                    identifier=identifier,
                    identifier_type=identifier_type,
                    endpoint=endpoint,
                    request_count=1,
                    window_start=window_start,
                    window_end=window_end
                )
                self.session.add(rate_limit)

            await self.session.commit()

            return {
                'request_count': rate_limit.request_count,
                'window_start': rate_limit.window_start,
                'window_end': rate_limit.window_end,
                'limit_exceeded': rate_limit.limit_exceeded
            }

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to track rate limit: {e}")
            return {'request_count': 0, 'error': str(e)}

    # Security Metrics
    async def store_security_metrics(
        self,
        metric_date: datetime,
        metric_type: str,
        metric_value: Dict[str, Any],
        aggregation_period: str = "day"
    ) -> bool:
        """Store security metrics."""
        try:
            metrics = SecurityMetricsModel(
                metric_date=metric_date,
                metric_type=metric_type,
                metric_value=metric_value,
                aggregation_period=aggregation_period
            )

            self.session.add(metrics)
            await self.session.commit()
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to store security metrics: {e}")
            return False

    async def get_security_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        metric_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get security metrics for date range."""
        try:
            query = select(SecurityMetricsModel).where(
                and_(
                    SecurityMetricsModel.metric_date >= start_date,
                    SecurityMetricsModel.metric_date <= end_date
                )
            ).order_by(SecurityMetricsModel.metric_date)

            if metric_type:
                query = query.where(SecurityMetricsModel.metric_type == metric_type)

            result = await self.session.execute(query)
            metrics = result.scalars().all()

            return [
                {
                    'metric_date': metric.metric_date,
                    'metric_type': metric.metric_type,
                    'metric_value': metric.metric_value,
                    'aggregation_period': metric.aggregation_period
                }
                for metric in metrics
            ]

        except Exception as e:
            logger.error(f"Failed to get security metrics: {e}")
            return []

    # Compliance Logging
    async def log_compliance_event(
        self,
        event_id: str,
        compliance_framework: str,
        event_type: str,
        user_id: Optional[str] = None,
        data_subject_id: Optional[str] = None,
        data_categories: Optional[List[str]] = None,
        processing_purpose: Optional[str] = None,
        legal_basis: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log compliance event."""
        try:
            compliance_log = ComplianceLogModel(
                id=event_id,
                compliance_framework=compliance_framework,
                event_type=event_type,
                user_id=user_id,
                data_subject_id=data_subject_id,
                data_categories=data_categories,
                processing_purpose=processing_purpose,
                legal_basis=legal_basis,
                additional_metadata=additional_metadata
            )

            self.session.add(compliance_log)
            await self.session.commit()
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to log compliance event: {e}")
            return False

    # Cleanup operations
    async def cleanup_old_audit_logs(self, days_old: int = 90) -> int:
        """Clean up old audit logs."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            result = await self.session.execute(
                select(func.count(AuditLogModel.id)).where(
                    AuditLogModel.created_at < cutoff_date
                )
            )
            count_before = result.scalar()

            await self.session.execute(
                AuditLogModel.__table__.delete().where(
                    AuditLogModel.created_at < cutoff_date
                )
            )

            await self.session.commit()
            return count_before

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to cleanup old audit logs: {e}")
            return 0

    async def cleanup_expired_api_keys(self) -> int:
        """Clean up expired API keys."""
        try:
            current_time = datetime.utcnow()

            result = await self.session.execute(
                select(func.count(APIKeyModel.id)).where(
                    and_(
                        APIKeyModel.expires_at.is_not(None),
                        APIKeyModel.expires_at < current_time,
                        APIKeyModel.is_active == True
                    )
                )
            )
            count_before = result.scalar()

            # Deactivate expired keys instead of deleting them
            result = await self.session.execute(
                select(APIKeyModel).where(
                    and_(
                        APIKeyModel.expires_at.is_not(None),
                        APIKeyModel.expires_at < current_time,
                        APIKeyModel.is_active == True
                    )
                )
            )
            expired_keys = result.scalars().all()

            for key in expired_keys:
                key.is_active = False

            await self.session.commit()
            return len(expired_keys)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to cleanup expired API keys: {e}")
            return 0


# Global instance helper
_security_service: Optional[SecurityDatabaseService] = None


def get_database_service() -> SecurityDatabaseService:
    """Get global security database service instance."""
    global _security_service
    if _security_service is None:
        # This will be properly initialized when the database session is available
        _security_service = SecurityDatabaseService(session=None)
    return _security_service


async def initialize_security_service(session: AsyncSession):
    """Initialize security service with database session."""
    global _security_service
    _security_service = SecurityDatabaseService(session)