"""
End-to-end system tests for the complete AI Migration Validation pipeline.

Tests the entire workflow from API request to final unified report generation.
"""

import asyncio
import json
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.routes import app
from src.behavioral.crews import BehavioralValidationResult
from src.core.models import (SeverityLevel, ValidationDiscrepancy,
                             ValidationResult)


@pytest.mark.system
@pytest.mark.slow
class TestEndToEndValidationPipeline:
    """Test complete end-to-end validation pipeline scenarios."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def sample_code_files(self):
        """Create sample code files for testing."""
        # Create temporary files
        temp_dir = tempfile.mkdtemp()

        source_file = f"{temp_dir}/source.py"
        with open(source_file, "w") as f:
            f.write(
                """
def authenticate_user(username, password):
    if not username or not password:
        raise ValueError("Username and password required")

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    # Simulate authentication logic
    if username == "admin" and password == "password123":
        return {"user_id": 1, "username": username, "role": "admin"}

    return None

class UserManager:
    def __init__(self):
        self.users = {}

    def create_user(self, username, password, email):
        if username in self.users:
            raise ValueError("User already exists")

        auth_result = authenticate_user(username, password)
        if not auth_result:
            raise ValueError("Invalid credentials")

        self.users[username] = {
            "password": password,
            "email": email,
            "created_at": "2023-12-15"
        }
        return {"success": True, "user_id": len(self.users)}
"""
            )

        target_file = f"{temp_dir}/target.java"
        with open(target_file, "w") as f:
            f.write(
                """
public class AuthenticationService {
    public static AuthResult authenticateUser(String username, String password) {
        if (username == null || password == null || username.isEmpty() || password.isEmpty()) {
            throw new IllegalArgumentException("Username and password required");
        }

        if (password.length() < 8) {
            throw new IllegalArgumentException("Password must be at least 8 characters");
        }

        // Simulate authentication logic
        if ("admin".equals(username) && "password123".equals(password)) {
            return new AuthResult(1, username, "admin");
        }

        return null;
    }
}

public class UserManager {
    private Map<String, User> users = new HashMap<>();

