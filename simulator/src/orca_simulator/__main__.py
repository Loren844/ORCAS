"""Point d'entrée : `python -m orca_simulator` ou `orca-simulator`.

Chaque option peut aussi être fournie par une variable d'environnement `ORCA_SIM_*`.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import os

from .modbus_map import BASE_PORT
from .server import TankRegisters, create_server
from .simulation import TankSimulation
from .thermal import ThermalModel, ThermalParams

log = logging.getLogger("orca_simulator")


def _env(name: str, default: str) -> str:
    return os.environ.get(f"ORCA_SIM_{name}", default)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="orca-simulator", description="Simulateur ORCA v0 : un bassin, la température."
    )
    parser.add_argument("--host", default=_env("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(_env("PORT", str(BASE_PORT))))
    parser.add_argument(
        "--step", type=float, default=float(_env("STEP_S", "1.0")), help="pas réel, en s"
    )
    parser.add_argument(
        "--time-factor",
        type=float,
        default=float(_env("TIME_FACTOR", "1")),
        help="facteur de l'horloge simulée (×1 à ×600)",
    )
    parser.add_argument(
        "--initial-temp", type=float, default=float(_env("INITIAL_TEMP_C", "24.0")), help="°C"
    )
    parser.add_argument(
        "--room-temp", type=float, default=float(_env("ROOM_TEMP_C", "22.0")), help="°C"
    )
    parser.add_argument(
        "--volume", type=float, default=float(_env("VOLUME_L", "1000")), help="litres"
    )
    parser.add_argument(
        "--tau", type=float, default=float(_env("TAU_H", "12")), help="constante de temps, en h"
    )
    parser.add_argument(
        "--heater-power", type=float, default=float(_env("HEATER_POWER_W", "1000")), help="W"
    )
    parser.add_argument("--log-level", default=_env("LOG_LEVEL", "INFO"))
    return parser.parse_args(argv)


async def serve(args: argparse.Namespace) -> None:
    params = ThermalParams(
        volume_l=args.volume, tau_s=args.tau * 3600.0, heater_power_w=args.heater_power
    )
    model = ThermalModel(params, temperature_c=args.initial_temp, room_c=args.room_temp)
    registers = TankRegisters()
    simulation = TankSimulation(model, registers, step_s=args.step, time_factor=args.time_factor)
    server = create_server(registers, args.host, args.port)
    log.info(
        "Modbus TCP sur %s:%d, pas %.2f s, facteur ×%g",
        args.host,
        args.port,
        args.step,
        args.time_factor,
    )
    async with asyncio.TaskGroup() as group:
        group.create_task(server.serve_forever())
        group.create_task(simulation.run())


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(serve(args))


if __name__ == "__main__":
    main()
