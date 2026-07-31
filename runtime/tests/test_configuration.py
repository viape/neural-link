from __future__ import annotations

from neural_link.runtime.configuration import DeviceConfig, load


def test_sem_caminho_devolve_omissoes():
    cfg = load(None)
    assert cfg.source == "(defaults)"
    assert cfg.hostname == "neural-link"


def test_ficheiro_em_falta_devolve_omissoes(tmp_path):
    cfg = load(tmp_path / "nao_existe.toml")
    assert cfg.source == "(defaults)"


def test_ficheiro_corrompido_devolve_omissoes(tmp_path):
    caminho = tmp_path / "config.toml"
    caminho.write_text("isto nao e = toml valido [[[")
    cfg = load(caminho)
    assert cfg.source == "(defaults)"


def test_ficheiro_valido_e_lido(tmp_path):
    caminho = tmp_path / "config.toml"
    caminho.write_text(
        'hostname = "device-01"\n'
        'tenant = "empresa_a"\n'
        'device_id = "abc123"\n'
        "\n"
        "[gateway]\n"
        'host = "cloud.example.invalid"\n'
        "port = 9999\n"
        "\n"
        "[heartbeat]\n"
        "interval_s = 15.0\n"
    )
    cfg = load(caminho)
    assert cfg.hostname == "device-01"
    assert cfg.tenant == "empresa_a"
    assert cfg.device_id == "abc123"
    assert cfg.gateway_host == "cloud.example.invalid"
    assert cfg.gateway_port == 9999
    assert cfg.heartbeat_interval_s == 15.0
    assert cfg.source == str(caminho)


def test_secoes_em_falta_mantem_omissoes(tmp_path):
    caminho = tmp_path / "config.toml"
    caminho.write_text('hostname = "so-isto"\n')
    cfg = load(caminho)
    assert cfg.hostname == "so-isto"
    assert cfg.gateway_port == DeviceConfig().gateway_port
