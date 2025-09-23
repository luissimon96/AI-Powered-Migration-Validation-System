from typing import List, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_prefix="SECURITY_",
        # Disable automatic JSON parsing for list fields
        json_schema_serialization_defaults_required=True,
        json_encoders={}
    )

    SECRET_KEY: str = "super-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_HOSTS: str = "*"
    CORS_ORIGINS: str = "*"
    RATE_LIMIT_PER_MINUTE: int = 100
    MAX_UPLOAD_FILE_SIZE: int = 5 * 1024 * 1024  # 5 MB
    MAX_UPLOAD_FILES_PER_REQUEST: int = 5

    @property
    def allowed_hosts_list(self) -> List[str]:
        if self.ALLOWED_HOSTS == "*":
            return ["*"]
        return [host.strip() for host in self.ALLOWED_HOSTS.split(',') if host.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]


security_settings = SecuritySettings()
