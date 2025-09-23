"""Database integration layer for the FastAPI application.

Provides integration between the existing in-memory system and the new
database persistence layer, allowing for gradual migration and fallback.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.models import ValidationSession
from .service import ValidationDatabaseService
from .session import close_database, get_db_session, initialize_database

logger = logging.getLogger(__name__)


class DatabaseIntegration:
    """Integration layer that bridges the existing system with database persistence.

    Provides methods to gradually migrate from in-memory storage to database
    persistence while maintaining backward compatibility.
    """

    def __init__(self):
        """Initialize database integration."""
        self.enabled = True
        self.fallback_to_memory = True

    async def is_database_available(self) -> bool:
        """Check if database is available and responding.

        Returns:
            True if database is available, False otherwise

        """
        try:
            async for session in get_db_session():
                service = ValidationDatabaseService(session)
                # Simple health check
                await service.session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def save_validation_session(
        self,
        validation_session: ValidationSession,
    ) -> bool:
        """Save validation session to database.

        Args:
            validation_session: ValidationSession to save

        Returns:
            True if saved successfully, False otherwise

        """
        if not self.enabled:
            return False

        try:
            async for session in get_db_session():
                service = ValidationDatabaseService(session)
                await service.create_validation_session(validation_session.request)

                # Add processing logs
                for log_entry in validation_session.processing_log:
                    await service.add_session_log(
                        validation_session.request.request_id, log_entry
                    )

                # Save result if available
                if validation_session.result:
                    await service.save_validation_result(
                        validation_session.request.request_id,
                        validation_session.result,
                    )

                return True

        except Exception as e:
            logger.error(f"Failed to save validation session to database: {e}")
            return False

    async def load_validation_session(
        self,
        request_id: str,
    ) -> Optional[ValidationSession]:
        """Load validation session from database.

        Args:
            request_id: Request identifier

        Returns:
            ValidationSession if found, None otherwise

        """
        if not self.enabled:
            return None

        try:
            async for session in get_db_session():
                service = ValidationDatabaseService(session)
                return await service.get_validation_session(request_id)

        except Exception as e:
            logger.error(f"Failed to load validation session from database: {e}")
            return None

    async def update_session_status(
        self,
        request_id: str,
        status: str,
    ) -> bool:
        """Update validation session status in database.

        Args:
            request_id: Request identifier
            status: New status

        Returns:
            True if updated successfully

        """
        if not self.enabled:
            return False

        try:
            async for session in get_db_session():
                service = ValidationDatabaseService(session)
                return await service.update_session_status(request_id, status)

        except Exception as e:
            logger.error(f"Failed to update session status in database: {e}")
            return False

    async def add_session_log(
        self,
        request_id: str,
        message: str,
    ) -> bool:
        """Add log entry to validation session in database.

        Args:
            request_id: Request identifier
            message: Log message

        Returns:
            True if added successfully

        """
        if not self.enabled:
            return False

        try:
            async for session in get_db_session():
                service = ValidationDatabaseService(session)
                return await service.add_session_log(request_id, message)

        except Exception as e:
            logger.error(f"Failed to add session log to database: {e}")
            return False

    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        **filters,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List validation sessions from database.

        Args:
            limit: Maximum sessions to return
            offset: Sessions to skip
            **filters: Additional filters

        Returns:
            Tuple of (session list, total count)

        """
        if not self.enabled:
            return [], 0

        try:
            async for session in get_db_session():
                service = ValidationDatabaseService(session)
                return await service.list_validation_sessions(
                    limit=limit,
                    offset=offset,
                    **filters,
                )

        except Exception as e:
            logger.error(f"Failed to list sessions from database: {e}")
            return [], 0

    async def delete_session(self, request_id: str) -> bool:
        """Delete validation session from database.

        Args:
            request_id: Request identifier

        Returns:
            True if deleted successfully

        """
        if not self.enabled:
            return False

        try:
            async for session in get_db_session():
                service = ValidationDatabaseService(session)
                return await service.delete_validation_session(request_id)

        except Exception as e:
            logger.error(f"Failed to delete session from database: {e}")
            return False

    async def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics from database.

        Returns:
            Dictionary with statistics

        """
        if not self.enabled:
            return {}

        try:
            async for session in get_db_session():
                service = ValidationDatabaseService(session)
                return await service.get_session_statistics()

        except Exception as e:
            logger.error(f"Failed to get statistics from database: {e}")
            return {"error": str(e)}


# Global integration instance
_db_integration: Optional[DatabaseIntegration] = None


def get_database_integration() -> DatabaseIntegration:
    """Get global database integration instance.

    Returns:
        DatabaseIntegration: Global integration instance

    """
    global _db_integration
    if _db_integration is None:
        _db_integration = DatabaseIntegration()
    return _db_integration


class HybridSessionManager:
    """Hybrid session manager that uses both in-memory and database storage.

    This manager provides a transition layer between the existing in-memory
    system and the new database persistence, allowing for gradual migration.
    """

    def __init__(self):
        """Initialize hybrid session manager."""
        self.memory_sessions: Dict[str, ValidationSession] = {}
        self.db_integration = get_database_integration()

    async def store_session(
        self,
        request_id: str,
        validation_session: ValidationSession,
    ) -> None:
        """Store validation session in both memory and database.

        Args:
            request_id: Request identifier
            validation_session: ValidationSession to store

        """
        # Always store in memory for immediate access
        self.memory_sessions[request_id] = validation_session

        # Attempt to store in database
        try:
            await self.db_integration.save_validation_session(validation_session)
        except Exception as e:
            logger.warning(f"Failed to save session {request_id} to database: {e}")

    async def get_session(self, request_id: str) -> Optional[ValidationSession]:
        """Get validation session, preferring memory but falling back to database.

        Args:
            request_id: Request identifier

        Returns:
            ValidationSession if found, None otherwise

        """
        # Check memory first
        if request_id in self.memory_sessions:
            return self.memory_sessions[request_id]

        # Fallback to database
        try:
            session = await self.db_integration.load_validation_session(request_id)
            if session:
                # Cache in memory for future access
                self.memory_sessions[request_id] = session
            return session
        except Exception as e:
            logger.warning(f"Failed to load session {request_id} from database: {e}")
            return None

    async def update_session_status(self, request_id: str, status: str) -> None:
        """Update session status in both memory and database.

        Args:
            request_id: Request identifier
            status: New status

        """
        # Update memory if exists
        if request_id in self.memory_sessions:
            # Note: ValidationSession doesn't have direct status, but we could extend it
            pass

        # Update database
        try:
            await self.db_integration.update_session_status(request_id, status)
        except Exception as e:
            logger.warning(
                f"Failed to update session {request_id} status in database: {e}"
            )

    async def add_session_log(self, request_id: str, message: str) -> None:
        """Add log entry to session in both memory and database.

        Args:
            request_id: Request identifier
            message: Log message

        """
        # Update memory if exists
        if request_id in self.memory_sessions:
            self.memory_sessions[request_id].add_log(message)

        # Update database
        try:
            await self.db_integration.add_session_log(request_id, message)
        except Exception as e:
            logger.warning(
                f"Failed to add log to session {request_id} in database: {e}"
            )

    async def list_sessions(
        self,
        include_memory: bool = True,
        include_database: bool = True,
        **filters,
    ) -> List[Dict[str, Any]]:
        """List sessions from both memory and database sources.

        Args:
            include_memory: Include in-memory sessions
            include_database: Include database sessions
            **filters: Filtering options

        Returns:
            List of session dictionaries

        """
        sessions = []

        # Get memory sessions
        if include_memory:
            for request_id, session in self.memory_sessions.items():
                session_dict = {
                    "request_id": request_id,
                    "status": "completed" if session.result else "processing",
                    "source_technology": session.request.source_technology.type.value,
                    "target_technology": session.request.target_technology.type.value,
                    "validation_scope": session.request.validation_scope.value,
                    "created_at": session.request.created_at.isoformat(),
                    "fidelity_score": session.result.fidelity_score
                    if session.result
                    else None,
                    "source": "memory",
                }
                sessions.append(session_dict)

        # Get database sessions
        if include_database:
            try:
                db_sessions, _ = await self.db_integration.list_sessions(**filters)
                for session in db_sessions:
                    session["source"] = "database"
                    sessions.append(session)
            except Exception as e:
                logger.warning(f"Failed to get sessions from database: {e}")

        return sessions

    async def delete_session(self, request_id: str) -> bool:
        """Delete session from both memory and database.

        Args:
            request_id: Request identifier

        Returns:
            True if deleted from at least one location

        """
        memory_deleted = False
        database_deleted = False

        # Delete from memory
        if request_id in self.memory_sessions:
            del self.memory_sessions[request_id]
            memory_deleted = True

        # Delete from database
        try:
            database_deleted = await self.db_integration.delete_session(request_id)
        except Exception as e:
            logger.warning(f"Failed to delete session {request_id} from database: {e}")

        return memory_deleted or database_deleted

    def clear_memory_cache(self) -> None:
        """Clear the in-memory session cache."""
        self.memory_sessions.clear()
        logger.info("Cleared in-memory session cache")


# Global hybrid session manager
_hybrid_manager: Optional[HybridSessionManager] = None


def get_hybrid_session_manager() -> HybridSessionManager:
    """Get global hybrid session manager.

    Returns:
        HybridSessionManager: Global manager instance

    """
    global _hybrid_manager
    if _hybrid_manager is None:
        _hybrid_manager = HybridSessionManager()
    return _hybrid_manager


@asynccontextmanager
async def database_lifespan(app: FastAPI):
    """Database lifespan manager for FastAPI application.

    Handles database initialization and cleanup during application lifecycle.
    """
    try:
        # Initialize database
        logger.info("Initializing database...")
        await initialize_database()

        # Check database availability
        db_integration = get_database_integration()
        db_available = await db_integration.is_database_available()

        if db_available:
            logger.info("Database initialization completed successfully")
        else:
            logger.warning(
                "Database initialization completed but database may not be fully available",
            )

        yield

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Continue with in-memory mode
        db_integration = get_database_integration()
        db_integration.enabled = False
        logger.warning("Continuing in memory-only mode")
        yield

    finally:
        try:
            logger.info("Closing database connections...")
            await close_database()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")


# FastAPI dependency for database service
async def get_db_service(
    session: AsyncSession = Depends(get_db_session),
) -> ValidationDatabaseService:
    """FastAPI dependency for getting database service.

    Args:
        session: Database session

    Returns:
        ValidationDatabaseService: Database service instance

    """
    return ValidationDatabaseService(session)
