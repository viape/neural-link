"""`OfflineQueue` — arquitetura profissional por cima do `OfflineBuffer`
já existente (`neural_link.buffering`), nunca uma fila nova: quatro
categorias (áudio/comandos/telemetria/eventos), cada uma o MESMO
`OfflineBuffer` de sempre, só com roteamento por categoria por cima.

DESACOPLADA do Gateway por desenho: `flush_all`/`flush_category` recebem
uma função de envio (`send_fn`) — este ficheiro nunca importa
`neural_link.gateway.LinkGateway`. Quem liga as duas coisas é o
`ConnectionManager` (`connection.py`), não isto."""

from __future__ import annotations

from typing import Callable

from ..buffering.buffer import OfflineBuffer

AUDIO = "audio"
COMMANDS = "commands"
TELEMETRY = "telemetry"
EVENTS = "events"

CATEGORIAS = (AUDIO, COMMANDS, TELEMETRY, EVENTS)


class OfflineQueue:
    def __init__(self, *, max_size_per_category: int = 1000) -> None:
        self._filas: dict[str, OfflineBuffer] = {
            categoria: OfflineBuffer(max_size=max_size_per_category)
            for categoria in CATEGORIAS
        }

    def enqueue(self, category: str, payload: dict) -> None:
        if category not in self._filas:
            raise ValueError(f"categoria desconhecida: {category!r}")
        self._filas[category].enqueue(payload)

    def __len__(self) -> int:
        return sum(len(fila) for fila in self._filas.values())

    def size(self, category: str) -> int:
        return len(self._filas[category])

    def flush_category(self, category: str, send_fn: Callable[[dict], bool]) -> int:
        return self._filas[category].flush(send_fn)

    def flush_all(self, send_fn: Callable[[str, dict], bool]) -> dict[str, int]:
        """`send_fn(categoria, payload) -> bool`. Ordem fixa — telemetria
        e eventos nunca atrasam áudio/comandos (mais sensíveis a tempo)."""
        resultado = {}
        for categoria in (AUDIO, COMMANDS, TELEMETRY, EVENTS):
            resultado[categoria] = self.flush_category(
                categoria, lambda payload, c=categoria: send_fn(c, payload)
            )
        return resultado
