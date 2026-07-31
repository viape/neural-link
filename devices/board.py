"""`LinkBoard` — o contrato de UMA placa (SBC) que corre o Neural Link.

Mesma forma de `neural_core/body/registry.py` — um nome entra, uma placa
sai — mas independente: um SBC companheiro de auriculares não é o corpo
de um robô, e este ficheiro nunca importa `neural_core.body`.

    board = create("simulated")   # hoje, sem hardware
    board = create("raspberry_pi")  # amanhã — MESMA chamada, zero mudança
                                    # a montante (a promessa do critério
                                    # de aceitação: trocar de SBC sem
                                    # tocar no Neural Core)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from typing import Callable

from neural_audio import AudioChunk, AudioSource

from ..ble.base import BleAdapter
from ..power.power import PowerProvider, SimulatedPower


class QueuedAudioSource(AudioSource):
    """Um `AudioSource` real, sem hardware: `push()` alimenta, `read()`
    consome — o mesmo padrão fila-interna já usado em `neural_gateway.
    transports.WebSocketTransport`. Útil para `SimulatedBoard` e para
    testar `LinkAudioPipeline` sem microfone nenhum."""

    def __init__(self) -> None:
        self._fila: deque[AudioChunk] = deque()

    def push(self, chunk: AudioChunk) -> None:
        self._fila.append(chunk)

    def read(self) -> AudioChunk | None:
        return self._fila.popleft() if self._fila else None


class LinkBoard(ABC):
    name: str = "board"

    def microphone(self) -> AudioSource | None:
        return None

    def ble(self) -> BleAdapter | None:
        return None

    def power(self) -> PowerProvider | None:
        return None

    def start(self) -> None: ...

    def stop(self) -> None: ...


class SimulatedBoard(LinkBoard):
    """Real, testável, sem hardware nenhum — o `SimulatedMobileBase`/
    `MockTTS` do Neural Link."""

    name = "simulated"

    def __init__(self, **_ignorado) -> None:
        self._mic = QueuedAudioSource()
        self._power = SimulatedPower(level=1.0)

    def microphone(self) -> AudioSource:
        return self._mic

    def power(self) -> PowerProvider:
        return self._power


_PLACAS: dict[str, Callable[..., LinkBoard]] = {}


def register(name: str, factory: Callable[..., LinkBoard]) -> None:
    _PLACAS[name] = factory


def create(name: str, **kwargs) -> LinkBoard:
    if name not in _PLACAS:
        raise KeyError(f"placa {name!r} desconhecida. Disponíveis: {available()}")
    return _PLACAS[name](**kwargs)


def available() -> tuple[str, ...]:
    return tuple(sorted(_PLACAS))


def has(name: str) -> bool:
    return name in _PLACAS


register("simulated", lambda **kw: SimulatedBoard(**kw))
