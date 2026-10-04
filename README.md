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
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
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
pio run -c platformio.local.ini --target upload --upload-port /dev/cu.usbmodem11303
pio device monitor --port /dev/cu.usbmodem11303 --baud 115200
```

By default, firmware uses Wi-Fi credentials already stored on the MXChip.
To build with explicit credentials:

```bash
pio run --target upload --upload-port /dev/cu.usbmodem11303 \
  --project-option='build_flags=-D DEVICE_ID=\"mxchip-devkit-01\" -D WIFI_SSID=\"YourSSID\" -D WIFI_PASS=\"YourPassword\" -D BACKEND_HOST=\"your-ec2-public-host-or-domain\" -D BACKEND_PORT=80'
```

Rust firmware logic lives in `mxchip/rust-firmware/`.

```bash
cargo test --manifest-path mxchip/rust-firmware/Cargo.toml
cargo build --manifest-path mxchip/rust-firmware/Cargo.toml --target thumbv7em-none-eabihf
```

## Remote infrastructure

The EC2 runtime is defined in `infra/`.

Follow [infra/README.md](infra/README.md) for first deployment, certificate
issuance, and automatic renewal. Once the certificate is installed, manage the
HTTPS stack with both Compose files:

```bash
cd infra
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d
```

The remote host needs the runtime configuration, provisioning files, and TLS
renewal scripts under `infra/`, a private `.env`, and Docker volumes. Build the
FastAPI image from `backend/` and set `BACKEND_IMAGE` in `infra/.env`.

```bash
docker build -t mxchip-room-telemetry-api:latest backend
```

Public EC2 routes:

- FastAPI: `http://<public-host>/`
- Telemetry ingestion: `http://<public-host>/api/v1/telemetry`
- Grafana: `https://<public-ip>/grafana/` after the HTTPS setup in [infra/README.md](infra/README.md).

The dashboard uses a free Let's Encrypt IP certificate, with automatic renewal
checks twice daily on EC2 and Nginx reloads. No domain or load balancer is required.
The MXChip continues posting over HTTP on port 80.

InfluxDB is bound only to localhost on the EC2 host and can be reached through
an SSH tunnel when needed.

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
