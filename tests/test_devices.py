from __future__ import annotations

from neural_link.devices.device import EARBUDS, Device, DeviceManager


def test_register_e_get():
    manager = DeviceManager()
    manager.register(Device(device_id="fone-1", kind=EARBUDS))
    dispositivo = manager.get("fone-1")
    assert dispositivo is not None
    assert dispositivo.kind == EARBUDS
    assert dispositivo.connected is True


def test_unregister():
    manager = DeviceManager()
    manager.register(Device(device_id="fone-1", kind=EARBUDS))
    manager.unregister("fone-1")
    assert manager.get("fone-1") is None


def test_all_e_connected_devices():
    manager = DeviceManager()
    manager.register(Device(device_id="a", kind=EARBUDS))
    manager.register(Device(device_id="b", kind=EARBUDS, connected=False))
    assert {d.device_id for d in manager.all()} == {"a", "b"}
    assert [d.device_id for d in manager.connected_devices()] == ["a"]


def test_mark_disconnected_e_connected():
    manager = DeviceManager()
    manager.register(Device(device_id="a", kind=EARBUDS))
    manager.mark_disconnected("a")
    assert manager.get("a").connected is False
    manager.mark_connected("a")
    assert manager.get("a").connected is True
