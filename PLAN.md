# Venta de entradas en línea — Cine Variedades — Plan de construcción

> Plan de piezas verticales para construir el sistema especificado en `ESPECIFICACION.md` según
> el diseño de `DISENO.md`. Cada pieza es un recorrido completo, de la pantalla al dato
> persistido, con una comprobación observable definida antes de construirla. Para ejecutar una
> pieza, use la skill `superpowers:test-driven-development` dentro de ella (rojo → verde → commit)
> y `superpowers:executing-plans` o `superpowers:subagent-driven-development` para avanzar de
> pieza en pieza con revisión entre cada una.

**Objetivo:** vender entradas por internet con selección de butaca desde el teléfono, sobre el
mismo mapa de ocupación que usa la taquilla, reemplazando el control manual en papel.

**Arquitectura:** ver `DISENO.md`. El **Mapa de ocupación** es el único módulo autorizado a
escribir en la tabla `ocupacion`, donde vive la restricción de unicidad que hace cumplir RNF-1.
Ventas y Cancelaciones orquestan; los demás módulos no saben que existe nadie por encima de ellos.

**Tecnología:** Python 3.11+, FastAPI, Jinja2, SQLite (`sqlite3` de la biblioteca estándar, modo
WAL, sin ORM), pytest + `httpx`, `openpyxl` para las planillas. Decisión formal, con su
justificación y sus condiciones, en `DISENO.md` → «Decisiones mayores → Lenguaje, marco de
trabajo y motor de base de datos».

Este documento no lleva código de implementación. Cuando una pieza tiene un mecanismo cuya forma
exacta es la razón de ser de una decisión de diseño —el apoderamiento atómico del apartado, la
actualización en el lugar al bloquear una butaca—, se cita como referencia corta, no como
implementación completa: el código real se escribe al ejecutar la pieza, con TDD.

---

## Restricciones globales

Rigen para todas las piezas.

1. Toda hora viene de un reloj inyectable (`Reloj` real en producción, `RelojFijo` en pruebas).
   Ningún módulo llama a `datetime.now()` ni a `datetime('now')` de SQLite directamente. Sin esto,
   CA-6, CA-10 y CA-15 no se pueden comprobar sin esperar minutos reales.
2. Las horas se guardan en UTC como texto ISO-8601 de ancho fijo, para que la comparación
   lexicográfica de SQLite ordene fechas correctamente.
3. Todo monto de dinero es un entero en céntimos. Nunca `float`.
4. Solo el módulo `mapa/` escribe en la tabla `ocupacion`. Es lo que permite auditar RNF-1
   mirando un solo lugar.
5. Queda prohibido borrar-luego-insertar en `ocupacion`: apoderarse de un apartado vencido y
   bloquear una butaca se hacen actualizando la fila existente, para que la unicidad no se suelte
   ni por un instante.
6. Toda operación que cambia estado corre dentro de una transacción con `BEGIN IMMEDIATE`.
   Apartar, confirmar una compra, anular, cancelar una función y declarar fuera de servicio son
   transacciones o no son nada (RNF-2).
7. Ninguna tarea programada (barrido de filas muertas, reintento de avisos) es condición para la
   integridad del sistema.
8. Vocabulario del dominio en español, en el código y en la base de datos: `butaca`, `funcion`,
   `ocupacion`, `apartado`, `compra`, `entrada`, `reembolso`, `anulacion`. Nunca «boleto» ni
   «reserva» (glosario de la especificación).
9. Cada pieza que agrega tablas trae su propia migración SQL numerada; ninguna migración se edita
   después de aplicarse.
10. Cada tarea dentro de una pieza sigue TDD (prueba que falla → implementación mínima → prueba
    que pasa) y termina en un commit propio, en español, en imperativo.

---

## Infraestructura de prueba común

Tres piezas de utilería que varias piezas necesitan y que se construyen la primera vez que hacen
falta, no antes:

| Utilidad | Se construye en | Para qué |
|---|---|---|
| Reloj inyectable (`RelojFijo`, con `avanzar()` y `poner()`) | Pieza 1 | Probar vencimientos y cierres de venta sin esperar minutos reales |
| Buzón de correo falso (archivo por correo) y remitente que siempre falla | Pieza 3 | Probar el comprobante, el aviso de cancelación y el caso «el correo está caído», sin contratar un servicio |
| Arranque de peticiones concurrentes desde hilos, con `threading.Barrier` | Pieza 2 | Probar CA-1 y RNF-4 con simultaneidad real, no con dos pestañas a mano |

---

## Estructura de archivos

Partida por responsabilidad, siguiendo los once componentes del diseño. Lo que cambia junto vive
junto; el número entre paréntesis es la pieza que lo crea.

