"""Test data management and cleanup automation for T002 completion.
Automated test data lifecycle management.
"""

import asyncio
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from src.core.models import ValidationRequest, ValidationScope
from src.database.models import User, ValidationSession


@pytest.mark.integration
class TestDataManagement:
    """Test data management and cleanup automation."""

    @pytest.fixture(autouse=True)
    def setup_test_data_directory(self):
        """Setup temporary test data directory."""
        self.test_data_dir = Path(tempfile.mkdtemp(prefix="test_data_"))
        yield
        # Cleanup after test
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)

    def test_automated_file_cleanup(self):
        """Test automated cleanup of temporary test files."""
        # Create test files
        test_files = []
        for i in range(5):
            test_file = self.test_data_dir / f"test_file_{i}.py"
            test_file.write_text(f"# Test file {i}\ndef test_{i}(): pass")
            test_files.append(test_file)

        # Verify files created
        assert len(list(self.test_data_dir.iterdir())) == 5

        # Test cleanup mechanism
        from tests.utils.data_cleanup import TestDataCleaner

        cleaner = TestDataCleaner(self.test_data_dir)
        cleaned_count = cleaner.cleanup_temp_files()

        assert cleaned_count == 5
        assert len(list(self.test_data_dir.iterdir())) == 0

    async def test_database_test_data_lifecycle(self, db_session):
        """Test database test data lifecycle management."""
        # Create test user
        test_user = User(
            username="test_user_cleanup",
            email="cleanup@test.com",
            password_hash="test_hash",
        )
        db_session.add(test_user)
        db_session.commit()

        # Create test sessions
        test_sessions = []
        for i in range(3):
            session = ValidationSession(
                user_id=test_user.id,
                request_data={"test_cleanup": True, "index": i},
                status="completed" if i % 2 == 0 else "failed",
                created_at=datetime.utcnow() - timedelta(minutes=i),
            )
            db_session.add(session)
            test_sessions.append(session)

        db_session.commit()

        # Verify sessions created
        created_sessions = (
            db_session.query(ValidationSession)
            .filter(
                ValidationSession.user_id == test_user.id,
            )
            .all()
        )
        assert len(created_sessions) == 3

        # Test cleanup
        from tests.utils.data_cleanup import DatabaseTestCleaner

        cleaner = DatabaseTestCleaner(db_session)

        # Cleanup test user and related data
        cleanup_count = cleaner.cleanup_test_user_data(test_user.id)
        assert cleanup_count >= 3  # User + 3 sessions

        # Verify cleanup
        remaining_sessions = (
            db_session.query(ValidationSession)
            .filter(
                ValidationSession.user_id == test_user.id,
            )
            .all()
        )
        assert len(remaining_sessions) == 0

    def test_mock_data_generation(self):
        """Test generation of consistent mock test data."""
        from tests.utils.mock_generators import ValidationDataGenerator

        generator = ValidationDataGenerator()

        # Generate mock validation requests
        mock_requests = generator.generate_validation_requests(count=5)
        assert len(mock_requests) == 5

        for request in mock_requests:
            assert isinstance(request, ValidationRequest)
            assert request.source_technology in generator.SUPPORTED_TECHNOLOGIES
            assert request.target_technology in generator.SUPPORTED_TECHNOLOGIES
            assert request.validation_scope in ValidationScope
            assert len(request.source_files) > 0
            assert len(request.target_files) > 0

    def test_test_fixture_data_consistency(self):
        """Test consistency of test fixture data across runs."""
        from tests.fixtures.sample_data import SampleDataProvider

        provider = SampleDataProvider()

        # Generate same data multiple times
        data_sets = []
        for _ in range(3):
            data_set = provider.get_python_to_java_sample()
            data_sets.append(data_set)

        # Verify consistency
        first_set = data_sets[0]
        for data_set in data_sets[1:]:
            assert data_set["source_files"] == first_set["source_files"]
            assert data_set["target_files"] == first_set["target_files"]
            assert data_set["expected_result"] == first_set["expected_result"]

    async def test_concurrent_test_data_access(self):
        """Test concurrent access to test data resources."""
        from tests.utils.mock_generators import ValidationDataGenerator

        generator = ValidationDataGenerator()

        # Simulate concurrent data generation
        async def generate_data():
            return generator.generate_validation_requests(count=2)

        tasks = [generate_data() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # Verify all tasks completed successfully
        assert len(results) == 5
        for result in results:
            assert len(result) == 2
            assert all(isinstance(req, ValidationRequest) for req in result)

    def test_memory_efficient_large_dataset_handling(self):
        """Test memory-efficient handling of large test datasets."""
        from tests.utils.mock_generators import LargeDatasetGenerator

        generator = LargeDatasetGenerator()

        # Generate large dataset with streaming
        large_dataset = generator.generate_streaming_dataset(
            file_count=100,
            chunk_size=10,
        )

        processed_count = 0
        for chunk in large_dataset:
            assert len(chunk) <= 10
            processed_count += len(chunk)

        assert processed_count == 100

    def test_test_environment_isolation(self):
        """Test isolation between different test environments."""
        from tests.utils.environment_manager import TestEnvironmentManager

        manager = TestEnvironmentManager()

        # Create isolated environments
        env1 = manager.create_isolated_environment("integration_test_1")
        env2 = manager.create_isolated_environment("integration_test_2")

        # Verify isolation
        assert env1.temp_dir != env2.temp_dir
        assert env1.db_url != env2.db_url
        assert env1.cache_prefix != env2.cache_prefix

        # Cleanup environments
        manager.cleanup_environment(env1)
        manager.cleanup_environment(env2)

    async def test_async_test_data_preparation(self):
        """Test asynchronous test data preparation."""
        from tests.utils.async_data_prep import AsyncTestDataPreparator

        preparator = AsyncTestDataPreparator()

        # Prepare test data asynchronously
        tasks = [
            preparator.prepare_code_samples("python", 5),
            preparator.prepare_code_samples("java", 5),
            preparator.prepare_screenshots(3),
        ]

        python_samples, java_samples, screenshots = await asyncio.gather(*tasks)

        assert len(python_samples) == 5
        assert len(java_samples) == 5
        assert len(screenshots) == 3

        # Verify content quality
        for sample in python_samples:
            assert sample["language"] == "python"
            assert "content" in sample
            assert len(sample["content"]) > 0

    def test_test_data_versioning(self):
        """Test versioning of test data for reproducible tests."""
        from tests.utils.data_versioning import TestDataVersionManager

        manager = TestDataVersionManager()

        # Create versioned test data
        v1_data = manager.get_test_data_version("sample_migration", "1.0")
        v2_data = manager.get_test_data_version("sample_migration", "2.0")

        # Verify version differences
        assert v1_data["version"] == "1.0"
        assert v2_data["version"] == "2.0"
        assert v1_data["data"] != v2_data["data"]

        # Verify reproducibility
        v1_data_again = manager.get_test_data_version("sample_migration", "1.0")
        assert v1_data == v1_data_again


@pytest.mark.integration
class TestPerformanceDataScenarios:
    """Test performance with different data scenarios."""

    def test_small_dataset_performance(self):
        """Test performance with small datasets."""
        from tests.utils.performance_tester import DatasetPerformanceTester

        tester = DatasetPerformanceTester()

        # Test with small dataset (1-5 files)
        metrics = tester.test_validation_performance(
            file_count=3,
            avg_file_size=1024,  # 1KB
        )

        assert metrics["processing_time"] < 5.0  # < 5 seconds
        assert metrics["memory_usage"] < 50  # < 50MB
        assert metrics["success_rate"] >= 0.95

    def test_medium_dataset_performance(self):
        """Test performance with medium datasets."""
        from tests.utils.performance_tester import DatasetPerformanceTester

        tester = DatasetPerformanceTester()

        # Test with medium dataset (20-50 files)
        metrics = tester.test_validation_performance(
            file_count=30,
            avg_file_size=10240,  # 10KB
        )

        assert metrics["processing_time"] < 30.0  # < 30 seconds
        assert metrics["memory_usage"] < 200  # < 200MB
        assert metrics["success_rate"] >= 0.90

    def test_large_dataset_performance(self):
        """Test performance with large datasets."""
        from tests.utils.performance_tester import DatasetPerformanceTester

        tester = DatasetPerformanceTester()

        # Test with large dataset (100+ files)
        metrics = tester.test_validation_performance(
            file_count=100,
            avg_file_size=51200,  # 50KB
        )

        assert metrics["processing_time"] < 120.0  # < 2 minutes
        assert metrics["memory_usage"] < 500  # < 500MB
        assert metrics["success_rate"] >= 0.85

    async def test_stress_test_data_cleanup(self):
        """Test cleanup under stress conditions."""
        from tests.utils.data_cleanup import StressTestCleaner

        cleaner = StressTestCleaner()

        # Generate stress test scenario
        temp_dirs = []
        for i in range(20):
            temp_dir = Path(tempfile.mkdtemp(prefix=f"stress_test_{i}_"))

            # Create many files in each directory
            for j in range(50):
                test_file = temp_dir / f"file_{j}.py"
                test_file.write_text(f"# Stress test file {i}_{j}")

            temp_dirs.append(temp_dir)

        # Test cleanup performance
        start_time = datetime.utcnow()
        cleanup_count = await cleaner.async_cleanup_directories(temp_dirs)
        end_time = datetime.utcnow()

        duration = (end_time - start_time).total_seconds()

        assert cleanup_count == 20 * 50  # 20 dirs * 50 files
        assert duration < 10.0  # Should complete in under 10 seconds

        # Verify all directories cleaned
        for temp_dir in temp_dirs:
            assert not temp_dir.exists()
