import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "mxchip-room-telemetry"
    influx_url: str = "http://localhost:8086"
    influx_token: str = "dev-token"
    influx_org: str = "mxchip"
    influx_bucket: str = "room_telemetry"
    influx_enabled: bool = True


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", Settings.model_fields["app_name"].default),
        influx_url=os.getenv("INFLUX_URL", Settings.model_fields["influx_url"].default),
        influx_token=os.getenv("INFLUX_TOKEN", Settings.model_fields["influx_token"].default),
        influx_org=os.getenv("INFLUX_ORG", Settings.model_fields["influx_org"].default),
        influx_bucket=os.getenv("INFLUX_BUCKET", Settings.model_fields["influx_bucket"].default),
        influx_enabled=_bool_env("INFLUX_ENABLED", True),
    )
