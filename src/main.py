"""Main entry point for AI-Powered Migration Validation System.

This module provides the main application entry point and CLI interface.
"""

import asyncio
import json
import sys
from pathlib import Path

import click
import uvicorn

from .behavioral.crews import (
    BehavioralValidationRequest,
    create_behavioral_validation_crew,
)
from .core.config import get_settings, get_validation_config, is_development
from .core.migration_validator import MigrationValidator
from .core.models import (
    InputData,
    InputType,
    MigrationValidationRequest,
    TechnologyContext,
    TechnologyType,
    ValidationScope,
)


@click.group()
def cli():
    """AI-Powered Migration Validation System CLI."""


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--workers", default=1, help="Number of worker processes")
def serve(host, port, reload, workers):
    """Start the API server."""
    settings = get_settings()

    # Use settings from config if not provided via CLI
    host = host or settings.api_host
    port = port or settings.api_port

    if reload or is_development():
        workers = 1  # Auto-reload doesn't work with multiple workers

    click.echo("🚀 Starting AI-Powered Migration Validation System")
    click.echo(f"📡 Server: http://{host}:{port}")
    click.echo(f"📖 API Docs: http://{host}:{port}/docs")
    click.echo(f"🔧 Environment: {settings.environment}")

    uvicorn.run(
        "src.api.database_routes:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=settings.log_level.lower(),
    )


@cli.command()
@click.option(
    "--source-tech", required=True, help="Source technology (e.g., python-flask)"
)
@click.option(
    "--target-tech", required=True, help="Target technology (e.g., java-spring)"
)
@click.option("--source-files", required=True, help="Source files directory or file")
@click.option("--target-files", required=True, help="Target files directory or file")
@click.option("--scope", default="full_system", help="Validation scope")
@click.option("--output", help="Output file for results")
def validate(source_tech, target_tech, source_files, target_files, scope, output):
    """Run migration validation via CLI."""
    click.echo("🔍 Starting migration validation...")

    try:
        # Convert string to enum
        source_tech_enum = TechnologyType(source_tech.replace("-", "_").upper())
        target_tech_enum = TechnologyType(target_tech.replace("-", "_").upper())
        scope_enum = ValidationScope(scope.upper())

    except ValueError as e:
        click.echo(f"❌ Error: Invalid technology or scope: {e}")
        return

    # Collect files
    source_path = Path(source_files)
    target_path = Path(target_files)

    if source_path.is_file():
        source_file_list = [str(source_path)]
    else:
        source_file_list = [str(f) for f in source_path.rglob("*") if f.is_file()]

    if target_path.is_file():
        target_file_list = [str(target_path)]
    else:
        target_file_list = [str(f) for f in target_path.rglob("*") if f.is_file()]

    if not source_file_list:
        click.echo(f"❌ Error: No source files found in {source_files}")
        return

    if not target_file_list:
        click.echo(f"❌ Error: No target files found in {target_files}")
        return

    click.echo(f"📁 Source files: {len(source_file_list)}")
    click.echo(f"📁 Target files: {len(target_file_list)}")

    # Create validation request
    request = MigrationValidationRequest(
        source_technology=TechnologyContext(type=source_tech_enum),
        target_technology=TechnologyContext(type=target_tech_enum),
        validation_scope=scope_enum,
        source_input=InputData(type=InputType.CODE_FILES, files=source_file_list),
        target_input=InputData(type=InputType.CODE_FILES, files=target_file_list),
    )

    # Run validation
    async def run_validation():
        validator = MigrationValidator()
        session = await validator.validate_migration(request)
        return session

    session = asyncio.run(run_validation())

    # Display results
    if session.result:
        click.echo("\n✅ Validation completed!")
        click.echo(f"📊 Status: {session.result.overall_status}")
        click.echo(f"🎯 Fidelity Score: {session.result.fidelity_score:.2%}")
        click.echo(f"⚠️  Discrepancies: {len(session.result.discrepancies)}")
        click.echo(f"⏱️  Execution Time: {session.result.execution_time:.1f}s")

        if session.result.discrepancies:
            click.echo("\n🔍 Key Issues:")
            for i, disc in enumerate(session.result.discrepancies[:5], 1):
                click.echo(f"  {i}. [{disc.severity.value.upper()}] {disc.description}")

            if len(session.result.discrepancies) > 5:
                click.echo(f"  ... and {len(session.result.discrepancies) - 5} more")

        # Save results if output specified
        if output:
            output_path = Path(output)
            report = await validator.generate_report(session, "json")
            output_path.write_text(report)
            click.echo(f"💾 Results saved to: {output}")

    else:
        click.echo("❌ Validation failed - no results generated")