    public CreateUserResult createUser(String username, String password, String email) {
        if (users.containsKey(username)) {
            throw new IllegalArgumentException("User already exists");
        }

        AuthResult authResult = AuthenticationService.authenticateUser(username, password);
        if (authResult == null) {
            throw new IllegalArgumentException("Invalid credentials");
        }

        User user = new User(password, email, "2023-12-15");
        users.put(username, user);
        return new CreateUserResult(true, users.size());
    }
}
"""
            )

        return {
            "temp_dir": temp_dir,
            "source_file": source_file,
            "target_file": target_file,
        }

    def test_health_check_endpoints(self, client):
        """Test system health check endpoints."""
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        assert "AI-Powered Migration Validation System" in response.json()["message"]

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_technology_options_endpoint(self, client):
        """Test technology options endpoint."""
        response = client.get("/api/technologies")
        assert response.status_code == 200

        data = response.json()
        assert "source_technologies" in data
        assert "target_technologies" in data
        assert "validation_scopes" in data
        assert "input_types" in data

        # Verify we have some technologies available
        assert len(data["source_technologies"]) > 0
        assert len(data["target_technologies"]) > 0

    def test_compatibility_check_endpoint(self, client):
        """Test compatibility check endpoint."""
        request_data = {
            "source_technology": "python_flask",
            "target_technology": "java_spring",
            "validation_scope": "business_logic",
        }

        response = client.post("/api/compatibility/check", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert "compatible" in data
        assert "issues" in data
        assert "warnings" in data

    @patch("src.core.migration_validator.MigrationValidator.validate_migration")
    def test_static_validation_pipeline_e2e(
        self, mock_validate, client, sample_code_files
    ):
        """Test complete static validation pipeline end-to-end."""
        # Mock static validation result
        mock_result = ValidationResult(
            overall_status="approved_with_warnings",
            fidelity_score=0.88,
            summary="Static validation completed with minor differences in error handling",
            discrepancies=[
                ValidationDiscrepancy(
                    type="exception_handling_difference",
                    severity=SeverityLevel.WARNING,
                    description="Source uses ValueError while target uses IllegalArgumentException",
                    recommendation="Consider standardizing exception types for consistency",
                ),
                ValidationDiscrepancy(
                    type="return_value_structure",
                    severity=SeverityLevel.INFO,
                    description="Return value structures differ slightly between implementations",
                    recommendation="Document return value differences for maintenance",
                ),
            ],
            execution_time=42.5,
            timestamp=datetime.now(),
        )

        mock_session = MagicMock()
        mock_session.result = mock_result
        mock_validate.return_value = mock_session

        # Prepare file upload
        with open(sample_code_files["source_file"], "rb") as source_f, open(
            sample_code_files["target_file"], "rb"
        ) as target_f:
            files = [
                ("source_files", ("source.py", source_f, "text/plain")),
                ("target_files", ("target.java", target_f, "text/plain")),
            ]

            form_data = {
                "request_data": json.dumps(
                    {
                        "source_technology": "python_flask",
                        "target_technology": "java_spring",
                        "validation_scope": "business_logic",
                        "metadata": {"test_run": True},
                    }
                )
            }

            # Submit validation request
            response = client.post("/api/validate", data=form_data, files=files)
            assert response.status_code == 200

            request_id = response.json()["request_id"]
            assert request_id is not None

            # Check validation status
            status_response = client.get(f"/api/validate/{request_id}/status")
            assert status_response.status_code == 200

            # Get validation results
            result_response = client.get(f"/api/validate/{request_id}/result")
            assert result_response.status_code == 200

            result_data = result_response.json()
            assert result_data["overall_status"] == "approved_with_warnings"
            assert result_data["fidelity_score"] == 0.88
            assert result_data["fidelity_percentage"] == "88.0%"
            assert result_data["discrepancy_counts"]["warning"] == 1
            assert result_data["discrepancy_counts"]["info"] == 1

            # Get detailed report
            report_response = client.get(
                f"/api/validate/{request_id}/report?format=json"
            )
            assert report_response.status_code == 200

            # Clean up
            cleanup_response = client.delete(f"/api/validate/{request_id}")
            assert cleanup_response.status_code == 200

    @patch("src.api.routes.run_behavioral_validation_background")
    def test_behavioral_validation_pipeline_e2e(self, mock_background_task, client):
        """Test complete behavioral validation pipeline end-to-end."""
        # Test behavioral validation request
        request_data = {
            "source_url": "https://legacy-app.example.com/login",
            "target_url": "https://new-app.example.com/login",
            "validation_scenarios": [
                "User login with valid credentials",
                "User login with invalid email",
                "Password reset flow",
                "Account registration process",
            ],
            "credentials": {
                "username": "test.user@example.com",
                "password": "TestPassword123",
            },
            "timeout": 300,
            "metadata": {"environment": "staging", "browser": "chromium"},
        }

        # Submit behavioral validation request
        response = client.post("/api/behavioral/validate", json=request_data)
        assert response.status_code == 200

        response_data = response.json()
        request_id = response_data["request_id"]
        assert request_id.startswith("behavioral_")
        assert response_data["status"] == "accepted"

        # Verify background task was scheduled
        mock_background_task.assert_called_once()

        # Mock behavioral validation session with completed result
        behavioral_result = BehavioralValidationResult(
            overall_status="approved_with_warnings",
            fidelity_score=0.75,
            discrepancies=[
                ValidationDiscrepancy(
                    type="response_time_degradation",
                    severity=SeverityLevel.WARNING,
                    description="Target system login is 400ms slower than source system",
                    recommendation="Optimize login endpoint performance to match source system",
                ),
                ValidationDiscrepancy(
                    type="error_message_inconsistency",
                    severity=SeverityLevel.INFO,
                    description="Invalid login error messages differ between systems",
                    recommendation="Standardize error messages for user consistency",
                ),
            ],
            execution_log=[
                "Source system exploration started",
                "Tested 4 validation scenarios successfully",
                "Target system execution completed",
                "Performance comparison analysis completed",
                "Behavioral validation report generated",
            ],
            execution_time=245.8,
            timestamp=datetime.now(),
        )

        with patch(
            "src.api.routes.behavioral_validation_sessions",
            {
                request_id: {
                    "status": "completed",
                    "progress": "Behavioral validation completed",
                    "result": behavioral_result,
                    "logs": behavioral_result.execution_log,
                }
            },
        ):
            # Check validation status
            status_response = client.get(f"/api/behavioral/{request_id}/status")
            assert status_response.status_code == 200
            assert status_response.json()["status"] == "completed"

            # Get validation results
            result_response = client.get(f"/api/behavioral/{request_id}/result")
            assert result_response.status_code == 200

            result_data = result_response.json()
            assert result_data["overall_status"] == "approved_with_warnings"
            assert result_data["fidelity_score"] == 0.75
            assert result_data["fidelity_percentage"] == "75.0%"
            assert len(result_data["discrepancies"]) == 2

            # Verify discrepancy details
            performance_discrepancy = next(
                d
                for d in result_data["discrepancies"]
                if d["type"] == "response_time_degradation"
            )
            assert performance_discrepancy["severity"] == "warning"
            assert "400ms slower" in performance_discrepancy["description"]

            # Get validation logs
            logs_response = client.get(f"/api/behavioral/{request_id}/logs")
            assert logs_response.status_code == 200
            assert len(logs_response.json()["logs"]) == 5

            # Clean up
            cleanup_response = client.delete(f"/api/behavioral/{request_id}")
            assert cleanup_response.status_code == 200

    @patch("src.api.routes.run_hybrid_validation_background")
    def test_hybrid_validation_pipeline_e2e(
        self, mock_background_task, client, sample_code_files
    ):
        """Test complete hybrid validation pipeline end-to-end."""
        # Prepare hybrid validation request
        with open(sample_code_files["source_file"], "rb") as source_f, open(
            sample_code_files["target_file"], "rb"
        ) as target_f:
            files = [
                ("source_files", ("source.py", source_f, "text/plain")),
                ("target_files", ("target.java", target_f, "text/plain")),
            ]

            form_data = {
                "request_data": json.dumps(
                    {
                        "source_technology": "python_flask",
                        "target_technology": "java_spring",
                        "validation_scope": "full_system",
                        "source_url": "https://legacy-app.example.com",
                        "target_url": "https://new-app.example.com",
                        "validation_scenarios": [
                            "User authentication flow",
                            "User registration process",
                        ],
                        "credentials": {
                            "username": "test.user@example.com",
                            "password": "TestPassword123",
                        },
                        "behavioral_timeout": 240,
                        "metadata": {
                            "hybrid_validation": True,
                            "environment": "staging",
                        },
                    }
                )
            }

            # Submit hybrid validation request
            response = client.post("/api/validate/hybrid", data=form_data, files=files)
            assert response.status_code == 200

            response_data = response.json()
            request_id = response_data["request_id"]
            assert request_id.startswith("hybrid_")
            assert response_data["status"] == "accepted"
            assert response_data["validation_types"]["static_analysis"] is True
            assert response_data["validation_types"]["behavioral_testing"] is True

            # Verify background task was scheduled
            mock_background_task.assert_called_once()

            # Mock hybrid validation session with completed result
            hybrid_result = ValidationResult(
                overall_status="approved_with_warnings",
                fidelity_score=0.82,  # Combined score
                summary="Hybrid validation completed. Static fidelity: 0.88, Behavioral fidelity: 0.75, Combined: 0.82",
                discrepancies=[
                    # Static discrepancies
                    ValidationDiscrepancy(
                        type="static_exception_handling_difference",
                        severity=SeverityLevel.WARNING,
                        description="[Static Analysis] Source uses ValueError while target uses IllegalArgumentException",
                        recommendation="Consider standardizing exception types for consistency",
                    ),
                    # Behavioral discrepancies
                    ValidationDiscrepancy(
                        type="behavioral_response_time_degradation",
                        severity=SeverityLevel.WARNING,
                        description="[Behavioral Testing] Target system login is 400ms slower than source system",
                        recommendation="Optimize login endpoint performance to match source system",
                    ),
                    ValidationDiscrepancy(
                        type="behavioral_error_message_inconsistency",
                        severity=SeverityLevel.INFO,
                        description="[Behavioral Testing] Invalid login error messages differ between systems",
                        recommendation="Standardize error messages for user consistency",
                    ),
                ],
                execution_time=288.3,  # Combined execution time
                timestamp=datetime.now(),
            )

            with patch(
                "src.api.routes.validation_sessions",
                {
                    request_id: MagicMock(
                        result=hybrid_result,
                        processing_log=[
                            "Hybrid validation started - Static: True, Behavioral: True",
                            "Static validation completed with fidelity score: 0.88",
                            "Behavioral validation completed with fidelity score: 0.75",
                            "Combining static and behavioral validation results",
                            "Hybrid validation completed successfully",
                        ],
                    )
                },
            ):
                # Check validation status
                status_response = client.get(f"/api/validate/{request_id}/status")
                assert status_response.status_code == 200
                assert status_response.json()["status"] == "completed"

                # Get validation results
                result_response = client.get(f"/api/validate/{request_id}/result")
                assert result_response.status_code == 200

                result_data = result_response.json()
                assert result_data["overall_status"] == "approved_with_warnings"
                assert result_data["fidelity_score"] == 0.82
                assert result_data["fidelity_percentage"] == "82.0%"
                assert result_data["discrepancy_counts"]["warning"] == 2
                assert result_data["discrepancy_counts"]["info"] == 1

                # Verify hybrid summary
                assert "Static fidelity: 0.88" in result_data["summary"]
                assert "Behavioral fidelity: 0.75" in result_data["summary"]
                assert "Combined: 0.82" in result_data["summary"]

                # Get detailed report in different formats
                json_report_response = client.get(
                    f"/api/validate/{request_id}/report?format=json"
                )
                assert json_report_response.status_code == 200

                html_report_response = client.get(
                    f"/api/validate/{request_id}/report?format=html"
                )
                assert html_report_response.status_code == 200
                assert "text/html" in html_report_response.headers["content-type"]

                markdown_report_response = client.get(
                    f"/api/validate/{request_id}/report?format=markdown"
                )
                assert markdown_report_response.status_code == 200

                # Get processing logs
                logs_response = client.get(f"/api/validate/{request_id}/logs")
                assert logs_response.status_code == 200
                logs_data = logs_response.json()
                assert len(logs_data["logs"]) == 5
                assert any(
                    "Hybrid validation started" in log for log in logs_data["logs"]
                )

    def test_validation_session_lifecycle_management(self, client):
        """Test validation session lifecycle management."""
        # List sessions when empty
        response = client.get("/api/validate")
        assert response.status_code == 200
        assert response.json()["total_count"] == 0

        # List behavioral sessions when empty
        response = client.get("/api/behavioral")
        assert response.status_code == 200
        assert response.json()["total_count"] == 0

        # Test getting non-existent session status
        response = client.get("/api/validate/nonexistent/status")
        assert response.status_code == 404

        response = client.get("/api/behavioral/nonexistent/status")
        assert response.status_code == 404

        # Test getting non-existent session results
        response = client.get("/api/validate/nonexistent/result")
        assert response.status_code == 404

        response = client.get("/api/behavioral/nonexistent/result")
        assert response.status_code == 404

        # Test deleting non-existent session
        response = client.delete("/api/validate/nonexistent")
        assert response.status_code == 404

        response = client.delete("/api/behavioral/nonexistent")
        assert response.status_code == 404

    def test_error_handling_and_recovery(self, client):
        """Test system error handling and recovery."""
        # Test invalid JSON in validation request
        response = client.post(
            "/api/validate", data={"request_data": "invalid json"}, files=[]
        )
        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["detail"]

        # Test invalid JSON in behavioral validation
        response = client.post(
            "/api/behavioral/validate", json="invalid json structure"
        )
        assert response.status_code == 422  # Validation error

        # Test invalid JSON in hybrid validation
        response = client.post(
            "/api/validate/hybrid", data={"request_data": "invalid json"}, files=[]
        )
        assert response.status_code == 400

        # Test invalid compatibility check request
        response = client.post("/api/compatibility/check", json={"invalid": "request"})
        assert response.status_code == 422

    @pytest.mark.performance
    def test_system_performance_characteristics(self, client):
        """Test system performance characteristics."""
        import time

        # Test health endpoint response time
        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 1.0, f"Health check too slow: {response_time:.3f}s"

        # Test technology options endpoint response time
        start_time = time.time()
        response = client.get("/api/technologies")
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 2.0, f"Technology options too slow: {response_time:.3f}s"

        # Test compatibility check response time
        start_time = time.time()
        response = client.post(
            "/api/compatibility/check",
            json={
                "source_technology": "python_flask",
                "target_technology": "java_spring",
                "validation_scope": "business_logic",
            },
        )
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time
        assert (
            response_time < 3.0
        ), f"Compatibility check too slow: {response_time:.3f}s"

    def test_api_documentation_availability(self, client):
        """Test API documentation is available."""
        # Test OpenAPI docs
        response = client.get("/docs")
        assert response.status_code == 200

        # Test ReDoc docs
        response = client.get("/redoc")
        assert response.status_code == 200

        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

        # Verify key endpoints are documented
        paths = schema["paths"]
        expected_paths = [
            "/api/validate",
            "/api/behavioral/validate",
            "/api/validate/hybrid",
            "/api/technologies",
            "/health",
        ]

        for path in expected_paths:
            assert any(
                path in documented_path for documented_path in paths.keys()
            ), f"Missing documentation for {path}"

    def test_cors_headers(self, client):
        """Test CORS headers are properly configured."""
        # Test preflight request
        response = client.options("/api/technologies")

        # Note: TestClient may not fully simulate CORS, but we can check the app configuration
        # In a real test with a browser, we would verify CORS headers
        assert response.status_code in [200, 405]  # TestClient behavior varies

    def test_concurrent_request_handling(self, client):
        """Test system can handle concurrent requests."""
        import threading
        import time

        results = []

        def make_request():
            response = client.get("/health")
            results.append(response.status_code)

        # Create multiple concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()
        end_time = time.time()

        # Verify all requests succeeded
        assert len(results) == 10
        assert all(status == 200 for status in results)

        # Should complete within reasonable time
        total_time = end_time - start_time
        assert total_time < 5.0, f"Concurrent requests took too long: {total_time:.3f}s"
