import asyncio
import socket

from pymodbus.client import AsyncModbusTcpClient

from orca_simulator.modbus_map import UNIT_ID, Coil, InputRegister
from orca_simulator.server import TankRegisters, create_server


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_registres_aux_adresses_de_la_carte():
    regs = TankRegisters()
    regs.set_input(InputRegister.S01_TEMPERATURE_1, 2450)
    assert regs.get_input(InputRegister.S01_TEMPERATURE_1) == 2450
    assert regs.get_coil(Coil.A01_HEATER) is False
    regs.set_coil(Coil.A01_HEATER, True)
    assert regs.get_coil(Coil.A01_HEATER) is True


def test_un_client_lit_s01_et_ecrit_a01_aux_adresses_du_contrat():
    async def scenario() -> None:
        regs = TankRegisters()
        regs.set_input(InputRegister.S01_TEMPERATURE_1, 2450)
        port = free_port()
        server = create_server(regs, "127.0.0.1", port)
        task = asyncio.create_task(server.serve_forever())
        client = AsyncModbusTcpClient("127.0.0.1", port=port)
        try:
            for _ in range(50):
                if await client.connect():
                    break
                await asyncio.sleep(0.05)
            read = await client.read_input_registers(0, count=1, device_id=UNIT_ID)
            assert read.registers == [2450]

            await client.write_coil(0, True, device_id=UNIT_ID)
            assert regs.get_coil(Coil.A01_HEATER) is True
            coils = await client.read_coils(0, count=1, device_id=UNIT_ID)
            assert coils.bits[0] is True
        finally:
            client.close()
            await server.shutdown()
            task.cancel()

    asyncio.run(scenario())
