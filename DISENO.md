# Venta de entradas en línea — Cine Variedades — Diseño

Documento de diseño de la solución especificada en `ESPECIFICACION.md`. Todas las referencias
con forma `RN-n`, `RF-n`, `REG-n`, `RNF-n` y `CA-n` remiten a ese documento.

## Panorama de la arquitectura

Una sola aplicación web sobre una base de datos relacional. Tres audiencias entran por la misma
puerta y ven cosas distintas: el cliente compra desde el navegador de su teléfono, el taquillero
vende y atiende la puerta desde una computadora del cine, y el administrador programa la
cartelera, edita precios y consulta reportes. No hay programas que instalar ni aplicaciones que
publicar en tiendas.

Puertas adentro, el sistema se parte por responsabilidad y no por capa técnica: lo que cambia
junto vive junto. El centro de gravedad es el **Mapa de ocupación**, el único componente
autorizado a escribir en la tabla donde vive la restricción de unicidad que hace cumplir RNF-1.
Todo lo demás —la venta por internet, la venta en taquilla, la anulación, la cancelación de una
función, la puesta fuera de servicio de una butaca— le pide a él que aparte, confirme, bloquee o
libere. Esa frontera es lo que permite auditar el cumplimiento de RNF-1 mirando un solo
componente, en vez de rastrear cada camino que termina en una venta.

Las tres decisiones mayores se materializan en tres lugares concretos y aislados. La unicidad de
la butaca es una restricción declarada en la definición de la tabla, no una comprobación escrita
en el código. El vencimiento del apartado es una fecha guardada en la fila, que se evalúa en la
misma consulta que dibuja el mapa; apoderarse de un apartado vencido es una sola operación
indivisible. El refresco del mapa vive enteramente en la parte que corre en el teléfono, y su
falla degrada la experiencia sin tocar la integridad.

Vale la pena decir qué **no** hay, porque fue elegido: no hay cola de mensajes, no hay coordinador
de concurrencia y no hay conexiones permanentes. Hay dos tareas programadas —el barrido de filas
muertas y el reintento de avisos por correo— y **ninguna de las dos es necesaria para la
integridad del sistema**. Si el barrido no corre, las butacas se liberan igual por su fecha de
vencimiento. Si el reintento no corre, los correos se atrasan, pero ninguna venta, cancelación ni
reembolso queda comprometido ni a medias. Los reportes están separados lógicamente del flujo de
venta: no modifican su estado ni forman parte de sus transacciones, aunque compartan la misma
base de datos.

## Componentes

Once componentes agrupados por responsabilidad. Las dependencias van en una sola dirección:
**Ventas** y **Cancelaciones** orquestan; los demás no saben que existe nadie por encima de ellos.

```
Ventas ──────┬──> Catálogo        Cancelaciones ──┬──> Catálogo
             ├──> Reglas de selección              ├──> Mapa de ocupación
             ├──> Tarifas                          ├──> Ventas
             ├──> Mapa de ocupación                └──> Avisos
             ├──> Cobro simulado
             └──> Avisos          Puerta ──> Ventas

Reportes ──> (todos, solo lectura)      Acceso ──> (nadie)
```

### Mapa de ocupación

**Propósito**: ser la única fuente de verdad sobre qué butaca de qué función está disponible.

**Responsabilidades**:
- Devolver el estado de cada butaca de una función, resolviendo el vencimiento de los apartados
  dentro de la misma consulta.
- Apartar un conjunto de butacas para una sesión de compra, con su fecha de vencimiento.
- Convertir en venta las butacas que sigan siendo apartado de esa sesión.
- Bloquear butacas por puesta fuera de servicio (RN-17).
- Liberar butacas por anulación o por cancelación de función.
- Barrer filas muertas, como aseo.

**Límite con el resto**: es el único componente que escribe en la tabla de ocupación. Recibe
identificadores de función y butaca; no sabe de precios, de correos ni de quién es el cliente. Lo
que promete a quien lo consume: si responde que apartó, esas butacas son de esa sesión hasta que
venza el plazo; si responde conflicto, dice exactamente cuáles fallaron y por qué.

**Restricciones que lo gobiernan**, heredadas de las decisiones mayores aprobadas:
- La pareja función–butaca está declarada única en la base de datos.
- Apoderarse de un apartado vencido y crear el nuevo son una sola operación atómica. Queda
  prohibido el par borrar-luego-insertar, porque entre los dos pasos cabe una condición de
  carrera.
