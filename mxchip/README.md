# MXChip Firmware

Device-side firmware for the MXChip AZ3166 board.

## Layout

- `src/`: C/C++ firmware for board setup, Wi-Fi, HTTP POST, UART input, and retry queue use.
- `include/`: C firmware headers.
- `test/`: PlatformIO/host-oriented firmware tests.
- `rust-firmware/`: Rust sensor logic and telemetry JSON preparation crate.
- `platformio.ini`: PlatformIO project configuration.

## C firmware

Run from this directory:

```bash
pio run
pio run --target upload --upload-port /dev/cu.usbmodem11403
pio device monitor --port /dev/cu.usbmodem11403 --baud 115200
```

To override network settings at build time:

```bash
pio run --target upload --upload-port /dev/cu.usbmodem11403 \
  --project-option='build_flags=-D DEVICE_ID=\"mxchip-devkit-01\" -D WIFI_SSID=\"YourSSID\" -D WIFI_PASS=\"YourPassword\" -D BACKEND_HOST=\"your-ec2-public-host-or-domain\" -D BACKEND_PORT=80'
```

For a persistent local target, copy `platformio.local.ini.example` to
`platformio.local.ini`, put the real host there, and keep that file uncommitted.

```bash
pio run -c platformio.local.ini --target upload --upload-port /dev/cu.usbmodem11403
```

## Rust firmware

Run from the repository root:

```bash
cargo test --manifest-path mxchip/rust-firmware/Cargo.toml
cargo build --manifest-path mxchip/rust-firmware/Cargo.toml --target thumbv7em-none-eabihf
```
