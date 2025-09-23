"""
Database models for security-related entities.

Defines SQLAlchemy models for API keys, audit logs, and security configurations.
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import (JSON, Boolean, Column, DateTime, Index, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.sql import func

from .config import metadata
from .models import Base, TimestampMixin


class APIKeyModel(Base, TimestampMixin):
    """API key storage model."""

    __tablename__ = "api_keys"

    id = Column(String(32), primary_key=True)
    hashed_key = Column(String(256), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    scopes = Column(JSON, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    rate_limit_per_minute = Column(Integer, nullable=False, default=60)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(32), nullable=False)
    usage_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_api_keys_active", "is_active"),
        Index("idx_api_keys_created_by", "created_by"),
        Index("idx_api_keys_expires_at", "expires_at"),
    )


class AuditLogModel(Base, TimestampMixin):
    """Audit log model for security events."""

    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)  # UUID
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    user_id = Column(String(32), nullable=True, index=True)
    api_key_id = Column(String(32), nullable=True, index=True)
    source_ip = Column(String(45), nullable=True, index=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    resource = Column(String(255), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    result = Column(String(50), nullable=False)
    details = Column(JSON, nullable=True)
    request_id = Column(String(36), nullable=True, index=True)
    session_id = Column(String(36), nullable=True, index=True)

    __table_args__ = (
        Index("idx_audit_logs_timestamp", "created_at"),
        Index("idx_audit_logs_event_severity", "event_type", "severity"),
        Index("idx_audit_logs_user_action", "user_id", "action"),
        Index("idx_audit_logs_api_key_action", "api_key_id", "action"),
    )


class SecurityConfigModel(Base, TimestampMixin):
    """Security configuration model."""

    __tablename__ = "security_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_name = Column(String(100), nullable=False, unique=True)
    config_value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    updated_by = Column(String(32), nullable=False)

    __table_args__ = (
        Index("idx_security_configs_active", "is_active"),
        Index("idx_security_configs_name", "config_name"),
    )


class RateLimitModel(Base, TimestampMixin):
    """Rate limiting tracking model."""

    __tablename__ = "rate_limits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), nullable=False, index=True)  # API key ID or IP
    identifier_type = Column(String(20), nullable=False)  # 'api_key', 'ip', 'user'
    endpoint = Column(String(255), nullable=True)
    request_count = Column(Integer, nullable=False, default=0)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    limit_exceeded = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_rate_limits_identifier", "identifier", "identifier_type"),
        Index("idx_rate_limits_window", "window_start", "window_end"),
        UniqueConstraint("identifier", "identifier_type", "endpoint", "window_start"),
    )


class SecurityMetricsModel(Base, TimestampMixin):
    """Security metrics aggregation model."""

    __tablename__ = "security_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_date = Column(DateTime(timezone=True), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False, index=True)
    metric_value = Column(JSON, nullable=False)
    aggregation_period = Column(String(20), nullable=False)  # 'hour', 'day', 'week'

    __table_args__ = (
        Index("idx_security_metrics_date_type", "metric_date", "metric_type"),
        UniqueConstraint("metric_date", "metric_type", "aggregation_period"),
    )


class FileUploadModel(Base, TimestampMixin):
    """File upload tracking model."""

    __tablename__ = "file_uploads"

    id = Column(String(36), primary_key=True)  # UUID
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    upload_type = Column(String(50), nullable=False)
    uploaded_by_user = Column(String(32), nullable=True)
    uploaded_by_api_key = Column(String(32), nullable=True)
    source_ip = Column(String(45), nullable=True)
    validation_result = Column(JSON, nullable=False)
    storage_path = Column(String(500), nullable=True)
    is_quarantined = Column(Boolean, nullable=False, default=False)
    quarantine_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_file_uploads_hash", "file_hash"),
        Index("idx_file_uploads_user", "uploaded_by_user"),
        Index("idx_file_uploads_api_key", "uploaded_by_api_key"),
        Index("idx_file_uploads_quarantined", "is_quarantined"),
    )


class SecurityIncidentModel(Base, TimestampMixin):
    """Security incident tracking model."""

    __tablename__ = "security_incidents"

    id = Column(String(36), primary_key=True)  # UUID
    incident_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    source_ip = Column(String(45), nullable=True, index=True)
    user_id = Column(String(32), nullable=True, index=True)
    api_key_id = Column(String(32), nullable=True, index=True)
    attack_vectors = Column(JSON, nullable=True)
    mitigation_actions = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="open")  # open, investigating, resolved
    assigned_to = Column(String(32), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_security_incidents_type_severity", "incident_type", "severity"),
        Index("idx_security_incidents_status", "status"),
        Index("idx_security_incidents_assigned", "assigned_to"),
    )


class ComplianceLogModel(Base, TimestampMixin):
    """Compliance and regulatory logging model."""

    __tablename__ = "compliance_logs"

    id = Column(String(36), primary_key=True)  # UUID
    compliance_framework = Column(String(50), nullable=False, index=True)  # GDPR, SOX, HIPAA, etc.
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(String(32), nullable=True, index=True)
    data_subject_id = Column(String(32), nullable=True, index=True)
    data_categories = Column(JSON, nullable=True)
    processing_purpose = Column(String(255), nullable=True)
    legal_basis = Column(String(100), nullable=True)
    retention_period = Column(Integer, nullable=True)  # Days
    consent_status = Column(String(20), nullable=True)
    cross_border_transfer = Column(Boolean, nullable=False, default=False)
    encryption_status = Column(String(20), nullable=True)
    additional_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_compliance_logs_framework", "compliance_framework"),
        Index("idx_compliance_logs_event_type", "event_type"),
        Index("idx_compliance_logs_data_subject", "data_subject_id"),
    )