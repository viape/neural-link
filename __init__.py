"""Neural Link — a ponte portátil entre um dispositivo físico
(auriculares, hoje; smartwatch, amanhã) e o Neural Cloud.

    Auriculares -> BLE -> Neural Link -> [WebSocket] -> neural_gateway
                                                       -> Cloud Runtime -> Core

O Neural Link NÃO é um Runtime. Não executa Brain, Memory nem Providers —
só capta áudio localmente (Wake Word + VAD, reaproveitados de
`neural_core.interfaces`/`neural_core.integrations.speech`, nunca
duplicados), encaminha para a nuvem transcrever, e gere o que é do
dispositivo em si: periféricos BLE, energia, emparelhamento, atualização.

Por pedido explícito, não há uma classe "LinkRuntime": as peças compõem-se
(ver `neural_link/tests/test_end_to_end_link_to_cloud.py` para a
composição completa), nunca um objeto com lifecycle de Runtime.

`gateway/ws_client.py` é a ÚNICA peça deste pacote que fala com o resto
da plataforma — e fá-lo só pelo protocolo de rede (WebSocket), nunca por
import. Todo o resto deste pacote pode, em teoria, correr num processo
que nunca teve `neural_core`/`neural_runtime`/`neural_gateway` instalados.

Trocar de placa (Raspberry Pi, Orange Pi, Compute Module, SBC OEM,
hardware próprio) é trocar um nome em `neural_link.devices.create(...)` —
zero linhas do Neural Core tocadas, a mesma promessa que `neural_core.
body.registry` já cumpre para o corpo do robô."""

from __future__ import annotations

from .audio.pipeline import LinkAudioPipeline
from .ble.base import BleAdapter
from .buffering.buffer import OfflineBuffer
from .devices.board import LinkBoard, SimulatedBoard
from .devices.device import Device, DeviceManager
from .gateway.link_gateway import LinkGateway
from .gateway.ws_client import WebSocketClient
from .pairing.pairing import PairingManager
from .power.power import PowerProvider, SimulatedPower
from .security.auth import DummyLinkAuth, LinkAuthProvider
from .updates.ota import OtaUpdater

__all__ = [
    "LinkGateway", "WebSocketClient",
    "LinkAudioPipeline",
    "Device", "DeviceManager",
    "LinkBoard", "SimulatedBoard",
    "BleAdapter",
    "PairingManager",
    "LinkAuthProvider", "DummyLinkAuth",
    "OfflineBuffer",
    "PowerProvider", "SimulatedPower",
    "OtaUpdater",
]
