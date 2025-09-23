
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_prefix="DB_")

    DATABASE_URL: str = "sqlite:///./sql_app.db"
    POOL_SIZE: int = 10
    MAX_OVERFLOW: int = 20
    ECHO_SQL: bool = False


database_settings = DatabaseSettings()
