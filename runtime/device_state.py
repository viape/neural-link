"""`DeviceState` — a máquina de estados do dispositivo, como dados puros.
Nenhuma lógica aqui — só o vocabulário e a tabela do que é uma transição
válida. `lifecycle.py` é quem a interpreta.

    BOOTING        a arrancar — hardware ainda não inicializado
    INITIALIZING   HAL/drivers a inicializar
    CONNECTING     drivers prontos, a tentar ligar ao Gateway
    ONLINE         ligado, a funcionar normalmente
    OFFLINE        sem ligação, em repouso (não está a tentar agora)
    RECONNECTING   a tentar ativamente voltar a ligar
    UPDATING       um OTA está em curso (só a partir de ONLINE — precisa
                   de rede para transferir)
    SHUTTING_DOWN  a desligar — terminal, alcançável de qualquer estado
                   (um SIGTERM pode chegar em qualquer altura)
"""

from __future__ import annotations

BOOTING = "BOOTING"
INITIALIZING = "INITIALIZING"
CONNECTING = "CONNECTING"
ONLINE = "ONLINE"
OFFLINE = "OFFLINE"
RECONNECTING = "RECONNECTING"
UPDATING = "UPDATING"
SHUTTING_DOWN = "SHUTTING_DOWN"

TODOS_OS_ESTADOS = (
    BOOTING, INITIALIZING, CONNECTING, ONLINE, OFFLINE,
    RECONNECTING, UPDATING, SHUTTING_DOWN,
)

# Tabela de transições válidas: estado atual -> conjunto de destinos
# permitidos. SHUTTING_DOWN é alcançável de qualquer estado (um sinal
# pode chegar a qualquer momento) — acrescentado a todos abaixo.
_TRANSICOES_BASE: dict[str, frozenset[str]] = {
    BOOTING: frozenset({INITIALIZING}),
    INITIALIZING: frozenset({CONNECTING}),
    CONNECTING: frozenset({ONLINE, OFFLINE}),
    ONLINE: frozenset({OFFLINE, UPDATING}),
    OFFLINE: frozenset({RECONNECTING}),
    RECONNECTING: frozenset({ONLINE, OFFLINE}),
    UPDATING: frozenset({ONLINE, BOOTING}),  # BOOTING se o update pedir reiniciar
    SHUTTING_DOWN: frozenset(),  # terminal
}

TRANSICOES_VALIDAS: dict[str, frozenset[str]] = {
    estado: (destinos | {SHUTTING_DOWN}) if estado != SHUTTING_DOWN else destinos
    for estado, destinos in _TRANSICOES_BASE.items()
}


def is_valid_transition(de: str, para: str) -> bool:
    return para in TRANSICOES_VALIDAS.get(de, frozenset())
