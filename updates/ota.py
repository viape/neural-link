"""`OtaUpdater` — "preparar atualização remota". Flashing é específico de
bootloader/placa — fora de âmbito por ser hardware. A forma fica pronta;
nenhum método faz nada ainda."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    url: str


class OtaUpdater:
    def check_for_update(self, current_version: str) -> UpdateInfo | None:
        raise NotImplementedError(
            "OTA preparado, não implementado — específico de bootloader/"
            "placa. Ver neural_link/updates/ota.py."
        )

    def apply(self, update: UpdateInfo) -> None:
        raise NotImplementedError("OTA preparado, não implementado.")
