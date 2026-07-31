"""A Hardware Abstraction Layer do Neural Link — 8 contratos, interfaces
separadas de implementações. Três já existiam (biblioteca do round
anterior) e são só ALIASADOS aqui — nunca redefinidos:

    AudioDriver     = neural_audio.AudioSource
    BluetoothDriver = neural_link.ble.BleAdapter
    PowerDriver     = neural_link.power.PowerProvider

Os outros cinco são novos, sem equivalente anterior:
    NetworkDriver, StorageDriver, LEDDriver, ButtonDriver, Updater

`AudioDriver` vem de `neural_audio`, não de `neural_core` — o Neural Link
nunca importa `neural_core` diretamente (ver `neural_link/tests/
test_di_boundaries.py`)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from neural_audio import AudioSource

from ...ble.base import BleAdapter
from ...power.power import PowerProvider

# --- os três já existentes — nunca uma segunda definição --------------
AudioDriver = AudioSource
BluetoothDriver = BleAdapter
PowerDriver = PowerProvider


# --- os cinco novos -----------------------------------------------------
class NetworkDriver(ABC):
    @abstractmethod
    def is_connected(self) -> bool: ...

    def wifi_info(self) -> dict:
        """SSID/sinal, quando disponível. `{}` se não houver como saber
        (omissão segura — nem toda a plataforma tem `nmcli`)."""
        return {}


class StorageDriver(ABC):
    @abstractmethod
    def read(self, key: str) -> bytes | None: ...

    @abstractmethod
    def write(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class LEDDriver(ABC):
    @abstractmethod
    def show(self, state: str) -> None:
        """Ex.: "booting", "online", "offline", "updating"."""


class ButtonDriver(ABC):
    @abstractmethod
    def read(self) -> list[dict]:
        """Os cliques desde a última leitura. Lista vazia se não houve
        nenhum — mesmo contrato de `neural_core.body.ports.TouchSensor`,
        nunca importado daqui (fronteira de hardware diferente)."""


class Updater(ABC):
    """Ao nível do HARDWARE — aplicar bytes já transferidos. Distinto de
    `neural_link.updates.ota.OtaUpdater` (orquestração: decidir SE há
    update e ir buscá-lo) e de `runtime.updater.VersionChecker`/
    `DownloadStrategy` (essas decidem O QUÊ; esta aplica)."""

    @abstractmethod
    def verify(self, path: str) -> bool: ...

    @abstractmethod
    def apply(self, path: str) -> None: ...
