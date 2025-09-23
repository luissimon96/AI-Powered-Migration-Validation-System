#!/usr/bin/env python3
"""Database management script for AI-Powered Migration Validation System.

Provides command-line interface for database operations including:
- Running migrations
- Creating/dropping tables
- Backup and restore operations
- Performance optimization
- Data validation and cleanup
"""

from src.database.utils import (
    cleanup_database,
    export_session_data,
    get_database_statistics,
    optimize_database_performance,
    validate_database_integrity,
)
from src.database.session import DatabaseManager
from src.database.migrations import DataMigrator, MigrationManager
from src.database.config import get_database_config
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


@click.group()
def cli():
    """Database management commands for AI-Powered Migration Validation System."""
    pass


@cli.command()
@click.option("--verbose", is_flag=True, help="Enable verbose output")
async def init(verbose: bool):
    """Initialize database and run initial setup."""
    try:
        if verbose:
            click.echo("Initializing database manager...")

        db_config = get_database_config()
        db_manager = DatabaseManager(db_config)

        await db_manager.initialize()

        if verbose:
            click.echo(f"Connected to database: {db_config.url}")

        # Create tables
        click.echo("Creating database tables...")
        await db_manager.create_tables()

        # Run migrations
        migration_manager = MigrationManager(db_manager)
        migration_needed = await migration_manager.is_migration_needed()

        if migration_needed:
            click.echo("Running database migrations...")
            success = await migration_manager.run_migrations()
            if success:
                click.echo("✅ Migrations completed successfully")
            else:
                click.echo("❌ Migrations failed")
                return

        click.echo("✅ Database initialization completed successfully")

    except Exception as e:
        click.echo(f"❌ Database initialization failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--target", default="head", help="Target migration revision")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
async def migrate(target: str, verbose: bool):
    """Run database migrations."""
    try:
        db_config = get_database_config()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()

        migration_manager = MigrationManager(db_manager)

        current = await migration_manager.get_current_revision()
        head = await migration_manager.get_head_revision()

        if verbose:
            click.echo(f"Current revision: {current or 'None'}")
            click.echo(f"Head revision: {head or 'None'}")
            click.echo(f"Target revision: {target}")

        if not await migration_manager.is_migration_needed():
            click.echo("✅ Database is already up to date")
            return

        click.echo("Running database migrations...")
        success = await migration_manager.run_migrations(target)

        if success:
            new_current = await migration_manager.get_current_revision()
            click.echo(f"✅ Migrations completed successfully (now at: {new_current})")
        else:
            click.echo("❌ Migrations failed")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Migration failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--message", "-m", required=True, help="Migration message")
@click.option("--autogenerate", is_flag=True,
              default=True, help="Auto-generate migration")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
async def create_migration(message: str, autogenerate: bool, verbose: bool):
    """Create a new migration."""
    try:
        db_config = get_database_config()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()

        migration_manager = MigrationManager(db_manager)

        if verbose:
            click.echo(f"Creating migration: {message}")

        revision = await migration_manager.generate_migration(message, autogenerate)

        if revision:
            click.echo(f"✅ Migration created successfully: {revision}")
        else:
            click.echo("❌ Migration creation failed")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Migration creation failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--include-data", is_flag=True, help="Include actual data in backup")
@click.option("--output", "-o", help="Output directory for backup")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
async def backup(include_data: bool, output: Optional[str], verbose: bool):
    """Create database backup."""
    try:
        db_config = get_database_config()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()

        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"backup_{timestamp}"

        os.makedirs(output, exist_ok=True)

        if verbose:
            click.echo(f"Creating backup in: {output}")

        # Backup schema
        migration_manager = MigrationManager(db_manager)
        schema_validation = await migration_manager.validate_schema()

        with open(os.path.join(output, "schema.json"), "w") as f:
            json.dump(schema_validation, f, indent=2)

        if verbose:
            click.echo("✅ Schema backup completed")

        if include_data:
            # Backup metadata tables
            data_migrator = DataMigrator(db_manager)
            backup_success = await data_migrator.backup_data()

            if backup_success:
                if verbose:
                    click.echo("✅ Data backup completed")
            else:
                click.echo("❌ Data backup failed")

        # Backup statistics
        async with db_manager.get_session() as session:
            stats = await get_database_statistics(session)

        with open(os.path.join(output, "statistics.json"), "w") as f:
            json.dump(stats, f, indent=2)

        click.echo(f"✅ Backup completed successfully in: {output}")

    except Exception as e:
        click.echo(f"❌ Backup failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--days-old", default=30, help="Delete sessions older than N days")
