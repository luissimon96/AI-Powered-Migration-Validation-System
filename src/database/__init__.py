"""Database layer for AI-Powered Migration Validation System.

This module provides:
- SQLAlchemy models and configuration
- Database session management
- Repository pattern implementation
- Connection pooling and transaction management
"""

from .config import DatabaseConfig
from .config import get_database_config
from .models import Base
from .models import DiscrepancyModel
from .models import ValidationResultModel
from .models import ValidationSessionModel
from .repositories import DiscrepancyRepository
from .repositories import ValidationResultRepository
from .repositories import ValidationSessionRepository
from .session import DatabaseManager
from .session import get_db_session

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
