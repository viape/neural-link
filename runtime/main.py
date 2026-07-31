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
import logging
import sys
import time

from . import device_state as estados
from .boot import boot
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


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    args = _analisar_argumentos(argv if argv is not None else sys.argv[1:])

    config = load_config(args.config)
    componentes = boot(config, version=args.version)
    sm = componentes.state_machine
    sm.install_signal_handlers()

    log.info("neural-link a arrancar — device_id=%s tenant=%s",
              config.device_id, config.tenant)

    try:
        while not sm.shutdown_requested:
            componentes.connection.poll()

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
        componentes.connection.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
