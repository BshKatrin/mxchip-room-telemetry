from fastapi import APIRouter, Depends, status

from app.core.config import Settings, get_settings
from app.models.telemetry import TelemetryIn, TelemetryOut
from app.services.influx import TelemetryWriter, get_writer

router = APIRouter()


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return {
        "status": "ok",
        "influx_enabled": settings.influx_enabled,
    }


@router.post(
    "/api/v1/telemetry",
    response_model=TelemetryOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_telemetry(
    payload: TelemetryIn,
    writer: TelemetryWriter = Depends(get_writer),
) -> TelemetryOut:
    stored = writer.write(payload)
    return TelemetryOut(accepted=True, stored=stored, telemetry=payload)
