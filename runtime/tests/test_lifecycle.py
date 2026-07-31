from __future__ import annotations

import pytest

from neural_link.runtime import device_state as estados
from neural_link.runtime.lifecycle import DeviceStateMachine, InvalidTransitionError


def test_estado_inicial():
    sm = DeviceStateMachine()
    assert sm.state == estados.BOOTING


def test_transicao_valida():
    sm = DeviceStateMachine()
    sm.transition_to(estados.INITIALIZING)
    assert sm.state == estados.INITIALIZING


def test_transicao_invalida_levanta():
    sm = DeviceStateMachine()
    with pytest.raises(InvalidTransitionError):
        sm.transition_to(estados.ONLINE)
    assert sm.state == estados.BOOTING  # nunca muda em transição inválida


def test_observadores_sao_chamados():
    sm = DeviceStateMachine()
    vistos = []
    sm.on_transition(lambda de, para: vistos.append((de, para)))
    sm.transition_to(estados.INITIALIZING)
    assert vistos == [(estados.BOOTING, estados.INITIALIZING)]


def test_shutdown_requested_comeca_falso():
    sm = DeviceStateMachine()
    assert sm.shutdown_requested is False


def test_sigterm_marca_a_flag_sem_terminar_o_processo():
    import os
    import signal

    sm = DeviceStateMachine()
    sm.install_signal_handlers()
    os.kill(os.getpid(), signal.SIGTERM)
    assert sm.shutdown_requested is True