- Bloquear una butaca actualiza la fila que exista en vez de borrarla e insertar otra, de modo que
  la unicidad no se suelta ni por un instante.
- El barrido nunca es condición para que una butaca vuelva a estar disponible.

**Limitaciones**: apartar es todo o nada. Si una de las butacas pedidas falla, no queda ninguna
apartada, y es la interfaz del teléfono la que conserva la selección del cliente para que solo
tenga que cambiar la butaca en conflicto. Un apartado ya creado sí puede perder butacas, de dos
maneras y solo de esas dos: porque una de ellas se declaró fuera de servicio (RN-17), o porque
tras vencer su plazo otra sesión reclamó alguna (RN-14).

### Reglas de selección

**Propósito**: decidir si una selección de butacas es admisible, antes de intentar apartarla.

**Responsabilidades**: aplicar la regla de butaca solitaria (RN-15) y el límite de seis entradas
(RN-16), y cuando rechaza, señalar cuál butaca quedaría aislada.

**Límite con el resto**: cálculo puro. Recibe el plano de la sala con el estado de cada butaca y
la selección propuesta, y devuelve admisible o el motivo del rechazo. No consulta la base de
datos ni sabe qué es una compra. Vive en un solo lugar, y por eso rige igual para la web y para
la taquilla sin posibilidad de que una copia se desactualice.

**Limitaciones**: juzga contra el mapa que le entregan. No garantiza nada sobre el instante del
apartado; de eso se encarga el Mapa de ocupación.

### Tarifas

**Propósito**: calcular cuánto cuesta cada entrada y custodiar los parámetros de precio.

**Responsabilidades**:
- Calcular la tarifa aplicable según el día de la función y la condición declarada (RN-6 a RN-8).
  Este cálculo es una operación pura que recibe los parámetros vigentes y no guarda nada.
- Consultar la versión de tarifa vigente y registrar cada cambio de precio con su antes y su
  después (REG-7). Esta parte sí persiste, y es responsabilidad del componente, no del cálculo.

**Límite con el resto**: no conoce compras. El monto que devuelve el cálculo se copia dentro de
la entrada, y esa copia es la que manda para siempre (RN-11).

### Catálogo

**Propósito**: saber qué se exhibe, dónde y cuándo.

**Responsabilidades**: salas con su plano de filas y butacas, películas con su duración,
clasificación por edad y distribuidora, y funciones. Rechazar funciones solapadas en la misma
sala (RN-2) y decir si una función está a la venta (RN-3), si ya empezó y si ya terminó (RN-18).

**Límite con el resto**: no sabe que existen las compras. Lo consultan el Mapa de ocupación,
Ventas, Cancelaciones y Reportes.

### Cobro simulado

**Propósito**: aprobar o rechazar un cobro, dejar constancia y poder revertirlo.

**Responsabilidades**: registrar cada intento con su monto, su fecha, su identificador y su estado
—aprobado, rechazado o revertido— aunque la compra que iba a respaldar nunca llegue a existir
(REG-2, RF-11).

**Límite con el resto**: interfaz mínima —monto y referencia de la sesión— que devuelve el
resultado y el identificador del cobro. Está aislado a propósito: es el único punto que habría
que reemplazar el día que exista una pasarela real, y esa sustitución no debería tocar ningún
otro componente.

### Ventas

**Propósito**: llevar una compra de principio a fin y ser el dueño del registro de compras y
entradas.

**Responsabilidades**:
- Orquestar la compra: comprobar que la función esté a la venta, consultar Reglas de selección,
  pedir el apartado al Mapa, tarifar, cobrar, confirmar y generar el código.
- Generar códigos de confirmación irrepetibles.
- Anular ventas con sus plazos, motivos y prohibiciones (RN-24 a RN-26).
- Responder la consulta de una compra por su código (RF-13).

**Límite con el resto**: es el único que crea compras. No escribe en la tabla de ocupación —se lo
pide al Mapa— y no manda correos —se lo pide a Avisos—. Esa disciplina es lo que hace que taquilla
y web compartan reglas por construcción y no por convención.

### Cancelaciones

**Propósito**: cancelar una función y dejar registrada la devolución de todas sus compras.

**Responsabilidades**: comprobar que la función no haya terminado (RN-18), marcarla cancelada con
su motivo, pedirle al Mapa que libere todas sus butacas, marcar cada compra vigente como
reembolsada con su monto y su fecha (RN-19 a RN-21), y pedirle a Avisos que salgan los correos.

