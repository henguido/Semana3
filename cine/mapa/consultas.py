"""Unica consulta de lectura del Mapa de ocupacion.

El vencimiento del apartado se resuelve DENTRO de esta consulta (DISENO.md -> Decision
mayor 2: "el vencimiento del apartado es una fecha guardada en la fila, que se evalua en
la misma consulta que dibuja el mapa"). Una butaca sin fila esta libre.
"""
import sqlite3
from datetime import datetime

from cine.mapa.modelos import ButacaDelMapa, EstadoButaca
from cine.reloj import iso

SQL_MAPA = """
SELECT b.id      AS butaca_id,
       b.fila    AS fila,
       b.numero  AS numero,
       CASE
         WHEN o.id IS NULL                                    THEN 'disponible'
         WHEN o.estado = 'vendida'                            THEN 'vendida'
         WHEN o.estado = 'bloqueada'                          THEN 'no_vendible'
         WHEN o.estado = 'apartada' AND o.vence_en > :ahora   THEN 'apartada'
         ELSE 'disponible'
       END AS estado,
       CASE WHEN o.estado = 'apartada' THEN o.sesion_id ELSE NULL END AS sesion_id
  FROM funcion f
  JOIN butaca  b ON b.sala_id = f.sala_id
  LEFT JOIN ocupacion o ON o.funcion_id = f.id AND o.butaca_id = b.id
 WHERE f.id = :funcion_id
 ORDER BY b.fila, b.numero
"""


def estado_del_mapa(
    cx: sqlite3.Connection, funcion_id: int, ahora: datetime
) -> list[ButacaDelMapa]:
    filas = cx.execute(SQL_MAPA, {"funcion_id": funcion_id, "ahora": iso(ahora)})
    return [
        ButacaDelMapa(
            butaca_id=f["butaca_id"],
            fila=f["fila"],
            numero=f["numero"],
            estado=EstadoButaca(f["estado"]),
            sesion_id=f["sesion_id"],
        )
        for f in filas
    ]
