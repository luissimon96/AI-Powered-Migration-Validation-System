"""Repository pattern implementation for database operations.

Provides high-level data access methods with business logic
encapsulation, query optimization, and transaction management.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.models import (SeverityLevel, TechnologyType,
                           ValidationDiscrepancy, ValidationScope)
from .models import (BehavioralTestResultModel, DiscrepancyModel,
                     ValidationMetricsModel, ValidationResultModel,
                     ValidationSessionModel)


class BaseRepository:
    """Base repository with common database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations

        """
        self.session = session

    async def commit(self) -> None:
        """Commit current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback current transaction."""
        await self.session.rollback()

    async def refresh(self, instance) -> None:
        """Refresh instance from database."""
        await self.session.refresh(instance)


class ValidationSessionRepository(BaseRepository):
    """Repository for validation session operations."""

    async def create_session(
        self,
        request_id: str,
        source_technology: TechnologyType,
        target_technology: TechnologyType,
        validation_scope: ValidationScope,
        **kwargs,
    ) -> ValidationSessionModel:
        """Create new validation session.

        Args:
            request_id: Unique request identifier
            source_technology: Source technology type
            target_technology: Target technology type
            validation_scope: Validation scope
            **kwargs: Additional session data

        Returns:
            ValidationSessionModel: Created session

        """
        session_data = {
            "request_id": request_id,
            "source_technology": source_technology,
            "target_technology": target_technology,
            "validation_scope": validation_scope,
            "status": "pending",
            **kwargs,
        }

        session_model = ValidationSessionModel(**session_data)
        self.session.add(session_model)
        await self.session.flush()  # Get ID without committing
        return session_model

    async def get_by_request_id(
            self, request_id: str) -> Optional[ValidationSessionModel]:
        """Get session by request ID.

        Args:
            request_id: Request identifier

        Returns:
            ValidationSessionModel or None

        """
        result = await self.session.execute(
            select(ValidationSessionModel)
            .options(
                selectinload(ValidationSessionModel.results),
                selectinload(ValidationSessionModel.discrepancies),
            )
            .where(ValidationSessionModel.request_id == request_id),
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, session_id: int) -> Optional[ValidationSessionModel]:
        """Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            ValidationSessionModel or None

        """
        result = await self.session.execute(
            select(ValidationSessionModel)
            .options(
                selectinload(ValidationSessionModel.results),
                selectinload(ValidationSessionModel.discrepancies),
            )
            .where(ValidationSessionModel.id == session_id),
        )
        return result.scalar_one_or_none()

    async def update_status(self, request_id: str, status: str) -> bool:
        """Update session status.

        Args:
            request_id: Request identifier
            status: New status

        Returns:
            bool: True if updated, False if not found

        """
        result = await self.session.execute(
            update(ValidationSessionModel)
            .where(ValidationSessionModel.request_id == request_id)
            .values(status=status, updated_at=func.now()),
        )
        return result.rowcount > 0

    async def add_log_entry(self, request_id: str, message: str) -> bool:
        """Add log entry to session.

        Args:
            request_id: Request identifier
            message: Log message

        Returns:
            bool: True if added, False if session not found

        """
        session_model = await self.get_by_request_id(request_id)
        if session_model:
            session_model.add_log_entry(message)
            return True
        return False

    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        technology_pair: Optional[Tuple[TechnologyType, TechnologyType]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[List[ValidationSessionModel], int]:
        """List validation sessions with filtering and pagination.

        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            status: Filter by status
            technology_pair: Filter by technology pair (source, target)
            date_from: Filter sessions created after this date
            date_to: Filter sessions created before this date

        Returns:
            Tuple of (sessions list, total count)

        """
        query = select(ValidationSessionModel)
        count_query = select(func.count(ValidationSessionModel.id))

        # Apply filters
        filters = []
        if status:
            filters.append(ValidationSessionModel.status == status)
        if technology_pair:
            source_tech, target_tech = technology_pair
            filters.append(
                and_(
                    ValidationSessionModel.source_technology == source_tech,
                    ValidationSessionModel.target_technology == target_tech,
                ),
            )
        if date_from:
            filters.append(ValidationSessionModel.created_at >= date_from)
        if date_to:
            filters.append(ValidationSessionModel.created_at <= date_to)

        if filters:
            filter_condition = and_(*filters)
            query = query.where(filter_condition)
            count_query = count_query.where(filter_condition)

        # Get total count
        total_result = await self.session.execute(count_query)
        total_count = total_result.scalar()

        # Get sessions with pagination
        sessions_result = await self.session.execute(
            query.options(
                selectinload(ValidationSessionModel.results),
                selectinload(ValidationSessionModel.discrepancies),
            )
            .order_by(desc(ValidationSessionModel.created_at))
            .limit(limit)
            .offset(offset),
        )
        sessions = sessions_result.scalars().all()

        return list(sessions), total_count

    async def delete_session(self, request_id: str) -> bool:
        """Delete validation session and all related data.

        Args:
            request_id: Request identifier

        Returns:
            bool: True if deleted, False if not found

        """
        session_model = await self.get_by_request_id(request_id)
        if session_model:
            await self.session.delete(session_model)
            return True
        return False

    async def get_active_sessions(self) -> List[ValidationSessionModel]:
        """Get all active (processing) sessions.

        Returns:
            List of active sessions

        """
        result = await self.session.execute(
            select(ValidationSessionModel)
            .where(ValidationSessionModel.status.in_(["pending", "processing"]))
            .order_by(ValidationSessionModel.created_at),
        )
        return list(result.scalars().all())

    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Cleanup old completed sessions.

        Args:
            days_old: Delete sessions older than this many days

        Returns:
            Number of sessions deleted

        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Only delete completed or failed sessions
        result = await self.session.execute(
            select(ValidationSessionModel).where(
                and_(
                    ValidationSessionModel.created_at < cutoff_date,
                    ValidationSessionModel.status.in_(["completed", "error"]),
                ),
            ),
        )
        old_sessions = result.scalars().all()

        for session_model in old_sessions:
            await self.session.delete(session_model)

        return len(old_sessions)


class ValidationResultRepository(BaseRepository):
    """Repository for validation result operations."""

    async def create_result(
        self,
        session_id: int,
        overall_status: str,
        fidelity_score: float,
        summary: str,
        result_type: str = "static",
        **kwargs,
    ) -> ValidationResultModel:
        """Create validation result.

        Args:
            session_id: Session ID
            overall_status: Overall validation status
            fidelity_score: Fidelity score (0.0 to 1.0)
            summary: Result summary
            result_type: Type of result (static, behavioral, hybrid)
            **kwargs: Additional result data

        Returns:
            ValidationResultModel: Created result

        """
        result_data = {
            "session_id": session_id,
            "overall_status": overall_status,
            "fidelity_score": fidelity_score,
            "summary": summary,
            "result_type": result_type,
            **kwargs,
        }

        result_model = ValidationResultModel(**result_data)
        self.session.add(result_model)
        await self.session.flush()
        return result_model

    async def get_by_session_id(self, session_id: int) -> List[ValidationResultModel]:
        """Get all results for a session.

        Args:
            session_id: Session ID

        Returns:
            List of validation results

        """
        result = await self.session.execute(
            select(ValidationResultModel)
            .where(ValidationResultModel.session_id == session_id)
            .order_by(desc(ValidationResultModel.created_at)),
        )
        return list(result.scalars().all())

    async def get_latest_by_session_id(
            self, session_id: int) -> Optional[ValidationResultModel]:
        """Get latest result for a session.

        Args:
            session_id: Session ID

        Returns:
            Latest validation result or None

        """
        result = await self.session.execute(
            select(ValidationResultModel)
            .where(ValidationResultModel.session_id == session_id)
            .order_by(desc(ValidationResultModel.created_at))
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def get_statistics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get validation result statistics.

        Args:
            date_from: Start date for statistics
            date_to: End date for statistics

        Returns:
            Dictionary with statistics

        """
        query = select(ValidationResultModel)

        if date_from:
            query = query.where(ValidationResultModel.created_at >= date_from)
        if date_to:
            query = query.where(ValidationResultModel.created_at <= date_to)

        result = await self.session.execute(query)
        results = result.scalars().all()

        if not results:
            return {
                "total_results": 0,
                "avg_fidelity_score": 0.0,
                "status_breakdown": {},
                "type_breakdown": {},
            }

        # Calculate statistics
        total_results = len(results)
        avg_fidelity = sum(r.fidelity_score for r in results) / total_results

        status_breakdown = {}
        type_breakdown = {}

        for result_model in results:
            # Status breakdown
            status = result_model.overall_status
            status_breakdown[status] = status_breakdown.get(status, 0) + 1

            # Type breakdown
            result_type = result_model.result_type
            type_breakdown[result_type] = type_breakdown.get(result_type, 0) + 1

        return {
            "total_results": total_results,
            "avg_fidelity_score": round(avg_fidelity, 3),
            "status_breakdown": status_breakdown,
            "type_breakdown": type_breakdown,
        }


