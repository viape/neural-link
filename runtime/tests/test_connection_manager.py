from __future__ import annotations

from neural_gateway.transports import WebSocketTransport
from neural_link.gateway.link_gateway import LinkGateway
from neural_link.runtime import device_state as estados
from neural_link.runtime.connection import ConnectionManager
from neural_link.runtime.lifecycle import DeviceStateMachine


def test_connect_com_sucesso_vai_para_online():
    servidor = WebSocketTransport(port=8175)
    servidor.connect()
    try:
        sm = DeviceStateMachine()
        sm.transition_to(estados.INITIALIZING)
        sm.transition_to(estados.CONNECTING)
        gestor = ConnectionManager(LinkGateway("127.0.0.1", 8175), sm)
        assert gestor.connect() is True
        assert sm.state == estados.ONLINE
    finally:
        servidor.disconnect()


def test_connect_sem_servidor_vai_para_offline():
    sm = DeviceStateMachine()
    sm.transition_to(estados.INITIALIZING)
    sm.transition_to(estados.CONNECTING)
    gestor = ConnectionManager(LinkGateway("127.0.0.1", 8176), sm)
    assert gestor.connect() is False
    assert sm.state == estados.OFFLINE


def test_poll_deteta_queda_e_reconecta_com_sucesso():
    servidor = WebSocketTransport(port=8177)
    servidor.connect()
    try:
        sm = DeviceStateMachine()
        sm.transition_to(estados.INITIALIZING)
        sm.transition_to(estados.CONNECTING)
        gestor = ConnectionManager(LinkGateway("127.0.0.1", 8177), sm)
        assert gestor.connect() is True

        # simula uma queda DETERMINÍSTICA — desliga o lado cliente
        # diretamente, em vez de esperar por uma falha de socket real
        gestor._gateway.disconnect()
        gestor.poll()
        assert sm.state == estados.ONLINE  # reconectou já nesta chamada
    finally:
        servidor.disconnect()


def test_poll_deteta_queda_sem_servidor_fica_offline_com_backoff():
    sm = DeviceStateMachine()
    sm.transition_to(estados.INITIALIZING)
    sm.transition_to(estados.CONNECTING)
    gestor = ConnectionManager(LinkGateway("127.0.0.1", 8178), sm,
                                backoff_initial_s=1.0, backoff_max_s=10.0)
    gestor.connect()
    assert sm.state == estados.OFFLINE
    backoff_inicial = gestor.backoff_s

    gestor.poll()
    assert sm.state == estados.OFFLINE
    assert gestor.backoff_s > backoff_inicial  # cresceu


def test_backoff_nunca_ultrapassa_o_maximo():
    sm = DeviceStateMachine()
    sm.transition_to(estados.INITIALIZING)
    sm.transition_to(estados.CONNECTING)
    gestor = ConnectionManager(LinkGateway("127.0.0.1", 8179), sm,
                                backoff_initial_s=5.0, backoff_max_s=8.0)
    gestor.connect()
    for _ in range(5):
        gestor.poll()
    assert gestor.backoff_s <= 8.0


def test_on_connected_dispara_no_arranque():
    servidor = WebSocketTransport(port=8173)
    servidor.connect()
    try:
        sm = DeviceStateMachine()
        sm.transition_to(estados.INITIALIZING)
        sm.transition_to(estados.CONNECTING)
        chamadas = []
        gestor = ConnectionManager(LinkGateway("127.0.0.1", 8173), sm,
                                    on_connected=lambda: chamadas.append(1))
        gestor.connect()
        assert chamadas == [1]
    finally:
        servidor.disconnect()


def test_on_connected_nao_dispara_quando_a_ligacao_falha():
    sm = DeviceStateMachine()
    sm.transition_to(estados.INITIALIZING)
    sm.transition_to(estados.CONNECTING)
    chamadas = []
    gestor = ConnectionManager(LinkGateway("127.0.0.1", 8174), sm,
                                on_connected=lambda: chamadas.append(1))
    gestor.connect()
    assert chamadas == []


def test_on_connected_dispara_outra_vez_na_reconexao():
    servidor = WebSocketTransport(port=8180)
    servidor.connect()
    try:
        sm = DeviceStateMachine()
        sm.transition_to(estados.INITIALIZING)
        sm.transition_to(estados.CONNECTING)
        chamadas = []
        gestor = ConnectionManager(LinkGateway("127.0.0.1", 8180), sm,
                                    on_connected=lambda: chamadas.append(1))
        gestor.connect()
        assert chamadas == [1]

        gestor._gateway.disconnect()
        gestor.poll()  # reconecta já nesta chamada (mesmo padrão do teste acima)
        assert chamadas == [1, 1]
    finally:
        servidor.disconnect()


def test_send_encaminha_quando_ligado():
    servidor = WebSocketTransport(port=8172, default_channel="teste")
    servidor.connect()
    try:
        sm = DeviceStateMachine()
        sm.transition_to(estados.INITIALIZING)
        sm.transition_to(estados.CONNECTING)
        gestor = ConnectionManager(LinkGateway("127.0.0.1", 8172, channel="teste"), sm)
        gestor.connect()
        assert gestor.send({"ola": "mundo"}) is True
    finally:
        servidor.disconnect()
