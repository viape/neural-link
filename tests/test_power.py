from __future__ import annotations

from neural_link.power.power import SimulatedPower


def test_nivel_configurado():
    power = SimulatedPower(level=0.42, charging=True)
    assert power.battery_percent() == 0.42
    assert power.is_charging() is True


def test_set_level():
    power = SimulatedPower(level=1.0)
    power.set_level(0.1)
    assert power.battery_percent() == 0.1


def test_sleep_wake_nao_rebentam():
    power = SimulatedPower()
    power.sleep()
    power.wake()