**Límite con el resto**: no toca la ocupación por su cuenta y no calcula montos: copia lo que cada
compra pagó.

**Garantía de atomicidad**: marcar la función como cancelada, liberar sus butacas y registrar los
reembolsos quedan consistentes como una misma operación de negocio. El envío de los correos no
forma parte de esa atomicidad: los avisos se solicitan después y, si fallan, se registran y se
reintentan sin revertir la cancelación.

### Puerta

**Propósito**: atender el ingreso a la sala.

**Responsabilidades**: localizar una compra por su código, mostrar sus entradas, marcar el ingreso
de cada una por separado (RN-27) y registrar la diferencia cobrada cuando falta el carné de
estudiante (RN-9).

**Límite con el resto**: anota sobre compras que ya existen; no crea ni anula ninguna. La
diferencia por carné faltante **también es un cobro simulado**: se registra el monto adicional y no
se procesa dinero real, igual que el resto de los pagos del alcance.

### Avisos

**Propósito**: mandar los correos y registrar si salieron.

**Responsabilidades**: comprobante de compra con su código (RF-12) y aviso de cancelación con el
monto reembolsado (RF-18), llevando registro del envío, su estado y sus intentos. Una tarea
programada reintenta los que fallaron.

**Límite con el resto**: no decide cuándo hay que avisar, se lo indican. Su falla nunca revierte
una venta ni una cancelación, y la tarea de reintento puede no correr sin comprometer la
integridad de ventas, cancelaciones ni reembolsos.

### Reportes

**Propósito**: contestar las preguntas de gestión y producir las planillas.

**Responsabilidades**: las consultas de RF-20 a RF-25 y la exportación de RF-26.

**Límite con el resto**: solo lectura. Separado lógicamente del flujo de venta: no modifica su
estado ni forma parte de sus transacciones.

### Acceso

**Propósito**: saber quién es quién y qué le está permitido.

**Responsabilidades**: identificar al taquillero y al administrador y aplicar las restricciones de
RF-28. El cliente no se identifica: compra como invitado (RF-5).

**Límite con el resto**: no conoce el dominio. Responde si una acción está permitida para quien la
pide, nada más.

## Modelo de datos

```
Sala ──< Butaca ──< Fuera de servicio        Película
  │         │                                   │
  └──< Función >────────────────────────────────┘
         │  │
         │  └──< Ocupación >── Butaca      (única: función + butaca)
         │                                  estados: bloqueada | apartada | vendida
         └──< Compra ──< Entrada ── Butaca
                 │           └── Ingreso   (0 ó 1 por entrada)
                 ├── Anulación             (0 ó 1)
                 ├── Reembolso             (0 ó 1)
                 └──< Aviso

Cobro simulado ──> Compra   (0 ó 1: el cobro existe primero y puede quedarse solo)
```

**Sala** — nombre y nada más. La capacidad no se guarda: se cuenta de sus butacas, para que 120 y
60 no puedan quedar desmentidos por el plano.

**Butaca** — sala, fila y número, con la combinación declarada única. No tiene atributo de
vendible. La vecindad que necesita la regla de butaca solitaria sale de aquí: butacas de la misma
sala y la misma fila con número contiguo.

**Fuera de servicio** — butaca, motivo, desde cuándo, hasta cuándo (vacío si es indefinido), quién
lo declaró y cuándo. Es el hecho durable de que una butaca está dañada, reservada o es de acceso
preferente. No decide disponibilidad por sí solo: sirve para que las funciones que se programen
después nazcan ya con esa butaca bloqueada.

**Función** — película, sala, inicio, fin, y su estado: programada o cancelada. Si se canceló,
guarda el motivo, quién la canceló, cuándo, y si la proyección ya había empezado en ese momento
(REG-5). El fin se calcula de la duración de la película, y es lo que permite rechazar solapes
(RN-2) y saber si una función ya terminó (RN-18). La cartelera semanal no es una tabla: es el
conjunto de funciones cuyo inicio cae entre un jueves y el miércoles siguiente.

**Ocupación** — la tabla central del diseño. Una fila por butaca no disponible de una función, con
la pareja **función–butaca declarada única**, y tres estados posibles: bloqueada, apartada o
vendida. Guarda la fecha de vencimiento cuando está apartada, el identificador de la sesión que la
apartó, y la compra cuando está vendida. Una butaca sin fila está libre. Una butaca cuya fila es un
apartado con fecha pasada cuenta como libre para los demás, y el siguiente comprador se apodera de
esa misma fila en una sola operación indivisible.

