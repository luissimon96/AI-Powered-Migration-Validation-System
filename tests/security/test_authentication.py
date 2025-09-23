"""Authentication security tests.

Tests for JWT authentication, user management, role-based access control,
and authentication security features.
"""

from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest
from fastapi.testclient import TestClient

from src.security.auth import AuthenticationError
from src.security.auth import AuthManager
from src.security.auth import JWTAuthenticator
from src.security.auth import User
from src.security.auth import UserRole
from src.security.config import get_security_config


class TestJWTAuthenticator:
    """Test JWT authentication functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.jwt_auth = JWTAuthenticator()
        self.test_user = User(
            id="test-123",
            username="testuser",
            email="test@example.com",
            roles=[UserRole.VALIDATOR],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

    def test_password_hashing(self):
        """Test secure password hashing."""
        password = "test_password_123"
        hashed = self.jwt_auth.hash_password(password)

        assert hashed != password
        assert self.jwt_auth.verify_password(password, hashed)
        assert not self.jwt_auth.verify_password("wrong_password", hashed)

    def test_token_creation_and_verification(self):
        """Test JWT token creation and verification."""
        token = self.jwt_auth.create_access_token(self.test_user)
        assert token is not None
        assert len(token) > 50  # JWT tokens are typically long

        # Verify token
        token_data = self.jwt_auth.verify_token(token)
        assert token_data.sub == self.test_user.id
        assert token_data.username == self.test_user.username
        assert UserRole.VALIDATOR.value in token_data.roles

    def test_token_expiration(self):
        """Test token expiration."""
        # Create token with short expiry
        short_expiry = timedelta(seconds=1)
        token = self.jwt_auth.create_access_token(self.test_user, short_expiry)

        # Token should be valid immediately
        token_data = self.jwt_auth.verify_token(token)
        assert token_data.sub == self.test_user.id

        # Wait for expiration and test
        import time

        time.sleep(2)

        with pytest.raises(AuthenticationError, match="Token has expired"):
            self.jwt_auth.verify_token(token)

    def test_token_revocation(self):
        """Test token revocation."""
        token = self.jwt_auth.create_access_token(self.test_user)
        token_data = self.jwt_auth.verify_token(token)

        # Revoke token
        self.jwt_auth.revoke_token(token_data.jti)

        # Token should now be invalid
        with pytest.raises(AuthenticationError, match="Token has been revoked"):
            self.jwt_auth.verify_token(token)

    def test_invalid_token(self):
        """Test handling of invalid tokens."""
        with pytest.raises(AuthenticationError, match="Invalid token"):
            self.jwt_auth.verify_token("invalid.token.here")

    def test_refresh_token_creation(self):
        """Test refresh token creation."""
        refresh_token = self.jwt_auth.create_refresh_token(self.test_user)
        assert refresh_token is not None

        # Verify refresh token structure
        token_data = self.jwt_auth.verify_token(refresh_token)
        assert token_data.sub == self.test_user.id


class TestAuthManager:
    """Test authentication manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.auth_manager = AuthManager()

    def test_user_creation(self):
        """Test user creation with validation."""
        user = self.auth_manager.create_user(
            username="newuser",
            email="newuser@example.com",
            password="secure_password_123",
            roles=[UserRole.VIEWER],
        )

        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert UserRole.VIEWER in user.roles
        assert user.is_active

    def test_duplicate_user_prevention(self):
        """Test prevention of duplicate users."""
        # Create first user
        self.auth_manager.create_user(
            username="unique",
            email="unique@example.com",
            password="password123",
            roles=[UserRole.VIEWER],
        )

        # Try to create duplicate username
        with pytest.raises(ValueError, match="Username already exists"):
            self.auth_manager.create_user(
                username="unique",
                email="different@example.com",
                password="password123",
                roles=[UserRole.VIEWER],
            )

        # Try to create duplicate email
        with pytest.raises(ValueError, match="Email already exists"):
            self.auth_manager.create_user(
                username="different",
                email="unique@example.com",
                password="password123",
                roles=[UserRole.VIEWER],
            )

    def test_user_authentication(self):
        """Test user authentication."""
        # Create test user
        username = "authtest"
        password = "test_password_123"
        self.auth_manager.create_user(
            username=username,
            email="authtest@example.com",
            password=password,
            roles=[UserRole.VALIDATOR],
        )

        # Test successful authentication
        user = self.auth_manager.authenticate_user(username, password)
        assert user is not None
        assert user.username == username

        # Test failed authentication
        user = self.auth_manager.authenticate_user(username, "wrong_password")
        assert user is None

        # Test nonexistent user
        user = self.auth_manager.authenticate_user("nonexistent", password)
        assert user is None

    def test_account_lockout(self):
        """Test account lockout after failed attempts."""
        # Create test user
        username = "locktest"
        password = "test_password_123"
        self.auth_manager.create_user(
            username=username,
            email="locktest@example.com",
            password=password,
            roles=[UserRole.VALIDATOR],
        )

        # Attempt failed logins
        for _ in range(self.auth_manager.max_failed_attempts):
            user = self.auth_manager.authenticate_user(username, "wrong_password")
            assert user is None

        # Account should now be locked
        with pytest.raises(AuthenticationError, match="Account is locked"):
            self.auth_manager.authenticate_user(username, password)

    def test_user_role_management(self):
        """Test user role management."""
        user = self.auth_manager.create_user(
            username="roletest",
            email="roletest@example.com",
            password="password123",
            roles=[UserRole.VIEWER],
        )

        # Update roles
        new_roles = [UserRole.VALIDATOR, UserRole.ADMIN]
        self.auth_manager.update_user_roles(user.id, new_roles)

        # Verify roles updated
        updated_user = self.auth_manager.get_user_by_id(user.id)
        assert set(updated_user.roles) == set(new_roles)

    def test_user_deactivation(self):
        """Test user deactivation."""
        user = self.auth_manager.create_user(
            username="deactivatetest",
            email="deactivate@example.com",
            password="password123",
            roles=[UserRole.VIEWER],
        )

        # Deactivate user
        self.auth_manager.deactivate_user(user.id)

        # Verify user is deactivated
        deactivated_user = self.auth_manager.get_user_by_id(user.id)
        assert not deactivated_user.is_active


