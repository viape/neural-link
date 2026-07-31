"""Fixtures — mesmo padrão de `neural_gateway/tests/conftest.py`: sem
rede, sem LLM real."""

from __future__ import annotations

import pytest

from neural_runtime import CloudRuntime, RuntimeConfig
from neural_runtime.configuration.config import CoreRuntimeConfig


def _sem_rede(monkeypatch):
    from neural_core.runtime import composition
    monkeypatch.setattr(composition, "cloud_alive", lambda *a, **k: False)


@pytest.fixture
def cloud_runtime(monkeypatch):
    _sem_rede(monkeypatch)
    cfg = RuntimeConfig(core_config=CoreRuntimeConfig(llm_provider="none"))
    rt = CloudRuntime(cfg)
    rt.initialize()
    rt.start()
    yield rt
    rt.request_shutdown()
    rt.shutdown()
