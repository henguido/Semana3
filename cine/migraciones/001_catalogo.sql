-- Pieza 1: catalogo minimo y la tabla central del diseno.
--
-- La tabla `ocupacion` se declara completa aqui, con sus tres estados y todas sus
-- columnas, porque DISENO.md la fija como UNA sola decision indivisible (el "Modelo de
-- datos" no la reparte por pieza). Lo que SI se reparte por pieza es quien escribe en
-- ella: la Pieza 1 solo la lee; apartar, confirmar, bloquear y liberar llegan en las
-- Piezas 2, 3, 6, 9 y 10.

CREATE TABLE sala (
    id      INTEGER PRIMARY KEY,
    nombre  TEXT NOT NULL UNIQUE
);

-- La capacidad no se guarda: se cuenta de las butacas, para que 120 y 60 no puedan
-- quedar desmentidos por el plano.
CREATE TABLE butaca (
    id       INTEGER PRIMARY KEY,
    sala_id  INTEGER NOT NULL REFERENCES sala(id),
    fila     TEXT NOT NULL,
    numero   INTEGER NOT NULL,
    UNIQUE (sala_id, fila, numero)
);

CREATE TABLE pelicula (
    id                  INTEGER PRIMARY KEY,
    titulo              TEXT NOT NULL,
    duracion_minutos    INTEGER NOT NULL,
    clasificacion_edad  INTEGER NOT NULL DEFAULT 0,
    distribuidora       TEXT NOT NULL
);

CREATE TABLE funcion (
    id          INTEGER PRIMARY KEY,
    pelicula_id INTEGER NOT NULL REFERENCES pelicula(id),
    sala_id     INTEGER NOT NULL REFERENCES sala(id),
    inicio      TEXT NOT NULL,
    fin         TEXT NOT NULL,
    estado      TEXT NOT NULL DEFAULT 'programada'
                CHECK (estado IN ('programada', 'cancelada'))
);
CREATE INDEX idx_funcion_inicio ON funcion (inicio);
CREATE INDEX idx_funcion_sala_inicio ON funcion (sala_id, inicio);

-- La tabla central del diseno. Una fila por butaca NO disponible de una funcion. La
-- pareja funcion-butaca declarada unica es el mecanismo que cumple RNF-1: la garantia
-- vive aqui, no en el codigo (Restriccion global 4 y 5 de PLAN.md).
CREATE TABLE ocupacion (
    id          INTEGER PRIMARY KEY,
    funcion_id  INTEGER NOT NULL REFERENCES funcion(id),
    butaca_id   INTEGER NOT NULL REFERENCES butaca(id),
    estado      TEXT NOT NULL CHECK (estado IN ('bloqueada', 'apartada', 'vendida')),
    vence_en    TEXT,
    sesion_id   TEXT,
    compra_id   INTEGER,
    UNIQUE (funcion_id, butaca_id)
);
CREATE INDEX idx_ocupacion_funcion ON ocupacion (funcion_id);