**Compra** — código de confirmación único, función, canal, quién la hizo si fue en taquilla, fecha
y hora, correo del cliente, monto total, referencia al cobro simulado que la respalda, y su
estado: vigente, anulada o reembolsada. Nace solo cuando el cobro se aprueba y la conversión de
sus butacas se completa: mientras el cliente escoge, lo único que existe es el apartado con su
identificador de sesión.

**Entrada** — una por butaca comprada. Guarda la butaca, la tarifa aplicada —general, estudiante o
miércoles—, el monto cobrado, si se declaró estudiante, y la diferencia que se le cobró en la
puerta por no presentar carné. El monto es una copia y no una referencia al precio vigente: por
eso cambiar el precio base no altera compras viejas ni sus reembolsos (RN-11).

**Cobro simulado** — la sesión que lo intentó, el monto, la fecha, su identificador y su estado:
aprobado, rechazado o revertido. **Es el único registro del flujo de compra que sobrevive a que la
compra no llegue a existir**, y esa es su razón de ser: permite registrar y revertir un cobro
aprobado aunque la transacción que iba a crear la compra no se complete (REG-2). Si la compra sí
se confirma, queda vinculada a su cobro aprobado.

**Ingreso** — a lo sumo uno **por entrada**: cuándo se marcó y quién lo marcó. Las entradas de una
misma compra pueden ingresar en momentos distintos, o algunas no ingresar nunca. Su ausencia es lo
que define un no presentado, que se cuenta por entrada y no por compra completa.

**Anulación** — a lo sumo una por compra: quién anuló, cuándo y el motivo (REG-4). Se rechaza si
alguna entrada de esa compra ya tiene ingreso (RN-26).

**Reembolso** — a lo sumo uno por compra: el monto devuelto, la fecha y la función cancelada que lo
originó (REG-6).

**Aviso** — un correo por enviar o enviado: a quién, de qué tipo, de qué compra, en qué estado y
cuántos intentos lleva. Vive aparte de la compra precisamente porque su falla no puede arrastrar a
la venta ni a la cancelación.

**Versión de tarifa** — precio base, tarifa de estudiante, desde cuándo rige y quién la fijó. Una
fila por cambio; la vigente es la versión aplicable más reciente. El conjunto de filas es el
historial que satisface REG-7.

**Parámetros de operación** — minutos de apartado, máximo de entradas por compra y minutos de la
ventana de anulación. Una sola fila editable, sin historial porque nadie lo pidió.

**Usuario** — taquilleros y administradores, con su rol. El cliente no aparece: compra como
invitado y su correo vive en la compra.

### Cómo se declara una butaca fuera de servicio

Al declararla, el sistema recorre las funciones de esa sala que todavía no han empezado y resuelve
cada butaca–función **actualizando la fila que exista**, sin borrarla en ningún momento:

| Estado de la butaca en esa función | Qué ocurre |
|---|---|
| Sin fila (libre) | Se inserta una fila bloqueada |
| Fila apartada, con o sin vencimiento cumplido | Se actualiza a bloqueada y se suelta su sesión. Las demás butacas de ese apartado no se tocan |
| Fila vendida | No se toca. La colisión con la restricción de unicidad **es** la lista de compras afectadas que RN-17 pide mostrarle al administrador |

Una fila bloqueada no puede convertirse en venta, porque la confirmación de una compra solo
convierte filas que sigan siendo apartado de esa sesión. Rehabilitar la butaca cierra el registro
con su fecha de fin y borra las filas bloqueadas de funciones que no hayan empezado; **las de
funciones pasadas nunca se tocan**, y por eso la ocupación reportada de semanas anteriores no
cambia (CA-14).

### Verificación contra «Qué queda registrado»

| Registro | Se contesta con |
|---|---|
| REG-1 — todo de la compra | Compra, más sus Entradas para butacas, tarifas y montos |
| REG-2 — cobro simulado, exista o no la compra | Cobro simulado |
| REG-3 — ingreso y diferencia, por entrada | Ingreso (una por entrada) y el campo de diferencia de Entrada |
| REG-4 — quién anuló, cuándo, por qué | Anulación |
| REG-5 — función cancelada, con motivo y si había empezado | Función |
| REG-6 — reembolso, monto, fecha, origen | Reembolso |
| REG-7 — historial de precios | Versión de tarifa |
| Entradas y recaudación por película | Entrada → Compra vigente → Función → Película |
| Desglose por tarifa | El campo de tarifa de cada Entrada |
| Ocupación de una función | Entradas vendidas contra las butacas de la sala menos las filas bloqueadas de esa función |
| Venta por canal | El canal de la Compra |
| No presentados | Entradas de compras vigentes cuya función terminó sin cancelarse y que no tienen Ingreso |
| Reembolsos y su monto | Reembolso, con la función que los originó |

