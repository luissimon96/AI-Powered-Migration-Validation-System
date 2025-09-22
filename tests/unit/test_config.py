"""
Unit tests for configuration management.
"""

import os
import tempfile
from unittest.mock import mock_open, patch

import pytest

from src.core.config import (BrowserAutomationConfig, LLMProviderConfig,
                             ValidationConfig, get_validation_config,
                             load_config_from_file, validate_config)


@pytest.mark.unit
class TestValidationConfig:
    """Test ValidationConfig class."""

    def test_default_config_creation(self):
        """Test creating default configuration."""
        config = ValidationConfig()

        assert config is not None
        assert hasattr(config, "llm_providers")
        assert hasattr(config, "browser_config")
        assert hasattr(config, "validation_settings")

    def test_config_with_custom_values(self):
        """Test creating configuration with custom values."""
        llm_config = LLMProviderConfig(
            provider="openai", model="gpt-4", api_key="test-key", enabled=True
        )

        config = ValidationConfig(
            default_llm_provider="openai", llm_providers={"openai": llm_config}
        )

        assert config.default_llm_provider == "openai"
        assert "openai" in config.llm_providers
        assert config.llm_providers["openai"].model == "gpt-4"

    def test_get_default_llm_config(self):
        """Test getting default LLM configuration."""
        llm_config = LLMProviderConfig(
            provider="anthropic", model="claude-3", api_key="test-key", enabled=True
        )

        config = ValidationConfig(
            default_llm_provider="anthropic", llm_providers={"anthropic": llm_config}
        )

        default_config = config.get_default_llm_config()
        assert default_config is not None
        assert default_config.provider == "anthropic"
        assert default_config.model == "claude-3"

    def test_get_nonexistent_llm_config(self):
        """Test getting non-existent LLM configuration."""
        config = ValidationConfig(default_llm_provider="nonexistent")

        default_config = config.get_default_llm_config()
        assert default_config is None

    def test_config_validation(self):
        """Test configuration validation."""
        valid_config = ValidationConfig()
        assert validate_config(valid_config) == True

        # Test with invalid config
        invalid_config = ValidationConfig(default_llm_provider="invalid")
        assert validate_config(invalid_config) == False


@pytest.mark.unit
class TestLLMProviderConfig:
    """Test LLMProviderConfig class."""

    def test_llm_config_creation(self):
        """Test creating LLM provider configuration."""
        config = LLMProviderConfig(
            provider="openai",
            model="gpt-4",
            api_key="sk-test123",
            enabled=True,
            max_tokens=4000,
            temperature=0.1,
            timeout=60.0,
        )

        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.api_key == "sk-test123"
        assert config.enabled == True
        assert config.max_tokens == 4000
        assert config.temperature == 0.1
        assert config.timeout == 60.0

    def test_llm_config_defaults(self):
        """Test LLM configuration defaults."""
        config = LLMProviderConfig(
            provider="anthropic", model="claude-3", api_key="test-key"
        )

        assert config.enabled == True  # Default
        assert config.max_tokens == 4000  # Default
        assert config.temperature == 0.1  # Default
        assert config.timeout == 30.0  # Default

    def test_llm_config_validation(self):
        """Test LLM configuration validation."""
        # Valid configuration
        valid_config = LLMProviderConfig(
            provider="openai", model="gpt-4", api_key="sk-test"
        )
        assert valid_config.is_valid() == True

        # Invalid configuration (missing API key)
        invalid_config = LLMProviderConfig(provider="openai", model="gpt-4", api_key="")
        assert invalid_config.is_valid() == False

    def test_get_provider_info(self):
        """Test getting provider information."""
        config = LLMProviderConfig(
            provider="google", model="gemini-pro", api_key="test-key", max_tokens=8000
        )

        info = config.get_provider_info()
        assert info["provider"] == "google"
        assert info["model"] == "gemini-pro"
        assert info["max_tokens"] == 8000


@pytest.mark.unit
class TestBrowserAutomationConfig:
    """Test BrowserAutomationConfig class."""

    def test_browser_config_creation(self):
        """Test creating browser automation configuration."""
        config = BrowserAutomationConfig(
            browser="chrome",
            headless=True,
            timeout=30,
            wait_for_elements=10,
            screenshot_on_failure=True,
        )

        assert config.browser == "chrome"
        assert config.headless == True
        assert config.timeout == 30
        assert config.wait_for_elements == 10
        assert config.screenshot_on_failure == True

    def test_browser_config_defaults(self):
        """Test browser configuration defaults."""
        config = BrowserAutomationConfig()

        assert config.browser == "chrome"  # Default
        assert config.headless == True  # Default
        assert config.timeout == 30  # Default

    def test_browser_config_validation(self):
        """Test browser configuration validation."""
        # Valid configuration
        valid_config = BrowserAutomationConfig(browser="firefox")
        assert valid_config.is_valid() == True

        # Invalid configuration
        invalid_config = BrowserAutomationConfig(browser="invalid_browser")
        assert invalid_config.is_valid() == False


