"""`BleAdapter` — o contrato de UM rádio BLE. Preparado, não implementado
— BLE real precisa de um rádio físico e de uma biblioteca externa
(`bleak`/`pybluez`), incompatível com a disciplina `dependencies=[]` do
projeto. Ver `stubs.py`."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BleAdapter(ABC):
    @abstractmethod
    def scan(self, *, timeout_s: float = 5.0) -> list[str]:
        """Endereços dos dispositivos BLE visíveis."""

    @abstractmethod
    def connect(self, address: str) -> None: ...

    @abstractmethod
    def disconnect(self, address: str) -> None: ...

    @abstractmethod
    def send(self, address: str, data: bytes) -> None: ...

    @abstractmethod
    def receive(self, address: str) -> bytes | None:
        """Não bloqueia. `None` se não houver nada pendente."""