## Flujo de una compra

El orden importa, porque define qué se puede deshacer y qué no.

1. Se comprueba que la función esté a la venta (RN-3).
2. **Reglas de selección** juzga la selección propuesta contra el mapa que el teléfono tiene a la
   vista. Si rechaza, no se toca nada.
3. **Mapa de ocupación** aparta las butacas, todo o nada, con vencimiento a 5 minutos.
4. **Tarifas** calcula el total con los parámetros vigentes.
5. Se verifica que las butacas sigan siendo de esa sesión, inmediatamente antes de cobrar. Esto no
   elimina la carrera; la reduce a una ventana muy angosta.
6. **Cobro simulado** aprueba o rechaza, y queda registrado en cualquier caso.
7. **Transacción única**: se convierten las butacas en vendidas, se crea la Compra con su código y
   se crean las Entradas. O ocurre todo, o no ocurre nada.
8. Fuera de la transacción, se le pide a **Avisos** el comprobante por correo.

El límite de la transacción está en el paso 7 a propósito: es el único punto donde el estado del
mapa y el registro de la venta tienen que quedar de acuerdo. Los pasos anteriores son reversibles
por vencimiento, y el posterior no puede arrastrar a nada.

## Manejo de errores

Tres principios gobiernan la sección: lo que puede pasar en un día normal es un resultado
esperado y se explica en los términos de quien lo provoca, no una falla; ninguna operación queda
hecha a medias; y ante cualquier duda se sacrifica la comodidad antes que RNF-1 o RNF-2.

| Situación | Qué ve quien la provoca | Qué queda registrado | Qué se revierte |
|---|---|---|---|
| Selección que aísla una butaca | Cuál butaca quedaría sola y por qué no se puede | Nada | Nada: se rechaza antes de apartar |
| Más de seis entradas | El límite y cuántas lleva | Nada | Nada |
| Función que ya empezó | Que la venta cerró, con la cartelera al día | Nada | Nada |
| Butaca tomada por otro al apartar | Cuáles fallaron, con el mapa fresco y su selección conservada | Nada | El apartado completo: no queda ninguna butaca tomada |
| Butaca bloqueada mientras la tenía apartada | La butaca marcada en conflicto y el aviso de escoger otra | La declaración de fuera de servicio | Solo esa butaca; las demás siguen apartadas |
| Apartado vencido y reclamado por otro | Que venció, con el mapa al día | Nada | Nada |
| Cobro simulado rechazado | El rechazo, con las butacas todavía apartadas para reintentar | El intento y su resultado | Nada: el apartado sigue vigente hasta su vencimiento |
| Código de confirmación inexistente | Que no existe, sin pistas sobre cuáles sí existen | Nada | Nada |
| Entrada que ya había ingresado | Cuándo ingresó y quién la marcó | Nada | Nada |
| Anulación fuera de plazo | Que su plazo venció y debe pedirle a un administrador | Nada | Nada |
| Anulación de compra con alguna entrada ingresada | Que no se puede, y cuál entrada ya ingresó | Nada | Nada |
| Cancelar una función ya terminada | Que no se puede cancelar lo que ya ocurrió | Nada | Nada |
| Correo que no sale | Nada: el cliente no está mirando | El aviso con su estado y sus intentos | Nada: ni la venta ni la cancelación se tocan |

Cuatro casos no se resuelven con un mensaje.

**El cobro se aprueba y la confirmación resulta imposible.** Es la carrera más delicada del
diseño: entre que el pago simulado se aprueba y que la compra se escribe, una butaca pudo quedar
bloqueada por una puesta fuera de servicio, o pudo ser reclamada por otra sesión tras vencer el
apartado. La compra, las entradas y la conversión del apartado en venta ocurren en una sola
transacción; si esa transacción no puede completarse, no queda compra. El cobro ya registrado se
marca entonces como **revertido** en la entidad Cobro simulado, que existe aparte de la compra
precisamente para poder sobrevivirla. Esa reversión no es un reembolso y no aparece en ningún
reporte de reembolsos ni en la recaudación: el reembolso, por definición, solo nace de una función
cancelada (RN-22, CA-16). Al cliente se le dice qué butaca se perdió y se le devuelve al mapa.

