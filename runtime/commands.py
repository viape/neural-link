"""`handle_command` — só infraestrutura, nunca comportamento: recebe um
comando (`PlayAudio`/`StopAudio`/`Speak`/`Reboot`/`OTAAvailable`/`Ping`/
`GetStatus`), devolve um Ack e um Result. Continua PURA — nunca toca em
áudio/altifalante/rede/hardware nenhum, nem mesmo agora que Speak/
PlayAudio/StopAudio já têm reprodução real: quem toca no driver é
`main.py` (o único sítio que já tinha esse trabalho, para
`drivers.audio.start()`/`.stop()`), que pré-calcula o resultado e
passa-o cá para dentro em `audio_result`. Isto mantém `handle_command`
testável com zero mocks de hardware, exatamente como já era.

`Reboot`/`OTAAvailable` continuam `{"status": "not_implemented"}` —
Reboot não tem nenhuma execução real ainda (decisão explícita: fica
para pedido futuro); OTA fica por implementar por pedido explícito
anterior ("não implementar atualização, projetar arquitetura").

Função pura de propósito — recebe a identidade do dispositivo por
parâmetro em vez de ler `DeviceConfig`/`componentes` diretamente, para
`main.py` a poder chamar com o que já tem em mão, sem `boot()` precisar
de saber nada disto."""

from __future__ import annotations

from typing import Callable

PING = "Ping"
GET_STATUS = "GetStatus"
PLAY_AUDIO = "PlayAudio"
STOP_AUDIO = "StopAudio"
SPEAK = "Speak"
REBOOT = "Reboot"
OTA_AVAILABLE = "OTAAvailable"

COMANDOS_AUDIO = (PLAY_AUDIO, STOP_AUDIO, SPEAK)
COMANDOS_CONHECIDOS = (
    PLAY_AUDIO, STOP_AUDIO, SPEAK, REBOOT, OTA_AVAILABLE, PING, GET_STATUS,
)


def _envelope(*, tipo: str, device_id: str, tenant: str, token: str,
              correlation_id: str, payload: dict) -> dict:
    return {
        "type": tipo, "device_id": device_id, "tenant": tenant, "token": token,
        "correlation_id": correlation_id, **payload,
    }


def handle_command(
    command_type: str, payload: dict, *, correlation_id: str,
    device_id: str, tenant: str, token: str,
    state_provider: Callable[[], str],
    audio_result: dict | None = None,
) -> tuple[dict, dict]:
    """Devolve `(ack, result)`, ambos já prontos para `connection.send()`.
    Nunca levanta — um `command_type` desconhecido não devia chegar aqui
    (quem chama já filtra por `COMANDOS_CONHECIDOS`), mas mesmo assim
    devolve um Result honesto em vez de rebentar.

    `audio_result`: só para PlayAudio/StopAudio/Speak — o resultado JÁ
    CALCULADO por quem chamou (`main.py`, que é quem tem o driver de
    som em mãos), ex.: `{"status": "ok"}` ou `{"status": "error",
    "reason": ...}`. Omissão (`None`) preserva o comportamento antigo
    (`{"status": "not_implemented"}`) — nunca uma alteração silenciosa
    para quem chama sem passar isto."""
    ack = _envelope(tipo="Ack", device_id=device_id, tenant=tenant, token=token,
                     correlation_id=correlation_id, payload={})

    if command_type == PING:
        resultado_payload = {"pong": True}
    elif command_type == GET_STATUS:
        resultado_payload = {"state": state_provider()}
    elif command_type in COMANDOS_AUDIO:
        resultado_payload = audio_result if audio_result is not None else {"status": "not_implemented"}
    elif command_type in COMANDOS_CONHECIDOS:
        resultado_payload = {"status": "not_implemented"}
    else:
        resultado_payload = {"status": "unknown_command"}

    result = _envelope(tipo="CommandResult", device_id=device_id, tenant=tenant, token=token,
                        correlation_id=correlation_id, payload=resultado_payload)
    return ack, result
