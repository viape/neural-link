from __future__ import annotations

from neural_link.buffering.buffer import OfflineBuffer


def test_enqueue_e_len():
    buffer = OfflineBuffer()
    buffer.enqueue({"a": 1})
    assert len(buffer) == 1


def test_flush_envia_por_ordem_e_esvazia():
    buffer = OfflineBuffer()
    buffer.enqueue({"n": 1})
    buffer.enqueue({"n": 2})
    enviadas = []
    resultado = buffer.flush(lambda p: enviadas.append(p) or True)
    assert resultado == 2
    assert enviadas == [{"n": 1}, {"n": 2}]
    assert len(buffer) == 0


def test_flush_para_no_primeiro_falhanco_preserva_ordem():
    buffer = OfflineBuffer()
    buffer.enqueue({"n": 1})
    buffer.enqueue({"n": 2})
    buffer.enqueue({"n": 3})

    tentativas = []

    def _enviar(payload):
        tentativas.append(payload)
        return payload["n"] != 2  # falha na segunda

    resultado = buffer.flush(_enviar)
    assert resultado == 1
    assert tentativas == [{"n": 1}, {"n": 2}]
    assert len(buffer) == 2  # {"n":2} e {"n":3} continuam na fila


def test_flush_com_excecao_conta_como_falhanco():
    buffer = OfflineBuffer()
    buffer.enqueue({"n": 1})

    def _rebenta(_payload):
        raise RuntimeError("boom")

    resultado = buffer.flush(_rebenta)
    assert resultado == 0
    assert len(buffer) == 1


def test_max_size_descarta_o_mais_antigo():
    buffer = OfflineBuffer(max_size=2)
    buffer.enqueue({"n": 1})
    buffer.enqueue({"n": 2})
    buffer.enqueue({"n": 3})
    assert len(buffer) == 2
