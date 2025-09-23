"""Comprehensive security audit logging system.

Provides detailed audit trails for all security-related events including
authentication, authorization, data access, and security violations.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from typing import Dict
from typing import Optional

from pydantic import BaseModel

from ..core.config import get_settings
from ..core.logging import logger
from ..database.service import get_database_service


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_EXPIRED = "token_expired"

    # API key events
    API_KEY_CREATED = "api_key_created"
    API_KEY_USED = "api_key_used"
    API_KEY_REVOKED = "api_key_revoked"
    API_KEY_INVALID = "api_key_invalid"
    API_KEY_RATE_LIMITED = "api_key_rate_limited"

    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_ESCALATION = "permission_escalation"
    SCOPE_VIOLATION = "scope_violation"

    # Data access events
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"

    # Security violations
    SECURITY_VIOLATION = "security_violation"
    INPUT_VALIDATION_FAILURE = "input_validation_failure"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ATTACK_ATTEMPT = "attack_attempt"

    # System events
    SYSTEM_ERROR = "system_error"
    CONFIGURATION_CHANGE = "configuration_change"
    BACKUP_CREATED = "backup_created"
    MAINTENANCE_MODE = "maintenance_mode"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    """Audit event model."""

    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    api_key_id: Optional[str]
    source_ip: Optional[str]
    user_agent: Optional[str]
    resource: Optional[str]
    action: str
    result: str  # success, failure, blocked, etc.
    details: Dict[str, Any]
    request_id: Optional[str]
    session_id: Optional[str]


class SecurityAuditLogger:
    """Comprehensive security audit logging system."""

    def __init__(self, session=None):
        self.settings = get_settings()
        self.db = get_database_service(session) if session else None
        self.logger = logger.bind(component="SecurityAudit")

    async def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        action: str,
        result: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """Log a security audit event."""
        import uuid

        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            api_key_id=api_key_id,
            source_ip=source_ip,
            user_agent=user_agent,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
            request_id=request_id,
            session_id=session_id,
        )

        try:
            # Store in database
            await self.db.store_audit_event(event.dict())

            # Log to application logger
            self.logger.info(
                f"Audit: {event_type.value}",
                event_id=event.event_id,
                severity=severity.value,
                user_id=user_id,
                api_key_id=api_key_id,
                action=action,
                result=result,
                resource=resource,
                source_ip=source_ip,
            )

            # Alert on critical events
            if severity == AuditSeverity.CRITICAL:
                await self._alert_critical_event(event)

        except Exception as e:
            self.logger.error("Failed to log audit event", error=str(e))

    async def _alert_critical_event(self, event: AuditEvent):
        """Alert on critical security events."""
        # In production, this would trigger alerts via email, Slack, etc.
        self.logger.critical(
            f"CRITICAL SECURITY EVENT: {event.event_type.value}",
            event_id=event.event_id,
            details=event.details,
        )

    # Authentication audit methods
    async def log_login_success(
        self,
        user_id: str,
        source_ip: str,
        user_agent: str,
        request_id: Optional[str] = None,
    ):
        """Log successful login."""
        await self.log_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            action="user_login",
            result="success",
            user_id=user_id,
            source_ip=source_ip,
            user_agent=user_agent,
            request_id=request_id,
        )

    async def log_login_failure(
        self,
        username: str,
        reason: str,
        source_ip: str,
        user_agent: str,
        request_id: Optional[str] = None,
    ):
        """Log failed login attempt."""
        await self.log_event(
            event_type=AuditEventType.LOGIN_FAILURE,
            severity=AuditSeverity.MEDIUM,
            action="user_login",
            result="failure",
            source_ip=source_ip,
            user_agent=user_agent,
            details={"username": username, "failure_reason": reason},
            request_id=request_id,
        )

    async def log_logout(
        self,
        user_id: str,
        source_ip: str,
        request_id: Optional[str] = None,
    ):
        """Log user logout."""
        await self.log_event(
            event_type=AuditEventType.LOGOUT,
            severity=AuditSeverity.LOW,
            action="user_logout",
            result="success",
            user_id=user_id,
            source_ip=source_ip,
            request_id=request_id,
        )

    # API key audit methods
    async def log_api_key_created(
        self,
        api_key_id: str,
        created_by: str,
        scopes: list,
        source_ip: str,
        request_id: Optional[str] = None,
    ):
        """Log API key creation."""
        await self.log_event(
            event_type=AuditEventType.API_KEY_CREATED,
            severity=AuditSeverity.MEDIUM,
            action="api_key_create",
            result="success",
            user_id=created_by,
            api_key_id=api_key_id,
            source_ip=source_ip,
            details={"scopes": scopes},
            request_id=request_id,
        )

    async def log_api_key_used(
        self,
        api_key_id: str,
        action: str,
        resource: str,
        source_ip: str,
        request_id: Optional[str] = None,
    ):
        """Log API key usage."""
        await self.log_event(
            event_type=AuditEventType.API_KEY_USED,
            severity=AuditSeverity.LOW,
            action=action,
            result="success",
            api_key_id=api_key_id,
            source_ip=source_ip,
            resource=resource,
            request_id=request_id,
        )

    async def log_api_key_invalid(
        self,
        provided_key: str,
        source_ip: str,
        user_agent: str,
        request_id: Optional[str] = None,
    ):
        """Log invalid API key usage."""
        await self.log_event(
            event_type=AuditEventType.API_KEY_INVALID,
            severity=AuditSeverity.HIGH,
            action="api_key_validate",
            result="failure",
            source_ip=source_ip,
            user_agent=user_agent,
            details={"provided_key_prefix": provided_key[:8] if provided_key else ""},
            request_id=request_id,
        )

    async def log_api_key_rate_limited(
        self,
        api_key_id: str,
        rate_limit: int,
        source_ip: str,
        request_id: Optional[str] = None,
    ):
        """Log API key rate limiting."""
        await self.log_event(
            event_type=AuditEventType.API_KEY_RATE_LIMITED,
            severity=AuditSeverity.MEDIUM,
            action="api_request",
            result="rate_limited",
            api_key_id=api_key_id,
            source_ip=source_ip,
            details={"rate_limit": rate_limit},
            request_id=request_id,
        )

    # Authorization audit methods
    async def log_access_denied(
        self,
        user_id: Optional[str],
        api_key_id: Optional[str],
        resource: str,
        required_permission: str,
        source_ip: str,
        request_id: Optional[str] = None,
    ):
        """Log access denied event."""
        await self.log_event(
            event_type=AuditEventType.ACCESS_DENIED,
            severity=AuditSeverity.MEDIUM,
            action="access_check",
            result="denied",
            user_id=user_id,
            api_key_id=api_key_id,
            source_ip=source_ip,
            resource=resource,
            details={"required_permission": required_permission},
            request_id=request_id,
        )

    async def log_scope_violation(
        self,
        api_key_id: str,
        required_scope: str,
        available_scopes: list,
        resource: str,
        source_ip: str,
        request_id: Optional[str] = None,
    ):
        """Log scope violation."""
        await self.log_event(
            event_type=AuditEventType.SCOPE_VIOLATION,
            severity=AuditSeverity.HIGH,
            action="scope_check",
            result="violation",
            api_key_id=api_key_id,
            source_ip=source_ip,
            resource=resource,
            details={
                "required_scope": required_scope,
                "available_scopes": available_scopes,
            },
            request_id=request_id,
        )

    # Data access audit methods
    async def log_file_upload(
        self,
        user_id: Optional[str],
        api_key_id: Optional[str],
        filename: str,
        file_size: int,
        content_type: str,
        validation_result: dict,
        source_ip: str,
        request_id: Optional[str] = None,
    ):
        """Log file upload event."""
        severity = (
            AuditSeverity.HIGH
            if not validation_result.get("is_valid")
            else AuditSeverity.LOW
        )

        await self.log_event(
            event_type=AuditEventType.FILE_UPLOAD,
            severity=severity,
            action="file_upload",
            result="success"
            if validation_result.get("is_valid")
            else "validation_failed",
            user_id=user_id,
            api_key_id=api_key_id,
            source_ip=source_ip,
            resource=filename,
            details={
                "file_size": file_size,
                "content_type": content_type,
                "validation_result": validation_result,
            },
            request_id=request_id,
        )

    async def log_data_access(
        self,
        user_id: Optional[str],
        api_key_id: Optional[str],
        resource: str,
        action: str,
        source_ip: str,
        request_id: Optional[str] = None,
    ):
        """Log data access event."""
        await self.log_event(
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.LOW,
            action=action,
            result="success",
            user_id=user_id,
            api_key_id=api_key_id,
            source_ip=source_ip,
            resource=resource,
            request_id=request_id,
        )

    # Security violation audit methods
    async def log_input_validation_failure(
        self,
        user_id: Optional[str],
        api_key_id: Optional[str],
        field_name: str,
        violation_type: str,
        value_sample: str,
        source_ip: str,
        request_id: Optional[str] = None,
    ):
        """Log input validation failure."""
        await self.log_event(
            event_type=AuditEventType.INPUT_VALIDATION_FAILURE,
            severity=AuditSeverity.HIGH,
            action="input_validation",
            result="failure",
            user_id=user_id,
            api_key_id=api_key_id,
            source_ip=source_ip,
            details={
                "field_name": field_name,
                "violation_type": violation_type,
                "value_sample": value_sample[:100],  # Limit sample size
            },
            request_id=request_id,
        )

    async def log_attack_attempt(
        self,
        attack_type: str,
        source_ip: str,
        user_agent: str,
        details: dict,
        request_id: Optional[str] = None,
    ):
        """Log potential attack attempt."""
        await self.log_event(
            event_type=AuditEventType.ATTACK_ATTEMPT,
            severity=AuditSeverity.CRITICAL,
            action="attack_detection",
            result="blocked",
            source_ip=source_ip,
            user_agent=user_agent,
            details={
                "attack_type": attack_type,
                **details,
            },
            request_id=request_id,
        )

    async def log_suspicious_activity(
        self,
        user_id: Optional[str],
        api_key_id: Optional[str],
        activity_type: str,
        source_ip: str,
        details: dict,
        request_id: Optional[str] = None,
    ):
        """Log suspicious activity."""
        await self.log_event(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            severity=AuditSeverity.HIGH,
            action="activity_monitoring",
            result="detected",
            user_id=user_id,
            api_key_id=api_key_id,
            source_ip=source_ip,
            details={
                "activity_type": activity_type,
                **details,
            },
            request_id=request_id,
        )

    # Query methods
    async def get_audit_events(
        self,
        start_date: datetime,
        end_date: datetime,
        event_types: Optional[list] = None,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100,
    ) -> list:
        """Query audit events with filters."""
        try:
            return await self.db.query_audit_events(
                start_date=start_date,
                end_date=end_date,
                event_types=event_types,
                user_id=user_id,
                api_key_id=api_key_id,
                severity=severity,
                limit=limit,
            )
        except Exception as e:
            self.logger.error("Failed to query audit events", error=str(e))
            return []

    async def get_security_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """Get security metrics for a date range."""
        try:
            events = await self.get_audit_events(start_date, end_date, limit=10000)

            metrics = {
                "total_events": len(events),
                "events_by_type": {},
                "events_by_severity": {},
                "failed_logins": 0,
                "api_key_violations": 0,
                "input_validation_failures": 0,
                "attack_attempts": 0,
            }

            for event in events:
                event_type = event.get("event_type")
                severity = event.get("severity")

                # Count by type
                metrics["events_by_type"][event_type] = (
                    metrics["events_by_type"].get(event_type, 0) + 1
                )

                # Count by severity
                metrics["events_by_severity"][severity] = (
                    metrics["events_by_severity"].get(severity, 0) + 1
                )

                # Specific metrics
                if event_type == AuditEventType.LOGIN_FAILURE:
                    metrics["failed_logins"] += 1
                elif event_type in [
                    AuditEventType.API_KEY_INVALID,
                    AuditEventType.SCOPE_VIOLATION,
                ]:
                    metrics["api_key_violations"] += 1
                elif event_type == AuditEventType.INPUT_VALIDATION_FAILURE:
                    metrics["input_validation_failures"] += 1
                elif event_type == AuditEventType.ATTACK_ATTEMPT:
                    metrics["attack_attempts"] += 1

            return metrics

        except Exception as e:
            self.logger.error("Failed to get security metrics", error=str(e))
            return {}


# Global audit logger instance
# Global instance - will be initialized when needed
security_audit = None


def get_security_audit(session=None):
    """Get security audit logger instance with optional session."""
    global security_audit
    if security_audit is None or session:
        security_audit = SecurityAuditLogger(session)
    return security_audit


# For backward compatibility
security_audit = get_security_audit()
