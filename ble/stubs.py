"""Preparado, não implementado — mesmo idioma já usado três vezes neste
projeto para o que precisa de hardware que não temos aqui (`neural_core/
body/ros2/adapters.py`, `neural_runtime/transports/stubs.py`,
`neural_gateway/transports/stubs.py`). Construir nunca rebenta; só
`scan()`/`connect()` (o primeiro contacto real com o rádio) levantam
`NotImplementedError`."""

from __future__ import annotations

from .base import BleAdapter


class UnimplementedBleAdapter(BleAdapter):
    def __init__(self, **config) -> None:
        self._config = config

    def scan(self, *, timeout_s: float = 5.0) -> list[str]:
        raise NotImplementedError(
            "BLE real preparado, não implementado — precisa de rádio + "
            "biblioteca externa (bleak/pybluez). Ver neural_link/ble/stubs.py."
        )

    def connect(self, address: str) -> None:
        raise NotImplementedError("BLE real preparado, não implementado.")

    def disconnect(self, address: str) -> None:
        return None

    def send(self, address: str, data: bytes) -> None:
        raise NotImplementedError("BLE real preparado, não implementado.")

    def receive(self, address: str) -> bytes | None:
        return None
