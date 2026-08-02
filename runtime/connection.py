"""`ConnectionManager` — embrulha `neural_link.gateway.LinkGateway` (não
o duplica) e conduz a máquina de estados: CONNECTING no arranque,
RECONNECTING com backoff exponencial sempre que a ligação cai.

Limitação conhecida, documentada em vez de escondida: `connected`
reflete o ÚLTIMO ESTADO CONHECIDO do socket local, não uma verificação
ativa — se o SERVIDOR cair sem o cliente tentar enviar/receber entretanto
(TCP permite um `send()` local ter sucesso mesmo com o outro lado já
fechado), a queda só é detetada na PRÓXIMA operação que falhar. Um
keepalive ao nível do protocolo (ping/pong) resolveria isto — fica para
uma iteração futura, fora do âmbito desta v1 ("implementações simples")."""

from __future__ import annotations

from typing import Callable

from ..gateway.link_gateway import LinkGateway
from . import device_state as estados
from .lifecycle import DeviceStateMachine


class ConnectionManager:
    def __init__(
        self,
        gateway: LinkGateway,
        state_machine: DeviceStateMachine,
        *,
        backoff_initial_s: float = 1.0,
        backoff_max_s: float = 60.0,
        on_connected: Callable[[], None] | None = None,
    ) -> None:
        self._gateway = gateway
        self._sm = state_machine
        self._backoff_initial_s = backoff_initial_s
        self._backoff_max_s = backoff_max_s
        self._backoff_atual = backoff_initial_s
        # Chamado depois de CADA transição para ONLINE — arranque E
        # reconexão — nunca só uma vez no processo. É o que garante que
        # o hello (handshake de capabilities) sai de novo depois de uma
        # queda, não só no boot.
        self._on_connected = on_connected

    @property
    def backoff_s(self) -> float:
        return self._backoff_atual

    @property
    def connected(self) -> bool:
        return self._gateway.connected

    def connect(self) -> bool:
        """Chamado uma vez, no arranque — assume que a máquina já está
        em CONNECTING (transição feita por `boot.py`)."""
        if self._gateway.connect():
            self._backoff_atual = self._backoff_initial_s
            self._sm.transition_to(estados.ONLINE)
            if self._on_connected is not None:
                self._on_connected()
            return True
        self._sm.transition_to(estados.OFFLINE)
        return False

    def poll(self) -> None:
        """Chamar em loop. Deteta ligação perdida e conduz o
        RECONNECTING com backoff — nunca bloqueia mais do que uma
        tentativa de ligação por chamada."""
        if self._sm.state == estados.ONLINE and not self._gateway.connected:
            self._sm.transition_to(estados.OFFLINE)

        if self._sm.state == estados.OFFLINE:
            self._sm.transition_to(estados.RECONNECTING)
            self._tentar_reconectar()

    def _tentar_reconectar(self) -> None:
        if self._gateway.connect():
            self._backoff_atual = self._backoff_initial_s
            self._sm.transition_to(estados.ONLINE)
            if self._on_connected is not None:
                self._on_connected()
        else:
            self._backoff_atual = min(self._backoff_atual * 2, self._backoff_max_s)
            self._sm.transition_to(estados.OFFLINE)

    def send(self, payload: dict) -> bool:
        """Encaminha já; se falhar, quem chama decide se cai na
        `OfflineQueue` — este ficheiro nunca a conhece, por desenho."""
        return self._gateway.forward(payload)

    def receive(self, *, timeout_s: float = 0.05) -> dict | None:
        """Sondagem — chamar em loop, mesmo idioma de `poll()`. `timeout_s`
        pequeno de propósito: um bloqueio de 5s (a omissão do
        `WebSocketClient`) travaria o loop principal de 0.5s do Runtime;
        isto é sempre chamado quando já se sabe que há ligação."""
        if not self.connected:
            return None
        return self._gateway.receive(timeout_s=timeout_s)

    def disconnect(self) -> None:
        self._gateway.disconnect()
