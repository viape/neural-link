from __future__ import annotations

from neural_link.security.auth import DummyLinkAuth


def test_dummy_autoriza_sempre():
    resultado = DummyLinkAuth().authenticate("fone-1", {})
    assert resultado.authorized is True
    assert resultado.device_id == "fone-1"
