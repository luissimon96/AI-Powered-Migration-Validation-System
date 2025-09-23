"""Password policy enforcement for S002 authentication system.
Ultra-compressed implementation with essential security policies.
"""

import re
from typing import List, Tuple

from pydantic import BaseModel


class PasswordPolicy(BaseModel):
    """Password policy configuration."""

    min_length: int = 12
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special: bool = True
    min_special_chars: int = 1
    forbidden_patterns: List[str] = ["password", "admin", "user", "test"]
    max_age_days: int = 90


class PasswordValidator:
    """Password policy validator."""

    def __init__(self, policy: PasswordPolicy = None):
        self.policy = policy or PasswordPolicy()

    def validate_password(self, password: str,
                          username: str = "") -> Tuple[bool, List[str]]:
        """Validate password against policy. Returns (is_valid, errors)."""
        errors = []

        # Length check
        if len(password) < self.policy.min_length:
            errors.append(
                f"Password must be at least {
                    self.policy.min_length} characters")

        # Character requirements
        if self.policy.require_uppercase and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        if self.policy.require_lowercase and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        if self.policy.require_digits and not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")

        if self.policy.require_special:
            special_chars = re.findall(r'[!@#$%^&*(),.?":{}|<>]', password)
            if len(special_chars) < self.policy.min_special_chars:
                errors.append(
                    f"Password must contain at least {
                        self.policy.min_special_chars} special character(s)")

        # Forbidden patterns
        password_lower = password.lower()
        for pattern in self.policy.forbidden_patterns:
            if pattern.lower() in password_lower:
                errors.append(f"Password cannot contain '{pattern}'")

        # Username similarity
        if username and username.lower() in password_lower:
            errors.append("Password cannot contain username")

        return len(errors) == 0, errors

    def generate_policy_description(self) -> str:
        """Generate human-readable policy description."""
        return f"""Password Requirements:
• Minimum {self.policy.min_length} characters
• Contains uppercase and lowercase letters
• Contains at least one digit
• Contains at least {self.policy.min_special_chars} special character(s)
• Does not contain common patterns or username
• Maximum age: {self.policy.max_age_days} days"""


# Global password validator
password_validator = PasswordValidator()
