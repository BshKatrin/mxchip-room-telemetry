#![no_std]

use heapless::String;

pub const PAYLOAD_CAPACITY: usize = 192;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct SensorReading {
    pub temperature_c: f32,
    pub humidity_percent: f32,
    pub pressure_hpa: Option<f32>,
    pub light_lux: Option<f32>,
    pub co2_ppm: Option<f32>,
}

impl SensorReading {
    pub const fn new(temperature_c: f32, humidity_percent: f32) -> Self {
        Self {
            temperature_c,
            humidity_percent,
            pressure_hpa: None,
            light_lux: None,
            co2_ppm: None,
        }
    }
}

pub fn build_payload(device_id: &str, reading: SensorReading) -> Result<String<PAYLOAD_CAPACITY>, ()> {
    let mut out = String::new();
    use core::fmt::Write;

    write!(
        out,
        "{{\"device_id\":\"{}\",\"temperature_c\":{:.2},\"humidity_percent\":{:.2}",
        device_id, reading.temperature_c, reading.humidity_percent
    )
    .map_err(|_| ())?;

    if let Some(value) = reading.pressure_hpa {
        write!(out, ",\"pressure_hpa\":{:.2}", value).map_err(|_| ())?;
    }
    if let Some(value) = reading.light_lux {
        write!(out, ",\"light_lux\":{:.2}", value).map_err(|_| ())?;
    }
    if let Some(value) = reading.co2_ppm {
        write!(out, ",\"co2_ppm\":{:.2}", value).map_err(|_| ())?;
    }

    out.push('}').map_err(|_| ())?;
    Ok(out)
}

#[cfg(test)]
extern crate std;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_required_payload() {
        let payload = build_payload("mxchip-devkit-01", SensorReading::new(22.35, 45.0)).unwrap();
        assert_eq!(
            payload.as_str(),
            "{\"device_id\":\"mxchip-devkit-01\",\"temperature_c\":22.35,\"humidity_percent\":45.00}"
        );
    }

    #[test]
    fn builds_optional_fields() {
        let mut reading = SensorReading::new(20.0, 50.0);
        reading.pressure_hpa = Some(1012.6);
        reading.light_lux = Some(120.0);

        let payload = build_payload("dev", reading).unwrap();

        assert!(payload.contains("\"pressure_hpa\":1012.60"));
        assert!(payload.contains("\"light_lux\":120.00"));
    }
}
