# Database Layer Documentation

## Overview

The database layer provides comprehensive persistence for the AI-Powered Migration Validation System. It includes:

- **SQLAlchemy Models**: Production-ready database models with proper relationships
- **Repository Pattern**: Clean data access layer with business logic encapsulation
- **Async Support**: Full async/await compatibility with FastAPI
- **Migration Management**: Alembic-based schema versioning and migration
- **Performance Optimization**: Connection pooling, indexes, and query optimization
- **Multi-Database Support**: SQLite (development) and PostgreSQL (production)

## Architecture

### Core Components

```
src/database/
├── __init__.py          # Public API exports
├── config.py            # Database configuration and connection settings
├── models.py            # SQLAlchemy ORM models
├── session.py           # Database session management and lifecycle
├── repositories.py      # Repository pattern implementation
├── service.py           # High-level business logic service layer
├── integration.py       # Integration with existing FastAPI application
├── migrations.py        # Migration utilities and data migration helpers
└── utils.py            # Database utilities and maintenance functions
```

### Database Schema

#### Core Tables

1. **validation_sessions** - Main session tracking
   - Primary validation session data
   - Technology contexts and configuration
   - Input data references and metadata
   - Processing logs and execution tracking

2. **validation_results** - Validation outcomes
   - Fidelity scores and overall status
   - Result summaries and execution time
   - Source/target representations
   - Result type (static, behavioral, hybrid)

3. **validation_discrepancies** - Individual issues
   - Discrepancy details and severity
   - Source/target element references
   - Recommendations and confidence scores
   - Resolution tracking

4. **behavioral_test_results** - Behavioral test details
   - Test scenario execution results
   - Screenshots and interaction logs
   - Performance metrics
   - Error handling and debugging info

5. **validation_metrics** - Aggregated analytics
   - Daily/weekly/monthly metrics
   - Performance and quality trends
   - Technology usage statistics

## Configuration

### Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/migration_validator
DB_DRIVER=postgresql+asyncpg  # or sqlite+aiosqlite
DB_HOST=localhost
DB_PORT=5432
DB_NAME=migration_validator
DB_USER=validator_user
DB_PASSWORD=secure_password

# Connection Pool Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true

# Migration Settings
DB_CONNECT_RETRIES=3
DB_RETRY_INTERVAL=1.0
```

### Database URLs

```python
# SQLite (Development)
DATABASE_URL = "sqlite+aiosqlite:///./migration_validator.db"

# PostgreSQL (Production)
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/migration_validator"
```

## Usage

### Basic Setup

```python
from src.database import (
    initialize_database,
    get_db_session,
    ValidationDatabaseService
)

# Initialize database (typically in FastAPI startup)
await initialize_database()

# Use in FastAPI dependency injection
@app.get("/api/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_db_session),
    service: ValidationDatabaseService = Depends(get_validation_service)
):
    sessions, total = await service.list_validation_sessions()
    return {"sessions": sessions, "total": total}
```

### Repository Pattern

```python
from src.database.repositories import ValidationSessionRepository

async def example_repository_usage():
    async with get_db_session() as session:
        repo = ValidationSessionRepository(session)

        # Create session
        session_model = await repo.create_session(
            request_id="req_123",
            source_technology=TechnologyType.PYTHON_FLASK,
            target_technology=TechnologyType.TYPESCRIPT_REACT,
            validation_scope=ValidationScope.FULL_SYSTEM
        )

        # Query with filters
        sessions, count = await repo.list_sessions(
            limit=20,
            status="completed",
            technology_pair=(TechnologyType.PYTHON_FLASK, TechnologyType.TYPESCRIPT_REACT)
        )

        await repo.commit()
```

### Service Layer

```python
from src.database.service import ValidationDatabaseService

async def example_service_usage():
    async with get_db_session() as session:
        service = ValidationDatabaseService(session)

        # Save complete validation session
        await service.create_validation_session(validation_request)

        # Update session status
        await service.update_session_status("req_123", "processing")

        # Add log entry
        await service.add_session_log("req_123", "Analysis completed")

        # Save validation result
        await service.save_validation_result(
            "req_123",
            validation_result,
            result_type="hybrid"
        )
```

## Database Management

### CLI Tool

The `manage_db.py` script provides comprehensive database management:

```bash
# Initialize database
./manage_db.py init

