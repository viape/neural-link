from __future__ import annotations

import pytest

from neural_link.runtime import device_state as estados


def test_sequencia_de_arranque_e_valida():
    assert estados.is_valid_transition(estados.BOOTING, estados.INITIALIZING)
    assert estados.is_valid_transition(estados.INITIALIZING, estados.CONNECTING)
    assert estados.is_valid_transition(estados.CONNECTING, estados.ONLINE)
    assert estados.is_valid_transition(estados.CONNECTING, estados.OFFLINE)


def test_reconexao_e_valida():
    assert estados.is_valid_transition(estados.ONLINE, estados.OFFLINE)
    assert estados.is_valid_transition(estados.OFFLINE, estados.RECONNECTING)
    assert estados.is_valid_transition(estados.RECONNECTING, estados.ONLINE)
    assert estados.is_valid_transition(estados.RECONNECTING, estados.OFFLINE)


def test_update_so_a_partir_de_online():
    assert estados.is_valid_transition(estados.ONLINE, estados.UPDATING)
    assert not estados.is_valid_transition(estados.OFFLINE, estados.UPDATING)
    assert estados.is_valid_transition(estados.UPDATING, estados.ONLINE)
    assert estados.is_valid_transition(estados.UPDATING, estados.BOOTING)


@pytest.mark.parametrize("estado", estados.TODOS_OS_ESTADOS)
def test_shutting_down_alcancavel_de_qualquer_estado(estado):
    if estado == estados.SHUTTING_DOWN:
        return
    assert estados.is_valid_transition(estado, estados.SHUTTING_DOWN)


def test_shutting_down_e_terminal():
    assert estados.TRANSICOES_VALIDAS[estados.SHUTTING_DOWN] == frozenset()


def test_saltos_invalidos():
    assert not estados.is_valid_transition(estados.BOOTING, estados.ONLINE)
    assert not estados.is_valid_transition(estados.OFFLINE, estados.ONLINE)
