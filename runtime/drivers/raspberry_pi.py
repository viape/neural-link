"""Drivers da Raspberry Pi — hardware real comprado, por isso alguns
destes são implementações a sério (não stub), como o pedido permite
("podem inicialmente ser implementações simples"). Preparados para
crescer para BlueZ/PipeWire/ALSA/GPIO/NetworkManager sem que o resto do
Runtime mude — cada driver só precisa de continuar a cumprir o contrato
`hal.interfaces`.

O ÚNICO ponto de risco real, e a razão de este ficheiro existir: o
`RaspberryPiAudioDriver` embrulha `neural_audio.Microphone`, cujo
CONSTRUTOR abre e arranca o stream de áudio imediatamente. Por isso a
construção do `Microphone` fica ADIADA para `start()` — nunca `__init__`
— para que instanciar este driver (nos testes, ou durante a composição
do boot antes de decidir arrancar) nunca abra hardware.

`Microphone` vem de `neural_audio`, não de `neural_core` — o Neural Link
nunca importa `neural_core` diretamente."""

from __future__ import annotations

import socket
import subprocess
from pathlib import Path

from neural_audio import AudioChunk, Microphone

from ..hal.interfaces import (AudioDriver, ButtonDriver, LEDDriver,
                               NetworkDriver, StorageDriver, Updater)


class RaspberryPiAudioDriver(AudioDriver):
    def __init__(self, *, sample_rate: int = 16000, chunk_ms: int = 80,
                 device: int | None = None) -> None:
        self._sample_rate = sample_rate
        self._chunk_ms = chunk_ms
        self._device = device
        self._mic: Microphone | None = None

    def start(self) -> None:
        """Só aqui é que o microfone real abre. Nunca chamado pelos
        testes desta ronda."""
        if self._mic is not None:
            return
        self._mic = Microphone(
            sample_rate=self._sample_rate, chunk_ms=self._chunk_ms,
            device=self._device,
        )

    def stop(self) -> None:
        if self._mic is not None:
            self._mic.close()
            self._mic = None

    def read(self) -> AudioChunk | None:
        if self._mic is None:
            return None
        return self._mic.read()


class RaspberryPiNetworkDriver(NetworkDriver):
    """Real: ligação = "consigo abrir um socket TCP ao destino
    configurado". `wifi_info()` é melhor-esforço via `nmcli`
    (NetworkManager) — se não existir (ex.: esta máquina de
    desenvolvimento), devolve `{}`, nunca rebenta."""

    def __init__(self, *, probe_host: str = "1.1.1.1", probe_port: int = 443,
                 timeout_s: float = 2.0) -> None:
        self._probe_host = probe_host
        self._probe_port = probe_port
        self._timeout_s = timeout_s

    def is_connected(self) -> bool:
        try:
            with socket.create_connection(
                (self._probe_host, self._probe_port), timeout=self._timeout_s,
            ):
                return True
        except OSError:
            return False

    def wifi_info(self) -> dict:
        try:
            resultado = subprocess.run(
                ["nmcli", "-t", "-f", "active,ssid,signal", "dev", "wifi"],
                capture_output=True, text=True, timeout=self._timeout_s,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return {}
        for linha in resultado.stdout.splitlines():
            partes = linha.split(":")
            if len(partes) >= 3 and partes[0] == "yes":
                return {"ssid": partes[1], "signal": partes[2]}
        return {}


class RaspberryPiStorageDriver(StorageDriver):
    """Real: ficheiros num diretório, stdlib puro."""

    def __init__(self, directory: str | Path) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _caminho(self, key: str) -> Path:
        seguro = key.replace("/", "_").replace("..", "_")
        return self._dir / seguro

    def read(self, key: str) -> bytes | None:
        caminho = self._caminho(key)
        return caminho.read_bytes() if caminho.is_file() else None

    def write(self, key: str, data: bytes) -> None:
        self._caminho(key).write_bytes(data)

    def delete(self, key: str) -> None:
        caminho = self._caminho(key)
        if caminho.is_file():
            caminho.unlink()


class NullLEDDriver(LEDDriver):
    """Real, no seu género: um dispositivo sem LEDs dedicados usa isto,
    de propósito — nunca rebenta por falta de hardware de sinalização."""

    def show(self, state: str) -> None:
        return None


class NullButtonDriver(ButtonDriver):
    def read(self) -> list[dict]:
        return []


class _GpioPorLigar:
    """Preparado, não implementado — GPIO real precisa de `RPi.GPIO`/
    `gpiozero`, dependência externa fora de `dependencies=[]`."""

    def __init__(self, **config) -> None:
        self._config = config


class GpioLEDDriver(_GpioPorLigar, LEDDriver):
    def show(self, state: str) -> None:
        raise NotImplementedError(
            "GPIO real preparado, não implementado — precisa de RPi.GPIO/"
            "gpiozero. Ver neural_link/runtime/drivers/raspberry_pi.py."
        )


class GpioButtonDriver(_GpioPorLigar, ButtonDriver):
    def read(self) -> list[dict]:
        raise NotImplementedError("GPIO real preparado, não implementado.")


class RaspberryPiUpdater(Updater):
    def verify(self, path: str) -> bool:
        raise NotImplementedError(
            "Atualização real preparada, não implementada — por pedido "
            "explícito ('não implementar atualização, projetar arquitetura')."
        )

    def apply(self, path: str) -> None:
        raise NotImplementedError("Atualização real preparada, não implementada.")
