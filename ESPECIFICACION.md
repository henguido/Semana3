# Especificación: Venta de entradas en línea — Cine Variedades

## Resumen

Sistema de venta de entradas para Cine Variedades que permite comprar por internet y escoger
butaca desde el teléfono, sobre el mismo mapa de asientos que usa la taquilla. Reemplaza el
control manual con mapas impresos, que hoy impide vender fuera del cine y obliga a llevar la
ocupación a mano.

## Glosario

| Término | Definición |
|---|---|
| Sala | Recinto físico con butacas numeradas. El cine tiene dos: Sala 1 con 120 butacas y Sala 2 con 60. |
| Butaca | Asiento físico de una sala, identificado por fila y número (ej. `F-12`). Existe con independencia de las funciones. |
| Butaca no vendible | Butaca que no se ofrece a la venta porque el cine la declaró fuera de servicio: dañada, de acceso preferente o reservada. «Fuera de servicio» es el acto de declararla; «no vendible» es el estado en que queda. Aparece en el mapa marcada como tal. |
| Cartelera | Conjunto de películas y funciones de una semana. Va de jueves a miércoles y se reemplaza completa cada jueves. |
| Función | Proyección concreta de una película en una sala, en una fecha y hora. Es lo que se vende. |
| Entrada | Derecho de una persona a ocupar una butaca en una función. Se descarta el término «boleto», que aparece en el encargo original. |
| Compra | Operación que produce una o varias entradas de la misma función, pagadas juntas. Es la unidad que se anula, se consulta y se reembolsa. |
| Apartado | Bloqueo temporal de las butacas escogidas mientras el cliente termina de pagar. Se descarta el término «reserva», que sugiere pagar después. |
| Código de confirmación | Código corto que identifica una compra. Es lo que el cliente muestra en la puerta y lo que usa para consultar su compra. |
| Canal | Vía por la que se hizo una compra: web o taquilla. |
| Precio base | Monto de una entrada general. Es un parámetro que edita el administrador; no hay ningún monto fijo en el sistema. |
| Tarifa | Precio que se le cobra a una entrada según el día y la condición declarada: general, estudiante o miércoles. |
| Reembolso | Devolución del dinero pagado por una compra cuando el cine cancela la función. Como el cobro es simulado, la devolución también lo es: el sistema registra el monto devuelto y la deja hecha, sin transacción bancaria (RN-21). |
| Anulación | Deshacer una venta hecha por error del personal. Es distinta del reembolso: nace de una equivocación, no de una cancelación. |
| Ingreso | Registro de que la persona de una entrada se presentó en la puerta y entró a la sala. Se marca por entrada, no por compra. |
| No presentado | Entrada vendida cuya función se realizó y terminó sin que se haya registrado el ingreso. |
| Butaca solitaria | Butaca disponible que queda aislada porque sus vecinas inmediatas de la misma fila no lo están. Definición precisa en RN-15. |
| Administrador | Persona que programa la cartelera, edita precios, cancela funciones, consulta reportes y anula ventas antiguas. |
| Taquillero | Persona que vende en taquilla y marca los ingresos en la puerta. |

## Objetivos

- Vender entradas por internet, con selección de butaca desde el teléfono.
- Mantener un único mapa de ocupación por función, compartido entre web y taquilla, de modo que
  una butaca vendida por un canal deje de estar disponible en el otro de inmediato.
- Reemplazar el control manual en papel por el registro del sistema.
- Cobrar automáticamente la tarifa correcta según el día y la condición declarada.
- Permitir cancelar una función y dejar registrada la devolución a todos los afectados con una
  sola acción.
- Producir el reporte mensual de entradas vendidas por película, y las demás consultas de
  gestión que hoy no se pueden contestar.

## Fuera de alcance

- Transacciones bancarias, tanto al cobrar como al devolver. El pago se simula: el sistema pide
  un medio de pago, lo da por aprobado o rechazado y registra el resultado. La devolución se
  simula igual: se registra el monto devuelto y ahí termina (RN-21).
