#!/usr/bin/env python3
"""Database management CLI for AI-Powered Migration Validation System.

Provides command-line interface for database operations including
initialization, migration, backup, and maintenance tasks.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.database.config import get_database_config
from src.database.migrations import MigrationManager
from src.database.session import get_database_manager
from src.database.utils import (
    cleanup_database,
    export_session_data,
    get_database_statistics,
    optimize_database_performance,
    validate_database_integrity,
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database with tables and initial setup."""
    logger.info("Initializing database...")

    try:
        db_manager = get_database_manager()
        await db_manager.initialize()
        await db_manager.create_tables()

        logger.info("Database initialization completed successfully")
        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


async def run_migrations(target_revision: str = "head"):
    """Run database migrations."""
    logger.info(f"Running migrations to revision: {target_revision}")

    try:
        db_manager = get_database_manager()
        migration_manager = MigrationManager(db_manager)

        # Check if migration is needed
        is_needed = await migration_manager.is_migration_needed()
        if not is_needed:
            logger.info("Database is already up to date")
            return True

        # Run migrations
        success = await migration_manager.run_migrations(target_revision)
        if success:
            logger.info("Migrations completed successfully")
        else:
            logger.error("Migration failed")

        return success

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


async def check_migration_status():
    """Check current migration status."""
    logger.info("Checking migration status...")

    try:
        db_manager = get_database_manager()
        migration_manager = MigrationManager(db_manager)

        current = await migration_manager.get_current_revision()
        head = await migration_manager.get_head_revision()
        is_needed = await migration_manager.is_migration_needed()

        print(f"Current revision: {current or 'None'}")
        print(f"Head revision: {head or 'None'}")
        print(f"Migration needed: {is_needed}")

        return True

    except Exception as e:
        logger.error(f"Failed to check migration status: {e}")
        return False


async def validate_schema():
    """Validate database schema."""
    logger.info("Validating database schema...")

    try:
        db_manager = get_database_manager()
        migration_manager = MigrationManager(db_manager)

        validation_result = await migration_manager.validate_schema()

        if validation_result.get("is_valid"):
            logger.info("Database schema is valid")
        else:
            logger.warning("Database schema issues found:")
            for issue in validation_result.get("missing_tables", []):
                logger.warning(f"  Missing table: {issue}")
            for issue in validation_result.get("extra_tables", []):
                logger.warning(f"  Extra table: {issue}")

        return validation_result.get("is_valid", False)

    except Exception as e:
        logger.error(f"Schema validation failed: {e}")
        return False


async def cleanup_old_data(days: int = 30, include_failed: bool = True):
    """Clean up old validation data."""
    logger.info(f"Cleaning up data older than {days} days...")

    try:
        db_manager = get_database_manager()
        await db_manager.initialize()

        async with db_manager.get_session() as session:
            cleanup_counts = await cleanup_database(
                session, days_old=days, include_failed=include_failed
            )

            if "error" in cleanup_counts:
                logger.error(f"Cleanup failed: {cleanup_counts['error']}")
                return False

            total = sum(cleanup_counts.values())
            logger.info(f"Cleanup completed: {total} records removed")

            for record_type, count in cleanup_counts.items():
                if count > 0:
                    logger.info(f"  {record_type}: {count}")

            return True

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return False


async def show_statistics():
    """Show database statistics."""
    logger.info("Generating database statistics...")

    try:
        db_manager = get_database_manager()
        await db_manager.initialize()

        async with db_manager.get_session() as session:
            stats = await get_database_statistics(session)

            if "error" in stats:
                logger.error(f"Failed to get statistics: {stats['error']}")
                return False

            print("\n=== Database Statistics ===")
            print(f"Generated at: {stats.get('generated_at')}")
            print(f"Sessions (total): {stats.get('validation_sessions_count', 0)}")
            print(f"Sessions (last week): {stats.get('sessions_last_week', 0)}")
            print(f"Results: {stats.get('validation_results_count', 0)}")
            print(f"Discrepancies: {stats.get('validation_discrepancies_count', 0)}")
            print(f"Behavioral tests: {stats.get('behavioral_test_results_count', 0)}")
            print(f"Success rate: {stats.get('success_rate', 0)}%")
            print(f"Average fidelity: {stats.get('avg_fidelity_score', 0)}")

            if stats.get("popular_technology_pairs"):
                print("\nPopular technology pairs:")
                for pair in stats["popular_technology_pairs"]:
                    print(f"  {pair['source']} → {pair['target']}: {pair['count']}")

            if stats.get("common_discrepancy_types"):
                print("\nCommon discrepancy types:")
                for disc_type in stats["common_discrepancy_types"]:
                    print(f"  {disc_type['type']}: {disc_type['count']}")

            return True

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        return False


async def optimize_performance():
    """Optimize database performance."""
    logger.info("Optimizing database performance...")

    try:
        db_manager = get_database_manager()
        await db_manager.initialize()

        async with db_manager.get_session() as session:
            optimization_result = await optimize_database_performance(session)

            if optimization_result.get("status") == "completed":
                logger.info("Database optimization completed")

                for key, value in optimization_result.items():
                    if key not in ["status", "timestamp"]:
                        logger.info(f"  {key}: {value}")

                return True
            else:
                logger.error(f"Optimization failed: {optimization_result.get('error')}")
                return False

    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        return False


