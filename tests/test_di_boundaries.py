"""Guarda de arquitetura — a prova executável de que o Neural Link já não
depende do Neural Core.

Antes desta ronda, `neural_link` importava `AudioChunk`/`AudioSource`/
`VoiceActivityDetector`/`WakeWordProvider`/`AdaptiveEnergyVAD`/
`SimulatedWakeWord`/`Microphone` de `neural_core.interfaces`/
`neural_core.integrations.speech`. Esses símbolos foram extraídos para
`neural_audio` (a fonte partilhada com o próprio `neural_core`, que
também passou a consumi-los por lá). O pacote DEPLOYÁVEL (tudo o que
correria no Raspberry Pi) tem agora **zero** imports de `neural_core`.

Duas exceções explícitas, e só estas: ficheiros de teste que montam o
lado CLOUD para o teste de integração ponta-a-ponta (`test_end_to_end_
link_to_cloud.py` e o `conftest.py` que o serve) — isso nunca vai para
o Raspberry Pi, é só o "servidor de mentira" contra o qual o Neural Link
se testa. Qualquer outro ficheiro, produção ou teste, é proibido."""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Só estes dois — nunca "tests/" inteiro. Um novo ficheiro de teste que
# precise de neural_core tem de justificar a sua própria exceção aqui,
# não herdar uma isenção silenciosa da pasta.
ISENTOS = {
    "tests/conftest.py",
    "tests/test_end_to_end_link_to_cloud.py",
}


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


def test_zero_imports_de_neural_core_fora_das_excecoes():
    violacoes = []
    for caminho in RAIZ.rglob("*.py"):
        relativo = str(caminho.relative_to(RAIZ))
        if relativo in ISENTOS:
            continue
        importados = _modulos_importados(caminho)
        for modulo in importados:
            if modulo == "neural_core" or modulo.startswith("neural_core."):
                violacoes.append((relativo, modulo))
    assert not violacoes, (
        f"neural_link ainda importa neural_core — o Raspberry Pi não "
        f"consegue correr isto sozinho: {violacoes}"
    )


def test_ws_client_e_standalone():
    """`ws_client.py` nunca importa nem `neural_core`, nem `neural_audio`,
    nem `neural_runtime`/`neural_gateway` — fala só o protocolo de rede,
    de propósito (um Neural Link real não teria o resto instalado)."""
    caminho = RAIZ / "gateway" / "ws_client.py"
    importados = _modulos_importados(caminho)
    proibidos = [
        m for m in importados
        if m.startswith(("neural_core", "neural_audio", "neural_runtime", "neural_gateway"))
    ]
    assert not proibidos, f"ws_client.py deixou de ser standalone: {proibidos}"
