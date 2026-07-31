from __future__ import annotations

from neural_link.devices.device import EARBUDS, Device, DeviceManager
from neural_link.power.power import SimulatedPower
from neural_link.runtime.heartbeat import HeartbeatManager


class _RelogioFalso:
    def __init__(self, inicio: float = 1000.0) -> None:
        self.agora = inicio

    def __call__(self) -> float:
        return self.agora


def test_due_respeita_o_intervalo():
    relogio = _RelogioFalso()
    hb = HeartbeatManager(version="1.0.0", interval_s=10.0, clock=relogio)
    assert hb.due() is True  # nunca bateu ainda
    hb.beat()
    assert hb.due() is False
    relogio.agora += 5
    assert hb.due() is False
    relogio.agora += 6
    assert hb.due() is True


def test_payload_tem_os_8_campos():
    hb = HeartbeatManager(version="1.2.3", state_provider=lambda: "ONLINE")
    payload = hb.beat()
    campos = payload.as_dict()
    assert set(campos) == {
        "timestamp", "temperature_c", "memory_percent", "uptime_s",
        "version", "battery_percent", "wifi_connected", "ble_connected", "state",
    }
    assert campos["version"] == "1.2.3"
    assert campos["state"] == "ONLINE"


def test_bateria_vem_do_power_provider_injetado():
    hb = HeartbeatManager(version="1.0.0", power=SimulatedPower(level=0.55))
    assert hb.beat().battery_percent == 0.55


def test_sem_power_provider_bateria_e_none():
    hb = HeartbeatManager(version="1.0.0")
    assert hb.beat().battery_percent is None


def test_ble_connected_via_device_manager():
    manager = DeviceManager()
    manager.register(Device(device_id="fone-1", kind=EARBUDS, connected=True))
    hb = HeartbeatManager(version="1.0.0", device_manager=manager)
    assert hb.beat().ble_connected is True

    manager.mark_disconnected("fone-1")
    assert hb.beat().ble_connected is False


def test_uptime_cresce_com_o_relogio():
    relogio = _RelogioFalso(inicio=100.0)
    hb = HeartbeatManager(version="1.0.0", clock=relogio)
    relogio.agora = 150.0
    payload = hb.beat()
    assert payload.uptime_s == 50.0