```
cine/
  reloj.py, db.py                 Reloj inyectable, conexión SQLite, transacción (1)
  migraciones/                    Una migración numerada por pieza que agrega tablas
  siembra.py                      Planos de las dos salas y personal de arranque (1, 5)
  catalogo/                       Salas, películas, funciones (1, 7); fuera de servicio (6)
  mapa/                           Único escritor de `ocupacion`: mapa, apartado, bloqueo (1, 2, 6, 9, 10)
  seleccion/                      Regla de butaca solitaria y límite de seis, cálculo puro (2)
  tarifas/                        Cálculo de tarifa y versión de precios con su historial (3, 7)
  cobro/                          Cobro simulado: aprueba, rechaza, revierte (3)
  ventas/                         Código de confirmación, compra, consulta, anulación (3, 4, 9)
  cancelaciones/                  Cancelar función y reembolsar todo (10)
  puerta/                         Ingreso por entrada y diferencia de estudiante (8)
  avisos/                         Correo: remitente, buzón de archivos, reintento (3, 10)
  acceso/                         Usuarios, roles, autenticación (5)
  reportes/                       Consultas de solo lectura y planillas (11)
  tareas.py                       Barrido y reintento de avisos, ninguno crítico (10)
  web/                            FastAPI: rutas de cliente, taquilla y administración; plantillas Jinja2
tests/
  conftest.py                     Fixtures compartidas: cx, reloj, cliente, personal, buzón
  test_pieza01_*.py … test_pieza11_*.py
```

---

# Piezas

## Pieza 1 — Ver la cartelera y el mapa de una sala

**Estado:** Cerrada (2026-08-18)

**Recorrido:** el cliente abre la cartelera de la semana desde el teléfono, ve las funciones que
todavía no han empezado, entra a una y ve el mapa de la sala con el estado de cada butaca.

**Requisitos que cubre:** RF-3, RF-6 (lectura), RN-3, RN-4 (exclusión de canceladas en la
cartelera), RNF-6, CA-10.

**Alcance:**
- Incluye: esqueleto del proyecto, reloj inyectable, conexión y migraciones de SQLite, catálogo
  mínimo (sala, butaca, película, función), la tabla `ocupacion` con su restricción
  `UNIQUE(funcion, butaca)`, la consulta que resuelve el estado de cada butaca —incluido el
  vencimiento del apartado— en una sola consulta, siembra de las dos salas (120 y 60 butacas),
  pantallas de cartelera y mapa, primero teléfono.
- No incluye: seleccionar butacas ni apartar (Pieza 2), ninguna escritura sobre `ocupacion`.
- Depende de: nada. Es la primera pieza.

**Componentes que toca:** `cine/reloj.py`, `cine/db.py`, `cine/migraciones/001_catalogo.sql`,
`cine/siembra.py`, `cine/catalogo/consultas.py`, `cine/mapa/modelos.py`,
`cine/mapa/consultas.py`, `cine/web/app.py`, `cine/web/rutas_cliente.py`, plantillas `base`,
`cartelera`, `mapa`, `aviso`.

**Comprobación observable:**
1. Con filas de `ocupacion` insertadas a mano —una vendida, una apartada con vencimiento futuro,
   una apartada con vencimiento pasado, una bloqueada— el mapa dibuja los cuatro estados y la de
   vencimiento pasado aparece **disponible**.
2. Con el reloj puesto un segundo antes del inicio de una función, esa función está en la
   cartelera; un segundo después, no aparece (CA-10).
3. El mapa de 120 butacas se ve y se usa en una ventana de 375 px de ancho, con desplazamiento
   lateral solo dentro del mapa, nunca de la página completa.

**Evidencia (al cerrar la pieza):**
- [x] **Pruebas ejecutadas:** `./.venv/Scripts/python -m pytest -v` → **13 passed, 1 warning
  in 2.59s** (`tests/test_pieza01_cimientos.py`, `tests/test_pieza01_consultas.py`,
  `tests/test_pieza01_pantallas.py`). El único warning es una advertencia de obsolescencia de
  Starlette sobre `httpx` en `TestClient`, sin efecto funcional.
- [x] **Comprobación observable realizada:** con `scripts/datos_prueba.py` (recrea `cine.db`,
  siembra las dos salas, una película y dos funciones) y el servidor real
  (`uvicorn cine.web.app:app`), verificado en el navegador a 375×812 px:
  1. Función B (`/funcion/2`) con A-1 insertada a mano como `vendida`, A-2 como `apartada`
     vigente, A-3 como `apartada` con `vence_en` ya pasado, A-4 como `bloqueada`: el mapa
     mostró exactamente `vendida` / `apartada` (deshabilitada) / **`disponible`** / `no_vendible`
     — la de vencimiento pasado apareció disponible, tal como exige la comprobación.
  2. Función A (`/funcion/1`), sembrada para empezar 30 segundos después del arranque real:
     estuvo en la cartelera antes de esa hora y, comprobado con el reloj real (no `RelojFijo`),
     `GET /funcion/1` pasó de 200 a **410** exactamente al cruzar su hora de inicio, sin ninguna
     intervención manual (CA-10 con el reloj real, además de la prueba automatizada que ya lo
     cubre con `RelojFijo`).
  3. Medido con JavaScript en el navegador a 375 px: `document.body.scrollWidth` (375) es igual
     al ancho de la ventana (375) — **la página nunca se desplaza a lo ancho**; `mapa.scrollWidth`
     (451) es mayor que `mapa.clientWidth` (343) — **el desplazamiento ocurre solo dentro del
     mapa** (RNF-6).
