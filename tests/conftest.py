"""Enhanced pytest configuration and fixtures for AI-Powered Migration Validation System.

Provides comprehensive fixtures, test data management, and advanced testing utilities
for property-based testing, performance testing, and visual regression testing.
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Third-party imports for advanced testing
try:
    from hypothesis import strategies as st
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Project imports
from src.analyzers.code_analyzer import CodeAnalyzer
from src.behavioral.crews import BehavioralValidationCrew
from src.core.input_processor import InputProcessor
from src.core.migration_validator import MigrationValidator
from src.core.models import (
    InputData,
    InputType,
    MigrationValidationRequest,
    TechnologyContext,
    TechnologyType,
    ValidationScope,
)
from src.security.api_keys import APIKeyManager, APIKeyMetadata
from src.security.schemas import APIKeyScope
from src.services.llm_service import LLMResponse, LLMService

# ═══════════════════════════════════════════════════════════════
# Test Configuration and Setup
# ═══════════════════════════════════════════════════════════════


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "behavioral: marks tests as behavioral validation tests")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")
    config.addinivalue_line("markers", "benchmark: marks tests as benchmark tests")
    config.addinivalue_line("markers", "memory: marks tests as memory profiling tests")
    config.addinivalue_line("markers", "security: marks tests as security tests")
    config.addinivalue_line("markers", "property: marks tests as property-based tests")
    config.addinivalue_line("markers", "mutation: marks tests as mutation testing targets")
    config.addinivalue_line("markers", "contract: marks tests as contract tests")
    config.addinivalue_line("markers", "chaos: marks tests as chaos engineering tests")
    config.addinivalue_line("markers", "visual: marks tests as visual regression tests")
    config.addinivalue_line("markers", "regression: marks tests as regression tests")
    config.addinivalue_line("markers", "critical: marks tests as critical path tests")
    config.addinivalue_line("markers", "smoke: marks tests as smoke tests")
    config.addinivalue_line("markers", "fuzz: marks tests as fuzzing tests")
    config.addinivalue_line("markers", "penetration: marks tests as penetration tests")
    config.addinivalue_line("markers", "external: marks tests requiring external services")
    config.addinivalue_line("markers", "llm: marks tests requiring LLM API access")
    config.addinivalue_line("markers", "browser: marks tests requiring browser automation")
    config.addinivalue_line("markers", "database: marks tests requiring database connections")
    config.addinivalue_line("markers", "network: marks tests requiring network access")
    config.addinivalue_line("markers", "api: marks tests for API endpoints")


def pytest_collection_modifyitems(config, items):
    """Modify collected test items based on configuration."""
    # Skip slow tests if --fast is specified
    if config.getoption("--fast", default=False):
        skip_slow = pytest.mark.skip(reason="Skipping slow tests (--fast mode)")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    # Skip external tests in CI if no external access
    if os.environ.get("CI") and not os.environ.get("ALLOW_EXTERNAL_TESTS"):
        skip_external = pytest.mark.skip(reason="Skipping external tests in CI")
        for item in items:
            if "external" in item.keywords:
                item.add_marker(skip_external)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption("--fast", action="store_true", default=False, help="Skip slow tests")
    parser.addoption(
        "--hypothesis-profile",
        action="store",
        default="default",
        help="Hypothesis testing profile (default, dev, ci)",
    )
    parser.addoption(
        "--performance-baseline",
        action="store",
        default=None,
        help="Performance baseline file for regression testing",
    )


# ═══════════════════════════════════════════════════════════════
# Core Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture."""
    return {
        "environment": "testing",
        "debug": True,
        "log_level": "DEBUG",
        "test_data_dir": Path(__file__).parent / "data",
        "temp_dir": Path(tempfile.gettempdir()) / "migration_validator_tests",
        "performance_baseline_file": "performance_baselines.json",
        "timeout_default": 30,
        "timeout_slow": 300,
        "max_file_size_mb": 10,
        "max_concurrent_tests": 10,
    }


@pytest.fixture
def temp_directory(test_config):
    """Create and cleanup temporary directory for tests."""
    temp_dir = test_config["temp_dir"]
    temp_dir.mkdir(parents=True, exist_ok=True)

    yield temp_dir

    # Cleanup
    import shutil

    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
