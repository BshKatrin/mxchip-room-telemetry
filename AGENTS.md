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

These services are deployed together as a single unit.

### Deployment artifact

The remote instance should only contain:

- `docker-compose.yml`
- `.env` (secrets/config)
- persistent Docker volumes (InfluxDB + Grafana data)

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
- MUST expose only FastAPI publicly (via security group)
- InfluxDB and Grafana must remain internal services
- All persistence must use Docker volumes or EBS-backed storage

### Allowed changes

- Modify FastAPI internal structure
- Modify Docker Compose services
- Adjust environment variables and service configuration
- Add reverse proxy (optional, e.g. Nginx) if needed

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
- Endpoint: FastAPI `/sensor` (or equivalent stable ingestion route)

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
