"""`PowerProvider` — a bateria do SBC do Neural Link. Mesma FORMA de
`neural_core.interfaces.BatteryProvider` (a bateria do ROBÔ), fronteira
de hardware diferente — nunca importa essa, para não confundir os dois
domínios."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PowerProvider(ABC):
    @abstractmethod
    def battery_percent(self) -> float:
        """0.0 .. 1.0"""

    @abstractmethod
    def is_charging(self) -> bool: ...

    def sleep(self) -> None:
        """Baixo consumo. Omissão: nada — nem toda a placa tem um modo."""

    def wake(self) -> None: ...


class SimulatedPower(PowerProvider):
    def __init__(self, *, level: float = 1.0, charging: bool = False) -> None:
        self._level = level
        self._charging = charging

    def battery_percent(self) -> float:
        return self._level

    def is_charging(self) -> bool:
        return self._charging

    def set_level(self, level: float) -> None:
        """Só para testes/simulação — nunca existiria numa placa real."""
        self._level = level
