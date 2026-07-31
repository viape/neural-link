"""Arquitetura completa para `neural-link.service` (systemd): boot
automático, restart automático, logs por `journald`, shutdown correto
(`ExecStop` implícito — o `SIGTERM` que `lifecycle.py` já trata).

`install()`/`uninstall()` nunca tocam no systemd real por omissão nos
testes — o diretório de destino é sempre parametrizável; só quem chamar
isto num Raspberry Pi a sério, sem indicar outro caminho, é que escreve
em `/etc/systemd/system/`."""

from __future__ import annotations

import subprocess
from pathlib import Path

NOME_SERVICO = "neural-link.service"
CAMINHO_SYSTEMD_OMISSAO = Path("/etc/systemd/system")


def unit_file_content(*, python_executable: str, working_directory: str,
                       user: str = "neural-link",
                       config_path: str = "/etc/neural-link/config.toml") -> str:
    return (
        "[Unit]\n"
        "Description=Neural Link Runtime — ponte entre hardware e a Neural Cloud\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        f"User={user}\n"
        f"WorkingDirectory={working_directory}\n"
        f"Environment=NEURAL_LINK_CONFIG={config_path}\n"
        f"ExecStart={python_executable} -m neural_link.runtime.main\n"
        "Restart=always\n"
        "RestartSec=5\n"
        "StandardOutput=journal\n"
        "StandardError=journal\n"
        "TimeoutStopSec=15\n"
        "\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )


def install(*, python_executable: str, working_directory: str,
            systemd_dir: Path = CAMINHO_SYSTEMD_OMISSAO,
            enable: bool = True, **kwargs) -> Path:
    """Escreve o unit file em `systemd_dir`. Só chama `systemctl` (para
    recarregar/ativar) se `systemd_dir` for o caminho real do SO — nos
    testes, `systemd_dir` aponta para um diretório temporário, e
    `systemctl` nunca é invocado."""
    systemd_dir = Path(systemd_dir)
    systemd_dir.mkdir(parents=True, exist_ok=True)
    destino = systemd_dir / NOME_SERVICO
    destino.write_text(unit_file_content(
        python_executable=python_executable,
        working_directory=working_directory, **kwargs,
    ))
    if enable and systemd_dir == CAMINHO_SYSTEMD_OMISSAO:
        subprocess.run(["systemctl", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "enable", NOME_SERVICO], check=False)
    return destino


def uninstall(*, systemd_dir: Path = CAMINHO_SYSTEMD_OMISSAO) -> None:
    systemd_dir = Path(systemd_dir)
    destino = systemd_dir / NOME_SERVICO
    if systemd_dir == CAMINHO_SYSTEMD_OMISSAO:
        subprocess.run(["systemctl", "disable", NOME_SERVICO], check=False)
    if destino.is_file():
        destino.unlink()
