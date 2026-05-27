# mxchip-room-telemetry

Local-first MXChip room telemetry scaffold.

Flow:

```text
MXChip -> HTTP POST -> FastAPI -> InfluxDB -> Grafana
```

On device:

```text
Rust sensor logic -> UART JSON line -> C networking -> HTTP POST
```

## Quick start backend

```bash
docker compose up -d influxdb grafana
uv run --project backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

URLs:

- FastAPI: http://localhost:8000/docs
- InfluxDB: http://localhost:8086
- Grafana: http://localhost:3000 (`admin` / `admin`)

Post test payload:

```bash
curl -X POST http://localhost:8000/api/v1/telemetry \
  -H 'Content-Type: application/json' \
  -d '{"device_id":"mxchip-devkit-01","temperature_c":22.4,"humidity_percent":45.0,"pressure_hpa":1012.6,"light_lux":120}'
```

## Firmware

C firmware lives in `src/`.

```bash
pio run
pio run --target upload
pio device monitor --baud 115200
```

Rust firmware logic lives in `rust-firmware/`.

```bash
cargo test --manifest-path rust-firmware/Cargo.toml
cargo build --manifest-path rust-firmware/Cargo.toml --target thumbv7em-none-eabihf
```

## Telemetry JSON

Required:

- `device_id`
- `temperature_c`
- `humidity_percent`

Optional:

- `pressure_hpa`
- `light_lux`
- `co2_ppm`
- `timestamp`
