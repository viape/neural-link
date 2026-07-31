"""`WebSocketClient` contra um `neural_gateway.transports.WebSocketTransport`
REAL — a prova de que os dois lados falam o mesmo protocolo."""

from __future__ import annotations

import time

from neural_gateway.transports import WebSocketTransport
from neural_link.gateway.ws_client import WebSocketClient


def test_handshake_e_envio_e_recepcao():
    servidor = WebSocketTransport(port=8280, default_channel="teste")
    servidor.connect()
    try:
        cliente = WebSocketClient("127.0.0.1", 8280)
        cliente.connect()
        try:
            assert cliente.connected is True
            cliente.send_json({"ola": "mundo"})
            time.sleep(0.1)
            recebida = servidor.receive()
            assert recebida is not None
            assert recebida.payload == {"ola": "mundo"}

            servidor.send(recebida.reply({"resposta": True}))
            corpo = cliente.receive_json(timeout_s=3.0)
            assert corpo == {"resposta": True}
        finally:
            cliente.disconnect()
    finally:
        servidor.disconnect()


def test_connect_falha_sem_servidor_levanta_erro_proprio():
    from neural_link.gateway.ws_client import WebSocketConnectionError

    cliente = WebSocketClient("127.0.0.1", 8281)  # nada a escutar
    import pytest
    with pytest.raises(WebSocketConnectionError):
        cliente.connect()


def test_connect_e_idempotente():
    servidor = WebSocketTransport(port=8282)
    servidor.connect()
    try:
        cliente = WebSocketClient("127.0.0.1", 8282)
        cliente.connect()
        try:
            cliente.connect()  # não rebenta a ligar duas vezes
            assert cliente.connected is True
        finally:
            cliente.disconnect()
    finally:
        servidor.disconnect()
