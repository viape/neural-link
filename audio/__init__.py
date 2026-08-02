"""Microfone -> Wake Word -> VAD -> encaminhar (`pipeline.py`).
Reprodução de resposta (`playback.py`)."""

from __future__ import annotations

from .pipeline import LinkAudioPipeline, NullWakeWordProvider
from .playback import SpeakerPlayback, playback_available

__all__ = [
    "LinkAudioPipeline", "NullWakeWordProvider",
    "SpeakerPlayback", "playback_available",
]