@click.option("--include-failed", is_flag=True,
              help="Include failed sessions in cleanup")
@click.option("--dry-run", is_flag=True,
              help="Show what would be deleted without deleting")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
async def cleanup(days_old: int, include_failed: bool, dry_run: bool, verbose: bool):
    """Clean up old database records."""
    try:
        db_config = get_database_config()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()

        if verbose:
            click.echo(f"Cleaning up records older than {days_old} days")
            click.echo(f"Include failed sessions: {include_failed}")
            click.echo(f"Dry run mode: {dry_run}")

        if dry_run:
            click.echo("🔍 DRY RUN MODE - No actual deletions will be performed")

        async with db_manager.get_session() as session:
            if not dry_run:
                cleanup_results = await cleanup_database(session, days_old, include_failed)
            else:
                # For dry run, just show statistics
                stats = await get_database_statistics(session)
                click.echo("Current database statistics:")
                click.echo(
                    f"  Total sessions: {
                        stats.get(
                            'validation_sessions_count',
                            0)}")
                click.echo(
                    f"  Total results: {
                        stats.get(
                            'validation_results_count',
                            0)}")
                click.echo(
                    f"  Total discrepancies: {
                        stats.get(
                            'validation_discrepancies_count',
                            0)}")
                click.echo("Use --verbose for detailed statistics")
                return

            if "error" in cleanup_results:
                click.echo(f"❌ Cleanup failed: {cleanup_results['error']}")
                sys.exit(1)

            total_cleaned = sum(v for k, v in cleanup_results.items()
                                if k != "error" and isinstance(v, int))
            click.echo(f"✅ Cleanup completed: {total_cleaned} records removed")

            if verbose:
                for key, value in cleanup_results.items():
                    if isinstance(value, int):
                        click.echo(f"  {key}: {value}")

    except Exception as e:
        click.echo(f"❌ Cleanup failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--verbose", is_flag=True, help="Enable verbose output")
async def optimize(verbose: bool):
    """Optimize database performance."""
    try:
        db_config = get_database_config()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()

        if verbose:
            click.echo("Running database optimization...")

        async with db_manager.get_session() as session:
            optimization_results = await optimize_database_performance(session)

            if optimization_results.get("status") == "completed":
                click.echo("✅ Database optimization completed successfully")

                if verbose:
                    for key, value in optimization_results.items():
                        if key != "status":
                            click.echo(f"  {key}: {value}")
            else:
                error = optimization_results.get("error", "Unknown error")
                click.echo(f"❌ Database optimization failed: {error}")
                sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Database optimization failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--verbose", is_flag=True, help="Enable verbose output")
async def validate(verbose: bool):
    """Validate database integrity."""
    try:
        db_config = get_database_config()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()

        if verbose:
            click.echo("Validating database integrity...")

        async with db_manager.get_session() as session:
            validation_results = await validate_database_integrity(session)

            if validation_results.get("is_valid"):
                click.echo("✅ Database integrity validation passed")
            else:
                click.echo("❌ Database integrity issues found:")
                for issue in validation_results.get("integrity_issues", []):
                    click.echo(f"  - {issue}")

                if "error" in validation_results:
                    click.echo(f"  Error: {validation_results['error']}")

            if verbose:
                click.echo(f"Issues found: {validation_results.get('issues_count', 0)}")
                click.echo(
                    f"Checked at: {
                        validation_results.get(
                            'checked_at',
                            'Unknown')}")

    except Exception as e:
        click.echo(f"❌ Database validation failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--verbose", is_flag=True, help="Enable verbose output")
