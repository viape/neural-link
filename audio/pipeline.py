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
eco, fica por acrescentar quando existir — não escondido, documentado.

--- MODO DE CONVERSA ------------------------------------------------

Pedido explícito: repetir "hey jarvis" antes de CADA pergunta não é
natural. Depois da wake word disparar a primeira vez, o dispositivo
entra em "conversa" — as frases seguintes são segmentadas só pelo VAD,
sem precisar da wake word outra vez — até:

  1. alguém (do lado de fora — a Cloud, depois de transcrever) chamar
     `dormir()`, porque o texto reconhecido era uma frase de paragem
     ("já está mudar de sítio" não faz sentido aqui: a decisão de QUE
     texto conta como "parar" vive na Cloud, que é quem tem o STT —
     `LinkAudioPipeline` nunca vê texto, só bytes); ou
  2. tempo a mais sem ninguém falar (`conversation_timeout_chunks`) —
     para não ficar a ouvir para sempre depois de a pessoa se ir
     embora, o mesmo cuidado de bateria que já motivava a wake word."""

from __future__ import annotations

from collections import deque
from typing import Callable

from neural_audio import (AudioChunk, AudioSource, VoiceActivityDetector,
                           WakeWordProvider)


class NullWakeWordProvider(WakeWordProvider):
    """A omissão de `boot()` quando nenhum motor de wake word real está
    configurado — nunca deteta nada. Um Raspberry sem palavra-chave
    configurada arranca e grava o pipeline na mesma (limpo, testável),
    mas nunca ouve; documentado, não escondido. `OpenWakeWord`/Porcupine
    entram aqui no dia em que existir uma implementação real."""

    def detect(self, chunk: AudioChunk) -> bool:
        return False


class LinkAudioPipeline:
    def __init__(
        self,
        mic: AudioSource,
        wake_word: WakeWordProvider,
        vad: VoiceActivityDetector,
        *,
        on_utterance: Callable[[bytes], None],
        preroll_chunks: int = 15,
        # 15 (1.2s) cortava a frase mal a pessoa fizesse uma pausa
        # natural logo a seguir à wake word ("hey jarvis... [respira]...
        # que horas são?") — a gravação terminava vazia, antes de a
        # pergunta a sério começar. 25 (2.0s) dá essa margem, mesma
        # ordem de grandeza do que assistentes de voz comuns usam.
        silence_chunks: int = 25,
        max_chunks: int = 300,
        # 30 minutos (a 80ms/bocado) sem ninguém falar depois de uma
        # frase, em modo de conversa, e volta a exigir "hey jarvis" —
        # nunca fica a ouvir para sempre por esquecimento.
        conversation_timeout_chunks: int = 22500,
    ) -> None:
        self._mic = mic
        self._wake = wake_word
        self._vad = vad
        self._on_utterance = on_utterance
        self._silence_chunks = silence_chunks
        self._max_chunks = max_chunks
        self._conversation_timeout_chunks = conversation_timeout_chunks

        self._preroll: deque[AudioChunk] = deque(maxlen=preroll_chunks)
        self._a_ouvir = False
        self._em_conversa = False
        self._silencio_em_conversa = 0
        self._buffer: list[AudioChunk] = []
        self._silencio_seguido = 0

    @property
    def listening(self) -> bool:
        return self._a_ouvir

    @property
    def in_conversation(self) -> bool:
        return self._em_conversa

    def dormir(self) -> None:
        """Sai do modo de conversa — a próxima frase volta a precisar da
        wake word. Chamado por `main.py` quando a Cloud manda um
        comando `Sleep` (a pessoa disse uma frase de paragem, ou o
        próprio dispositivo atingiu o `conversation_timeout_chunks`)."""
        self._em_conversa = False
        self._a_ouvir = False
        self._buffer = []
        self._silencio_seguido = 0
        self._silencio_em_conversa = 0
        self._preroll.clear()

    def poll(self) -> None:
        """Uma sondagem — nunca bloqueia. Esvazia TUDO o que o microfone
        já tiver disponível, não só um bocado.

        BUG REAL, apanhado com hardware a sério: quem chama isto (o loop
        principal do Runtime) só o faz a cada ~500ms, mas o microfone
        produz um bocado novo a cada 80ms (`chunk_ms`). Ler só um bocado
        por chamada consumia áudio a 1/6 da velocidade a que era
        produzido — a fila do `Microphone` enchia-se e começava a
        descartar o mais antigo (ver `Microphone.read()`), e a wake
        word nunca via os bocados a tempo de reconhecer a frase
        inteira. Esvaziar tudo aqui corrige isso sem mexer no ritmo do
        loop principal."""
        while True:
            chunk = self._mic.read()
            if chunk is None:
                return
            self._processar_bocado(chunk)

    def _processar_bocado(self, chunk: AudioChunk) -> None:
        if not self._a_ouvir:
            if self._em_conversa:
                self._processar_bocado_em_conversa(chunk)
                return

            self._preroll.append(chunk)
            if self._wake.detect(chunk):
                self._a_ouvir = True
                self._em_conversa = True
                self._silencio_em_conversa = 0
                # NUNCA `list(self._preroll)` — os bocados no preroll são
                # exatamente os que contêm a própria wake word ("hey
                # jarvis" a ser dita). Incluí-los aqui mandava a wake
                # word para o STT como se fosse parte do pedido — bug
                # real, apanhado a testar com hardware a sério (o
                # Whisper transcrevia "hey jarvis" como texto solto, e a
                # LLM tentava interpretá-lo como parte da pergunta).
                self._buffer = []
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

    def _processar_bocado_em_conversa(self, chunk: AudioChunk) -> None:
        """Já em conversa, entre frases — sem wake word, o VAD sozinho
        decide quando a próxima começa. Se ninguém falar durante
        `conversation_timeout_chunks`, volta a dormir sozinho.

        O VAD exige energia sustentada para confirmar "é fala" (`hold`
        bocados seguidos, ver `AdaptiveEnergyVAD`) — nunca o primeiro
        bocado da frase. Sem preroll aqui, essa primeira sílaba
        perdia-se sempre, a cada frase depois da primeira. Reaproveita
        o mesmo `_preroll` da wake word (aqui não há palavra nenhuma a
        excluir, é só o áudio logo antes de o VAD confirmar)."""
        if self._vad.is_speech(chunk):
            self._a_ouvir = True
            self._silencio_em_conversa = 0
            self._buffer = list(self._preroll) + [chunk]
            self._preroll.clear()
            self._silencio_seguido = 0
            return

        self._preroll.append(chunk)
        self._silencio_em_conversa += 1
        if self._silencio_em_conversa >= self._conversation_timeout_chunks:
            self.dormir()

    def _finalizar_frase(self) -> None:
        audio = b"".join(c.samples for c in self._buffer)
        self._a_ouvir = False
        self._buffer = []
        self._silencio_seguido = 0
        self._silencio_em_conversa = 0
        self._preroll.clear()
        self._on_utterance(audio)
