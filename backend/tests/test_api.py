from fastapi.testclient import TestClient

from app.api.routes import get_writer
from app.main import app


class MemoryWriter:
    def __init__(self) -> None:
        self.items = []

    def write(self, telemetry):
        self.items.append(telemetry)
        return True


def test_health():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_ingest_telemetry():
    writer = MemoryWriter()
    app.dependency_overrides[get_writer] = lambda: writer
    client = TestClient(app)

    res = client.post(
        "/api/v1/telemetry",
        json={
            "device_id": "mxchip-devkit-01",
            "temperature_c": 22.4,
            "humidity_percent": 45.0,
            "pressure_hpa": 1012.6,
            "light_lux": 120.0,
        },
    )

    app.dependency_overrides.clear()

    assert res.status_code == 202
    assert res.json()["accepted"] is True
    assert res.json()["stored"] is True
    assert len(writer.items) == 1
