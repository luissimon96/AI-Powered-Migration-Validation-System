from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_prefix="SECURITY_")

    SECRET_KEY: str = "super-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = ["*"]
    RATE_LIMIT_PER_MINUTE: int = 100
    MAX_UPLOAD_FILE_SIZE: int = 5 * 1024 * 1024  # 5 MB
    MAX_UPLOAD_FILES_PER_REQUEST: int = 5


security_settings = SecuritySettings()
