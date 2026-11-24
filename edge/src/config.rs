//! Configuration du contrôleur, lue dans les variables d'environnement `ORCA_EDGE_*`.

use std::time::Duration;

use thiserror::Error;

/// Paramètres de démarrage d'un contrôleur (un par bassin).
#[derive(Debug, Clone, PartialEq)]
pub struct Config {
    /// Identifiant du site, premier segment des topics.
    pub site: String,
    /// Identifiant du bassin, second segment des topics.
    pub tank: String,
    pub modbus_host: String,
    pub modbus_port: u16,
    pub modbus_unit_id: u8,
    /// Délai maximal d'une connexion ou d'une lecture Modbus.
    pub modbus_timeout: Duration,
    pub mqtt_host: String,
    pub mqtt_port: u16,
    /// Période de *polling* de S01 (60 s selon la carte Modbus).
    pub poll_period: Duration,
    /// Filtre `tracing` (`info`, `debug`, `orca_edge=debug`…).
    pub log_level: String,
}

#[derive(Debug, Error, PartialEq)]
pub enum ConfigError {
    #[error("variable {0} obligatoire")]
    Missing(&'static str),
    #[error("variable {name} : valeur « {value} » invalide ({reason})")]
    Invalid {
        name: &'static str,
        value: String,
        reason: &'static str,
    },
}

impl Config {
    /// Lit la configuration dans l'environnement du processus.
    pub fn from_env() -> Result<Self, ConfigError> {
        Self::from_lookup(|name| std::env::var(name).ok())
    }

