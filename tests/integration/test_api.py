"""
Integration tests for API endpoints.
"""

import pytest
import json
from fastapi.testclient import TestClient
from src.api.routes import app


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints."""
    
    def test_health_check(self):
        """Test health check endpoint."""
        with TestClient(app) as client:
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "services" in data
    
    def test_technology_options(self):
        """Test technology options endpoint."""
        with TestClient(app) as client:
            response = client.get("/api/technologies")
            
            assert response.status_code == 200
            data = response.json()
            assert "source_technologies" in data
            assert "target_technologies" in data
            assert "validation_scopes" in data
            assert len(data["source_technologies"]) > 0
    
    def test_capabilities_endpoint(self):
        """Test system capabilities endpoint."""
        with TestClient(app) as client:
            response = client.get("/api/capabilities")
            
            assert response.status_code == 200
            data = response.json()
            assert "technologies" in data
            assert "validation_scopes" in data
            assert "capabilities" in data
    
    def test_file_upload_source(self):
        """Test source file upload."""
        test_file_content = b"def hello(): return 'world'"
        
        with TestClient(app) as client:
            response = client.post(
                "/api/upload/source",
                files={"files": ("test.py", test_file_content, "text/python")}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "files" in data
            assert len(data["files"]) == 1
    
    def test_file_upload_target(self):
        """Test target file upload."""
        test_file_content = b"public class Test { public String hello() { return \"world\"; } }"
        
        with TestClient(app) as client:
            response = client.post(
                "/api/upload/target",
                files={"files": ("Test.java", test_file_content, "text/java")}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "files" in data
            assert len(data["files"]) == 1
    
    @pytest.mark.asyncio
    async def test_validation_workflow(self):
        """Test complete validation workflow."""
        validation_request = {
            "source_technology": "python-flask",
            "target_technology": "java-spring",
            "validation_scope": "business_logic",
            "source_tech_version": "2.0",
            "target_tech_version": "3.0"
        }
        
        test_source = b"def validate_email(email): return '@' in email"
        test_target = b"public boolean validateEmail(String email) { return email.contains(\"@\"); }"
        
        with TestClient(app) as client:
            # Start validation
            response = client.post(
                "/api/validate",
                data={"request_data": json.dumps(validation_request)},
                files={
                    "source_files": ("source.py", test_source, "text/python"),
                    "target_files": ("Target.java", test_target, "text/java")
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "request_id" in data
            assert data["status"] == "accepted"
            
            request_id = data["request_id"]
            
            # Check status
            status_response = client.get(f"/api/validate/{request_id}/status")
            assert status_response.status_code in [200, 202]  # Either completed or processing
            
            # Get logs
            logs_response = client.get(f"/api/validate/{request_id}/logs")
            assert logs_response.status_code == 200
            logs_data = logs_response.json()
            assert "logs" in logs_data
            assert len(logs_data["logs"]) > 0
    
    def test_validation_sessions_list(self):
        """Test listing validation sessions."""
        with TestClient(app) as client:
            response = client.get("/api/validate")
            
            assert response.status_code == 200
            data = response.json()
            assert "sessions" in data
            assert "total_count" in data
            assert isinstance(data["sessions"], list)
    
    def test_compatibility_check(self):
        """Test compatibility check endpoint."""
        compatibility_request = {
            "source_technology": "python-flask",
            "target_technology": "java-spring",
            "validation_scope": "full_system"
        }
        
        with TestClient(app) as client:
            response = client.post("/api/compatibility/check", json=compatibility_request)
            
            assert response.status_code == 200
            data = response.json()
            assert "compatible" in data
            assert "issues" in data
            assert "warnings" in data
            assert isinstance(data["compatible"], bool)


@pytest.mark.integration
class TestAPIErrorHandling:
    """Test API error handling."""
    
    def test_invalid_technology_validation(self):
        """Test validation with invalid technology."""
        invalid_request = {
            "source_technology": "invalid-tech",
            "target_technology": "java-spring",
            "validation_scope": "business_logic"
        }
        
        with TestClient(app) as client:
            response = client.post(
                "/api/validate",
                data={"request_data": json.dumps(invalid_request)}
            )
            
            assert response.status_code == 400
            assert "detail" in response.json()
    
    def test_missing_files_validation(self):
        """Test validation without required files."""
        valid_request = {
            "source_technology": "python-flask",
            "target_technology": "java-spring",
            "validation_scope": "business_logic"
        }
        
        with TestClient(app) as client:
            response = client.post(
                "/api/validate",
                data={"request_data": json.dumps(valid_request)}
                # No files provided
            )
            
            assert response.status_code == 400
    
    def test_nonexistent_validation_status(self):
        """Test status check for nonexistent validation."""
        with TestClient(app) as client:
            response = client.get("/api/validate/nonexistent-id/status")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    def test_invalid_json_request(self):
        """Test handling of invalid JSON in request."""
        with TestClient(app) as client:
            response = client.post(
                "/api/validate",
                data={"request_data": "invalid-json"}
            )
            
            assert response.status_code == 400
            assert "JSON" in response.json()["detail"]