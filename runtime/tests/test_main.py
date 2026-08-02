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


class _SpeakerFalso:
    def __init__(self) -> None:
        self.tocados: list[bytes] = []
        self.parado = False

    def play(self, wav_bytes: bytes) -> None:
        self.tocados.append(wav_bytes)

    def stop(self) -> None:
        self.parado = True


class _ConexaoNula:
    def disconnect(self) -> None:
        pass


class _AudioPipelineNulo:
    def poll(self) -> None:
        pass


class _AudioPipelineComDormir:
    def __init__(self) -> None:
        self.adormeceu = False

    def poll(self) -> None:
        pass

    def dormir(self) -> None:
        self.adormeceu = True


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
        audio_pipeline=_AudioPipelineNulo(),
    )


def test_caminho_por_omissao_e_o_oficial():
    args = main_module._analisar_argumentos([])
    assert args.config == "/etc/neural-link/config.toml"
    assert args.config == main_module.CAMINHO_CONFIG_OFICIAL


def test_ficheiro_inexistente_mantem_o_comportamento_atual_de_omissoes(
    tmp_path, monkeypatch,
):
    capturado = {}

    def _boot_falso(config, *, version, wake_word=None):
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

    def _boot_falso(config, *, version, wake_word=None):
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


class _ConexaoComComando:
    """Devolve UMA mensagem em `receive()`, depois `None` sempre — mesmo
    idioma de um socket real que só tem uma frame pendente."""

    def __init__(self, resposta: dict) -> None:
        self._resposta: dict | None = resposta
        self.enviados: list[dict] = []
        self.connected = False

    def poll(self) -> None:
        pass

    def receive(self):
        resposta, self._resposta = self._resposta, None
        return resposta

    def send(self, payload: dict) -> bool:
        self.enviados.append(payload)
        return True

    def disconnect(self) -> None:
        pass


class _HeartbeatNuncaDevido:
    def due(self) -> bool:
        return False


def _componentes_com_comando_pendente(
    resposta: dict, *, speaker: _SpeakerFalso | None = None,
    audio_pipeline=None,
) -> tuple[DeviceRuntimeComponents, DeviceStateMachine, _ConexaoComComando]:
    sm = DeviceStateMachine(initial=estados.BOOTING)
    conexao = _ConexaoComComando(resposta)
    componentes = DeviceRuntimeComponents(
        state_machine=sm,
        connection=conexao,
        offline_queue=None,
        heartbeat=_HeartbeatNuncaDevido(),
        device_manager=None,
        drivers=DriverSet(audio=_AudioNula(), network=None, storage=None,
                           led=NullLEDDriver(), button=NullButtonDriver(),
                           speaker=speaker),
        audio_pipeline=audio_pipeline or _AudioPipelineNulo(),
    )
    return componentes, sm, conexao


def test_main_despacha_comando_conhecido_envia_ack_depois_result(tmp_path, monkeypatch):
    componentes, sm, conexao = _componentes_com_comando_pendente(
        {"type": "Ping", "correlation_id": "c-1"})

    def _boot_falso(config, *, version, wake_word=None):
        return componentes

    def _parar_apos_uma_iteracao(*_a, **_k):
        sm.shutdown_requested = True

    monkeypatch.setattr(main_module, "boot", _boot_falso)
    monkeypatch.setattr(main_module.time, "sleep", _parar_apos_uma_iteracao)

    caminho = tmp_path / "nao_existe.toml"
    codigo = main_module.main(["--config", str(caminho)])

    assert codigo == 0
    assert len(conexao.enviados) == 2
    assert conexao.enviados[0]["type"] == "Ack"
    assert conexao.enviados[1]["type"] == "CommandResult"
    assert conexao.enviados[1]["pong"] is True
    for envelope in conexao.enviados:
        assert envelope["correlation_id"] == "c-1"


def test_main_despacha_speak_toca_no_driver_de_som_e_devolve_ok(tmp_path, monkeypatch):
    import base64
    audio_b64 = base64.b64encode(b"RIFFxxxxWAVEfake").decode("ascii")
    speaker = _SpeakerFalso()
    componentes, sm, conexao = _componentes_com_comando_pendente(
        {"type": "Speak", "correlation_id": "c-2", "audio_b64": audio_b64},
        speaker=speaker,
    )

    def _boot_falso(config, *, version, wake_word=None):
        return componentes

    def _parar_apos_uma_iteracao(*_a, **_k):
        sm.shutdown_requested = True

    monkeypatch.setattr(main_module, "boot", _boot_falso)
    monkeypatch.setattr(main_module.time, "sleep", _parar_apos_uma_iteracao)

    codigo = main_module.main(["--config", str(tmp_path / "nao_existe.toml")])

    assert codigo == 0
    assert speaker.tocados == [b"RIFFxxxxWAVEfake"]
    assert conexao.enviados[1]["status"] == "ok"


