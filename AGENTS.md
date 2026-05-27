# Repo Handoff

## 1. Project overview

This repository contains a hybrid embedded systems project using an STM32-based MXChip IoT board.

The system collects environmental sensor data and forwards it to a local backend for storage and visualization.

The architecture is split into two firmware components:

- C firmware: hardware access, Wi-Fi, and HTTP networking
- Rust firmware: sensor logic, computation, and data preparation

Telemetry is sent to a local backend for time-series storage and visualization.

---

## 2. System architecture

### 2.1 On-device architecture

- C firmware: hardware abstraction, Wi-Fi connectivity, HTTP networking
- Rust firmware: sensor processing and computation
- Communication between layers: UART (primary interface)

### 2.2 System-level architecture

MXChip → HTTP POST → FastAPI server → InfluxDB → Grafana

---

## 3. Telemetry design

### 3.1 Device → backend transport

- Protocol: HTTP
- Payload format: JSON
- Transmission: periodic HTTP POST requests from MXChip to backend

### 3.2 Backend stack (local-first)

- FastAPI: telemetry ingestion API
- InfluxDB: time-series storage
- Grafana: visualization and dashboards

### 3.3 Client access

- Grafana accessed via browser (desktop or mobile)

---

## 4. Data reliability constraints

- Backend may be temporarily offline
- Device-side retry or buffering may be required
- System must tolerate intermittent connectivity
- No guarantee of continuous connectivity

---

## 5. Build systems

- C firmware: PlatformIO
- Rust firmware: Cargo (bare-metal embedded target)

---

## 6. Hardware

- Target device: MXChip IoT Developer Kit (STM32-based)

---

## 7. Backend structure management

The `backend/` Python service is not fixed and may be refactored when beneficial for clarity, maintainability, or scalability.

### Allowed actions

- Restructure backend internals without changing system behavior
- Introduce standard FastAPI layouts (`app/`, `core/`, `services/`, `api/`)
- Split or merge modules to improve separation of concerns
- Add missing `__init__.py` files when required
- Introduce a `src/` layout if it improves packaging correctness

### Constraints

- MUST preserve system-level architecture (HTTP → FastAPI → InfluxDB → Grafana)
- MUST preserve existing API behavior and telemetry format unless explicitly instructed otherwise
- MUST NOT introduce unnecessary complexity
- MUST NOT introduce external services, brokers, or messaging systems
- MUST NOT change device-to-backend protocol without explicit instruction

### Guiding principle

Prefer practical structure over initial layout. The backend is expected to evolve over time, but behavior stability takes priority over refactoring.

---

## 8. Python environment and dependency management

All Python dependencies and execution must be managed using `uv`.

- `uv` is the only supported dependency manager
- Do NOT use `pip`, `venv`, or `poetry`
- All commands must be executed from the repository root unless explicitly stated otherwise

### Install dependencies

```bash
uv --project=backend add <package>
```

### Run Python applications

```bash
uv run --project backend <command>
```

## Development priorities

- Prefer minimal firmware complexity
- Keep device-side logic simple and robust
- Maintain clear separation between computation (Rust) and hardware/networking (C)
- Keep backend easy to run locally and portable
- Avoid premature optimization or over-engineering

## Notes for agents

- Do not introduce MQTT, brokers, or external messaging systems unless explicitly requested
- Maintain HTTP-based ingestion as the primary communication method
- Keep telemetry format simple and stable (JSON over HTTP)
- Prefer incremental improvements over architectural redesigns