- Vales, créditos y cambios de función. La única compensación prevista es el reembolso del monto
  pagado.
- Boletos impresos, códigos de barras y códigos QR.
- Más de una semana de cartelera a la vez. La cartelera vigente reemplaza a la anterior.
- Cuentas de cliente, contraseñas e historial de compras. La compra es de invitado (RF-5).
- Venta de confitería, promociones, paquetes y programas de fidelidad.
- Precios distintos por sala, por horario o por fin de semana. El precio base es único (RN-5).
- Numeración o asignación automática de butacas: el cliente siempre escoge.
- Reubicación automática de clientes cuando una butaca vendida se daña (RN-17).
- Control de acceso a la sala por medios electrónicos. La puerta se atiende con una persona.

## Reglas del negocio

**Cartelera y funciones**

1. RN-1: La cartelera va de jueves a miércoles. Cada jueves entra una cartelera nueva que
   reemplaza a la anterior.
2. RN-2: Una función pertenece a una sola sala y ocupa esa sala desde su hora de inicio hasta su
   hora de fin. Dos funciones de la misma sala no pueden solaparse en el tiempo.
3. RN-3: Una función deja de estar a la venta exactamente a su hora de inicio, en los dos
   canales. Después de esa hora no se vende una entrada más para ella.
4. RN-4: Una función cancelada no admite ventas nuevas y no cuenta como vendida en los reportes
   de recaudación.

**Precios**

5. RN-5: Cada película de la cartelera se vende al precio base del cine, que es único para las
   dos salas y todos los horarios. El precio base y la tarifa de estudiante son parámetros que
   edita el administrador; el sistema no fija ningún monto.
6. RN-6: Las funciones de miércoles se cobran a mitad del precio base, a todo el mundo.
7. RN-7: El miércoles no existe la tarifa de estudiante. Ese día hay una sola tarifa y es la
   mitad del precio base.
8. RN-8: De jueves a martes, quien declara ser estudiante paga la tarifa de estudiante. Las
   tarifas nunca se acumulan: a una entrada se le aplica una sola.
9. RN-9: La condición de estudiante se declara al comprar y se comprueba en la puerta. Quien no
   presenta carné vigente paga ahí la diferencia hasta la tarifa general, y esa diferencia queda
   registrada en la entrada que la generó. Ese cobro también es simulado: se registra el monto,
   no se procesa dinero real.
10. RN-10: La clasificación por edad de una película se declara al comprar y se comprueba en la
    puerta. Quien no cumple la edad no entra y pierde la entrada, sin reembolso.
11. RN-11: Cada compra conserva el monto que se le cobró. Cambiar el precio base o la tarifa de
    estudiante afecta únicamente a las ventas posteriores al cambio, y nunca al monto que se
    reembolsa por una compra anterior.

**Butacas y apartado**

12. RN-12: Una butaca no vendible no se ofrece a la venta, aunque la sala esté llena.
13. RN-13: Una butaca solo puede estar vendida una vez por función. Esto vale aunque las dos
    compras ocurran al mismo tiempo y por canales distintos.
14. RN-14: Al escoger butacas, estas quedan apartadas para esa compra durante 5 minutos. Vencido
    el plazo sin pago aprobado, se liberan solas y vuelven a estar disponibles. Un apartado
    vigente bloquea la butaca en los dos canales. El plazo es un parámetro editable.

    Vencer significa perder la exclusividad, no perder la butaca. Mientras nadie más la haya
    reclamado, la butaca sigue asignada a esa sesión y su compra se puede confirmar aunque los
    5 minutos ya hayan pasado. Si otra sesión se apoderó de alguna de esas butacas, la
    confirmación falla entera —no se confirma ninguna— y el cobro simulado que se hubiera
    aprobado queda marcado como revertido.
