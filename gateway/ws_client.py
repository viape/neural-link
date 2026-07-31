"""`WebSocketClient` — o lado CLIENTE do protocolo já servido por
`neural_gateway.transports.WebSocketTransport`. RFC6455 mínimo, stdlib
puro (`socket`, `hashlib`, `base64`, `struct`) — sem dependências novas,
mesma disciplina de todo o projeto.

DELIBERADAMENTE STANDALONE: este ficheiro nunca importa `neural_gateway`,
`neural_runtime` nem `neural_core` — um Neural Link real não teria o
resto deste repositório instalado, só precisa de FALAR o protocolo. O
handshake e os frames são o espelho exato do lado servidor (cliente
MASCARA os frames que envia; servidor NÃO mascara os que devolve — ao
contrário do lado servidor, que exige máscara de entrada e nunca mascara
a saída).

ÂMBITO ESTREITO, igual ao lado servidor: só frames de texto, sem
fragmentação, sem ping/pong, sem extensões."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct

_GUID_RFC6455 = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_OPCODE_TEXTO = 0x1
_OPCODE_FECHO = 0x8


class WebSocketConnectionError(ConnectionError):
    pass


def _chave_pedido() -> str:
    return base64.b64encode(os.urandom(16)).decode("ascii")


def _aceitacao_esperada(chave: str) -> str:
    digest = hashlib.sha1((chave + _GUID_RFC6455).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def _receber_exatamente(sock: socket.socket, n: int) -> bytes | None:
    partes = bytearray()
    while len(partes) < n:
        pedaco = sock.recv(n - len(partes))
        if not pedaco:
            return None
        partes += pedaco
    return bytes(partes)


def _codificar_frame_texto_mascarado(texto: str) -> bytes:
    dados = texto.encode("utf-8")
    mascara = os.urandom(4)
    mascarado = bytes(b ^ mascara[i % 4] for i, b in enumerate(dados))
    comprimento = len(dados)
    if comprimento < 126:
        cabecalho = struct.pack("BB", 0x80 | _OPCODE_TEXTO, 0x80 | comprimento)
    elif comprimento < 65536:
        cabecalho = struct.pack("!BBH", 0x80 | _OPCODE_TEXTO, 0x80 | 126, comprimento)
    else:
        cabecalho = struct.pack("!BBQ", 0x80 | _OPCODE_TEXTO, 0x80 | 127, comprimento)
    return cabecalho + mascara + mascarado


def _ler_frame_nao_mascarado(sock: socket.socket) -> tuple[int, bytes] | None:
    """Frame de entrada (servidor -> cliente): nunca mascarado, por RFC."""
    cabecalho = _receber_exatamente(sock, 2)
    if cabecalho is None:
        return None
    byte0, byte1 = cabecalho
    opcode = byte0 & 0x0F
    comprimento = byte1 & 0x7F
    if comprimento == 126:
        dados = _receber_exatamente(sock, 2)
        if dados is None:
            return None
        comprimento = struct.unpack(">H", dados)[0]
    elif comprimento == 127:
        dados = _receber_exatamente(sock, 8)
        if dados is None:
            return None
        comprimento = struct.unpack(">Q", dados)[0]
    payload = _receber_exatamente(sock, comprimento) if comprimento else b""
    if payload is None:
        return None
    return opcode, payload


class WebSocketClient:
    def __init__(self, host: str, port: int, *, path: str = "/",
                 connect_timeout_s: float = 5.0) -> None:
        self._host = host
        self._port = port
        self._path = path
        self._connect_timeout_s = connect_timeout_s
        self._sock: socket.socket | None = None

    @property
    def connected(self) -> bool:
        return self._sock is not None

    def connect(self) -> None:
        """Handshake RFC6455. Levanta `WebSocketConnectionError` se o
        servidor recusar ou não responder — nunca deixa a ligação a meio."""
        if self._sock is not None:
            return
        chave = _chave_pedido()
        pedido = (
            f"GET {self._path} HTTP/1.1\r\n"
            f"Host: {self._host}:{self._port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {chave}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        sock = None
        try:
            sock = socket.create_connection(
                (self._host, self._port), timeout=self._connect_timeout_s,
            )
            sock.sendall(pedido.encode("ascii"))
            resposta = sock.recv(4096).decode("ascii", errors="replace")
            linhas = resposta.splitlines()
            if not linhas or "101" not in linhas[0]:
                raise WebSocketConnectionError(f"handshake recusado: {linhas[:1]}")
            if _aceitacao_esperada(chave) not in resposta:
                raise WebSocketConnectionError("Sec-WebSocket-Accept inválido")
        except OSError as erro:
            if sock is not None:
                sock.close()
            raise WebSocketConnectionError(str(erro)) from erro
        except WebSocketConnectionError:
            if sock is not None:
                sock.close()
            raise
        self._sock = sock

    def disconnect(self) -> None:
        if self._sock is None:
            return
        try:
            self._sock.close()
        except OSError:
            pass
        self._sock = None

    def send_json(self, payload: dict) -> None:
        if self._sock is None:
            raise WebSocketConnectionError("não ligado — chame connect() primeiro")
        frame = _codificar_frame_texto_mascarado(json.dumps(payload, ensure_ascii=False))
        try:
            self._sock.sendall(frame)
        except OSError as erro:
            self.disconnect()
            raise WebSocketConnectionError(str(erro)) from erro

    def receive_json(self, *, timeout_s: float = 5.0) -> dict | None:
        """Bloqueia até `timeout_s`. `None` se não chegar nada, ou se o
        servidor fechar a ligação (que também é tratada aqui, nunca
        levanta por um fecho normal)."""
        if self._sock is None:
            raise WebSocketConnectionError("não ligado — chame connect() primeiro")
        self._sock.settimeout(timeout_s)
        try:
            resultado = _ler_frame_nao_mascarado(self._sock)
        except socket.timeout:
            return None
        except OSError as erro:
            self.disconnect()
            raise WebSocketConnectionError(str(erro)) from erro
        if resultado is None:
            self.disconnect()
            return None
        opcode, payload = resultado
        if opcode == _OPCODE_FECHO:
            self.disconnect()
            return None
        if opcode != _OPCODE_TEXTO:
            return None
        try:
            return json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
