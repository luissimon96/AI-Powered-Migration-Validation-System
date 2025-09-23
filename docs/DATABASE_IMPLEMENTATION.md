# Database Implementation Guide

This guide provides comprehensive information about the database layer implementation for the AI-Powered Migration Validation System.

## Overview

The system has been enhanced with a robust database layer that provides:

- **PostgreSQL & SQLite Support**: Production-ready PostgreSQL with SQLite for development
- **Session Persistence**: Replace in-memory storage with database-backed sessions
- **Audit Trail**: Soft deletes and comprehensive logging for compliance
- **Migration Management**: Alembic-based schema management
- **Performance Optimization**: Connection pooling, indexing, and query optimization
- **High Availability**: Connection retry logic and graceful degradation

## Architecture

### Core Components

```
src/database/
├── __init__.py           # Public API exports
├── config.py             # Database configuration management
├── models.py             # SQLAlchemy models with relationships
├── session.py            # Connection and session management
├── repositories.py       # Repository pattern implementation
├── service.py            # High-level business logic service
├── integration.py        # FastAPI integration layer
├── migrations.py         # Migration utilities and management
└── utils.py              # Database utilities and helpers
```

### Database Models

#### ValidationSessionModel
- **Purpose**: Core validation session storage
- **Features**: Soft deletes, audit trail, comprehensive indexing
- **Relationships**: One-to-many with results, discrepancies, behavioral tests

#### ValidationResultModel
- **Purpose**: Store validation results and fidelity scores
- **Features**: JSON representation storage, execution metrics
- **Relationships**: Belongs to session, has many discrepancies

#### DiscrepancyModel
- **Purpose**: Individual validation discrepancies
- **Features**: Severity tracking, resolution management
- **Relationships**: Belongs to session and result

#### ValidationMetricsModel
- **Purpose**: Aggregated analytics and reporting
- **Features**: Time-series data, technology breakdowns
- **Relationships**: Standalone metrics table

#### BehavioralTestResultModel
- **Purpose**: Behavioral validation test results
- **Features**: Screenshot storage, interaction logs
- **Relationships**: Belongs to session

## Setup and Configuration

### Environment Configuration

Copy the example environment file and configure for your setup:

```bash
cp .env.example .env
```

#### Development Setup (SQLite)
```env
DB_DRIVER=sqlite+aiosqlite
DB_FILE=migration_validator.db
```

#### Production Setup (PostgreSQL)
```env
DB_DRIVER=postgresql+asyncpg
DB_HOST=localhost
DB_PORT=5432
DB_NAME=migration_validator
DB_USER=migration_user
DB_PASSWORD=secure_password
DB_SSLMODE=prefer
```

#### Advanced Configuration
```env
# Connection pooling
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Retry logic
DB_CONNECT_RETRIES=3
DB_RETRY_INTERVAL=1.0
```

### Database Initialization

#### Using CLI Commands
```bash
# Initialize database and run migrations
python -m src.main db-init

# Check database health
python -m src.main health

# Clean up old records
python -m src.main db-cleanup --days-old 30
```

#### Using Management Script
```bash
# Initialize database
python scripts/database_management.py init

# Run migrations
python scripts/database_management.py migrate

# Create new migration
python scripts/database_management.py create-migration -m "Add new feature"

# Get statistics
python scripts/database_management.py stats

# Backup database
python scripts/database_management.py backup

# Clean up old data
python scripts/database_management.py cleanup --days-old 30

# Validate integrity
python scripts/database_management.py validate

# Optimize performance
python scripts/database_management.py optimize
```

### Manual Database Setup

For manual setup or debugging:

```python
from src.database.config import get_database_config
from src.database.session import DatabaseManager
from src.database.migrations import MigrationManager

# Initialize database manager
db_config = get_database_config()
db_manager = DatabaseManager(db_config)
await db_manager.initialize()

# Create tables
await db_manager.create_tables()

# Run migrations
migration_manager = MigrationManager(db_manager)
await migration_manager.run_migrations()
```

## API Integration

### FastAPI Application

The new database-backed API is available through `database_routes.py`:

```python
from src.api.database_routes import create_database_app

app = create_database_app()
```

### Key Endpoints

#### Session Management
- `POST /api/validate-migration` - Start new validation with database persistence
- `GET /api/sessions` - List sessions with filtering and pagination
- `GET /api/sessions/{request_id}` - Get session details
- `PUT /api/sessions/{request_id}/status` - Update session status
- `DELETE /api/sessions/{request_id}` - Delete session (soft delete)

