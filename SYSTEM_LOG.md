# System Log

## 2026-05-30 - Public host scrub for GitHub

- Replaced committed EC2 IP references with `<public-host>` or `your-ec2-public-host-or-domain` placeholders.
- Kept the real EC2 host as private runtime configuration in ignored `.env` files or PlatformIO build flags.

## 2026-05-30 - Public Nginx entrypoint for EC2

- Added Nginx to the remote Compose stack as the public HTTP entrypoint for FastAPI and Grafana.
- Routed FastAPI at `http://<public-host>/` and Grafana at `http://<public-host>/grafana/`.
- Kept InfluxDB private by binding it to `127.0.0.1:8086` on the EC2 host only for SSH-tunnel access.
- Updated MXChip PlatformIO build flags so telemetry posts to EC2 over public HTTP port 80.

## 2026-05-30 - Repository module split for remote deployment

- Moved device firmware into `mxchip/`, keeping PlatformIO C/C++ firmware and Rust sensor/data-prep crate together as one device module.
- Moved Docker Compose and Grafana provisioning into `infra/` so EC2 deployment assets are isolated from source modules.
- Changed Compose to a remote-centric stack with public FastAPI only; InfluxDB and Grafana no longer publish host ports and persist through Docker volumes.
- Added backend Docker image build files so the remote stack can run from `BACKEND_IMAGE` without requiring backend source on the instance.
- Updated READMEs with new module paths, image build command, and EC2 runtime flow.
- Verification: backend tests, host C queue test, Compose config render, PlatformIO build from `mxchip/`, and backend Docker image build passed.
- Blocked checks: `cargo` was not available on `PATH`, so Rust firmware tests were not run.

## 2026-05-28 - Workable telemetry scaffold

- Implemented local-first backend scaffold preserving `HTTP -> FastAPI -> InfluxDB -> Grafana`.
- Added `POST /api/v1/telemetry` with stable JSON payload fields: `device_id`, `temperature_c`, `humidity_percent`, optional `pressure_hpa`, `light_lux`, `co2_ppm`, `timestamp`.
- Added InfluxDB writer for `room_environment` measurement; write failures return `stored=false` instead of failing ingestion, so backend remains responsive while DB is offline.
- Added Docker Compose for InfluxDB and Grafana plus Grafana datasource/dashboard provisioning for temperature and humidity.
- Added C firmware scaffold for MXChip: periodic sampling loop, UART JSON input from Rust layer, HTTP POST boundary, fixed-size retry queue with exponential backoff, fallback sample payload.
- Added Rust `no_std` sensor logic crate that builds bounded JSON payloads with `heapless`, keeping computation/data prep separate from C hardware/networking layer.
- Added focused tests for FastAPI ingestion and C retry queue behavior.
- Updated repo docs with backend, firmware, telemetry, and local run commands.
- Verification: `uv run --project backend pytest` passed; host C queue test via `cc` passed.
- Blocked checks: `cargo` and `pio` were not available on `PATH`, so Rust firmware tests/build and PlatformIO build/upload were not run. MXChip serial port was detected at `/dev/cu.usbmodem11403`.

## 2026-05-30 - Backend import path fix

- Fixed backend packaging so `uv run --project backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` can import `app` when executed from repo root.
- Intent: keep documented repo-root command working without requiring callers to `cd backend` or set `PYTHONPATH`.

## 2026-05-30 - MXChip send path implementation

- Switched firmware environment from raw STM32Cube scaffold to MXChip Arduino framework because PlatformIO provides board-specific Wi-Fi, screen, sensor, and HTTP APIs there.
- Populated device-side functions: board init, Wi-Fi connect, sensor payload creation, HTTP POST, UART JSON line read, serial debug logging.
- Firmware now reads HTS221/LPS22HB values through DevKit APIs, builds stable telemetry JSON, queues it, and posts to FastAPI over HTTP.
- Wi-Fi uses credentials already stored on the device by default; optional `WIFI_SSID`, `WIFI_PASS`, `BACKEND_HOST` build flags can override at build time.
- Added serial logging for queued payload, POST URL, HTTP status, and response body to debug what MXChip sends.
- First upload succeeded over ST-Link. Serial showed sensor payload generation and HTTP attempts; initial build still targeted fallback host, so backend host was moved into `platformio.ini`.
- Replaced MXChip `HTTPClient` POST with raw `WiFiClient` HTTP because the bundled client appends an extra CRLF after the body; uvicorn accepted the telemetry but then emitted a follow-on `400 Invalid HTTP request`, causing duplicate retries.
- Verified on hardware after upload: MXChip posted telemetry to the local backend, received repeated `HTTP/1.1 202 Accepted`, and logged `telemetry posted`.