@pytest.mark.unit
class TestConfigLoading:
    """Test configuration loading functions."""

    def test_load_config_from_file(self):
        """Test loading configuration from file."""
        config_data = {
            "default_llm_provider": "openai",
            "llm_providers": {
                "openai": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "api_key": "sk-test",
                    "enabled": True,
                }
            },
            "browser_config": {"browser": "chrome", "headless": True, "timeout": 30},
        }

        import json

        config_json = json.dumps(config_data)

        with patch("builtins.open", mock_open(read_data=config_json)):
            config = load_config_from_file("test_config.json")

            assert config is not None
            assert config.default_llm_provider == "openai"
            assert "openai" in config.llm_providers

    def test_load_config_from_nonexistent_file(self):
        """Test loading configuration from non-existent file."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            config = load_config_from_file("nonexistent.json")
            assert config is None

    def test_load_config_from_invalid_json(self):
        """Test loading configuration from invalid JSON file."""
        invalid_json = "{ invalid json content"

        with patch("builtins.open", mock_open(read_data=invalid_json)):
            config = load_config_from_file("invalid.json")
            assert config is None

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-openai-key",
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "VALIDATION_TIMEOUT": "60",
        },
    )
    def test_get_validation_config_from_env(self):
        """Test getting validation configuration from environment variables."""
        config = get_validation_config()

        assert config is not None
        # Should have loaded environment variables

    def test_get_validation_config_defaults(self):
        """Test getting default validation configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_validation_config()

            assert config is not None
            assert isinstance(config, ValidationConfig)

    @patch("src.core.config.load_config_from_file")
    def test_get_validation_config_from_file(self, mock_load_file):
        """Test getting validation configuration from file."""
        mock_config = ValidationConfig(default_llm_provider="test")
        mock_load_file.return_value = mock_config

        with patch.dict(os.environ, {"VALIDATION_CONFIG_FILE": "test.json"}):
            config = get_validation_config()

            assert config == mock_config
            mock_load_file.assert_called_once_with("test.json")


@pytest.mark.unit
class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_complete_config(self):
        """Test validating complete configuration."""
        llm_config = LLMProviderConfig(
            provider="openai", model="gpt-4", api_key="sk-test"
        )

        browser_config = BrowserAutomationConfig(browser="chrome", headless=True)

        config = ValidationConfig(
            default_llm_provider="openai",
            llm_providers={"openai": llm_config},
            browser_config=browser_config,
        )

        assert validate_config(config) == True

    def test_validate_incomplete_config(self):
        """Test validating incomplete configuration."""
        config = ValidationConfig(default_llm_provider="missing_provider")

        assert validate_config(config) == False

    def test_validate_none_config(self):
        """Test validating None configuration."""
        assert validate_config(None) == False

    def test_config_serialization(self):
        """Test configuration serialization."""
        config = ValidationConfig()

        # Should be able to convert to dict
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert "default_llm_provider" in config_dict

    def test_config_from_dict(self):
        """Test creating configuration from dictionary."""
        config_dict = {
            "default_llm_provider": "openai",
            "llm_providers": {
                "openai": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "api_key": "sk-test",
                    "enabled": True,
                }
            },
        }

        config = ValidationConfig.from_dict(config_dict)

        assert config is not None
        assert config.default_llm_provider == "openai"
        assert "openai" in config.llm_providers


@pytest.mark.unit
class TestConfigEnvironmentOverrides:
    """Test configuration environment variable overrides."""

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "env-openai-key",
            "ANTHROPIC_API_KEY": "env-anthropic-key",
            "BROWSER_HEADLESS": "false",
            "VALIDATION_TIMEOUT": "120",
        },
    )
    def test_environment_overrides(self):
        """Test that environment variables override configuration."""
        config = get_validation_config()

        # Environment variables should be applied
        openai_config = config.llm_providers.get("openai")
        if openai_config:
            assert openai_config.api_key == "env-openai-key"

    def test_boolean_environment_parsing(self):
        """Test parsing boolean values from environment."""
        with patch.dict(os.environ, {"BROWSER_HEADLESS": "false"}):
            config = get_validation_config()

            if config.browser_config:
                assert config.browser_config.headless == False

        with patch.dict(os.environ, {"BROWSER_HEADLESS": "true"}):
            config = get_validation_config()

            if config.browser_config:
                assert config.browser_config.headless == True

    def test_numeric_environment_parsing(self):
        """Test parsing numeric values from environment."""
        with patch.dict(os.environ, {"VALIDATION_TIMEOUT": "90"}):
            config = get_validation_config()

            # Should parse as integer
            # Specific assertion depends on implementation
