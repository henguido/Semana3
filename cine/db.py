"""Conexion SQLite, transaccion y migraciones.

Motor decidido en DISENO.md -> "Decisiones mayores -> Lenguaje, marco de trabajo y motor
de base de datos": SQLite en modo WAL, sin ORM. Este modulo es la unica puerta de
entrada a la base de datos.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

# RETURNING (usado a partir de la Pieza 2, en el apartado atomico) exige 3.35.0 o mas.
VERSION_SQLITE_MINIMA = (3, 35, 0)


def conectar(ruta: str) -> sqlite3.Connection:
    if sqlite3.sqlite_version_info < VERSION_SQLITE_MINIMA:
        exigida = ".".join(str(n) for n in VERSION_SQLITE_MINIMA)
        raise RuntimeError(
            f"Se requiere SQLite {exigida} o superior; esta instalacion trae "
            f"{sqlite3.sqlite_version}"
        )
    # check_same_thread=False: FastAPI/Starlette despachan las rutas sincronas en un
    # hilo del pool, distinto del que crea la conexion. La seguridad de escritura no
    # depende de esto: la da BEGIN IMMEDIATE (transaccion()), no la afinidad de hilo.
    cx = sqlite3.connect(ruta, isolation_level=None, timeout=5.0, check_same_thread=False)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA journal_mode = WAL")
    cx.execute("PRAGMA foreign_keys = ON")
    cx.execute("PRAGMA busy_timeout = 5000")
    return cx


@contextmanager
def transaccion(cx: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE: toma el bloqueo de escritura de entrada (Restriccion global 6)."""
    cx.execute("BEGIN IMMEDIATE")
    try:
        yield cx
    except Exception:
        cx.execute("ROLLBACK")
        raise
    else:
        cx.execute("COMMIT")


def aplicar_migraciones(cx: sqlite3.Connection, carpeta: Path) -> list[str]:
    """Cada migracion se sella junto con su propio contenido, en el mismo script: o
    quedan juntos, o no queda ninguno de los dos (Restriccion global 9)."""
    cx.execute("CREATE TABLE IF NOT EXISTS migracion (nombre TEXT PRIMARY KEY)")
    aplicadas = {f["nombre"] for f in cx.execute("SELECT nombre FROM migracion")}
    nuevas: list[str] = []
    for archivo in sorted(carpeta.glob("*.sql")):
        if archivo.name in aplicadas:
            continue
        guion = (
            "BEGIN IMMEDIATE;\n"
            + archivo.read_text(encoding="utf-8")
            + f"\nINSERT INTO migracion (nombre) VALUES ('{archivo.name}');\nCOMMIT;"
        )
        cx.executescript(guion)
        nuevas.append(archivo.name)
    return nuevas
