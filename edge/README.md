# Contrôleur de bassin (edge)

Un processus par bassin. Tout ce qui est nécessaire à la survie du bassin est calculé ici, sans
dépendance au réseau : acquisition Modbus, prétraitement, fusion, *digital twin*, qualification,
décision, régulation sous garde-fous, tampon local et publication du Rapport de bassin.

Langage : Rust. Voir le [périmètre](../docs/PERIMETRE-POC.md#5-edge-rust-un-conteneur-par-bassin).

## État (v0)

Le chemin minimal capteur → MQTT :

- *polling* Modbus TCP de S01 (*input register* 0) à période fixe, 60 s par défaut ;
- *Anti-Corruption Layer* : échelle constructeur (0,01 °C) → °C, sentinelle `0xFFFF` → absence de
  valeur ([carte Modbus](../docs/contracts/modbus-map.md)) ;
- publication brute en QoS 0, non *retained*, sur `orca/{site}/{tank}/measurement/temperature` :

```json
{"sensor": "S01", "value": 24.12, "unit": "°C", "timestamp": "2026-11-24T18:30:00.000Z"}
```

`value` vaut `null` quand le capteur renvoie la sentinelle. Une sonde muette (exception Modbus ou
*timeout*) ne publie rien. L'horodatage est l'heure système UTC, en attendant l'horloge simulée.

Le contrôleur ne s'arrête pas sur une panne : la connexion Modbus est rouverte au tour suivant, le
client MQTT se reconnecte seul et une publication impossible est abandonnée sans bloquer
l'acquisition.

## Développement

```bash
cargo fmt --check && cargo clippy --all-targets
cargo test
```

## Lancer

Contre le [simulateur](../simulator/README.md) et un broker MQTT locaux :

```bash
mosquitto -p 1883
../simulator/.venv/bin/orca-simulator --time-factor 600
ORCA_EDGE_SITE=brest ORCA_EDGE_TANK=b01 ORCA_EDGE_POLL_PERIOD_S=2 cargo run
mosquitto_sub -t 'orca/#' -v
```

Ou avec Docker (le simulateur et le broker joignables sous les noms `simulator` et `mosquitto`) :

```bash
docker build -t orca-edge .
docker run --rm -e ORCA_EDGE_SITE=brest -e ORCA_EDGE_TANK=b01 \
  -e ORCA_EDGE_MODBUS_HOST=simulator -e ORCA_EDGE_MQTT_HOST=mosquitto orca-edge
```

| Variable | Défaut | Rôle |
|---|---|---|
| `ORCA_EDGE_SITE` | obligatoire | Identifiant du site (segment de topic) |
| `ORCA_EDGE_TANK` | obligatoire | Identifiant du bassin (segment de topic) |
| `ORCA_EDGE_MODBUS_HOST` | `127.0.0.1` | Serveur Modbus TCP du bassin |
| `ORCA_EDGE_MODBUS_PORT` | `5020` | Port Modbus (`5020 + index du bassin`) |
| `ORCA_EDGE_MODBUS_UNIT_ID` | `1` | *Unit id* Modbus |
| `ORCA_EDGE_MODBUS_TIMEOUT_S` | `5` | Délai maximal d'une connexion ou d'une lecture, en s |
| `ORCA_EDGE_MQTT_HOST` | `127.0.0.1` | Broker MQTT |
| `ORCA_EDGE_MQTT_PORT` | `1883` | Port du broker |
| `ORCA_EDGE_POLL_PERIOD_S` | `60` | Période de *polling* de S01, en s |
| `ORCA_EDGE_LOG_LEVEL` | `info` | Filtre de journalisation (`debug`, `orca_edge=debug`…) |
