"""Prova o critério de aceitação: trocar de placa é trocar um nome."""

from __future__ import annotations

import pytest

from neural_link.devices.board import SimulatedBoard, available, create, has


def test_placas_disponiveis():
    esperadas = {"simulated", "raspberry_pi", "orange_pi",
                 "compute_module", "sbc_oem", "custom_hardware"}
    assert esperadas <= set(available())


def test_has():
    assert has("simulated") is True
    assert has("nao_existe") is False


def test_create_desconhecida_levanta_erro_claro():
    with pytest.raises(KeyError):
        create("nao_existe")


def test_simulated_board_funciona_de_verdade():
    board = create("simulated")
    assert isinstance(board, SimulatedBoard)
    assert board.microphone() is not None
    assert board.power().battery_percent() == 1.0
    board.start()
    board.stop()


@pytest.mark.parametrize("nome", [
    "orange_pi", "compute_module", "sbc_oem", "custom_hardware",
])
def test_placas_fisicas_constroem_mas_nao_arrancam(nome):
    board = create(nome, qualquer="config")  # nunca rebenta a construir
    assert board.microphone() is None  # omissão de LinkBoard
    with pytest.raises(NotImplementedError):
        board.start()


def test_raspberry_pi_tem_microfone_real_desde_o_runtime():
    """A Raspberry Pi deixou de ser stub (`neural_link/runtime/`, hardware
    comprado): `microphone()` devolve um `RaspberryPiAudioDriver` real."""
    board = create("raspberry_pi")
    assert board.microphone() is not None


def test_raspberry_pi_start_stop_sem_pedir_microfone_nunca_tocam_em_hardware():
    """Sem ninguém ter chamado `microphone()` antes, `start()`/`stop()`
    são no-ops seguros — nunca abrem o microfone real desta máquina."""
    board = create("raspberry_pi")
    board.start()
    board.stop()
