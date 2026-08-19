"""Modelos del Mapa de ocupacion (DISENO.md -> Componentes -> Mapa de ocupacion).

Solo lo que la Pieza 1 necesita para LEER el mapa. Los modelos de apartado
(ResultadoApartado y similares) llegan en la Pieza 2, que es quien primero los usa.
"""
from dataclasses import dataclass
from enum import Enum


class EstadoButaca(str, Enum):
    DISPONIBLE = "disponible"
    APARTADA = "apartada"
    VENDIDA = "vendida"
    NO_VENDIBLE = "no_vendible"


@dataclass(frozen=True)
class ButacaDelMapa:
    butaca_id: int
    fila: str
    numero: int
    estado: EstadoButaca
    sesion_id: str | None  # la sesion del apartado, haya vencido o no