def test_main_despacha_sleep_para_a_pipeline_de_audio(tmp_path, monkeypatch):
    pipeline = _AudioPipelineComDormir()
    componentes, sm, conexao = _componentes_com_comando_pendente(
        {"type": "Sleep", "correlation_id": "c-4"}, audio_pipeline=pipeline,
    )

    def _boot_falso(config, *, version, wake_word=None):
        return componentes

    def _parar_apos_uma_iteracao(*_a, **_k):
        sm.shutdown_requested = True

    monkeypatch.setattr(main_module, "boot", _boot_falso)
    monkeypatch.setattr(main_module.time, "sleep", _parar_apos_uma_iteracao)

    codigo = main_module.main(["--config", str(tmp_path / "nao_existe.toml")])

    assert codigo == 0
    assert pipeline.adormeceu is True
    assert conexao.enviados[1]["status"] == "ok"


def test_main_despacha_stop_audio_para_o_driver(tmp_path, monkeypatch):
    speaker = _SpeakerFalso()
    componentes, sm, conexao = _componentes_com_comando_pendente(
        {"type": "StopAudio", "correlation_id": "c-3"}, speaker=speaker,
    )

    def _boot_falso(config, *, version, wake_word=None):
        return componentes

    def _parar_apos_uma_iteracao(*_a, **_k):
        sm.shutdown_requested = True

    monkeypatch.setattr(main_module, "boot", _boot_falso)
    monkeypatch.setattr(main_module.time, "sleep", _parar_apos_uma_iteracao)

    codigo = main_module.main(["--config", str(tmp_path / "nao_existe.toml")])

    assert codigo == 0
    assert speaker.parado is True
    assert conexao.enviados[1]["status"] == "ok"


def test_main_speak_sem_driver_devolve_erro_honesto(tmp_path, monkeypatch):
    """Sem `speaker` (omissão None) o resultado nunca finge sucesso."""
    componentes, sm, conexao = _componentes_com_comando_pendente(
        {"type": "Speak", "correlation_id": "c-4", "audio_b64": "abc"})

    def _boot_falso(config, *, version, wake_word=None):
        return componentes

    def _parar_apos_uma_iteracao(*_a, **_k):
        sm.shutdown_requested = True

    monkeypatch.setattr(main_module, "boot", _boot_falso)
    monkeypatch.setattr(main_module.time, "sleep", _parar_apos_uma_iteracao)

    main_module.main(["--config", str(tmp_path / "nao_existe.toml")])

    assert conexao.enviados[1]["status"] == "error"


def test_main_mensagem_sem_type_conhecido_cai_no_log_antigo(tmp_path, monkeypatch):
    """Guarda de regressão: uma resposta legacy (`{"ok": True}`, sem
    `type` reconhecido) NUNCA é tratada como comando — comportamento
    idêntico ao de antes da Fase B."""
    componentes, sm, conexao = _componentes_com_comando_pendente({"ok": True})

    def _boot_falso(config, *, version, wake_word=None):
        return componentes

    def _parar_apos_uma_iteracao(*_a, **_k):
        sm.shutdown_requested = True

    monkeypatch.setattr(main_module, "boot", _boot_falso)
    monkeypatch.setattr(main_module.time, "sleep", _parar_apos_uma_iteracao)

    codigo = main_module.main(["--config", str(tmp_path / "nao_existe.toml")])

    assert codigo == 0
    assert conexao.enviados == []  # nada foi enviado — só logado


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

    def _boot_falso(config, *, version, wake_word=None):
        capturado["config"] = config
        return _componentes_ja_desligados()

    monkeypatch.setattr(main_module, "load_config", _load_config_espia)
    monkeypatch.setattr(main_module, "boot", _boot_falso)

    main_module.main(["--config", str(caminho)])

    assert capturado["config"] is devolvida["cfg"]


class _AudioQueRebentaAoArrancar:
    """Simula hardware ausente (ex.: PortAudio não instalado no SO) —
    `start()` levanta, tal como `neural_audio.Microphone` faz de
    verdade nesse caso."""

    def start(self) -> None:
        raise RuntimeError("PortAudio library not found")

    def stop(self) -> None:
        pass


class _SpeakerQueRebentaAoArrancar:
    def start(self) -> None:
        raise RuntimeError("PortAudio library not found")

    def stop(self) -> None:
        pass


