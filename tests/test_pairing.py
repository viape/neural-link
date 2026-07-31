from __future__ import annotations

import pytest

from neural_link.pairing.pairing import PairingManager


def test_constroi_livremente():
    PairingManager()


@pytest.mark.parametrize("chamada", [
    lambda m: m.start_pairing("fone-1"),
    lambda m: m.confirm_pairing("fone-1", "123456"),
    lambda m: m.forget("fone-1"),
])
def test_todos_os_metodos_nao_implementados(chamada):
    with pytest.raises(NotImplementedError):
        chamada(PairingManager())