- [x] **Commit(s):** pendiente — se hace después de esta revisión, según lo acordado.
- [x] **Notas / desviaciones del plan:** se corrigieron dos defectos reales que las pruebas
  detectaron y que `PLAN.md` no había anticipado, ninguno cambia alcance ni requisitos:
  (a) `sqlite3.Connection` necesitó `check_same_thread=False` en `cine/db.py`, porque
  Starlette/FastAPI despachan las rutas síncronas en un hilo del pool distinto al que abre la
  conexión; la seguridad de escritura la sigue dando `BEGIN IMMEDIATE`, no la afinidad de hilo.
  (b) en `mapa.html` los atributos `data-butaca` y `data-estado` se unieron en la misma línea del
  botón, para que coincidan sin ambigüedad con el contrato de marcado que la Pieza 2 va a
  consumir. Se agregó además `scripts/datos_prueba.py` (datos de prueba reales para ejecutar la
  comprobación, no previsto como archivo propio en `PLAN.md` pero exigido por la consigna de esta
  ronda) y `.gitignore` (excluye `.venv/`, `cine.db*`, `__pycache__/`, `correos/`).

---

## Pieza 2 — Escoger butacas y que queden apartadas

**Estado:** Pendiente

**Recorrido:** el cliente selecciona butacas, el sistema juzga la selección y, si es admisible,
la aparta por 5 minutos para su sesión. Mientras escoge, el mapa se refresca cada 10 segundos sin
tocarle la selección.

**Requisitos que cubre:** RF-6 (escritura), RF-7, RF-8, RF-9, RN-13, RN-14 (creación, vencimiento
y apoderamiento), RN-15, RN-16, RNF-1, RNF-4, y las tres decisiones mayores del diseño (unicidad
por restricción, vencimiento por fecha, refresco cada 10 segundos).

**Alcance:**
- Incluye: regla de butaca solitaria y límite de seis (cálculo puro, sin base de datos),
  parámetros de operación editables, el apartado atómico (una sola sentencia que inserta si la
  butaca está libre o se apodera de una fila de apartado vencida), barrido de filas muertas
  (aseo, nunca condición para liberar), pantalla de selección con refresco JS cada 10 segundos.
- No incluye: pago ni confirmación de compra (Pieza 3).
- Depende de: Pieza 1 (mapa, catálogo).

**Componentes que toca:** `cine/seleccion/reglas.py`, `cine/migraciones/002_parametros.sql`,
`cine/parametros.py`, `cine/mapa/apartado.py`, `cine/web/estaticos/mapa.js`, ampliación de
`mapa.html`.

**Mecanismo de referencia (no se implementa aquí, se cita porque es la razón de ser de la
pieza):** el apartado se resuelve con una sola sentencia `INSERT … ON CONFLICT(funcion, butaca)
DO UPDATE … WHERE estado='apartada' AND (vence_en <= :ahora OR sesion_id = :sesion) RETURNING id`.
Si el `WHERE` no se cumple, no se actualiza nada y la ausencia de fila en `RETURNING` **es** el
conflicto. Nunca se borra una fila para insertar otra.

**Comprobación observable:**
1. Fila 1–10 con la 1 y la 3 vendidas: escoger 4 y 5 se acepta; escoger 5 y 7 se rechaza
   nombrando la butaca 6 (CA-2). Fila libre: escoger la 2 se rechaza nombrando la 1; escoger 1 y 2
   se acepta (CA-3).
2. Escoger 7 butacas se rechaza indicando el límite y cuántas lleva.
3. Con el reloj adelantado más de 5 minutos, la butaca apartada vuelve a estar disponible **sin
   que corra ninguna tarea**, otra sesión se la lleva, y queda **exactamente una fila** de
   `ocupacion` para esa butaca (CA-6): prueba de que no hubo borrar-luego-insertar.
4. 50 hilos concurrentes apartando la misma butaca: uno gana, 49 reciben conflicto nombrando la
   butaca, y hay una sola fila en `ocupacion` (CA-1, RNF-4).
5. Con dos pestañas abiertas: el refresco de 10 segundos nunca deselecciona en silencio —si una
   butaca escogida se ocupa, se marca **en conflicto**— y no toca butacas que el cliente no había
   escogido.

**Evidencia (al cerrar la pieza):**
- [ ] Pruebas ejecutadas (comando y resultado):
- [ ] Comprobación observable realizada (pasos seguidos y resultado):
- [ ] Commit(s):
- [ ] Notas / desviaciones del plan:

---

## Pieza 3 — Pagar y confirmar la compra

**Estado:** Pendiente

**Recorrido:** el cliente declara por cada entrada si es de estudiante, ve el desglose, confirma
la edad si la película la exige, da su correo, paga con un cobro simulado y recibe el código de
confirmación en pantalla y por correo.

**Requisitos que cubre:** RF-5, RF-10, RF-11, RF-12, RN-6 a RN-11, RN-14 (segunda mitad), RNF-2,
REG-1, REG-2, CA-4, CA-15, mitad de CA-16.

**Alcance:**
- Incluye: cálculo de tarifa por día y condición (cálculo puro, con la zona horaria del cine para
  decidir si una función es de miércoles), versión de tarifa vigente con su historial, cobro
  simulado (aprobado / rechazado / revertido, sobrevive a que la compra no llegue a existir),
  código de confirmación irrepetible, la transacción única que convierte apartado en venta y crea
  compra + entradas, avisos por correo (remitente abstracto, buzón de archivos para desarrollo y
  pruebas, remitente que falla para probar el caso adverso), pantallas de pago y confirmación.
- No incluye: consulta por código (Pieza 4), venta en taquilla (Pieza 5).
- Depende de: Pieza 2 (apartado, `butacas_de_la_sesion`).

