from datetime import datetime, timezone

from pydantic import BaseModel, Field


class TelemetryIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    temperature_c: float = Field(ge=-40.0, le=125.0)
    humidity_percent: float = Field(ge=0.0, le=100.0)
    pressure_hpa: float | None = Field(default=None, ge=300.0, le=1200.0)
    light_lux: float | None = Field(default=None, ge=0.0)
    co2_ppm: float | None = Field(default=None, ge=0.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TelemetryOut(BaseModel):
    accepted: bool
    stored: bool
    telemetry: TelemetryIn