**El apartado venció durante el pago pero nadie reclamó las butacas.** La confirmación se acepta.
Vencer significa perder la exclusividad, no perder la butaca: mientras nadie más la haya
reclamado, la fila sigue siendo de esa sesión y confirmarla no compromete RNF-1. Rechazarla
castigaría al cliente por una demora que no perjudicó a nadie. Si en cambio otra sesión ya se
apoderó de alguna de las butacas, la confirmación falla entera —no se confirma ninguna— y se
aplica la reversión del caso anterior (RN-14, CA-15).

**Los correos de una cancelación fallan.** La cancelación de una función —marcarla cancelada,
liberar sus butacas y registrar sus reembolsos— es una sola operación consistente. Los avisos
quedan fuera de esa atomicidad: se registran como pendientes y los reintenta una tarea programada.
Si el servicio de correo está caído, la función sigue cancelada, el dinero sigue registrado como
devuelto y los avisos salen cuando el servicio vuelva. Ningún fallo de correo revierte una
cancelación ni una venta. El administrador ve en la lista de RF-19 cuáles avisos todavía no
salieron.

**El sistema se cae a mitad de una operación.** Todo lo que RNF-2 exige descansa en que las
operaciones que cambian estado sean transacciones: apartar, confirmar una compra, anular, cancelar
una función y declarar una butaca fuera de servicio. Al volver, o la operación está completa o es
como si nunca hubiera empezado. El único estado que puede quedar en el aire son las filas de
apartados que nadie confirmó, y esas se resuelven solas por su fecha de vencimiento, sin que nadie
tenga que intervenir. Esa es la razón de fondo por la que la Decisión 2 no depende de ningún
proceso en segundo plano.

## Decisiones mayores

### Cómo se garantiza que una butaca no se venda dos veces

**Por qué es una decisión mayor:** es el mecanismo que cumple RNF-1, el requisito que la
especificación declara innegociable. Cambia el comportamiento del sistema cuando 50 personas
pelean por la misma función (RNF-4) y qué ve el cliente que pierde la carrera.

| | A: Restricción de unicidad | B: Versión por función | C: Confirmaciones en fila |
|---|---|---|---|
| **Experiencia de uso** | Solo se estorban quienes piden la misma butaca | A un cliente le falla por culpa de butacas que no le interesaban | Correcta, con espera al confirmar |
| **Rendimiento** | Contención del tamaño del conflicto real | Se degrada justo en el pico: todos contra el mismo contador | Serializa lo que podría ser paralelo |
| **Recursos** | Ninguno adicional | Ninguno adicional | Exige un coordinador que no existe |
| **Complejidad** | Baja | Media: reintentos y su agotamiento | Alta |
| **Riesgo** | La garantía es invisible en el código: vive en la tabla | Los reintentos se apilan bajo carga | La garantía vive en memoria; muere con el proceso y no soporta una segunda instancia |

**Elección: opción A.** Es la única en que RNF-1 no depende de que el código se comporte bien, sino
de una restricción que el motor hace cumplir siempre y para los dos canales. Se mitiga su riesgo
documentando la restricción como la razón de ser de la tabla y cubriéndola con CA-1.

### Cómo se libera un apartado cuando vencen sus 5 minutos

**Por qué es una decisión mayor:** define si RN-14 se cumple con exactitud o solo aproximadamente,
y si el sistema necesita un proceso en segundo plano para ser correcto.

| | A: La fecha manda | B: Barrido programado | C: Temporizador en memoria |
|---|---|---|---|
| **Experiencia de uso** | Exacta al segundo | Imprecisa: bloqueada de más entre vencimiento y barrido | Exacta hasta el próximo reinicio |
| **Rendimiento** | Sin costo: se evalúa en la consulta que ya se hace | Recorre la tabla aunque no haya nada que liberar | Bueno a esta escala |
| **Recursos** | Ninguno indispensable | Programador de tareas, y hay que vigilarlo | Ninguno adicional |
| **Complejidad** | Baja, con un punto delicado bien localizado | Media, repartida en dos lugares | Baja de escribir, engañosa de operar |
| **Riesgo** | Si el paso atómico se implementa mal, se rompe RNF-1 | Si el barrido muere, las butacas quedan bloqueadas y nadie se entera | Al reiniciar se pierden los temporizadores y esas butacas quedan bloqueadas para siempre; choca con RNF-2 |

