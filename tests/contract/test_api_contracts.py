"""Contract testing for AI-Powered Migration Validation System API endpoints.

This module implements contract testing to ensure API compatibility across versions
and validate request/response schemas against OpenAPI specifications.
"""

from typing import Any, Dict
from unittest.mock import patch

import jsonschema
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft7Validator

from src.api.routes import app
from src.core.models import (InputType, TechnologyType, ValidationResult,
                             ValidationScope, ValidationStatus)

# ═══════════════════════════════════════════════════════════════
# Contract Testing Framework
# ═══════════════════════════════════════════════════════════════


class APIContractTester:
    """Contract testing framework for API endpoints."""

    def __init__(self, client: TestClient):
        self.client = client

    def validate_response_schema(
        self, response: Dict[str, Any], expected_schema: Dict[str, Any],
    ) -> None:
        """Validate response against expected JSON schema."""
        try:
            jsonschema.validate(instance=response, schema=expected_schema)
        except jsonschema.exceptions.ValidationError as e:
            pytest.fail(f"Response schema validation failed: {e.message}")

    def validate_request_schema(
        self, request_data: Dict[str, Any], expected_schema: Dict[str, Any],
    ) -> None:
        """Validate request against expected JSON schema."""
        try:
            jsonschema.validate(instance=request_data, schema=expected_schema)
        except jsonschema.exceptions.ValidationError as e:
            pytest.fail(f"Request schema validation failed: {e.message}")

    def test_endpoint_contract(
        self,
        method: str,
        endpoint: str,
        request_data: Dict[str, Any],
        expected_status: int,
        response_schema: Dict[str, Any],
        headers: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """Test an endpoint against its contract."""
        headers = headers or {"Content-Type": "application/json"}

        # Make request
        if method.upper() == "GET":
            response = self.client.get(endpoint, headers=headers)
        elif method.upper() == "POST":
            response = self.client.post(endpoint, json=request_data, headers=headers)
        elif method.upper() == "PUT":
            response = self.client.put(endpoint, json=request_data, headers=headers)
        elif method.upper() == "DELETE":
            response = self.client.delete(endpoint, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        # Validate status code
        assert response.status_code == expected_status, (
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response: {response.text}"
        )

        # Validate response schema
        if response.status_code < 300:  # Success responses
            response_json = response.json()
            self.validate_response_schema(response_json, response_schema)
            return response_json

        return response.json() if response.content else {}


# ═══════════════════════════════════════════════════════════════
# OpenAPI Schema Definitions
# ═══════════════════════════════════════════════════════════════

# Request schemas
MIGRATION_VALIDATION_REQUEST_SCHEMA = {
    "type": "object",
    "required": [
        "source_technology",
        "target_technology",
        "validation_scope",
        "source_input",
        "target_input",
    ],
    "properties": {
        "source_technology": {
            "type": "object",
            "required": ["type", "version"],
            "properties": {
                "type": {"type": "string", "enum": [t.value for t in TechnologyType]},
                "version": {"type": "string"},
            },
        },
        "target_technology": {
            "type": "object",
            "required": ["type", "version"],
            "properties": {
                "type": {"type": "string", "enum": [t.value for t in TechnologyType]},
                "version": {"type": "string"},
            },
        },
        "validation_scope": {"type": "string", "enum": [scope.value for scope in ValidationScope]},
        "source_input": {
            "type": "object",
            "required": ["type"],
            "properties": {
                "type": {"type": "string", "enum": [t.value for t in InputType]},
                "files": {"type": "array", "items": {"type": "string"}},
                "url": {"type": "string"},
                "text": {"type": "string"},
            },
        },
        "target_input": {
            "type": "object",
            "required": ["type"],
            "properties": {
                "type": {"type": "string", "enum": [t.value for t in InputType]},
                "files": {"type": "array", "items": {"type": "string"}},
                "url": {"type": "string"},
                "text": {"type": "string"},
            },
        },
    },
}

# Response schemas
VALIDATION_RESULT_SCHEMA = {
    "type": "object",
    "required": ["validation_id", "status", "timestamp"],
    "properties": {
        "validation_id": {"type": "string"},
        "status": {"type": "string", "enum": [status.value for status in ValidationStatus]},
        "timestamp": {"type": "string", "format": "date-time"},
        "source_analysis": {"type": "object"},
        "target_analysis": {"type": "object"},
        "comparison_results": {"type": "object"},
        "similarity_score": {"type": "number", "minimum": 0, "maximum": 1},
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "errors": {"type": "array", "items": {"type": "string"}},
    },
}

HEALTH_CHECK_SCHEMA = {
    "type": "object",
    "required": [
        "status",
        "timestamp"],
    "properties": {
        "status": {
            "type": "string",
            "enum": [
                    "healthy",
                    "unhealthy"]},
        "timestamp": {
            "type": "string",
            "format": "date-time"},
        "version": {
            "type": "string"},
        "dependencies": {
            "type": "object",
            "properties": {
                "llm_service": {
                    "type": "string"},
                "database": {
                    "type": "string"}},
        },
    },
}

ERROR_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["error", "message"],
    "properties": {
        "error": {"type": "string"},
        "message": {"type": "string"},
        "details": {"type": "object"},
        "timestamp": {"type": "string", "format": "date-time"},
    },
}


# ═══════════════════════════════════════════════════════════════
# Contract Tests for Core API Endpoints
# ═══════════════════════════════════════════════════════════════


@pytest.mark.contract
@pytest.mark.integration
class TestAPIContracts:
    """Contract tests for API endpoints."""

    def setup_method(self):
        """Setup test environment."""
        self.client = TestClient(app)
        self.contract_tester = APIContractTester(self.client)

    def test_health_check_contract(self):
        """Test health check endpoint contract."""
        response = self.contract_tester.test_endpoint_contract(
            method="GET",
            endpoint="/health",
            request_data={},
            expected_status=200,
            response_schema=HEALTH_CHECK_SCHEMA,
        )

        # Additional contract validations
        assert response["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in response
        assert isinstance(response["timestamp"], str)

    def test_migration_validation_contract_success(self):
        """Test successful migration validation contract."""
        request_data = {
            "source_technology": {
                "type": TechnologyType.PYTHON_FLASK.value,
                "version": "2.0"},
            "target_technology": {
                "type": TechnologyType.JAVA_SPRING.value,
                "version": "3.0"},
            "validation_scope": ValidationScope.BUSINESS_LOGIC.value,
            "source_input": {
                "type": InputType.TEXT.value,
                "text": "def hello(): return 'Hello World'",
            },
            "target_input": {
                "type": InputType.TEXT.value,
                "text": 'public String hello() { return "Hello World"; }',
            },
        }

        # Validate request schema
        self.contract_tester.validate_request_schema(
            request_data, MIGRATION_VALIDATION_REQUEST_SCHEMA,
        )

        with patch("src.core.migration_validator.MigrationValidator.validate") as mock_validate:
            # Mock successful validation
            mock_validate.return_value = ValidationResult(
                validation_id="test-123",
                status=ValidationStatus.COMPLETED,
                similarity_score=0.85,
                recommendations=["Consider updating documentation"],
            )

            response = self.contract_tester.test_endpoint_contract(
                method="POST",
                endpoint="/validate",
                request_data=request_data,
                expected_status=200,
                response_schema=VALIDATION_RESULT_SCHEMA,
            )

            # Additional contract validations
            assert "validation_id" in response
            assert response["status"] == ValidationStatus.COMPLETED.value
            assert isinstance(response["similarity_score"], (int, float))
            assert 0 <= response["similarity_score"] <= 1

    def test_migration_validation_contract_error(self):
        """Test migration validation contract with error response."""
        invalid_request = {
            "source_technology": {
                "type": "INVALID_TECH",  # Invalid technology type
                "version": "1.0",
            },
            "target_technology": {"type": TechnologyType.JAVA_SPRING.value, "version": "3.0"},
            "validation_scope": ValidationScope.BUSINESS_LOGIC.value,
            "source_input": {"type": InputType.TEXT.value, "text": "def hello(): return 'Hello'"},
            "target_input": {
                "type": InputType.TEXT.value,
                "text": 'public String hello() { return "Hello"; }',
            },
        }

        response = self.contract_tester.test_endpoint_contract(
            method="POST",
            endpoint="/validate",
            request_data=invalid_request,
            expected_status=422,  # Validation error
            response_schema=ERROR_RESPONSE_SCHEMA,
        )

        # Validate error response structure
        assert "error" in response
        assert "message" in response

    def test_validation_status_contract(self):
        """Test validation status endpoint contract."""
        validation_id = "test-validation-123"

        with patch(
            "src.core.migration_validator.MigrationValidator.get_validation_status",
        ) as mock_status:
            mock_status.return_value = ValidationResult(
                validation_id=validation_id,
                status=ValidationStatus.IN_PROGRESS,
                similarity_score=None,
            )

            response = self.contract_tester.test_endpoint_contract(
                method="GET",
                endpoint=f"/validate/{validation_id}/status",
                request_data={},
                expected_status=200,
                response_schema=VALIDATION_RESULT_SCHEMA,
            )

            assert response["validation_id"] == validation_id
            assert response["status"] == ValidationStatus.IN_PROGRESS.value

    def test_validation_status_not_found_contract(self):
        """Test validation status endpoint with non-existent ID."""
        non_existent_id = "non-existent-123"

        response = self.contract_tester.test_endpoint_contract(
            method="GET",
            endpoint=f"/validate/{non_existent_id}/status",
            request_data={},
            expected_status=404,
            response_schema=ERROR_RESPONSE_SCHEMA,
        )

        assert response["error"] == "NOT_FOUND"


# ═══════════════════════════════════════════════════════════════
# Contract Tests for Behavioral Validation Endpoints
# ═══════════════════════════════════════════════════════════════


@pytest.mark.contract
@pytest.mark.behavioral
class TestBehavioralAPIContracts:
    """Contract tests for behavioral validation endpoints."""

    def setup_method(self):
        """Setup test environment."""
        self.client = TestClient(app)
        self.contract_tester = APIContractTester(self.client)

    def test_behavioral_validation_contract(self):
        """Test behavioral validation endpoint contract."""
        request_data = {
            "source_url": "http://legacy-app.test/login",
            "target_url": "http://new-app.test/login",
            "validation_scenarios": [
                "User login with valid credentials",
                "User login with invalid password",
                "Password reset workflow",
            ],
            "timeout": 300,
            "metadata": {"test_environment": "staging", "browser": "chromium"},
        }

        behavioral_request_schema = {
            "type": "object",
            "required": ["source_url", "target_url", "validation_scenarios"],
            "properties": {
                "source_url": {"type": "string", "format": "uri"},
                "target_url": {"type": "string", "format": "uri"},
                "validation_scenarios": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
                "timeout": {"type": "integer", "minimum": 30, "maximum": 3600},
                "metadata": {"type": "object"},
            },
        }

        behavioral_response_schema = {
            "type": "object",
            "required": ["validation_id", "status", "timestamp"],
            "properties": {
                "validation_id": {"type": "string"},
                "status": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "scenarios_completed": {"type": "integer"},
                "scenarios_passed": {"type": "integer"},
                "scenarios_failed": {"type": "integer"},
                "behavioral_similarity": {"type": "number", "minimum": 0, "maximum": 1},
                "discrepancies": {"type": "array", "items": {"type": "object"}},
            },
        }

        # Validate request schema
        self.contract_tester.validate_request_schema(
            request_data, behavioral_request_schema)

        with patch("src.behavioral.crews.BehavioralValidationCrew.validate") as mock_validate:
            mock_validate.return_value = {
                "validation_id": "behavioral-123",
                "status": "completed",
                "scenarios_completed": 3,
                "scenarios_passed": 2,
                "scenarios_failed": 1,
                "behavioral_similarity": 0.75,
            }

            response = self.contract_tester.test_endpoint_contract(
                method="POST",
                endpoint="/behavioral/validate",
                request_data=request_data,
                expected_status=200,
                response_schema=behavioral_response_schema,
            )

            assert response["scenarios_completed"] == 3
            assert (
                response["scenarios_passed"] + response["scenarios_failed"]
                <= response["scenarios_completed"]
            )


# ═══════════════════════════════════════════════════════════════
# Backward Compatibility Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.contract
@pytest.mark.regression
class TestAPIBackwardCompatibility:
    """Test backward compatibility of API changes."""

    def setup_method(self):
        """Setup test environment."""
        self.client = TestClient(app)
        self.contract_tester = APIContractTester(self.client)

    def test_v1_api_backward_compatibility(self):
        """Test that v1 API endpoints remain compatible."""
        # Test legacy request format (if applicable)
        legacy_request = {
            "source": {
                "technology": "python_flask",  # Old format
                "version": "2.0",
                "code": "def hello(): return 'Hello'",
            },
            "target": {
                "technology": "java_spring",  # Old format
                "version": "3.0",
                "code": 'public String hello() { return "Hello"; }',
            },
            "scope": "business_logic",
        }

        # Should either work with legacy format or return appropriate error
        response = self.client.post("/validate", json=legacy_request)

        # Should not return 500 (internal server error)
        assert response.status_code != 500

        if response.status_code == 422:
            # If legacy format is no longer supported, error should be clear
            error_response = response.json()
            assert "error" in error_response
            assert (
                "deprecated" in error_response["message"].lower()
                or "format" in error_response["message"].lower()
            )

    def test_response_field_stability(self):
        """Test that response fields remain stable across versions."""
        request_data = {
            "source_technology": {
                "type": TechnologyType.PYTHON_FLASK.value,
                "version": "2.0"},
            "target_technology": {
                "type": TechnologyType.JAVA_SPRING.value,
                "version": "3.0"},
            "validation_scope": ValidationScope.BUSINESS_LOGIC.value,
            "source_input": {
                "type": InputType.TEXT.value,
                "text": "def test(): pass"},
            "target_input": {
                "type": InputType.TEXT.value,
                "text": "public void test() {}"},
        }

        with patch("src.core.migration_validator.MigrationValidator.validate") as mock_validate:
            mock_validate.return_value = ValidationResult(
                validation_id="test-123", status=ValidationStatus.COMPLETED, similarity_score=0.85, )

            response = self.client.post("/validate", json=request_data)
            assert response.status_code == 200

            response_json = response.json()

            # Core fields should always be present
            required_fields = ["validation_id", "status", "timestamp"]
            for field in required_fields:
                assert field in response_json, f"Required field '{field}' missing from response"

            # Field types should remain consistent
            assert isinstance(response_json["validation_id"], str)
            assert isinstance(response_json["status"], str)
            assert isinstance(response_json["timestamp"], str)

            if "similarity_score" in response_json:
                assert isinstance(response_json["similarity_score"], (int, float))


# ═══════════════════════════════════════════════════════════════
# API Version Compatibility Matrix
# ═══════════════════════════════════════════════════════════════


@pytest.mark.contract
@pytest.mark.parametrize(
    "api_version,endpoint,expected_status",
    [
        ("v1", "/validate", 200),
        ("v1", "/health", 200),
        ("v2", "/validate", 200),  # Future version
        ("v2", "/health", 200),
    ],
)
class TestAPIVersionCompatibility:
    """Test API version compatibility matrix."""

    def setup_method(self):
        """Setup test environment."""
        self.client = TestClient(app)

    def test_api_version_support(self, api_version, endpoint, expected_status):
        """Test API version support across endpoints."""
        headers = {"Accept": f"application/vnd.migration-validator.{api_version}+json"}

        if endpoint == "/validate":
            request_data = {
                "source_technology": {
                    "type": TechnologyType.PYTHON_FLASK.value,
                    "version": "2.0"},
                "target_technology": {
                    "type": TechnologyType.JAVA_SPRING.value,
                    "version": "3.0"},
                "validation_scope": ValidationScope.BUSINESS_LOGIC.value,
                "source_input": {
                    "type": InputType.TEXT.value,
                    "text": "def test(): pass"},
                "target_input": {
                    "type": InputType.TEXT.value,
                    "text": "public void test() {}"},
            }

            with patch("src.core.migration_validator.MigrationValidator.validate"):
                response = self.client.post(
                    endpoint, json=request_data, headers=headers)
        else:
            response = self.client.get(endpoint, headers=headers)

        # Should either support the version or return appropriate error
        if api_version == "v1":
            assert response.status_code in [200, 201, 202]  # Success codes
        else:
            # Future versions might not be implemented yet
            assert response.status_code in [
                200, 201, 202, 404, 501]  # Success or not implemented


# ═══════════════════════════════════════════════════════════════
# Contract Test Utilities
# ═══════════════════════════════════════════════════════════════


class ContractTestHelper:
    """Helper utilities for contract testing."""

    @staticmethod
    def generate_valid_request(
        source_tech: TechnologyType = TechnologyType.PYTHON_FLASK,
        target_tech: TechnologyType = TechnologyType.JAVA_SPRING,
        scope: ValidationScope = ValidationScope.BUSINESS_LOGIC,
    ) -> Dict[str, Any]:
        """Generate a valid migration validation request."""
        return {
            "source_technology": {
                "type": source_tech.value,
                "version": "2.0"},
            "target_technology": {
                "type": target_tech.value,
                "version": "3.0"},
            "validation_scope": scope.value,
            "source_input": {
                "type": InputType.TEXT.value,
                "text": "def test(): pass"},
            "target_input": {
                "type": InputType.TEXT.value,
                "text": "public void test() {}"},
        }

    @staticmethod
    def validate_pagination_contract(response: Dict[str, Any]) -> None:
        """Validate pagination contract in list responses."""
        if "pagination" in response:
            pagination = response["pagination"]
            required_fields = ["page", "per_page", "total", "pages"]
            for field in required_fields:
                assert field in pagination, f"Pagination field '{field}' missing"
                assert isinstance(
                    pagination[field], int,
                ), f"Pagination field '{field}' must be integer"

            assert pagination["page"] >= 1, "Page number must be >= 1"
            assert pagination["per_page"] >= 1, "Per page must be >= 1"
            assert pagination["total"] >= 0, "Total must be >= 0"
            assert pagination["pages"] >= 0, "Pages must be >= 0"

    @staticmethod
    def validate_error_contract(response: Dict[str, Any]) -> None:
        """Validate error response contract."""
        required_fields = ["error", "message"]
        for field in required_fields:
            assert field in response, f"Error response field '{field}' missing"
            assert isinstance(
                response[field], str,
            ), f"Error response field '{field}' must be string"

        if "details" in response:
            assert isinstance(
                response["details"], dict), "Error details must be an object"


@pytest.mark.contract
class TestContractHelpers:
    """Test contract helper utilities."""

    def test_valid_request_generation(self):
        """Test valid request generation helper."""
        request = ContractTestHelper.generate_valid_request()

        # Validate against schema
        validator = Draft7Validator(MIGRATION_VALIDATION_REQUEST_SCHEMA)
        errors = list(validator.iter_errors(request))
        assert len(errors) == 0, f"Generated request is invalid: {errors}"

    def test_pagination_contract_validation(self):
        """Test pagination contract validation."""
        valid_pagination = {
            "pagination": {"page": 1, "per_page": 10, "total": 100, "pages": 10},
            "data": [],
        }

        # Should not raise exception
        ContractTestHelper.validate_pagination_contract(valid_pagination)

        invalid_pagination = {
            "pagination": {"page": 0, "per_page": 10},  # Missing fields, invalid page
            "data": [],
        }

        with pytest.raises(AssertionError):
            ContractTestHelper.validate_pagination_contract(invalid_pagination)

    def test_error_contract_validation(self):
        """Test error contract validation."""
        valid_error = {"error": "VALIDATION_ERROR", "message": "Invalid input"}

        # Should not raise exception
        ContractTestHelper.validate_error_contract(valid_error)

        invalid_error = {"error": "VALIDATION_ERROR"}  # Missing message

        with pytest.raises(AssertionError):
            ContractTestHelper.validate_error_contract(invalid_error)
