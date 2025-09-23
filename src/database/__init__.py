"""Database layer for AI-Powered Migration Validation System.

This module provides:
- SQLAlchemy models and configuration
- Database session management
- Repository pattern implementation
- Connection pooling and transaction management
"""

from .config import DatabaseConfig, get_database_config
from .models import (Base, DiscrepancyModel, ValidationResultModel,
                     ValidationSessionModel)
from .repositories import (DiscrepancyRepository, ValidationResultRepository,
                           ValidationSessionRepository)
from .session import DatabaseManager, get_db_session

__all__ = [
    "Base",
    "DatabaseConfig",
    "DatabaseManager",
    "DiscrepancyModel",
    "DiscrepancyRepository",
    "ValidationResultModel",
    "ValidationResultRepository",
    "ValidationSessionModel",
    "ValidationSessionRepository",
    "get_database_config",
    "get_db_session",
]
