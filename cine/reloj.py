"""Reloj inyectable. Ningun otro modulo llama a datetime.now() directamente: el momento
actual entra siempre como parametro `ahora`, para que CA-6, CA-10 y CA-15 se puedan
comprobar sin esperar minutos reales (Restriccion global 1 de PLAN.md)."""
from datetime import datetime, timedelta, timezone
from typing import Protocol

FORMATO = "%Y-%m-%dT%H:%M:%S.%f"

# El cine esta en Costa Rica. Piezas futuras que decidan "es miercoles" deben calcularlo
# en esta zona, no en UTC.
ZONA_CINE = timezone(timedelta(hours=-6))


class Reloj(Protocol):
    def ahora(self) -> datetime: ...


class RelojReal:
    def ahora(self) -> datetime:
        return datetime.now(timezone.utc)


class RelojFijo:
    """Reloj de pruebas: no avanza solo, para que las pruebas controlen el tiempo."""

    def __init__(self, momento: datetime) -> None:
        self._momento = momento

    def ahora(self) -> datetime:
        return self._momento

    def avanzar(self, **delta: int) -> None:
        self._momento += timedelta(**delta)

    def poner(self, momento: datetime) -> None:
        self._momento = momento


def iso(momento: datetime) -> str:
    """Ancho fijo de 24 caracteres: de eso depende que SQLite compare bien las fechas
    con una simple comparacion de texto (Restriccion global 2)."""
    return momento.astimezone(timezone.utc).strftime(FORMATO)[:-3] + "Z"


def desde_iso(texto: str) -> datetime:
    return datetime.strptime(texto[:-1], FORMATO).replace(tzinfo=timezone.utc)