@cli.command()
@click.option("--source-url", required=True, help="Source system URL")
@click.option("--target-url", required=True, help="Target system URL")
@click.option("--scenarios", help="Validation scenarios (comma-separated)")
@click.option("--output", help="Output file for results")
def behavioral(source_url, target_url, scenarios, output):
    """Run behavioral validation via CLI."""
    click.echo("🎭 Starting behavioral validation...")

    # Parse scenarios
    scenario_list = (
        scenarios.split(",")
        if scenarios
        else [
            "User login flow",
            "Form submission and validation",
            "Error handling scenarios",
        ]
    )

    click.echo(f"🌐 Source URL: {source_url}")
    click.echo(f"🎯 Target URL: {target_url}")
    click.echo(f"📝 Scenarios: {len(scenario_list)}")

    # Create behavioral validation request
    request = BehavioralValidationRequest(
        source_url=source_url,
        target_url=target_url,
        validation_scenarios=scenario_list,
        timeout=300,
    )

    # Run behavioral validation
    async def run_behavioral_validation():
        crew = create_behavioral_validation_crew()
        result = await crew.validate_migration(request)
        return result

    result = asyncio.run(run_behavioral_validation())

    # Display results
    click.echo("\n✅ Behavioral validation completed!")
    click.echo(f"📊 Status: {result.overall_status}")
    click.echo(f"🎯 Fidelity Score: {result.fidelity_score:.2%}")
    click.echo(f"⚠️  Discrepancies: {len(result.discrepancies)}")
    click.echo(f"⏱️  Execution Time: {result.execution_time:.1f}s")

    if result.discrepancies:
        click.echo("\n🔍 Key Issues:")
        for i, disc in enumerate(result.discrepancies[:3], 1):
            click.echo(f"  {i}. [{disc.severity.value.upper()}] {disc.description}")

    # Save results if output specified
    if output:
        output_path = Path(output)
        result_data = {
            "overall_status": result.overall_status,
            "fidelity_score": result.fidelity_score,
            "discrepancies": [
                {
                    "type": d.type,
                    "severity": d.severity.value,
                    "description": d.description,
                    "recommendation": d.recommendation,
                }
                for d in result.discrepancies
            ],
            "execution_log": result.execution_log,
            "execution_time": result.execution_time,
            "timestamp": result.timestamp.isoformat(),
        }

        output_path.write_text(json.dumps(result_data, indent=2))
        click.echo(f"💾 Results saved to: {output}")


@cli.command()
def config():
    """Show current configuration."""
    settings = get_settings()
    validation_config = get_validation_config()

    click.echo("⚙️  System Configuration:")
    click.echo(f"  Environment: {settings.environment}")
    click.echo(f"  Debug: {settings.debug}")
    click.echo(f"  API Host: {settings.api_host}:{settings.api_port}")
    click.echo(f"  Log Level: {settings.log_level}")

    click.echo("\n🤖 LLM Configuration:")
    click.echo(f"  Default Provider: {settings.default_llm_provider}")
    click.echo(f"  Default Model: {settings.default_llm_model}")

    available_providers = validation_config.list_available_providers()
    if available_providers:
        click.echo(f"  Available Providers: {', '.join(available_providers)}")
    else:
        click.echo("  ⚠️  No LLM providers configured with valid API keys")

    click.echo("\n📁 File Settings:")
    click.echo(f"  Upload Directory: {settings.upload_dir}")
    click.echo(f"  Max File Size: {settings.max_file_size / 1024 / 1024:.1f}MB")
    click.echo(f"  Max Files per Request: {settings.max_files_per_request}")


