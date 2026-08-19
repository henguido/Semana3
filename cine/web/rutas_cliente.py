"""Rutas del cliente. Pieza 1: solo lectura (cartelera y mapa). Las rutas de seleccion,
apartado, pago y consulta por codigo llegan en las Piezas 2, 3 y 4."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from cine.catalogo.consultas import cartelera_vigente, esta_a_la_venta, funcion_por_id
from cine.mapa.consultas import estado_del_mapa
from cine.web.app import obtener_cx, obtener_reloj, plantillas

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def ver_cartelera(request: Request, cx=Depends(obtener_cx), reloj=Depends(obtener_reloj)):
    funciones = cartelera_vigente(cx, reloj.ahora())
    return plantillas.TemplateResponse(
        request=request, name="cartelera.html", context={"funciones": funciones}
    )


@router.get("/funcion/{funcion_id}", response_class=HTMLResponse)
def ver_mapa(
    request: Request, funcion_id: int, cx=Depends(obtener_cx), reloj=Depends(obtener_reloj)
):
    ahora = reloj.ahora()
    funcion = funcion_por_id(cx, funcion_id)
    if funcion is None:
        return plantillas.TemplateResponse(
            request=request,
            name="aviso.html",
            context={"titulo": "Esa funcion no existe", "detalle": ""},
            status_code=404,
        )
    if not esta_a_la_venta(funcion, ahora):
        return plantillas.TemplateResponse(
            request=request,
            name="aviso.html",
            context={
                "titulo": "La venta de esta funcion ya cerro",
                "detalle": "Vuelva a la cartelera para ver las funciones a la venta.",
            },
            status_code=410,
        )
    return plantillas.TemplateResponse(
        request=request,
        name="mapa.html",
        context={"funcion": funcion, "butacas": estado_del_mapa(cx, funcion_id, ahora)},
    )
