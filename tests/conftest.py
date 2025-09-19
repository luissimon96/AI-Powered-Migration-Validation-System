"""
Pytest configuration and fixtures for AI-Powered Migration Validation System.

Provides common fixtures and setup for all tests.
"""

import pytest
import asyncio
import tempfile
import os
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

from src.core.models import (
    MigrationValidationRequest,
    TechnologyContext,
    TechnologyType,
    ValidationScope,
    InputData,
    InputType
)
from src.services.llm_service import LLMService, LLMConfig, LLMProvider, LLMResponse
from src.core.migration_validator import MigrationValidator
from src.behavioral.crews import BehavioralValidationCrew


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing."""
    mock_service = AsyncMock(spec=LLMService)
    
    # Mock response for general queries
    mock_response = LLMResponse(
        content='{"similarity_score": 0.85, "functionally_equivalent": true, "confidence": 0.9}',
        model="mock-model",
        provider="mock",
        usage={"total_tokens": 150}
    )
    mock_service.generate_response.return_value = mock_response
    
    # Mock specialized methods
    mock_service.analyze_code_semantic_similarity.return_value = {
        "similarity_score": 0.85,
        "functionally_equivalent": True,
        "confidence": 0.9,
        "key_differences": ["Minor variable naming differences"],
        "potential_issues": [],
        "business_logic_preserved": True,
        "recommendations": ["Consider standardizing naming conventions"]
    }
    
    mock_service.compare_ui_elements.return_value = {
        "elements_matched": 8,
        "missing_elements": [],
        "additional_elements": [],
        "functional_equivalent": True,
        "ux_preserved": True,
        "recommendations": []
    }
    
    mock_service.validate_business_logic.return_value = {
        "business_logic_preserved": True,
        "critical_discrepancies": [],
        "validation_gaps": [],
        "risk_assessment": "low",
        "recommendations": []
    }
    
    mock_service.get_provider_info.return_value = {
        "provider": "mock",
        "model": "mock-model",
        "max_tokens": 4000,
        "temperature": 0.1,
        "timeout": 60.0
    }
    
    return mock_service


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return '''
def validate_user_input(email, password):
    """Validate user input for login."""
    if not email or "@" not in email:
        raise ValueError("Invalid email address")
    
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    
    return True

class UserManager:
    def __init__(self):
        self.users = {}
    
    def create_user(self, email, password):
        if email in self.users:
            raise ValueError("User already exists")
        
        validate_user_input(email, password)
        self.users[email] = {"password": password, "active": True}
        return {"id": len(self.users), "email": email}
'''


@pytest.fixture
def sample_java_code():
    """Sample Java code for testing."""
    return '''
public class UserValidator {
    public static boolean validateUserInput(String email, String password) {
        if (email == null || !email.contains("@")) {
            throw new IllegalArgumentException("Invalid email address");
        }
        
        if (password == null || password.length() < 8) {
            throw new IllegalArgumentException("Password must be at least 8 characters");
        }
        
        return true;
    }
}

public class UserManager {
    private Map<String, User> users = new HashMap<>();
    
    public User createUser(String email, String password) {
        if (users.containsKey(email)) {
            throw new IllegalArgumentException("User already exists");
        }
        
        validateUserInput(email, password);
        User user = new User(email, password);
        users.put(email, user);
        return user;
    }
}
'''


@pytest.fixture
def temp_files():
    """Create temporary files for testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Create sample source file
    source_file = os.path.join(temp_dir, "source.py")
    with open(source_file, "w") as f:
        f.write("""
def calculate_total(price, tax_rate):
    return price * (1 + tax_rate)

def process_order(items, discount=0.0):
    total = sum(item['price'] * item['quantity'] for item in items)
    total *= (1 - discount)
    return total
""")
    
    # Create sample target file
    target_file = os.path.join(temp_dir, "target.java")
    with open(target_file, "w") as f:
        f.write("""
public class OrderProcessor {
    public static double calculateTotal(double price, double taxRate) {
        return price * (1 + taxRate);
    }
    
    public static double processOrder(List<Item> items, double discount) {
        double total = items.stream()
            .mapToDouble(item -> item.getPrice() * item.getQuantity())
            .sum();
        return total * (1 - discount);
    }
}
""")
    
    yield {
        "temp_dir": temp_dir,
        "source_file": source_file,
        "target_file": target_file
    }
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_validation_request(temp_files):
    """Sample validation request for testing."""
    return MigrationValidationRequest(
        source_technology=TechnologyContext(
            type=TechnologyType.PYTHON_FLASK,
            version="2.0"
        ),
        target_technology=TechnologyContext(
            type=TechnologyType.JAVA_SPRING,
            version="3.0"
        ),
        validation_scope=ValidationScope.BUSINESS_LOGIC,
        source_input=InputData(
            type=InputType.CODE_FILES,
            files=[temp_files["source_file"]]
        ),
        target_input=InputData(
            type=InputType.CODE_FILES,
            files=[temp_files["target_file"]]
        )
    )


@pytest.fixture
def behavioral_validation_request():
    """Sample behavioral validation request."""
    from src.behavioral.crews import BehavioralValidationRequest
    
    return BehavioralValidationRequest(
        source_url="http://legacy-system.test/login",
        target_url="http://new-system.test/login",
        validation_scenarios=[
            "User login with valid credentials",
            "User login with invalid email",
            "User login with short password",
            "Password reset flow",
            "Account creation workflow"
        ],
        timeout=300,
        metadata={"test_environment": "staging"}
    )


@pytest.fixture
def migration_validator(mock_llm_service):
    """Migration validator with mocked dependencies."""
    return MigrationValidator(llm_client=mock_llm_service)


@pytest.fixture
def behavioral_crew(mock_llm_service):
    """Behavioral validation crew with mocked dependencies."""
    return BehavioralValidationCrew(llm_service=mock_llm_service)


@pytest.fixture
def mock_fastapi_client():
    """Mock FastAPI test client."""
    from fastapi.testclient import TestClient
    from src.api.routes import app
    
    return TestClient(app)


# Markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.behavioral = pytest.mark.behavioral
pytest.mark.performance = pytest.mark.performance
pytest.mark.security = pytest.mark.security


# Test configuration
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DEBUG"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    # Disable actual LLM calls in tests
    os.environ["OPENAI_API_KEY"] = "test-key-disabled"
    os.environ["ANTHROPIC_API_KEY"] = "test-key-disabled"
    os.environ["GOOGLE_API_KEY"] = "test-key-disabled"
    
    yield
    
    # Cleanup environment
    test_vars = ["ENVIRONMENT", "DEBUG", "LOG_LEVEL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    for var in test_vars:
        if var in os.environ:
            del os.environ[var]