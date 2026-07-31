"""O teste que prova o diagrama inteiro:

    Auriculares(simulado) -> Neural Link -> WebSocket -> neural_gateway
                           -> Cloud Runtime -> Core

Reaproveita tudo o que já existe (`CloudRuntime`, `Gateway`,
`WebSocketTransport`, `wire_dashboard_channel`) sem tocar numa linha —
só o lado Neural Link é código novo desta ronda.

Âmbito assumido: nesta v1 não há STT local nem um canal dedicado a áudio
binário sobre WebSocket — `on_utterance` encaminha um texto que descreve
a captura (mesmo princípio do que `dashboard_bridge`'s `POST /audio` já
faz a partir de um browser, só que aí a transcrição é HTTP; aqui prova-se
o transporte). Transcrição real a partir de áudio no canal WebSocket fica
para uma integração futura — não é o que este teste verifica."""

from __future__ import annotations

import time

import pytest

from neural_audio import AdaptiveEnergyVAD, AudioChunk, SimulatedWakeWord
from neural_gateway import Gateway
from neural_gateway.adapters import wire_dashboard_channel
from neural_gateway.transports import HTTPTransport, WebSocketTransport
from neural_link.audio.pipeline import LinkAudioPipeline
from neural_link.devices.board import QueuedAudioSource
from neural_link.gateway.link_gateway import LinkGateway


def _chunk(texto: str = "") -> AudioChunk:
    return AudioChunk(samples=texto.encode().ljust(320, b"\x00"))


def _silencio() -> AudioChunk:
    return AudioChunk(samples=b"\x00" * 320)


@pytest.fixture
def plataforma(cloud_runtime):
    http = HTTPTransport(cloud_runtime, port=8290)
    ws = WebSocketTransport(port=8291, default_channel="dashboard")
    gateway = Gateway()
    gateway.register_transport("http", http)
    gateway.register_transport("ws", ws)
    gateway.start()
    wire_dashboard_channel(gateway.router, http)
    yield http
    gateway.stop()


def test_utterance_do_link_chega_a_conversa_do_dashboard(plataforma, cloud_runtime):
    http = plataforma
    link_gateway = LinkGateway("127.0.0.1", 8291)
    capturas: list[str] = []

    def _ao_captar_frase(audio: bytes) -> None:
        texto = f"[neural link] utterance de {len(audio)} bytes"
        capturas.append(texto)
        link_gateway.forward({"action": "say", "text": texto})

    mic = QueuedAudioSource()
    pipeline = LinkAudioPipeline(
        mic, SimulatedWakeWord(phrase="robo"), AdaptiveEnergyVAD(),
        on_utterance=_ao_captar_frase, silence_chunks=3,
    )

    mic.push(_chunk("robo"))
    pipeline.poll()
    for _ in range(3):
        mic.push(_chunk("ola tudo bem"))
        pipeline.poll()
    for _ in range(3):
        mic.push(_silencio())
        pipeline.poll()

    assert len(capturas) == 1
    time.sleep(0.2)
    cloud_runtime.core.bus.pump()

    snap = http.bridge.state()
    turnos = snap["dashboard_conversation"]["turns"]
    assert any(t["text"] == capturas[0] for t in turnos)