15. RN-15: Una compra no puede crear butacas solitarias. Una butaca queda solitaria cuando está
    disponible y todas sus vecinas inmediatas de la misma fila no lo están —vendidas, apartadas,
    no vendibles o escogidas en esa misma compra—. Las butacas de los extremos de fila tienen
    una sola vecina inmediata. La regla se evalúa solo contra los huecos que la propia compra
    crea: una butaca que ya estaba solitaria antes de empezar sí se puede vender, y venderla
    nunca infringe la regla. La regla rige igual en los dos canales y nadie puede saltársela, ni
    el taquillero ni el administrador.
16. RN-16: Una compra no puede tener más de 6 entradas. El límite se aplica por compra; en
    taquilla, además, el taquillero lo aplica a la persona que tiene enfrente. El límite es un
    parámetro editable.
17. RN-17: Declarar una butaca fuera de servicio rige de ahí en adelante y nunca hacia atrás. Las
    funciones que ya empezaron o terminaron no se tocan. Sobre cada función que todavía no ha
    empezado, el efecto depende de cómo esté esa butaca:
    - **Libre:** queda bloqueada y deja de ofrecerse.
    - **Apartada y sin pagar:** el apartado pierde esa butaca, que queda bloqueada. El cliente se
      entera en el siguiente refresco del mapa o, a más tardar, al intentar continuar. Las demás
      butacas de ese mismo apartado no se ven afectadas y siguen siendo suyas hasta su
      vencimiento.
    - **Vendida:** la venta no se modifica. El sistema le muestra al administrador la lista de
      esas compras para que las resuelva con el cliente en la puerta.

    Una butaca bloqueada no puede convertirse en venta mientras siga fuera de servicio.
    Rehabilitarla la vuelve a ofrecer únicamente en funciones que aún no han empezado.

**Cancelación y reembolso**

18. RN-18: Una función se puede cancelar mientras no haya terminado, incluso con la proyección
    ya empezada y la sala llena. Una función que ya terminó no se cancela.
19. RN-19: Cancelar una función reembolsa todas sus compras vigentes y libera todas sus butacas,
    con una sola acción y sin revisar compra por compra. El reembolso alcanza también a las
    compras con entradas ya ingresadas, porque quien entró y se quedó sin película también tiene
    derecho a su dinero.
20. RN-20: El monto reembolsado de una compra es exactamente lo que se pagó por ella. No hay
    reembolsos parciales ni por butaca suelta: la compra se reembolsa entera o no se reembolsa.
21. RN-21: El reembolso queda hecho en el momento de la cancelación. El sistema registra el monto
    devuelto, la fecha y la función que lo originó, y la compra pasa a estado reembolsada. Como
    el cobro es simulado, la devolución también lo es: no hay transacción bancaria ni entrega de
    efectivo.
22. RN-22: El cliente no puede cancelar su compra ni pedir dinero de vuelta por su cuenta. La
    venta es final. El reembolso existe únicamente cuando el cine cancela la función. Quien no
    llega pierde la entrada y su butaca queda vacía. Revertir un cobro cuya compra nunca llegó a
    existir (RN-14) no es un reembolso y no cuenta como tal en ningún reporte.
23. RN-23: Las entradas de una función cancelada no cuentan como no presentadas, aunque nadie
    haya marcado el ingreso.

**Anulación por error**

24. RN-24: El taquillero puede anular una venta que él mismo hizo, dentro de los 5 minutos
    siguientes a haberla hecho. Pasado ese plazo, solo un administrador puede anularla. El plazo
    es un parámetro editable.
25. RN-25: Anular una venta libera sus butacas y deja registrado quién anuló, cuándo y por qué.
    Una venta anulada no cuenta en ningún reporte de ventas ni de recaudación.
26. RN-26: Una venta con al menos una de sus entradas ya ingresada no se puede anular. Sí se
    puede reembolsar, si su función se cancela (RN-19).

**Puerta**

