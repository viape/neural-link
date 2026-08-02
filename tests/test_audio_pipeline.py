"""`LinkAudioPipeline` com VAD/Wake Word REAIS (`neural_audio`, a fonte
partilhada com `neural_core`), microfone falso. Prova a segmentação sem
reimplementar `VoicePipeline`."""

from __future__ import annotations

from neural_audio import AdaptiveEnergyVAD, AudioChunk, SimulatedWakeWord
from neural_link.audio.pipeline import LinkAudioPipeline
from neural_link.devices.board import QueuedAudioSource


def _chunk(texto: str = "") -> AudioChunk:
    return AudioChunk(samples=texto.encode().ljust(320, b"\x00"))


def _silencio() -> AudioChunk:
    return AudioChunk(samples=b"\x00" * 320)


def test_nao_ouve_sem_wake_word():
    mic = QueuedAudioSource()
    capturas = []
    pipeline = LinkAudioPipeline(
        mic, SimulatedWakeWord(phrase="robo"), AdaptiveEnergyVAD(),
        on_utterance=capturas.append,
    )
    for _ in range(5):
        mic.push(_chunk("silencio total"))
        pipeline.poll()
    assert pipeline.listening is False
    assert capturas == []


def test_wake_word_ativa_a_escuta():
    mic = QueuedAudioSource()
    pipeline = LinkAudioPipeline(
        mic, SimulatedWakeWord(phrase="robo"), AdaptiveEnergyVAD(),
        on_utterance=lambda _a: None,
    )
    mic.push(_chunk("robo"))
    pipeline.poll()
    assert pipeline.listening is True


def test_silencio_prolongado_finaliza_a_frase():
    mic = QueuedAudioSource()
    capturas: list[bytes] = []
    pipeline = LinkAudioPipeline(
        mic, SimulatedWakeWord(phrase="robo"), AdaptiveEnergyVAD(),
        on_utterance=capturas.append, silence_chunks=3,
    )
    mic.push(_chunk("robo"))
    pipeline.poll()
    assert pipeline.listening is True

    for _ in range(3):
        mic.push(_chunk("ola tudo bem"))
        pipeline.poll()

    for _ in range(3):
        mic.push(_silencio())
        pipeline.poll()

    assert pipeline.listening is False
    assert len(capturas) == 1
    assert len(capturas[0]) > 0


def test_max_chunks_e_um_limite_de_seguranca():
    mic = QueuedAudioSource()
    capturas: list[bytes] = []
    pipeline = LinkAudioPipeline(
        mic, SimulatedWakeWord(phrase="robo"), AdaptiveEnergyVAD(),
        on_utterance=capturas.append, max_chunks=5, silence_chunks=999,
    )
    mic.push(_chunk("robo"))
    pipeline.poll()
    for _ in range(10):
        mic.push(_chunk("fala sem parar"))
        pipeline.poll()
    assert len(capturas) == 1  # finalizou pelo limite, não pelo silêncio


def test_poll_sem_audio_nao_rebenta():
    mic = QueuedAudioSource()
    pipeline = LinkAudioPipeline(
        mic, SimulatedWakeWord(phrase="robo"), AdaptiveEnergyVAD(),
        on_utterance=lambda _a: None,
    )
    pipeline.poll()  # mic.read() -> None
    assert pipeline.listening is False


def test_poll_esvazia_varios_bocados_de_uma_so_vez():
    """Guarda de regressão para um bug real: o loop principal do Runtime
    só chama poll() a cada ~500ms, mas o microfone produz um bocado
    novo a cada 80ms — um poll() que só lesse UM bocado ficava sempre
    ~6x atrasado em relação ao que realmente se estava a dizer, e a
    wake word nunca via os bocados a tempo. Um único poll() tem de
    processar TUDO o que já estiver na fila, não só o mais antigo."""
    mic = QueuedAudioSource()
    pipeline = LinkAudioPipeline(
        mic, SimulatedWakeWord(phrase="robo"), AdaptiveEnergyVAD(),
        on_utterance=lambda _a: None, silence_chunks=3,
    )
    # 6 bocados empilhados ANTES de qualquer poll() — simula o microfone
    # a produzir mais depressa do que o loop principal consome.
    mic.push(_chunk("robo"))
    for _ in range(5):
        mic.push(_chunk("ola tudo bem"))

    pipeline.poll()  # UMA só chamada

    # se só tivesse lido um bocado, a wake word nunca teria sido detetada
    # a tempo de os restantes 5 bocados contarem para o buffer da frase.
    assert pipeline.listening is True


def test_poll_processa_ate_finalizar_a_frase_dentro_de_uma_so_chamada():
    mic = QueuedAudioSource()
    capturas: list[bytes] = []
    pipeline = LinkAudioPipeline(
        mic, SimulatedWakeWord(phrase="robo"), AdaptiveEnergyVAD(),
        on_utterance=capturas.append, silence_chunks=2,
    )
    mic.push(_chunk("robo"))
    mic.push(_chunk("ola"))
    mic.push(_silencio())
    mic.push(_silencio())

    pipeline.poll()  # tudo isto tem de ser processado numa só chamada

    assert pipeline.listening is False
    assert len(capturas) == 1
