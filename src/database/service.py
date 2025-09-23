"""Database service layer for AI-Powered Migration Validation System.

Provides high-level business logic methods that integrate the repository
pattern with the existing Pydantic models and system architecture.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.models import (MigrationValidationRequest, TechnologyType,
                           ValidationDiscrepancy, ValidationResult,
                           ValidationSession)
from .models import ValidationSessionModel
from .repositories import (BehavioralTestRepository, DiscrepancyRepository,
                           MetricsRepository, ValidationResultRepository,
                           ValidationSessionRepository)

logger = logging.getLogger(__name__)


class ValidationDatabaseService:
    """High-level database service for validation operations.

    Bridges between the Pydantic models used by the application
    and the SQLAlchemy models used for persistence.
    """

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: AsyncSession for database operations

        """
        self.session = session
        self.session_repo = ValidationSessionRepository(session)
        self.result_repo = ValidationResultRepository(session)
        self.discrepancy_repo = DiscrepancyRepository(session)
        self.behavioral_repo = BehavioralTestRepository(session)
        self.metrics_repo = MetricsRepository(session)

    async def create_validation_session(
        self,
        validation_request: MigrationValidationRequest,
    ) -> ValidationSession:
        """Create a new validation session from a validation request.

        Args:
            validation_request: The migration validation request

        Returns:
            ValidationSession: Created session with database persistence

        """
        try:
            # Create database session model
            session_model = await self.session_repo.create_session(
                request_id=validation_request.request_id,
                source_technology=validation_request.source_technology.type,
                target_technology=validation_request.target_technology.type,
                validation_scope=validation_request.validation_scope,
                source_technology_version=validation_request.source_technology.version,
                source_framework_details=validation_request.source_technology.framework_details,
                target_technology_version=validation_request.target_technology.version,
                target_framework_details=validation_request.target_technology.framework_details,
                source_input_type=validation_request.source_input.type,
                source_files=validation_request.source_input.files,
                source_screenshots=validation_request.source_input.screenshots,
                source_urls=validation_request.source_input.urls,
                source_metadata=validation_request.source_input.metadata,
                target_input_type=validation_request.target_input.type,
                target_files=validation_request.target_input.files,
                target_screenshots=validation_request.target_input.screenshots,
                target_urls=validation_request.target_input.urls,
                target_metadata=validation_request.target_input.metadata,
                validation_scenarios=validation_request.target_input.validation_scenarios,
                session_metadata=validation_request.target_input.metadata,
            )

            await self.session.commit()

            # Convert to Pydantic ValidationSession
            validation_session = ValidationSession(request=validation_request)
            validation_session.add_log("Validation session created in database")

            logger.info(f"Created validation session: {validation_request.request_id}")
            return validation_session

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create validation session: {e}")
            raise

    async def get_validation_session(
            self, request_id: str) -> Optional[ValidationSession]:
        """Retrieve a validation session by request ID.

        Args:
            request_id: Request identifier

        Returns:
            ValidationSession or None if not found

        """
        try:
            session_model = await self.session_repo.get_by_request_id(request_id)
            if not session_model:
                return None

            # Convert database model back to Pydantic model
            validation_session = await self._convert_session_model_to_pydantic(session_model)
            return validation_session

        except Exception as e:
            logger.error(f"Failed to get validation session {request_id}: {e}")
            return None

    async def update_session_status(self, request_id: str, status: str) -> bool:
        """Update validation session status.

        Args:
            request_id: Request identifier
            status: New status (pending, processing, completed, error)

        Returns:
            True if updated successfully

        """
        try:
            updated = await self.session_repo.update_status(request_id, status)
            if updated:
                await self.session.commit()
                logger.info(f"Updated session {request_id} status to {status}")
            return updated

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update session status: {e}")
            return False

    async def add_session_log(self, request_id: str, message: str) -> bool:
        """Add log entry to validation session.

        Args:
            request_id: Request identifier
            message: Log message

        Returns:
            True if added successfully

        """
        try:
            added = await self.session_repo.add_log_entry(request_id, message)
            if added:
                await self.session.commit()
            return added

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to add session log: {e}")
            return False

    async def save_validation_result(
        self,
        request_id: str,
        validation_result: ValidationResult,
        result_type: str = "static",
        source_representation: Optional[Dict[str, Any]] = None,
        target_representation: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Save validation result to database.

        Args:
            request_id: Request identifier
            validation_result: Validation result to save
            result_type: Type of result (static, behavioral, hybrid)
            source_representation: Source system representation
            target_representation: Target system representation

        Returns:
            True if saved successfully

        """
        try:
            # Get session
            session_model = await self.session_repo.get_by_request_id(request_id)
            if not session_model:
                logger.error(f"Session not found: {request_id}")
                return False

            # Create result model
            result_model = await self.result_repo.create_result(
                session_id=session_model.id,
                overall_status=validation_result.overall_status,
                fidelity_score=validation_result.fidelity_score,
                summary=validation_result.summary,
                result_type=result_type,
                execution_time=validation_result.execution_time,
                source_representation=source_representation,
                target_representation=target_representation,
            )

            # Save discrepancies
            if validation_result.discrepancies:
                await self.discrepancy_repo.bulk_create_discrepancies(
                    session_id=session_model.id,
                    discrepancies=validation_result.discrepancies,
                    result_id=result_model.id,
                )

            # Update session status to completed
            session_model.status = "completed"
            session_model.execution_time = validation_result.execution_time

            await self.session.commit()

            logger.info(f"Saved validation result for session: {request_id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save validation result: {e}")
            return False

    async def list_validation_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        source_technology: Optional[str] = None,
        target_technology: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List validation sessions with filtering and pagination.

        Args:
            limit: Maximum sessions to return
            offset: Sessions to skip
            status: Filter by status
            source_technology: Filter by source technology
            target_technology: Filter by target technology
            date_from: Filter sessions after this date
            date_to: Filter sessions before this date

        Returns:
            Tuple of (session list, total count)

        """
        try:
            # Convert technology strings to enums
            technology_pair = None
            if source_technology and target_technology:
                try:
                    source_tech = TechnologyType(source_technology)
                    target_tech = TechnologyType(target_technology)
                    technology_pair = (source_tech, target_tech)
                except ValueError:
                    logger.warning(
                        f"Invalid technology types: {source_technology}, {target_technology}", )

            sessions, total_count = await self.session_repo.list_sessions(
                limit=limit,
                offset=offset,
                status=status,
                technology_pair=technology_pair,
                date_from=date_from,
                date_to=date_to,
            )

            # Convert to dictionaries for API response
            session_dicts = []
            for session_model in sessions:
                session_dict = session_model.to_dict()

                # Add summary information
                if session_model.results:
                    # Already ordered by created_at desc
                    latest_result = session_model.results[0]
                    session_dict["fidelity_score"] = latest_result.fidelity_score
                    session_dict["result_status"] = latest_result.overall_status

                session_dict["discrepancy_count"] = len(session_model.discrepancies)
                session_dicts.append(session_dict)

            return session_dicts, total_count

        except Exception as e:
            logger.error(f"Failed to list validation sessions: {e}")
            return [], 0

    async def get_session_statistics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get validation session statistics.

        Args:
            date_from: Start date for statistics
            date_to: End date for statistics

        Returns:
            Dictionary with session statistics

        """
        try:
            # Get result statistics
            result_stats = await self.result_repo.get_statistics(date_from, date_to)

            # Get discrepancy trends
            discrepancy_trends = await self.discrepancy_repo.get_discrepancy_trends(
                days=30 if not date_from else (datetime.utcnow() - date_from).days,
            )

            # Combine statistics
            return {
                **result_stats,
                **discrepancy_trends,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            return {"error": str(e)}

    async def delete_validation_session(self, request_id: str) -> bool:
        """Delete validation session and all related data.

        Args:
            request_id: Request identifier

        Returns:
            True if deleted successfully

        """
        try:
            deleted = await self.session_repo.delete_session(request_id)
            if deleted:
                await self.session.commit()
                logger.info(f"Deleted validation session: {request_id}")
            return deleted

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete validation session: {e}")
            return False

    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Cleanup old validation sessions.

        Args:
            days_old: Delete sessions older than this many days

        Returns:
            Number of sessions deleted

        """
        try:
            deleted_count = await self.session_repo.cleanup_old_sessions(days_old)
            if deleted_count > 0:
                await self.session.commit()
                logger.info(f"Cleaned up {deleted_count} old validation sessions")
            return deleted_count

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0

    async def _convert_session_model_to_pydantic(
        self,
        session_model: ValidationSessionModel,
    ) -> ValidationSession:
        """Convert database session model to Pydantic ValidationSession.

        Args:
            session_model: Database session model

        Returns:
            ValidationSession: Pydantic model

        """
        # Reconstruct the validation request
        from ..core.models import (InputData, MigrationValidationRequest,
                                   TechnologyContext)

        source_technology = TechnologyContext(
            type=session_model.source_technology,
            version=session_model.source_technology_version,
            framework_details=session_model.source_framework_details or {},
        )

        target_technology = TechnologyContext(
            type=session_model.target_technology,
            version=session_model.target_technology_version,
            framework_details=session_model.target_framework_details or {},
        )

        source_input = InputData(
            type=session_model.source_input_type,
            files=session_model.source_files or [],
            screenshots=session_model.source_screenshots or [],
            urls=session_model.source_urls or [],
            validation_scenarios=session_model.validation_scenarios or [],
            metadata=session_model.source_metadata or {},
        )

        target_input = InputData(
            type=session_model.target_input_type,
            files=session_model.target_files or [],
            screenshots=session_model.target_screenshots or [],
            urls=session_model.target_urls or [],
            validation_scenarios=session_model.validation_scenarios or [],
            metadata=session_model.target_metadata or {},
        )

        validation_request = MigrationValidationRequest(
            source_technology=source_technology,
            target_technology=target_technology,
            validation_scope=session_model.validation_scope,
            source_input=source_input,
            target_input=target_input,
            request_id=session_model.request_id,
            created_at=session_model.created_at,
        )

        # Create ValidationSession
        validation_session = ValidationSession(request=validation_request)
        validation_session.processing_log = session_model.processing_log or []

        # Add latest result if available
        if session_model.results:
            latest_result = session_model.results[0]  # Ordered by created_at desc

            # Convert discrepancies
            discrepancies = []
            for disc_model in session_model.discrepancies:
                discrepancy = ValidationDiscrepancy(
                    type=disc_model.discrepancy_type,
                    severity=disc_model.severity,
                    description=disc_model.description,
                    source_element=disc_model.source_element,
                    target_element=disc_model.target_element,
                    recommendation=disc_model.recommendation,
                    confidence=disc_model.confidence,
                )
                discrepancies.append(discrepancy)

            validation_result = ValidationResult(
                overall_status=latest_result.overall_status,
                fidelity_score=latest_result.fidelity_score,
                summary=latest_result.summary,
                discrepancies=discrepancies,
                execution_time=latest_result.execution_time,
                timestamp=latest_result.created_at,
            )
            validation_session.result = validation_result

        return validation_session


# Dependency injection helper
async def get_validation_service(session: AsyncSession) -> ValidationDatabaseService:
    """FastAPI dependency for getting validation database service.

    Args:
        session: Database session

    Returns:
        ValidationDatabaseService: Service instance

    """
    return ValidationDatabaseService(session)


def get_database_service(session: AsyncSession) -> ValidationDatabaseService:
    """Factory function to create ValidationDatabaseService instance.

    Args:
        session: AsyncSession for database operations

    Returns:
        ValidationDatabaseService: Configured service instance
    """
    return ValidationDatabaseService(session)