@cli.command()
def health():
    """Check system health and dependencies."""
    click.echo("🔧 System Health Check:")

    # Check core dependencies
    try:
        import fastapi

        click.echo(f"✅ FastAPI: {fastapi.__version__}")
    except ImportError:
        click.echo("❌ FastAPI: Not installed")

    try:
        import crewai

        click.echo("✅ CrewAI: Available")
    except ImportError:
        click.echo("❌ CrewAI: Not installed")

    # Check database dependencies
    click.echo("\n🗃️  Database:")

    try:
        import sqlalchemy

        click.echo(f"✅ SQLAlchemy: {sqlalchemy.__version__}")
    except ImportError:
        click.echo("❌ SQLAlchemy: Not installed")

    try:
        import alembic

        click.echo("✅ Alembic: Available")
    except ImportError:
        click.echo("❌ Alembic: Not installed")

    try:
        import asyncpg

        click.echo(f"✅ AsyncPG: {asyncpg.__version__}")
    except ImportError:
        click.echo("❌ AsyncPG: Not installed")

    try:
        import aiosqlite

        click.echo(f"✅ AIOSQLite: {aiosqlite.__version__}")
    except ImportError:
        click.echo("❌ AIOSQLite: Not installed")

    # Check LLM providers
    click.echo("\n🤖 LLM Providers:")

    try:
        import openai

        click.echo(f"✅ OpenAI: {openai.__version__}")
    except ImportError:
        click.echo("❌ OpenAI: Not installed")

    try:
        import anthropic

        click.echo("✅ Anthropic: Available")
    except ImportError:
        click.echo("❌ Anthropic: Not installed")

    try:
        import google.generativeai

        click.echo("✅ Google GenAI: Available")
    except ImportError:
        click.echo("❌ Google GenAI: Not installed")

    # Check browser automation
    click.echo("\n🌐 Browser Automation:")

    try:
        import playwright

        click.echo("✅ Playwright: Available")
    except ImportError:
        click.echo("❌ Playwright: Not installed")

    # Check database connectivity
    click.echo("\n💾 Database Connectivity:")
    try:
        from .database.config import get_database_config
        from .database.session import DatabaseManager

        async def check_db():
            db_config = get_database_config()
            db_manager = DatabaseManager(db_config)
            try:
                await db_manager.initialize()
                is_healthy = await db_manager.health_check()
                return is_healthy, db_config.url
            except Exception as e:
                return False, str(e)
            finally:
                await db_manager.close()

        is_healthy, db_info = asyncio.run(check_db())
        if is_healthy:
            click.echo(f"✅ Database: Connected ({db_info})")
        else:
            click.echo(f"❌ Database: Connection failed ({db_info})")

    except Exception as e:
        click.echo(f"❌ Database: Configuration error ({e})")

    # Check configuration
    click.echo("\n⚙️  Configuration:")
    validation_config = get_validation_config()
    available_providers = validation_config.list_available_providers()

    if available_providers:
        click.echo(f"✅ LLM Providers: {', '.join(available_providers)}")
    else:
        click.echo("⚠️  No LLM providers configured")


@cli.command()
@click.option("--target", default="head", help="Target migration revision")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def db_init(target: str, verbose: bool):
    """Initialize database and run migrations."""
    click.echo("🗃️  Initializing database...")

    try:
        from .database.config import get_database_config
        from .database.migrations import MigrationManager
        from .database.session import DatabaseManager

        async def init_database():
            db_config = get_database_config()
            db_manager = DatabaseManager(db_config)

            await db_manager.initialize()

            if verbose:
                click.echo(f"Connected to database: {db_config.url}")

            # Create tables
            await db_manager.create_tables()

            # Run migrations
            migration_manager = MigrationManager(db_manager)
            migration_needed = await migration_manager.is_migration_needed()

            if migration_needed:
                click.echo("Running database migrations...")
                success = await migration_manager.run_migrations(target)
                if success:
                    click.echo("✅ Migrations completed successfully")
                else:
                    click.echo("❌ Migrations failed")
                    return False
            else:
                click.echo("✅ Database is already up to date")

            await db_manager.close()
            return True

        success = asyncio.run(init_database())
        if success:
            click.echo("✅ Database initialization completed successfully")
        else:
            click.echo("❌ Database initialization failed")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Database initialization failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--days-old", default=30, help="Delete sessions older than N days")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be deleted without deleting"
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def db_cleanup(days_old: int, dry_run: bool, verbose: bool):
    """Clean up old database records."""
    click.echo(f"🧹 Cleaning up database records older than {days_old} days...")

    try:
        from .database.config import get_database_config
        from .database.session import DatabaseManager
        from .database.utils import cleanup_database, get_database_statistics

        async def cleanup_db():
            db_config = get_database_config()
            db_manager = DatabaseManager(db_config)
            await db_manager.initialize()

            async with db_manager.get_session() as session:
                if dry_run:
                    stats = await get_database_statistics(session)
                    click.echo("Current database statistics:")
                    click.echo(
                        f"  Total sessions: {stats.get('validation_sessions_count', 0)}"
                    )
                    click.echo(
                        f"  Total results: {stats.get('validation_results_count', 0)}"
                    )
                    click.echo("Use without --dry-run to perform actual cleanup")
                    return True

                cleanup_results = await cleanup_database(session, days_old, True)

                if "error" in cleanup_results:
                    click.echo(f"❌ Cleanup failed: {cleanup_results['error']}")
                    return False

                total_cleaned = sum(
                    v
                    for k, v in cleanup_results.items()
                    if k != "error" and isinstance(v, int)
                )
                click.echo(f"✅ Cleanup completed: {total_cleaned} records removed")

                if verbose:
                    for key, value in cleanup_results.items():
                        if isinstance(value, int):
                            click.echo(f"  {key}: {value}")

            await db_manager.close()
            return True

        success = asyncio.run(cleanup_db())
        if not success:
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Database cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
