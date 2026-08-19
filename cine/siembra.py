"""Planos de las dos salas. El cine los aporta una sola vez (ESPECIFICACION.md ->
Dependencias)."""
import sqlite3
from string import ascii_uppercase

from cine.db import transaccion

# (cantidad de filas, butacas por fila). Sala 1: 10 x 12 = 120. Sala 2: 6 x 10 = 60
# (ESPECIFICACION.md -> Glosario -> Sala).
PLANOS = {"Sala 1": (10, 12), "Sala 2": (6, 10)}


def sembrar_salas(cx: sqlite3.Connection) -> None:
    with transaccion(cx):
        for nombre, (cantidad_filas, por_fila) in PLANOS.items():
            cursor = cx.execute("INSERT INTO sala (nombre) VALUES (?)", (nombre,))
            sala_id = cursor.lastrowid
            cx.executemany(
                "INSERT INTO butaca (sala_id, fila, numero) VALUES (?, ?, ?)",
                [
                    (sala_id, ascii_uppercase[f], n)
                    for f in range(cantidad_filas)
                    for n in range(1, por_fila + 1)
                ],
            )
