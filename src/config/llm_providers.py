from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class LLMProviderSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_prefix="LLM_")

    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None # Added
    DEFAULT_MODEL_OPENAI: str = "gpt-4-turbo-preview"
    DEFAULT_MODEL_ANTHROPIC: str = "claude-3-sonnet-20240229"
    DEFAULT_MODEL_GOOGLE: str = "gemini-pro"
    DEFAULT_MODEL_OPENROUTER: str = "mistralai/mistral-7b-instruct" # Added
    DEFAULT_TEMPERATURE: float = 0.1
    DEFAULT_MAX_TOKENS: int = 4000
    DEFAULT_TIMEOUT: float = 60.0


llm_provider_settings = LLMProviderSettings()