**Componentes que toca:** `cine/tarifas/`, `cine/cobro/`, `cine/ventas/codigo.py`,
`cine/ventas/compra.py`, `cine/avisos/`, plantillas `pago`, `confirmacion`.

**Decisión de orden que gobierna esta pieza:** el flujo sigue el orden fijado en `DISENO.md` →
«Flujo de una compra» (venta abierta → reglas → apartar → tarifar → verificar → cobrar →
transacción única → aviso fuera de la transacción). Si el cobro se aprueba y la conversión falla
—porque otra sesión reclamó una butaca tras vencer el apartado—, el cobro se marca **revertido**;
eso no es un reembolso y no debe aparecer como tal en ningún reporte (RN-22).

**Comprobación observable:**
1. Una compra de estudiante para un miércoles cuesta exactamente la mitad del precio base, y su
   tarifa registrada es «miércoles», no «estudiante» (CA-4).
2. Un pago rechazado se informa y las butacas siguen apartadas para reintentar sin volver a
   escoger.
3. Con el reloj adelantado 6 minutos y nadie más tocando las butacas, la compra se confirma
   (CA-15, primera mitad).
4. Con el reloj adelantado 6 minutos y otra sesión llevándose una butaca, **no se confirma
   ninguna** y el cobro simulado queda **revertido** (CA-15, segunda mitad; CA-16).
5. Confirmada la compra, aparece el código en pantalla y existe un archivo nuevo en el buzón de
   correo con ese código; matando el proceso justo después de confirmar y volviendo a levantarlo,
   la compra sigue ahí (RNF-2).

**Evidencia (al cerrar la pieza):**
- [ ] Pruebas ejecutadas (comando y resultado):
- [ ] Comprobación observable realizada (pasos seguidos y resultado):
- [ ] Commit(s):
- [ ] Notas / desviaciones del plan:

---

## Pieza 4 — Consultar mi compra por su código

**Estado:** Pendiente

**Recorrido:** el cliente escribe su código de confirmación y ve su función, sus butacas, el
monto y el estado de su compra.

**Requisitos que cubre:** RF-13.

**Alcance:**
- Incluye: consulta de una compra por código, con sus entradas; pantallas de búsqueda y de
  resultado.
- No incluye: nada más allá de la lectura. Es la pieza más pequeña del plan, y se adelanta a
  propósito: sin ella, comprobar las Piezas 8, 9 y 10 exigiría mirar la base de datos directamente
  en vez de una pantalla.
- Depende de: Pieza 3 (existencia de compras confirmadas).

**Componentes que toca:** `cine/ventas/consulta.py`, plantillas `consultar`, `compra`.

**Comprobación observable:**
1. El código de una compra real muestra su función, sus butacas, su monto y su estado.
2. Un código inexistente responde que la compra no existe, **sin dar ninguna pista** sobre cuáles
   códigos sí existen.

**Evidencia (al cerrar la pieza):**
- [ ] Pruebas ejecutadas (comando y resultado):
- [ ] Comprobación observable realizada (pasos seguidos y resultado):
- [ ] Commit(s):
- [ ] Notas / desviaciones del plan:

---

## Pieza 5 — El personal entra al sistema y la taquilla vende sobre el mismo mapa

**Estado:** Pendiente

**Recorrido:** el taquillero se identifica con su cuenta propia y vende sobre la misma función,
el mismo mapa y las mismas reglas que la web. Una butaca vendida en taquilla desaparece del
teléfono del cliente en el siguiente refresco.

**Requisitos que cubre:** RF-14, RF-28, RN-13 entre canales, RN-15 y RN-16 sin excepción para el
personal, REG-1 (canal y quién vendió), CA-1 entre canales, CA-3 (última frase).

**Alcance:**
- Incluye: cuentas del personal (una por persona, no por rol), autenticación, restricción por
  rol, sesión del personal; **extracción a un módulo compartido** de las reglas de selección, el
  apartado y la confirmación de compra, para que la web y la taquilla llamen exactamente las
  mismas funciones; rutas y pantallas de taquilla (mapa, pago, confirmación); pantalla de
  entrar/salir.
- No incluye: anulación (Pieza 9), puerta (Pieza 8).
- Depende de: Piezas 2 y 3, cuya lógica se extrae a un módulo compartido sin cambiar su
  comportamiento (las pruebas de esas dos piezas deben seguir pasando sin tocarlas).

**Componentes que toca:** `cine/acceso/`, `cine/web/flujo_compra.py` (el módulo compartido),
`cine/web/rutas_taquilla.py`, plantillas `entrar`, `taquilla`, `taquilla_mapa`, `taquilla_pago`,
`taquilla_confirmacion`, `admin` (esqueleto).

**Comprobación observable:**
1. El taquillero vende la butaca F-12; el mapa del cliente en su teléfono la muestra vendida en
   menos de 10 segundos, y la compra registra canal `taquilla` y la identidad de quien vendió.
2. Un cliente sin sesión que pide la dirección de taquilla recibe negativa.
3. El taquillero que intenta aislar una butaca recibe el mismo rechazo, con las mismas palabras,
   que el cliente (CA-3).
4. Una venta web y una de taquilla, simultáneas, por la misma butaca: solo una se confirma
   (CA-1 entre canales).
5. Las pruebas de las Piezas 2, 3 y 4 siguen pasando sin modificarlas: es la prueba de que la
   extracción del flujo compartido no cambió el comportamiento de la web.

