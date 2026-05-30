# mxchip-room-telemetry

MXChip room telemetry system split into device firmware, backend service, and
remote infrastructure modules.

Flow:

```text
MXChip -> HTTP POST -> FastAPI -> InfluxDB -> Grafana
```

On device:

```text
Rust sensor logic -> UART JSON line -> C networking -> HTTP POST
```

## Repository layout

```text
mxchip/   PlatformIO C/C++ firmware plus Rust sensor/data-prep crate
backend/  FastAPI telemetry ingestion service
infra/    EC2 Docker Compose runtime for API, InfluxDB, and Grafana
```

## Backend local development

```bash
docker compose --env-file infra/.env.example -f infra/docker-compose.yml up -d influxdb
uv run --project backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

URLs:

- FastAPI: http://localhost:8000/docs

Post test payload:

```bash
curl -X POST http://localhost:8000/api/v1/telemetry \
  -H 'Content-Type: application/json' \
  -d '{"device_id":"mxchip-devkit-01","temperature_c":22.4,"humidity_percent":45.0,"pressure_hpa":1012.6,"light_lux":120}'
```

## Firmware

C firmware lives in `mxchip/src/`.

```bash
cd mxchip
pio run
pio run --target upload --upload-port /dev/cu.usbmodem11403
pio device monitor --port /dev/cu.usbmodem11403 --baud 115200
```

By default, firmware uses Wi-Fi credentials already stored on the MXChip.
To build with explicit credentials:

```bash
pio run --target upload --upload-port /dev/cu.usbmodem11403 \
  --project-option='build_flags=-D DEVICE_ID=\"mxchip-devkit-01\" -D WIFI_SSID=\"YourSSID\" -D WIFI_PASS=\"YourPassword\" -D BACKEND_HOST=\"192.168.1.25\"'
```

Rust firmware logic lives in `mxchip/rust-firmware/`.

```bash
cargo test --manifest-path mxchip/rust-firmware/Cargo.toml
cargo build --manifest-path mxchip/rust-firmware/Cargo.toml --target thumbv7em-none-eabihf
```

## Remote infrastructure

The EC2 runtime is defined in `infra/`.

```bash
cd infra
cp .env.example .env
docker compose --env-file .env up -d
```

The remote host should only need `infra/docker-compose.yml`, `infra/.env`, the
Grafana provisioning files under `infra/grafana/`, and Docker volumes. Build the
FastAPI image from `backend/` and set `BACKEND_IMAGE` in `infra/.env`.

```bash
docker build -t mxchip-room-telemetry-api:latest backend
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
