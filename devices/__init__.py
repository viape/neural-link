"""Periféricos ligados (`device.py`) e a placa que os hospeda
(`board.py`, `boards_stub.py`)."""

from __future__ import annotations

from . import boards_stub  # noqa: F401 — regista as placas físicas stub
from .board import (LinkBoard, QueuedAudioSource, SimulatedBoard, available,
                     create, has, register)
from .device import (BUTTON, EARBUDS, LED, MICROPHONE, SMARTWATCH, Device,
                      DeviceManager)

__all__ = [
    "Device", "DeviceManager", "EARBUDS", "BUTTON", "MICROPHONE", "LED", "SMARTWATCH",
    "LinkBoard", "SimulatedBoard", "QueuedAudioSource",
    "register", "create", "available", "has",
]