# Run migrations
./manage_db.py migrate

# Check migration status
./manage_db.py migration-status

# Show statistics
./manage_db.py stats

# Clean up old data
./manage_db.py cleanup --days 30

# Optimize performance
./manage_db.py optimize

# Validate integrity
./manage_db.py validate

# Export session data
./manage_db.py export req_123 --output session_data.json

# Create backup
./manage_db.py backup --output backup.sql

# Reset database (WARNING: deletes all data)
./manage_db.py reset
```

### Programmatic Management

```python
from src.database.migrations import MigrationManager, DataMigrator
from src.database.utils import cleanup_database, get_database_statistics

# Migration management
db_manager = get_database_manager()
migration_manager = MigrationManager(db_manager)

# Check if migration needed
is_needed = await migration_manager.is_migration_needed()

# Run migrations
await migration_manager.run_migrations()

# Data cleanup
async with get_db_session() as session:
    cleanup_counts = await cleanup_database(session, days_old=30)
    stats = await get_database_statistics(session)
```

## Migrations

### Alembic Configuration

The system uses Alembic for schema migrations:

```bash
# Generate new migration
alembic revision --autogenerate -m "Add new column"

# Run migrations
alembic upgrade head

# Downgrade
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

### Migration Files

Migrations are stored in `alembic/versions/` with descriptive names:

```
alembic/versions/
├── 001_initial_migration.py
├── 002_add_behavioral_testing.py
└── 003_add_metrics_table.py
```

## Performance Optimization

### Indexes

The schema includes optimized indexes for common query patterns:

```sql
-- Session queries
CREATE INDEX ix_validation_sessions_status_created
ON validation_sessions(status, created_at);

CREATE INDEX ix_validation_sessions_technologies
ON validation_sessions(source_technology, target_technology);

-- Result queries
CREATE INDEX ix_validation_results_status_score
ON validation_results(overall_status, fidelity_score);

-- Discrepancy queries
CREATE INDEX ix_discrepancies_severity_type
ON validation_discrepancies(severity, discrepancy_type);
```

### Connection Pooling

```python
# Production configuration
DATABASE_CONFIG = {
    "pool_size": 10,           # Number of persistent connections
    "max_overflow": 20,        # Additional connections when needed
    "pool_timeout": 30,        # Timeout for getting connection
    "pool_recycle": 3600,      # Recycle connections after 1 hour
    "pool_pre_ping": True,     # Verify connections before use
}
```

### Query Optimization

```python
# Use selectinload for eager loading
from sqlalchemy.orm import selectinload

sessions = await session.execute(
    select(ValidationSessionModel)
    .options(
        selectinload(ValidationSessionModel.results),
        selectinload(ValidationSessionModel.discrepancies)
    )
    .where(ValidationSessionModel.status == "completed")
)

# Use pagination for large result sets
sessions, total = await repo.list_sessions(limit=50, offset=100)

# Use specific field selection for large tables
summary_data = await session.execute(
    select(ValidationSessionModel.id, ValidationSessionModel.status)
    .where(ValidationSessionModel.created_at >= cutoff_date)
)
```

## Integration with FastAPI

### Lifespan Management

```python
from contextlib import asynccontextmanager
from src.database.integration import database_lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database initialization
    async with database_lifespan(app):
        yield

app = FastAPI(lifespan=lifespan)
```

### Dependency Injection

```python
from fastapi import Depends
from src.database.session import get_db_session
from src.database.service import get_validation_service

@app.post("/api/validate")
async def validate_migration(
    request: ValidationRequest,
    db_service: ValidationDatabaseService = Depends(get_validation_service)
):
    # Service automatically handles database operations
    await db_service.create_validation_session(validation_request)
    return {"status": "created"}
```

### Hybrid Storage

The integration layer provides hybrid storage that uses both memory and database:

```python
from src.database.integration import get_hybrid_session_manager

# Automatic fallback between memory and database
manager = get_hybrid_session_manager()
await manager.store_session(request_id, validation_session)
session = await manager.get_session(request_id)  # Checks memory first, then DB
```

## Error Handling

### Connection Retry

```python
# Automatic retry with exponential backoff
db_manager = DatabaseManager()
result = await db_manager.execute_with_retry(
    operation=lambda: session.execute(query),
    max_retries=3
)
```

### Transaction Management

