# Setup and telemetry

Run commands below from the repository root. The production system runs on EC2;
local development is optional. Use Python 3.13+ and `uv` for the backend.

## Local API without storage

```bash
INFLUX_ENABLED=false uv run --project backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open [API docs](http://localhost:8000/docs) or check
`curl http://localhost:8000/health`. This mode validates payloads but does not
persist them: valid requests return `202` with `accepted=true, stored=false`.

The following values are synthetic, not measurements from the room:

```bash
curl -X POST http://localhost:8000/api/v1/telemetry \
  -H 'Content-Type: application/json' \
  -d '{"device_id":"example-device","temperature_c":22.4,"humidity_percent":45.0,"pressure_hpa":1012.6,"light_lux":120}'
```

## Local API with InfluxDB

For an isolated development database, copy `infra/.env.example` to `infra/.env`,
replace the example credentials, and start just InfluxDB:

```bash
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d influxdb
```

Export `INFLUX_URL=http://localhost:8086`, `INFLUX_TOKEN`, `INFLUX_ORG`, and
`INFLUX_BUCKET` in the API process's shell, matching your private `infra/.env`,
then run:

```bash
uv run --project backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API reads environment variables; it does not load `.env` files itself.
With a healthy database, the sample request should return `stored=true`.
`202` alone confirms acceptance, not persistence. Do not use production volumes
for development experiments.

## Telemetry contract

`POST /api/v1/telemetry`, JSON body:

| Field | Required | Meaning / validation |
| --- | --- | --- |
| `device_id` | Yes | String, 1–64 characters |
| `temperature_c` | Yes | −40 to 125 °C |
| `humidity_percent` | Yes | 0 to 100% |
| `pressure_hpa` | No | 300 to 1200 hPa |
| `light_lux` | No | Nonnegative illuminance |
| `co2_ppm` | No | Nonnegative CO₂ concentration |
| `timestamp` | No | Datetime; defaults to server receipt time in UTC |

Source: [Pydantic models](../backend/app/models/telemetry.py). These ranges are API
validation bounds, not accuracy specifications. The current board payload sends
temperature, humidity, and valid pressure; light and CO₂ are schema extensions,
not demonstrated measurements from this device.

## Firmware and remote deployment

Follow the [firmware guide](../mxchip/README.md) for PlatformIO build/upload,
serial monitoring, stored Wi-Fi credentials, private host overrides, and Rust
tests/builds. Select your own serial port; do not copy a machine-specific device
path blindly. `platformio.local.ini` is ignored by Git.

Build the deployable API image with:

```bash
docker build -t mxchip-room-telemetry-api:latest backend
```

Follow the [infrastructure guide](../infra/README.md) for the runtime files,
private `.env`, firewall, first certificate issuance, retention provisioning,
and renewal validation. After certificate issuance, manage the HTTPS deployment
from its infrastructure directory with both Compose files:

```bash
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d
```

Device ingestion remains `http://<public-host>/api/v1/telemetry` on port 80;
the login-protected dashboard is `https://<public-ip>/grafana/`. InfluxDB is
available only through host loopback or an SSH tunnel. Keep actual addresses and
credentials in private configuration.

## Known limits

- The deployed path reads sensors in C/C++. The `no_std` Rust crate builds JSON,
  and C/C++ accepts UART JSON lines, but the deployment log does not establish
  an active Rust-to-UART sensor pipeline.
- The [retry queue](../mxchip/include/telemetry_queue.h) holds eight payloads in
  memory, loses them on reboot, and drops new samples when full.
- The [API](../backend/app/api/routes.py) returns `202` with `stored=false` if
  persistence fails. The device treats any successful HTTP status as delivered,
  so database outages can lose readings despite the HTTP retry queue.
- The C/C++ sensor payload omits timestamps; queued samples receive server
  arrival times rather than their original acquisition times.
- Invalid optional pressure is omitted, not corrected. Sensor calibration,
  measurement accuracy, throughput, and long-term uptime have not been measured.
- Device HTTP ingestion has no authentication or transport encryption. HTTPS
  protects browser access to Grafana, not that separate device path.

The engineering record documents hardware-to-database/dashboard verification on
[October 4](../SYSTEM_LOG.md#2026-10-04---public-https-dashboard-and-automatic-renewal),
[retention deployment on October 15](../SYSTEM_LOG.md#2026-10-15---bounded-telemetry-retention-and-daily-summaries),
and [historical timestamp checks on October 21](../SYSTEM_LOG.md#2026-10-21---restore-grafana-sample-timestamps-after-aggregation).
These are recorded checks, not a new live audit. The configured retention is
30 days raw and 1825 days summarized; it does not establish that amount of
collected history. Summaries store UTC daily mean/minimum/maximum/count per
device and field; Grafana shows older means. See the
[storage guide](../infra/influxdb/README.md) for boundary and outage handling.
