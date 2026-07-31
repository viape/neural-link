"""`LinkAudioPipeline` — Microfone -> Wake Word -> VAD -> encaminhar.

Não é o `neural_core.integrations.speech.pipeline.VoicePipeline` — esse
publica no `EventBus` do Core e transcreve localmente; o Link só segmenta
a frase e entrega os bytes brutos a quem os for encaminhar para a nuvem
(a transcrição é "Cloud", como o diagrama do pedido já diz — o mesmo
desenho que `dashboard_bridge`'s `POST /audio` já usa a partir de um
browser). Reaproveita os PORTOS e implementações de VAD/Wake Word de
`neural_audio` — a fonte partilhada com `neural_core`, nunca um import
direto de `neural_core` (ver `neural_link/tests/test_di_boundaries.py`).

Simplificação conhecida e assumida nesta v1: sem estado MUTED/half-duplex
(o `VoicePipeline` tem-no para não se ouvir a si próprio enquanto fala
pelas colunas do robô). Sem hardware real de auriculares para validar o
eco, fica por acrescentar quando existir — não escondido, documentado."""

from __future__ import annotations

from collections import deque
from typing import Callable

from neural_audio import (AudioChunk, AudioSource, VoiceActivityDetector,
                           WakeWordProvider)


class LinkAudioPipeline:
    def __init__(
        self,
        mic: AudioSource,
        wake_word: WakeWordProvider,
        vad: VoiceActivityDetector,
        *,
        on_utterance: Callable[[bytes], None],
        preroll_chunks: int = 15,
        silence_chunks: int = 15,
        max_chunks: int = 300,
    ) -> None:
        self._mic = mic
        self._wake = wake_word
        self._vad = vad
        self._on_utterance = on_utterance
        self._silence_chunks = silence_chunks
        self._max_chunks = max_chunks

        self._preroll: deque[AudioChunk] = deque(maxlen=preroll_chunks)
        self._a_ouvir = False
        self._buffer: list[AudioChunk] = []
        self._silencio_seguido = 0

    @property
    def listening(self) -> bool:
        return self._a_ouvir

    def poll(self) -> None:
        """Uma sondagem. Chamar em loop (mesmo idioma de `Transport.
        receive()`/`Gateway.receive()` — nunca bloqueia)."""
        chunk = self._mic.read()
        if chunk is None:
            return

        if not self._a_ouvir:
            self._preroll.append(chunk)
            if self._wake.detect(chunk):
                self._a_ouvir = True
                self._buffer = list(self._preroll)
                self._silencio_seguido = 0
            return

        self._buffer.append(chunk)
        if self._vad.is_speech(chunk):
            self._silencio_seguido = 0
        else:
            self._silencio_seguido += 1

        if (self._silencio_seguido >= self._silence_chunks
                or len(self._buffer) >= self._max_chunks):
            self._finalizar_frase()

    def _finalizar_frase(self) -> None:
        audio = b"".join(c.samples for c in self._buffer)
        self._a_ouvir = False
        self._buffer = []
        self._silencio_seguido = 0
        self._preroll.clear()
        self._on_utterance(audio)
