"""
Database utilities and helper functions.

Provides utility functions for database operations, data conversion,
and maintenance tasks.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.models import (
    MigrationValidationRequest,
    SeverityLevel,
    ValidationDiscrepancy,
    ValidationResult,
    ValidationSession,
)
from .models import DiscrepancyModel, ValidationResultModel, ValidationSessionModel
from .session import get_database_manager

logger = logging.getLogger(__name__)


async def convert_pydantic_to_db_models(
    validation_session: ValidationSession,
    session: AsyncSession,
) -> ValidationSessionModel:
    """
    Convert Pydantic ValidationSession to database models.

    Args:
        validation_session: Pydantic validation session
        session: Database session

    Returns:
        ValidationSessionModel: Database session model
    """
    request = validation_session.request

    # Create session model
    session_model = ValidationSessionModel(
        request_id=request.request_id,
        source_technology=request.source_technology.type,
        target_technology=request.target_technology.type,
        validation_scope=request.validation_scope,
        source_technology_version=request.source_technology.version,
        source_framework_details=request.source_technology.framework_details,
        target_technology_version=request.target_technology.version,
        target_framework_details=request.target_technology.framework_details,
        source_input_type=request.source_input.type,
        source_files=request.source_input.files,
        source_screenshots=request.source_input.screenshots,
        source_urls=request.source_input.urls,
        source_metadata=request.source_input.metadata,
        target_input_type=request.target_input.type,
        target_files=request.target_input.files,
        target_screenshots=request.target_input.screenshots,
        target_urls=request.target_input.urls,
        target_metadata=request.target_input.metadata,
        validation_scenarios=request.target_input.validation_scenarios,
        processing_log=validation_session.processing_log,
        session_metadata=request.target_input.metadata,
        status="pending",
    )

    session.add(session_model)
    await session.flush()

    return session_model


async def convert_db_model_to_pydantic(
    session_model: ValidationSessionModel,
) -> ValidationSession:
    """
    Convert database session model to Pydantic ValidationSession.

    Args:
        session_model: Database session model

    Returns:
        ValidationSession: Pydantic validation session
    """
    from ..core.models import InputData, MigrationValidationRequest, TechnologyContext

    # Reconstruct technology contexts
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

    # Reconstruct input data
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

    # Reconstruct validation request
    validation_request = MigrationValidationRequest(
        source_technology=source_technology,
        target_technology=target_technology,
        validation_scope=session_model.validation_scope,
        source_input=source_input,
        target_input=target_input,
        request_id=session_model.request_id,
        created_at=session_model.created_at,
    )

    # Create validation session
    validation_session = ValidationSession(request=validation_request)
    validation_session.processing_log = session_model.processing_log or []

    # Add result if available
    if session_model.results:
        latest_result = session_model.results[0]

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


async def migrate_in_memory_sessions_to_db(
    memory_sessions: Dict[str, ValidationSession],
    session: AsyncSession,
) -> Dict[str, bool]:
    """
    Migrate in-memory validation sessions to database.

    Args:
        memory_sessions: Dictionary of in-memory sessions
        session: Database session

    Returns:
        Dictionary mapping request_id to migration success status
    """
    migration_results = {}

    for request_id, validation_session in memory_sessions.items():
        try:
            # Check if session already exists in database
            existing = await session.execute(
                text("SELECT id FROM validation_sessions WHERE request_id = :request_id"),
                {"request_id": request_id},
            )
            if existing.scalar():
                logger.info(f"Session {request_id} already exists in database, skipping")
                migration_results[request_id] = True
                continue

            # Convert and save session
            session_model = await convert_pydantic_to_db_models(validation_session, session)

            # Save result if available
            if validation_session.result:
                result_model = ValidationResultModel(
                    session_id=session_model.id,
                    overall_status=validation_session.result.overall_status,
                    fidelity_score=validation_session.result.fidelity_score,
                    summary=validation_session.result.summary,
                    execution_time=validation_session.result.execution_time,
                    result_type="static",
                )
                session.add(result_model)
                await session.flush()

                # Save discrepancies
                for discrepancy in validation_session.result.discrepancies:
                    disc_model = DiscrepancyModel(
                        session_id=session_model.id,
                        result_id=result_model.id,
                        discrepancy_type=discrepancy.type,
                        severity=discrepancy.severity,
                        description=discrepancy.description,
                        source_element=discrepancy.source_element,
                        target_element=discrepancy.target_element,
                        recommendation=discrepancy.recommendation,
                        confidence=discrepancy.confidence,
                    )
                    session.add(disc_model)

            migration_results[request_id] = True
            logger.info(f"Successfully migrated session {request_id} to database")

        except Exception as e:
            logger.error(f"Failed to migrate session {request_id}: {e}")
            migration_results[request_id] = False

    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to commit migration batch: {e}")
        # Mark all as failed
        for request_id in migration_results:
            migration_results[request_id] = False

    return migration_results


async def cleanup_database(
    session: AsyncSession,
    days_old: int = 30,
    include_failed: bool = True,
) -> Dict[str, int]:
    """
    Clean up old records from the database.

    Args:
        session: Database session
        days_old: Delete records older than this many days
        include_failed: Whether to include failed sessions in cleanup

    Returns:
        Dictionary with cleanup counts by type
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    cleanup_counts = {}

    try:
        # Build status filter
        status_filter = ["completed"]
        if include_failed:
            status_filter.append("error")

        status_placeholders = ",".join([f"'{s}'" for s in status_filter])

        # Delete old validation sessions (cascading deletes will handle related records)
        result = await session.execute(
            text(
                f"""
            DELETE FROM validation_sessions
            WHERE created_at < :cutoff_date
            AND status IN ({status_placeholders})
            """
            ),
            {"cutoff_date": cutoff_date},
        )
        cleanup_counts["sessions"] = result.rowcount

        # Clean up orphaned records that might exist
        result = await session.execute(
            text(
                """
            DELETE FROM validation_results
            WHERE session_id NOT IN (SELECT id FROM validation_sessions)
            """
            )
        )
        cleanup_counts["orphaned_results"] = result.rowcount

        result = await session.execute(
            text(
                """
            DELETE FROM validation_discrepancies
            WHERE session_id NOT IN (SELECT id FROM validation_sessions)
            """
            )
        )
        cleanup_counts["orphaned_discrepancies"] = result.rowcount

        result = await session.execute(
            text(
                """
            DELETE FROM behavioral_test_results
            WHERE session_id NOT IN (SELECT id FROM validation_sessions)
            """
            )
        )
        cleanup_counts["orphaned_behavioral_tests"] = result.rowcount

        await session.commit()

        total_cleaned = sum(cleanup_counts.values())
        logger.info(f"Database cleanup completed: {total_cleaned} records removed")

        return cleanup_counts

    except Exception as e:
        await session.rollback()
        logger.error(f"Database cleanup failed: {e}")
        return {"error": str(e)}


