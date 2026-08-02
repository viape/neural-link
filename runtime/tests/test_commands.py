from __future__ import annotations

from neural_link.runtime.commands import (COMANDOS_AUDIO, COMANDOS_CONHECIDOS,
                                           OTA_AVAILABLE, PLAY_AUDIO, REBOOT,
                                           SPEAK, STOP_AUDIO, handle_command)


def _handle(tipo, **payload):
    return handle_command(
        tipo, payload, correlation_id="c-1", device_id="pi-01",
        tenant="empresa_a", token="segredo", state_provider=lambda: "ONLINE",
    )


def test_ping_devolve_pong():
    ack, resultado = _handle("Ping")
    assert ack["type"] == "Ack"
    assert ack["correlation_id"] == "c-1"
    assert resultado["type"] == "CommandResult"
    assert resultado["correlation_id"] == "c-1"
    assert resultado["pong"] is True


def test_get_status_devolve_o_estado_atual():
    _, resultado = _handle("GetStatus")
    assert resultado["state"] == "ONLINE"


def test_comandos_placeholder_nunca_tocam_hardware_devolvem_not_implemented():
    for comando in ("PlayAudio", "StopAudio", "Speak", "Reboot", "OTAAvailable"):
        _, resultado = _handle(comando)
        assert resultado["status"] == "not_implemented", comando


def test_ack_e_result_carregam_identidade():
    ack, resultado = _handle("Ping")
    for envelope in (ack, resultado):
        assert envelope["device_id"] == "pi-01"
        assert envelope["tenant"] == "empresa_a"
        assert envelope["token"] == "segredo"


def test_comando_desconhecido_nunca_levanta():
    ack, resultado = handle_command(
        "AlgoNovo", {}, correlation_id="c-2", device_id="pi-01",
        tenant="empresa_a", token="segredo", state_provider=lambda: "ONLINE",
    )
    assert resultado["status"] == "unknown_command"


def test_todos_os_comandos_do_pedido_estao_cobertos():
    assert set(COMANDOS_CONHECIDOS) == {
        "PlayAudio", "StopAudio", "Speak", "Reboot", "OTAAvailable", "Ping", "GetStatus",
    }


def test_audio_result_omisso_mantem_not_implemented():
    """Guarda de regressão: quem chamar sem passar audio_result (como
    já acontecia antes desta ronda) continua a ver exatamente o mesmo
    comportamento de sempre."""
    for comando in (PLAY_AUDIO, STOP_AUDIO, SPEAK):
        _, resultado = _handle(comando)
        assert resultado["status"] == "not_implemented", comando


def test_audio_result_e_devolvido_tal_e_qual_para_comandos_de_audio():
    for comando in (PLAY_AUDIO, STOP_AUDIO, SPEAK):
        _, resultado = handle_command(
            comando, {}, correlation_id="c-1", device_id="pi-01", tenant="empresa_a",
            token="segredo", state_provider=lambda: "ONLINE",
            audio_result={"status": "ok"},
        )
        assert resultado["status"] == "ok", comando

        _, resultado_erro = handle_command(
            comando, {}, correlation_id="c-1", device_id="pi-01", tenant="empresa_a",
            token="segredo", state_provider=lambda: "ONLINE",
            audio_result={"status": "error", "reason": "sem altifalante"},
        )
        assert resultado_erro == {
            "type": "CommandResult", "device_id": "pi-01", "tenant": "empresa_a",
            "token": "segredo", "correlation_id": "c-1",
            "status": "error", "reason": "sem altifalante",
        }, comando


def test_reboot_e_ota_ignoram_audio_result():
    """Reboot/OTAAvailable nunca estão em COMANDOS_AUDIO — passar
    audio_result não muda nada, continuam not_implemented."""
    for comando in (REBOOT, OTA_AVAILABLE):
        assert comando not in COMANDOS_AUDIO
        _, resultado = handle_command(
            comando, {}, correlation_id="c-1", device_id="pi-01", tenant="empresa_a",
            token="segredo", state_provider=lambda: "ONLINE",
            audio_result={"status": "ok"},
        )
        assert resultado["status"] == "not_implemented", comando
