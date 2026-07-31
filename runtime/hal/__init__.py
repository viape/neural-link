"""Hardware Abstraction Layer do Neural Link — 8 contratos. Ver `interfaces.py`."""

from __future__ import annotations

from .interfaces import (AudioDriver, BluetoothDriver, ButtonDriver,
                          LEDDriver, NetworkDriver, PowerDriver,
                          StorageDriver, Updater)

__all__ = [
    "AudioDriver", "BluetoothDriver", "PowerDriver",
    "NetworkDriver", "StorageDriver", "LEDDriver", "ButtonDriver", "Updater",
]
