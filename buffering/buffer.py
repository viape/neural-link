"""`OfflineBuffer` — a fila para quando a Internet falha.

Fila real em memória (sem persistência em disco nesta v1 — "nunca
hardware" também significa não assumir que tipo de armazenamento
persistente uma placa qualquer vai ter; fica documentado como extensão
futura, não escondido). FIFO: a ordem em que as mensagens foram ditas é a
ordem em que chegam à nuvem quando a ligação volta."""

from __future__ import annotations

from collections import deque
from typing import Callable


class OfflineBuffer:
    def __init__(self, *, max_size: int = 1000) -> None:
        self._fila: deque[dict] = deque(maxlen=max_size)

    def enqueue(self, payload: dict) -> None:
        self._fila.append(payload)

    def __len__(self) -> int:
        return len(self._fila)

    def flush(self, send_fn: Callable[[dict], bool]) -> int:
        """Tenta `send_fn(payload)` por ordem. Para no primeiro falhanço
        (`send_fn` devolve `False` ou levanta) — nunca envia fora de ordem,
        nunca descarta o que ainda não foi confirmado. Devolve quantas
        mensagens saíram com sucesso desta vez."""
        enviadas = 0
        while self._fila:
            payload = self._fila[0]
            try:
                sucesso = send_fn(payload)
            except Exception:
                sucesso = False
            if not sucesso:
                break
            self._fila.popleft()
            enviadas += 1
        return enviadas
