"""Neural Link Runtime — o serviço residente que corre num dispositivo
físico (Raspberry Pi, hoje). Nunca contém raciocínio: não conhece Brain,
não conhece Memory, não executa Tools. Só liga hardware à Cloud.

    Boot -> Inicializar Hardware -> HAL -> Drivers -> Gateway Client
         -> Heartbeat -> Aguardar Eventos

A biblioteca `neural_link` (gateway/audio/buffering/devices/security/
power/ble/updates) continua a mesma e é reaproveitada aqui, nunca
duplicada — este pacote só COMPÕE, com um ciclo de vida de dispositivo
por cima."""

from __future__ import annotations

from . import device_state
from .boot import DeviceRuntimeComponents, DriverSet, boot
from .configuration import DeviceConfig
from .configuration import load as load_config
from .connection import ConnectionManager
from .heartbeat import HeartbeatManager
from .interfaces.types import DeviceEvent, HeartbeatPayload
from .lifecycle import DeviceStateMachine, InvalidTransitionError
from .offline_queue import OfflineQueue

__all__ = [
    "device_state",
    "DeviceConfig", "load_config",
    "DeviceStateMachine", "InvalidTransitionError",
    "ConnectionManager",
    "OfflineQueue",
    "HeartbeatManager",
    "DeviceEvent", "HeartbeatPayload",
    "boot", "DeviceRuntimeComponents", "DriverSet",
]