async def stats(verbose: bool):
    """Show database statistics."""
    try:
        db_config = get_database_config()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()

        async with db_manager.get_session() as session:
            stats = await get_database_statistics(session)

            if "error" in stats:
                click.echo(f"❌ Failed to get statistics: {stats['error']}")
                sys.exit(1)

            click.echo("📊 Database Statistics:")
            click.echo(f"  Sessions: {stats.get('validation_sessions_count', 0)}")
            click.echo(f"  Results: {stats.get('validation_results_count', 0)}")
            click.echo(
                f"  Discrepancies: {
                    stats.get(
                        'validation_discrepancies_count',
                        0)}")
            click.echo(
                f"  Behavioral Tests: {
                    stats.get(
                        'behavioral_test_results_count',
                        0)}")
            click.echo(f"  Sessions (last week): {stats.get('sessions_last_week', 0)}")
            click.echo(f"  Success Rate: {stats.get('success_rate', 0)}%")
            click.echo(f"  Avg Fidelity Score: {stats.get('avg_fidelity_score', 0)}")

            if verbose:
                click.echo("\n🔍 Detailed Statistics:")
                for key, value in stats.items():
                    if key not in [
                        "validation_sessions_count",
                        "validation_results_count",
                        "validation_discrepancies_count",
                        "behavioral_test_results_count",
                        "sessions_last_week",
                        "success_rate",
                            "avg_fidelity_score"]:
                        click.echo(f"  {key}: {value}")

    except Exception as e:
        click.echo(f"❌ Failed to get statistics: {e}")
        sys.exit(1)


@cli.command()
@click.argument("request_id")
@click.option("--output", "-o", help="Output file for exported data")
@click.option("--include-representations", is_flag=True,
              help="Include source/target representations")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
async def export(
        request_id: str,
        output: Optional[str],
        include_representations: bool,
        verbose: bool):
    """Export session data for backup or analysis."""
    try:
        db_config = get_database_config()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()

        if verbose:
            click.echo(f"Exporting session data for: {request_id}")

        async with db_manager.get_session() as session:
            session_data = await export_session_data(session, request_id, include_representations)

            if not session_data:
                click.echo(f"❌ Session not found: {request_id}")
                sys.exit(1)

            if not output:
                output = f"session_{request_id}_{
                    datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(output, "w") as f:
                json.dump(session_data, f, indent=2, default=str)

            click.echo(f"✅ Session data exported to: {output}")

            if verbose:
                click.echo(f"  Results: {len(session_data.get('results', []))}")
                click.echo(
                    f"  Discrepancies: {len(session_data.get('discrepancies', []))}")
                click.echo(
                    f"  Behavioral Tests: {len(session_data.get('behavioral_tests', []))}")

    except Exception as e:
        click.echo(f"❌ Export failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--confirm", is_flag=True, help="Confirm destructive operation")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
async def reset(confirm: bool, verbose: bool):
    """Reset database (DESTRUCTIVE OPERATION)."""
    if not confirm:
        click.echo("❌ This operation will delete ALL data. Use --confirm to proceed.")
        sys.exit(1)

    try:
        if verbose:
            click.echo("⚠️  RESETTING DATABASE - ALL DATA WILL BE LOST")

        db_config = get_database_config()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()

        await db_manager.reset_database()

        click.echo("✅ Database reset completed successfully")

    except Exception as e:
        click.echo(f"❌ Database reset failed: {e}")
        sys.exit(1)


def run_async_command(func):
    """Decorator to run async commands."""
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper


# Apply async decorator to all commands
for command in [
        init,
        migrate,
        create_migration,
        backup,
        cleanup,
        optimize,
        validate,
        stats,
        export,
        reset]:
    command.callback = run_async_command(command.callback)


if __name__ == "__main__":
    cli()
