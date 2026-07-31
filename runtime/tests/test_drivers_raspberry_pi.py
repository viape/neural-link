"""`RaspberryPiAudioDriver` NUNCA constrói `Microphone` real aqui — só se
prova que a construção fica adiada para `start()`. Os outros drivers são
reais e testados a sério (rede, ficheiros)."""

from __future__ import annotations

import socket
import threading

from neural_link.runtime.drivers.raspberry_pi import (
    NullButtonDriver, NullLEDDriver, RaspberryPiAudioDriver,
    RaspberryPiNetworkDriver, RaspberryPiStorageDriver)


def test_audio_driver_construir_nao_toca_em_hardware():
    driver = RaspberryPiAudioDriver()
    assert driver.read() is None  # nunca arrancado, nunca rebenta


def test_audio_driver_stop_sem_start_nao_rebenta():
    RaspberryPiAudioDriver().stop()


def test_network_driver_deteta_ligacao_real():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind(("127.0.0.1", 0))
    servidor.listen(1)
    porta = servidor.getsockname()[1]
    parar = threading.Event()

    def _aceitar():
        servidor.settimeout(2.0)
        try:
            conexao, _ = servidor.accept()
            conexao.close()
        except OSError:
            pass

    fio = threading.Thread(target=_aceitar, daemon=True)
    fio.start()
    try:
        driver = RaspberryPiNetworkDriver(probe_host="127.0.0.1", probe_port=porta,
                                            timeout_s=1.0)
        assert driver.is_connected() is True
    finally:
        parar.set()
        servidor.close()
        fio.join(timeout=2.0)


def test_network_driver_deteta_falta_de_ligacao():
    driver = RaspberryPiNetworkDriver(probe_host="127.0.0.1", probe_port=1,
                                        timeout_s=1.0)
    assert driver.is_connected() is False


def test_network_driver_wifi_info_nunca_rebenta_sem_nmcli():
    driver = RaspberryPiNetworkDriver()
    assert isinstance(driver.wifi_info(), dict)


def test_storage_driver_real(tmp_path):
    driver = RaspberryPiStorageDriver(tmp_path / "estado")
    assert driver.read("chave") is None
    driver.write("chave", b"valor")
    assert driver.read("chave") == b"valor"
    driver.delete("chave")
    assert driver.read("chave") is None


def test_storage_driver_delete_sem_existir_nao_rebenta(tmp_path):
    RaspberryPiStorageDriver(tmp_path).delete("nao-existe")


def test_null_drivers_nunca_rebentam():
    NullLEDDriver().show("online")
    assert NullButtonDriver().read() == []