# Mock Service Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def mock_llm_service():
    """Enhanced mock LLM service for testing."""
    mock_service = AsyncMock(spec=LLMService)

    # Mock response for general queries
    mock_response = LLMResponse(
        content='{"similarity_score": 0.85, "functionally_equivalent": true, "confidence": 0.9}',
        model="mock-model",
        provider="mock",
        usage={"total_tokens": 150, "prompt_tokens": 100, "completion_tokens": 50},
    )
    mock_service.generate_response.return_value = mock_response

    # Mock specialized methods with realistic responses
    mock_service.analyze_code_semantic_similarity.return_value = AsyncMock(
        result={
            "similarity_score": 0.85,
            "functionally_equivalent": True,
            "confidence": 0.9,
            "key_differences": ["Minor variable naming differences"],
            "potential_issues": [],
            "business_logic_preserved": True,
            "recommendations": ["Consider standardizing naming conventions"],
            "execution_time_ms": 150,
            "token_usage": {"total": 150, "prompt": 100, "completion": 50},
        },
        confidence=0.9,
        provider_used="mock",
        model_used="mock-model",
    )

    mock_service.compare_ui_elements.return_value = {
        "elements_matched": 8,
        "elements_total": 10,
        "missing_elements": ["submit_button"],
        "additional_elements": ["cancel_button"],
        "functional_equivalent": True,
        "ux_preserved": True,
        "accessibility_score": 0.92,
        "recommendations": ["Add missing submit button", "Consider accessibility improvements"],
    }

    mock_service.validate_business_logic.return_value = AsyncMock(
        result={
            "business_logic_preserved": True,
            "critical_discrepancies": [],
            "validation_gaps": [],
            "risk_assessment": "low",
            "confidence_score": 0.91,
            "recommendations": [],
            "detailed_analysis": {
                "input_validation": "preserved",
                "business_rules": "equivalent",
                "error_handling": "improved",
            },
        },
        confidence=0.91,
        provider_used="mock",
    )

    mock_service.get_provider_info.return_value = [
        {
            "provider": "mock",
            "model": "mock-model-v1.0",
            "max_tokens": 4000,
            "temperature": 0.1,
            "timeout": 60.0,
        },
    ]

    # Mock error scenarios for edge case testing
    mock_service.simulate_rate_limit = AsyncMock(side_effect=Exception("Rate limit exceeded"))
    mock_service.simulate_timeout = AsyncMock(side_effect=asyncio.TimeoutError("Request timeout"))
    mock_service.simulate_invalid_response = AsyncMock(
        return_value=LLMResponse(
            content="Invalid JSON response", model="mock-model", provider="mock", usage={},
        ),
    )

    return mock_service


@pytest.fixture
def mock_database():
    """Mock database for testing."""
    mock_db = AsyncMock()

    # Mock connection and session management
    mock_db.connect.return_value = True
    mock_db.disconnect.return_value = True
    mock_db.begin_transaction.return_value = MagicMock()
    mock_db.commit.return_value = True
    mock_db.rollback.return_value = True

    # Mock CRUD operations
    mock_db.create.return_value = {"id": "test-123", "created_at": "2023-01-01T00:00:00Z"}
    mock_db.read.return_value = {"id": "test-123", "status": "completed"}
    mock_db.update.return_value = True
    mock_db.delete.return_value = True

    # Mock query operations
    mock_db.query.return_value = [
        {"id": "test-1", "status": "completed"},
        {"id": "test-2", "status": "in_progress"},
    ]
    mock_db.count.return_value = 2

    # Mock API key operations
    mock_db.store_api_key.return_value = True
    mock_db.get_api_key_by_hash.return_value = {
        "metadata": {
            "id": "test-api-key-123",
            "name": "Test API Key",
            "description": "Test API key for unit testing",
            "scopes": [APIKeyScope.READ_ONLY],
            "created_at": "2023-01-01T00:00:00Z",
            "expires_at": None,
            "last_used_at": None,
            "rate_limit_per_minute": 60,
            "is_active": True,
            "created_by": "test_user",
            "usage_count": 0,
        },
    }
    mock_db.update_api_key_last_used.return_value = True
    mock_db.deactivate_api_key.return_value = True
    mock_db.list_api_keys.return_value = []

    return mock_db


