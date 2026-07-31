from __future__ import annotations

import pytest

from neural_link.ble.stubs import UnimplementedBleAdapter


def test_constroi_livremente():
    UnimplementedBleAdapter(qualquer="config")


def test_scan_e_connect_nao_implementados():
    adapter = UnimplementedBleAdapter()
    with pytest.raises(NotImplementedError):
        adapter.scan()
    with pytest.raises(NotImplementedError):
        adapter.connect("aa:bb:cc:dd:ee:ff")


def test_disconnect_e_receive_nunca_rebentam():
    adapter = UnimplementedBleAdapter()
    adapter.disconnect("aa:bb:cc:dd:ee:ff")
    assert adapter.receive("aa:bb:cc:dd:ee:ff") is None
