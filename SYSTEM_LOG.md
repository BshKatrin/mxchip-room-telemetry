# System Log

## 2026-10-31 - README architecture diagram

- Made the HTTP device route and HTTPS browser route explicit through Nginx, with private services, storage retention, and persistence inside the single EC2 boundary. Removed middle-dot separators from the README and diagram; runtime behavior is unchanged.

## 2026-10-21 - Restore Grafana sample timestamps after aggregation

- Diagnosed the apparent September 21-only history: regrouping raw and daily series exposed `_start`/`_stop` as ordinary time columns, so Grafana plotted every reading at the selected range start instead of `_time`. EC2 still held readings on every day from October 3 through October 21, with complete daily summaries through October 20 and successful hourly task runs.
- Limited all three panel results to sample time, value, field, and device, restoring the correct time axis while preserving retention and aggregation. Added a Grafana API regression covering raw-only, summary-only, and mixed ranges across multiple devices; all five isolated InfluxDB/Grafana integration tests passed.
- Deployed the dashboard to EC2 without restarting services. Verified the loaded panels through Grafana over 24-hour, 30-day, and historical absolute ranges: each returns one varying sample-time column. Public HTTP ingestion/HTTPS Grafana health and the production retention/task checks passed.

## 2026-10-15 - Bounded telemetry retention and daily summaries

- Set the raw-data policy to 30 days and introduced daily UTC mean/minimum/maximum/count per device and sensor with 1825-day retention, preserving long-term trends while bounding storage growth.
- Added repeatable InfluxDB provisioning that backfills and independently verifies summaries and a successful task run before shortening existing raw retention. The hourly task recomputes fully retained completed days to handle delayed readings and downtime without a local scheduler.
- Updated Grafana to join older daily means with recent raw readings at a whole UTC day boundary; preserved the existing HTTP ingestion schema and remote Docker architecture.
- Deployed to EC2 after four isolated InfluxDB integration tests passed, covering historical backfill, per-field/device statistics, late writes, repeated provisioning, empty data, failure before retention changes, and partly expired day boundaries. Verified 2009 real raw field values against 144 daily statistics before applying 30-day raw retention; the persisted hourly task passed its test run.
- Verified loaded Grafana queries over one-day and 40-day ranges for all three panels, access to all daily statistics through the datasource, and healthy public HTTPS Grafana/public HTTP ingestion. Temporary test buckets and tasks were removed; existing services required no restart.

## 2026-10-13 - Grafana historical telemetry visibility

- Investigated the apparent 12-hour history limit on EC2: the InfluxDB bucket has infinite retention and still contains readings from 2026-10-03 22:03 UTC (October 4 in Paris). All three live dashboard queries instead hardcoded a six-hour window, ignoring Grafana's selected range.
- Changed temperature, humidity, and pressure queries to use Grafana's selected start and stop times, including historical absolute ranges; expanded the default view to 24 hours. Storage and device ingestion remain unchanged.
- Deployed the provisioning file to EC2; Grafana loaded it automatically without a restart. Authenticated Grafana queries passed for all three panels over 24 hours, seven days, and October 4 (Paris), including readings older than 12 hours. Public HTTP ingestion health remains healthy.

## 2026-10-04 - Public HTTPS dashboard and automatic renewal

- Added a separate HTTPS Compose configuration with a trusted Let's Encrypt IP certificate and secure Grafana session cookies. Public dashboard HTTP redirects to HTTPS; device HTTP ingestion stays unchanged.
- Added persisted ACME account/certificate and HTTP-01 webroot volumes. The base HTTP configuration supports certificate bootstrap before enabling TLS, preventing Nginx startup failures from missing keys.
- Added an EC2 systemd timer that checks renewal twice daily, catches missed runs after reboot, and validates/reloads Nginx after successful Certbot checks. No laptop or Codex runtime is involved.
- Updated deployment docs and AGENTS.md to authorize HTTPS dashboard access through Nginx while keeping database and Grafana container ports private; documented certificate issuance, renewal checks, and firewall requirements.
- Initial outbound HTTPS failures were resolved after security group changes. Issued the production IP certificate (expires 2026-10-10), enabled HTTPS, and passed a staging renewal dry run with Nginx reload. The remote renewal timer is enabled and active.
- HTTPS initially worked only inside EC2. AWS console inspection identified an IPv6-only HTTPS rule (`::/0`); after the user added IPv4 access, public HTTPS Grafana health and public HTTP ingestion health both passed, and HTTP dashboard requests redirect to HTTPS.
- Reconciled the root and firmware READMEs with the deployed behavior; documented IPv4/IPv6 firewall troubleshooting and use of both Compose files for an existing HTTPS deployment.
- Final verification: public HTTPS dashboard and authenticated Grafana datasource queries return the real device's temperature, humidity, and pressure; HTTP API health and dashboard-to-HTTPS redirects pass. Remote Compose/Nginx validation, backend tests, and shell syntax checks pass; the renewal timer remains enabled and active after its scheduled run.

## 2026-10-03 - Replacement EC2 deployment

- Updated ignored runtime and firmware configuration to target the replacement instance through `ssh ec2-aws`; generated fresh InfluxDB and Grafana credentials for its new volumes.
- Removed the Compose source-build dependency and added API restart persistence so the remote stack runs from a prebuilt image after Docker or host restarts.
- Moved Grafana behind a loopback-only proxy listener for SSH access, preserving public HTTP telemetry ingestion and private InfluxDB/Grafana services.
- Firmware now queues its first sensor reading immediately after boot, then retains the 30-minute sample interval, allowing deployment verification without a long initial wait.
- Restored the missing backend uv lockfile required by the Docker build. Backend tests passed.
- Installation initially failed because EC2 outbound HTTP/HTTPS timed out; used a temporary SSH download proxy for provisioning. The legacy MXChip GCC requires Rosetta on this Mac; a native GCC 12 experiment failed against the board SDK headers, so retained the supported GCC 6 toolchain.
- End-to-end verification exposed an out-of-range pressure sensor reading (`256.12 hPa`) that caused HTTP 422 rejection of every sample. Firmware now omits invalid optional pressure values while preserving valid temperature/humidity and the existing schema; pressure hardware/driver diagnosis remains separate.
- Removed macOS AppleDouble metadata files accidentally included in the initial transfer, which Grafana tried to parse as provisioning YAML; subsequent transfers disable that metadata.
- Verification completed on 2026-10-04 (Paris): flashed and verified MXChip; observed HTTP 202 with `stored=true`; queried its real readings directly in InfluxDB and through Grafana. Backend tests, queue test, Compose validation, and Nginx validation passed.
- Removed the temporary build source and download proxy, restarted Docker, and confirmed all four services recovered automatically with device data preserved. Public health responds; public Grafana returns 404 while loopback Grafana works. Direct EC2 outbound HTTPS still times out, affecting future downloads but not current ingestion.

## 2026-06-30 - Grafana pressure visibility

- Added a Grafana time-series panel for `pressure_hpa`, matching the pressure field already emitted by MXChip firmware and stored in InfluxDB.
- Intent: make the dashboard reflect all environmental readings currently sent by the active device payload.

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