async def get_database_statistics(session: AsyncSession) -> Dict[str, Any]:
    """
    Get comprehensive database statistics.

    Args:
        session: Database session

    Returns:
        Dictionary with database statistics
    """
    try:
        stats = {}

        # Table counts
        tables = [
            "validation_sessions",
            "validation_results",
            "validation_discrepancies",
            "behavioral_test_results",
            "validation_metrics",
        ]

        for table in tables:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            stats[f"{table}_count"] = result.scalar()

        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        result = await session.execute(
            text(
                """
            SELECT COUNT(*) FROM validation_sessions
            WHERE created_at >= :week_ago
            """
            ),
            {"week_ago": week_ago},
        )
        stats["sessions_last_week"] = result.scalar()

        # Success rate
        result = await session.execute(
            text(
                """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed
            FROM validation_sessions
            """
            )
        )
        row = result.fetchone()
        if row.total > 0:
            stats["success_rate"] = round((row.completed / row.total) * 100, 2)
            stats["failure_rate"] = round((row.failed / row.total) * 100, 2)
        else:
            stats["success_rate"] = 0
            stats["failure_rate"] = 0

        # Average fidelity score
        result = await session.execute(
            text(
                """
            SELECT AVG(fidelity_score) FROM validation_results
            WHERE created_at >= :week_ago
            """
            ),
            {"week_ago": week_ago},
        )
        avg_fidelity = result.scalar()
        stats["avg_fidelity_score"] = round(avg_fidelity, 3) if avg_fidelity else 0

        # Most common technologies
        result = await session.execute(
            text(
                """
            SELECT
                source_technology,
                target_technology,
                COUNT(*) as count
            FROM validation_sessions
            WHERE created_at >= :week_ago
            GROUP BY source_technology, target_technology
            ORDER BY count DESC
            LIMIT 5
            """
            ),
            {"week_ago": week_ago},
        )
        stats["popular_technology_pairs"] = [
            {"source": row.source_technology, "target": row.target_technology, "count": row.count}
            for row in result.fetchall()
        ]

        # Most common discrepancy types
        result = await session.execute(
            text(
                """
            SELECT
                discrepancy_type,
                COUNT(*) as count
            FROM validation_discrepancies
            WHERE created_at >= :week_ago
            GROUP BY discrepancy_type
            ORDER BY count DESC
            LIMIT 5
            """
            ),
            {"week_ago": week_ago},
        )
        stats["common_discrepancy_types"] = [
            {"type": row.discrepancy_type, "count": row.count} for row in result.fetchall()
        ]

        stats["generated_at"] = datetime.utcnow().isoformat()
        return stats

    except Exception as e:
        logger.error(f"Failed to get database statistics: {e}")
        return {"error": str(e)}


