"""Fala com o `neural_gateway` da plataforma. Cliente WebSocket standalone
(`ws_client.py`) + gestão de ligação/buffer (`link_gateway.py`)."""

from __future__ import annotations

from .link_gateway import LinkGateway
from .ws_client import WebSocketClient, WebSocketConnectionError

__all__ = ["LinkGateway", "WebSocketClient", "WebSocketConnectionError"]
