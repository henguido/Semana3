# Cine Variedades — venta de entradas en línea

Prototipo construido por piezas verticales según `PLAN.md`, sobre el diseño de `DISENO.md` y la
especificación de `ESPECIFICACION.md`. Estado actual: **Pieza 1** cerrada (ver `PLAN.md`).

## Requisitos

- Python 3.11 o superior (probado con 3.13).
- SQLite 3.35 o superior (viene con Python; verificar con `python -c "import sqlite3; print(sqlite3.sqlite_version)"`).

## Instalación

```bash
python -m venv .venv
# Windows:
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install "fastapi>=0.110" "uvicorn[standard]>=0.29" "jinja2>=3.1" "python-multipart>=0.0.9" "pytest>=8.0" "httpx>=0.27"
# Unix / Git Bash:
./.venv/Scripts/python -m pip install --upgrade pip
./.venv/Scripts/python -m pip install "fastapi>=0.110" "uvicorn[standard]>=0.29" "jinja2>=3.1" "python-multipart>=0.0.9" "pytest>=8.0" "httpx>=0.27"
```

## Dependencias

Todas las que el proyecto usa realmente, con la versión instalada en este entorno y el
repositorio oficial de cada una (tomado de sus propios metadatos, no de memoria):

| Paquete | Versión | Para qué se usa | Repositorio oficial |
|---|---|---|---|
| FastAPI | 0.141.1 | Framework web: enrutamiento y respuestas HTTP | https://github.com/fastapi/fastapi |
| Uvicorn (`[standard]`) | 0.52.3 | Servidor ASGI que sirve la aplicación | https://github.com/Kludex/uvicorn |
| Jinja2 | 3.1.6 | Motor de plantillas de las pantallas HTML | https://github.com/pallets/jinja |
| python-multipart | 0.0.32 | Requerido por FastAPI para leer formularios (`Form(...)`) | https://github.com/Kludex/python-multipart |
| pytest | 9.1.1 | Marco de pruebas | https://github.com/pytest-dev/pytest |
| httpx | 0.28.1 | Cliente HTTP que usa `TestClient` para probar las rutas | https://github.com/encode/httpx |

SQLite no aparece en esta tabla porque no se instala: viene con la biblioteca estándar de
Python (`sqlite3`). No se usa ningún ORM, según la decisión de `DISENO.md`.

## Ejecutar las pruebas

```bash
./.venv/Scripts/python -m pytest -v
```

Las pruebas usan una base de datos SQLite temporal por prueba (fixture `cx` en
`tests/conftest.py`); no tocan `cine.db`.

## Recrear los datos de prueba y arrancar el servidor

`cine.db` no se versiona (ver `.gitignore`). Para recrearlo con datos de ejemplo:

```bash
./.venv/Scripts/python scripts/datos_prueba.py
```

Esto borra y vuelve a crear `cine.db`, aplica las migraciones de `cine/migraciones/`, siembra
las dos salas (Sala 1: 120 butacas, Sala 2: 60) y dos funciones de una misma película: una que
cierra 30 segundos después de sembrarla (para ver en vivo que una función deja de estar a la
venta exactamente a su hora de inicio) y otra, cuatro horas más adelante, con cuatro butacas
insertadas a mano en los cuatro estados posibles (vendida, apartada vigente, apartada vencida,
bloqueada). El script imprime las rutas exactas de cada función al terminar.

Luego, levantar el servidor:

```bash
./.venv/Scripts/python -m uvicorn cine.web.app:app --reload
```

Abrir `http://127.0.0.1:8000/` en el navegador. El mapa de butacas está pensado primero para
teléfono: se ve y se usa igual en una ventana angosta (375 px de ancho).

## Qué existe hasta ahora (Pieza 1)

- Cartelera de la semana: `GET /`.
- Mapa de una función: `GET /funcion/{id}`.
- Ambas son de solo lectura. Escoger butacas, apartar, pagar, taquilla, roles, cancelación y
  reportes llegan en piezas siguientes — ver `PLAN.md`.

## Variables de entorno

- `CINE_DB`: ruta del archivo SQLite (por defecto `cine.db` en la raíz del proyecto).
