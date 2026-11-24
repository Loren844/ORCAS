//! Mesure brute publiée sur `orca/{site}/{tank}/measurement/{quantity}`.

use chrono::{DateTime, SecondsFormat, Utc};
use serde::{Serialize, Serializer};

use crate::acl::Sensor;

/// Une lecture de capteur après l'ACL. `value` vaut `null` si le capteur est en défaut.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Measurement {
    pub sensor: &'static str,
    pub value: Option<f64>,
    pub unit: &'static str,
    #[serde(serialize_with = "iso8601")]
    pub timestamp: DateTime<Utc>,
}

impl Measurement {
    pub fn new(sensor: &Sensor, raw: u16, timestamp: DateTime<Utc>) -> Self {
        Self {
            sensor: sensor.id,
            value: sensor.convert(raw),
            unit: sensor.unit,
            timestamp,
        }
    }
}

pub fn topic(site: &str, tank: &str, sensor: &Sensor) -> String {
    format!("orca/{site}/{tank}/measurement/{}", sensor.quantity)
}

fn iso8601<S: Serializer>(t: &DateTime<Utc>, s: S) -> Result<S::Ok, S::Error> {
    s.serialize_str(&t.to_rfc3339_opts(SecondsFormat::Millis, true))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::acl::{S01, SENTINEL};
    use chrono::TimeZone;
    use serde_json::json;

    fn at() -> DateTime<Utc> {
        Utc.with_ymd_and_hms(2026, 11, 24, 18, 30, 0).unwrap()
    }

    #[test]
    fn topic_de_temperature() {
        assert_eq!(
            topic("brest", "b01", &S01),
            "orca/brest/b01/measurement/temperature"
        );
    }

    #[test]
    fn charge_utile_json() {
        let m = Measurement::new(&S01, 2412, at());
        assert_eq!(
            serde_json::to_value(&m).unwrap(),
            json!({
                "sensor": "S01",
                "value": 24.12,
                "unit": "°C",
                "timestamp": "2026-11-24T18:30:00.000Z",
            })
        );
    }

    #[test]
    fn sentinelle_publiee_en_null() {
        let m = Measurement::new(&S01, SENTINEL, at());
        assert_eq!(serde_json::to_value(&m).unwrap()["value"], json!(null));
    }
}
