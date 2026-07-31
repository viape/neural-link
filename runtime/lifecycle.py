"""`DeviceStateMachine` — valida transições contra `device_state.
TRANSICOES_VALIDAS` (levanta em transição inválida — apanha bugs em vez
de os esconder) e trata sinais do SO. Mesmo idioma `_Sinalizador` já
usado em `neural_runtime/cloud/tenant/entrypoint.py`: um handler de
sinal só marca uma flag; o trabalho a sério acontece no loop principal
de `main.py`, nunca dentro do próprio handler."""

from __future__ import annotations

import logging
import signal
from typing import Callable

from . import device_state as estados

log = logging.getLogger("neural_link.runtime.lifecycle")

Observador = Callable[[str, str], None]  # (de, para)


class InvalidTransitionError(RuntimeError):
    pass


class DeviceStateMachine:
    def __init__(self, *, initial: str = estados.BOOTING) -> None:
        self._estado = initial
        self._observadores: list[Observador] = []
        self.shutdown_requested = False

    @property
    def state(self) -> str:
        return self._estado

    def on_transition(self, observador: Observador) -> None:
        self._observadores.append(observador)

    def transition_to(self, novo_estado: str) -> None:
        if not estados.is_valid_transition(self._estado, novo_estado):
            raise InvalidTransitionError(
                f"{self._estado} -> {novo_estado} não é uma transição válida "
                f"(permitidas: {sorted(estados.TRANSICOES_VALIDAS[self._estado])})"
            )
        anterior = self._estado
        self._estado = novo_estado
        log.info("estado: %s -> %s", anterior, novo_estado)
        for observador in self._observadores:
            observador(anterior, novo_estado)

    # --- sinais do SO — só marcam flags, nunca trabalham aqui dentro ---
    def install_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, self._pedir_encerramento)
        signal.signal(signal.SIGINT, self._pedir_encerramento)

    def _pedir_encerramento(self, *_args) -> None:
        self.shutdown_requested = True
