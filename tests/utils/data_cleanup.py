"""
Test data cleanup utilities for automated test data management.
"""

import asyncio
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

from src.database.models import ValidationSession, User


class TestDataCleaner:
    """Automated test data cleanup utility."""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up temporary test files older than max_age_hours."""
        cleaned_count = 0
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for file_path in self.base_dir.rglob("*"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_time:
                    file_path.unlink()
                    cleaned_count += 1
        
        return cleaned_count


class DatabaseTestCleaner:
    """Database test data cleanup utility."""

    def __init__(self, db_session):
        self.db_session = db_session

    def cleanup_test_user_data(self, user_id: int) -> int:
        """Clean up all data for a test user."""
        cleaned_count = 0
        
        # Delete validation sessions
        sessions = self.db_session.query(ValidationSession).filter(
            ValidationSession.user_id == user_id
        ).all()
        
        for session in sessions:
            self.db_session.delete(session)
            cleaned_count += 1
        
        # Delete user
        user = self.db_session.query(User).filter(User.id == user_id).first()
        if user:
            self.db_session.delete(user)
            cleaned_count += 1
        
        self.db_session.commit()
        return cleaned_count


class StressTestCleaner:
    """Cleanup utility for stress testing scenarios."""

    async def async_cleanup_directories(self, directories: List[Path]) -> int:
        """Asynchronously clean up multiple directories."""
        tasks = []
        for directory in directories:
            task = asyncio.create_task(self._cleanup_single_directory(directory))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return sum(results)

    async def _cleanup_single_directory(self, directory: Path) -> int:
        """Clean up a single directory asynchronously."""
        await asyncio.sleep(0.01)  # Simulate async I/O
        
        if directory.exists():
            file_count = len(list(directory.rglob("*")))
            shutil.rmtree(directory)
            return file_count
        return 0