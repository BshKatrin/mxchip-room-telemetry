# Repo Handoff

## Project overview

This repository contains a hybrid embedded systems project using an STM32-based MXChip IoT board. The system collects environmental sensor data and forwards it to a local backend for storage and visualization.

The system is designed as a split firmware architecture:

- C firmware handles hardware, Wi-Fi, and networking
- Rust firmware handles sensor logic and processing

Telemetry is exposed to a local backend for time-series storage and visualization.

## Change tracking

Use SYSTEM_LOG.md as the running engineering log for this project.

When making changes:

- Update SYSTEM_LOG.md in the same change set as any code modification
- Record _intent and system impact_, not just file diffs
- Focus on why a change was made and what behavior changed (e.g. telemetry reliability, latency, buffering, schema changes)
- Keep entries short and incremental rather than large summaries
- Include failed experiments if they affect design decisions

Keep AGENTS.md as a stable orientation document (architecture + rules only).  
Keep SYSTEM_LOG.md as the evolving history of design decisions and system behavior.

## Architecture

### On-device architecture

- C firmware: hardware access + Wi-Fi + HTTP networking
- Rust firmware: sensor processing, computation, and data preparation
- Communication between layers: UART (primary interface)

### System-level architecture

MXChip → HTTP POST → FastAPI server → InfluxDB → Grafana

## Build systems

- C firmware is built using PlatformIO
- Rust firmware is built using Cargo (bare-metal embedded target)

## Hardware

Target device: MXChip IoT Developer Kit (STM32-based)

## Key constraints

- Keep Rust and C components independent
- UART is the only defined communication boundary between firmware layers
- Avoid tight coupling between Rust and C codebases
- No MQTT or broker-based systems unless explicitly introduced later
- No external cloud services required
- System must run fully locally on available devices

## Telemetry design

### Device → backend transport

- Protocol: HTTP
- Payload format: JSON
- Transmission: periodic HTTP POST requests from MXChip to backend

### Backend stack (local-first)

- FastAPI server receives telemetry from device
- InfluxDB stores time-series data
- Grafana provides dashboards and visualization

### Client access

- Grafana accessed via browser

## Data reliability constraints

- Backend may be temporarily offline
- Device-side retry or buffering may be required for reliability
- System should tolerate intermittent connectivity
- No guarantee of continuous connectivity in current design

## Telemetry goal

The system produces live environmental telemetry intended to be accessible remotely via computer or mobile device.

The transport mechanism is intentionally simple (HTTP-based) to minimize infrastructure complexity and avoid dependency on external services.

## Development priorities

- Prefer minimal firmware complexity
- Keep device-side logic simple and robust
- Maintain clear separation between computation (Rust) and hardware/network (C)
- Keep backend easy to run locally and portable
- Avoid premature optimization or over-engineering

## Notes for agents

- Do not introduce MQTT, brokers, or external messaging systems unless explicitly requested
- Maintain HTTP-based ingestion as the primary communication method
- Keep telemetry format simple and stable (JSON over HTTP)
- Prefer incremental improvements over architectural redesigns
