import math

import pytest

from orca_simulator.thermal import ThermalModel, ThermalParams, equilibrium_c, step

PARAMS = ThermalParams(volume_l=1000.0, tau_s=12 * 3600.0, heater_power_w=1000.0)


def test_capacite_thermique_d_un_metre_cube_d_eau():
    assert PARAMS.heat_capacity_j_per_k == pytest.approx(4.186e6)


def test_sans_chauffage_l_equilibre_est_la_temperature_du_local():
    assert equilibrium_c(PARAMS, room_c=20.0, heater_on=False) == 20.0


def test_le_chauffage_decale_l_equilibre_de_p_tau_sur_c():
    expected = 20.0 + 1000.0 * 12 * 3600.0 / 4.186e6
    assert equilibrium_c(PARAMS, room_c=20.0, heater_on=True) == pytest.approx(expected)


def test_pas_nul_ne_change_rien():
    assert step(PARAMS, 25.0, room_c=20.0, heater_on=True, dt_s=0.0) == 25.0


def test_a_l_equilibre_la_temperature_ne_bouge_pas():
    assert step(PARAMS, 20.0, room_c=20.0, heater_on=False, dt_s=3600.0) == pytest.approx(20.0)


def test_sans_chauffage_l_eau_relaxe_vers_le_local():
    hot = step(PARAMS, 26.0, room_c=20.0, heater_on=False, dt_s=600.0)
    cold = step(PARAMS, 14.0, room_c=20.0, heater_on=False, dt_s=600.0)
    assert 20.0 < hot < 26.0
    assert 14.0 < cold < 20.0


def test_apres_une_constante_de_temps_il_reste_un_sur_e_de_l_ecart():
    t = step(PARAMS, 26.0, room_c=20.0, heater_on=False, dt_s=PARAMS.tau_s)
    assert t - 20.0 == pytest.approx(6.0 / math.e)


def test_le_chauffage_fait_monter_la_temperature():
    off = step(PARAMS, 24.0, room_c=20.0, heater_on=False, dt_s=600.0)
    on = step(PARAMS, 24.0, room_c=20.0, heater_on=True, dt_s=600.0)
    assert off < 24.0 < on


def test_pente_initiale_conforme_a_l_equation_differentielle():
    # Petit pas : (T(dt) − T) / dt ≈ (T_local − T)/τ + P/C.
    dt = 1.0
    t0 = 24.0
    slope = (step(PARAMS, t0, room_c=20.0, heater_on=True, dt_s=dt) - t0) / dt
    expected = (20.0 - t0) / PARAMS.tau_s + 1000.0 / PARAMS.heat_capacity_j_per_k
    assert slope == pytest.approx(expected, rel=1e-4)


def test_un_grand_pas_equivaut_a_plusieurs_petits():
    big = step(PARAMS, 24.0, room_c=20.0, heater_on=True, dt_s=3600.0)
    small = 24.0
    for _ in range(60):
        small = step(PARAMS, small, room_c=20.0, heater_on=True, dt_s=60.0)
    assert big == pytest.approx(small)


def test_un_pas_tres_long_reste_stable_et_converge():
    t = step(PARAMS, 24.0, room_c=20.0, heater_on=True, dt_s=1e9)
    assert t == pytest.approx(equilibrium_c(PARAMS, 20.0, heater_on=True))


def test_pas_negatif_refuse():
    with pytest.raises(ValueError):
        step(PARAMS, 24.0, room_c=20.0, heater_on=False, dt_s=-1.0)


@pytest.mark.parametrize("kwargs", [{"volume_l": 0.0}, {"tau_s": -1.0}, {"heater_power_w": -10.0}])
def test_parametres_invalides_refuses(kwargs):
    with pytest.raises(ValueError):
        ThermalParams(**kwargs)


def test_modele_avance_et_garde_son_etat():
    model = ThermalModel(PARAMS, temperature_c=24.0, room_c=20.0)
    model.advance(600.0)
    assert model.temperature_c < 24.0
    model.heater_on = True
    before = model.temperature_c
    assert model.advance(600.0) > before
