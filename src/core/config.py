"""Configuration management for AI-Powered Migration Validation System.

Handles environment variables, LLM provider settings, and system configuration.
"""

import logging
import os
import tempfile
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

logger = structlog.get_logger(__name__) if STRUCTLOG_AVAILABLE else None


class Environment(Enum):
    """Application environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


@dataclass
class LLMProviderConfig:
    """Configuration for LLM providers."""

    provider: str
    model: str
    api_key: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.1
    timeout: float = 60.0
    enabled: bool = True


class SystemSettings(BaseSettings):
    """System-wide settings using Pydantic BaseSettings."""

    # Environment
    environment: str = Environment.DEVELOPMENT.value
    debug: bool = False

    # API Settings
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_workers: int = 1
    cors_origins: list = field(default_factory=lambda: ["*"])

    # File Upload Settings
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_files_per_request: int = 20
    upload_dir: str = os.path.join(tempfile.gettempdir(), "migration_validator_uploads")

    # LLM Settings
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4-turbo-preview"
    llm_timeout: float = 60.0
    llm_max_tokens: int = 4000
    llm_temperature: float = 0.1

    # OpenAI Settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    openai_enabled: bool = True

    # Anthropic Settings
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    anthropic_enabled: bool = True

    # Google Settings
    google_api_key: Optional[str] = None
    google_model: str = "gemini-pro"
    google_enabled: bool = True

    # Security Settings
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30

    # Database Settings (optional)
    database_url: Optional[str] = None

    # Redis Settings for P001 async processing
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_enabled: bool = True

    # Celery Settings
    celery_worker_concurrency: int = 4
    celery_task_time_limit: int = 1800  # 30 minutes
    celery_task_soft_time_limit: int = 1500  # 25 minutes

    # Performance Settings
    async_concurrency_limit: int = 10
    request_timeout: float = 300.0

    # Cache Settings
    cache_ttl: int = 3600  # 1 hour
    cache_enabled: bool = True

    # Logging Settings
    log_level: str = "INFO"
    log_format: str = "json"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"


class ValidationConfig:
    """Configuration for migration validation behavior."""

    def __init__(self, settings: SystemSettings):
        self.settings = settings
        self.llm_providers = self._initialize_llm_providers()

    # Redis configuration properties
    @property
    def redis_host(self) -> str:
        """Redis host for task queue and caching."""
        return self.settings.redis_host

    @property
    def redis_port(self) -> int:
        """Redis port."""
        return self.settings.redis_port

    @property
    def redis_db(self) -> int:
        """Redis database number."""
        return self.settings.redis_db

    @property
    def celery_broker_url(self) -> str:
        """Celery broker URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_result_backend(self) -> str:
        """Celery result backend URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def _initialize_llm_providers(self) -> Dict[str, LLMProviderConfig]:
        """Initialize LLM provider configurations."""
        providers = {}

        # OpenAI Configuration
        if self.settings.openai_enabled:
            providers["openai"] = LLMProviderConfig(
                provider="openai",
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key or os.getenv("OPENAI_API_KEY"),
                max_tokens=self.settings.llm_max_tokens,
                temperature=self.settings.llm_temperature,
                timeout=self.settings.llm_timeout,
                enabled=self.settings.openai_enabled,
            )

        # Anthropic Configuration
        if self.settings.anthropic_enabled:
            providers["anthropic"] = LLMProviderConfig(
                provider="anthropic",
                model=self.settings.anthropic_model,
                api_key=self.settings.anthropic_api_key
                or os.getenv("ANTHROPIC_API_KEY"),
                max_tokens=self.settings.llm_max_tokens,
                temperature=self.settings.llm_temperature,
                timeout=self.settings.llm_timeout,
                enabled=self.settings.anthropic_enabled,
            )

        # Google Configuration
        if self.settings.google_enabled:
            providers["google"] = LLMProviderConfig(
                provider="google",
                model=self.settings.google_model,
                api_key=self.settings.google_api_key or os.getenv("GOOGLE_API_KEY"),
                max_tokens=self.settings.llm_max_tokens,
                temperature=self.settings.llm_temperature,
                timeout=self.settings.llm_timeout,
                enabled=self.settings.google_enabled,
            )

        return providers

    def get_default_llm_config(self) -> Optional[LLMProviderConfig]:
        """Get default LLM provider configuration."""
        default_provider = self.settings.default_llm_provider

        if default_provider in self.llm_providers:
            config = self.llm_providers[default_provider]
            if config.enabled and config.api_key:
                return config

        # Fallback to first available provider
        for provider_config in self.llm_providers.values():
            if provider_config.enabled and provider_config.api_key:
                logger.info(
                    "Using fallback LLM provider",
                    provider=provider_config.provider,
                    default_requested=default_provider,
                )
                return provider_config

        logger.warning("No LLM provider available with valid API key")
        return None

    def get_llm_config(self, provider: str) -> Optional[LLMProviderConfig]:
        """Get specific LLM provider configuration."""
        return self.llm_providers.get(provider)

    def list_available_providers(self) -> List[str]:
        """List available LLM providers."""
        return [
            name
            for name, config in self.llm_providers.items()
            if config.enabled and config.api_key
        ]


# Global settings instance
_settings: Optional[SystemSettings] = None
_validation_config: Optional[ValidationConfig] = None


def get_settings() -> SystemSettings:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = SystemSettings()

        # Configure logging
        if STRUCTLOG_AVAILABLE:
            import structlog

            structlog.configure(
                processors=[
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.add_log_level,
                    structlog.processors.StackInfoRenderer(),
                    (
                        structlog.dev.ConsoleRenderer()
                        if _settings.environment == "development"
                        else structlog.processors.JSONRenderer()
                    ),
                ],
                wrapper_class=structlog.make_filtering_bound_logger(
                    getattr(logging, _settings.log_level.upper(), logging.INFO)
                ),
                context_class=dict,
                logger_factory=structlog.PrintLoggerFactory(),
                cache_logger_on_first_use=True,
            )

    return _settings


def get_validation_config() -> ValidationConfig:
    """Get global validation configuration."""
    global _validation_config
    if _validation_config is None:
        _validation_config = ValidationConfig(get_settings())
    return _validation_config


def reload_config():
    """Reload configuration from environment."""
    global _settings, _validation_config
    _settings = None
    _validation_config = None
    return get_settings(), get_validation_config()


# Environment-specific configuration helpers
def is_development() -> bool:
    """Check if running in development environment."""
    return get_settings().environment == Environment.DEVELOPMENT.value


def is_production() -> bool:
    """Check if running in production environment."""
    return get_settings().environment == Environment.PRODUCTION.value


def is_testing() -> bool:
    """Check if running in testing environment."""
    return get_settings().environment == Environment.TESTING.value
