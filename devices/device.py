"""`Device`/`DeviceManager` — o registo dos periféricos ligados ao Neural
Link: auriculares, botões, microfones, LEDs, e o futuro smartwatch. Nunca
sabe FALAR com eles (isso é `neural_link.ble`) — só sabe quem está
ligado, desde quando, e visto pela última vez."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

EARBUDS = "earbuds"
BUTTON = "button"
MICROPHONE = "microphone"
LED = "led"
SMARTWATCH = "smartwatch"


@dataclass
class Device:
    device_id: str
    kind: str
    connected: bool = True
    last_seen: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def touch(self) -> None:
        self.last_seen = time.time()


class DeviceManager:
    def __init__(self) -> None:
        self._devices: dict[str, Device] = {}

    def register(self, device: Device) -> None:
        self._devices[device.device_id] = device

    def unregister(self, device_id: str) -> None:
        self._devices.pop(device_id, None)

    def get(self, device_id: str) -> Device | None:
        return self._devices.get(device_id)

    def all(self) -> list[Device]:
        return list(self._devices.values())

    def connected_devices(self) -> list[Device]:
        return [d for d in self._devices.values() if d.connected]

    def mark_disconnected(self, device_id: str) -> None:
        device = self._devices.get(device_id)
        if device is not None:
            device.connected = False

    def mark_connected(self, device_id: str) -> None:
        device = self._devices.get(device_id)
        if device is not None:
            device.connected = True
            device.touch()
