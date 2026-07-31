"""Autenticação local Auriculares<->Link. Ver `auth.py`."""

from __future__ import annotations

from .auth import DummyLinkAuth, LinkAuthProvider, LinkAuthResult

__all__ = ["LinkAuthProvider", "LinkAuthResult", "DummyLinkAuth"]
