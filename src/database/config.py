"""
Database configuration management.

Handles database URL construction, connection pooling settings,
and environment-specific database configurations.
"""

import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus

from sqlalchemy import MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool, StaticPool

from ..core.config import get_settings


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    url: str
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True

    # Connection retry settings
    connect_retries: int = 3
    retry_interval: float = 1.0

    # Transaction settings
    autocommit: bool = False
    autoflush: bool = True
    expire_on_commit: bool = True

    # Migration settings
    migration_timeout: int = 300

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return self.url.startswith("sqlite")

    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL database."""
        return self.url.startswith("postgresql")

    @property
    def engine_kwargs(self) -> dict:
        """Get SQLAlchemy engine configuration."""
        kwargs = {
            "echo": self.echo,
            "pool_pre_ping": self.pool_pre_ping,
        }

        if self.is_sqlite:
            # SQLite-specific configuration
            kwargs.update(
                {
                    "poolclass": StaticPool,
                    "connect_args": {
                        "check_same_thread": False,
                        "timeout": self.pool_timeout,
                    },
                }
            )
        else:
            # PostgreSQL and other databases
            kwargs.update(
                {
                    "poolclass": QueuePool,
                    "pool_size": self.pool_size,
                    "max_overflow": self.max_overflow,
                    "pool_timeout": self.pool_timeout,
                    "pool_recycle": self.pool_recycle,
                }
            )

        return kwargs


def build_database_url(
    driver: str = "postgresql+asyncpg",
    host: str = "localhost",
    port: int = 5432,
    database: str = "migration_validator",
    username: Optional[str] = None,
    password: Optional[str] = None,
    **params,
) -> str:
    """
    Build database URL from components.

    Args:
        driver: Database driver (postgresql+asyncpg, sqlite+aiosqlite, etc.)
        host: Database host
        port: Database port
        database: Database name
        username: Database username
        password: Database password
        **params: Additional connection parameters

    Returns:
        Complete database URL
    """
    if driver.startswith("sqlite"):
        # SQLite URL format
        if database.startswith("/") or database == ":memory:":
            return f"{driver}:///{database}"
        else:
            return f"{driver}:///./{database}"

    # PostgreSQL and other databases
    auth_part = ""
    if username:
        if password:
            auth_part = f"{quote_plus(username)}:{quote_plus(password)}@"
        else:
            auth_part = f"{quote_plus(username)}@"

    url = f"{driver}://{auth_part}{host}:{port}/{database}"

    if params:
        param_string = "&".join(f"{k}={v}" for k, v in params.items())
        url += f"?{param_string}"

    return url


def get_database_config() -> DatabaseConfig:
    """
    Get database configuration from environment.

    Returns:
        DatabaseConfig instance
    """
    settings = get_settings()

    # Check for explicit database URL
    if settings.database_url:
        database_url = settings.database_url
    else:
        # Build URL from environment variables
        db_driver = os.getenv("DB_DRIVER", "sqlite+aiosqlite")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = int(os.getenv("DB_PORT", "5432"))
        db_name = os.getenv("DB_NAME", "migration_validator")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")

        if db_driver.startswith("sqlite"):
            # For development, use SQLite
            db_file = os.getenv("DB_FILE", "migration_validator.db")
            database_url = build_database_url(driver=db_driver, database=db_file)
        else:
            # For production, use PostgreSQL
            database_url = build_database_url(
                driver=db_driver,
                host=db_host,
                port=db_port,
                database=db_name,
                username=db_user,
                password=db_password,
                sslmode=os.getenv("DB_SSLMODE", "prefer"),
            )

    return DatabaseConfig(
        url=database_url,
        echo=settings.debug and settings.environment == "development",
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
        pool_pre_ping=os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
        connect_retries=int(os.getenv("DB_CONNECT_RETRIES", "3")),
        retry_interval=float(os.getenv("DB_RETRY_INTERVAL", "1.0")),
    )


# SQLAlchemy naming convention for constraints
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Metadata instance with naming convention
metadata = MetaData(naming_convention=NAMING_CONVENTION)
