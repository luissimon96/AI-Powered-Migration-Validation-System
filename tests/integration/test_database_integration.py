"""Database integration tests for T002 completion.
Ultra-compressed implementation focusing on core database operations.
"""

import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.models import ValidationRequest, ValidationScope
from src.database.integration import DatabaseManager
from src.database.models import ValidationResult, ValidationSession


@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseIntegration:
    """Database integration tests."""

    async def test_session_persistence_workflow(self, db_session, sample_user):
        """Test complete session persistence workflow."""
        db_manager = DatabaseManager(db_session)

        # Create validation request
        request = ValidationRequest(
            source_technology="python-flask",
            target_technology="java-spring",
            validation_scope=ValidationScope.BUSINESS_LOGIC,
        )

        # Create session
        session = ValidationSession(
            user_id=sample_user.id,
            request_data=request.dict(),
            status="processing",
            created_at=datetime.utcnow(),
        )

        # Persist session
        saved_session = await db_manager.create_session(session)
        assert saved_session.id is not None
        assert saved_session.status == "processing"

        # Update session with results
        result = ValidationResult(
            overall_status="approved",
            fidelity_score=0.85,
            differences_found=[],
        )

        saved_session.result_data = result.dict()
        saved_session.status = "completed"
        await db_manager.update_session(saved_session)

        # Retrieve and verify
        retrieved = await db_manager.get_session(saved_session.id)
        assert retrieved.status == "completed"
        assert retrieved.result_data["fidelity_score"] == 0.85

    async def test_session_search_filtering(self, db_session, sample_user):
        """Test session search and filtering."""
        db_manager = DatabaseManager(db_session)

        # Create multiple sessions
        sessions = []
        for i, tech in enumerate(["python-flask", "java-spring", "react"]):
            session = ValidationSession(
                user_id=sample_user.id,
                request_data={
                    "source_technology": tech,
                    "target_technology": "nodejs",
                    "validation_scope": "business_logic",
                },
                status="completed" if i % 2 == 0 else "failed",
                created_at=datetime.utcnow() - timedelta(days=i),
            )
            sessions.append(await db_manager.create_session(session))

        # Search by technology
        python_sessions = await db_manager.search_sessions(
            user_id=sample_user.id,
            source_technology="python-flask",
        )
        assert len(python_sessions) == 1
        assert python_sessions[0].request_data["source_technology"] == "python-flask"

        # Search by status
        completed_sessions = await db_manager.search_sessions(
            user_id=sample_user.id,
            status="completed",
        )
        assert len(completed_sessions) == 2

        # Search by date range
        recent_sessions = await db_manager.search_sessions(
            user_id=sample_user.id,
            created_after=datetime.utcnow() - timedelta(days=1),
        )
        assert len(recent_sessions) >= 1

    async def test_session_archival_cleanup(self, db_session, sample_user):
        """Test session archival and cleanup."""
        db_manager = DatabaseManager(db_session)

        # Create old session
        old_session = ValidationSession(
            user_id=sample_user.id,
            request_data={"source_technology": "legacy"},
            status="completed",
            created_at=datetime.utcnow() - timedelta(days=91),  # 3+ months old
        )
        await db_manager.create_session(old_session)

        # Create recent session
        recent_session = ValidationSession(
            user_id=sample_user.id,
            request_data={"source_technology": "current"},
            status="completed",
            created_at=datetime.utcnow() - timedelta(days=1),
        )
        await db_manager.create_session(recent_session)

        # Run cleanup
        cleanup_count = await db_manager.cleanup_old_sessions(max_age_days=90)
        assert cleanup_count == 1

        # Verify recent session still exists
        remaining = await db_manager.search_sessions(user_id=sample_user.id)
        assert len(remaining) == 1
        assert remaining[0].request_data["source_technology"] == "current"

    async def test_database_transaction_rollback(self, db_session):
        """Test database transaction rollback on errors."""
        db_manager = DatabaseManager(db_session)

        # Attempt to create session with invalid data
        with pytest.raises(IntegrityError):
            invalid_session = ValidationSession(
                user_id=999999,  # Non-existent user
                request_data={},
                status="processing",
            )
            await db_manager.create_session(invalid_session)

        # Verify no partial data was saved
        all_sessions = await db_manager.get_all_sessions()
        invalid_sessions = [s for s in all_sessions if s.user_id == 999999]
        assert len(invalid_sessions) == 0

    async def test_concurrent_session_access(self, db_session, sample_user):
        """Test concurrent session access patterns."""
        db_manager = DatabaseManager(db_session)

        # Create session
        session = ValidationSession(
            user_id=sample_user.id,
            request_data={"concurrent_test": True},
            status="processing",
        )
        saved_session = await db_manager.create_session(session)

        # Simulate concurrent reads
        tasks = []
        for _ in range(5):
            task = db_manager.get_session(saved_session.id)
            tasks.append(task)

        # Execute concurrent reads
        results = await asyncio.gather(*tasks)

        # Verify all reads successful
        assert len(results) == 5
        assert all(r.id == saved_session.id for r in results)
        assert all(r.request_data["concurrent_test"] is True for r in results)


@pytest.mark.integration
class TestDatabaseMigrations:
    """Test database migration integration."""

    def test_migration_version_tracking(self, db_session):
        """Test migration version tracking."""
        from alembic.runtime.migration import MigrationContext

        # Get current migration version
        context = MigrationContext.configure(db_session.connection())
        current_rev = context.get_current_revision()

        assert current_rev is not None
        assert len(current_rev) > 0

    def test_soft_delete_functionality(self, db_session, sample_user):
        """Test soft delete functionality."""
        # Create session
        session = ValidationSession(
            user_id=sample_user.id,
            request_data={"test": "soft_delete"},
            status="completed",
        )
        db_session.add(session)
        db_session.commit()

        # Soft delete
        session.deleted_at = datetime.utcnow()
        db_session.commit()

        # Verify not in active queries
        active_sessions = db_session.query(ValidationSession).filter(
            ValidationSession.deleted_at.is_(None),
        ).all()
        assert session not in active_sessions

        # Verify still in database with deleted_at
        all_sessions = db_session.query(ValidationSession).filter(
            ValidationSession.id == session.id,
        ).all()
        assert len(all_sessions) == 1
        assert all_sessions[0].deleted_at is not None


@pytest.mark.integration
class TestDatabasePerformance:
    """Test database performance scenarios."""

    async def test_bulk_session_operations(self, db_session, sample_user):
        """Test bulk session operations performance."""
        db_manager = DatabaseManager(db_session)

        # Create multiple sessions in bulk
        sessions = []
        for i in range(50):
            session = ValidationSession(
                user_id=sample_user.id,
                request_data={"bulk_test": i},
                status="completed",
            )
            sessions.append(session)

        # Bulk insert
        start_time = datetime.utcnow()
        created_sessions = await db_manager.bulk_create_sessions(sessions)
        end_time = datetime.utcnow()

        # Verify performance
        duration = (end_time - start_time).total_seconds()
        assert duration < 5.0  # Should complete in under 5 seconds
        assert len(created_sessions) == 50

    def test_connection_pooling(self, db_session):
        """Test database connection pooling."""
        # Verify connection pool configuration
        engine = db_session.get_bind()
        pool = engine.pool

        assert pool.size() > 0
        assert hasattr(pool, "checked_in")
        assert hasattr(pool, "checked_out")


# Import asyncio for gather
