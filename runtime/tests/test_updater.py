from __future__ import annotations

import pytest

from neural_link.runtime.updater import (OtaUpdater, UnimplementedDownloadStrategy,
                                          UnimplementedRollbackStrategy,
                                          UnimplementedVersionChecker,
                                          UpdateInfo, UpdateState)
from neural_link.updates.ota import OtaUpdater as OtaUpdaterOriginal


def test_ota_updater_reexportado_e_o_mesmo():
    assert OtaUpdater is OtaUpdaterOriginal


def test_update_state_tem_os_estados_pedidos():
    esperados = {"IDLE", "CHECKING", "DOWNLOADING", "APPLYING",
                 "ROLLING_BACK", "DONE", "FAILED"}
    assert {e.value for e in UpdateState} == esperados


def test_version_checker_preparado_nao_implementado():
    with pytest.raises(NotImplementedError):
        UnimplementedVersionChecker().latest_version("stable")


def test_download_strategy_preparado_nao_implementado():
    info = UpdateInfo(version="1.1.0", url="https://example.invalid/fw.bin")
    with pytest.raises(NotImplementedError):
        UnimplementedDownloadStrategy().download(info, destination="/tmp/fw.bin")


def test_rollback_strategy_preparado_nao_implementado():
    estrategia = UnimplementedRollbackStrategy()
    with pytest.raises(NotImplementedError):
        estrategia.snapshot()
    with pytest.raises(NotImplementedError):
        estrategia.restore("qualquer")
