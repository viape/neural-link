"""`PairingManager` — "arquitetura apenas", por pedido explícito.

A forma fica definida (é o que um emparelhamento BLE real precisa: um
pedido, uma confirmação por código, e uma forma de esquecer o
dispositivo) — nenhum método FAZ nada ainda. Construir nunca rebenta."""

from __future__ import annotations


class PairingManager:
    def start_pairing(self, device_id: str) -> None:
        raise NotImplementedError(
            "Emparelhamento preparado, não implementado — arquitetura "
            "apenas, por pedido explícito. Ver neural_link/pairing/pairing.py."
        )

    def confirm_pairing(self, device_id: str, code: str) -> None:
        raise NotImplementedError("Emparelhamento preparado, não implementado.")

    def forget(self, device_id: str) -> None:
        raise NotImplementedError("Emparelhamento preparado, não implementado.")