27. RN-27: El ingreso se marca por entrada, no por compra. El taquillero localiza la compra por
    su código de confirmación, ve sus entradas y marca cuáles ingresaron. Una entrada no se
    puede marcar dos veces, y las entradas de una misma compra pueden ingresar en momentos
    distintos.

## Qué queda registrado

1. REG-1: De cada compra: canal, quién la hizo (el taquillero, o «web»), fecha y hora, función,
   butacas, tarifa aplicada a cada entrada, monto cobrado, correo del cliente, código de
   confirmación, el cobro simulado que la respalda y estado actual (vigente, anulada o
   reembolsada).
2. REG-2: De cada cobro simulado, exista o no la compra que iba a respaldar: la sesión que lo
   intentó, el monto, la fecha, su identificador y su estado (aprobado, rechazado o revertido).
3. REG-3: De cada entrada en la puerta: si se marcó el ingreso, cuándo y quién lo marcó, y la
   diferencia cobrada por carné de estudiante no presentado.
4. REG-4: De cada anulación: quién anuló, cuándo y el motivo.
5. REG-5: De cada función cancelada: quién la canceló, cuándo, el motivo, y si ya había empezado.
6. REG-6: De cada reembolso: la compra que lo origina, el monto devuelto, la fecha, la
   cancelación que lo provocó y si el aviso por correo salió.
7. REG-7: De cada cambio de precio base o de tarifa de estudiante: el monto anterior, el nuevo,
   quién lo cambió y cuándo.

Con eso se pueden contestar, sobre cualquier período:

- Cuántas entradas vendió cada película y cuánto se recaudó por película, por sala y por mes.
- Cuánto de esa recaudación se cobró a tarifa general, a tarifa de estudiante y a tarifa de
  miércoles.
- Qué porcentaje de butacas se ocupó en cada función, y cómo se comporta eso por horario y por
  día de la semana.
- Cuánto se vendió por internet y cuánto en taquilla.
- Cuántas entradas vendidas no se presentaron en la puerta.
- Cuántas compras se reembolsaron por funciones canceladas y cuánto dinero representaron.

## Salidas que consume alguien más

| Quién | Qué recibe | Formato | Frecuencia |
|---|---|---|---|
| Distribuidora de películas | Una fila por película del mes: entradas vendidas y recaudación, ya netas de anulaciones y reembolsos | Archivo de planilla descargable | Mensual |
| Contabilidad interna | Ingresos del mes desglosados por tarifa, por canal y por sala, y el total reembolsado | Archivo de planilla descargable | Mensual |
| Cliente que compró | Comprobante con el código de confirmación, la función y las butacas | Correo electrónico | Al confirmarse cada compra |
| Cliente afectado | Aviso de función cancelada, con el monto que se le reembolsó | Correo electrónico | Al cancelarse una función |

## Recorridos

**Compra en línea que termina bien**

1. El cliente abre la cartelera de la semana y escoge una función que todavía no ha empezado.
2. Ve el mapa de la sala con las butacas disponibles, las vendidas, las apartadas por otros y
   las no vendibles.
3. Escoge sus butacas. El sistema comprueba el límite de 6 (RN-16) y la regla de butaca solitaria
   (RN-15), y las aparta por 5 minutos (RN-14).
4. Declara, por cada entrada, si es de estudiante. El sistema calcula el precio según el día
   (RN-6 a RN-8) y muestra el total.
5. Si la película tiene restricción de edad, confirma que la cumple (RN-10).
6. Da su correo.
7. Paga. El pago simulado se aprueba.
8. El sistema confirma la compra, convierte el apartado en venta, genera el código de
   confirmación, lo muestra en pantalla y lo manda por correo.

**El apartado vence antes de pagar**

En el paso 7, el cliente se demora más de 5 minutos. El sistema libera las butacas, le avisa que
el apartado venció y lo devuelve al mapa, ya actualizado. No se cobra nada.

**Alguien más se lleva la butaca**

