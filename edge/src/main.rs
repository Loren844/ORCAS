//! Contrôleur de bassin ORCA (edge).
//!
//! v0 : interroge S01 en Modbus TCP à période fixe, le traduit par l'ACL et publie la mesure
//! brute en MQTT.

mod acl;
mod config;
mod measurement;
mod modbus;

use std::process::ExitCode;
use std::time::Duration;

use chrono::Utc;
use rumqttc::{AsyncClient, Event, MqttOptions, Packet, QoS};
use tokio::time::{MissedTickBehavior, interval, sleep};
use tracing_subscriber::EnvFilter;

use crate::acl::{S01, Sensor};
use crate::config::Config;
use crate::measurement::Measurement;
use crate::modbus::ModbusClient;

#[tokio::main]
async fn main() -> ExitCode {
    let config = match Config::from_env() {
        Ok(config) => config,
        Err(e) => {
            eprintln!("configuration invalide : {e}");
            return ExitCode::FAILURE;
        }
    };
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_new(&config.log_level).unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .init();
    tracing::info!(site = %config.site, tank = %config.tank, "démarrage du contrôleur");

    run(config).await;
    ExitCode::SUCCESS
}

async fn run(config: Config) {
    let mqtt = connect_mqtt(&config);
    let mut modbus = ModbusClient::new(
        config.modbus_host.clone(),
        config.modbus_port,
        config.modbus_unit_id,
        config.modbus_timeout,
    );

    let mut ticker = interval(config.poll_period);
    ticker.set_missed_tick_behavior(MissedTickBehavior::Skip);
    let shutdown = shutdown_signal();
    tokio::pin!(shutdown);

    loop {
        tokio::select! {
            _ = ticker.tick() => poll(&config, &mut modbus, &mqtt, &S01).await,
            () = &mut shutdown => break,
        }
    }

    tracing::info!("arrêt du contrôleur");
    if let Err(e) = mqtt.disconnect().await {
        tracing::debug!(error = %e, "déconnexion MQTT");
    }
}

/// Lit un capteur et publie sa mesure. Une sonde muette (exception, *timeout*) ne publie rien.
async fn poll(config: &Config, modbus: &mut ModbusClient, mqtt: &AsyncClient, sensor: &Sensor) {
    let raw = match modbus.read_input_register(sensor.address).await {
        Ok(raw) => raw,
        Err(e) => {
            tracing::warn!(sensor = sensor.id, error = %e, "lecture impossible");
            return;
        }
    };
    let measurement = Measurement::new(sensor, raw, Utc::now());
    match measurement.value {
        Some(value) => tracing::info!(sensor = sensor.id, value, unit = sensor.unit, "mesure"),
        None => tracing::warn!(sensor = sensor.id, raw, "sentinelle : capteur en défaut"),
    }

    let topic = measurement::topic(&config.site, &config.tank, sensor);
    let payload = serde_json::to_vec(&measurement).expect("mesure sérialisable");
    // `try_publish` : un broker injoignable ne doit jamais bloquer l'acquisition.
    if let Err(e) = mqtt.try_publish(&topic, QoS::AtMostOnce, false, payload) {
        tracing::warn!(%topic, error = %e, "publication abandonnée");
    }
}

/// Client MQTT ; sa boucle d'événements tourne en tâche de fond et se reconnecte seule.
fn connect_mqtt(config: &Config) -> AsyncClient {
    let client_id = format!("orca-edge-{}-{}", config.site, config.tank);
    let mut options = MqttOptions::new(client_id, &config.mqtt_host, config.mqtt_port);
    options.set_keep_alive(Duration::from_secs(30));

    let (client, mut eventloop) = AsyncClient::new(options, 64);
    let broker = format!("{}:{}", config.mqtt_host, config.mqtt_port);
    tokio::spawn(async move {
        loop {
            match eventloop.poll().await {
                Ok(Event::Incoming(Packet::ConnAck(_))) => {
                    tracing::info!(%broker, "connecté au broker MQTT");
                }
                Ok(_) => {}
                Err(e) => {
                    tracing::warn!(%broker, error = %e, "broker MQTT injoignable, nouvel essai");
                    sleep(Duration::from_secs(2)).await;
                }
            }
        }
    });
    client
}

async fn shutdown_signal() {
    let ctrl_c = async {
        let _ = tokio::signal::ctrl_c().await;
    };
    #[cfg(unix)]
    let terminate = async {
        match tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate()) {
            Ok(mut sigterm) => {
                sigterm.recv().await;
            }
            Err(_) => std::future::pending().await,
        }
    };
    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        () = ctrl_c => {}
        () = terminate => {}
    }
}
