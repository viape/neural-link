from __future__ import annotations

import pytest

from neural_link.updates.ota import OtaUpdater, UpdateInfo


def test_constroi_livremente():
    OtaUpdater()


def test_check_for_update_nao_implementado():
    with pytest.raises(NotImplementedError):
        OtaUpdater().check_for_update("1.0.0")


def test_apply_nao_implementado():
    with pytest.raises(NotImplementedError):
        OtaUpdater().apply(UpdateInfo(version="1.1.0", url="https://example.invalid/fw.bin"))
