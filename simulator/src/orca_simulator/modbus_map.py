"""Carte Modbus d'un bassin, d'après `docs/contracts/modbus-map.md` (version 1).

Seuls les points utilisés par le simulateur v0 sont déclarés ici ; les autres capteurs et
actionneurs arrivent avec l'issue #6.
"""

from __future__ import annotations

from enum import IntEnum

MODBUS_MAP_VERSION = 1
UNIT_ID = 1
BASE_PORT = 5020
"""Port du bassin d'index i : `BASE_PORT + i`."""

SENTINEL = 0xFFFF
"""Valeur renvoyée par un capteur en défaut."""
RAW_MAX = 0xFFFE
"""Plus grande valeur brute valide : `0xFFFF` est réservé à la sentinelle."""

INPUT_REGISTER_COUNT = 10
COIL_COUNT = 6


class InputRegister(IntEnum):
    """Adresses des *input registers* (capteurs)."""

    S01_TEMPERATURE_1 = 0


class Coil(IntEnum):
    """Adresses des *coils* (actionneurs)."""

    A01_HEATER = 0


def encode_temperature_s01(temperature_c: float) -> int:
    """Valeur brute de S01 : centièmes de °C, entier non signé sur 16 bits.

    Une température hors de la plage représentable est écrêtée ; elle ne produit jamais la
    sentinelle, réservée aux défauts capteur.
    """
    raw = round(temperature_c * 100)
    return max(0, min(RAW_MAX, raw))


def decode_temperature_s01(raw: int) -> float:
    """Conversion de l'ACL pour S01 : `raw / 100`, en °C."""
    return raw / 100