class DiscrepancyRepository(BaseRepository):
    """Repository for validation discrepancy operations."""

    async def create_discrepancy(
        self,
        session_id: int,
        discrepancy_type: str,
        severity: SeverityLevel,
        description: str,
        result_id: Optional[int] = None,
        **kwargs,
    ) -> DiscrepancyModel:
        """Create validation discrepancy.

        Args:
            session_id: Session ID
            discrepancy_type: Type of discrepancy
            severity: Severity level
            description: Discrepancy description
            result_id: Optional result ID
            **kwargs: Additional discrepancy data

        Returns:
            DiscrepancyModel: Created discrepancy

        """
        discrepancy_data = {
            "session_id": session_id,
            "result_id": result_id,
            "discrepancy_type": discrepancy_type,
            "severity": severity,
            "description": description,
            **kwargs,
        }

        discrepancy_model = DiscrepancyModel(**discrepancy_data)
        self.session.add(discrepancy_model)
        await self.session.flush()
        return discrepancy_model

    async def bulk_create_discrepancies(
        self,
        session_id: int,
        discrepancies: List[ValidationDiscrepancy],
        result_id: Optional[int] = None,
    ) -> List[DiscrepancyModel]:
        """Create multiple discrepancies in bulk.

        Args:
            session_id: Session ID
            discrepancies: List of ValidationDiscrepancy objects
            result_id: Optional result ID

        Returns:
            List of created discrepancy models

        """
        discrepancy_models = []

        for discrepancy in discrepancies:
            discrepancy_data = {
                "session_id": session_id,
                "result_id": result_id,
                "discrepancy_type": discrepancy.type,
                "severity": discrepancy.severity,
                "description": discrepancy.description,
                "source_element": discrepancy.source_element,
                "target_element": discrepancy.target_element,
                "recommendation": discrepancy.recommendation,
                "confidence": discrepancy.confidence,
            }

            discrepancy_model = DiscrepancyModel(**discrepancy_data)
            self.session.add(discrepancy_model)
            discrepancy_models.append(discrepancy_model)

        await self.session.flush()
        return discrepancy_models

    async def get_by_session_id(
        self,
        session_id: int,
        severity: Optional[SeverityLevel] = None,
    ) -> List[DiscrepancyModel]:
        """Get discrepancies for a session.

        Args:
            session_id: Session ID
            severity: Optional severity filter

        Returns:
            List of discrepancies

        """
        query = select(DiscrepancyModel).where(
            DiscrepancyModel.session_id == session_id)

        if severity:
            query = query.where(DiscrepancyModel.severity == severity)

        query = query.order_by(
            DiscrepancyModel.severity.desc(), DiscrepancyModel.created_at.desc(),
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_resolved(
        self,
        discrepancy_id: int,
        resolved_by: str,
        resolution_notes: Optional[str] = None,
    ) -> bool:
        """Mark discrepancy as resolved.

        Args:
            discrepancy_id: Discrepancy ID
            resolved_by: User or system that resolved it
            resolution_notes: Optional resolution notes

        Returns:
            bool: True if updated, False if not found

        """
        result = await self.session.execute(
            update(DiscrepancyModel)
            .where(DiscrepancyModel.id == discrepancy_id)
            .values(
                is_resolved=True,
                resolved_at=func.now(),
                resolved_by=resolved_by,
                resolution_notes=resolution_notes,
                updated_at=func.now(),
            ),
        )
        return result.rowcount > 0

    async def get_discrepancy_trends(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get discrepancy trends over time.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with trend data

        """
        date_from = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            select(DiscrepancyModel)
            .where(DiscrepancyModel.created_at >= date_from)
            .order_by(DiscrepancyModel.created_at),
        )
        discrepancies = result.scalars().all()

        # Group by severity and type
        severity_trends = {severity.value: 0 for severity in SeverityLevel}
        type_trends = {}
        daily_counts = {}

        for discrepancy in discrepancies:
            # Severity trends
            severity_trends[discrepancy.severity.value] += 1

            # Type trends
            disc_type = discrepancy.discrepancy_type
            type_trends[disc_type] = type_trends.get(disc_type, 0) + 1

            # Daily counts
            day = discrepancy.created_at.date()
            daily_counts[str(day)] = daily_counts.get(str(day), 0) + 1

        return {
            "severity_trends": severity_trends,
            "type_trends": type_trends,
            "daily_counts": daily_counts,
            "total_discrepancies": len(discrepancies),
        }


class BehavioralTestRepository(BaseRepository):
    """Repository for behavioral test result operations."""

    async def create_test_result(
        self,
        session_id: int,
        scenario_name: str,
        source_url: str,
        target_url: str,
        execution_status: str,
        **kwargs,
    ) -> BehavioralTestResultModel:
        """Create behavioral test result.

        Args:
            session_id: Session ID
            scenario_name: Test scenario name
            source_url: Source system URL
            target_url: Target system URL
            execution_status: Test execution status
            **kwargs: Additional test data

        Returns:
            BehavioralTestResultModel: Created test result

        """
        test_data = {
            "session_id": session_id,
            "scenario_name": scenario_name,
            "source_url": source_url,
            "target_url": target_url,
            "execution_status": execution_status,
            **kwargs,
        }

        test_model = BehavioralTestResultModel(**test_data)
        self.session.add(test_model)
        await self.session.flush()
        return test_model

    async def get_by_session_id(
            self, session_id: int) -> List[BehavioralTestResultModel]:
        """Get behavioral test results for a session.

        Args:
            session_id: Session ID

        Returns:
            List of test results

        """
        result = await self.session.execute(
            select(BehavioralTestResultModel)
            .where(BehavioralTestResultModel.session_id == session_id)
            .order_by(BehavioralTestResultModel.created_at),
        )
        return list(result.scalars().all())


class MetricsRepository(BaseRepository):
    """Repository for validation metrics and analytics."""

    async def create_or_update_metrics(
        self,
        metric_date: datetime,
        metric_period: str,
        metrics_data: Dict[str, Any],
    ) -> ValidationMetricsModel:
        """Create or update validation metrics for a specific period.

        Args:
            metric_date: Date for the metrics
            metric_period: Period type (daily, weekly, monthly)
            metrics_data: Metrics data

        Returns:
            ValidationMetricsModel: Created or updated metrics

        """
        # Try to find existing metrics
        result = await self.session.execute(
            select(ValidationMetricsModel).where(
                and_(
                    ValidationMetricsModel.metric_date == metric_date,
                    ValidationMetricsModel.metric_period == metric_period,
                ),
            ),
        )
        existing_metrics = result.scalar_one_or_none()

        if existing_metrics:
            # Update existing metrics
            for key, value in metrics_data.items():
                if hasattr(existing_metrics, key):
                    setattr(existing_metrics, key, value)
            existing_metrics.updated_at = func.now()
            return existing_metrics
        # Create new metrics
        metrics_data.update(
            {
                "metric_date": metric_date,
                "metric_period": metric_period,
            },
        )
        metrics_model = ValidationMetricsModel(**metrics_data)
        self.session.add(metrics_model)
        await self.session.flush()
        return metrics_model

    async def get_metrics(
        self,
        period: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[ValidationMetricsModel]:
        """Get metrics for a specific period.

        Args:
            period: Period type (daily, weekly, monthly)
            date_from: Start date
            date_to: End date

        Returns:
            List of metrics

        """
        query = select(ValidationMetricsModel).where(
            ValidationMetricsModel.metric_period == period,
        )

        if date_from:
            query = query.where(ValidationMetricsModel.metric_date >= date_from)
        if date_to:
            query = query.where(ValidationMetricsModel.metric_date <= date_to)

        query = query.order_by(ValidationMetricsModel.metric_date)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def compute_daily_metrics(self, target_date: datetime) -> Dict[str, Any]:
        """Compute metrics for a specific date.

        Args:
            target_date: Date to compute metrics for

        Returns:
            Dictionary with computed metrics

        """
        # Get sessions for the target date
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        sessions_result = await self.session.execute(
            select(ValidationSessionModel)
            .options(
                selectinload(ValidationSessionModel.results),
                selectinload(ValidationSessionModel.discrepancies),
            )
            .where(
                and_(
                    ValidationSessionModel.created_at >= start_of_day,
                    ValidationSessionModel.created_at < end_of_day,
                ),
            ),
        )
        sessions = sessions_result.scalars().all()

        # Compute metrics
        total_sessions = len(sessions)
        completed_sessions = len([s for s in sessions if s.status == "completed"])
        failed_sessions = len([s for s in sessions if s.status == "error"])

        results = []
        for session in sessions:
            results.extend(session.results)

        approved_count = len([r for r in results if r.overall_status == "approved"])
        approved_with_warnings_count = len(
            [r for r in results if r.overall_status == "approved_with_warnings"],
        )
        rejected_count = len([r for r in results if r.overall_status == "rejected"])

        execution_times = [r.execution_time for r in results if r.execution_time]
        avg_execution_time = sum(execution_times) / \
            len(execution_times) if execution_times else 0
        max_execution_time = max(execution_times) if execution_times else 0
        min_execution_time = min(execution_times) if execution_times else 0

        fidelity_scores = [r.fidelity_score for r in results]
        avg_fidelity_score = sum(fidelity_scores) / \
            len(fidelity_scores) if fidelity_scores else 0
        max_fidelity_score = max(fidelity_scores) if fidelity_scores else 0
        min_fidelity_score = min(fidelity_scores) if fidelity_scores else 0

        all_discrepancies = []
        for session in sessions:
            all_discrepancies.extend(session.discrepancies)

        total_discrepancies = len(all_discrepancies)
        critical_discrepancies = len(
            [d for d in all_discrepancies if d.severity == SeverityLevel.CRITICAL],
        )
        warning_discrepancies = len(
            [d for d in all_discrepancies if d.severity == SeverityLevel.WARNING],
        )
        info_discrepancies = len(
            [d for d in all_discrepancies if d.severity == SeverityLevel.INFO],
        )

        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "failed_sessions": failed_sessions,
            "approved_count": approved_count,
            "approved_with_warnings_count": approved_with_warnings_count,
            "rejected_count": rejected_count,
            "avg_execution_time": avg_execution_time,
            "max_execution_time": max_execution_time,
            "min_execution_time": min_execution_time,
            "avg_fidelity_score": avg_fidelity_score,
            "max_fidelity_score": max_fidelity_score,
            "min_fidelity_score": min_fidelity_score,
            "total_discrepancies": total_discrepancies,
            "critical_discrepancies": critical_discrepancies,
            "warning_discrepancies": warning_discrepancies,
            "info_discrepancies": info_discrepancies,
        }