Entre los pasos 2 y 3, un taquillero vende una de esas butacas. El sistema no aparta esa butaca,
le indica al cliente cuál se ocupó y le muestra el mapa actualizado para que vuelva a escoger.

**El pago se rechaza**

En el paso 7, el pago simulado se rechaza. El sistema lo informa y mantiene el apartado hasta que
venzan los 5 minutos, para que pueda reintentar sin perder las butacas.

**La función se cancela**

1. Un administrador marca la función como cancelada y anota el motivo —el proyector se dañó, por
   ejemplo—. Puede hacerlo aunque la proyección ya haya empezado (RN-18).
2. El sistema libera todas las butacas y reembolsa cada compra vigente por el monto que pagó,
   incluidas las de quienes ya habían entrado a la sala (RN-19, RN-20).
3. Cada reembolso queda registrado con su monto y su fecha, y sale un correo al cliente
   indicándole cuánto se le devolvió (RN-21).
4. La función desaparece de la cartelera a la venta y sus entradas dejan de contar como no
   presentadas (RN-23).

**En la puerta, sin carné de estudiante**

El taquillero busca el código, ve que hay entradas declaradas como de estudiante y pide los
carnés. Falta uno: cobra la diferencia hasta la tarifa general, la registra en esa entrada y le
marca el ingreso. Las demás entradas de la compra se marcan cuando entren sus personas, que
pueden llegar en otro momento.

**En la puerta, sin cumplir la edad**

El taquillero comprueba que la persona no cumple la edad de la película. No la deja entrar, no le
marca el ingreso a su entrada y no se emite reembolso (RN-10). Las demás entradas de la misma
compra sí pueden ingresar.

**El taquillero se equivocó**

Vendió la butaca equivocada. Dentro de sus 5 minutos (RN-24) anula la venta, anota el motivo, las
butacas se liberan y vuelve a vender bien. Si ya pasó el plazo, llama a un administrador. Si la
compra ya tiene alguna entrada ingresada, no se puede anular (RN-26).

**Se daña una butaca**

El administrador la declara fuera de servicio. En las funciones que no han empezado, la butaca
queda bloqueada si estaba libre; si alguien la tenía apartada sin pagar, el apartado la pierde y
esa persona lo descubre en el siguiente refresco del mapa, conservando las demás butacas que
había escogido; y si ya estaba vendida, esa venta no se toca. El sistema le muestra al
administrador la lista de compras futuras que incluyen esa butaca, con su código y el correo del
cliente, para que el cine las resuelva en la puerta (RN-17).

## Requisitos funcionales

**Cartelera y precios**

1. RF-1: Un administrador puede cargar la cartelera de la semana: qué películas se exhiben, con
   su duración y su clasificación por edad, y qué funciones tiene cada una en cada sala.
2. RF-2: El sistema rechaza programar dos funciones solapadas en la misma sala (RN-2).
3. RF-3: El sistema muestra la cartelera vigente con las funciones que todavía no han empezado.
4. RF-4: Un administrador puede editar el precio base y la tarifa de estudiante, y el sistema
   deja registro del cambio (RN-5, REG-7).

**Compra**

5. RF-5: El cliente compra sin crear cuenta. Da su correo y queda identificado por el código de
   confirmación de la compra.
6. RF-6: El sistema muestra, para una función, el estado de cada butaca de la sala: disponible,
   vendida, apartada o no vendible.
7. RF-7: El sistema aparta las butacas escogidas por 5 minutos y las libera solo al vencer
   (RN-14).
8. RF-8: El sistema impide una selección que cree butacas solitarias, y le indica al cliente cuál
   butaca quedaría aislada (RN-15).
9. RF-9: El sistema impide una compra de más de 6 entradas (RN-16).
10. RF-10: El sistema calcula el precio de cada entrada según el día de la función y la condición
    declarada, y muestra el desglose antes de cobrar.
