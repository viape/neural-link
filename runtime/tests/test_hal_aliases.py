"""Prova que 3 dos 8 contratos HAL são os MESMOS objetos já existentes,
nunca uma segunda definição."""

from __future__ import annotations

from neural_audio import AudioSource
from neural_link.ble.base import BleAdapter
from neural_link.power.power import PowerProvider
from neural_link.runtime.hal.interfaces import (AudioDriver, BluetoothDriver,
                                                  ButtonDriver, LEDDriver,
                                                  NetworkDriver, PowerDriver,
                                                  StorageDriver, Updater)


def test_audio_driver_e_o_mesmo_audio_source():
    assert AudioDriver is AudioSource


def test_bluetooth_driver_e_o_mesmo_ble_adapter():
    assert BluetoothDriver is BleAdapter


def test_power_driver_e_o_mesmo_power_provider():
    assert PowerDriver is PowerProvider


def test_os_cinco_novos_sao_classes_proprias():
    for interface in (NetworkDriver, StorageDriver, LEDDriver, ButtonDriver, Updater):
        assert interface not in (AudioSource, BleAdapter, PowerProvider)
