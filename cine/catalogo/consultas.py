"""Catalogo: que se exhibe, donde y cuando. No sabe que existen las compras
(DISENO.md -> Componentes -> Catalogo)."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from cine.reloj import desde_iso, iso


@dataclass(frozen=True)
class FuncionEnCartelera:
    funcion_id: int
    titulo: str
    clasificacion_edad: int
    sala_nombre: str
    inicio: datetime


@dataclass(frozen=True)
class FuncionDetalle:
    funcion_id: int
    pelicula_id: int
    titulo: str
    duracion_minutos: int
    clasificacion_edad: int
    distribuidora: str
    sala_id: int
    sala_nombre: str
    inicio: datetime
    fin: datetime
    estado: str


SQL_BASE = """
SELECT f.id AS funcion_id, f.pelicula_id, f.sala_id, f.inicio, f.fin, f.estado,
       p.titulo, p.duracion_minutos, p.clasificacion_edad, p.distribuidora,
       s.nombre AS sala_nombre
  FROM funcion f
  JOIN pelicula p ON p.id = f.pelicula_id
  JOIN sala     s ON s.id = f.sala_id
"""


def cartelera_vigente(cx: sqlite3.Connection, ahora: datetime) -> list[FuncionEnCartelera]:
    """Funciones programadas que todavia no han empezado (RF-3, RN-3, RN-4)."""
    filas = cx.execute(
        SQL_BASE + " WHERE f.estado = 'programada' AND f.inicio > :ahora ORDER BY f.inicio",
        {"ahora": iso(ahora)},
    )
    return [
        FuncionEnCartelera(
            funcion_id=f["funcion_id"],
            titulo=f["titulo"],
            clasificacion_edad=f["clasificacion_edad"],
            sala_nombre=f["sala_nombre"],
            inicio=desde_iso(f["inicio"]),
        )
        for f in filas
    ]


def funcion_por_id(cx: sqlite3.Connection, funcion_id: int) -> FuncionDetalle | None:
    f = cx.execute(SQL_BASE + " WHERE f.id = :id", {"id": funcion_id}).fetchone()
    if f is None:
        return None
    return FuncionDetalle(
        funcion_id=f["funcion_id"],
        pelicula_id=f["pelicula_id"],
        titulo=f["titulo"],
        duracion_minutos=f["duracion_minutos"],
        clasificacion_edad=f["clasificacion_edad"],
        distribuidora=f["distribuidora"],
        sala_id=f["sala_id"],
        sala_nombre=f["sala_nombre"],
        inicio=desde_iso(f["inicio"]),
        fin=desde_iso(f["fin"]),
        estado=f["estado"],
    )


def esta_a_la_venta(funcion: FuncionDetalle, ahora: datetime) -> bool:
    """RN-3: deja de estar a la venta exactamente a su hora de inicio, en los dos canales."""
    return funcion.estado == "programada" and ahora < funcion.inicio