    /// Lit la configuration via `lookup` (séparé de l'environnement pour les tests).
    pub fn from_lookup(lookup: impl Fn(&str) -> Option<String>) -> Result<Self, ConfigError> {
        let get = |name: &'static str| lookup(name).filter(|v| !v.trim().is_empty());

        Ok(Self {
            site: topic_segment("ORCA_EDGE_SITE", get("ORCA_EDGE_SITE"))?,
            tank: topic_segment("ORCA_EDGE_TANK", get("ORCA_EDGE_TANK"))?,
            modbus_host: get("ORCA_EDGE_MODBUS_HOST").unwrap_or_else(|| "127.0.0.1".into()),
            modbus_port: parse("ORCA_EDGE_MODBUS_PORT", get("ORCA_EDGE_MODBUS_PORT"), 5020)?,
            modbus_unit_id: parse(
                "ORCA_EDGE_MODBUS_UNIT_ID",
                get("ORCA_EDGE_MODBUS_UNIT_ID"),
                1,
            )?,
            modbus_timeout: seconds(
                "ORCA_EDGE_MODBUS_TIMEOUT_S",
                get("ORCA_EDGE_MODBUS_TIMEOUT_S"),
                5.0,
            )?,
            mqtt_host: get("ORCA_EDGE_MQTT_HOST").unwrap_or_else(|| "127.0.0.1".into()),
            mqtt_port: parse("ORCA_EDGE_MQTT_PORT", get("ORCA_EDGE_MQTT_PORT"), 1883)?,
            poll_period: seconds(
                "ORCA_EDGE_POLL_PERIOD_S",
                get("ORCA_EDGE_POLL_PERIOD_S"),
                60.0,
            )?,
            log_level: get("ORCA_EDGE_LOG_LEVEL").unwrap_or_else(|| "info".into()),
        })
    }
}

/// Un segment de topic MQTT : obligatoire, sans `/`, `+`, `#` ni espace.
fn topic_segment(name: &'static str, value: Option<String>) -> Result<String, ConfigError> {
    let value = value.ok_or(ConfigError::Missing(name))?;
    if value
        .chars()
        .any(|c| matches!(c, '/' | '+' | '#') || c.is_whitespace())
    {
        return Err(ConfigError::Invalid {
            name,
            value,
            reason: "caractère interdit dans un topic MQTT",
        });
    }
    Ok(value)
}

fn parse<T: std::str::FromStr>(
    name: &'static str,
    value: Option<String>,
    default: T,
) -> Result<T, ConfigError> {
    match value {
        None => Ok(default),
        Some(v) => v.trim().parse().map_err(|_| ConfigError::Invalid {
            name,
            value: v,
            reason: "nombre attendu",
        }),
    }
}

fn seconds(
    name: &'static str,
    value: Option<String>,
    default: f64,
) -> Result<Duration, ConfigError> {
    let s: f64 = parse(name, value.clone(), default)?;
    if !s.is_finite() || s <= 0.0 {
        return Err(ConfigError::Invalid {
            name,
            value: value.unwrap_or_default(),
            reason: "durée strictement positive attendue",
        });
    }
    Ok(Duration::from_secs_f64(s))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    fn config(vars: &[(&str, &str)]) -> Result<Config, ConfigError> {
        let vars: HashMap<String, String> = vars
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();
        Config::from_lookup(|name| vars.get(name).cloned())
    }

    const MINIMAL: [(&str, &str); 2] = [("ORCA_EDGE_SITE", "brest"), ("ORCA_EDGE_TANK", "b01")];

    #[test]
    fn valeurs_par_defaut() {
        let c = config(&MINIMAL).unwrap();
        assert_eq!(c.site, "brest");
        assert_eq!(c.tank, "b01");
        assert_eq!(c.modbus_host, "127.0.0.1");
        assert_eq!(c.modbus_port, 5020);
        assert_eq!(c.modbus_unit_id, 1);
        assert_eq!(c.modbus_timeout, Duration::from_secs(5));
        assert_eq!(c.mqtt_host, "127.0.0.1");
        assert_eq!(c.mqtt_port, 1883);
        assert_eq!(c.poll_period, Duration::from_secs(60));
        assert_eq!(c.log_level, "info");
    }

    #[test]
    fn surcharges() {
        let mut vars = MINIMAL.to_vec();
        vars.extend([
            ("ORCA_EDGE_MODBUS_HOST", "simulator"),
            ("ORCA_EDGE_MODBUS_PORT", "5021"),
            ("ORCA_EDGE_MQTT_HOST", "mosquitto"),
            ("ORCA_EDGE_POLL_PERIOD_S", "0.5"),
        ]);
        let c = config(&vars).unwrap();
        assert_eq!(c.modbus_host, "simulator");
        assert_eq!(c.modbus_port, 5021);
        assert_eq!(c.mqtt_host, "mosquitto");
        assert_eq!(c.poll_period, Duration::from_millis(500));
    }

    #[test]
    fn site_et_bassin_obligatoires() {
        assert_eq!(
            config(&[("ORCA_EDGE_TANK", "b01")]),
            Err(ConfigError::Missing("ORCA_EDGE_SITE"))
        );
        assert_eq!(
            config(&[("ORCA_EDGE_SITE", "brest"), ("ORCA_EDGE_TANK", " ")]),
            Err(ConfigError::Missing("ORCA_EDGE_TANK"))
        );
    }

    #[test]
    fn segment_de_topic_invalide() {
        for tank in ["b/01", "b+", "#", "b 01"] {
            let err = config(&[("ORCA_EDGE_SITE", "brest"), ("ORCA_EDGE_TANK", tank)]);
            assert!(matches!(err, Err(ConfigError::Invalid { .. })), "{tank}");
        }
    }

    #[test]
    fn nombres_invalides() {
        for (name, value) in [
            ("ORCA_EDGE_MODBUS_PORT", "70000"),
            ("ORCA_EDGE_MODBUS_UNIT_ID", "abc"),
            ("ORCA_EDGE_POLL_PERIOD_S", "0"),
            ("ORCA_EDGE_POLL_PERIOD_S", "-1"),
            ("ORCA_EDGE_MODBUS_TIMEOUT_S", "NaN"),
        ] {
            let mut vars = MINIMAL.to_vec();
            vars.push((name, value));
            assert!(
                matches!(config(&vars), Err(ConfigError::Invalid { .. })),
                "{name}={value}"
            );
        }
    }
}
