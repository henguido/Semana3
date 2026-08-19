"""Datos de prueba para comprobar a ojo la Pieza 1 (cartelera y mapa).

Recrea la base de datos desde cero: aplica las migraciones, siembra las dos salas y
carga una pelicula con dos funciones y unas filas de `ocupacion` insertadas a mano, tal
como pide la comprobacion observable de PLAN.md -> Pieza 1.

Uso:
    .venv/Scripts/python scripts/datos_prueba.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from cine.db import aplicar_migraciones, conectar  # noqa: E402
from cine.reloj import iso  # noqa: E402
from cine.siembra import sembrar_salas  # noqa: E402

RUTA_DB = os.environ.get("CINE_DB", str(RAIZ / "cine.db"))
MIGRACIONES = RAIZ / "cine" / "migraciones"


def recrear() -> None:
    for sufijo in ("", "-wal", "-shm"):
        candidato = Path(RUTA_DB + sufijo)
        if candidato.exists():
            candidato.unlink()

    cx = conectar(RUTA_DB)
    aplicar_migraciones(cx, MIGRACIONES)
    sembrar_salas(cx)

    ahora = datetime.now(timezone.utc)
    pelicula_id = cx.execute(
        "INSERT INTO pelicula (titulo, duracion_minutos, clasificacion_edad, distribuidora) "
        "VALUES ('Vertigo', 120, 0, 'Distribuidora Central') RETURNING id"
    ).fetchone()["id"]
    sala_1 = cx.execute("SELECT id FROM sala WHERE nombre = 'Sala 1'").fetchone()["id"]

    # Funcion A: empieza en 30 segundos reales. Sirve para ver en vivo la comprobacion
    # 2 de la Pieza 1 (CA-10): esta en la cartelera ahora, y desaparece sola al pasar
    # su hora de inicio, sin recargar nada mas que la pagina.
    funcion_a = cx.execute(
        "INSERT INTO funcion (pelicula_id, sala_id, inicio, fin) VALUES (?, ?, ?, ?) "
        "RETURNING id",
        (
            pelicula_id,
            sala_1,
            iso(ahora + timedelta(seconds=30)),
            iso(ahora + timedelta(seconds=30) + timedelta(minutes=120)),
        ),
    ).fetchone()["id"]

    # Funcion B: empieza en 4 horas. Sobre esta se insertan a mano los cuatro estados
    # de la comprobacion 1: vendida, apartada vigente, apartada vencida, bloqueada.
    funcion_b = cx.execute(
        "INSERT INTO funcion (pelicula_id, sala_id, inicio, fin) VALUES (?, ?, ?, ?) "
        "RETURNING id",
        (
            pelicula_id,
            sala_1,
            iso(ahora + timedelta(hours=4)),
            iso(ahora + timedelta(hours=6)),
        ),
    ).fetchone()["id"]

    butacas_a1 = cx.execute(
        "SELECT b.id, b.numero FROM butaca b JOIN sala s ON s.id = b.sala_id "
        "WHERE s.nombre = 'Sala 1' AND b.fila = 'A' ORDER BY b.numero"
    ).fetchall()
    ids = {f["numero"]: f["id"] for f in butacas_a1}

    cx.executemany(
        "INSERT INTO ocupacion (funcion_id, butaca_id, estado, vence_en, sesion_id) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (funcion_b, ids[1], "vendida", None, None),
            (funcion_b, ids[2], "apartada", iso(ahora + timedelta(minutes=30)), "demo-vigente"),
            (funcion_b, ids[3], "apartada", iso(ahora - timedelta(minutes=1)), "demo-vencida"),
            (funcion_b, ids[4], "bloqueada", None, None),
        ],
    )
    cx.close()

    print(f"Base de datos recreada en: {RUTA_DB}")
    print(f"Funcion A (cierra en 30s, para ver CA-10 en vivo): /funcion/{funcion_a}")
    print(f"Funcion B (mapa con los cuatro estados): /funcion/{funcion_b}")
    print("  A-1 vendida, A-2 apartada vigente, A-3 apartada vencida (debe verse "
          "disponible), A-4 bloqueada (no vendible).")


if __name__ == "__main__":
    recrear()
