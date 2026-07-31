from __future__ import annotations

import time

from neural_gateway.transports import WebSocketTransport
from neural_link.gateway.link_gateway import LinkGateway


def test_forward_com_sucesso_quando_ligado():
    servidor = WebSocketTransport(port=8283, default_channel="dashboard")
    servidor.connect()
    try:
        link = LinkGateway("127.0.0.1", 8283)
        ok = link.forward({"action": "say", "text": "oi"})
        assert ok is True
        assert len(link.buffer) == 0

        time.sleep(0.1)
        recebida = servidor.receive()
        assert recebida is not None
        assert recebida.payload["text"] == "oi"
    finally:
        servidor.disconnect()


def test_forward_sem_servidor_cai_no_buffer():
    link = LinkGateway("127.0.0.1", 8284)  # nada a escutar
    ok = link.forward({"action": "say", "text": "oi"})
    assert ok is False
    assert len(link.buffer) == 1


def test_flush_buffer_escoa_quando_liga():
    link = LinkGateway("127.0.0.1", 8285)
    link.forward({"action": "say", "text": "mensagem 1"})
    link.forward({"action": "say", "text": "mensagem 2"})
    assert len(link.buffer) == 2

    servidor = WebSocketTransport(port=8285, default_channel="dashboard")
    servidor.connect()
    try:
        enviadas = link.flush_buffer()
        assert enviadas == 2
        assert len(link.buffer) == 0

        time.sleep(0.1)
        vistas = []
        while True:
            m = servidor.receive()
            if m is None:
                break
            vistas.append(m.payload["text"])
        assert vistas == ["mensagem 1", "mensagem 2"]  # ordem preservada
    finally:
        servidor.disconnect()


def test_disconnect_nao_rebenta_sem_ligacao():
    LinkGateway("127.0.0.1", 8286).disconnect()
