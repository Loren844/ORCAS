# Simulateur

Joue le rôle du monde physique : l'eau de chaque bassin (modèle du premier ordre), ses capteurs et
ses actionneurs, exposés en Modbus TCP comme du vrai matériel. Il porte aussi l'horloge simulée et
l'API d'incidents utilisée par la console de démo.

Langage : Python. Voir le [périmètre](../docs/PERIMETRE-POC.md#simulateur), la
[carte Modbus](../docs/contracts/modbus-map.md) et
l'[ADR-0001](../docs/adr/0001-capteurs-actionneurs-simules-en-modbus-tcp.md).

## État (v0)

Un bassin, la température de l'eau :

- modèle thermique `dT/dt = (T_local − T)/τ + P_chauffe/C`, intégré exactement sur chaque pas ;
- S01 (*input register* 0, en 0,01 °C) et A01 chauffage (*coil* 0), *unit id* 1 ;
- boucle à pas fixe : lecture des *coils*, avancée du modèle, écriture des registres.

## Développement

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/pytest
```

## Lancer

```bash
.venv/bin/orca-simulator --time-factor 600
```

Ou avec Docker :

```bash
docker build -t orca-simulator .
docker run --rm -p 5020:5020 orca-simulator --time-factor 600
```

| Option | Variable | Défaut | Rôle |
|---|---|---|---|
| `--host` | `ORCA_SIM_HOST` | `0.0.0.0` | Adresse d'écoute |
| `--port` | `ORCA_SIM_PORT` | `5020` | Port Modbus TCP |
| `--step` | `ORCA_SIM_STEP_S` | `1.0` | Pas réel de la boucle, en s |
| `--time-factor` | `ORCA_SIM_TIME_FACTOR` | `1` | Facteur de l'horloge simulée |
| `--initial-temp` | `ORCA_SIM_INITIAL_TEMP_C` | `24.0` | Température initiale de l'eau, en °C |
| `--room-temp` | `ORCA_SIM_ROOM_TEMP_C` | `22.0` | Température du local, en °C |
| `--volume` | `ORCA_SIM_VOLUME_L` | `1000` | Volume d'eau, en L |
| `--tau` | `ORCA_SIM_TAU_H` | `12` | Constante de temps, en h |
| `--heater-power` | `ORCA_SIM_HEATER_POWER_W` | `1000` | Puissance du chauffage, en W |
| `--log-level` | `ORCA_SIM_LOG_LEVEL` | `INFO` | Niveau de journalisation |

Vérification rapide avec un client Modbus :

```python
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient("127.0.0.1", port=5020)
client.connect()
client.write_coil(0, True, device_id=1)  # A01 chauffage ON
print(client.read_input_registers(0, count=1, device_id=1).registers[0] / 100, "°C")
```
