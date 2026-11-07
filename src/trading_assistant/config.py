from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    kite_api_key: str
    kite_access_token: SecretStr
    kite_timeout_seconds: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
