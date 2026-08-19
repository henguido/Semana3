from datetime import timedelta

from cine.reloj import iso
from tests.conftest import JUEVES


def test_la_cartelera_muestra_la_funcion_y_deja_de_mostrarla_al_empezar(
    cliente, reloj, crear_funcion
):
    inicio = JUEVES + timedelta(hours=4)
    crear_funcion(inicio=inicio)

    reloj.poner(inicio - timedelta(seconds=1))
    assert "Vertigo" in cliente.get("/").text

    reloj.poner(inicio)
    assert "Vertigo" not in cliente.get("/").text  # CA-10


def test_el_mapa_marca_cada_butaca_con_su_estado(cx, cliente, reloj, funcion_jueves, butacas):
    fila = butacas()
    cx.executemany(
        "INSERT INTO ocupacion (funcion_id, butaca_id, estado, vence_en, sesion_id) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (funcion_jueves, fila[1], "vendida", None, None),
            (funcion_jueves, fila[2], "apartada",
             iso(reloj.ahora() + timedelta(minutes=5)), "otra"),
            (funcion_jueves, fila[3], "bloqueada", None, None),
        ],
    )

    html = cliente.get(f"/funcion/{funcion_jueves}").text

    assert f'data-butaca="{fila[1]}" data-estado="vendida"' in html
    assert f'data-butaca="{fila[2]}" data-estado="apartada"' in html
    assert f'data-butaca="{fila[3]}" data-estado="no_vendible"' in html
    assert f'data-butaca="{fila[4]}" data-estado="disponible"' in html


def test_el_mapa_de_una_funcion_que_ya_empezo_dice_que_la_venta_cerro(
    cliente, reloj, crear_funcion
):
    inicio = JUEVES + timedelta(hours=4)
    funcion_id = crear_funcion(inicio=inicio)
    reloj.poner(inicio)

    respuesta = cliente.get(f"/funcion/{funcion_id}")

    assert respuesta.status_code == 410
    assert "cerr" in respuesta.text.lower()


def test_una_funcion_inexistente_responde_404(cliente):
    respuesta = cliente.get("/funcion/999999")
    assert respuesta.status_code == 404
