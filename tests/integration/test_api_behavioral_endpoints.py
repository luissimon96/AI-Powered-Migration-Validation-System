"""Integration tests for behavioral validation API endpoints.

Tests the REST API endpoints for behavioral validation functionality.
"""

from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.routes import app
from src.behavioral.crews import BehavioralValidationResult
from src.core.models import SeverityLevel
from src.core.models import ValidationDiscrepancy


@pytest.mark.integration
class TestBehavioralValidationAPIEndpoints:
    """Test behavioral validation API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def sample_behavioral_request_data(self):
        """Sample behavioral validation request data."""
        return {
            "source_url": "https://source-app.test/login",
            "target_url": "https://target-app.test/login",
            "validation_scenarios": [
                "User login with valid credentials",
                "User login with invalid email format",
                "Password reset workflow",
                "Account creation process",
            ],
            "credentials": {
                "username": "testuser@example.com",
                "password": "SecurePassword123",
            },
            "timeout": 300,
            "metadata": {
                "environment": "staging",
                "test_suite": "migration_validation",
            },
        }

    @pytest.fixture
    def mock_successful_behavioral_result(self):
        """Mock successful behavioral validation result."""
        return BehavioralValidationResult(
            overall_status="approved_with_warnings",
            fidelity_score=0.82,
            discrepancies=[
                ValidationDiscrepancy(
                    type="performance_difference",
                    severity=SeverityLevel.WARNING,
                    description="Login response time is 150ms slower in target system",
                    recommendation="Optimize login endpoint performance for better user experience",
                ),
                ValidationDiscrepancy(
                    type="ui_layout_difference",
                    severity=SeverityLevel.INFO,
                    description="Login button styling differs slightly between systems",
                    recommendation="Consider standardizing button styles for consistency",
                ),
            ],
            execution_log=[
                "Source system exploration initiated",
                "Successfully tested 4 validation scenarios",
                "Target system execution completed",
                "Performance metrics collected",
                "Behavioral comparison analysis finished",
                "Validation report generated",
            ],
            execution_time=180.5,
            timestamp=datetime.now(),
        )

    def test_start_behavioral_validation_success(
        self,
        client,
        sample_behavioral_request_data,
        mock_successful_behavioral_result,
    ):
        """Test successful behavioral validation initiation."""
        with patch(
            "src.api.routes.run_behavioral_validation_background"
        ) as mock_background_task:
            response = client.post(
                "/api/behavioral/validate", json=sample_behavioral_request_data
            )

            assert response.status_code == 200
            response_data = response.json()

            # Verify response structure
            assert "request_id" in response_data
            assert response_data["status"] == "accepted"
            assert "Behavioral validation request accepted" in response_data["message"]
            assert response_data["estimated_time"] == "300s maximum"

            # Verify request ID format
            request_id = response_data["request_id"]
            assert request_id.startswith("behavioral_")
            assert len(request_id) > 20  # Should include timestamp and hash

            # Verify background task was scheduled
            mock_background_task.assert_called_once()

    def test_start_behavioral_validation_minimal_request(self, client):
        """Test behavioral validation with minimal required fields."""
        minimal_request = {
            "source_url": "https://source.test",
            "target_url": "https://target.test",
            "validation_scenarios": ["basic_test"],
        }

        with patch("src.api.routes.run_behavioral_validation_background"):
            response = client.post("/api/behavioral/validate", json=minimal_request)

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "accepted"

    def test_start_behavioral_validation_missing_required_fields(self, client):
        """Test behavioral validation with missing required fields."""
        invalid_requests = [
            # Missing source_url
            {"target_url": "https://target.test", "validation_scenarios": ["test"]},
            # Missing target_url
            {"source_url": "https://source.test", "validation_scenarios": ["test"]},
            # Missing validation_scenarios
            {"source_url": "https://source.test", "target_url": "https://target.test"},
            # Empty validation_scenarios
            {
                "source_url": "https://source.test",
                "target_url": "https://target.test",
                "validation_scenarios": [],
            },
        ]

        for invalid_request in invalid_requests:
            response = client.post("/api/behavioral/validate", json=invalid_request)
            assert response.status_code == 422  # Validation error

    def test_get_behavioral_validation_status_pending(self, client):
        """Test getting status of pending behavioral validation."""
        request_id = "behavioral_20231215_123456_7890"

        # Mock session data
        with patch(
            "src.api.routes.behavioral_validation_sessions",
            {
                request_id: {
                    "status": "pending",
                    "progress": "Behavioral validation queued for processing",
                    "logs": ["Request received", "Queued for processing"],
                    "result": None,
                },
            },
        ):
            response = client.get(f"/api/behavioral/{request_id}/status")

            assert response.status_code == 200
            response_data = response.json()

            assert response_data["request_id"] == request_id
            assert response_data["status"] == "pending"
            assert (
                response_data["progress"]
                == "Behavioral validation queued for processing"
            )
            assert response_data["message"] == "Queued for processing"
            assert response_data["result_available"] is False

    def test_get_behavioral_validation_status_processing(self, client):
        """Test getting status of processing behavioral validation."""
        request_id = "behavioral_20231215_123456_7890"

        with patch(
            "src.api.routes.behavioral_validation_sessions",
            {
                request_id: {
                    "status": "processing",
                    "progress": "Executing behavioral validation scenarios",
                    "logs": [
                        "Request received",
                        "Behavioral validation crew initialized",
                        "Source system exploration started",
                        "Executing login scenario",
                        "Capturing user interaction patterns",
                    ],
                    "result": None,
                },
            },
        ):
            response = client.get(f"/api/behavioral/{request_id}/status")

            assert response.status_code == 200
            response_data = response.json()

            assert response_data["request_id"] == request_id
            assert response_data["status"] == "processing"
            assert (
                response_data["progress"] == "Executing behavioral validation scenarios"
            )
            assert "Capturing user interaction patterns" in response_data["message"]
            assert response_data["result_available"] is False

    def test_get_behavioral_validation_status_completed(
        self,
        client,
        mock_successful_behavioral_result,
    ):
        """Test getting status of completed behavioral validation."""
        request_id = "behavioral_20231215_123456_7890"

        with patch(
            "src.api.routes.behavioral_validation_sessions",
            {
                request_id: {
                    "status": "completed",
                    "progress": "Behavioral validation completed",
                    "logs": ["Behavioral validation completed successfully"],
                    "result": mock_successful_behavioral_result,
                },
            },
        ):
            response = client.get(f"/api/behavioral/{request_id}/status")

            assert response.status_code == 200
            response_data = response.json()

            assert response_data["request_id"] == request_id
            assert response_data["status"] == "completed"
            assert response_data["progress"] == "Behavioral validation completed"
            assert response_data["result_available"] is True

    def test_get_behavioral_validation_status_not_found(self, client):
        """Test getting status of non-existent behavioral validation."""
        request_id = "nonexistent_request_id"

        response = client.get(f"/api/behavioral/{request_id}/status")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_behavioral_validation_result_success(
        self,
        client,
        mock_successful_behavioral_result,
    ):
        """Test getting successful behavioral validation results."""
        request_id = "behavioral_20231215_123456_7890"

        with patch(
            "src.api.routes.behavioral_validation_sessions",
            {
                request_id: {
                    "status": "completed",
                    "result": mock_successful_behavioral_result,
                    "logs": ["Completed successfully"],
                },
            },
        ):
            response = client.get(f"/api/behavioral/{request_id}/result")

            assert response.status_code == 200
            response_data = response.json()

            assert response_data["request_id"] == request_id
            assert response_data["overall_status"] == "approved_with_warnings"
            assert response_data["fidelity_score"] == 0.82
            assert response_data["fidelity_percentage"] == "82.0%"
            assert response_data["execution_time"] == 180.5
            assert len(response_data["discrepancies"]) == 2

            # Verify discrepancy structure
            discrepancy = response_data["discrepancies"][0]
            assert discrepancy["type"] == "performance_difference"
            assert discrepancy["severity"] == "warning"
            assert "login response time" in discrepancy["description"].lower()
            assert discrepancy["recommendation"] is not None

    def test_get_behavioral_validation_result_still_processing(self, client):
        """Test getting results while validation is still processing."""
        request_id = "behavioral_20231215_123456_7890"

        with patch(
            "src.api.routes.behavioral_validation_sessions",
            {
                request_id: {
                    "status": "processing",
                    "result": None,
                    "logs": ["Still processing"],
                },
            },
        ):
            response = client.get(f"/api/behavioral/{request_id}/result")

            assert response.status_code == 202
            assert "still in progress" in response.json()["detail"]

    def test_get_behavioral_validation_result_error(self, client):
        """Test getting results when validation failed."""
        request_id = "behavioral_20231215_123456_7890"

        error_result = BehavioralValidationResult(
            overall_status="error",
            fidelity_score=0.0,
            discrepancies=[
                ValidationDiscrepancy(
                    type="browser_initialization_failure",
                    severity=SeverityLevel.CRITICAL,
                    description="Failed to initialize browser automation",
                    recommendation="Check browser installation and configuration",
                ),
            ],
            execution_log=["Browser initialization failed"],
            execution_time=5.0,
            timestamp=datetime.now(),
        )

        with patch(
            "src.api.routes.behavioral_validation_sessions",
            {
                request_id: {
                    "status": "error",
                    "result": error_result,
                    "logs": ["Error occurred"],
                },
            },
        ):
            response = client.get(f"/api/behavioral/{request_id}/result")

            assert response.status_code == 500
            assert "Behavioral validation failed" in response.json()["detail"]

    def test_get_behavioral_validation_result_not_found(self, client):
        """Test getting results for non-existent validation."""
        request_id = "nonexistent_request_id"

        response = client.get(f"/api/behavioral/{request_id}/result")
        assert response.status_code == 404

    def test_get_behavioral_validation_logs(self, client):
        """Test getting behavioral validation logs."""
        request_id = "behavioral_20231215_123456_7890"

        sample_logs = [
            "Behavioral validation request received and queued",
            "Behavioral validation crew initialized",
            "Starting source system exploration",
            "Source system exploration completed",
            "Starting target system execution",
            "Target system execution completed",
            "Behavioral comparison analysis completed",
            "Final validation report completed",
        ]

        with patch(
            "src.api.routes.behavioral_validation_sessions",
            {request_id: {"logs": sample_logs, "status": "completed"}},
        ):
            response = client.get(f"/api/behavioral/{request_id}/logs")

            assert response.status_code == 200
            response_data = response.json()

            assert response_data["request_id"] == request_id
            assert response_data["logs"] == sample_logs
            assert response_data["log_count"] == len(sample_logs)

    def test_get_behavioral_validation_logs_not_found(self, client):
        """Test getting logs for non-existent validation."""
        request_id = "nonexistent_request_id"

        response = client.get(f"/api/behavioral/{request_id}/logs")
        assert response.status_code == 404

    def test_delete_behavioral_validation_session(self, client):
        """Test deleting behavioral validation session."""
        request_id = "behavioral_20231215_123456_7890"

        with patch(
            "src.api.routes.behavioral_validation_sessions",
            {
                request_id: {
                    "status": "completed",
                    "result": None,
                    "logs": ["Completed"],
                },
            },
        ) as mock_sessions:
            response = client.delete(f"/api/behavioral/{request_id}")

            assert response.status_code == 200
            response_data = response.json()
            assert request_id in response_data["message"]
            assert "deleted successfully" in response_data["message"]

            # Verify session was removed from mock
            assert request_id not in mock_sessions

    def test_delete_behavioral_validation_session_not_found(self, client):
        """Test deleting non-existent behavioral validation session."""
        request_id = "nonexistent_request_id"

        response = client.delete(f"/api/behavioral/{request_id}")
        assert response.status_code == 404

    def test_list_behavioral_validation_sessions_empty(self, client):
        """Test listing behavioral validation sessions when none exist."""
        with patch("src.api.routes.behavioral_validation_sessions", {}):
            response = client.get("/api/behavioral")

            assert response.status_code == 200
            response_data = response.json()

            assert response_data["sessions"] == []
            assert response_data["total_count"] == 0

    def test_list_behavioral_validation_sessions_with_data(
        self,
        client,
        mock_successful_behavioral_result,
    ):
        """Test listing behavioral validation sessions with data."""
        sessions_data = {
            "behavioral_session_1": {
                "status": "completed",
                "created_at": datetime(2023, 12, 15, 10, 30, 0),
                "request": MagicMock(
                    source_url="https://source1.test",
                    target_url="https://target1.test",
                    validation_scenarios=["login", "signup"],
                ),
                "result": mock_successful_behavioral_result,
            },
            "behavioral_session_2": {
                "status": "processing",
                "created_at": datetime(2023, 12, 15, 11, 0, 0),
                "request": MagicMock(
                    source_url="https://source2.test",
                    target_url="https://target2.test",
                    validation_scenarios=["checkout", "payment"],
                ),
                "result": None,
            },
        }

        with patch("src.api.routes.behavioral_validation_sessions", sessions_data):
            response = client.get("/api/behavioral")

            assert response.status_code == 200
            response_data = response.json()

            assert len(response_data["sessions"]) == 2
            assert response_data["total_count"] == 2

            # Verify session data structure
            session1 = response_data["sessions"][0]
            assert session1["request_id"] == "behavioral_session_1"
            assert session1["status"] == "completed"
            assert session1["source_url"] == "https://source1.test"
            assert session1["target_url"] == "https://target1.test"
            assert session1["scenarios_count"] == 2
            assert session1["fidelity_score"] == 0.82

            session2 = response_data["sessions"][1]
            assert session2["request_id"] == "behavioral_session_2"
            assert session2["status"] == "processing"
            assert session2["fidelity_score"] is None


@pytest.mark.integration
class TestBehavioralValidationBackgroundTasks:
    """Test behavioral validation background task execution."""

    @pytest.fixture
    def mock_behavioral_crew(self):
        """Mock behavioral validation crew."""
        with patch(
            "src.api.routes.create_behavioral_validation_crew"
        ) as mock_crew_factory:
            mock_crew = AsyncMock()
            mock_crew_factory.return_value = mock_crew
            yield mock_crew

    def test_background_task_successful_execution(
        self,
        mock_behavioral_crew,
        mock_successful_behavioral_result,
    ):
        """Test successful background task execution."""
        from src.api.routes import run_behavioral_validation_background
        from src.behavioral.crews import BehavioralValidationRequest

        # Mock successful crew execution
        mock_behavioral_crew.validate_migration.return_value = (
            mock_successful_behavioral_result
        )

        request_id = "test_request_123"
        behavioral_request = BehavioralValidationRequest(
            source_url="https://source.test",
            target_url="https://target.test",
            validation_scenarios=["test_scenario"],
        )

        # Mock sessions storage
        with patch(
            "src.api.routes.behavioral_validation_sessions", {}
        ) as mock_sessions:
            # Initialize session
            mock_sessions[request_id] = {
                "request": behavioral_request,
                "status": "pending",
                "created_at": datetime.now(),
                "progress": "Queued",
                "result": None,
                "logs": ["Request queued"],
            }

            # Run background task
            import asyncio

            asyncio.run(
                run_behavioral_validation_background(request_id, behavioral_request)
            )

            # Verify session was updated
            session = mock_sessions[request_id]
            assert session["status"] == "completed"
            assert session["result"] == mock_successful_behavioral_result
            assert len(session["logs"]) > 1
            assert any("completed" in log for log in session["logs"])

    def test_background_task_error_handling(self, mock_behavioral_crew):
        """Test background task error handling."""
        from src.api.routes import run_behavioral_validation_background
        from src.behavioral.crews import BehavioralValidationRequest

        # Mock crew execution failure
        mock_behavioral_crew.validate_migration.side_effect = Exception(
            "Validation infrastructure failure",
        )

        request_id = "test_request_error"
        behavioral_request = BehavioralValidationRequest(
            source_url="https://source.test",
            target_url="https://target.test",
            validation_scenarios=["test_scenario"],
        )

        with patch(
            "src.api.routes.behavioral_validation_sessions", {}
        ) as mock_sessions:
            # Initialize session
            mock_sessions[request_id] = {
                "request": behavioral_request,
                "status": "pending",
                "created_at": datetime.now(),
                "progress": "Queued",
                "result": None,
                "logs": ["Request queued"],
            }

            # Run background task
            import asyncio

            asyncio.run(
                run_behavioral_validation_background(request_id, behavioral_request)
            )

            # Verify error handling
            session = mock_sessions[request_id]
            assert session["status"] == "error"
            assert session["result"] is not None
            assert session["result"].overall_status == "error"
            assert any("error" in log.lower() for log in session["logs"])

    def test_background_task_progress_updates(self, mock_behavioral_crew):
        """Test background task progress updates."""
        from src.api.routes import run_behavioral_validation_background
        from src.behavioral.crews import BehavioralValidationRequest

        # Mock progressive crew execution
        async def mock_validation(*args, **kwargs):
            import asyncio

            await asyncio.sleep(0.1)  # Simulate processing time
            return BehavioralValidationResult(
                overall_status="approved",
                fidelity_score=0.9,
                discrepancies=[],
                execution_log=["Task completed"],
                execution_time=0.1,
                timestamp=datetime.now(),
            )

        mock_behavioral_crew.validate_migration.side_effect = mock_validation

        request_id = "test_request_progress"
        behavioral_request = BehavioralValidationRequest(
            source_url="https://source.test",
            target_url="https://target.test",
            validation_scenarios=["test_scenario"],
        )

        with patch(
            "src.api.routes.behavioral_validation_sessions", {}
        ) as mock_sessions:
            # Initialize session
            mock_sessions[request_id] = {
                "request": behavioral_request,
                "status": "pending",
                "created_at": datetime.now(),
                "progress": "Queued",
                "result": None,
                "logs": ["Request queued"],
            }

            # Run background task
            import asyncio

            asyncio.run(
                run_behavioral_validation_background(request_id, behavioral_request)
            )

            # Verify progress updates occurred
            session = mock_sessions[request_id]
            assert session["status"] == "completed"

            # Should have multiple log entries showing progress
            logs = session["logs"]
            assert len(logs) >= 3  # Initial + progress updates + completion
            assert any("crew" in log.lower() for log in logs)
            assert any("validation" in log.lower() for log in logs)