**Evidencia (al cerrar la pieza):**
- [ ] Pruebas ejecutadas (comando y resultado):
- [ ] Comprobación observable realizada (pasos seguidos y resultado):
- [ ] Commit(s):
- [ ] Notas / desviaciones del plan:

---

## Pieza 6 — Declarar una butaca fuera de servicio

**Estado:** Pendiente

**Recorrido:** el administrador declara una butaca dañada, el sistema la bloquea en las funciones
que no han empezado y le muestra la lista de compras futuras que la incluyen; después la
rehabilita.

**Requisitos que cubre:** RF-27, RN-12, RN-17, CA-13, CA-14 (parte de datos).

**Alcance:**
- Incluye: el hecho durable de que una butaca está fuera de servicio (motivo, desde, hasta),
  bloquear/desbloquear en el Mapa **actualizando la fila existente** (nunca borrar-luego-insertar,
  la misma disciplina que el apartado), declarar (recorre funciones no empezadas de esa sala) y
  rehabilitar (cierra el registro, solo toca funciones no empezadas), pantalla con la lista de
  compras futuras afectadas.
- No incluye: nada sobre funciones ya empezadas o terminadas, que nunca se tocan.
- Depende de: Pieza 5 (rol administrador), Pieza 2 (Mapa de ocupación).

**Componentes que toca:** `cine/migraciones/00X_fuera_de_servicio.sql`,
`cine/catalogo/fuera_de_servicio.py`, ampliación de `cine/mapa/apartado.py` (bloquear/
desbloquear), plantilla `admin_butacas`.

**Comprobación observable:**
1. Un cliente tiene apartadas 4, 5 y 6 sin pagar; se declara la 5 fuera de servicio. En el
   siguiente refresco del cliente, la 5 aparece **en conflicto** y la 4 y la 6 **siguen siendo
   suyas**; si intenta confirmar con la 5, falla nombrándola y el cobro queda revertido (CA-13).
2. Una butaca ya **vendida** declarada fuera de servicio no altera esa venta, y el administrador
   ve la lista de compras afectadas con su código y el correo del cliente.
3. Las filas de `ocupacion` de una función ya empezada o terminada son **idénticas** antes y
   después de declarar cualquier butaca fuera de servicio (CA-14, parte de datos).
4. Rehabilitar una butaca la vuelve a ofrecer solo en funciones que aún no han empezado.

**Evidencia (al cerrar la pieza):**
- [ ] Pruebas ejecutadas (comando y resultado):
- [ ] Comprobación observable realizada (pasos seguidos y resultado):
- [ ] Commit(s):
- [ ] Notas / desviaciones del plan:

---

## Pieza 7 — Programar la cartelera y editar los precios

**Estado:** Pendiente

**Recorrido:** el administrador carga la cartelera de la semana —películas con su duración y
clasificación, y las funciones de cada sala— y edita el precio base y la tarifa de estudiante.

**Requisitos que cubre:** RF-1, RF-2, RF-4, RN-1, RN-2, RN-5, RN-11, REG-7.

**Alcance:**
- Incluye: cálculo de la semana de cartelera (jueves a jueves, en hora local), carga de
  películas y funciones con rechazo de solapes en la misma sala, una función nueva nace ya con
  las butacas dañadas de su sala bloqueadas (RN-17), edición de precio base y tarifa de
  estudiante con su historial completo, pantallas de cartelera y de precios.
- No incluye: nada sobre cancelación (Pieza 10).
- Depende de: Pieza 5 (rol administrador) y Pieza 6 (butacas fuera de servicio, para que una
  función nueva nazca bloqueada donde corresponde).

**Componentes que toca:** `cine/catalogo/servicio.py`, ampliación de
`cine/tarifas/version.py`, plantillas `admin_cartelera`, `admin_precios`.

**Comprobación observable:**
1. Dos funciones que se solapan en la Sala 1 se rechazan nombrando el conflicto; sin solape se
   aceptan y aparecen en la cartelera del cliente, con fin = inicio + duración.
2. Una función fuera del rango jueves–miércoles cargado se rechaza.
3. Cambiado el precio base de X a Y: una compra nueva paga Y; la consulta por código de una
   compra hecha antes del cambio (Pieza 4) sigue mostrando X; el historial de precios muestra el
   monto anterior, el nuevo, quién lo cambió y cuándo (REG-7).

**Evidencia (al cerrar la pieza):**
- [ ] Pruebas ejecutadas (comando y resultado):
- [ ] Comprobación observable realizada (pasos seguidos y resultado):
- [ ] Commit(s):
- [ ] Notas / desviaciones del plan:

---

## Pieza 8 — La puerta: marcar ingresos y cobrar la diferencia

**Estado:** Pendiente

**Recorrido:** el taquillero busca la compra por su código, ve sus entradas, marca el ingreso de
cada una por separado y le cobra la diferencia a quien declaró ser estudiante y no trae carné.

**Requisitos que cubre:** RF-16, RF-17, RN-9, RN-10, RN-27, REG-3.

**Alcance:**
- Incluye: marcar el ingreso de una entrada (a lo sumo una vez, hecho cumplir por la base de
  datos), cobrar la diferencia hasta la tarifa general **vigente en la fecha en que se hizo la
  compra** (no la de hoy, por RN-11), pantalla de puerta.