@pytest.fixture
def mock_browser_automation():
    """Mock browser automation for behavioral testing."""
    mock_browser = MagicMock()

    # Mock browser lifecycle
    mock_browser.launch.return_value = True
    mock_browser.close.return_value = True
    mock_browser.new_page.return_value = MagicMock()

    # Mock page interactions
    mock_page = mock_browser.new_page.return_value
    mock_page.goto.return_value = True
    mock_page.wait_for_selector.return_value = MagicMock()
    mock_page.click.return_value = True
    mock_page.fill.return_value = True
    mock_page.screenshot.return_value = b"mock_screenshot_data"

    # Mock evaluation results
    mock_page.evaluate.return_value = {
        "elements_found": 5,
        "forms_detected": 1,
        "buttons_detected": 3,
        "page_title": "Test Page",
    }

    return mock_browser


@pytest.fixture
def mock_api_key_manager():
    """Mock API key manager for security testing."""
    mock_manager = AsyncMock(spec=APIKeyManager)

    # Sample API key metadata
    sample_metadata = APIKeyMetadata(
        id="test-key-123",
        name="Test API Key",
        description="Test key for unit testing",
        scopes=[APIKeyScope.READ_ONLY, APIKeyScope.VALIDATION],
        created_at=datetime.utcnow(),
        expires_at=None,
        last_used_at=None,
        rate_limit_per_minute=60,
        is_active=True,
        created_by="test_user",
        usage_count=0,
    )

    mock_manager.validate_api_key.return_value = sample_metadata
    mock_manager.create_api_key.return_value = ("amvs_test_key_123", sample_metadata)
    mock_manager.revoke_api_key.return_value = True
    mock_manager.check_scope_permission.return_value = True

    return mock_manager


# ═══════════════════════════════════════════════════════════════
# Test Data Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def sample_python_code():
    """Enhanced sample Python code for testing."""
    return '''
"""Sample Python module for testing migration validation."""

import os
import sys
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error."""
    pass


def validate_user_input(email: str, password: str) -> bool:
    """
    Validate user input for login.

    Args:
        email: User email address
        password: User password

    Returns:
        True if valid, raises ValidationError otherwise

    Raises:
        ValidationError: If validation fails
    """
    logger.info(f"Validating input for email: {email}")

    if not email or "@" not in email:
        raise ValidationError("Invalid email address")

    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters")

    # Check for common weak passwords
    weak_passwords = ["password", "12345678", "qwerty"]
    if password.lower() in weak_passwords:
        raise ValidationError("Password is too weak")

    return True


def hash_password(password: str) -> str:
    """Hash password for secure storage."""
    import hashlib
    import secrets

    # Generate salt
    salt = secrets.token_hex(16)

    # Hash password with salt
    pwd_hash = hashlib.pbkdf2_hmac('sha256',
                                  password.encode('utf-8'),
                                  salt.encode('utf-8'),
                                  100000)

    return f"{salt}:{pwd_hash.hex()}"


class UserManager:
    """User management system."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize user manager."""
        self.config = config or {}
        self.users: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = self.config.get("session_timeout", 3600)
        logger.info("UserManager initialized")

    def create_user(self, email: str, password: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a new user.

        Args:
            email: User email
            password: User password
            metadata: Additional user metadata

        Returns:
            User data dictionary

        Raises:
            ValidationError: If user creation fails
        """
        if email in self.users:
            raise ValidationError("User already exists")

        # Validate input
        validate_user_input(email, password)

        # Create user record
        user_data = {
            "id": len(self.users) + 1,
            "email": email,
            "password_hash": hash_password(password),
            "created_at": datetime.utcnow().isoformat(),
            "active": True,
            "metadata": metadata or {}
        }

        self.users[email] = user_data
        logger.info(f"User created: {email}")

        # Return safe user data (without password hash)
        return {
            "id": user_data["id"],
            "email": user_data["email"],
            "created_at": user_data["created_at"],
            "active": user_data["active"]
        }

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials."""
        if email not in self.users:
            return None

        user = self.users[email]
        if not user.get("active", False):
            return None

        # In a real implementation, you'd verify the password hash
        # For testing, we'll do a simple check
        try:
            validate_user_input(email, password)
            return {
                "id": user["id"],
                "email": user["email"],
                "last_login": datetime.utcnow().isoformat()
            }
        except ValidationError:
            return None

    def deactivate_user(self, email: str) -> bool:
        """Deactivate a user account."""
        if email in self.users:
            self.users[email]["active"] = False
            self.users[email]["deactivated_at"] = datetime.utcnow().isoformat()
            logger.info(f"User deactivated: {email}")
            return True
        return False

    def get_user_stats(self) -> Dict[str, int]:
        """Get user statistics."""
        active_users = sum(1 for user in self.users.values() if user.get("active", False))
        return {
            "total_users": len(self.users),
            "active_users": active_users,
            "inactive_users": len(self.users) - active_users
        }


def process_user_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process a list of user data."""
    if not data:
        return {"processed": 0, "errors": []}

    processed_count = 0
    errors = []

    user_manager = UserManager()

    for item in data:
        try:
            if "email" in item and "password" in item:
                user_manager.create_user(
                    email=item["email"],
                    password=item["password"],
                    metadata=item.get("metadata")
                )
                processed_count += 1
            else:
                errors.append(f"Missing required fields in item: {item}")
        except ValidationError as e:
            errors.append(f"Validation error for {item.get('email', 'unknown')}: {str(e)}")
        except Exception as e:
            errors.append(f"Unexpected error for {item.get('email', 'unknown')}: {str(e)}")

    return {
        "processed": processed_count,
        "errors": errors,
        "stats": user_manager.get_user_stats()
    }


if __name__ == "__main__":
    # Example usage
    manager = UserManager()

    try:
        user = manager.create_user("test@example.com", "securepassword123")
        print(f"Created user: {user}")

        auth_result = manager.authenticate_user("test@example.com", "securepassword123")
        print(f"Authentication result: {auth_result}")

    except ValidationError as e:
        print(f"Validation error: {e}")
'''


