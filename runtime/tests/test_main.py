"""`main.py` passa a carregar sempre, por omissão, o caminho oficial
/etc/neural-link/config.toml — sem exigir `--config` explícito (o systemd
real invoca `ExecStart=... -m neural_link.runtime.main` sem argumentos).
`boot()` é substituído por um duplo que devolve componentes já com
`shutdown_requested=True`, para o loop principal nunca correr — só
interessa aqui QUE configuração chega a `boot()`, não o resto do arranque
(já coberto por test_boot_sequence.py)."""

from __future__ import annotations

from neural_link.runtime import device_state as estados
from neural_link.runtime import main as main_module
from neural_link.runtime.boot import DeviceRuntimeComponents, DriverSet
from neural_link.runtime.configuration import DeviceConfig
from neural_link.runtime.drivers.raspberry_pi import NullButtonDriver, NullLEDDriver
from neural_link.runtime.lifecycle import DeviceStateMachine


class _AudioNula:
    def stop(self) -> None:
        pass


class _ConexaoNula:
    def disconnect(self) -> None:
        pass


def _componentes_ja_desligados() -> DeviceRuntimeComponents:
    sm = DeviceStateMachine(initial=estados.BOOTING)
    sm.shutdown_requested = True  # o loop principal não chega a correr
    return DeviceRuntimeComponents(
        state_machine=sm,
        connection=_ConexaoNula(),
        offline_queue=None,
        heartbeat=None,
        device_manager=None,
        drivers=DriverSet(audio=_AudioNula(), network=None, storage=None,
                           led=NullLEDDriver(), button=NullButtonDriver()),
    )


def test_caminho_por_omissao_e_o_oficial():
    args = main_module._analisar_argumentos([])
    assert args.config == "/etc/neural-link/config.toml"
    assert args.config == main_module.CAMINHO_CONFIG_OFICIAL


def test_ficheiro_inexistente_mantem_o_comportamento_atual_de_omissoes(
    tmp_path, monkeypatch,
):
    capturado = {}

    def _boot_falso(config, *, version):
        capturado["config"] = config
        return _componentes_ja_desligados()

    monkeypatch.setattr(main_module, "boot", _boot_falso)

    caminho = tmp_path / "nao_existe.toml"
    codigo = main_module.main(["--config", str(caminho)])

    assert codigo == 0
    assert capturado["config"].source == "(defaults)"
    assert capturado["config"].hostname == DeviceConfig().hostname
    assert capturado["config"].gateway_port == DeviceConfig().gateway_port


def test_ficheiro_existente_e_carregado_e_chega_ao_boot(tmp_path, monkeypatch):
    caminho = tmp_path / "config.toml"
    caminho.write_text(
        'hostname = "dispositivo-01"\n'
        'tenant = "empresa_a"\n'
        "\n"
        "[gateway]\n"
        'host = "cloud.exemplo.invalid"\n'
        "port = 9999\n"
    )

    capturado = {}

    def _boot_falso(config, *, version):
        capturado["config"] = config
        return _componentes_ja_desligados()

    monkeypatch.setattr(main_module, "boot", _boot_falso)

    codigo = main_module.main(["--config", str(caminho)])

    assert codigo == 0
    cfg = capturado["config"]
    assert cfg.source == str(caminho)
    assert cfg.hostname == "dispositivo-01"
    assert cfg.gateway_host == "cloud.exemplo.invalid"
    assert cfg.gateway_port == 9999


def test_runtime_usa_a_mesma_instancia_devolvida_por_load_config(
    tmp_path, monkeypatch,
):
    """Não chega ler o ficheiro certo — a instância que sai de
    load_config() tem de ser a MESMA que chega a boot(), não uma cópia
    reconstruída à parte."""
    caminho = tmp_path / "config.toml"
    caminho.write_text('hostname = "dispositivo-02"\n')

    original_load_config = main_module.load_config
    devolvida = {}

    def _load_config_espia(path):
        cfg = original_load_config(path)
        devolvida["cfg"] = cfg
        return cfg

    capturado = {}

    def _boot_falso(config, *, version):
        capturado["config"] = config
        return _componentes_ja_desligados()

    monkeypatch.setattr(main_module, "load_config", _load_config_espia)
    monkeypatch.setattr(main_module, "boot", _boot_falso)

    main_module.main(["--config", str(caminho)])

    assert capturado["config"] is devolvida["cfg"]
