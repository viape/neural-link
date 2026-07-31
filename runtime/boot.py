"""A sequência de arranque pedida, ao pé da letra:

    Boot -> Inicializar Hardware -> Inicializar HAL -> Inicializar
    Drivers -> Inicializar Gateway Client -> Heartbeat -> Aguardar Eventos

`boot()` só COMPÕE — zero lógica nova, tudo o resto já existe. "Aguardar
eventos" é o loop contínuo, que vive em `main.py` (isto aqui é um passo
só, não um serviço)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..devices.device import DeviceManager
from ..gateway.link_gateway import LinkGateway
from . import device_state as estados
from .configuration import DeviceConfig
from .connection import ConnectionManager
from .drivers.raspberry_pi import (NullButtonDriver, NullLEDDriver,
                                    RaspberryPiAudioDriver,
                                    RaspberryPiNetworkDriver,
                                    RaspberryPiStorageDriver)
from .hal.interfaces import AudioDriver, ButtonDriver, LEDDriver, NetworkDriver, StorageDriver
from .heartbeat import HeartbeatManager
from .lifecycle import DeviceStateMachine
from .offline_queue import OfflineQueue


@dataclass
class DriverSet:
    audio: AudioDriver
    network: NetworkDriver
    storage: StorageDriver
    led: LEDDriver
    button: ButtonDriver


@dataclass
class DeviceRuntimeComponents:
    state_machine: DeviceStateMachine
    connection: ConnectionManager
    offline_queue: OfflineQueue
    heartbeat: HeartbeatManager
    device_manager: DeviceManager
    drivers: DriverSet


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
    )


def boot(
    config: DeviceConfig,
    *,
    version: str = "0.1.0",
    driver_factory: Callable[[DeviceConfig], DriverSet] = _placa_raspberry_pi,
) -> DeviceRuntimeComponents:
    sm = DeviceStateMachine(initial=estados.BOOTING)

    # --- Inicializar Hardware / HAL / Drivers --------------------------
    sm.transition_to(estados.INITIALIZING)
    drivers = driver_factory(config)
    device_manager = DeviceManager()

    # --- Inicializar Gateway Client -------------------------------------
    sm.transition_to(estados.CONNECTING)
    gateway = LinkGateway(config.gateway_host, config.gateway_port)
    connection = ConnectionManager(gateway, sm)
    connection.connect()

    # --- Heartbeat ---------------------------------------------------------
    heartbeat = HeartbeatManager(
        version=version,
        interval_s=config.heartbeat_interval_s,
        power=None,  # sem bateria por omissão nesta placa; injetável
        network=drivers.network,
        device_manager=device_manager,
        state_provider=lambda: sm.state,
    )

    offline_queue = OfflineQueue()

    return DeviceRuntimeComponents(
        state_machine=sm,
        connection=connection,
        offline_queue=offline_queue,
        heartbeat=heartbeat,
        device_manager=device_manager,
        drivers=drivers,
    )