async def optimize_database_performance(session: AsyncSession) -> Dict[str, Any]:
    """
    Optimize database performance by analyzing and updating statistics.

    Args:
        session: Database session

    Returns:
        Dictionary with optimization results
    """
    try:
        optimization_results = {}

        # Get database type
        db_url = str(session.get_bind().url)

        if "postgresql" in db_url:
            # PostgreSQL optimizations
            logger.info("Running PostgreSQL optimizations...")

            # Analyze tables to update statistics
            tables = [
                "validation_sessions",
                "validation_results",
                "validation_discrepancies",
                "behavioral_test_results",
            ]

            for table in tables:
                await session.execute(text(f"ANALYZE {table}"))

            optimization_results["analyzed_tables"] = len(tables)

            # Check for unused indexes (this is a simplified check)
            result = await session.execute(
                text(
                    """
                SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
                FROM pg_stat_user_indexes
                WHERE idx_tup_read = 0 AND idx_tup_fetch = 0
                """
                )
            )
            unused_indexes = result.fetchall()
            optimization_results["unused_indexes"] = len(unused_indexes)

        elif "sqlite" in db_url:
            # SQLite optimizations
            logger.info("Running SQLite optimizations...")

            # Analyze database
            await session.execute(text("ANALYZE"))
            optimization_results["analyzed"] = True

            # Vacuum if needed (this would need to be done outside of transaction)
            optimization_results["vacuum_recommended"] = True

        await session.commit()

        optimization_results["status"] = "completed"
        optimization_results["timestamp"] = datetime.utcnow().isoformat()

        logger.info("Database optimization completed")
        return optimization_results

    except Exception as e:
        await session.rollback()
        logger.error(f"Database optimization failed: {e}")
        return {"status": "failed", "error": str(e)}


