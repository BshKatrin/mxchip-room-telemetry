# System Log

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