#### Analytics and Reports
- `GET /api/statistics` - Get system statistics
- `GET /api/sessions/{request_id}/report` - Generate session report

#### Administration
- `POST /api/admin/cleanup` - Clean up old sessions
- `POST /api/admin/migrate-memory-sessions` - Migrate in-memory sessions

### Database Dependencies

All endpoints support database dependency injection:

```python
@app.get("/api/sessions")
async def list_sessions(
    db_service: ValidationDatabaseService = Depends(get_db_service),
    hybrid_manager: HybridSessionManager = Depends(get_hybrid_session_manager),
):
    # Use database services
    pass
```

## Session Management

### Hybrid Session Manager

The system provides a hybrid approach supporting both in-memory and database storage:

```python
from src.database.integration import HybridSessionManager

manager = HybridSessionManager()

# Store session (tries database first, falls back to memory)
await manager.store_session(request_id, validation_session)

# Get session (checks memory first, falls back to database)
session = await manager.get_session(request_id)

# List sessions from both sources
sessions = await manager.list_sessions()
```

### Migration from In-Memory

Existing in-memory sessions can be migrated:

```python
from src.database.utils import migrate_in_memory_sessions_to_db

# Migrate sessions
migration_results = await migrate_in_memory_sessions_to_db(
    memory_sessions, db_session
)
```

## Repository Pattern

### Core Repositories

#### ValidationSessionRepository
```python
from src.database.repositories import ValidationSessionRepository

repo = ValidationSessionRepository(db_session)

# Create session
session = await repo.create_session(
    request_id="req_123",
    source_technology=TechnologyType.PYTHON_FLASK,
    target_technology=TechnologyType.JAVA_SPRING,
    validation_scope=ValidationScope.FULL_SYSTEM
)

# List with filtering
sessions, total = await repo.list_sessions(
    limit=50,
    status="completed",
    technology_pair=(TechnologyType.PYTHON_FLASK, TechnologyType.JAVA_SPRING)
)
```

#### ValidationResultRepository
```python
from src.database.repositories import ValidationResultRepository

repo = ValidationResultRepository(db_session)

# Save result
result = await repo.create_result(
    session_id=session.id,
    overall_status="approved",
    fidelity_score=0.95,
    summary="Migration validation completed successfully"
)

# Get statistics
stats = await repo.get_statistics(date_from=week_ago)
```

### Service Layer

High-level business logic through the service layer:

```python
from src.database.service import ValidationDatabaseService

service = ValidationDatabaseService(db_session)

# Create session from request
session = await service.create_validation_session(validation_request)

# Save complete result
success = await service.save_validation_result(
    request_id, validation_result, result_type="hybrid"
)
```

## Soft Deletes and Audit Trail

### Soft Delete Implementation

All models support soft deletes for audit compliance:

```python
# Soft delete a session
session_model.soft_delete(
    deleted_by="admin_user",
    reason="Data retention policy"
)
await db_session.commit()

# Restore soft-deleted record
session_model.restore()
await db_session.commit()

# Query only active records
active_sessions = await db_session.execute(
    select(ValidationSessionModel).where(
        ValidationSessionModel.is_deleted == False
    )
)
```

### Audit Trail Features

- **Timestamp Tracking**: Created/updated timestamps on all records
- **Soft Deletes**: Records marked as deleted rather than removed
- **Deletion Tracking**: Who deleted and why
- **Session Logs**: Comprehensive processing logs
- **Status History**: Track session status changes

## Performance Optimization

### Connection Pooling

Configured for high-throughput scenarios:

```env
DB_POOL_SIZE=10           # Base connection pool size
DB_MAX_OVERFLOW=20        # Additional connections under load
DB_POOL_TIMEOUT=30        # Connection timeout
DB_POOL_RECYCLE=3600      # Recycle connections hourly
DB_POOL_PRE_PING=true     # Validate connections before use
```

### Indexing Strategy

Comprehensive indexing for query performance:

- **Primary Indexes**: All foreign keys and frequently queried fields
- **Composite Indexes**: Multi-column indexes for common query patterns
- **Partial Indexes**: Filtered indexes for soft delete queries
- **JSON Indexes**: PostgreSQL JSONB indexes for metadata queries

### Query Optimization

- **Eager Loading**: Use `selectinload` for related data
- **Pagination**: Limit/offset with count optimization
- **Filtering**: Indexed WHERE clauses
- **Aggregation**: Database-level aggregation for metrics

### Database Maintenance

