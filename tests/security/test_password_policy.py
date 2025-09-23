"""
Unit tests for password policy module.
Ultra-compressed test implementation for T001 completion.
"""

import pytest
from src.security.password_policy import PasswordPolicy, PasswordValidator, password_validator


class TestPasswordPolicy:
    """Test PasswordPolicy model."""

    def test_default_policy(self):
        """Test default password policy settings."""
        policy = PasswordPolicy()

        assert policy.min_length == 12
        assert policy.require_uppercase is True
        assert policy.require_lowercase is True
        assert policy.require_digits is True
        assert policy.require_special is True
        assert policy.min_special_chars == 1
        assert "password" in policy.forbidden_patterns
        assert policy.max_age_days == 90

    def test_custom_policy(self):
        """Test custom password policy configuration."""
        policy = PasswordPolicy(
            min_length=8,
            require_special=False,
            forbidden_patterns=["admin", "test"]
        )

        assert policy.min_length == 8
        assert policy.require_special is False
        assert policy.forbidden_patterns == ["admin", "test"]


class TestPasswordValidator:
    """Test PasswordValidator class."""

    @pytest.fixture
    def validator(self):
        """Default password validator."""
        return PasswordValidator()

    @pytest.fixture
    def lenient_validator(self):
        """Lenient password validator for testing."""
        policy = PasswordPolicy(min_length=6, require_special=False)
        return PasswordValidator(policy)

    def test_valid_password(self, validator):
        """Test valid password validation."""
        valid, errors = validator.validate_password("MySecurePass123!", "user")

        assert valid is True
        assert len(errors) == 0

    def test_short_password(self, validator):
        """Test password too short."""
        valid, errors = validator.validate_password("Short1!", "user")

        assert valid is False
        assert any("at least 12 characters" in error for error in errors)

    def test_missing_uppercase(self, validator):
        """Test password missing uppercase letter."""
        valid, errors = validator.validate_password("mysecurepass123!", "user")

        assert valid is False
        assert any("uppercase letter" in error for error in errors)

    def test_missing_lowercase(self, validator):
        """Test password missing lowercase letter."""
        valid, errors = validator.validate_password("MYSECUREPASS123!", "user")

        assert valid is False
        assert any("lowercase letter" in error for error in errors)

    def test_missing_digit(self, validator):
        """Test password missing digit."""
        valid, errors = validator.validate_password("MySecurePass!", "user")

        assert valid is False
        assert any("digit" in error for error in errors)

    def test_missing_special_char(self, validator):
        """Test password missing special character."""
        valid, errors = validator.validate_password("MySecurePass123", "user")

        assert valid is False
        assert any("special character" in error for error in errors)

    def test_forbidden_pattern_password(self, validator):
        """Test password containing forbidden pattern."""
        valid, errors = validator.validate_password("MyPassword123!", "user")

        assert valid is False
        assert any("cannot contain 'password'" in error for error in errors)

    def test_forbidden_pattern_admin(self, validator):
        """Test password containing admin pattern."""
        valid, errors = validator.validate_password("AdminPass123!", "user")

        assert valid is False
        assert any("cannot contain 'admin'" in error for error in errors)

    def test_username_similarity(self, validator):
        """Test password containing username."""
        valid, errors = validator.validate_password("MyUserPass123!", "user")

        assert valid is False
        assert any("cannot contain username" in error for error in errors)

    def test_case_insensitive_checks(self, validator):
        """Test case insensitive forbidden pattern checks."""
        valid, errors = validator.validate_password("MyPASSWORD123!", "user")

        assert valid is False
        assert any("cannot contain 'password'" in error for error in errors)

    def test_multiple_special_chars(self, validator):
        """Test password with multiple special characters."""
        policy = PasswordPolicy(min_special_chars=3)
        validator = PasswordValidator(policy)

        # Not enough special chars
        valid, errors = validator.validate_password("MyPassword123!", "user")
        assert valid is False

        # Enough special chars
        valid, errors = validator.validate_password("MyPassword123!@#", "user")
        assert valid is True

    def test_empty_username(self, validator):
        """Test validation with empty username."""
        valid, errors = validator.validate_password("MySecurePass123!", "")

        assert valid is True
        assert len(errors) == 0

    def test_lenient_policy(self, lenient_validator):
        """Test with lenient policy."""
        valid, errors = lenient_validator.validate_password("Simple1", "user")

        assert valid is True
        assert len(errors) == 0

    def test_multiple_errors(self, validator):
        """Test password with multiple validation errors."""
        valid, errors = validator.validate_password("bad", "user")

        assert valid is False
        assert len(errors) >= 4  # Short, no uppercase, no digit, no special

    def test_edge_case_special_chars(self, validator):
        """Test various special characters."""
        special_chars = "!@#$%^&*(),.?\":{}|<>"

        for char in special_chars:
            password = f"MySecurePass123{char}"
            valid, errors = validator.validate_password(password, "user")
            assert valid is True, f"Failed for special char: {char}"

    def test_generate_policy_description(self, validator):
        """Test policy description generation."""
        description = validator.generate_policy_description()

        assert "Minimum 12 characters" in description
        assert "uppercase and lowercase" in description
        assert "at least one digit" in description
        assert "special character" in description
        assert "90 days" in description

    def test_forbidden_patterns_comprehensive(self, validator):
        """Test all default forbidden patterns."""
        forbidden_words = ["password", "admin", "user", "test"]

        for word in forbidden_words:
            password = f"My{word.title()}123!"
            valid, errors = validator.validate_password(password, "testuser")
            assert valid is False
            assert any(f"cannot contain '{word}'" in error for error in errors)


class TestGlobalPasswordValidator:
    """Test global password validator instance."""

    def test_global_instance_exists(self):
        """Test global password validator exists."""
        assert password_validator is not None
        assert isinstance(password_validator, PasswordValidator)

    def test_global_instance_functionality(self):
        """Test global instance basic functionality."""
        valid, errors = password_validator.validate_password("TestPassword123!", "user")

        assert valid is True
        assert len(errors) == 0

    def test_global_instance_policy(self):
        """Test global instance uses default policy."""
        policy = password_validator.policy

        assert policy.min_length == 12
        assert policy.require_uppercase is True
        assert policy.require_lowercase is True


class TestPasswordPolicyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_exactly_min_length(self):
        """Test password exactly at minimum length."""
        policy = PasswordPolicy(min_length=12)
        validator = PasswordValidator(policy)

        # Exactly 12 characters
        valid, errors = validator.validate_password("MyPassword1!", "user")
        assert valid is True

        # 11 characters
        valid, errors = validator.validate_password("MyPassword!", "user")
        assert valid is False

    def test_username_none(self):
        """Test validation with None username."""
        validator = PasswordValidator()
        valid, errors = validator.validate_password("MySecurePass123!", None)

        assert valid is True

    def test_empty_password(self):
        """Test validation with empty password."""
        validator = PasswordValidator()
        valid, errors = validator.validate_password("", "user")

        assert valid is False
        assert len(errors) > 0

    def test_whitespace_password(self):
        """Test password with whitespace."""
        validator = PasswordValidator()

        # Password with spaces
        valid, errors = validator.validate_password("My Secure Pass 123!", "user")
        assert valid is True  # Spaces are allowed

    def test_unicode_characters(self):
        """Test password with unicode characters."""
        validator = PasswordValidator()

        # Unicode special characters
        valid, errors = validator.validate_password("MyPăssword123!", "user")
        assert valid is True