@pytest.fixture
def sample_java_code():
    """Enhanced sample Java code for testing."""
    return """
package com.example.migration.validator;

import java.util.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.logging.Logger;
import java.util.logging.Level;

/**
 * User management system for testing migration validation.
 *
 * @author Migration Validator
 * @version 1.0
 */
public class UserManager {

    private static final Logger logger = Logger.getLogger(UserManager.class.getName());
    private static final int MIN_PASSWORD_LENGTH = 8;
    private static final Set<String> WEAK_PASSWORDS = Set.of("password", "12345678", "qwerty");

    private final Map<String, User> users;
    private final Map<String, Object> config;
    private final int sessionTimeout;

    /**
     * Custom validation exception.
     */
    public static class ValidationException extends Exception {
        public ValidationException(String message) {
            super(message);
        }
    }

    /**
     * User data class.
     */
    public static class User {
        private final long id;
        private final String email;
        private final String passwordHash;
        private final LocalDateTime createdAt;
        private boolean active;
        private Map<String, Object> metadata;

        public User(long id, String email, String passwordHash, Map<String, Object> metadata) {
            this.id = id;
            this.email = email;
            this.passwordHash = passwordHash;
            this.createdAt = LocalDateTime.now();
            this.active = true;
            this.metadata = metadata != null ? metadata : new HashMap<>();
        }

        // Getters
        public long getId() { return id; }
        public String getEmail() { return email; }
        public String getPasswordHash() { return passwordHash; }
        public LocalDateTime getCreatedAt() { return createdAt; }
        public boolean isActive() { return active; }
        public Map<String, Object> getMetadata() { return metadata; }

        // Setters
        public void setActive(boolean active) { this.active = active; }
        public void setMetadata(Map<String, Object> metadata) { this.metadata = metadata; }
    }

    /**
     * Initialize user manager.
     */
    public UserManager() {
        this(new HashMap<>());
    }

    /**
     * Initialize user manager with configuration.
     *
     * @param config Configuration map
     */
    public UserManager(Map<String, Object> config) {
        this.config = config;
        this.users = new HashMap<>();
        this.sessionTimeout = (Integer) config.getOrDefault("sessionTimeout", 3600);
        logger.info("UserManager initialized");
    }

    /**
     * Validate user input for login.
     *
     * @param email User email address
     * @param password User password
     * @return true if valid
     * @throws ValidationException if validation fails
     */
    public boolean validateUserInput(String email, String password) throws ValidationException {
        logger.info("Validating input for email: " + email);

        if (email == null || !email.contains("@")) {
            throw new ValidationException("Invalid email address");
        }

        if (password == null || password.length() < MIN_PASSWORD_LENGTH) {
            throw new ValidationException("Password must be at least " + MIN_PASSWORD_LENGTH + " characters");
        }

        if (WEAK_PASSWORDS.contains(password.toLowerCase())) {
            throw new ValidationException("Password is too weak");
        }

        return true;
    }

    /**
     * Hash password for secure storage.
     *
     * @param password Plain text password
     * @return Hashed password with salt
     */
    public String hashPassword(String password) {
        try {
            // Generate salt
            SecureRandom random = new SecureRandom();
            byte[] salt = new byte[16];
            random.nextBytes(salt);

            // Hash password with salt
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            md.update(salt);
            byte[] hashedPassword = md.digest(password.getBytes("UTF-8"));

            // Return salt + hash as hex string
            StringBuilder sb = new StringBuilder();
            for (byte b : salt) {
                sb.append(String.format("%02x", b));
            }
            sb.append(":");
            for (byte b : hashedPassword) {
                sb.append(String.format("%02x", b));
            }

            return sb.toString();
        } catch (Exception e) {
            throw new RuntimeException("Error hashing password", e);
        }
    }

    /**
     * Create a new user.
     *
     * @param email User email
     * @param password User password
     * @param metadata Additional user metadata
     * @return User data map
     * @throws ValidationException if user creation fails
     */
    public Map<String, Object> createUser(String email, String password, Map<String, Object> metadata)
            throws ValidationException {

        if (users.containsKey(email)) {
            throw new ValidationException("User already exists");
        }

        // Validate input
        validateUserInput(email, password);

        // Create user record
        long userId = users.size() + 1;
        User user = new User(userId, email, hashPassword(password), metadata);
        users.put(email, user);

        logger.info("User created: " + email);

        // Return safe user data (without password hash)
        Map<String, Object> userData = new HashMap<>();
        userData.put("id", user.getId());
        userData.put("email", user.getEmail());
        userData.put("createdAt", user.getCreatedAt().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
        userData.put("active", user.isActive());

        return userData;
    }

    /**
     * Authenticate user credentials.
     *
     * @param email User email
     * @param password User password
     * @return User data if authentication successful, null otherwise
     */
    public Map<String, Object> authenticateUser(String email, String password) {
        User user = users.get(email);
        if (user == null || !user.isActive()) {
            return null;
        }

        try {
            validateUserInput(email, password);

            Map<String, Object> authResult = new HashMap<>();
            authResult.put("id", user.getId());
            authResult.put("email", user.getEmail());
            authResult.put("lastLogin", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));

            return authResult;
        } catch (ValidationException e) {
            return null;
        }
    }

    /**
     * Deactivate a user account.
     *
     * @param email User email
     * @return true if user was deactivated, false if user not found
     */
    public boolean deactivateUser(String email) {
        User user = users.get(email);
        if (user != null) {
            user.setActive(false);
            logger.info("User deactivated: " + email);
            return true;
        }
        return false;
    }

    /**
     * Get user statistics.
     *
     * @return Map containing user statistics
     */
    public Map<String, Integer> getUserStats() {
        int activeUsers = (int) users.values().stream()
            .filter(User::isActive)
            .count();

        Map<String, Integer> stats = new HashMap<>();
        stats.put("totalUsers", users.size());
        stats.put("activeUsers", activeUsers);
        stats.put("inactiveUsers", users.size() - activeUsers);

        return stats;
    }
}
"""