```python
# Run optimization
from src.database.utils import optimize_database_performance

results = await optimize_database_performance(db_session)

# Validate integrity
from src.database.utils import validate_database_integrity

validation = await validate_database_integrity(db_session)

# Clean up old data
from src.database.utils import cleanup_database

cleanup_results = await cleanup_database(db_session, days_old=30)
```

## Migration Management

### Alembic Integration

Migrations are managed through Alembic:

```bash
# Create new migration
python scripts/database_management.py create-migration -m "Add new feature"

# Run migrations
python scripts/database_management.py migrate

# Check migration status
python scripts/database_management.py migrate --verbose
```

### Migration Files

Migrations are stored in `alembic/versions/`:

- `001_initial_migration.py` - Initial schema
- `002_add_soft_delete_functionality.py` - Soft delete columns

### Custom Migration Operations

```python
from src.database.migrations import MigrationManager, DataMigrator

# Check if migration needed
migration_needed = await migration_manager.is_migration_needed()

# Run data migrations
data_migrator = DataMigrator(db_manager)
success = await data_migrator.migrate_validation_sessions_v1_to_v2()
```

## Monitoring and Analytics

### Database Statistics

```python
from src.database.utils import get_database_statistics

stats = await get_database_statistics(db_session)
# Returns: session counts, success rates, fidelity scores, popular technology pairs
```

### Performance Metrics

```python
from src.database.repositories import MetricsRepository

metrics_repo = MetricsRepository(db_session)

# Compute daily metrics
daily_metrics = await metrics_repo.compute_daily_metrics(target_date)

# Get trends
metrics = await metrics_repo.get_metrics("daily", date_from, date_to)
```

### Health Monitoring

```python
from src.database.session import DatabaseManager

# Health check
db_manager = DatabaseManager()
is_healthy = await db_manager.health_check()

# Connection retry with backoff
result = await db_manager.execute_with_retry(operation, max_retries=3)
```

## Security Considerations

### Connection Security

- **SSL/TLS**: Encrypted connections for production
- **Authentication**: Database user authentication
- **Network Security**: Firewall and VPC configuration
- **Credential Management**: Environment variable configuration

### Data Protection

- **Soft Deletes**: Maintain audit trail while removing data
- **Encryption**: Database-level encryption for sensitive fields
- **Access Control**: Role-based database permissions
- **Audit Logging**: Comprehensive operation logging

### Input Validation

- **SQL Injection Prevention**: Parameterized queries only
- **Data Validation**: Pydantic model validation
- **Size Limits**: File upload and request size limits
- **Rate Limiting**: Database connection rate limiting

## Troubleshooting

### Common Issues

#### Connection Issues
```bash
# Check database connectivity
python -m src.main health

# Test database connection
python scripts/database_management.py stats
```

#### Migration Issues
```bash
# Check migration status
python scripts/database_management.py migrate --verbose

# Reset database (DESTRUCTIVE)
python scripts/database_management.py reset --confirm
```

#### Performance Issues
```bash
# Optimize database
python scripts/database_management.py optimize

# Clean up old data
python scripts/database_management.py cleanup --days-old 30
```

### Debugging

Enable debug logging in configuration:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

Use database query logging:

```env
DB_ECHO=true  # Log all SQL queries
```

### Recovery Procedures

#### Backup and Restore
```bash
# Create backup
python scripts/database_management.py backup --include-data

# Export specific session
python scripts/database_management.py export session_id --include-representations
```

#### Integrity Validation
```bash
# Validate database integrity
python scripts/database_management.py validate

# Clean up orphaned records
python scripts/database_management.py cleanup --verbose
```

## Future Enhancements

### Planned Features

1. **Read Replicas**: Support for read-only database replicas
2. **Sharding**: Horizontal partitioning for large datasets
3. **Caching**: Redis integration for frequently accessed data
4. **Event Sourcing**: Complete audit trail with event replay
5. **Multi-tenancy**: Support for multiple organizations

### Scalability Considerations

1. **Connection Pooling**: Increase pool sizes for high load
2. **Database Clustering**: PostgreSQL clustering for HA
3. **Monitoring**: Comprehensive database monitoring
4. **Backup Strategy**: Automated backup and point-in-time recovery

## Support and Maintenance

### Regular Maintenance

1. **Daily**: Health checks and monitoring
2. **Weekly**: Performance optimization and statistics review
3. **Monthly**: Cleanup old data and backup verification
4. **Quarterly**: Schema optimization and index analysis

### Monitoring Checklist

- [ ] Database connectivity
- [ ] Connection pool utilization
- [ ] Query performance
- [ ] Storage usage
- [ ] Backup completion
- [ ] Migration status

For additional support, refer to the main documentation or contact the development team.