**Elección: opción A.** Es la única en la que la disponibilidad de una butaca es un hecho
verificable en los datos y no la consecuencia de que algo haya corrido a tiempo. Con dos
condiciones expresas: la sustitución de un apartado vencido por uno nuevo es una sola operación
atómica —queda prohibido borrar-luego-insertar—, y el barrido periódico es exclusivamente limpieza
de datos, nunca requisito para liberar una butaca. Se prueba con CA-6.

### Cómo se entera el teléfono de que el mapa cambió

**Por qué es una decisión mayor:** define cuántas veces le rechazan la selección al cliente, y es
la única de las tres que podría exigir infraestructura adicional.

| | A: Solo al abrir y al apartar | B: Refresco cada 10 segundos | C: Conexión permanente |
|---|---|---|---|
| **Experiencia de uso** | El cliente escoge sobre un mapa que envejece | Ve la sala llenarse; el rechazo pasa a ser raro | La mejor, por una diferencia de segundos que nadie percibe |
| **Rendimiento** | Una lectura por visita | 5 consultas por segundo en el pico: irrelevante | Menos tráfico, a cambio de 50 conexiones abiertas |
| **Recursos** | Ninguno | Ninguno | Sostener conexiones persistentes y su reconexión |
| **Complejidad** | La más baja | Baja | La más alta, concentrada en el teléfono |
| **Riesgo** | Rechazos encadenados hacen abandonar la compra | Si falla, se degrada exactamente hasta A | Una reconexión mal resuelta congela el mapa sin que el cliente lo note |

**Elección: opción B.** Compra la mejora justo en el escenario que RNF-4 describe, sin agregar
infraestructura, y su modo de falla es degradarse a la opción A sin comprometer la integridad de
las ventas. Con tres condiciones expresas:

- El refresco nunca deselecciona en silencio. Si una butaca ya escogida deja de estar disponible,
  se muestra claramente **en conflicto** y se le avisa al cliente que debe escoger otra.
- La validación definitiva al intentar apartar se mantiene igual, porque el mapa puede cambiar
  entre el último refresco y la operación.
- El refresco solo actualiza el estado de las butacas ajenas; no redibuja ni altera la selección
  del cliente.

### Lenguaje, marco de trabajo y motor de base de datos

**Por qué es una decisión mayor:** el diseño la había dejado abierta a propósito, pero condiciona
directamente cómo se implementan las tres decisiones anteriores. En particular, el paso atómico
de la Decisión mayor 2 —apoderarse de un apartado vencido sin borrar-luego-insertar— necesita que
el motor soporte una sentencia de inserción-o-actualización condicionada de una sola vuelta; no
todos los motores la ofrecen igual de limpia.

| | A: Python + FastAPI + SQLite | B: Node/TypeScript + PostgreSQL | C: Java + Spring Boot + PostgreSQL |
|---|---|---|---|
| **Ajuste al paso atómico** | `INSERT … ON CONFLICT DO UPDATE … WHERE …` en una sola sentencia, con `RETURNING` para saber si ganó | Mismo mecanismo disponible en PostgreSQL, con el mismo `RETURNING` | El mismo mecanismo existe, pero un ORM (JPA/Hibernate) tiende a partirlo en lectura-más-escritura si no se escribe la consulta nativa a mano |
| **Recursos operativos** | Un solo archivo, sin servidor de base de datos que administrar | Exige un servidor PostgreSQL aparte | Exige un servidor PostgreSQL aparte y una JVM |
| **Ajuste al volumen (RNF-4, RNF-5)** | Sobra holgadamente: miles de filas por semana, decenas de sesiones concurrentes | Sobra igual, con más capacidad de la que se necesita | Sobra igual |
| **Complejidad para exigir «sin ORM» en la escritura de ocupación** | Baja: `sqlite3` de la biblioteca estándar ejecuta SQL a la vista sin capas de por medio | Baja con un cliente SQL directo (`pg`), pero el ecosistema empuja hacia un ORM | Alta: hay que resistir el patrón habitual de Spring Data / JPA en el único punto donde no conviene |
| **Riesgo** | Un solo proceso de escritura; conviene documentarlo porque SQLite serializa escrituras por diseño, lo cual aquí es una ventaja y no una limitación a esta escala | Ninguno adicional | El riesgo real es de disciplina del equipo, no del motor |