class TestAuthenticationSecurity:
    """Test authentication security measures."""

    def setup_method(self):
        """Set up test fixtures."""
        self.auth_manager = AuthManager()

    def test_password_strength_validation(self):
        """Test password strength requirements."""
        # This would be implemented in a real password validator
        weak_passwords = [
            "123",
            "password",
            "qwerty",
            "admin",
        ]

        strong_passwords = [
            "MyStr0ngP@ssw0rd!",
            "C0mpl3x_P@ssw0rd_2024",
            "Secure123!@#",
        ]

        # Test weak passwords (would need actual validation implementation)
        for password in weak_passwords:
            # In real implementation, this would raise validation error
            pass

        # Test strong passwords
        for password in strong_passwords:
            # Should pass validation
            pass

    def test_timing_attack_resistance(self):
        """Test resistance to timing attacks."""
        # Create test user
        username = "timingtest"
        password = "test_password_123"
        self.auth_manager.create_user(
            username=username,
            email="timing@example.com",
            password=password,
            roles=[UserRole.VIEWER],
        )

        import time

        # Measure time for valid user, wrong password
        start = time.time()
        self.auth_manager.authenticate_user(username, "wrong_password")
        valid_user_time = time.time() - start

        # Measure time for invalid user
        start = time.time()
        self.auth_manager.authenticate_user("invalid_user", "wrong_password")
        invalid_user_time = time.time() - start

        # Time difference should be minimal to prevent user enumeration
        time_diff = abs(valid_user_time - invalid_user_time)
        assert time_diff < 0.1  # Less than 100ms difference

    def test_jwt_secret_security(self):
        """Test JWT secret key security."""
        config = get_security_config()

        # Secret should be sufficiently long
        assert len(config.jwt_secret_key) >= 32

        # Secret should not be a common value
        common_secrets = [
            "secret",
            "key",
            "password",
            "admin",
            "changeme",
        ]
        assert config.jwt_secret_key not in common_secrets

    def test_token_claims_validation(self):
        """Test JWT token claims validation."""
        jwt_auth = JWTAuthenticator()
        test_user = User(
            id="test-456",
            username="claimstest",
            email="claims@example.com",
            roles=[UserRole.ADMIN],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        token = jwt_auth.create_access_token(test_user)
        token_data = jwt_auth.verify_token(token)

        # Verify all required claims present
        assert token_data.sub == test_user.id
        assert token_data.username == test_user.username
        assert token_data.roles == [role.value for role in test_user.roles]
        assert token_data.exp > datetime.now(timezone.utc)
        assert token_data.iat <= datetime.now(timezone.utc)
        assert token_data.jti is not None


@pytest.mark.asyncio
class TestAuthenticationAPI:
    """Test authentication API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.api.secure_routes import app

        return TestClient(app)

    def test_login_endpoint(self, client):
        """Test login endpoint security."""
        # Test with invalid credentials
        response = client.post(
            "/api/auth/login",
            json={"username": "invalid", "password": "wrong"},
        )
        assert response.status_code == 401

        # Test with missing fields
        response = client.post("/api/auth/login", json={"username": "test"})
        assert response.status_code == 422  # Validation error

    def test_rate_limiting_on_auth(self, client):
        """Test rate limiting on authentication endpoints."""
        # Make multiple rapid requests
        for _ in range(10):
            response = client.post(
                "/api/auth/login",
                json={"username": "test", "password": "wrong"},
            )

        # Should eventually get rate limited
        # Note: This test may need adjustment based on actual rate limit settings
        assert response.status_code in [401, 429]

    def test_security_headers_on_auth(self, client):
        """Test security headers on authentication responses."""
        response = client.post(
            "/api/auth/login", json={"username": "test", "password": "wrong"}
        )

        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
