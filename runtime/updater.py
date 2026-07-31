"""Arquitetura de OTA mais fina do que `neural_link.updates.ota.
OtaUpdater` — reexportado aqui, nunca duplicado. As três interfaces
novas decompõem o que `OtaUpdater.check_for_update`/`apply` faziam num
só passo: SABER que versão existe, TRANSFERIR, e — se algo correr mal —
RECUAR. Todas preparadas, nenhuma implementada, por pedido explícito
("não implementar atualização, projetar arquitetura")."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from ..updates.ota import OtaUpdater, UpdateInfo

__all__ = ["OtaUpdater", "UpdateInfo", "UpdateState",
           "VersionChecker", "DownloadStrategy", "RollbackStrategy",
           "UnimplementedVersionChecker", "UnimplementedDownloadStrategy",
           "UnimplementedRollbackStrategy"]


class UpdateState(str, Enum):
    IDLE = "IDLE"
    CHECKING = "CHECKING"
    DOWNLOADING = "DOWNLOADING"
    APPLYING = "APPLYING"
    ROLLING_BACK = "ROLLING_BACK"
    DONE = "DONE"
    FAILED = "FAILED"


class VersionChecker(ABC):
    @abstractmethod
    def latest_version(self, channel: str) -> UpdateInfo | None: ...


class DownloadStrategy(ABC):
    @abstractmethod
    def download(self, update: UpdateInfo, *, destination: str) -> str:
        """Devolve o caminho local do ficheiro transferido."""


class RollbackStrategy(ABC):
    @abstractmethod
    def snapshot(self) -> str:
        """Regista o estado atual, devolve um identificador para
        `restore()`."""

    @abstractmethod
    def restore(self, snapshot_id: str) -> None: ...


# --- preparadas, não implementadas — mesmo idioma do resto do projeto -
class UnimplementedVersionChecker(VersionChecker):
    def latest_version(self, channel: str) -> UpdateInfo | None:
        raise NotImplementedError(
            "VersionChecker preparado, não implementado. Ver "
            "neural_link/runtime/updater.py."
        )


class UnimplementedDownloadStrategy(DownloadStrategy):
    def download(self, update: UpdateInfo, *, destination: str) -> str:
        raise NotImplementedError("DownloadStrategy preparado, não implementado.")


class UnimplementedRollbackStrategy(RollbackStrategy):
    def snapshot(self) -> str:
        raise NotImplementedError("RollbackStrategy preparado, não implementado.")

    def restore(self, snapshot_id: str) -> None:
        raise NotImplementedError("RollbackStrategy preparado, não implementado.")