def test_main_cai_no_null_quando_openwakeword_falha(tmp_path, monkeypatch):
    """Independente de `openwakeword` estar instalado nesta máquina —
    força a falha explicitamente, para o teste não depender do ambiente:
    tem de cair no `NullWakeWordProvider`, nunca `None`, nunca rebentar."""
    from neural_link.audio.pipeline import NullWakeWordProvider

    def _open_wake_word_que_falha(*, model, threshold):
        raise RuntimeError("openwakeword não está instalado")

    monkeypatch.setattr(main_module, "OpenWakeWord", _open_wake_word_que_falha)

    capturado = {}

    def _boot_falso(config, *, version, wake_word=None):
        capturado["wake_word"] = wake_word
        return _componentes_ja_desligados()

    monkeypatch.setattr(main_module, "boot", _boot_falso)

    main_module.main(["--config", str(tmp_path / "nao_existe.toml")])

    assert capturado["wake_word"] is not None
    assert isinstance(capturado["wake_word"], NullWakeWordProvider)


def test_main_cai_no_null_quando_modelo_onnx_esta_em_falta(tmp_path, monkeypatch):
    """Guarda de regressão para um bug real, apanhado ao validar contra o
    openwakeword a sério: com o pacote instalado mas os modelos ONNX por
    descarregar, `Model()` levanta `onnxruntime...NoSuchFile` — que NÃO
    é uma RuntimeError. Um `except RuntimeError` sozinho deixava isto
    escapar e crashava o dispositivo inteiro no arranque."""
    from neural_link.audio.pipeline import NullWakeWordProvider

    def _open_wake_word_que_falha(*, model, threshold):
        raise OSError("modelo ONNX em falta — correr download_models() primeiro")

    monkeypatch.setattr(main_module, "OpenWakeWord", _open_wake_word_que_falha)

    capturado = {}

    def _boot_falso(config, *, version, wake_word=None):
        capturado["wake_word"] = wake_word
        return _componentes_ja_desligados()

    monkeypatch.setattr(main_module, "boot", _boot_falso)

    main_module.main(["--config", str(tmp_path / "nao_existe.toml")])

    assert capturado["wake_word"] is not None
    assert isinstance(capturado["wake_word"], NullWakeWordProvider)


def test_main_usa_o_modelo_e_threshold_configurados(tmp_path, monkeypatch):
    """`_construir_wake_word` tenta mesmo o `OpenWakeWord` com os valores
    do config.toml antes de cair no fallback — prova-se monkeypatchando
    `OpenWakeWord` por um duplo que só regista o que recebeu."""
    capturado = {}

    class _OpenWakeWordFalso:
        def __init__(self, *, model, threshold):
            capturado["model"] = model
            capturado["threshold"] = threshold

    monkeypatch.setattr(main_module, "OpenWakeWord", _OpenWakeWordFalso)

    caminho = tmp_path / "config.toml"
    caminho.write_text("[wake_word]\nmodel = \"alexa\"\nthreshold = 0.8\n")
    config = main_module.load_config(caminho)

    wake = main_module._construir_wake_word(config)

    assert capturado == {"model": "alexa", "threshold": 0.8}
    assert isinstance(wake, _OpenWakeWordFalso)


def test_microfone_ou_altifalante_ausente_nunca_impede_o_arranque(tmp_path, monkeypatch, caplog):
    """Guarda de regressão: hardware de áudio em falta tem de degradar
    (log + continuar), nunca travar o dispositivo inteiro — a mesma
    honestidade que já vale para temperatura/CPU ausentes."""
    sm = DeviceStateMachine(initial=estados.BOOTING)
    sm.shutdown_requested = True
    componentes = DeviceRuntimeComponents(
        state_machine=sm,
        connection=_ConexaoNula(),
        offline_queue=None,
        heartbeat=None,
        device_manager=None,
        drivers=DriverSet(
            audio=_AudioQueRebentaAoArrancar(), network=None, storage=None,
            led=NullLEDDriver(), button=NullButtonDriver(),
            speaker=_SpeakerQueRebentaAoArrancar(),
        ),
        audio_pipeline=_AudioPipelineNulo(),
    )

    def _boot_falso(config, *, version, wake_word=None):
        return componentes

    monkeypatch.setattr(main_module, "boot", _boot_falso)

    with caplog.at_level("WARNING"):
        codigo = main_module.main(["--config", str(tmp_path / "nao_existe.toml")])

    assert codigo == 0
    assert "microfone indisponível" in caplog.text
    assert "altifalante indisponível" in caplog.text
