# Backend

FastAPI ingestion service for MXChip room telemetry.

## Run locally

From repo root:

```bash
uv run --project backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health:

```bash
curl http://localhost:8000/health
```

Post sample telemetry:

```bash
curl -X POST http://localhost:8000/api/v1/telemetry \
  -H 'Content-Type: application/json' \
  -d '{"device_id":"mxchip-devkit-01","temperature_c":22.4,"humidity_percent":45.0,"pressure_hpa":1012.6,"light_lux":120}'
```

## Config

Env vars:

- `INFLUX_URL`
- `INFLUX_TOKEN`
- `INFLUX_ORG`
- `INFLUX_BUCKET`
- `INFLUX_ENABLED`
