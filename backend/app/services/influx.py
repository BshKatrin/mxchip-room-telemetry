from typing import Protocol

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from app.core.config import get_settings
from app.models.telemetry import TelemetryIn


class TelemetryWriter(Protocol):
    def write(self, telemetry: TelemetryIn) -> bool:
        ...


class InfluxTelemetryWriter:
    def write(self, telemetry: TelemetryIn) -> bool:
        settings = get_settings()
        if not settings.influx_enabled:
            return False

        point = (
            Point("room_environment")
            .tag("device_id", telemetry.device_id)
            .field("temperature_c", telemetry.temperature_c)
            .field("humidity_percent", telemetry.humidity_percent)
            .time(telemetry.timestamp, WritePrecision.NS)
        )

        optional_fields = {
            "pressure_hpa": telemetry.pressure_hpa,
            "light_lux": telemetry.light_lux,
            "co2_ppm": telemetry.co2_ppm,
        }
        for name, value in optional_fields.items():
            if value is not None:
                point.field(name, value)

        try:
            with InfluxDBClient(
                url=settings.influx_url,
                token=settings.influx_token,
                org=settings.influx_org,
            ) as client:
                write_api = client.write_api(write_options=SYNCHRONOUS)
                write_api.write(bucket=settings.influx_bucket, org=settings.influx_org, record=point)
        except Exception:
            return False

        return True


class NoopTelemetryWriter:
    def write(self, telemetry: TelemetryIn) -> bool:
        return False


def get_writer() -> TelemetryWriter:
    return InfluxTelemetryWriter()
