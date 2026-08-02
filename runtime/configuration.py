"""`DeviceConfig` — configuração persistente, nunca hardcoded. MESMO
padrão de `neural_core.runtime.config.load` (já replicado antes em
`neural_runtime/configuration/config.py`): TOML, `tomllib` puro, função
de módulo (não método), tolerante a ficheiro em falta ou corrompido —
um dispositivo que não arranca por falta de config.toml é um dispositivo
mau."""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger("neural_link.runtime.configuration")


@dataclass
class DeviceConfig:
    hostname: str = "neural-link"
    gateway_host: str = "127.0.0.1"
    gateway_port: int = 8291
    tenant: str = ""
    device_id: str = ""
    wifi_ssid: str = ""
    tls_cert: str = ""
    tls_key: str = ""
    ota_channel: str = "stable"
    heartbeat_interval_s: float = 30.0
    token: str = ""
    source: str = "(defaults)"


def load(path: str | Path | None = None) -> DeviceConfig:
    cfg = DeviceConfig()
    if path is None:
        return cfg

    p = Path(path)
    if not p.is_file():
        log.info("%s não existe — a usar os valores por omissão", p)
        return cfg

    try:
        with p.open("rb") as fh:
            dados = tomllib.load(fh)
    except (tomllib.TOMLDecodeError, OSError) as exc:
        log.error("%s está corrompido (%s) — a usar os valores por omissão", p, exc)
        return cfg

    cfg.source = str(p)
    cfg.hostname = str(dados.get("hostname", cfg.hostname))
    cfg.tenant = str(dados.get("tenant", cfg.tenant))
    cfg.device_id = str(dados.get("device_id", cfg.device_id))

    gateway = dados.get("gateway") or {}
    if isinstance(gateway, dict):
        cfg.gateway_host = str(gateway.get("host", cfg.gateway_host))
        cfg.gateway_port = int(gateway.get("port", cfg.gateway_port))

    wifi = dados.get("wifi") or {}
    if isinstance(wifi, dict):
        cfg.wifi_ssid = str(wifi.get("ssid", cfg.wifi_ssid))

    certificados = dados.get("certificados") or {}
    if isinstance(certificados, dict):
        cfg.tls_cert = str(certificados.get("cert", cfg.tls_cert))
        cfg.tls_key = str(certificados.get("key", cfg.tls_key))

    ota = dados.get("ota") or {}
    if isinstance(ota, dict):
        cfg.ota_channel = str(ota.get("channel", cfg.ota_channel))

    seguranca = dados.get("security") or {}
    if isinstance(seguranca, dict):
        cfg.token = str(seguranca.get("token", cfg.token))

    heartbeat = dados.get("heartbeat") or {}
    if isinstance(heartbeat, dict):
        try:
            cfg.heartbeat_interval_s = float(
                heartbeat.get("interval_s", cfg.heartbeat_interval_s)
            )
        except (TypeError, ValueError):
            log.warning("heartbeat.interval_s inválido — a manter %.1fs",
                        cfg.heartbeat_interval_s)

    return cfg
