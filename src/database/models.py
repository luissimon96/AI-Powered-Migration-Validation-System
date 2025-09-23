"""SQLAlchemy database models for AI-Powered Migration Validation System.

Maps the existing Pydantic models to persistent database tables
with proper relationships, constraints, and indexes.
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.models import InputType, SeverityLevel, TechnologyType, ValidationScope
from .config import metadata

# Base class for all models
Base = declarative_base(metadata=metadata)


class TimestampMixin:
    """Mixin for timestamp fields."""

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality with audit trail."""

    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    deleted_by = Column(String(255), nullable=True)
    deletion_reason = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    def soft_delete(self, deleted_by: str = "system", reason: str = None):
        """Mark record as deleted without removing from database."""
        self.is_deleted = True
        self.deleted_at = func.now()
        self.deleted_by = deleted_by
        self.deletion_reason = reason

    def restore(self):
        """Restore soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.deletion_reason = None


class ValidationSessionModel(Base, TimestampMixin, SoftDeleteMixin):
    """Validation session database model.

    Represents a complete validation session including request details,
    processing status, and relationships to results and discrepancies.
    """

    __tablename__ = "validation_sessions"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Unique request identifier
    request_id = Column(String(255), unique=True, nullable=False, index=True)

    # Session status
    status = Column(
        String(50), nullable=False, default="pending", index=True,
    )  # pending, processing, completed, error

    # Technology contexts
    source_technology = Column(Enum(TechnologyType), nullable=False)
    source_technology_version = Column(String(100))
    source_framework_details = Column(JSON)

    target_technology = Column(Enum(TechnologyType), nullable=False)
    target_technology_version = Column(String(100))
    target_framework_details = Column(JSON)

    # Validation configuration
    validation_scope = Column(Enum(ValidationScope), nullable=False)

    # Input data
    source_input_type = Column(Enum(InputType), nullable=False)
    source_files = Column(JSON)  # List of file paths
    source_screenshots = Column(JSON)  # List of screenshot paths
    source_urls = Column(JSON)  # List of URLs for behavioral validation
    source_metadata = Column(JSON)

    target_input_type = Column(Enum(InputType), nullable=False)
    target_files = Column(JSON)  # List of file paths
    target_screenshots = Column(JSON)  # List of screenshot paths
    target_urls = Column(JSON)  # List of URLs for behavioral validation
    target_metadata = Column(JSON)

    # Behavioral validation specific
    validation_scenarios = Column(JSON)  # List of test scenarios
    behavioral_timeout = Column(Integer, default=300)

    # Processing details
    processing_log = Column(JSON, default=list)  # List of log entries
    execution_time = Column(Float)  # Total execution time in seconds

    # Session metadata
    session_metadata = Column(JSON)

    # Relationships
    results = relationship(
        "ValidationResultModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ValidationResultModel.created_at.desc()",
    )

    discrepancies = relationship(
        "DiscrepancyModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="DiscrepancyModel.severity.desc(), DiscrepancyModel.created_at.desc()",
    )

    # Indexes for performance
    __table_args__ = (
        Index("ix_validation_sessions_status_created", "status", "created_at"),
        Index("ix_validation_sessions_technologies", "source_technology", "target_technology"),
        Index("ix_validation_sessions_scope", "validation_scope"),
    )

    def add_log_entry(self, message: str) -> None:
        """Add a timestamped log entry."""
        if self.processing_log is None:
            self.processing_log = []

        timestamp = datetime.now().isoformat()
        self.processing_log.append(f"[{timestamp}] {message}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "request_id": self.request_id,
            "status": self.status,
            "source_technology": self.source_technology.value if self.source_technology else None,
            "target_technology": self.target_technology.value if self.target_technology else None,
            "validation_scope": self.validation_scope.value if self.validation_scope else None,
            "execution_time": self.execution_time,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ValidationResultModel(Base, TimestampMixin, SoftDeleteMixin):
    """Validation result database model.

    Stores the overall validation results including fidelity scores,
    status, and summary information.
    """

    __tablename__ = "validation_results"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to validation session
    session_id = Column(
        Integer,
        ForeignKey("validation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Result details
    overall_status = Column(
        String(50), nullable=False, index=True,
    )  # approved, approved_with_warnings, rejected, error
    fidelity_score = Column(Float, nullable=False, index=True)  # 0.0 to 1.0
    summary = Column(Text, nullable=False)

    # Analysis results
    source_representation = Column(JSON)  # Serialized AbstractRepresentation
    target_representation = Column(JSON)  # Serialized AbstractRepresentation

    # Execution metadata
    execution_time = Column(Float)  # Execution time for this specific result
    result_metadata = Column(JSON)

    # Result type (static, behavioral, hybrid)
    result_type = Column(String(50), default="static", index=True)

    # Relationships
    session = relationship("ValidationSessionModel", back_populates="results")

    # Indexes for performance
    __table_args__ = (
        Index("ix_validation_results_status_score", "overall_status", "fidelity_score"),
        Index("ix_validation_results_type_created", "result_type", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "overall_status": self.overall_status,
            "fidelity_score": self.fidelity_score,
            "summary": self.summary,
            "result_type": self.result_type,
            "execution_time": self.execution_time,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DiscrepancyModel(Base, TimestampMixin, SoftDeleteMixin):
    """Validation discrepancy database model.

    Stores individual discrepancies found during validation with
    detailed information for analysis and reporting.
    """

    __tablename__ = "validation_discrepancies"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to validation session
    session_id = Column(
        Integer,
        ForeignKey("validation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional foreign key to specific result
    result_id = Column(
        Integer,
        ForeignKey("validation_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Discrepancy details
    discrepancy_type = Column(
        String(100), nullable=False, index=True,
    )  # missing_field, type_mismatch, etc.
    severity = Column(Enum(SeverityLevel), nullable=False, index=True)
    description = Column(Text, nullable=False)

    # Element references
    source_element = Column(String(500))  # Element identifier in source
    target_element = Column(String(500))  # Element identifier in target

    # Resolution information
    recommendation = Column(Text)
    confidence = Column(Float, default=1.0, index=True)  # 0.0 to 1.0

    # Context information
    component_type = Column(String(50), index=True)  # ui, backend, data, api, behavioral
    validation_context = Column(JSON)  # Additional context data

    # Resolution tracking
    is_resolved = Column(Boolean, default=False, index=True)
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(String(255))

    # Relationships
    session = relationship("ValidationSessionModel", back_populates="discrepancies")
    result = relationship("ValidationResultModel")

    # Indexes for performance
    __table_args__ = (
        Index("ix_discrepancies_severity_type", "severity", "discrepancy_type"),
        Index("ix_discrepancies_component_resolved", "component_type", "is_resolved"),
        Index("ix_discrepancies_confidence", "confidence"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "result_id": self.result_id,
            "discrepancy_type": self.discrepancy_type,
            "severity": self.severity.value if self.severity else None,
            "description": self.description,
            "source_element": self.source_element,
            "target_element": self.target_element,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "component_type": self.component_type,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ValidationMetricsModel(Base, TimestampMixin):
    """Aggregated validation metrics for reporting and analytics.

    Stores computed metrics and statistics for dashboard views
    and performance monitoring.
    """

    __tablename__ = "validation_metrics"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Time period
    metric_date = Column(DateTime(timezone=True), nullable=False, index=True)
    metric_period = Column(String(20), nullable=False, index=True)  # daily, weekly, monthly

    # Session counts
    total_sessions = Column(Integer, default=0)
    completed_sessions = Column(Integer, default=0)
    failed_sessions = Column(Integer, default=0)

    # Validation results
    approved_count = Column(Integer, default=0)
    approved_with_warnings_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)

    # Performance metrics
    avg_execution_time = Column(Float)
    max_execution_time = Column(Float)
    min_execution_time = Column(Float)

    # Fidelity metrics
    avg_fidelity_score = Column(Float)
    max_fidelity_score = Column(Float)
    min_fidelity_score = Column(Float)

    # Technology breakdown
    technology_breakdown = Column(JSON)  # Technology pair usage statistics
    scope_breakdown = Column(JSON)  # Validation scope usage statistics

    # Discrepancy metrics
    total_discrepancies = Column(Integer, default=0)
    critical_discrepancies = Column(Integer, default=0)
    warning_discrepancies = Column(Integer, default=0)
    info_discrepancies = Column(Integer, default=0)

    # Additional metrics
    additional_metrics = Column(JSON)

    # Indexes for performance
    __table_args__ = (
        Index("ix_metrics_date_period", "metric_date", "metric_period"),
        UniqueConstraint("metric_date", "metric_period", name="uq_metrics_date_period"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "metric_date": self.metric_date.isoformat() if self.metric_date else None,
            "metric_period": self.metric_period,
            "total_sessions": self.total_sessions,
            "completed_sessions": self.completed_sessions,
            "avg_fidelity_score": self.avg_fidelity_score,
            "total_discrepancies": self.total_discrepancies,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BehavioralTestResultModel(Base, TimestampMixin):
    """Behavioral test result storage for detailed behavioral validation tracking.

    Stores individual test scenario results, screenshots, and interaction logs
    for behavioral validation sessions.
    """

    __tablename__ = "behavioral_test_results"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to validation session
    session_id = Column(
        Integer,
        ForeignKey("validation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Test scenario details
    scenario_name = Column(String(255), nullable=False, index=True)
    scenario_description = Column(Text)

    # Execution details
    source_url = Column(String(1000), nullable=False)
    target_url = Column(String(1000), nullable=False)
    execution_status = Column(String(50), nullable=False, index=True)  # passed, failed, error

    # Results
    source_result = Column(JSON)  # Source system interaction result
    target_result = Column(JSON)  # Target system interaction result
    comparison_result = Column(JSON)  # Comparison analysis

    # Evidence
    source_screenshots = Column(JSON)  # List of screenshot paths
    target_screenshots = Column(JSON)  # List of screenshot paths
    interaction_log = Column(JSON)  # Detailed interaction steps

    # Performance data
    source_load_time = Column(Float)
    target_load_time = Column(Float)
    execution_duration = Column(Float)

    # Error handling
    error_message = Column(Text)
    error_stack_trace = Column(Text)

    # Relationships
    session = relationship("ValidationSessionModel")

    # Indexes for performance
    __table_args__ = (
        Index("ix_behavioral_tests_status_scenario", "execution_status", "scenario_name"),
        Index("ix_behavioral_tests_session_created", "session_id", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "scenario_name": self.scenario_name,
            "execution_status": self.execution_status,
            "source_url": self.source_url,
            "target_url": self.target_url,
            "execution_duration": self.execution_duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
