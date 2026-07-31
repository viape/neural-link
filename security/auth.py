"""`LinkAuthProvider` — autenticação LOCAL (Auriculares <-> Neural Link).

Não é `neural_gateway.authentication.AuthenticationProvider` — essa
autentica quem fala com a nuvem (Dashboard/Link -> Cloud); esta autentica
quem fala com o próprio Link (um dispositivo já emparelhado). Fronteiras
de confiança diferentes, mesma FORMA — sem importar uma da outra.

Hoje: `DummyLinkAuth`, autoriza sempre. Amanhã: chaves por dispositivo
trocadas no emparelhamento (`neural_link.pairing`, ainda por implementar)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LinkAuthResult:
    device_id: str
    authorized: bool


class LinkAuthProvider(ABC):
    @abstractmethod
    def authenticate(self, device_id: str, credentials: dict) -> LinkAuthResult: ...


class DummyLinkAuth(LinkAuthProvider):
    def authenticate(self, device_id: str, credentials: dict) -> LinkAuthResult:
        return LinkAuthResult(device_id=device_id, authorized=True)