```python
# Automatic rollback on errors
async with get_db_session() as session:
    try:
        # Database operations
        session.add(new_record)
        await session.commit()  # Auto-commit on success
    except Exception:
        # Auto-rollback on exception
        raise
```

### Graceful Degradation

```python
# Fall back to memory storage if database unavailable
db_integration = get_database_integration()
if not await db_integration.is_database_available():
    db_integration.enabled = False
    # System continues with in-memory storage
```

## Monitoring and Maintenance

### Health Checks

```python
# Database health check
async def check_database_health():
    db_manager = get_database_manager()
    return await db_manager.health_check()

# Integration with FastAPI health endpoint
@app.get("/health")
async def health_check():
    db_healthy = await check_database_health()
    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "up" if db_healthy else "down"
    }
```

### Metrics Collection

```python
# Automatic metrics computation
async with get_db_session() as session:
    metrics_repo = MetricsRepository(session)

    # Compute daily metrics
    today = datetime.now().date()
    metrics = await metrics_repo.compute_daily_metrics(today)

    # Store metrics
    await metrics_repo.create_or_update_metrics(
        metric_date=today,
        metric_period="daily",
        metrics_data=metrics
    )
```

### Cleanup Automation

```python
# Scheduled cleanup task
async def scheduled_cleanup():
    async with get_db_session() as session:
        # Clean up sessions older than 30 days
        cleanup_counts = await cleanup_database(session, days_old=30)

        # Optimize database performance
        await optimize_database_performance(session)

        # Validate integrity
        integrity_result = await validate_database_integrity(session)

        if not integrity_result["is_valid"]:
            # Alert administrators about integrity issues
            logger.error("Database integrity issues found")
```

## Security Considerations

### Connection Security

- Use SSL/TLS for production database connections
- Store credentials in environment variables or secure vaults
- Use connection pooling to limit database connections
- Implement proper authentication and authorization

### Data Protection

- Sensitive data is stored in JSON fields with encryption options
- Personal information can be excluded from exports
- Audit trails track data access and modifications
- Regular backups ensure data recovery capabilities

### SQL Injection Prevention

- All queries use parameterized statements
- Input validation at service layer
- ORM-level protection through SQLAlchemy
- No dynamic SQL construction from user input

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   ```bash
   # Check database connectivity
   ./manage_db.py migration-status

   # Verify connection settings
   echo $DATABASE_URL
   ```

2. **Migration Failures**
   ```bash
   # Check current migration state
   ./manage_db.py migration-status

   # Validate schema
   ./manage_db.py validate-schema

   # Reset and re-run migrations
   alembic downgrade base
   alembic upgrade head
   ```

3. **Performance Issues**
   ```bash
   # Analyze database statistics
   ./manage_db.py stats

   # Optimize performance
   ./manage_db.py optimize

   # Check for integrity issues
   ./manage_db.py validate
   ```

4. **Data Integrity Issues**
   ```bash
   # Run integrity validation
   ./manage_db.py validate

   # Clean up orphaned records
   ./manage_db.py cleanup --days 0
   ```

### Debug Mode

Enable debug logging for detailed database operation logs:

```python
# Set in environment or configuration
DEBUG = True
LOG_LEVEL = "DEBUG"

# Database operations will log SQL queries
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
```

## Best Practices

1. **Always use the service layer** for business operations
2. **Use repository pattern** for data access
3. **Implement proper error handling** with rollbacks
4. **Use transactions** for multi-operation consistency
5. **Monitor performance** with regular statistics
6. **Regular maintenance** with cleanup and optimization
7. **Test migrations** on staging before production
8. **Backup regularly** before major changes
9. **Use connection pooling** for production deployments
10. **Implement health checks** for monitoring

## Migration from In-Memory Storage

The database layer provides seamless migration from the existing in-memory system:

```python
# Gradual migration approach
from src.database.integration import HybridSessionManager

# 1. Start with hybrid storage (memory + database)
manager = HybridSessionManager()

# 2. Migrate existing sessions
memory_sessions = {...}  # Existing in-memory sessions
migration_results = await migrate_in_memory_sessions_to_db(memory_sessions, session)

# 3. Switch to database-only mode
db_integration = get_database_integration()
db_integration.fallback_to_memory = False
```

This approach ensures zero downtime migration with fallback capabilities.