async def validate_integrity():
    """Validate database integrity."""
    logger.info("Validating database integrity...")

    try:
        db_manager = get_database_manager()
        await db_manager.initialize()

        async with db_manager.get_session() as session:
            validation_result = await validate_database_integrity(session)

            if validation_result.get("is_valid"):
                logger.info("Database integrity validation passed")
                return True
            else:
                logger.warning("Database integrity issues found:")
                for issue in validation_result.get("integrity_issues", []):
                    logger.warning(f"  {issue}")

                return False

    except Exception as e:
        logger.error(f"Integrity validation failed: {e}")
        return False


async def export_session(
    request_id: str, output_file: str = None, include_representations: bool = False
):
    """Export session data."""
    logger.info(f"Exporting session: {request_id}")

    try:
        db_manager = get_database_manager()
        await db_manager.initialize()

        async with db_manager.get_session() as session:
            session_data = await export_session_data(
                session, request_id, include_representations=include_representations
            )

            if not session_data:
                logger.error(f"Session {request_id} not found")
                return False

            # Generate output filename if not provided
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"session_export_{request_id}_{timestamp}.json"

            # Write to file
            with open(output_file, "w") as f:
                json.dump(session_data, f, indent=2, default=str)

            logger.info(f"Session data exported to: {output_file}")
            return True

    except Exception as e:
        logger.error(f"Export failed: {e}")
        return False


async def backup_database(output_file: str = None):
    """Create database backup."""
    logger.info("Creating database backup...")

    try:
        db_config = get_database_config()

        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"database_backup_{timestamp}.sql"

        if db_config.is_postgresql:
            # PostgreSQL backup
            import subprocess
            from urllib.parse import urlparse

            url = urlparse(db_config.url)
            cmd = [
                "pg_dump",
                f"--host={url.hostname}",
                f"--port={url.port or 5432}",
                f"--username={url.username}",
                f"--dbname={url.path[1:]}",  # Remove leading slash
                f"--file={output_file}",
                "--verbose",
                "--no-password",
            ]

            if url.password:
                import os

                os.environ["PGPASSWORD"] = url.password

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Database backup created: {output_file}")
                return True
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return False

        elif db_config.is_sqlite:
            # SQLite backup
            import shutil

            db_file = db_config.url.replace("sqlite:///", "").replace(
                "sqlite+aiosqlite:///", ""
            )
            shutil.copy2(db_file, output_file)
            logger.info(f"Database backup created: {output_file}")
            return True

        else:
            logger.error("Backup not supported for this database type")
            return False

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return False


async def reset_database():
    """Reset database (drop and recreate all tables)."""
    logger.warning("This will delete ALL data in the database!")
    response = input("Are you sure you want to continue? (yes/no): ")

    if response.lower() != "yes":
        logger.info("Operation cancelled")
        return False

    logger.info("Resetting database...")

    try:
        db_manager = get_database_manager()
        await db_manager.initialize()
        await db_manager.reset_database()

        logger.info("Database reset completed")
        return True

    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Database management CLI for AI-Powered Migration Validation System"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Initialize command
    subparsers.add_parser("init", help="Initialize database with tables")

    # Migration commands
    migrate_parser = subparsers.add_parser("migrate", help="Run database migrations")
    migrate_parser.add_argument(
        "--revision", default="head", help="Target revision (default: head)"
    )

    subparsers.add_parser("migration-status", help="Check migration status")
    subparsers.add_parser("validate-schema", help="Validate database schema")

    # Maintenance commands
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old data")
    cleanup_parser.add_argument(
        "--days", type=int, default=30, help="Delete data older than N days"
    )
    cleanup_parser.add_argument(
        "--exclude-failed",
        action="store_true",
        help="Exclude failed sessions from cleanup",
    )

    subparsers.add_parser("stats", help="Show database statistics")
    subparsers.add_parser("optimize", help="Optimize database performance")
    subparsers.add_parser("validate", help="Validate database integrity")

    # Export/backup commands
    export_parser = subparsers.add_parser("export", help="Export session data")
    export_parser.add_argument("request_id", help="Request ID to export")
    export_parser.add_argument("--output", help="Output file path")
    export_parser.add_argument(
        "--include-representations",
        action="store_true",
        help="Include source/target representations",
    )

    backup_parser = subparsers.add_parser("backup", help="Create database backup")
    backup_parser.add_argument("--output", help="Output file path")

    # Reset command
    subparsers.add_parser("reset", help="Reset database (WARNING: deletes all data)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run the appropriate command
    try:
        if args.command == "init":
            success = asyncio.run(init_database())
        elif args.command == "migrate":
            success = asyncio.run(run_migrations(args.revision))
        elif args.command == "migration-status":
            success = asyncio.run(check_migration_status())
        elif args.command == "validate-schema":
            success = asyncio.run(validate_schema())
        elif args.command == "cleanup":
            success = asyncio.run(
                cleanup_old_data(days=args.days, include_failed=not args.exclude_failed)
            )
        elif args.command == "stats":
            success = asyncio.run(show_statistics())
        elif args.command == "optimize":
            success = asyncio.run(optimize_performance())
        elif args.command == "validate":
            success = asyncio.run(validate_integrity())
        elif args.command == "export":
            success = asyncio.run(
                export_session(
                    args.request_id, args.output, args.include_representations
                )
            )
        elif args.command == "backup":
            success = asyncio.run(backup_database(args.output))
        elif args.command == "reset":
            success = asyncio.run(reset_database())
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1

        return 0 if success else 1

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
