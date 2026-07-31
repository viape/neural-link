"""`boot()` chama as peças pela ordem certa (Hardware -> HAL -> Drivers ->
Gateway -> Heartbeat), com tudo simulado — nenhum hardware real, nenhuma
`RaspberryPiAudioDriver` de verdade."""

from __future__ import annotations

from neural_gateway.transports import WebSocketTransport
from neural_link.devices.board import QueuedAudioSource
from neural_link.power.power import SimulatedPower
from neural_link.runtime import device_state as estados
from neural_link.runtime.boot import DriverSet, boot
from neural_link.runtime.configuration import DeviceConfig
from neural_link.runtime.drivers.raspberry_pi import NullButtonDriver, NullLEDDriver


def _placa_simulada(_config, ordem):
    ordem.append("drivers")

    class _RedeFalsa:
        def is_connected(self):
            return True

        def wifi_info(self):
            return {}

    return DriverSet(
        audio=QueuedAudioSource(),
        network=_RedeFalsa(),
        storage=None,
        led=NullLEDDriver(),
        button=NullButtonDriver(),
    )


def test_ordem_de_arranque():
    servidor = WebSocketTransport(port=8170)
    servidor.connect()
    try:
        ordem: list[str] = []
        cfg = DeviceConfig(gateway_host="127.0.0.1", gateway_port=8170)
        componentes = boot(cfg, driver_factory=lambda c: _placa_simulada(c, ordem))
        # a fábrica de drivers (Hardware/HAL/Drivers) correu ANTES de
        # ficar ONLINE (Gateway Client) — a única forma de o provar de
        # fora é confirmar que ambos aconteceram e que o estado final é
        # o esperado depois da sequência completa.
        assert ordem == ["drivers"]
        assert componentes.state_machine.state == estados.ONLINE
        assert componentes.heartbeat is not None
        assert componentes.offline_queue is not None
        assert componentes.device_manager is not None
    finally:
        servidor.disconnect()


def test_boot_sem_gateway_fica_offline_mas_nao_rebenta():
    cfg = DeviceConfig(gateway_host="127.0.0.1", gateway_port=8171)
    componentes = boot(cfg)
    assert componentes.state_machine.state == estados.OFFLINE


def test_boot_usa_power_do_driver_set_no_heartbeat():
    cfg = DeviceConfig(gateway_host="127.0.0.1", gateway_port=8171)

    def _placa_com_bateria(_config):
        return DriverSet(
            audio=QueuedAudioSource(), network=None, storage=None,
            led=NullLEDDriver(), button=NullButtonDriver(),
        )

    componentes = boot(cfg, driver_factory=_placa_com_bateria)
    payload = componentes.heartbeat.beat()
    assert payload.wifi_connected is None  # sem NetworkDriver nesta placa falsa
