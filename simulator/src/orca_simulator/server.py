"""Serveur Modbus TCP d'un bassin."""

from __future__ import annotations

from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusSequentialDataBlock,
    ModbusServerContext,
)
from pymodbus.server import ModbusTcpServer

from .modbus_map import COIL_COUNT, INPUT_REGISTER_COUNT, UNIT_ID, Coil, InputRegister

# Codes fonction utilisés pour accéder au datastore.
_FC_READ_COILS = 1
_FC_READ_INPUT_REGISTERS = 4


class TankRegisters:
    """Les registres Modbus d'un bassin, vus du simulateur.

    Le simulateur écrit les *input registers* (capteurs) et lit les *coils* (actionneurs) ;
    le contrôleur de bassin fait l'inverse à travers le réseau.
    """

    def __init__(self) -> None:
        # Le datastore décale les adresses de 1 : un bloc commençant à 1 expose l'adresse 0.
        self.device = ModbusDeviceContext(
            di=ModbusSequentialDataBlock(1, [False] * COIL_COUNT),
            co=ModbusSequentialDataBlock(1, [False] * COIL_COUNT),
            hr=ModbusSequentialDataBlock(1, [0] * INPUT_REGISTER_COUNT),
            ir=ModbusSequentialDataBlock(1, [0] * INPUT_REGISTER_COUNT),
        )
        self.context = ModbusServerContext(devices={UNIT_ID: self.device}, single=False)

    def set_input(self, register: InputRegister, raw: int) -> None:
        self.device.setValues(_FC_READ_INPUT_REGISTERS, int(register), [raw])

    def get_input(self, register: InputRegister) -> int:
        return self.device.getValues(_FC_READ_INPUT_REGISTERS, int(register), 1)[0]

    def get_coil(self, coil: Coil) -> bool:
        return bool(self.device.getValues(_FC_READ_COILS, int(coil), 1)[0])

    def set_coil(self, coil: Coil, value: bool) -> None:
        self.device.setValues(_FC_READ_COILS, int(coil), [value])


def create_server(registers: TankRegisters, host: str, port: int) -> ModbusTcpServer:
    """Serveur Modbus TCP qui expose les registres d'un bassin."""
    return ModbusTcpServer(registers.context, address=(host, port))