@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript/TypeScript code for testing."""
    return """
/**
 * User management system for testing migration validation.
 * TypeScript/JavaScript implementation.
 */

import crypto from 'crypto';
import { EventEmitter } from 'events';

interface UserConfig {
  sessionTimeout?: number;
  enableLogging?: boolean;
  maxUsers?: number;
}

interface UserMetadata {
  [key: string]: any;
}

interface User {
  id: number;
  email: string;
  passwordHash: string;
  createdAt: Date;
  active: boolean;
  metadata: UserMetadata;
  lastLogin?: Date;
}

class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

/**
 * User management class with full CRUD operations.
 */
export class UserManager extends EventEmitter {
  private users: Map<string, User> = new Map();
  private config: UserConfig;
  private sessionTimeout: number;
  private userIdCounter: number = 1;

  private static readonly MIN_PASSWORD_LENGTH = 8;
  private static readonly WEAK_PASSWORDS = ['password', '12345678', 'qwerty'];

  constructor(config: UserConfig = {}) {
    super();
    this.config = config;
    this.sessionTimeout = config.sessionTimeout || 3600;

    if (config.enableLogging) {
      console.log('UserManager initialized');
    }
  }

  /**
   * Validate user input for registration/login.
   */
  validateUserInput(email: string, password: string): boolean {
    if (this.config.enableLogging) {
      console.log(`Validating input for email: ${email}`);
    }

    if (!email || !email.includes('@')) {
      throw new ValidationError('Invalid email address');
    }

    if (!password || password.length < UserManager.MIN_PASSWORD_LENGTH) {
      throw new ValidationError(`Password must be at least ${UserManager.MIN_PASSWORD_LENGTH} characters`);
    }

    if (UserManager.WEAK_PASSWORDS.includes(password.toLowerCase())) {
      throw new ValidationError('Password is too weak');
    }

    return true;
  }

