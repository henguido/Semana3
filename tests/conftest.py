from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cine.db import aplicar_migraciones, conectar
from cine.reloj import RelojFijo, iso
from cine.siembra import sembrar_salas

MIGRACIONES = Path(__file__).resolve().parents[1] / "cine" / "migraciones"

# Jueves 7 de agosto de 2025, dia de cambio de cartelera (RN-1).
JUEVES = datetime(2025, 8, 7, 10, 0, tzinfo=timezone.utc)
# Miercoles 13 de agosto de 2025, para piezas futuras que lo necesiten.
MIERCOLES = datetime(2025, 8, 13, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def ruta_db(tmp_path):
    return str(tmp_path / "prueba.db")


@pytest.fixture
def cx(ruta_db):
    conexion = conectar(ruta_db)
    aplicar_migraciones(conexion, MIGRACIONES)
    sembrar_salas(conexion)
    yield conexion
    conexion.close()


@pytest.fixture
def reloj():
    return RelojFijo(JUEVES)


@pytest.fixture
def pelicula(cx):
    cursor = cx.execute(
        "INSERT INTO pelicula (titulo, duracion_minutos, clasificacion_edad, distribuidora) "
        "VALUES ('Vertigo', 120, 0, 'Distribuidora Central')"
    )
    return cursor.lastrowid


def _crear_funcion(cx, pelicula_id, sala_nombre, inicio, duracion=120):
    sala_id = cx.execute(
        "SELECT id FROM sala WHERE nombre = ?", (sala_nombre,)
    ).fetchone()["id"]
    cursor = cx.execute(
        "INSERT INTO funcion (pelicula_id, sala_id, inicio, fin) VALUES (?, ?, ?, ?)",
        (pelicula_id, sala_id, iso(inicio), iso(inicio + timedelta(minutes=duracion))),
    )
    return cursor.lastrowid


@pytest.fixture
def funcion_jueves(cx, pelicula):
    """Empieza cuatro horas despues del momento del reloj: esta a la venta."""
    return _crear_funcion(cx, pelicula, "Sala 1", JUEVES + timedelta(hours=4))


@pytest.fixture
def crear_funcion(cx, pelicula):
    def hacer(sala="Sala 1", inicio=None, duracion=120):
        return _crear_funcion(cx, pelicula, sala, inicio, duracion)

    return hacer


@pytest.fixture
def butacas(cx):
    """Devuelve {numero: butaca_id} de una fila entera."""

    def hacer(sala="Sala 1", fila="A"):
        filas = cx.execute(
            "SELECT b.id, b.numero FROM butaca b JOIN sala s ON s.id = b.sala_id "
            "WHERE s.nombre = ? AND b.fila = ? ORDER BY b.numero",
            (sala, fila),
        ).fetchall()
        return {f["numero"]: f["id"] for f in filas}

    return hacer


@pytest.fixture
def cliente(cx, reloj):
    from fastapi.testclient import TestClient

    from cine.web.app import crear_app, obtener_cx, obtener_reloj

    app = crear_app()
    app.dependency_overrides[obtener_cx] = lambda: cx
    app.dependency_overrides[obtener_reloj] = lambda: reloj
    with TestClient(app) as prueba:
        yield prueba