- No incluye: nada sobre anulación (Pieza 9) ni cancelación (Pieza 10).
- Depende de: Pieza 3 (entradas y compras) y Pieza 5 (rol taquillero/administrador).

**Componentes que toca:** `cine/migraciones/00X_puerta.sql`, `cine/puerta/servicio.py`,
ampliación de `cine/ventas/consulta.py` (traer ingreso y diferencia), plantilla `puerta`.

**Comprobación observable:**
1. En una compra de tres entradas con una declarada estudiante: marcar el ingreso de la primera
   no toca las otras dos.
2. Marcar la misma entrada dos veces se rechaza diciendo **cuándo** ingresó y **quién** la marcó.
3. Cobrar la diferencia guarda exactamente tarifa general (la vigente cuando se compró) menos lo
   pagado, y esa diferencia queda registrada en la entrada.
4. La consulta por código (Pieza 4) muestra el ingreso y la diferencia cobrada.

**Evidencia (al cerrar la pieza):**
- [ ] Pruebas ejecutadas (comando y resultado):
- [ ] Comprobación observable realizada (pasos seguidos y resultado):
- [ ] Commit(s):
- [ ] Notas / desviaciones del plan:

---

## Pieza 9 — Anular una venta hecha por error

**Estado:** Pendiente

**Recorrido:** el taquillero anula, dentro de su plazo, una venta que él mismo hizo, anota el
motivo, y las butacas se liberan. Pasado el plazo, solo un administrador puede anularla.

**Requisitos que cubre:** RF-15, RN-24, RN-25, RN-26, REG-4, CA-9.

**Alcance:**
- Incluye: anular una compra (libera sus butacas, registra quién anuló, cuándo y por qué),
  reglas de quién puede anular y hasta cuándo (el taquillero solo lo suyo, dentro de su plazo; un
  administrador siempre), prohibición cuando alguna entrada ya ingresó, pantalla de anulación.
- No incluye: nada sobre cancelación de funciones (Pieza 10), que es un mecanismo distinto.
- Depende de: Pieza 5 (identidad de quien vendió, rol) y Pieza 8 (prohibición por ingreso).

**Componentes que toca:** `cine/migraciones/00X_anulacion.sql`, `cine/ventas/anulacion.py`,
ampliación de `cine/mapa/apartado.py` (liberar butacas de una compra), plantilla `anular`.

**Comprobación observable:**
1. Anulada una venta, sus butacas vuelven a aparecer disponibles en el mapa del cliente, y la
   consulta por código muestra «anulada» con quién anuló, cuándo y por qué.
2. Pasado el plazo del taquillero, este recibe negativa indicando que llame a un administrador;
   el administrador sí puede anularla.
3. Una compra de cuatro entradas con **una sola** ya ingresada no se puede anular, ni por el
   taquillero ni por el administrador, y el mensaje dice cuál entrada ya ingresó (CA-9).

**Evidencia (al cerrar la pieza):**
- [ ] Pruebas ejecutadas (comando y resultado):
- [ ] Comprobación observable realizada (pasos seguidos y resultado):
- [ ] Commit(s):
- [ ] Notas / desviaciones del plan:

---

## Pieza 10 — Cancelar una función y reembolsar todo

**Estado:** Pendiente

**Recorrido:** el administrador cancela una función con su motivo, incluso ya empezada, y con esa
sola acción el sistema reembolsa todas las compras vigentes, libera las butacas y manda los
avisos.

**Requisitos que cubre:** RF-18, RF-19, RN-18 a RN-23, REG-5, REG-6, CA-5, CA-7, CA-8.

**Alcance:**
- Incluye: cancelar una función como una sola transacción (marcar cancelada + liberar butacas +
  registrar un reembolso por cada compra vigente, con el monto exacto que se pagó), envío de
  avisos **fuera** de esa transacción (su falla nunca revierte la cancelación), la lista de
  reembolsos de una cancelación con el estado de cada aviso, pantalla de cancelación, las dos
  tareas programadas (reintento de avisos y barrido), ninguna crítica para la integridad.
- No incluye: nada sobre reportes (Pieza 11), que solo lee lo que esta pieza deja escrito.
- Depende de: Pieza 3 (monto pagado por compra), Pieza 5 (rol administrador), Pieza 8 (una
  compra con entradas ya ingresadas también se reembolsa).

**Componentes que toca:** `cine/migraciones/00X_cancelacion.sql`,
`cine/cancelaciones/servicio.py`, ampliación de `cine/mapa/apartado.py` (liberar toda una
función, respetando las bloqueadas), `cine/tareas.py`, plantilla `admin_cancelar`.

**Comprobación observable:**
1. Con 40 compras de una función de miércoles y el precio base subido **después** de venderlas:
   cancelar con **una sola acción** reembolsa las 40 por lo que cada una pagó a mitad de precio
   —no por el precio nuevo—, libera todas las butacas y genera 40 avisos (CA-5, CA-7).
2. Una compra con una entrada ya ingresada también queda reembolsada (CA-8); una función ya
   terminada no se puede cancelar; una compra ya anulada no recibe reembolso.
3. Con el servicio de correo caído, la cancelación queda completa igual —función cancelada,
   dinero registrado como devuelto—, los avisos quedan pendientes con su conteo de intentos, y
   la tarea de reintento los manda después sin revertir nada.