async def validate_database_integrity(session: AsyncSession) -> Dict[str, Any]:
    """
    Validate database integrity and relationships.

    Args:
        session: Database session

    Returns:
        Dictionary with validation results
    """
    try:
        validation_results = {}
        issues = []

        # Check for orphaned records
        result = await session.execute(
            text(
                """
            SELECT COUNT(*) FROM validation_results
            WHERE session_id NOT IN (SELECT id FROM validation_sessions)
            """
            )
        )
        orphaned_results = result.scalar()
        if orphaned_results > 0:
            issues.append(f"{orphaned_results} orphaned validation results")

        result = await session.execute(
            text(
                """
            SELECT COUNT(*) FROM validation_discrepancies
            WHERE session_id NOT IN (SELECT id FROM validation_sessions)
            """
            )
        )
        orphaned_discrepancies = result.scalar()
        if orphaned_discrepancies > 0:
            issues.append(f"{orphaned_discrepancies} orphaned discrepancies")

        # Check for sessions without results that should have them
        result = await session.execute(
            text(
                """
            SELECT COUNT(*) FROM validation_sessions
            WHERE status = 'completed' AND id NOT IN (SELECT session_id FROM validation_results)
            """
            )
        )
        completed_without_results = result.scalar()
        if completed_without_results > 0:
            issues.append(f"{completed_without_results} completed sessions without results")

        # Check for invalid fidelity scores
        result = await session.execute(
            text(
                """
            SELECT COUNT(*) FROM validation_results
            WHERE fidelity_score < 0 OR fidelity_score > 1
            """
            )
        )
        invalid_scores = result.scalar()
        if invalid_scores > 0:
            issues.append(f"{invalid_scores} invalid fidelity scores")

        validation_results["integrity_issues"] = issues
        validation_results["is_valid"] = len(issues) == 0
        validation_results["issues_count"] = len(issues)
        validation_results["checked_at"] = datetime.utcnow().isoformat()

        if len(issues) == 0:
            logger.info("Database integrity validation passed")
        else:
            logger.warning(f"Database integrity issues found: {issues}")

        return validation_results

    except Exception as e:
        logger.error(f"Database integrity validation failed: {e}")
        return {
            "is_valid": False,
            "error": str(e),
            "checked_at": datetime.utcnow().isoformat(),
        }


async def export_session_data(
    session: AsyncSession,
    request_id: str,
    include_representations: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Export complete session data for backup or analysis.

    Args:
        session: Database session
        request_id: Request identifier
        include_representations: Include source/target representations

    Returns:
        Dictionary with complete session data or None if not found
    """
    try:
        # Get session with all related data
        from sqlalchemy.orm import selectinload

        result = await session.execute(
            text(
                """
            SELECT * FROM validation_sessions WHERE request_id = :request_id
            """
            ),
            {"request_id": request_id},
        )
        session_row = result.fetchone()

        if not session_row:
            return None

        # Export session data
        session_data = dict(session_row._mapping)
        session_data["created_at"] = session_data["created_at"].isoformat()
        session_data["updated_at"] = session_data["updated_at"].isoformat()

        # Get results
        result = await session.execute(
            text(
                """
            SELECT * FROM validation_results WHERE session_id = :session_id
            ORDER BY created_at DESC
            """
            ),
            {"session_id": session_data["id"]},
        )
        results = []
        for row in result.fetchall():
            result_data = dict(row._mapping)
            result_data["created_at"] = result_data["created_at"].isoformat()
            result_data["updated_at"] = result_data["updated_at"].isoformat()

            if not include_representations:
                result_data.pop("source_representation", None)
                result_data.pop("target_representation", None)

            results.append(result_data)

        session_data["results"] = results

        # Get discrepancies
        result = await session.execute(
            text(
                """
            SELECT * FROM validation_discrepancies WHERE session_id = :session_id
            ORDER BY severity DESC, created_at DESC
            """
            ),
            {"session_id": session_data["id"]},
        )
        discrepancies = []
        for row in result.fetchall():
            disc_data = dict(row._mapping)
            disc_data["created_at"] = disc_data["created_at"].isoformat()
            disc_data["updated_at"] = disc_data["updated_at"].isoformat()
            if disc_data["resolved_at"]:
                disc_data["resolved_at"] = disc_data["resolved_at"].isoformat()
            discrepancies.append(disc_data)

        session_data["discrepancies"] = discrepancies

        # Get behavioral test results if any
        result = await session.execute(
            text(
                """
            SELECT * FROM behavioral_test_results WHERE session_id = :session_id
            ORDER BY created_at
            """
            ),
            {"session_id": session_data["id"]},
        )
        behavioral_tests = []
        for row in result.fetchall():
            test_data = dict(row._mapping)
            test_data["created_at"] = test_data["created_at"].isoformat()
            test_data["updated_at"] = test_data["updated_at"].isoformat()
            behavioral_tests.append(test_data)

        session_data["behavioral_tests"] = behavioral_tests

        session_data["exported_at"] = datetime.utcnow().isoformat()
        return session_data

    except Exception as e:
        logger.error(f"Failed to export session data for {request_id}: {e}")
        return None