11. RF-11: El sistema simula el cobro y registra su resultado —aprobado, rechazado o revertido—
    aunque la compra no llegue a existir. Solo confirma la compra si el cobro se aprobó y todas
    sus butacas siguen siendo suyas (RN-14).
12. RF-12: Al confirmar una compra, el sistema genera un código de confirmación irrepetible, lo
    muestra y lo manda por correo.
13. RF-13: El cliente puede consultar su compra escribiendo su código de confirmación, y ver su
    función, butacas, monto y estado, incluido el monto reembolsado si su función se canceló.

**Taquilla y puerta**

14. RF-14: El taquillero vende con el mismo mapa y las mismas reglas que la web, sobre las mismas
    funciones.
15. RF-15: El taquillero puede anular una venta propia dentro de sus 5 minutos; pasado el plazo,
    solo un administrador (RN-24, RN-25, RN-26).
16. RF-16: El taquillero busca una compra por su código, ve sus entradas y marca el ingreso de
    cada una por separado. Una entrada solo se puede marcar una vez (RN-27).
17. RF-17: El taquillero registra la diferencia cobrada cuando un estudiante declarado no
    presenta carné (RN-9).

**Cancelación y reembolso**

18. RF-18: Un administrador cancela una función indicando el motivo, incluso si ya empezó. El
    sistema reembolsa todas las compras vigentes, libera las butacas y manda los avisos, sin
    intervención por compra (RN-18, RN-19, RN-21).
19. RF-19: El sistema muestra la lista de reembolsos de una cancelación, con su monto y si el
    aviso al cliente salió, para que el cine pueda cuadrar cuánto dinero devolvió esa
    cancelación.

**Reportes**

20. RF-20: El sistema produce, para un mes, las entradas vendidas y la recaudación por película.
21. RF-21: El sistema produce, para un período, la recaudación desglosada por tarifa, por canal y
    por sala.
22. RF-22: El sistema produce, para un período, la ocupación de cada función en porcentaje de
    butacas vendidas, agrupable por día de la semana y por horario.
23. RF-23: El sistema produce, para un período, las entradas vendidas que no registraron ingreso,
    excluyendo las de funciones canceladas (RN-23).
24. RF-24: El sistema produce, para un período, los reembolsos registrados y su monto total.
25. RF-25: Todos los reportes de ventas y recaudación descuentan las compras anuladas y
    reembolsadas (RN-4, RN-25).
26. RF-26: Los reportes de la distribuidora y de contabilidad se pueden descargar como archivo de
    planilla. El de la distribuidora lleva una fila por película, con entradas vendidas y
    recaudación neta.

**Administración**

27. RF-27: Un administrador puede marcar y desmarcar butacas como no vendibles en cada sala, y al
    marcarlas ve las compras futuras que las incluyen (RN-17).
28. RF-28: El sistema distingue tres clases de usuario —cliente, taquillero y administrador— y
    solo el administrador puede cargar cartelera, editar precios, cancelar funciones, ver
    reportes y anular ventas fuera del plazo del taquillero.

## Requisitos no funcionales

1. RNF-1: Una butaca de una función no puede quedar vendida dos veces bajo ninguna circunstancia,
   ni siquiera con dos compras simultáneas por canales distintos. Esta es la restricción más
   importante del sistema y ninguna otra la subordina.
2. RNF-2: Una compra confirmada no se pierde. Si el sistema se interrumpe justo después de
   confirmarla, al volver tiene que seguir ahí.
3. RNF-3: No se fija un objetivo formal de disponibilidad. Una interrupción breve es tolerable
   siempre que no viole RNF-1 ni RNF-2.
4. RNF-4: El sistema tiene que sostener de 20 a 50 personas escogiendo butaca al mismo tiempo
   —el pico de un estreno el jueves de cambio de cartelera— sin que se degrade RNF-1.
5. RNF-5: El volumen tope conocido es de 180 butacas por ronda de funciones. Con varias funciones
   por día, el sistema no supera unas mil entradas diarias ni unas siete mil por semana de
   cartelera.