**Evidencia (al cerrar la pieza):**
- [ ] Pruebas ejecutadas (comando y resultado):
- [ ] Comprobación observable realizada (pasos seguidos y resultado):
- [ ] Commit(s):
- [ ] Notas / desviaciones del plan:

---

## Pieza 11 — Reportes de gestión y planillas descargables

**Estado:** Pendiente

**Recorrido:** el administrador escoge un período, consulta los reportes de gestión y descarga
las dos planillas que consumen la distribuidora y contabilidad.

**Requisitos que cubre:** RF-20 a RF-26, CA-11, CA-12, CA-14 (cierre), CA-16.

**Alcance:**
- Incluye: entradas y recaudación por película; recaudación por tarifa, canal y sala; ocupación
  por función (agrupable por día y horario); entradas sin ingreso de funciones ya terminadas, sin
  contar las canceladas; reembolsos registrados y su total; los índices que sostienen estas
  consultas al volumen de RNF-5; las dos planillas en formato abierto (`.xlsx`); pantalla de
  reportes con sus dos descargas.
- No incluye: ninguna escritura. Es solo lectura, separada lógicamente del flujo de venta.
- Depende de: todas las piezas anteriores, porque reporta sobre los datos que ellas producen.

**Componentes que toca:** `cine/migraciones/00X_indices_reportes.sql`,
`cine/reportes/consultas.py`, `cine/reportes/planillas.py`, plantilla `admin_reportes`.

**Decisión que este plan toma y que la especificación no cerró:** la diferencia cobrada en la
puerta por carné faltante (RN-9) no entra en la recaudación por película que ve la distribuidora,
pero sí aparece como línea propia en la planilla de contabilidad, para que ningún colón
registrado quede sin mostrarse en ningún reporte.

**Comprobación observable:**
1. Sobre un mes con compras vigentes, una anulada, una reembolsada y un cobro revertido: la
   anulada y la reembolsada **no aparecen** en la recaudación por película (CA-11); el cobro
   revertido no aparece **ni** en reembolsos **ni** en recaudación (CA-16).
2. Una función cancelada **no aporta** entradas al reporte de no presentados (CA-12).
3. La ocupación usa como denominador las butacas de la sala **menos** las bloqueadas de esa
   función, y declarar hoy una butaca fuera de servicio no cambia la ocupación reportada de una
   función ya pasada (CA-14, cierre).
4. Las dos planillas se descargan y se abren en una hoja de cálculo; la de la distribuidora
   lleva una fila por película.

**Evidencia (al cerrar la pieza):**
- [ ] Pruebas ejecutadas (comando y resultado):
- [ ] Comprobación observable realizada (pasos seguidos y resultado):
- [ ] Commit(s):
- [ ] Notas / desviaciones del plan:

---

# Cobertura de la especificación

Cada identificador de `ESPECIFICACION.md` mapeado a la pieza donde se construye y se comprueba.
Cuando un requisito se toca en más de una pieza (se declara en una y se comprueba en otra), se
listan todas.

## Requisitos funcionales (RF)

| RF | Pieza | RF | Pieza |
|---|---|---|---|
| RF-1 Cargar cartelera | 7 | RF-15 Anular venta | 9 |
| RF-2 Rechazar solapes | 7 | RF-16 Marcar ingresos | 8 |
| RF-3 Mostrar cartelera vigente | 1 | RF-17 Cobrar diferencia | 8 |
| RF-4 Editar precios con registro | 7 | RF-18 Cancelar y reembolsar | 10 |
| RF-5 Compra de invitado | 3 | RF-19 Lista de reembolsos | 10 |
| RF-6 Estado de cada butaca | 1 (lectura), 2 (escritura) | RF-20 Por película | 11 |
| RF-7 Apartado de 5 minutos | 2 | RF-21 Por tarifa, canal, sala | 11 |
| RF-8 Butaca solitaria | 2 | RF-22 Ocupación | 11 |
| RF-9 Límite de seis | 2 | RF-23 No presentados | 11 |
| RF-10 Desglose de precio | 3 | RF-24 Reembolsos | 11 |
| RF-11 Cobro simulado | 3 | RF-25 Netos de anuladas/reembolsadas | 11 |
| RF-12 Código y comprobante | 3 | RF-26 Planillas descargables | 11 |
| RF-13 Consulta por código | 4 | RF-27 Butacas no vendibles | 6 |
| RF-14 Taquilla, mismo mapa | 5 | RF-28 Tres clases de usuario | 5 (roles), 6/7/9/10/11 (aplicado) |

## Qué queda registrado (REG) y no funcionales (RNF)

| REG | Pieza | RNF | Pieza / nota |
|---|---|---|---|
| REG-1 Datos de la compra | 3 (creación), 5 (canal/vendedor), 9 (anulada), 10 (reembolsada) | RNF-1 Nunca vendida dos veces | 2 (mecanismo), 3 (transacción), 5 (entre canales) |
| REG-2 Cobro simulado | 3 | RNF-2 Compra confirmada no se pierde | 3 |
| REG-3 Ingreso y diferencia | 8 | RNF-3 Sin objetivo de disponibilidad | Declarado, ver nota abajo |
| REG-4 Anulación | 9 | RNF-4 20 a 50 personas a la vez | 2 |
| REG-5 Función cancelada | 10 | RNF-5 Volumen tope semanal | 11 (índices); ver nota abajo |
| REG-6 Reembolso | 10 | RNF-6 Usable en el teléfono | 1, 2 |
| REG-7 Historial de precios | 7 | | |