  /**
   * Hash password for secure storage.
   */
  hashPassword(password: string): string {
    const salt = crypto.randomBytes(16).toString('hex');
    const hash = crypto.pbkdf2Sync(password, salt, 100000, 64, 'sha256').toString('hex');
    return `${salt}:${hash}`;
  }

  /**
   * Create a new user.
   */
  async createUser(email: string, password: string, metadata: UserMetadata = {}): Promise<Omit<User, 'passwordHash'>> {
    if (this.users.has(email)) {
      throw new ValidationError('User already exists');
    }

    if (this.config.maxUsers && this.users.size >= this.config.maxUsers) {
      throw new ValidationError('Maximum number of users reached');
    }

    // Validate input
    this.validateUserInput(email, password);

    // Create user record
    const user: User = {
      id: this.userIdCounter++,
      email,
      passwordHash: this.hashPassword(password),
      createdAt: new Date(),
      active: true,
      metadata
    };

    this.users.set(email, user);

    if (this.config.enableLogging) {
      console.log(`User created: ${email}`);
    }

    // Emit event
    this.emit('userCreated', { email, id: user.id });

    // Return safe user data (without password hash)
    const { passwordHash, ...safeUserData } = user;
    return safeUserData;
  }

  /**
   * Get user statistics.
   */
  getUserStats(): { totalUsers: number; activeUsers: number; inactiveUsers: number } {
    const activeUsers = Array.from(this.users.values()).filter(user => user.active).length;

    return {
      totalUsers: this.users.size,
      activeUsers,
      inactiveUsers: this.users.size - activeUsers
    };
  }
}
"""


@pytest.fixture
def complex_code_samples():
    """Complex code samples for advanced testing."""
    return {
        "large_python_module": "\n".join(
            [
                f"class AutoGeneratedClass_{i}:",
                "    def __init__(self):",
                f"        self.value = {i}",
                f"    def method_{i}(self, x):",
                f"        return x * {i}",
                "",
            ]
            for i in range(100)
        ),
        "nested_structures": """
class OuterClass:
    class MiddleClass:
        class InnerClass:
            def deeply_nested_method(self):
                def local_function():
                    def even_deeper():
                        return "deep"
                    return even_deeper()
                return local_function()
""",
        "unicode_heavy": """
# Unicode test: 你好世界 🌍 ñáéíóú àèìòù
def función_unicode(parámetro_ñ: str) -> str:
    \"\"\"Función con caracteres especiales: αβγδε\"\"\"
    variable_ñ = f"Hola, {parámetro_ñ}! 🚀"
    return variable_ñ

class ClaseConÑ:
    def método_tildes(self, données: str) -> str:
        return f"Résultat: {données} ✓"
""",
        "error_prone_code": """
def potentially_buggy_function(data):
    # Potential division by zero
    result = 100 / data.get('count', 0)

    # Potential key error
    user_id = data['user']['id']

    # Potential type error
    return result + user_id
""",
        "performance_heavy": """
def fibonacci_recursive(n):
    if n <= 1:
        return n
    return fibonacci_recursive(n-1) + fibonacci_recursive(n-2)

