"""Guarda de arquitetura — a prova executável de que `neural_link.runtime`
já não depende do Neural Core. `AudioChunk`/`AudioSource`/`Microphone`
mudaram-se para `neural_audio` (fonte partilhada com o próprio
`neural_core`) — zero import de `neural_core` continua a ser exigível em
qualquer ficheiro deste subpacote, produção ou testes."""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _modulos_importados(caminho: Path) -> set[str]:
    arvore = ast.parse(caminho.read_text(), filename=str(caminho))
    nomes = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                nomes.add(alias.name)
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            nomes.add(no.module)
    return nomes


def test_zero_imports_de_neural_core_em_todo_o_subpacote():
    violacoes = []
    for caminho in RAIZ.rglob("*.py"):
        importados = _modulos_importados(caminho)
        for modulo in importados:
            if modulo == "neural_core" or modulo.startswith("neural_core."):
                violacoes.append((str(caminho.relative_to(RAIZ)), modulo))
    assert not violacoes, f"neural_link.runtime ainda importa neural_core: {violacoes}"
