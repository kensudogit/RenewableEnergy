from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
_LOCAL_ENV = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), str(_LOCAL_ENV), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://re_user:re_password@localhost:5434/re_db"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"
    default_region: str = "tokyo"
    default_horizon_hours: int = 48

    # Auto trading / live market gateway
    autotrade_enabled: bool = False
    trading_default_mode: str = "paper"  # paper | live
    broker_api_url: str = ""  # e.g. https://gateway.example.com/v1/orders
    broker_api_key: str = ""
    broker_account_id: str = ""
    live_trading_confirm: str = ""  # must be "I_UNDERSTAND_LIVE_RISK" to allow live

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def live_trading_allowed(self) -> bool:
        return (
            bool(self.broker_api_url.strip())
            and bool(self.broker_api_key.strip())
            and self.live_trading_confirm.strip() == "I_UNDERSTAND_LIVE_RISK"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