**Nota sobre RNF-3:** la especificación no fija un objetivo formal de disponibilidad; pide que una
interrupción breve no viole RNF-1 ni RNF-2. Ninguna pieza depende de un proceso en segundo plano
para su integridad (Piezas 2 y 10 lo declaran explícitamente), así que este requisito se cumple
por construcción y no tiene una comprobación propia que agregar.

**Nota sobre RNF-5:** el volumen tope (180 butacas por ronda, ~1000 entradas diarias, ~7000 por
semana) es un techo de escala, no un comportamiento funcional. La Pieza 11 agrega los índices que
lo sostienen sobre SQLite. Verificar el techo real exigiría una prueba de carga, que **queda
fuera del alcance de este plan de piezas funcionales** — se declara aquí en vez de dejarlo
implícito.

## Reglas de negocio (RN)

| RN | Pieza | RN | Pieza |
|---|---|---|---|
| RN-1 Cartelera jueves–miércoles | 7 | RN-15 Sin butacas solitarias | 2 |
| RN-2 Sin solapes | 7 | RN-16 Máximo seis entradas | 2 |
| RN-3 Cierre a la hora exacta | 1 (lectura), 2 (apartado) | RN-17 Fuera de servicio | 6 |
| RN-4 Cancelada fuera de reportes | 1 (cartelera), 11 (reportes) | RN-18 Cancelar mientras no termine | 10 |
| RN-5 Precio base único | 7 | RN-19 Reembolso total con una acción | 10 |
| RN-6 Mitad de precio miércoles | 3 | RN-20 Monto exacto, sin parciales | 10 |
| RN-7 Sin tarifa estudiante en miércoles | 3 | RN-21 Reembolso hecho al cancelar | 10 |
| RN-8 Tarifa de estudiante jueves–martes | 3 | RN-22 Reversión no es reembolso | 3 (mecanismo), 11 (reportes) |
| RN-9 Estudiante declarado y comprobado | 3 (declara), 8 (comprueba y cobra) | RN-23 Cancelada no cuenta no presentados | 11 |
| RN-10 Edad declarada y comprobada | 3 (declara), 8 (comprueba) | RN-24 Anular dentro del plazo propio | 9 |
| RN-11 Compra conserva su monto | 3, 7, 8, 10 (cada una lo respeta en su contexto) | RN-25 Anular libera y registra | 9 |
| RN-12 No vendible no se ofrece | 6 | RN-26 No se anula con ingreso | 9 |
| RN-13 Vendida una sola vez | 2 (mecanismo), 5 (entre canales) | RN-27 Ingreso por entrada | 8 |
| RN-14 Apartado, vencimiento, apoderamiento | 2 (creación/vencimiento), 3 (confirmación tras vencer) | | |

## Criterios de aceptación (CA)

| CA | Pieza | CA | Pieza |
|---|---|---|---|
| CA-1 Dos compras simultáneas | 2, 5 | CA-9 Con ingreso no se anula | 9 |
| CA-2 Solitaria que ya lo estaba | 2 | CA-10 Cierre a la hora exacta | 1 |
| CA-3 Aislar la primera de la fila | 2, 5 | CA-11 Anulada fuera del reporte | 11 |
| CA-4 Estudiante en miércoles | 3 | CA-12 Cancelada sin no presentados | 11 |
| CA-5 Reembolso por lo pagado | 10 | CA-13 Fuera de servicio con apartado | 6 |
| CA-6 Apartado que vence solo | 2 | CA-14 No altera reportes pasados | 6, 11 |
| CA-7 Cuarenta reembolsos, una acción | 10 | CA-15 Vencido pero no reclamado | 3, 6 |
| CA-8 Cancelar ya empezada | 10 | CA-16 Revertido fuera de los reportes | 3, 11 |

## Salidas que consume alguien más

| Salida | Pieza |
|---|---|
| Planilla mensual de la distribuidora | 11 |
| Planilla mensual de contabilidad | 11 |
| Comprobante de compra por correo | 3 |
| Aviso de cancelación con el monto reembolsado | 10 |

---

# Decisiones técnicas y de alcance

**Cerradas por este plan, además de las que ya cierra `DISENO.md`:**
- Longitud y alfabeto del código de confirmación: seis caracteres, sin los que se confunden al
  dictarlos por teléfono (I/1, O/0, S/5, B/8, Z/2).
- Zona horaria del cine (UTC−6, Costa Rica) para decidir si una función cae en miércoles: se
  calcula en hora local, no en UTC, porque una función que empieza a las 20:00 del miércoles cae
  después de medianoche en UTC.
- La diferencia cobrada en la puerta no entra en la recaudación por película, pero sí aparece
  como línea propia en la planilla de contabilidad (ver Pieza 11).

**Siguen abiertas, por decisión de quien opere el cine (ver también `DISENO.md` → «Decisiones
dejadas abiertas»):**
- Servicio real de envío de correo (hoy: buzón de archivos de desarrollo).
- Cadencia del reintento de avisos y del barrido de filas muertas.
- Claves reales del personal de arranque, antes de la puesta en marcha.
- Cómo se cargan los planos iniciales de las dos salas, si difieren de los sembrados en la
  Pieza 1.
