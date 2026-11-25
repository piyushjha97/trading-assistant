from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    kite_api_key: str
    kite_access_token: SecretStr = SecretStr("")
    kite_api_secret: SecretStr = SecretStr("")
    kite_timeout_seconds: float = 10.0
    news_provider: Literal["hypeless", "marketaux", "disabled"] = "hypeless"
    hypeless_api_key: SecretStr = SecretStr("")
    marketaux_api_token: SecretStr = SecretStr("")


@lru_cache
def get_settings() -> Settings:
    return Settings()
