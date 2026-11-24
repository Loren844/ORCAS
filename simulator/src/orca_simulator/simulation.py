"""Boucle de simulation à pas fixe d'un bassin."""

from __future__ import annotations

import asyncio
import logging
import time

from .modbus_map import Coil, InputRegister, encode_temperature_s01
from .server import TankRegisters
from .thermal import ThermalModel

log = logging.getLogger(__name__)


class TankSimulation:
    """Relie le modèle physique d'un bassin à ses registres Modbus.

    À chaque pas : lecture des actionneurs (coils), avancée du modèle, écriture des capteurs
    (input registers). Le pas réel est fixe ; le pas simulé vaut `pas réel × facteur`.
    """

    def __init__(
        self,
        model: ThermalModel,
        registers: TankRegisters,
        step_s: float = 1.0,
        time_factor: float = 1.0,
    ) -> None:
        if step_s <= 0:
            raise ValueError("step_s doit être strictement positif")
        if time_factor <= 0:
            raise ValueError("time_factor doit être strictement positif")
        self.model = model
        self.registers = registers
        self.step_s = step_s
        self.time_factor = time_factor
        self.sim_elapsed_s = 0.0
        self._publish_sensors()

    @property
    def sim_step_s(self) -> float:
        return self.step_s * self.time_factor

    def tick(self) -> None:
        """Un pas de simulation."""
        self.model.heater_on = self.registers.get_coil(Coil.A01_HEATER)
        self.model.advance(self.sim_step_s)
        self.sim_elapsed_s += self.sim_step_s
        self._publish_sensors()

    def _publish_sensors(self) -> None:
        self.registers.set_input(
            InputRegister.S01_TEMPERATURE_1, encode_temperature_s01(self.model.temperature_c)
        )

    async def run(self, log_every_s: float = 10.0) -> None:
        """Enchaîne les pas à cadence fixe, sans dérive, jusqu'à annulation."""
        next_tick = time.monotonic()
        last_log = next_tick
        while True:
            self.tick()
            now = time.monotonic()
            if now - last_log >= log_every_s:
                last_log = now
                log.info(
                    "t_sim=%.0f s T=%.2f °C chauffage=%s",
                    self.sim_elapsed_s,
                    self.model.temperature_c,
                    "ON" if self.model.heater_on else "OFF",
                )
            next_tick += self.step_s
            delay = next_tick - time.monotonic()
            if delay < 0:
                # En retard (machine chargée) : on repart de maintenant, sans rafale de rattrapage.
                next_tick = time.monotonic()
                delay = 0.0
            await asyncio.sleep(delay)
