"""A sequência de arranque pedida, ao pé da letra:

    Boot -> Inicializar Hardware -> Inicializar HAL -> Inicializar
    Drivers -> Inicializar Gateway Client -> Heartbeat -> Aguardar Eventos

`boot()` só COMPÕE — zero lógica nova, tudo o resto já existe. "Aguardar
eventos" é o loop contínuo, que vive em `main.py` (isto aqui é um passo
só, não um serviço)."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Callable

from neural_audio import AdaptiveEnergyVAD, VoiceActivityDetector, WakeWordProvider

from ..audio.pipeline import LinkAudioPipeline, NullWakeWordProvider
from ..devices.device import DeviceManager
from ..gateway.link_gateway import LinkGateway
from . import device_state as estados
from .configuration import DeviceConfig
from .connection import ConnectionManager
from .drivers.raspberry_pi import (NullButtonDriver, NullLEDDriver,
                                    RaspberryPiAudioDriver,
                                    RaspberryPiNetworkDriver,
                                    RaspberryPiSpeakerDriver,
                                    RaspberryPiStorageDriver)
from .hal.interfaces import (AudioDriver, ButtonDriver, LEDDriver,
                              NetworkDriver, SpeakerDriver, StorageDriver)
from .heartbeat import HeartbeatManager
from .interfaces.types import HelloPayload
from .lifecycle import DeviceStateMachine
from .offline_queue import AUDIO, EVENTS, OfflineQueue


@dataclass
class DriverSet:
    audio: AudioDriver
    network: NetworkDriver
    storage: StorageDriver
    led: LEDDriver
    button: ButtonDriver
    # Omissão preserva os DriverSet(...) já existentes nos testes, todos
    # por keyword, nenhum passa speaker=.
    speaker: SpeakerDriver | None = None


@dataclass
class DeviceRuntimeComponents:
    state_machine: DeviceStateMachine
    connection: ConnectionManager
    offline_queue: OfflineQueue
    heartbeat: HeartbeatManager
    device_manager: DeviceManager
    drivers: DriverSet
    audio_pipeline: LinkAudioPipeline


def _placa_raspberry_pi(config: DeviceConfig) -> DriverSet:
    """A fábrica por omissão — hardware real comprado. Injetável (ver
    `driver_factory`) para nunca ser preciso hardware nos testes."""
    diretorio = f"~/.neural_link/{config.device_id or 'device'}"
    return DriverSet(
        audio=RaspberryPiAudioDriver(),
        network=RaspberryPiNetworkDriver(),
        storage=RaspberryPiStorageDriver(directory=diretorio),
        led=NullLEDDriver(),
        button=NullButtonDriver(),
        speaker=RaspberryPiSpeakerDriver(),
    )


def boot(
    config: DeviceConfig,
    *,
    version: str = "0.1.0",
    driver_factory: Callable[[DeviceConfig], DriverSet] = _placa_raspberry_pi,
    wake_word: WakeWordProvider | None = None,
    vad: VoiceActivityDetector | None = None,
) -> DeviceRuntimeComponents:
    sm = DeviceStateMachine(initial=estados.BOOTING)

    # --- Inicializar Hardware / HAL / Drivers --------------------------
    sm.transition_to(estados.INITIALIZING)
    drivers = driver_factory(config)
    # `drivers.audio.start()` NÃO é chamado aqui de propósito — para a
    # placa real (`_placa_raspberry_pi`, a omissão) isso abre um stream
    # `sounddevice` a sério. `boot()` só compõe; arrancar o hardware a
    # sério é responsabilidade de quem entra mesmo em produção
    # (`runtime/main.py`), simétrico ao `.stop()` que já só lá está.
    device_manager = DeviceManager()

    # --- Inicializar Gateway Client -------------------------------------
    sm.transition_to(estados.CONNECTING)
    offline_queue = OfflineQueue()

    def _enviar_hello() -> None:
        """O Capability Handshake — uma vez por ligação (arranque E cada
        reconexão, nunca só a primeira). Não substitui o heartbeat."""
        hello = HelloPayload(
            device_id=config.device_id, tenant=config.tenant, token=config.token,
            version=version, protocol_version="1",
        ).as_dict()
        if not connection.send(hello):
            offline_queue.enqueue(EVENTS, hello)

    gateway = LinkGateway(config.gateway_host, config.gateway_port)
    connection = ConnectionManager(gateway, sm, on_connected=_enviar_hello)
    connection.connect()

    # --- Heartbeat ---------------------------------------------------------
    heartbeat = HeartbeatManager(
        version=version,
        interval_s=config.heartbeat_interval_s,
        power=None,  # sem bateria por omissão nesta placa; injetável
        network=drivers.network,
        device_manager=device_manager,
        state_provider=lambda: sm.state,
        device_id=config.device_id,
        tenant=config.tenant,
        token_provider=lambda: config.token,
    )

    def _ao_ouvir_frase(audio: bytes) -> None:
        payload = {
            "audio_b64": base64.b64encode(audio).decode("ascii"),
            "device_id": config.device_id,
            "tenant": config.tenant,
            "token": config.token,
        }
        if not connection.send(payload):
            offline_queue.enqueue(AUDIO, payload)

    audio_pipeline = LinkAudioPipeline(
        drivers.audio,
        wake_word or NullWakeWordProvider(),
        vad or AdaptiveEnergyVAD(),
        on_utterance=_ao_ouvir_frase,
    )

    return DeviceRuntimeComponents(
        state_machine=sm,
        connection=connection,
        offline_queue=offline_queue,
        heartbeat=heartbeat,
        device_manager=device_manager,
        drivers=drivers,
        audio_pipeline=audio_pipeline,
    )
