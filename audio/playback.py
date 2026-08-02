"""`SpeakerPlayback` — reprodução real, sounddevice (PortAudio). Mesma
disciplina do `neural_audio.Microphone`: `import sounddevice` protegido,
falha honesta e clara se não estiver instalado, nunca hardware
construído por acidente num teste.

Nunca toca em `neural_link.ble`/`BleAdapter` (GATT, por implementar) —
Bluetooth ÁUDIO (A2DP, o perfil que liga a auriculares) é emparelhado
uma vez ao nível do sistema operativo (`bluetoothctl`), fora deste
código; depois disso, o dispositivo de áudio por omissão do SO já é o
auricular, e escrever nele é só isto — uma chamada `sounddevice`
normal, exatamente como já se faz para capturar."""

from __future__ import annotations

import io
import logging
import wave

log = logging.getLogger("neural_link.audio.playback")

try:
    import numpy as np
    import sounddevice as sd
    _AVAILABLE = True
except Exception as exc:                          # pragma: no cover
    _AVAILABLE = False
    _IMPORT_ERROR = exc

_TIPOS_POR_LARGURA = {1: "uint8", 2: "int16", 4: "int32"}


def playback_available() -> bool:
    return _AVAILABLE


class SpeakerPlayback:
    def __init__(self, *, device: int | None = None) -> None:
        if not _AVAILABLE:
            raise RuntimeError(
                "sounddevice não está instalado.\n"
                f"Causa: {_IMPORT_ERROR!r}\n"
                "Instalar:  pip install sounddevice   (precisa de libportaudio2)"
            )
        self._device = device

    def play(self, wav_bytes: bytes) -> None:
        """Recebe um WAV inteiro (cabeçalho+PCM) — o MESMO formato que
        `dashboard_bridge.DashboardBridge.synthesize()` já devolve, só
        que aqui chega já descodificado de base64, não por HTTP. Nunca
        bloqueia: `sd.play()` arranca a reprodução em segundo plano (o
        próprio PortAudio trata da fila) — o loop principal do Runtime
        continua de imediato."""
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            sample_rate = wf.getframerate()
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())
        dtype = _TIPOS_POR_LARGURA.get(sampwidth, "int16")
        amostras = np.frombuffer(frames, dtype=dtype)
        if n_channels > 1:
            amostras = amostras.reshape(-1, n_channels)
        sd.play(amostras, samplerate=sample_rate, device=self._device)

    def stop(self) -> None:
        if _AVAILABLE:
            sd.stop()
