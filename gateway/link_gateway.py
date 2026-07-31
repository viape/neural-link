"""`LinkGateway` — gere BLE (via `neural_link.ble`, preparado), Wi-Fi/
Internet (só o ESTADO da ligação — nunca rádio, isso é hardware) e
encaminha mensagens para o `neural_gateway` da plataforma, via
`WebSocketClient`.

"Gerir Wi-Fi/Internet" reduz-se, honestamente, a: tentar enviar; se
falhar, guardar em vez de perder (`OfflineBuffer`); voltar a tentar
quando a ligação volta. Nenhuma gestão de rádio nem driver de rede
acontece aqui — seria hardware, fora de âmbito por pedido explícito."""

from __future__ import annotations

from ..buffering.buffer import OfflineBuffer
from .ws_client import WebSocketClient, WebSocketConnectionError


class LinkGateway:
    def __init__(self, host: str, port: int, *, channel: str = "dashboard",
                 buffer: OfflineBuffer | None = None) -> None:
        self._channel = channel
        self._client = WebSocketClient(host, port)
        self.buffer = buffer or OfflineBuffer()

    @property
    def connected(self) -> bool:
        return self._client.connected

    def connect(self) -> bool:
        try:
            self._client.connect()
            return True
        except WebSocketConnectionError:
            return False

    def disconnect(self) -> None:
        self._client.disconnect()

    def forward(self, payload: dict) -> bool:
        """Tenta enviar já. Se a ligação estiver em baixo (ou cair a meio),
        a mensagem cai no `OfflineBuffer` em vez de se perder — nunca
        levanta por causa de rede, é o comportamento normal de um
        dispositivo de bordo."""
        mensagem = {"channel": self._channel, **payload}
        if not self.connected and not self.connect():
            self.buffer.enqueue(mensagem)
            return False
        try:
            self._client.send_json(mensagem)
            return True
        except WebSocketConnectionError:
            self.buffer.enqueue(mensagem)
            return False

    def flush_buffer(self) -> int:
        """Escoa o `OfflineBuffer` assim que houver ligação. Devolve
        quantas mensagens saíram desta vez."""
        if not self.connected and not self.connect():
            return 0

        def _enviar(mensagem: dict) -> bool:
            try:
                self._client.send_json(mensagem)
                return True
            except WebSocketConnectionError:
                return False

        return self.buffer.flush(_enviar)
