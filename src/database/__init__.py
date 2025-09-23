"""
Database layer for AI-Powered Migration Validation System.

This module provides:
- SQLAlchemy models and configuration
- Database session management
- Repository pattern implementation
- Connection pooling and transaction management
"""

from .config import DatabaseConfig, get_database_config
from .models import Base, ValidationSessionModel, ValidationResultModel, DiscrepancyModel
from .session import DatabaseManager, get_db_session
from .repositories import (
    ValidationSessionRepository,
    ValidationResultRepository,
    DiscrepancyRepository,
)

__all__ = [
    "DatabaseConfig",
    "get_database_config",
    "Base",
    "ValidationSessionModel",
    "ValidationResultModel",
    "DiscrepancyModel",
    "DatabaseManager",
    "get_db_session",
    "ValidationSessionRepository",
    "ValidationResultRepository",
    "DiscrepancyRepository",
]
