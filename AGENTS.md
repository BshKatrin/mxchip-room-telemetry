# Repo Handoff

## 1. Project overview

This repository contains a hybrid embedded systems project using an STM32-based MXChip IoT board.

The system collects environmental sensor data and forwards it to a backend for storage and visualization.

The architecture is split into:

- C firmware: hardware access, Wi-Fi, HTTP networking
- Rust firmware: sensor logic, computation, and data preparation
- Backend (remote-deployable): ingestion + storage + visualization stack

Telemetry is sent from device to a cloud-hosted backend.

---

## 2. Deployment model (remote-centric)

The backend is designed to run on a single remote instance using Docker Compose.

### Remote runtime stack

On remote, the following services run:

- FastAPI (telemetry ingestion API)
- InfluxDB (time-series database)
- Grafana (visualization dashboard)
- Nginx (public HTTP ingestion and HTTPS dashboard proxy)
- Certbot (on-demand certificate issuance and renewal)

These services are deployed together as a single unit.

### Deployment artifact

The remote instance should only contain:

- `docker-compose.yml`
- `.env` (secrets/config)
- `docker-compose.https.yml`, Nginx configuration, and Grafana provisioning
- certificate renewal scripts and systemd timer/service definitions
- persistent Docker volumes (InfluxDB + Grafana data, ACME webroot, and Let's Encrypt account/certificates)

Source code is not required at runtime if images are built or pulled.

---

## 3. Change tracking

Use SYSTEM_LOG.md as the running engineering log for this project.

When making changes:

- Update SYSTEM_LOG.md in the same change set as any code modification
- Record intent and system impact, not just file diffs
- Focus on why a change was made and what behavior changed
- Keep entries short and incremental
- Include failed experiments if they affect design decisions

Keep AGENTS.md as a stable architecture and operational contract.

---

## 4. System architecture

### 4.1 Device-side architecture

- C firmware: hardware abstraction, Wi-Fi connectivity, HTTP networking
- Rust firmware: sensor processing and computation
- Communication: UART (between Rust and C)

### 4.2 System-level architecture

MXChip → HTTP POST → FastAPI (remote) → InfluxDB (remote) → Grafana (remote)

---

## 5. Backend runtime constraints (remote)

The backend runs as a self-contained Docker stack.

### Constraints

- MUST run as a single remote-hosted system
- MUST NOT depend on local machine runtime
- MUST expose only Nginx host ports 80 and 443 publicly (via security group)
- Nginx exposes FastAPI HTTP ingestion and Grafana at HTTPS `/grafana/`; Grafana login remains required
- InfluxDB and Grafana container ports must remain internal; InfluxDB's optional host binding must use loopback
- All persistence must use Docker volumes or EBS-backed storage
- Dashboard TLS uses a trusted Let's Encrypt IP certificate; never use self-signed certificates for the public dashboard
- IP certificates require the `shortlived` ACME profile and Certbot >= 5.4
- Certificate renewal MUST run automatically on EC2, check twice daily, and reload Nginx after successful renewal
- Keep inbound 80 for HTTP-01 validation and device ingestion, inbound 443 for HTTPS, and outbound 443 for ACME renewal
- Renewal MUST NOT depend on a laptop, SSH download proxy, or Codex being open; preserve certificates and account state across restarts
- Verify renewal with a Certbot dry run and check the enabled systemd timer before reporting automatic renewal as working

### Allowed changes

- Modify FastAPI internal structure
- Modify Docker Compose services
- Adjust environment variables and service configuration
- Add reverse proxy (optional, e.g. Nginx) if needed
- Maintain the existing Nginx/Certbot TLS configuration and remote renewal timer

### Disallowed changes

- MUST NOT introduce external managed services unless explicitly requested
- MUST NOT change HTTP ingestion protocol without explicit instruction
- MUST NOT split backend across multiple cloud providers

---

## 6. Telemetry design

### 6.1 Device → backend transport

- Protocol: HTTP
- Method: POST
- Payload: JSON
- Endpoint: FastAPI `/api/v1/telemetry`
- Preserve HTTP POST on port 80 without redirecting the MXChip to HTTPS; dashboard HTTP requests redirect to HTTPS

### 6.2 Backend responsibilities

- FastAPI: validation + ingestion only
- InfluxDB: storage only
- Grafana: visualization only

No cross-layer coupling is allowed.

---

## 7. Reliability constraints

- Device must tolerate backend downtime
- Backend may restart (remote reboot, Docker restart)
- System must support intermittent connectivity
- Optional buffering on device is allowed but not required initially

---

## 8. Build systems

- C firmware: PlatformIO
- Rust firmware: Cargo (embedded target)
- Backend: Docker + uv (Python dependency management)

---

## 9. Backend structure management

The `backend/` service is deployable to remote and may be restructured for clarity.

### Allowed actions

- Introduce standard FastAPI layouts (`app/`, `core/`, `services/`, `api/`)
- Split/merge modules for maintainability
- Add `__init__.py` where needed
- Introduce `src/` layout if beneficial
- Modify Docker configuration for remote deployment

### Constraints

- MUST preserve HTTP → FastAPI → InfluxDB → Grafana flow
- MUST preserve telemetry schema unless explicitly changed
- MUST keep system deployable via Docker Compose on remote
- MUST NOT introduce messaging brokers (MQTT, Kafka, etc.)

---

## 10. Python environment and dependency management

All Python dependencies must use `uv`.

- `uv` is the only supported dependency manager
- Do NOT use pip, venv, or poetry directly

### Install dependencies

```bash
uv --project=backend add <package>
```