**Elección: opción A — Python 3.11+, FastAPI con plantillas Jinja2, y SQLite en modo WAL sin
ORM.** SQLite cumple exactamente lo que el diseño exige del motor —restricciones de unicidad y
transacciones— y nada más que eso hace falta a la escala de RNF-5. Se prohíbe explícitamente un
ORM para el módulo que escribe en la tabla de ocupación: la garantía de RNF-1 tiene que verse en
el SQL a simple vista, no detrás de una capa que podría partir el paso atómico en dos. FastAPI y
Jinja2 se escogen porque el recorrido del cliente es navegación de páginas con formularios —no
hace falta una aplicación de una sola página— y porque Jinja2 sirve igual de bien las pantallas
del cliente, la taquilla y la administración sin introducir un segundo lenguaje en el navegador
más allá del refresco de 10 segundos de la Decisión mayor 3.

**Con dos condiciones expresas:**
- El módulo que escribe en la tabla de ocupación (`cine/mapa/`) usa SQL directo mediante la
  biblioteca estándar `sqlite3`; ningún ORM intermedia esa escritura.
- La conexión abre en modo WAL (`PRAGMA journal_mode = WAL`) y toda operación que cambia estado
  abre su transacción con `BEGIN IMMEDIATE`, para que dos escrituras concurrentes descubran el
  conflicto de una sola vez y no a medio camino.

## Otras decisiones

| Decisión | Opciones consideradas | Elección | Razón |
|---|---|---|---|
| Identidad del cliente mientras escoge | Crear la Compra en estado «en proceso» / identificador de sesión efímero | Identificador de sesión | Evita que toda consulta de ventas tenga que acordarse de excluir un estado intermedio (RF-20 a RF-25) |
| Forma del código de confirmación | Número correlativo / código alfanumérico corto | Alfanumérico corto | Se dicta por teléfono y se escribe a mano; un correlativo además delataría el volumen de ventas (RF-12) |
| Dónde vive la capacidad de la sala | Campo en Sala / contar sus butacas | Contarlas | Impide que el número y el plano se contradigan (RF-22) |
| Representación de la cartelera | Entidad propia / conjunto de funciones por fecha | Por fecha | RN-1 ya se expresa como un rango de fechas |
| Denominador de la ocupación | Butacas de la sala / butacas menos las bloqueadas de esa función | Menos las bloqueadas de esa función | Mantiene inmutables los reportes pasados (CA-14) |
| Historial de los parámetros de operación | Con historial / sin historial | Sin historial | Nadie pidió auditar cambios de plazos; de los precios sí (REG-7) |
| Cuándo se aplican las reglas de selección | Solo al apartar / al seleccionar y al apartar | Ambas | La primera explica; la segunda es la que manda (RF-8) |
| Formato de las planillas | Formato propietario / formato abierto de planilla | Abierto | Contabilidad y la distribuidora las abren en su hoja de cálculo (RF-26) |
| Alcance del refresco del mapa | Redibujar todo / actualizar solo el estado de las butacas | Solo el estado | El refresco no puede tocar la selección del cliente |
| Reintento de avisos | En el mismo hilo de la operación / tarea aparte | Tarea aparte | Su falla no puede arrastrar la venta ni la cancelación |
| Cuentas del personal | Una por rol, compartida / una por persona | Una por persona | REG-4 y REG-5 exigen saber quién anuló y quién canceló |

## Decisiones dejadas abiertas

| Qué no se decidió | Quién lo decide y cuándo |
|---|---|
| ~~Lenguaje, marco de trabajo y motor de base de datos~~ | **Decidido**: Python + FastAPI + SQLite. Ver «Decisiones mayores → Lenguaje, marco de trabajo y motor de base de datos» |
| Nivel de aislamiento de las transacciones y forma exacta de la operación atómica de apartado | Ya acotado por la decisión anterior a `BEGIN IMMEDIATE` y `INSERT … ON CONFLICT DO UPDATE … WHERE … RETURNING`; la redacción exacta de esa sentencia queda para el plan de construcción, con CA-1 y CA-6 como prueba |
| Longitud y alfabeto del código de confirmación | Quien implemente, con el criterio de que se pueda dictar por teléfono sin ambigüedad |
| Servicio concreto de envío de correo | El cine, al contratarlo. El componente Avisos ya lo tiene aislado |
| Cadencia del reintento de avisos y cuántos intentos antes de rendirse | Quien implemente, al ponerlo en operación |
| Disposición visual del mapa en pantallas angostas | Quien haga la interfaz, contra RNF-6 |
| Cómo se cargan los planos iniciales de las dos salas | El cine y quien implemente, antes de la puesta en marcha |
