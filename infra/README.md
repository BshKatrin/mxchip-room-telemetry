# Infrastructure

Remote EC2 runtime for MXChip room telemetry.

The remote instance only needs this directory, a populated `.env`, and Docker volumes.
The FastAPI container is expected to be built elsewhere and referenced by `BACKEND_IMAGE`.

## Remote deploy

```bash
cp .env.example .env
docker compose --env-file .env up -d
```

Only the API service publishes a host port. InfluxDB and Grafana stay on the internal
Compose network and persist their data in Docker volumes.

## Image build

From the repository root:

```bash
docker build -t mxchip-room-telemetry-api:latest backend
```

Push or copy that image to the EC2 host, then set `BACKEND_IMAGE` in `infra/.env`.
