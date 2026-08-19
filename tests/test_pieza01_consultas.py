from datetime import timedelta

from cine.catalogo.consultas import cartelera_vigente, esta_a_la_venta, funcion_por_id
from cine.mapa.consultas import estado_del_mapa
from cine.mapa.modelos import EstadoButaca
from cine.reloj import iso
from tests.conftest import JUEVES


def test_la_funcion_desaparece_de_la_cartelera_a_la_hora_exacta_de_inicio(
    cx, reloj, crear_funcion
):
    inicio = JUEVES + timedelta(hours=4)
    crear_funcion(inicio=inicio)

    reloj.poner(inicio - timedelta(seconds=1))
    assert len(cartelera_vigente(cx, reloj.ahora())) == 1

    reloj.poner(inicio)
    assert cartelera_vigente(cx, reloj.ahora()) == []  # CA-10


def test_una_funcion_cancelada_no_aparece_en_la_cartelera(cx, reloj, funcion_jueves):
    cx.execute("UPDATE funcion SET estado = 'cancelada' WHERE id = ?", (funcion_jueves,))
    assert cartelera_vigente(cx, reloj.ahora()) == []  # RN-4


def test_el_mapa_dibuja_los_cuatro_estados_y_resuelve_el_vencimiento(
    cx, reloj, funcion_jueves, butacas
):
    fila = butacas()
    vigente = iso(reloj.ahora() + timedelta(minutes=5))
    vencido = iso(reloj.ahora() - timedelta(seconds=1))
    cx.executemany(
        "INSERT INTO ocupacion (funcion_id, butaca_id, estado, vence_en, sesion_id) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (funcion_jueves, fila[1], "vendida", None, None),
            (funcion_jueves, fila[2], "apartada", vigente, "sesion-viva"),
            (funcion_jueves, fila[3], "apartada", vencido, "sesion-muerta"),
            (funcion_jueves, fila[4], "bloqueada", None, None),
        ],
    )

    mapa = {b.butaca_id: b for b in estado_del_mapa(cx, funcion_jueves, reloj.ahora())}

    assert len(mapa) == 120
    assert mapa[fila[1]].estado is EstadoButaca.VENDIDA
    assert mapa[fila[2]].estado is EstadoButaca.APARTADA
    assert mapa[fila[3]].estado is EstadoButaca.DISPONIBLE  # vencio: libre para los demas
    assert mapa[fila[4]].estado is EstadoButaca.NO_VENDIBLE
    assert mapa[fila[5]].estado is EstadoButaca.DISPONIBLE


def test_el_mapa_sale_ordenado_por_fila_y_numero(cx, reloj, funcion_jueves):
    mapa = estado_del_mapa(cx, funcion_jueves, reloj.ahora())
    assert [(b.fila, b.numero) for b in mapa[:3]] == [("A", 1), ("A", 2), ("A", 3)]
    assert (mapa[-1].fila, mapa[-1].numero) == ("J", 12)


def test_la_funcion_por_id_trae_su_pelicula_y_su_sala(cx, reloj, funcion_jueves):
    detalle = funcion_por_id(cx, funcion_jueves)
    assert detalle.titulo == "Vertigo"
    assert detalle.sala_nombre == "Sala 1"
    assert esta_a_la_venta(detalle, reloj.ahora()) is True
