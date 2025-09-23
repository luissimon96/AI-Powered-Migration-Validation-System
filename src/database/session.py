"""Database session management for AI-Powered Migration Validation System.

Provides async database session handling, connection management,
and transaction support for the FastAPI application.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from .config import DatabaseConfig, get_database_config
from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database manager for handling connections and sessions.

    Provides centralized database connection management with
    connection pooling, health checks, and session lifecycle management.
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """Initialize database manager.

        Args:
            config: Database configuration. If None, loads from environment.

        """
        self.config = config or get_database_config()
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._is_initialized = False

    @property
    def engine(self) -> AsyncEngine:
        """Get database engine, initializing if necessary."""
        if not self._engine:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker:
        """Get session factory, initializing if necessary."""
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory

    async def initialize(self) -> None:
        """Initialize database engine and session factory.

        Creates the async engine with appropriate connection pooling
        and session factory for the application.
        """
        if self._is_initialized:
            logger.warning("Database already initialized")
            return

        try:
            logger.info(f"Initializing database connection to {self.config.url}")

            # Create async engine
            engine_kwargs = self.config.engine_kwargs.copy()

            # For testing, use NullPool to avoid connection issues
            if ":memory:" in self.config.url or "test" in self.config.url:
                engine_kwargs["poolclass"] = NullPool

            self._engine = create_async_engine(self.config.url, **engine_kwargs)

            # Create session factory
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                autocommit=self.config.autocommit,
                autoflush=self.config.autoflush,
                expire_on_commit=self.config.expire_on_commit,
            )

            # Test connection
            await self.health_check()

            self._is_initialized = True
            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            await self.close()
            raise

    async def close(self) -> None:
        """Close database connections and cleanup resources."""
        if self._engine:
            logger.info("Closing database connections")
            await self._engine.dispose()
            self._engine = None

        self._session_factory = None
        self._is_initialized = False

    async def health_check(self) -> bool:
        """Perform database health check.

        Returns:
            True if database is healthy, False otherwise

        """
        try:
            async with self.get_session() as session:
                # Execute a simple query to test connection
                result = await session.execute("SELECT 1")
                await result.fetchone()
                return True

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with automatic transaction management.

        Yields:
            AsyncSession: Database session

        Raises:
            SQLAlchemyError: If database operation fails

        """
        if not self._is_initialized:
            await self.initialize()

        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

    async def create_tables(self) -> None:
        """Create all database tables.

        This method creates all tables defined in the models.
        Should be called during application startup or migrations.
        """
        if not self._is_initialized:
            await self.initialize()

        try:
            logger.info("Creating database tables")
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")

        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    async def drop_tables(self) -> None:
        """Drop all database tables.

        WARNING: This will delete all data. Use with caution!
        """
        if not self._is_initialized:
            await self.initialize()

        try:
            logger.warning("Dropping all database tables")
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped successfully")

        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise

    async def reset_database(self) -> None:
        """Reset database by dropping and recreating all tables.

        WARNING: This will delete all data. Use with caution!
        """
        await self.drop_tables()
        await self.create_tables()

    async def execute_with_retry(self, operation, max_retries: int = None) -> any:
        """Execute database operation with retry logic.

        Args:
            operation: Async callable to execute
            max_retries: Maximum number of retries

        Returns:
            Operation result

        """
        max_retries = max_retries or self.config.connect_retries
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return await operation()
            except SQLAlchemyError as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = self.config.retry_interval * (2**attempt)
                    logger.warning(
                        f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {wait_time}s: {e}",
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Database operation failed after {
                            max_retries + 1} attempts")

        raise last_exception


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get global database manager instance.

    Returns:
        DatabaseManager: Global database manager

    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting database sessions.

    This function is designed to be used as a FastAPI dependency
    to provide database sessions to route handlers.

    Yields:
        AsyncSession: Database session

    Example:
        @app.get("/api/sessions")
        async def list_sessions(db: AsyncSession = Depends(get_db_session)):
            # Use db session here
            pass

    """
    db_manager = get_database_manager()
    async with db_manager.get_session() as session:
        yield session


async def initialize_database() -> None:
    """Initialize database for application startup.

    This function should be called during FastAPI application startup
    to ensure database connectivity and table creation.
    """
    db_manager = get_database_manager()
    await db_manager.initialize()

    # Create tables if they don't exist
    await db_manager.create_tables()


async def close_database() -> None:
    """Close database connections for application shutdown.

    This function should be called during FastAPI application shutdown
    to properly close database connections and cleanup resources.
    """
    global _db_manager
    if _db_manager:
        await _db_manager.close()
        _db_manager = None


# Context manager for database lifecycle
@asynccontextmanager
async def database_lifespan():
    """Database lifecycle context manager.

    Can be used with FastAPI lifespan events to manage database
    initialization and cleanup.

    Example:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with database_lifespan():
                yield

    """
    try:
        await initialize_database()
        yield
    finally:
        await close_database()
