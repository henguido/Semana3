"""Montaje de FastAPI. `obtener_cx` y `obtener_reloj` son dependencias sobreescribibles:
las pruebas inyectan su propia conexion y su propio reloj (Restriccion global 1)."""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cine.db import aplicar_migraciones, conectar
from cine.reloj import RelojReal

AQUI = Path(__file__).resolve().parent
MIGRACIONES = AQUI.parent / "migraciones"

plantillas = Jinja2Templates(directory=str(AQUI / "plantillas"))

_cx = None
_reloj = RelojReal()


def obtener_cx():
    global _cx
    if _cx is None:
        _cx = conectar(os.environ.get("CINE_DB", "cine.db"))
        aplicar_migraciones(_cx, MIGRACIONES)
    return _cx


def obtener_reloj():
    return _reloj


def crear_app() -> FastAPI:
    from cine.web import rutas_cliente

    app = FastAPI(title="Cine Variedades")
    app.mount("/estaticos", StaticFiles(directory=str(AQUI / "estaticos")), name="estaticos")
    app.include_router(rutas_cliente.router)
    return app


app = crear_app()
