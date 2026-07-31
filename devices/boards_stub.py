"""Placas físicas — preparadas, não implementadas. Constroem-se e
registam-se livremente; só `start()` levanta `NotImplementedError`. É
esta lista que prova o critério de aceitação: trocar de placa é trocar o
nome em `create(...)`, nunca uma linha do Neural Core."""

from __future__ import annotations

from .board import LinkBoard, register


class _PlacaFisicaPorLigar(LinkBoard):
    modelo = "?"

    def __init__(self, **config) -> None:
        self._config = config

    def start(self) -> None:
        raise NotImplementedError(
            f"Placa {self.modelo} preparada, não implementada — precisa de "
            f"hardware real. Ver neural_link/devices/boards_stub.py."
        )


class RaspberryPiBoard(LinkBoard):
    """Hardware real comprado — deixa de ser stub. Os drivers concretos
    vivem em `neural_link.runtime.drivers.raspberry_pi`; o import é
    LAZY (dentro dos métodos, não no topo do ficheiro) de propósito —
    `neural_link.runtime` importa `neural_link.devices.device`
    (`DeviceManager`), e um import de topo aqui criaria um ciclo entre
    os dois pacotes. `start()`/`stop()` continuam a não ser
    `NotImplementedError`: o hardware já existe."""

    name = "raspberry_pi"

    def __init__(self, **_ignorado) -> None:
        self._audio = None

    def microphone(self):
        from ..runtime.drivers.raspberry_pi import RaspberryPiAudioDriver
        if self._audio is None:
            self._audio = RaspberryPiAudioDriver()
        return self._audio

    def power(self):
        return None  # sem bateria nesta placa por omissão — ver PowerDriver

    def start(self) -> None:
        if self._audio is not None:
            self._audio.start()

    def stop(self) -> None:
        if self._audio is not None:
            self._audio.stop()


class OrangePiBoard(_PlacaFisicaPorLigar):
    name = modelo = "orange_pi"


class ComputeModuleBoard(_PlacaFisicaPorLigar):
    name = modelo = "compute_module"


class SbcOemBoard(_PlacaFisicaPorLigar):
    name = modelo = "sbc_oem"


class CustomHardwareBoard(_PlacaFisicaPorLigar):
    name = modelo = "custom_hardware"


for _classe in (RaspberryPiBoard, OrangePiBoard, ComputeModuleBoard,
                SbcOemBoard, CustomHardwareBoard):
    register(_classe.name, _classe)