6. RNF-6: El mapa de butacas tiene que ser usable en la pantalla de un teléfono, que es donde el
   cliente escoge.

## Criterios de aceptación

| ID | Criterio | Requisito asociado |
|---|---|---|
| CA-1 | Dos compras que piden la misma butaca al mismo tiempo: una se confirma y la otra recibe el aviso de butaca ocupada. Nunca se confirman las dos. | RNF-1, RN-13 |
| CA-2 | Fila con butacas 1 a 10 y las butacas 1 y 3 ya vendidas: escoger la 4 y la 5 se acepta, aunque la butaca 2 quede solitaria, porque ya lo estaba antes de esta compra. En la misma fila, escoger la 5 y la 7 se rechaza, porque la 6 queda solitaria y no lo estaba. | RN-15, RF-8 |
| CA-3 | Fila con butacas 1 a 10, todas libres: escoger la 2 se rechaza porque aislaría la 1. Escoger la 1 y la 2 se acepta. Lo mismo ocurre si quien vende es el taquillero. | RN-15, RF-8 |
| CA-4 | Un estudiante compra para un miércoles y paga la mitad del precio base, ni un centavo menos. | RN-6, RN-7 |
| CA-5 | Se cancela una función de miércoles: cada compra se reembolsa por lo que efectivamente pagó a mitad de precio, no por el precio base. Si el precio base subió después de esa venta, el reembolso sigue siendo el monto original. | RN-11, RN-20 |
| CA-6 | Se aparta una butaca y no se paga: a los 5 minutos vuelve a aparecer disponible sin que nadie intervenga. | RN-14, RF-7 |
| CA-7 | Se cancela una función con 40 compras: las 40 quedan reembolsadas con su monto registrado, se liberan todas las butacas y salen 40 correos, con una sola acción del administrador. | RN-19, RF-18 |
| CA-8 | Se cancela una función a los diez minutos de empezada: las compras con entradas ya ingresadas también quedan reembolsadas. | RN-18, RN-19 |
| CA-9 | Una compra con al menos una entrada ingresada no se puede anular, ni por el taquillero ni por el administrador. Una compra de cuatro entradas con solo una ingresada tampoco. | RN-26 |
| CA-10 | A la hora exacta de inicio de una función, deja de aparecer a la venta en la web y en taquilla. | RN-3 |
| CA-11 | Una compra anulada y una reembolsada no aparecen en la recaudación del reporte de la distribuidora. | RF-25 |
| CA-12 | Una función cancelada no aporta entradas al reporte de no presentados. | RN-23, RF-23 |
| CA-13 | Un cliente tiene apartadas las butacas 4, 5 y 6 sin pagar y el administrador declara la 5 fuera de servicio: la 5 queda bloqueada, la 4 y la 6 siguen apartadas para ese cliente, y él lo descubre en el refresco del mapa o al intentar continuar. La 5 no se le puede vender mientras siga fuera de servicio. | RN-17 |
| CA-14 | Declarar una butaca fuera de servicio hoy no altera la ocupación reportada de ninguna función que ya haya empezado o terminado. | RN-17, RF-22 |
| CA-15 | Un cliente tarda seis minutos en pagar y nadie tocó sus butacas: la compra se confirma. Si en cambio otra persona ya se llevó una de ellas, no se confirma ninguna y el cobro queda revertido. | RN-14, RF-11 |
| CA-16 | Un cobro aprobado y luego revertido no aparece en el reporte de reembolsos ni en la recaudación. | RN-22, RF-24 |

## Dependencias

- Servicio de envío de correo electrónico, para el comprobante de compra y el aviso de
  cancelación (RF-12, RF-18). Es la única dependencia externa del sistema.
- Plano de butacas de cada sala: filas, cantidad de butacas por fila y cuáles no son vendibles.
  Lo aporta el cine una sola vez.
