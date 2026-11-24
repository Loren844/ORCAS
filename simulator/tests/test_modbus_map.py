import pytest

from orca_simulator.modbus_map import (
    RAW_MAX,
    SENTINEL,
    decode_temperature_s01,
    encode_temperature_s01,
)


def test_s01_en_centiemes_de_degre():
    assert encode_temperature_s01(24.5) == 2450
    assert encode_temperature_s01(24.567) == 2457


@pytest.mark.parametrize("temperature_c", [0.0, 12.34, 24.5, 31.99])
def test_aller_retour_avec_la_conversion_de_l_acl(temperature_c):
    assert decode_temperature_s01(encode_temperature_s01(temperature_c)) == pytest.approx(
        temperature_c, abs=0.005
    )


def test_hors_plage_ecrete_sans_jamais_produire_la_sentinelle():
    assert encode_temperature_s01(-3.0) == 0
    assert encode_temperature_s01(1000.0) == RAW_MAX
    assert encode_temperature_s01(1000.0) != SENTINEL
