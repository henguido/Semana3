import sqlite3
from datetime import datetime, timezone

import pytest

from cine.reloj import RelojFijo, desde_iso, iso


def test_el_reloj_fijo_avanza_solo_cuando_se_lo_pide():
    reloj = RelojFijo(datetime(2025, 8, 7, 10, 0, tzinfo=timezone.utc))
    primero = reloj.ahora()
    assert reloj.ahora() == primero
    reloj.avanzar(minutes=6)
    assert (reloj.ahora() - primero).total_seconds() == 360


def test_el_iso_es_de_ancho_fijo_para_que_ordene_lexicograficamente():
    temprano = iso(datetime(2025, 8, 7, 9, 59, 59, 900000, tzinfo=timezone.utc))
    tarde = iso(datetime(2025, 8, 7, 10, 0, 0, 0, tzinfo=timezone.utc))
    assert len(temprano) == len(tarde) == 24
    assert temprano < tarde
    assert desde_iso(tarde) == datetime(2025, 8, 7, 10, 0, tzinfo=timezone.utc)


def test_las_dos_salas_tienen_120_y_60_butacas(cx):
    filas = cx.execute(
        "SELECT s.nombre, COUNT(b.id) AS total "
        "FROM sala s JOIN butaca b ON b.sala_id = s.id GROUP BY s.id ORDER BY s.nombre"
    ).fetchall()
    assert [(f["nombre"], f["total"]) for f in filas] == [("Sala 1", 120), ("Sala 2", 60)]


def test_la_unicidad_de_funcion_y_butaca_la_hace_cumplir_la_tabla(cx, funcion_jueves):
    butaca = cx.execute("SELECT id FROM butaca LIMIT 1").fetchone()["id"]
    cx.execute(
        "INSERT INTO ocupacion (funcion_id, butaca_id, estado) VALUES (?, ?, 'vendida')",
        (funcion_jueves, butaca),
    )
    with pytest.raises(sqlite3.IntegrityError):
        cx.execute(
            "INSERT INTO ocupacion (funcion_id, butaca_id, estado) VALUES (?, ?, 'apartada')",
            (funcion_jueves, butaca),
        )
