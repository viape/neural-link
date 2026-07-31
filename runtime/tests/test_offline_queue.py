from __future__ import annotations

import pytest

from neural_link.runtime.offline_queue import (AUDIO, COMMANDS, EVENTS,
                                                 TELEMETRY, OfflineQueue)


def test_categorias_isoladas():
    fila = OfflineQueue()
    fila.enqueue(AUDIO, {"a": 1})
    fila.enqueue(COMMANDS, {"c": 1})
    assert fila.size(AUDIO) == 1
    assert fila.size(COMMANDS) == 1
    assert fila.size(TELEMETRY) == 0
    assert len(fila) == 2


def test_categoria_desconhecida_levanta():
    fila = OfflineQueue()
    with pytest.raises(ValueError):
        fila.enqueue("nao_existe", {})


def test_flush_category():
    fila = OfflineQueue()
    fila.enqueue(EVENTS, {"n": 1})
    fila.enqueue(EVENTS, {"n": 2})
    enviadas = []
    resultado = fila.flush_category(EVENTS, lambda p: enviadas.append(p) or True)
    assert resultado == 2
    assert enviadas == [{"n": 1}, {"n": 2}]


def test_flush_all_respeita_ordem_por_categoria():
    fila = OfflineQueue()
    fila.enqueue(AUDIO, {"cat": "audio"})
    fila.enqueue(COMMANDS, {"cat": "commands"})
    fila.enqueue(TELEMETRY, {"cat": "telemetry"})
    fila.enqueue(EVENTS, {"cat": "events"})

    ordem = []

    def _enviar(categoria, payload):
        ordem.append(categoria)
        return True

    resultado = fila.flush_all(_enviar)
    assert ordem == [AUDIO, COMMANDS, TELEMETRY, EVENTS]
    assert resultado == {AUDIO: 1, COMMANDS: 1, TELEMETRY: 1, EVENTS: 1}
    assert len(fila) == 0


def test_desacoplada_do_gateway():
    """Guarda de arquitetura: este módulo nunca importa LinkGateway."""
    import ast
    from pathlib import Path

    caminho = Path(__file__).resolve().parent.parent / "offline_queue.py"
    arvore = ast.parse(caminho.read_text())
    for no in ast.walk(arvore):
        if isinstance(no, ast.ImportFrom) and no.module:
            assert "link_gateway" not in no.module
            assert "LinkGateway" not in [a.name for a in no.names]
