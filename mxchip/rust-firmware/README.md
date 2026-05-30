# Rust firmware

Bare-metal-friendly sensor logic crate.

Responsibilities:

- normalize sensor readings
- build stable JSON telemetry payload
- write newline-terminated payload to UART for C firmware

Commands:

```bash
cargo test --manifest-path mxchip/rust-firmware/Cargo.toml
cargo build --manifest-path mxchip/rust-firmware/Cargo.toml --target thumbv7em-none-eabihf
```

This crate is intentionally small. Board drivers stay in C firmware.
