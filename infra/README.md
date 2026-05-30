# Infrastructure

Remote EC2 runtime for MXChip room telemetry.

The remote instance only needs this directory, a populated `.env`, and Docker volumes.
The FastAPI container is expected to be built elsewhere and referenced by `BACKEND_IMAGE`.

## Public routes

- FastAPI: `http://<public-host>/`
- FastAPI telemetry endpoint: `http://<public-host>/api/v1/telemetry`
- Grafana: `http://<public-host>/grafana/`

InfluxDB is bound to `127.0.0.1:8086` on the EC2 host only. To access it from
your laptop, use an SSH tunnel:

```bash
ssh -i keys/room-telemetry-mxchip.pem -L 8086:127.0.0.1:8086 ec2-user@<public-host>
```

Then open `http://localhost:8086`.

## Remote deploy

```bash
cp .env.example .env
docker compose --env-file .env up -d
```

Set `PUBLIC_HOST` in `.env` to the EC2 public DNS name or IP. Keep `.env`
private and do not commit it.

Only Nginx publishes a public host port. It routes FastAPI and Grafana traffic.
InfluxDB stays private except for the localhost-only binding on the EC2 host.

The EC2 security group should allow inbound `80/tcp` from clients that need the
API/Grafana and `22/tcp` from your IP for SSH. It should not allow public
`3000/tcp` or `8086/tcp`.

## Image build

From the repository root:

```bash
docker build -t mxchip-room-telemetry-api:latest backend
```

Push or copy that image to the EC2 host, then set `BACKEND_IMAGE` in `infra/.env`.
