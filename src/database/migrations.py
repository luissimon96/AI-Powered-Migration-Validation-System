"""Database migration utilities and helpers.

Provides utilities for database migrations, schema updates,
and data migration between different system versions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, text

from alembic import command

from .models import Base
from .session import DatabaseManager

logger = logging.getLogger(__name__)


class MigrationManager:
    """Database migration manager for handling schema changes.

    Provides methods for running migrations, checking migration status,
    and handling data migrations between system versions.
    """

    def __init__(self, db_manager: DatabaseManager,
                 alembic_config_path: str = "alembic.ini"):
        """Initialize migration manager.

        Args:
            db_manager: Database manager instance
            alembic_config_path: Path to Alembic configuration file

        """
        self.db_manager = db_manager
        self.alembic_config_path = alembic_config_path
        self._alembic_config: Optional[Config] = None

    @property
    def alembic_config(self) -> Config:
        """Get Alembic configuration."""
        if self._alembic_config is None:
            self._alembic_config = Config(self.alembic_config_path)
            # Set database URL from our config
            self._alembic_config.set_main_option(
                "sqlalchemy.url", self.db_manager.config.url)
        return self._alembic_config

    async def get_current_revision(self) -> Optional[str]:
        """Get current database revision.

        Returns:
            Current revision ID or None if no migrations applied

        """
        try:
            async with self.db_manager.get_session() as session:
                async with session.get_bind().connect() as conn:
                    # Check if alembic_version table exists
                    result = await conn.execute(
                        text(
                            """
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = 'alembic_version'
                        )
                        """,
                        ),
                    )
                    table_exists = result.scalar()

                    if not table_exists:
                        return None

                    # Get current revision
                    result = await conn.execute(
                        text("SELECT version_num FROM alembic_version LIMIT 1"),
                    )
                    revision = result.scalar()
                    return revision

        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None

    async def get_head_revision(self) -> Optional[str]:
        """Get head revision from migration scripts.

        Returns:
            Head revision ID or None if no migrations

        """
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_config)
            return script_dir.get_current_head()
        except Exception as e:
            logger.error(f"Failed to get head revision: {e}")
            return None

    async def is_migration_needed(self) -> bool:
        """Check if database migration is needed.

        Returns:
            True if migration is needed, False otherwise

        """
        current = await self.get_current_revision()
        head = await self.get_head_revision()

        if current is None and head is not None:
            return True  # Need initial migration

        return current != head

    async def run_migrations(self, target_revision: str = "head") -> bool:
        """Run database migrations.

        Args:
            target_revision: Target revision to migrate to

        Returns:
            True if successful, False otherwise

        """
        try:
            logger.info(f"Running migrations to revision: {target_revision}")

            # Run migrations using Alembic
            command.upgrade(self.alembic_config, target_revision)

            logger.info("Database migrations completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            return False

    async def generate_migration(
        self,
        message: str,
        autogenerate: bool = True,
    ) -> Optional[str]:
        """Generate new migration script.

        Args:
            message: Migration message
            autogenerate: Whether to auto-generate migration script

        Returns:
            Generated migration revision ID or None if failed

        """
        try:
            logger.info(f"Generating migration: {message}")

            # Generate migration
            if autogenerate:
                revision = command.revision(
                    self.alembic_config,
                    message=message,
                    autogenerate=True,
                )
            else:
                revision = command.revision(
                    self.alembic_config,
                    message=message,
                )

            logger.info(f"Migration generated with revision: {revision.revision}")
            return revision.revision

        except Exception as e:
            logger.error(f"Failed to generate migration: {e}")
            return None

    async def create_tables_if_not_exist(self) -> bool:
        """Create all tables if they don't exist (for initial setup).

        Returns:
            True if successful, False otherwise

        """
        try:
            logger.info("Creating database tables if they don't exist")
            await self.db_manager.create_tables()
            logger.info("Database tables created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            return False

    async def validate_schema(self) -> Dict[str, Any]:
        """Validate database schema against expected schema.

        Returns:
            Dictionary with validation results

        """
        try:
            async with self.db_manager.get_session() as session:
                async with session.get_bind().connect() as conn:
                    # Get database metadata
                    metadata = MetaData()
                    await conn.run_sync(metadata.reflect)

                    # Compare with expected schema
                    expected_tables = set(Base.metadata.tables.keys())
                    actual_tables = set(metadata.tables.keys())

                    missing_tables = expected_tables - actual_tables
                    extra_tables = actual_tables - expected_tables

                    return {
                        "is_valid": len(missing_tables) == 0,
                        "expected_tables": list(expected_tables),
                        "actual_tables": list(actual_tables),
                        "missing_tables": list(missing_tables),
                        "extra_tables": list(extra_tables),
                    }

        except Exception as e:
            logger.error(f"Failed to validate schema: {e}")
            return {
                "is_valid": False,
                "error": str(e),
            }


class DataMigrator:
    """Data migration utilities for handling data transformations
    between different system versions.
    """

    def __init__(self, db_manager: DatabaseManager):
        """Initialize data migrator.

        Args:
            db_manager: Database manager instance

        """
        self.db_manager = db_manager

    async def migrate_validation_sessions_v1_to_v2(self) -> bool:
        """Example data migration: Migrate validation sessions from v1 to v2 format.

        This is an example of how to handle data migrations when
        the schema or data format changes between versions.

        Returns:
            True if successful, False otherwise

        """
        try:
            logger.info("Starting validation sessions v1 to v2 migration")

            async with self.db_manager.get_session() as session:
                # Example: Add default values for new columns
                await session.execute(
                    text(
                        """
                    UPDATE validation_sessions
                    SET behavioral_timeout = 300
                    WHERE behavioral_timeout IS NULL
                    """,
                    ),
                )

                # Example: Convert old JSON format to new format
                await session.execute(
                    text(
                        """
                    UPDATE validation_sessions
                    SET source_metadata = COALESCE(source_metadata, '{}')
                    WHERE source_metadata IS NULL
                    """,
                    ),
                )

                await session.commit()

            logger.info("Validation sessions v1 to v2 migration completed")
            return True

        except Exception as e:
            logger.error(f"Failed to migrate validation sessions: {e}")
            return False

    async def migrate_discrepancies_add_component_type(self) -> bool:
        """Example: Add component_type field to existing discrepancies.

        Returns:
            True if successful, False otherwise

        """
        try:
            logger.info("Starting discrepancies component_type migration")

            async with self.db_manager.get_session() as session:
                # Set default component_type based on discrepancy_type
                mappings = [
                    ("ui", [
                        "missing_ui_element", "ui_layout_mismatch", "visual_difference"]), ("backend", [
                            "missing_function", "logic_divergence", "api_mismatch"]), ("data", [
                                "missing_field", "type_mismatch", "constraint_violation"]), ("behavioral", [
                                    "interaction_failure", "navigation_error", "form_submission_error"], ), ]

                for component_type, discrepancy_types in mappings:
                    type_conditions = " OR ".join(
                        [f"discrepancy_type = '{dt}'" for dt in discrepancy_types],
                    )
                    await session.execute(
                        text(
                            f"""
                        UPDATE validation_discrepancies
                        SET component_type = '{component_type}'
                        WHERE component_type IS NULL AND ({type_conditions})
                        """,
                        ),
                    )

                # Set default for any remaining records
                await session.execute(
                    text(
                        """
                    UPDATE validation_discrepancies
                    SET component_type = 'general'
                    WHERE component_type IS NULL
                    """,
                    ),
                )

                await session.commit()

            logger.info("Discrepancies component_type migration completed")
            return True

        except Exception as e:
            logger.error(f"Failed to migrate discrepancies: {e}")
            return False

    async def cleanup_orphaned_records(self) -> Dict[str, int]:
        """Clean up orphaned records that might exist due to failed operations.

        Returns:
            Dictionary with count of cleaned records by type

        """
        cleanup_counts = {}

        try:
            logger.info("Starting orphaned records cleanup")

            async with self.db_manager.get_session() as session:
                # Clean up validation results without sessions
                result = await session.execute(
                    text(
                        """
                    DELETE FROM validation_results
                    WHERE session_id NOT IN (SELECT id FROM validation_sessions)
                    """,
                    ),
                )
                cleanup_counts["orphaned_results"] = result.rowcount

                # Clean up discrepancies without sessions
                result = await session.execute(
                    text(
                        """
                    DELETE FROM validation_discrepancies
                    WHERE session_id NOT IN (SELECT id FROM validation_sessions)
                    """,
                    ),
                )
                cleanup_counts["orphaned_discrepancies"] = result.rowcount

                # Clean up behavioral test results without sessions
                result = await session.execute(
                    text(
                        """
                    DELETE FROM behavioral_test_results
                    WHERE session_id NOT IN (SELECT id FROM validation_sessions)
                    """,
                    ),
                )
                cleanup_counts["orphaned_behavioral_tests"] = result.rowcount

                await session.commit()

            total_cleaned = sum(cleanup_counts.values())
            logger.info(
                f"Orphaned records cleanup completed: {total_cleaned} records cleaned")

            return cleanup_counts

        except Exception as e:
            logger.error(f"Failed to cleanup orphaned records: {e}")
            return {"error": str(e)}

    async def backup_data(self, backup_tables: Optional[List[str]] = None) -> bool:
        """Create backup of important data before migrations.

        Args:
            backup_tables: List of table names to backup, or None for all tables

        Returns:
            True if successful, False otherwise

        """
        try:
            backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            logger.info(f"Creating data backup with timestamp: {backup_timestamp}")

            if backup_tables is None:
                backup_tables = [
                    "validation_sessions",
                    "validation_results",
                    "validation_discrepancies",
                    "behavioral_test_results",
                ]

            async with self.db_manager.get_session() as session:
                for table_name in backup_tables:
                    backup_table_name = f"{table_name}_backup_{backup_timestamp}"

                    # Create backup table
                    await session.execute(
                        text(
                            f"""
                        CREATE TABLE {backup_table_name} AS
                        SELECT * FROM {table_name}
                        """,
                        ),
                    )

                    logger.info(f"Backed up table: {table_name} -> {backup_table_name}")

                await session.commit()

            logger.info("Data backup completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to backup data: {e}")
            return False
