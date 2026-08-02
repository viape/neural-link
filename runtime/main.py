"""O processo do Runtime — um dispositivo inteiro, residente.

    python -m neural_link.runtime.main

Carrega sempre /etc/neural-link/config.toml por omissão (o caminho
oficial — ver CAMINHO_CONFIG_OFICIAL); `--config outro/caminho.toml`
continua a existir para testes/casos excecionais. Sem o ficheiro no
caminho oficial, arranca à mesma nas omissões de `configuration.py`.

Mesmo idioma de sinal/loop de `neural_runtime/cloud/tenant/entrypoint.py`:
um handler de sinal só marca uma flag (`DeviceStateMachine.
shutdown_requested`); o trabalho acontece sempre no loop principal, nunca
dentro do handler. "Aguardar eventos" é este loop — a última etapa da
sequência de arranque pedida."""

from __future__ import annotations

import argparse
import base64
import logging
import sys
import time

from . import device_state as estados
from .boot import boot
from .commands import (COMANDOS_AUDIO, COMANDOS_CONHECIDOS, PLAY_AUDIO,
                        SPEAK, STOP_AUDIO, handle_command)
from .configuration import load as load_config
from .offline_queue import COMMANDS, TELEMETRY

log = logging.getLogger("neural_link.runtime")

_INTERVALO_LOOP_S = 0.5

# O único caminho oficial de configuração — o systemd real (ver
# `service.py::unit_file_content`) invoca `main.py` sem argumentos, por
# isso é este o caminho que o Runtime tem de tentar por omissão. `load()`
# (configuration.py, inalterado) já trata ficheiro em falta/corrompido
# caindo nas omissões — este caminho só lhe diz ONDE procurar primeiro.
CAMINHO_CONFIG_OFICIAL = "/etc/neural-link/config.toml"


def _analisar_argumentos(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Neural Link Runtime")
    parser.add_argument("--config", default=CAMINHO_CONFIG_OFICIAL)
    parser.add_argument("--version", default="0.1.0")
    return parser.parse_args(argv)


def _tocar_audio(speaker, audio_b64: str) -> dict:
    """O único sítio que toca no driver de som — `handle_command`
    continua pura. Devolve sempre um resultado honesto: `audio_b64` em
    falta/inválido ou sem driver nunca finge sucesso."""
    if speaker is None or not audio_b64:
        return {"status": "error", "reason": "no_speaker_or_audio"}
    try:
        speaker.play(base64.b64decode(audio_b64))
        return {"status": "ok"}
    except Exception as exc:                       # noqa: BLE001
        return {"status": "error", "reason": str(exc)}


def _parar_audio(speaker) -> dict:
    if speaker is None:
        return {"status": "error", "reason": "no_speaker"}
    speaker.stop()
    return {"status": "ok"}


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    args = _analisar_argumentos(argv if argv is not None else sys.argv[1:])

    config = load_config(args.config)
    componentes = boot(config, version=args.version)
    sm = componentes.state_machine
    sm.install_signal_handlers()

    # Só aqui, não em boot() — arrancar o microfone a sério (placa real)
    # é um passo de "ir a produção", simétrico ao .stop() do finally.
    # Nem todo `AudioDriver` injetado nos testes implementa start().
    if hasattr(componentes.drivers.audio, "start"):
        componentes.drivers.audio.start()
    if componentes.drivers.speaker is not None and hasattr(componentes.drivers.speaker, "start"):
        componentes.drivers.speaker.start()

    log.info("neural-link a arrancar — device_id=%s tenant=%s",
              config.device_id, config.tenant)

    try:
        while not sm.shutdown_requested:
            componentes.connection.poll()
            componentes.audio_pipeline.poll()

            resposta = componentes.connection.receive()
            if resposta is not None:
                tipo = resposta.get("type")
                if tipo in COMANDOS_CONHECIDOS:
                    audio_result = None
                    if tipo in (PLAY_AUDIO, SPEAK):
                        audio_result = _tocar_audio(
                            componentes.drivers.speaker, resposta.get("audio_b64", ""))
                    elif tipo == STOP_AUDIO:
                        audio_result = _parar_audio(componentes.drivers.speaker)
                    ack, resultado = handle_command(
                        tipo, resposta, correlation_id=resposta.get("correlation_id", ""),
                        device_id=config.device_id, tenant=config.tenant, token=config.token,
                        state_provider=lambda: sm.state, audio_result=audio_result,
                    )
                    if not componentes.connection.send(ack):
                        componentes.offline_queue.enqueue(COMMANDS, ack)
                    if not componentes.connection.send(resultado):
                        componentes.offline_queue.enqueue(COMMANDS, resultado)
                else:
                    log.info("mensagem recebida da Cloud: %s", resposta)

            if componentes.connection.connected:
                componentes.offline_queue.flush_all(
                    lambda categoria, payload: componentes.connection.send(payload)
                )

            if componentes.heartbeat.due():
                payload = componentes.heartbeat.beat()
                if not componentes.connection.send(payload.as_dict()):
                    componentes.offline_queue.enqueue(TELEMETRY, payload.as_dict())

            time.sleep(_INTERVALO_LOOP_S)
    finally:
        log.info("neural-link a desligar")
        sm.transition_to(estados.SHUTTING_DOWN)
        componentes.drivers.audio.stop()
        if componentes.drivers.speaker is not None:
            componentes.drivers.speaker.stop()
        componentes.connection.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
