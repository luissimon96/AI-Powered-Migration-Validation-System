"""Load testing with Locust for API endpoints."""

from locust import HttpUser, task, between
import json


class ValidationAPIUser(HttpUser):
    """User behavior for validation API load testing."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    def on_start(self):
        """Setup performed on user start."""
        # Mock authentication if needed
        self.client.headers.update({"Content-Type": "application/json"})

    @task(3)  # Weight: 3x more likely than other tasks
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        if response.status_code == 200:
            assert "status" in response.json()

    @task(2)
    def test_validation_simple(self):
        """Test simple validation request."""
        payload = {
            "source_files": ["test_file_1.py"],
            "target_framework": "fastapi",
            "validation_type": "syntax",
        }

        response = self.client.post("/api/validate", json=payload)
        if response.status_code in [200, 202]:  # Accept both sync/async responses
            result = response.json()
            assert "validation_id" in result or "results" in result

    @task(1)
    def test_validation_complex(self):
        """Test complex validation request."""
        payload = {
            "source_files": [
                "models.py",
                "views.py",
                "urls.py",
                "settings.py"
            ],
            "target_framework": "fastapi",
            "validation_type": "comprehensive",
            "options": {
                "check_dependencies": True,
                "analyze_performance": True,
                "validate_security": True,
            },
        }

        with self.client.post("/api/validate", json=payload, catch_response=True) as response:
            if response.status_code in [200, 202]:
                response.success()
                result = response.json()
                assert "validation_id" in result or "results" in result
            elif response.status_code == 429:  # Rate limit
                response.success()  # Don't fail on rate limits during load test
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(1)
    def test_get_validation_status(self):
        """Test getting validation status."""
        # Use a mock validation ID
        validation_id = "test-validation-123"
        response = self.client.get(f"/api/validate/{validation_id}/status")

        # Accept 404 (validation not found) as valid during load testing
        if response.status_code in [200, 404]:
            pass
        else:
            assert False, f"Unexpected status code: {response.status_code}"

    @task(1)
    def test_list_validations(self):
        """Test listing recent validations."""
        response = self.client.get("/api/validations?limit=10")
        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, (list, dict))


class AdminUser(HttpUser):
    """Administrative user behavior for system monitoring."""

    wait_time = between(5, 10)  # Longer wait time for admin operations

    @task
    def test_system_stats(self):
        """Test system statistics endpoint."""
        response = self.client.get("/api/admin/stats")
        if response.status_code == 200:
            stats = response.json()
            assert "total_validations" in stats or "error" in stats

    @task
    def test_health_detailed(self):
        """Test detailed health check."""
        response = self.client.get("/health/detailed")
        if response.status_code == 200:
            health = response.json()
            assert "database" in health or "status" in health