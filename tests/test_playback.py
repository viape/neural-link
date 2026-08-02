"""`SpeakerPlayback` — mesma disciplina de `neural_audio/tests/
test_microphone.py`: nunca hardware real, `sd` sempre falso."""

from __future__ import annotations

import io
import types
import wave

import pytest

from neural_link.audio import playback as playback_module
from neural_link.audio.playback import SpeakerPlayback, playback_available


def _wav(amostras: bytes, *, sample_rate: int = 16000, sampwidth: int = 2,
         nchannels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(nchannels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(amostras)
    return buf.getvalue()


def test_sem_sounddevice_levanta_erro_claro(monkeypatch):
    monkeypatch.setattr(playback_module, "_AVAILABLE", False)
    monkeypatch.setattr(playback_module, "_IMPORT_ERROR",
                         ModuleNotFoundError("sounddevice"), raising=False)
    with pytest.raises(RuntimeError):
        SpeakerPlayback()


def test_playback_available_reflete_o_import():
    assert playback_available() == playback_module._AVAILABLE


def test_play_descodifica_wav_e_chama_sounddevice_com_pcm_correto(monkeypatch):
    chamadas = []
    monkeypatch.setattr(playback_module, "sd", types.SimpleNamespace(
        play=lambda *a, **k: chamadas.append(("play", a, k)),
        stop=lambda: chamadas.append(("stop",)),
    ))
    monkeypatch.setattr(playback_module, "_AVAILABLE", True)

    amostras = (100).to_bytes(2, "little", signed=True) * 10
    wav_bytes = _wav(amostras, sample_rate=16000)

    sp = SpeakerPlayback()
    sp.play(wav_bytes)

    assert len(chamadas) == 1
    _, args, kwargs = chamadas[0]
    assert kwargs["samplerate"] == 16000
    assert kwargs["device"] is None
    assert list(args[0]) == [100] * 10


def test_stop_chama_sd_stop(monkeypatch):
    chamadas = []
    monkeypatch.setattr(playback_module, "sd", types.SimpleNamespace(
        play=lambda *a, **k: None,
        stop=lambda: chamadas.append("stop"),
    ))
    monkeypatch.setattr(playback_module, "_AVAILABLE", True)

    SpeakerPlayback().stop()
    assert chamadas == ["stop"]


def test_stop_sem_sounddevice_nunca_rebenta(monkeypatch):
    """Uma instância construída enquanto disponível continua segura a
    chamar `.stop()` mesmo que `sounddevice` deixe de o estar depois
    (ex.: driver removido a meio) — nunca rebenta, só não chama `sd.stop()`."""
    monkeypatch.setattr(playback_module, "_AVAILABLE", True)
    sp = SpeakerPlayback()
    monkeypatch.setattr(playback_module, "_AVAILABLE", False)
    sp.stop()
