"""`HeartbeatManager` — periodicidade configurável, publica os 8 campos
pedidos. Cada métrica vem de uma fonte INJETADA (`PowerProvider`,
`NetworkDriver`, `DeviceManager`) — nunca uma dependência direta de
hardware específico, por isso funciona igual em qualquer placa.

Temperatura e memória são lidas do SO diretamente (stdlib, melhor-
esforço): existem no Linux/Raspberry Pi, não nesta máquina de
desenvolvimento (macOS) — ausência devolve `None`, nunca rebenta."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable

from ..devices.device import EARBUDS, DeviceManager
from ..power.power import PowerProvider
from .hal.interfaces import NetworkDriver
from .interfaces.types import HeartbeatPayload

_CAMINHO_TEMPERATURA = Path("/sys/class/thermal/thermal_zone0/temp")
_CAMINHO_MEMINFO = Path("/proc/meminfo")


def _ler_temperatura_c() -> float | None:
    try:
        return int(_CAMINHO_TEMPERATURA.read_text().strip()) / 1000.0
    except (OSError, ValueError):
        return None


def _ler_cpu_percent() -> float | None:
    """Melhor-esforço via `os.getloadavg()` (stdlib, POSIX) — mesma
    disciplina de `_ler_temperatura_c`: ausente/indisponível devolve
    `None`, nunca rebenta."""
    try:
        return round(os.getloadavg()[0] * 100.0 / (os.cpu_count() or 1), 2)
    except (AttributeError, OSError):
        return None


def _ler_memoria_percent() -> float | None:
    try:
        linhas = _CAMINHO_MEMINFO.read_text().splitlines()
        valores = {}
        for linha in linhas:
            chave, _, resto = linha.partition(":")
            if chave in ("MemTotal", "MemAvailable"):
                valores[chave] = int(resto.strip().split()[0])
        total = valores.get("MemTotal")
        disponivel = valores.get("MemAvailable")
        if not total:
            return None
        usado = total - (disponivel or 0)
        return round(usado / total, 4)
    except (OSError, ValueError, IndexError, KeyError):
        return None


class HeartbeatManager:
    def __init__(
        self,
        *,
        version: str,
        interval_s: float = 30.0,
        power: PowerProvider | None = None,
        network: NetworkDriver | None = None,
        device_manager: DeviceManager | None = None,
        state_provider: Callable[[], str] = lambda: "UNKNOWN",
        clock: Callable[[], float] = time.time,
        device_id: str = "",
        tenant: str = "",
        token_provider: Callable[[], str] | None = None,
    ) -> None:
        self._version = version
        self._interval_s = interval_s
        self._power = power
        self._network = network
        self._device_manager = device_manager
        self._state_provider = state_provider
        self._clock = clock
        self._device_id = device_id
        self._tenant = tenant
        # Lido a cada heartbeat, não guardado em claro na construção —
        # o token pode vir de algo que ainda não existe no arranque (ex.:
        # emparelhamento), e nunca fica exposto em __repr__/logs por
        # acidente enquanto não for mesmo usado.
        self._token_provider = token_provider
        self._inicio = clock()
        self._ultimo_batimento = 0.0

    @property
    def interval_s(self) -> float:
        return self._interval_s

    def due(self) -> bool:
        return (self._clock() - self._ultimo_batimento) >= self._interval_s

    def beat(self) -> HeartbeatPayload:
        agora = self._clock()
        self._ultimo_batimento = agora
        return HeartbeatPayload(
            timestamp=agora,
            temperature_c=_ler_temperatura_c(),
            memory_percent=_ler_memoria_percent(),
            uptime_s=agora - self._inicio,
            version=self._version,
            battery_percent=self._power.battery_percent() if self._power else None,
            wifi_connected=self._network.is_connected() if self._network else None,
            ble_connected=self._algum_earbud_ligado(),
            state=self._state_provider(),
            device_id=self._device_id,
            tenant=self._tenant,
            token=self._token_provider() if self._token_provider else "",
            cpu_percent=_ler_cpu_percent(),
        )

    def _algum_earbud_ligado(self) -> bool | None:
        if self._device_manager is None:
            return None
        return any(d.kind == EARBUDS for d in self._device_manager.connected_devices())
