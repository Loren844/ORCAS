import asyncio
import socket

import pytest
from pymodbus.client import AsyncModbusTcpClient

from orca_simulator.modbus_map import UNIT_ID, Coil, InputRegister, decode_temperature_s01
from orca_simulator.server import TankRegisters, create_server
from orca_simulator.simulation import TankSimulation
from orca_simulator.thermal import ThermalModel, ThermalParams

PARAMS = ThermalParams()


def make_simulation(temperature_c=22.0, room_c=22.0, step_s=1.0, time_factor=60.0):
    model = ThermalModel(PARAMS, temperature_c=temperature_c, room_c=room_c)
    registers = TankRegisters()
    return TankSimulation(model, registers, step_s=step_s, time_factor=time_factor)


def s01(simulation: TankSimulation) -> float:
    return decode_temperature_s01(simulation.registers.get_input(InputRegister.S01_TEMPERATURE_1))


def test_s01_publie_des_le_demarrage():
    assert s01(make_simulation(temperature_c=24.5)) == 24.5


def test_le_pas_simule_vaut_pas_reel_fois_facteur():
    simulation = make_simulation(step_s=0.5, time_factor=600.0)
    simulation.tick()
    simulation.tick()
    assert simulation.sim_step_s == 300.0
    assert simulation.sim_elapsed_s == 600.0


def test_chauffage_eteint_la_temperature_reste_a_l_equilibre():
    simulation = make_simulation()
    for _ in range(100):
        simulation.tick()
    assert s01(simulation) == 22.0


def test_le_coil_a01_pilote_le_modele():
    simulation = make_simulation()
    simulation.registers.set_coil(Coil.A01_HEATER, True)
    for _ in range(60):
        simulation.tick()
    assert simulation.model.heater_on is True
    assert s01(simulation) > 22.0


@pytest.mark.parametrize("kwargs", [{"step_s": 0.0}, {"time_factor": -1.0}])
def test_parametres_de_boucle_invalides(kwargs):
    with pytest.raises(ValueError):
        make_simulation(**kwargs)


def test_critere_d_acceptation_la_temperature_lue_monte_quand_on_ecrit_le_coil():
    """Un client Modbus lit une température qui monte quand on écrit le coil du chauffage."""

    async def scenario() -> None:
        simulation = make_simulation(step_s=0.02, time_factor=600.0)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = create_server(simulation.registers, "127.0.0.1", port)
        tasks = [
            asyncio.create_task(server.serve_forever()),
            asyncio.create_task(simulation.run()),
        ]
        client = AsyncModbusTcpClient("127.0.0.1", port=port)

        async def read_s01() -> int:
            response = await client.read_input_registers(0, count=1, device_id=UNIT_ID)
            assert not response.isError()
            return response.registers[0]

        try:
            for _ in range(50):
                if await client.connect():
                    break
                await asyncio.sleep(0.05)

            await asyncio.sleep(0.2)
            idle = await read_s01()
            await asyncio.sleep(0.2)
            assert await read_s01() == idle

            await client.write_coil(0, True, device_id=UNIT_ID)
            readings = []
            for _ in range(5):
                await asyncio.sleep(0.2)
                readings.append(await read_s01())
            assert readings == sorted(readings)
            assert readings[-1] > idle
        finally:
            client.close()
            await server.shutdown()
            for task in tasks:
                task.cancel()

    asyncio.run(scenario())
