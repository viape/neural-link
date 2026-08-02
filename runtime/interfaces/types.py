"""Os DTOs neutros que atravessam o Runtime — dados, nunca contratos de
hardware (isso é `runtime.hal`). Mesma separação que `neural_core` já usa
entre `interfaces/` (portos+DTOs) e `hal/` (capacidades físicas)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DeviceEvent:
    """O envelope interno do Runtime — antes de ir para o Gateway (que
    tem o seu próprio `ProtocolMessage`, um conceito da PLATAFORMA, não
    do dispositivo). Nunca se confundem; este nunca sai do processo do
    Runtime sem ser traduzido por quem o envia."""

    id: str
    timestamp: float
    kind: str
    payload: dict
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def create(kind: str, payload: dict, *, metadata: dict | None = None) -> "DeviceEvent":
        return DeviceEvent(
            id=str(uuid.uuid4()), timestamp=time.time(),
            kind=kind, payload=payload, metadata=dict(metadata or {}),
        )


@dataclass(frozen=True)
class HeartbeatPayload:
    """O conteúdo tipado de um heartbeat — os 8 campos pedidos, mais
    device_id/tenant/token (correção crítica: sem isto o Gateway não tem
    como identificar nem autenticar quem fala — vêm todos de `DeviceConfig`,
    já carregados, só não eram transmitidos). Qualquer campo pode ser
    `None`: nem todo o hardware tem bateria, nem todo o Runtime sabe a
    temperatura (não existe em macOS de desenvolvimento, por exemplo) —
    ausência não é erro."""

    timestamp: float
    temperature_c: float | None
    memory_percent: float | None
    uptime_s: float
    version: str
    battery_percent: float | None
    wifi_connected: bool | None
    ble_connected: bool | None
    state: str
    device_id: str = ""
    tenant: str = ""
    token: str = ""
    cpu_percent: float | None = None

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "temperature_c": self.temperature_c,
            "memory_percent": self.memory_percent,
            "uptime_s": self.uptime_s,
            "version": self.version,
            "battery_percent": self.battery_percent,
            "wifi_connected": self.wifi_connected,
            "ble_connected": self.ble_connected,
            "state": self.state,
            "device_id": self.device_id,
            "tenant": self.tenant,
            "token": self.token,
            "cpu_percent": self.cpu_percent,
        }


# As capabilities que este dispositivo anuncia no handshake — hardcoded
# por agora: não existe deteção real de hardware (mesma honestidade sobre
# limitações que _ler_temperatura_c/_ler_memoria_percent já assumem em
# heartbeat.py). Ajustar aqui no dia em que houver deteção real.
CAPACIDADES_SUPORTADAS = ("heartbeat", "audio", "speaker", "camera", "avatar", "ota")


@dataclass(frozen=True)
class HelloPayload:
    """O handshake de capabilities — enviado UMA VEZ por ligação (arranque
    e cada reconexão), nunca substitui o heartbeat. Mesma disciplina de
    identidade do `HeartbeatPayload`: device_id/tenant/token autenticam
    isto exatamente como qualquer outra mensagem."""

    device_id: str
    tenant: str
    token: str
    version: str
    protocol_version: str
    capabilities: tuple[str, ...] = CAPACIDADES_SUPORTADAS

    def as_dict(self) -> dict:
        return {
            "type": "hello",
            "device_id": self.device_id,
            "tenant": self.tenant,
            "token": self.token,
            "version": self.version,
            "protocol_version": self.protocol_version,
            "capabilities": list(self.capabilities),
        }