def inefficient_sort(arr):
    # Bubble sort - O(n²)
    for i in range(len(arr)):
        for j in range(len(arr) - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
""",
    }


# ═══════════════════════════════════════════════════════════════
# File and Data Management Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def temp_files(temp_directory):
    """Create comprehensive temporary files for testing."""
    files = {}

    # Create various code files
    code_samples = {
        "python_simple.py": "def hello(): return 'Hello World'",
        "python_complex.py": """
import os
import sys
from typing import List, Dict

class DataProcessor:
    def __init__(self, config: Dict):
        self.config = config

    def process(self, data: List[Dict]) -> List[Dict]:
        return [self.transform_item(item) for item in data if self.validate_item(item)]

    def validate_item(self, item: Dict) -> bool:
        return 'id' in item and 'value' in item

    def transform_item(self, item: Dict) -> Dict:
        return {'id': item['id'], 'processed_value': item['value'] * 2}
""",
        "java_simple.java": 'public class Hello { public String hello() { return "Hello World"; } }',
        "malformed.py": "def incomplete_function(\n# Missing closing parenthesis and body",
        "empty.py": "",
        "unicode.py": "def función_ñ(): return 'español'",
        "large.py": "\n".join([f"def func_{i}(): return {i}" for i in range(100)]),
    }

    for filename, content in code_samples.items():
        file_path = temp_directory / filename
        file_path.write_text(content, encoding="utf-8")
        files[filename] = str(file_path)

    # Create binary file
    binary_path = temp_directory / "binary.bin"
    binary_path.write_bytes(b"\x00\x01\x02\x03\xFF\xFE\xFD")
    files["binary.bin"] = str(binary_path)

    # Create JSON data files
    json_data = {
        "test_data.json": {
            "users": [
                {"email": "user1@test.com", "password": "password123"},
                {"email": "user2@test.com", "password": "securepass456"},
            ],
        },
        "config.json": {"api_timeout": 30, "max_retries": 3, "enable_logging": True},
    }

    for filename, data in json_data.items():
        file_path = temp_directory / filename
        file_path.write_text(json.dumps(data, indent=2))
        files[filename] = str(file_path)

    return files


@pytest.fixture
def sample_validation_request(temp_files):
    """Enhanced sample validation request for testing."""
    return MigrationValidationRequest(
        source_technology=TechnologyContext(
            type=TechnologyType.PYTHON_FLASK,
            version="2.0",
            framework_details={"framework_variant": "Flask-RESTful"},
        ),
        target_technology=TechnologyContext(
            type=TechnologyType.JAVA_SPRING,
            version="3.0",
            framework_details={"framework_variant": "Spring Boot"},
        ),
        validation_scope=ValidationScope.BUSINESS_LOGIC,
        source_input=InputData(
            type=InputType.CODE_FILES,
            files=[temp_files["python_complex.py"]],
            metadata={"language": "python", "file_count": 1},
        ),
        target_input=InputData(
            type=InputType.CODE_FILES,
            files=[temp_files["java_simple.java"]],
            metadata={"language": "java", "file_count": 1},
        ),
    )


# ═══════════════════════════════════════════════════════════════
# Component Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def migration_validator(mock_llm_service):
    """Enhanced migration validator with comprehensive mocking."""
    with patch("src.core.migration_validator.create_llm_service", return_value=mock_llm_service):
        return MigrationValidator()


@pytest.fixture
def behavioral_crew(mock_llm_service):
    """Enhanced behavioral validation crew."""
    with patch("src.behavioral.crews.create_llm_service", return_value=mock_llm_service):
        return BehavioralValidationCrew(llm_service=mock_llm_service)


@pytest.fixture
def code_analyzer():
    """Code analyzer fixture."""
    tech_context = TechnologyContext(type=TechnologyType.PYTHON_FLASK)
    with patch("src.analyzers.code_analyzer.create_llm_service") as mock_create:
        mock_create.return_value = AsyncMock()
        return CodeAnalyzer(tech_context)


@pytest.fixture
def input_processor():
    """Input processor fixture."""
    return InputProcessor()


@pytest.fixture
def mock_fastapi_client():
    """Enhanced mock FastAPI test client."""
    from fastapi.testclient import TestClient

    # Mock the dependencies before creating the app
    with patch("src.api.routes.MigrationValidator"), \
         patch("src.api.routes.InputProcessor"), \
         patch("src.api.routes.create_behavioral_validation_crew"):

        from src.api.routes import app
        return TestClient(app)


# ═══════════════════════════════════════════════════════════════
# Performance and Monitoring Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def performance_monitor():
    """Performance monitoring fixture."""
    if not PSUTIL_AVAILABLE:
        pytest.skip("psutil not available for performance monitoring")

    class PerformanceMonitor:
        def __init__(self):
            self.process = psutil.Process()
            self.start_time = None
            self.start_memory = None
            self.start_cpu = None

        def start(self):
            self.start_time = time.perf_counter()
            self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            self.start_cpu = self.process.cpu_percent()

        def stop(self):
            if self.start_time is None:
                raise RuntimeError("Monitor not started")

            end_time = time.perf_counter()
            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            end_cpu = self.process.cpu_percent()

            return {
                "execution_time": end_time - self.start_time,
                "memory_used": end_memory - self.start_memory,
                "peak_memory": end_memory,
                "cpu_usage": max(end_cpu - self.start_cpu, 0),
            }

        @contextmanager
        def measure(self):
            self.start()
            try:
                yield self
            finally:
                metrics = self.stop()
                print(f"Performance metrics: {metrics}")

    return PerformanceMonitor()


# ═══════════════════════════════════════════════════════════════
# Test Environment and Cleanup Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup comprehensive test environment variables."""
    original_env = dict(os.environ)

    # Set test environment variables
    test_env = {
        "ENVIRONMENT": "testing",
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
        "TESTING": "true",
        # Disable actual external services
        "OPENAI_API_KEY": "test-key-disabled",
        "ANTHROPIC_API_KEY": "test-key-disabled",
        "GOOGLE_API_KEY": "test-key-disabled",
        # Test-specific configurations
        "SECRET_KEY": "test-secret-key-for-testing-only",
        "TEST_TIMEOUT": "30",
        "MAX_FILE_SIZE_MB": "10",
        "ENABLE_PERFORMANCE_MONITORING": "true",
        "MOCK_EXTERNAL_SERVICES": "true",
        # Database and cache settings for testing
        "DATABASE_URL": "sqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/15",  # Test database
        "CACHE_TTL": "60",
        # Security settings for testing
        "JWT_SECRET_KEY": "test-secret-key-not-for-production",
        "ENCRYPTION_KEY": "test-encryption-key-32-characters-long",
        # Feature flags for testing
        "ENABLE_BEHAVIORAL_VALIDATION": "true",
        "ENABLE_PERFORMANCE_ANALYSIS": "true",
        "ENABLE_SECURITY_ANALYSIS": "true",
        "ENABLE_VISUAL_REGRESSION": "true",
    }

    os.environ.update(test_env)

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def cleanup_resources():
    """Cleanup resources after tests."""
    created_files = []
    opened_connections = []
    background_tasks = []

    class ResourceManager:
        def track_file(self, filepath):
            created_files.append(filepath)

        def track_connection(self, connection):
            opened_connections.append(connection)

        def track_task(self, task):
            background_tasks.append(task)

    resource_manager = ResourceManager()

    yield resource_manager

    # Cleanup
    for filepath in created_files:
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except Exception as e:
            logging.warning(f"Failed to cleanup file {filepath}: {e}")

    for connection in opened_connections:
        try:
            if hasattr(connection, "close"):
                connection.close()
        except Exception as e:
            logging.warning(f"Failed to close connection: {e}")

    for task in background_tasks:
        try:
            if hasattr(task, "cancel"):
                task.cancel()
        except Exception as e:
            logging.warning(f"Failed to cancel task: {e}")


@pytest.fixture
def test_logger():
    """Test-specific logger configuration."""
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add test-specific handler
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# ═══════════════════════════════════════════════════════════════
# Additional Testing Utilities
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def security_test_data():
    """Security testing data fixture."""
    return {
        "valid_api_keys": [
            "amvs_test_key_valid_123456789012345678901234567890",
            "amvs_another_valid_key_098765432109876543210987654321",
        ],
        "invalid_api_keys": [
            "invalid_format_key",
            "amvs_too_short",
            "",
            None,
            "bearer_token_format",
        ],
        "malicious_payloads": [
            {"sql_injection": "'; DROP TABLE users; --"},
            {"xss_payload": "<script>alert('xss')</script>"},
            {"path_traversal": "../../../etc/passwd"},
            {"command_injection": "; rm -rf /"},
        ],
        "large_payloads": {
            "oversized_file": "A" * (11 * 1024 * 1024),  # 11MB file
            "long_string": "B" * 100000,  # 100KB string
        },
    }


# Import datetime here for fixtures that need it
from datetime import datetime

# Mark aliases for convenience
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.behavioral = pytest.mark.behavioral
pytest.mark.performance = pytest.mark.performance
pytest.mark.security = pytest.mark.security
pytest.mark.property = pytest.mark.property
pytest.mark.slow = pytest.mark.slow
pytest.mark.external = pytest.mark.external
pytest.mark.llm = pytest.mark.llm
pytest.mark.browser = pytest.mark.browser
pytest.mark.api = pytest.mark.api
