"""Modèle thermique du premier ordre d'un bassin.

    dT/dt = (T_local − T) / τ + (P_chauffe − P_froid) / C

L'eau relaxe vers la température du local avec la constante de temps τ ; le chauffage injecte
une puissance P dans une capacité thermique C. À puissance constante sur un pas, l'équation a
une solution exacte, utilisée pour l'intégration : le pas n'a donc aucune limite de stabilité,
ce qui permet d'accélérer l'horloge simulée sans faire diverger le modèle.

    T_eq = T_local + P · τ / C
    T(t + dt) = T_eq + (T(t) − T_eq) · exp(−dt / τ)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

WATER_HEAT_CAPACITY_J_PER_L_K = 4186.0
"""Capacité thermique volumique de l'eau, en J/(L·K)."""


@dataclass(frozen=True)
class ThermalParams:
    """Paramètres physiques d'un bassin."""

    volume_l: float = 1000.0
    """Volume d'eau, en litres."""
    tau_s: float = 12 * 3600.0
    """Constante de temps des échanges avec le local, en secondes."""
    heater_power_w: float = 1000.0
    """Puissance du chauffage A01 quand il est allumé, en watts."""

    def __post_init__(self) -> None:
        if self.volume_l <= 0:
            raise ValueError("volume_l doit être strictement positif")
        if self.tau_s <= 0:
            raise ValueError("tau_s doit être strictement positif")
        if self.heater_power_w < 0:
            raise ValueError("heater_power_w ne peut pas être négatif")

    @property
    def heat_capacity_j_per_k(self) -> float:
        """Capacité thermique du bassin C, en J/K."""
        return self.volume_l * WATER_HEAT_CAPACITY_J_PER_L_K


def equilibrium_c(params: ThermalParams, room_c: float, heater_on: bool) -> float:
    """Température d'équilibre de l'eau pour une température de local et un état du chauffage."""
    power_w = params.heater_power_w if heater_on else 0.0
    return room_c + power_w * params.tau_s / params.heat_capacity_j_per_k


def step(
    params: ThermalParams, temperature_c: float, room_c: float, heater_on: bool, dt_s: float
) -> float:
    """Température de l'eau après `dt_s` secondes simulées, chauffage constant sur le pas."""
    if dt_s < 0:
        raise ValueError("dt_s ne peut pas être négatif")
    t_eq = equilibrium_c(params, room_c, heater_on)
    return t_eq + (temperature_c - t_eq) * math.exp(-dt_s / params.tau_s)


@dataclass
class ThermalModel:
    """État thermique d'un bassin : température de l'eau et du local, chauffage."""

    params: ThermalParams
    temperature_c: float
    room_c: float
    heater_on: bool = False

    def advance(self, dt_s: float) -> float:
        """Fait avancer le modèle de `dt_s` secondes simulées et renvoie la nouvelle température."""
        self.temperature_c = step(
            self.params, self.temperature_c, self.room_c, self.heater_on, dt_s
        )
        return self.temperature_c
