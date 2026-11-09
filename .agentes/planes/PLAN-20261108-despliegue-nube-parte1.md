---
id: PLAN-20261108-despliegue-nube-parte1
estado: cerrado         # borrador | aprobado | en_ejecucion | cerrado
rama: agente/despliegue-nube
rama_base: agente/actividades-dinamicas   # o main si Oscar ya fusionó
stack: fastapi
zona_protegida: sí      # autenticación nueva + migración que BORRA las tablas de reportes y fotos
autor: claude
descartado: "2026-11-08 — Oscar decidió quedarse en local y seguir guardando los reportes. No se ejecutó."
---

# Despliegue en la nube — parte 1: backend sin estado (Render) + catálogos (Supabase)

## Objetivo
Dejar el backend listo para Render (gratuito, Docker) con Postgres de Supabase, guardando **solo catálogos y usuarios**. Los reportes ya no se guardan: el frontend manda la semana completa (datos y fotos) al pedir una descarga, y el backend genera el Excel o el PDF en memoria y lo devuelve sin almacenar nada. Se agrega inicio de sesión con JWT y los administradores los inyectan las semillas.
La parte 2 (`PLAN-20261108-despliegue-nube-parte2`) adapta el frontend a Vercel y a este flujo.

## Decisiones de Oscar (2026-11-08)
- **Acceso:** inicio de sesión propio con JWT. **Las semillas inyectan los usuarios administradores** para poder entrar.
- **Almacenamiento:** "no necesito almacenar, solo ir descargando los reportes". En el servidor solo viven los catálogos (colaboradores, herramientas, materiales y firmantes) y los usuarios.
- **Borrador:** la semana vive solo mientras la pestaña está abierta (parte 2). Si se cierra, se pierde.
- **Mapa y logo:** siguen fijos en `backend/app/plantillas/` (sin cambios).
- **Render:** plan gratuito (512 MB de RAM, se duerme, sin disco ni consola).
- **Datos:** la nube empieza de cero; solo se cargan las semillas.

## Contexto
- `backend/app/models/reportes.py`: ORM de `Reporte`, `Dia`, `Actividad`, `Asignacion`, `DiaHerramienta`, `DiaMaterial` y `Foto` (tablas 0001/0002).
- `backend/app/routers/reportes.py`: CRUD de reportes, días y fotos en disco (`/data/fotos`). `crear_reporte` calcula las fechas con `date.fromisocalendar(anio, semana, 1) + timedelta(days=i)`. `LIMITES_FOTOS` A–J y AD = 4.
- `backend/app/routers/exportar.py`: `GET /api/reportes/{id}/exportar/{tipo}`, que lee el reporte de la BD.
- `backend/app/services/excel_formato.py` (`generar_formato(reporte)`) y `excel_mejorado.py` (`generar_mejorado(reporte)`) usan `object_session(reporte)` para consultar catálogos y leen las fotos desde `fotos.FOTOS_DIR`. `services/calculos.py` (`recalcular_horas`, `totales_dia` y `jornada_dia`) trabaja por atributos (`dia.actividades`, `asignacion.horas`, etc.).
- `backend/app/schemas/reportes.py`: `ReporteCreate` (validador de semana ISO), `DiaWrite`, `ActividadWrite`, `AsignacionWrite`, `CantidadHerramientaWrite`, `CantidadMaterialWrite`, `Letra` y `Espacio`.
- `backend/app/services/fotos.py`: `procesar_foto` valida con Pillow y **escribe en disco**.
- `backend/app/services/semillas.py`: `cargar_semillas` idempotente, llamado en `lifespan`.
- `backend/alembic/versions/0002_actividades_a_j.py`: `batch_alter_table(recreate="always")` falla en Postgres (`DROP TABLE actividades` con FK desde `asignaciones`).
- `backend/app/main.py`: rutas sin autenticación; CORS solo con `Content-Type`.
- `backend/Dockerfile`: puerto fijo 8000; la plantilla `.xlsx` no se instala como *package data*.

## Alcance
**Dentro:** Postgres, compatibilidad de migraciones, RLS, eliminación de tablas y endpoints de reportes guardados, endpoint de exportación sin estado, autenticación JWT con admins por semillas, CORS y cabeceras, Docker y `render.yaml`, documentación.

**Fuera de alcance:**
- Frontend (parte 2). Entre la parte 1 y la 2 el frontend no funciona; se fusionan juntas.
- Guardar borradores en el servidor o en el navegador.
- Mapa o logo editables.
- Registro público, roles, recuperación de contraseña y refresh tokens.
- Crear las cuentas de Render, Vercel o Supabase; `git push` o desplegar (lo hace Oscar).
- Cambiar el diseño de los Excel o la lógica de cálculo de horas.

## Tareas

### Tarea 1 — Postgres y migraciones compatibles con ambos motores
- **Archivos:** `backend/pyproject.toml`, `backend/app/config.py`, `backend/alembic/versions/0002_actividades_a_j.py`, `backend/alembic/versions/0003_rls_supabase.py` (crear), `backend/tests/test_migraciones.py`, `.env.example`.
- **Patrón a seguir:** `0001`/`0002` (encabezado, tipos); validador `split_cors_origins` en `config.py`.
- **Seguridad:** #1, #4, #13, #20.
- **Qué hacer:**
  1. Agrega `psycopg[binary]` con versión exacta (la estable más reciente que pase `pip-audit`).
  2. `Settings`:
     - `environment: Literal["local", "test", "production"]`.
     - Validador `normalizar_database_url` (`mode="before"`): convierte `postgres://` o `postgresql://` en `postgresql+psycopg://` y agrega `sslmode=require` si la URL es de Postgres y no lo trae.
  3. `0002` según el motor: con `op.get_bind().dialect.name == "sqlite"` se queda el `batch_alter_table` actual; en otro motor usa `op.drop_constraint(..., type_="check")` y `op.create_check_constraint(...)` directos. Igual en el `downgrade`.
  4. `0003_rls_supabase`: solo en `postgresql`, `ALTER TABLE <t> ENABLE ROW LEVEL SECURITY` (sin políticas) para cada tabla existente en ese punto. El `downgrade` hace `DISABLE`. En SQLite no hace nada. Así la API de datos de Supabase (roles `anon`/`authenticated`) no expone nada, y el backend, que se conecta como dueño, sigue funcionando.
  5. `test_migracion_ida_y_vuelta_postgres`, con `pytest.mark.skipif` si no está `TEST_POSTGRES_URL`: upgrade a head, `relrowsecurity = true` en `pg_class` para todas las tablas de head, downgrade a base y upgrade otra vez.
  6. `.env.example`: URL de Supabase de ejemplo con datos ficticios y la nota de usar el *session pooler* (IPv4).
- **Criterio de aceptación:** `pytest -q` pasa en SQLite. Con un Postgres temporal (`docker run --rm -d -e POSTGRES_PASSWORD=prueba -p 55432:5432 postgres:17-alpine`) y `TEST_POSTGRES_URL=postgresql://postgres:prueba@localhost:55432/postgres`, `pytest -q tests/test_migraciones.py` pasa. `alembic check` está limpio en los dos motores.
- **Pruebas requeridas:** ida y vuelta en Postgres, RLS activo y normalización de URL (Postgres → `+psycopg` con `sslmode=require`; SQLite intacta).

### Tarea 2 — Exportación sin estado: el reporte llega completo en la petición
- **Archivos:** `backend/app/schemas/exportar.py` (crear), `backend/app/services/reporte_memoria.py` (crear), `backend/app/services/fotos.py`, `backend/app/services/excel_formato.py`, `backend/app/services/excel_mejorado.py`, `backend/app/routers/exportar.py`, `backend/app/config.py`, `backend/tests/test_exportar.py`, `backend/tests/test_excel_formato.py`.
- **Patrón a seguir:** schemas `extra="forbid"` de `schemas/reportes.py` (reutiliza `ReporteCreate`, `DiaWrite`, `Letra` y `Espacio`); servicio puro como `services/calculos.py`; router de `exportar.py`.
- **Seguridad:** #8, #14, #15, #16, #17.
- **Qué hacer:**
  1. `schemas/exportar.py`:
     - `FotoExportar{indice: int (ge=0), espacio: Espacio}`.
     - `DiaExportar(DiaWrite)` con `dia_semana: int` (de 0 a 5) y `fotos: list[FotoExportar]` (`max_length=44`). Validador: como máximo 4 fotos por `espacio`.
     - `ReporteExportar(ReporteCreate)` con `elaborado_por_id: int | None`, `revisado_por_id: int | None` y `dias: list[DiaExportar]` de exactamente 6 elementos con `dia_semana` 0–5 sin repetir. Los `indice` de fotos no se repiten en todo el reporte.
  2. `services/reporte_memoria.py` con dataclasses (`@dataclass`, sin ORM) que imitan los atributos que ya leen los servicios de Excel y `calculos.py`:
     - `ReporteMemoria(anio, semana, elaborado_por, revisado_por, dias)`.
     - `DiaMemoria(dia_semana, fecha, observacion, texto_fotos, actividades, herramientas, materiales, fotos)`.
     - `ActividadMemoria(letra, descripcion, asignaciones)`.
     - `AsignacionMemoria(colaborador_id, colaborador, horas, horas_manual)`.
     - `CantidadMemoria(herramienta|material, cantidad)`, con los campos que use cada exportador.
     - `FotoMemoria(espacio, orden, contenido: bytes)`.
     - Función `armar_reporte(datos: ReporteExportar, contenidos: list[bytes], session) -> ReporteMemoria`:
       - Resuelve `Colaborador`, `Herramienta`, `Material` y `Firmante` por id con `session.get`; si no existe → `NotFoundError("Colaborador no encontrado")` (mismos mensajes que hoy).
       - Calcula las fechas como `crear_reporte`.
       - Usa `TEXTO_FOTOS_PREDETERMINADO` si `texto_fotos` viene vacío.
       - Ordena las actividades por letra.
       - Aplica `recalcular_horas(dia, jornada_dia(dia))`.
       - Asigna `contenidos[foto.indice]` a cada foto; un `indice` fuera de rango → `InvalidInputError`.
  3. `fotos.procesar_foto(contenido, max_mb) -> bytes`: misma validación de Pillow (tipo real JPEG/PNG/WebP, `MAX_LADO`, re-codifica a JPEG) y devuelve los bytes **sin escribir a disco**. Elimina `FOTOS_DIR` y `eliminar_archivo`.
  4. `generar_formato(reporte, colaboradores, herramientas)` y `generar_mejorado(reporte, colaboradores, herramientas, materiales)` reciben los catálogos como parámetros; quita `object_session`. Las fotos se cargan con `ExcelImage(BytesIO(foto.contenido))`; quita los `is_file()`. El router consulta los catálogos con las mismas consultas que hoy (activos y ordenados en el formato; ordenados en el mejorado).
  5. `routers/exportar.py`: `POST /api/exportar/{tipo}` con `tipo: Literal["formato", "mejorado", "pdf"]`, como `multipart/form-data`:
     - `datos: Annotated[str, Form()]`, un JSON validado con `ReporteExportar.model_validate_json`. Si es inválido → 422 con `code="validation_error"`, usando el manejador existente o lanzando `InvalidInputError` con el detalle.
     - `fotos: list[UploadFile] = File(default=[])`.
     - Lee cada archivo con el tope `max_foto_mb` (igual que `subir_foto`) y la suma con el tope `max_exportacion_mb` (nuevo setting, por defecto 60, entre 5 y 200). Si se pasa → `FileTooLargeError`.
     - Procesa cada foto con `procesar_foto`.
     - Responde como `_respuesta` hoy (`attachment; filename="CH-RSG-{semana}-{anio}.xlsx|.pdf"` y el nombre del mejorado actual).
     - **No escribe nada en la BD ni en disco** (el PDF ya usa un `TemporaryDirectory`).
  6. Reescribe `test_exportar.py` y `test_excel_formato.py` para armar el reporte con `ReporteExportar`/`armar_reporte`, con imágenes sintéticas de Pillow en memoria. Deben conservar **todas** las comprobaciones actuales: celdas, fórmulas, bandas A–J, filas ocultas, fotos 1/2/4 sin superponerse y escape de fórmulas.
- **Criterio de aceptación:**
  - `pytest -q` pasa.
  - `POST /api/exportar/formato` con 6 días, A–J y 4 fotos en D → 200 y un `.xlsx` con 4 imágenes en el renglón D.
  - `pdf` → empieza con `%PDF`.
  - 5 fotos en un espacio → 422.
  - Un `.exe` renombrado a `.jpg` → 422 `invalid_file`.
  - Un colaborador inexistente → 404.
  - Con 5 días → 422.
  - Un campo extra en `datos` → 422.
  - Al terminar, `SELECT count(*)` de cada tabla de catálogos no cambia.
  - `rg -n "FOTOS_DIR|/data/fotos|object_session" backend/app` → 0 resultados.
- **Pruebas requeridas:** los casos del criterio, más el tope total (`max_exportacion_mb` parcheado a 1 → 413).

### Tarea 3 — Eliminar los reportes guardados (modelos, endpoints y tablas)
- **Archivos:** `backend/app/models/reportes.py`, `backend/app/models/__init__.py`, `backend/app/routers/reportes.py` (eliminar), `backend/app/schemas/reportes.py`, `backend/app/main.py`, `backend/alembic/versions/0004_quita_reportes.py` (crear), `backend/tests/test_reportes.py` (eliminar o reducir), `backend/tests/test_migraciones.py`.
- **Patrón a seguir:** migraciones 0001/0002.
- **Seguridad:** #13, #17.
- **Qué hacer:**
  1. Elimina las clases ORM `Reporte`, `Dia`, `Actividad`, `Asignacion`, `DiaHerramienta`, `DiaMaterial` y `Foto`. Conserva `LETRAS_ACTIVIDAD` y `TEXTO_FOTOS_PREDETERMINADO` (muévelas a `services/reporte_memoria.py` y actualiza las importaciones).
  2. Elimina `routers/reportes.py` y su `include_router`.
  3. Elimina de `schemas/reportes.py` lo que solo usaban esos endpoints (`ReporteRead`, `ReporteUpdate`, `DiaRead`, `ActividadRead`, `FotoRead`, etc.). Conserva los `*Write` y validadores que reutiliza la tarea 2.
  4. Las pruebas de cálculo de horas (`test_reportes.py`: repartir horas, horas manuales, sábado) se pasan a `test_calculos.py`/`test_exportar.py` usando `armar_reporte`. Que no se pierda ninguna comprobación de horas.
  5. `0004_quita_reportes`: `drop_table` en orden `fotos`, `asignaciones`, `actividades`, `dia_herramientas`, `dia_materiales`, `dias` y `reportes`. Comentario: "Borra los reportes guardados y sus fotos. Respaldar data/ antes." El `downgrade` recrea las tablas vacías con el esquema de 0002 (restricciones A–J incluidas).
  6. `test_migraciones.py`: `TABLAS` en head = `{colaboradores, herramientas, materiales, firmantes, usuarios}` (usuarios llega en la tarea 4; si esta tarea va antes, ajústalo al terminar la 4). La ida y vuelta pasa en los dos motores.
- **Criterio de aceptación:**
  - `pytest -q` pasa.
  - `GET /api/reportes` → 404.
  - `alembic upgrade head` sobre una **copia sintética** de la base antigua (creada en la prueba con 0002 + un reporte) deja solo las tablas de catálogos.
  - `rg -n "class (Reporte|Dia|Actividad|Asignacion|Foto)\(Base\)" backend/app` → 0.
  - Las pruebas de horas siguen existiendo y pasan.
- **Pruebas requeridas:** migración 0004 con datos sintéticos (ida y vuelta) y horas (repartir, manuales, sábado y advertencia), ahora sobre `armar_reporte`.

### Tarea 4 — Usuarios, login JWT y administradores inyectados por las semillas
- **Archivos:** `backend/pyproject.toml`, `backend/app/config.py`, `backend/app/models/usuarios.py` (crear), `backend/app/models/__init__.py`, `backend/alembic/versions/0005_usuarios.py` (crear), `backend/app/schemas/auth.py` (crear), `backend/app/services/auth.py` (crear), `backend/app/services/semillas.py`, `backend/app/routers/auth.py` (crear), `backend/app/errors.py`, `backend/app/main.py`, `backend/app/cli.py` (crear), `backend/tests/test_auth.py` (crear), `backend/tests/test_semillas.py` (crear), `backend/tests/conftest.py`.
- **Patrón a seguir:** modelos en `models/catalogos.py`; `cargar_semillas` (idempotente, en `lifespan`); schemas `extra="forbid"`; `routers/catalogos.py`; errores de dominio en `errors.py`.
- **Seguridad:** #1, #6, #8, #10, #11, #12, #14, #17.
- **Qué hacer:**
  1. Dependencias con versión exacta: `PyJWT` y `argon2-cffi`.
  2. `Settings`:
     - `jwt_secreto: SecretStr | None`.
     - `jwt_minutos: int = Field(480, ge=5, le=1440)`.
     - `admins_semilla: Annotated[list[AdminSemilla], NoDecode] = []`, que lee el JSON de `ADMINS_SEMILLA` (`[{"correo": "...", "contrasena_hash": "$argon2id$..."}]`). Se usa JSON porque los hashes llevan comas y `$`. Cada hash debe empezar con `$argon2`; si no → `ValueError`, para rechazar una contraseña pegada en claro.
     - En `production` se exige `jwt_secreto` de al menos 32 caracteres y `cors_origins` no vacío. En `local`/`test`, si falta el secreto, se genera uno aleatorio por proceso.
  3. Modelo `Usuario` (`usuarios`): `id`, `correo` `String(254)` único en minúsculas, `contrasena_hash` `String(255)`, `activo` (por defecto true), `intentos_fallidos` (por defecto 0), `bloqueado_hasta` `DateTime(timezone=True)` nullable y `creado_en` con `server_default=func.now()`. Migración `0005` con RLS en Postgres.
  4. `services/auth.py`:
     - `hashear` y `verificar` con argon2; `verificar` captura `VerifyMismatchError`.
     - `crear_token(usuario) -> (token, expira_en)`: HS256 con claims `sub`, `iat` y `exp`.
     - `leer_token(token) -> int`: `algorithms=["HS256"]`, exige `exp` y lanza `NoAutenticadoError` si falla.
  5. **Semillas:** `cargar_usuarios_semilla(session, admins)` en `services/semillas.py`, llamada desde `cargar_semillas` con `get_settings().admins_semilla`.
     - Crea cada admin cuyo correo no exista (`activo=True`).
     - Si el correo ya existe, no lo toca: no pisa contraseñas ni reactiva cuentas.
     - Es idempotente.
     - No registra correos ni hashes en logs.
  6. Errores: `NoAutenticadoError` (401, `no_autenticado`), `CredencialesInvalidasError` (401, `credenciales_invalidas`) y `DemasiadosIntentosError` (429, `demasiados_intentos`). Los 401 incluyen `WWW-Authenticate: Bearer`.
  7. `routers/auth.py` (`/api/auth`):
     - `POST /login` con `LoginEntrada{correo (max 254), contrasena (1–128)}`.
       - Usuario inexistente o inactivo → 401 genérico; verifica contra un hash ficticio para no dar pistas por tiempo de respuesta.
       - Usuario bloqueado → 429.
       - Contraseña incorrecta → suma al contador; al llegar a 5 fallos bloquea 15 minutos y reinicia el contador.
       - Correcto → reinicia el contador y devuelve `{access_token, token_type: "bearer", expira_en}`.
     - `GET /yo` → `{id, correo}`.
  8. Dependencia `usuario_actual` (`HTTPBearer(auto_error=False)`); un usuario inactivo → 401. En `main.py`, `include_router(catalogos.router, dependencies=[Depends(usuario_actual)])` y lo mismo para `exportar`. Solo `health` y `auth` son públicos.
  9. `cli.py`: `python -m app.cli hash-contrasena` pide la contraseña dos veces con `getpass`, exige al menos 12 caracteres e imprime solo el hash. Nunca acepta contraseñas como argumento.
  10. `conftest.py`: el fixture `client` va autenticado con un usuario de prueba; agrega el fixture `client_anonimo`.
- **Criterio de aceptación:**
  - `pytest -q` pasa.
  - Sin token, `GET /api/catalogos/colaboradores` y `POST /api/exportar/pdf` → 401; `GET /api/health` → 200.
  - El sexto intento fallido → 429.
  - Un token expirado, firmado con otra clave o con `alg=none` → 401.
  - Un campo extra en el login → 422.
  - `/yo` devuelve exactamente las claves `{"id", "correo"}`.
  - `production` sin secreto → `ValidationError`.
  - `test_semillas.py`:
    - 2 admins en `ADMINS_SEMILLA` → 2 usuarios, y cada uno puede iniciar sesión.
    - Repetir las semillas no duplica.
    - Un admin ya existente conserva su contraseña.
    - Un hash sin `$argon2` → `ValidationError`.
    - Sin la variable no se crean usuarios y los catálogos se cargan igual.
- **Pruebas requeridas:** las del criterio, más el desbloqueo pasado el tiempo (reloj parcheado) y la CLI con contraseña corta rechazada.

### Tarea 5 — CORS, cabeceras, imagen Docker y `render.yaml`
- **Archivos:** `backend/app/main.py`, `backend/pyproject.toml`, `backend/Dockerfile`, `docker-compose.yml`, `render.yaml` (crear), `.env.example`, `backend/tests/test_cors.py` (crear).
- **Patrón a seguir:** bloque CORS de `main.py`, `Dockerfile` y `docker-compose.yml` actuales.
- **Seguridad:** #1, #2, #6, #18, #19, #20.
- **Qué hacer:**
  1. CORS: `allow_origins=settings.cors_origins` (nunca `*`), `allow_credentials=False`, `allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"]`, `allow_headers=["Content-Type", "Authorization"]` y `expose_headers=["Content-Disposition"]`.
  2. En `production`: `docs_url=None` y `openapi_url=None`.
  3. Middleware de cabeceras: `nosniff`, `X-Frame-Options: DENY` y `Referrer-Policy: no-referrer`; HSTS solo en `production`.
  4. `pyproject.toml`: `[tool.setuptools.package-data] app = ["plantillas/*", "seeds/*.json"]`.
  5. `Dockerfile`:
     - Sin `/data` (ya no se usa).
     - `USER app`.
     - `CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]`.
     - En `docker-compose.yml`, el volumen `./data` sigue solo para el SQLite local de catálogos (`DATABASE_URL` por defecto). Ajusta los permisos para que `make up` funcione con `USER app` (p. ej. `user: "${UID:-1000}:${GID:-1000}"`).
  6. `render.yaml`:
     - Servicio `reportes-servicios-api`, `runtime: docker`, `plan: free`, `dockerContext: ./backend`, `dockerfilePath: ./backend/Dockerfile` y `healthCheckPath: /api/health`.
     - `envVars`:
       - `ENVIRONMENT=production`.
       - `JWT_SECRETO` con `generateValue: true`.
       - `DATABASE_URL`, `CORS_ORIGINS` y `ADMINS_SEMILLA` con `sync: false`.
       - `JORNADA_SEMANA=8`, `JORNADA_SABADO=5`, `MAX_FOTO_MB=15` y `MAX_EXPORTACION_MB=60`.
  7. `.env.example`: `JWT_SECRETO=`, `JWT_MINUTOS=480`, `ADMINS_SEMILLA=[]` (con el formato de ejemplo ficticio y cómo generar el hash) y `MAX_EXPORTACION_MB=60`.
- **Criterio de aceptación:**
  - Preflight con un origen permitido → `Access-Control-Allow-Origin` presente y `Authorization` permitido; con un origen no permitido → sin `Access-Control-Allow-Origin`.
  - En `production`, `/api/docs` → 404.
  - Imagen: `docker run --rm --memory=512m -e ENVIRONMENT=production -e JWT_SECRETO=<32+> -e CORS_ORIGINS=https://ejemplo.vercel.app -e DATABASE_URL=<postgres temporal> -e ADMINS_SEMILLA='[...]' -e PORT=10000 -p 10000:10000 <imagen>`:
    - Arranca, migra y responde `/api/health` 200.
    - El login con el admin semilla funciona.
    - `POST /api/exportar/pdf` con 6 días, A–J y 4 fotos por actividad del lunes (fotos sintéticas de unos 300 KB) responde 200. Anota en el reporte el pico de `docker stats`.
  - Dentro de la imagen, `python -I -c "import app.services.excel_formato as m; print((m.PLANTILLAS_DIR/'plantilla_formato.xlsx').is_file())"` → `True`.
  - `make up` local funciona.
- **Pruebas requeridas:** `test_cors.py` (casos de CORS, docs y `nosniff`); la prueba de la imagen va documentada en el reporte.

### Tarea 6 — Documentación y decisiones del proyecto
- **Archivos:** `README.md`, `.agentes/PROYECTO.md`.
- **Patrón a seguir:** secciones actuales del README.
- **Seguridad:** #1, #2.
- **Qué hacer:**
  - README, sección "Despliegue":
    - Supabase: crear el proyecto y usar la URL del *session pooler*.
    - Render: crear desde Blueprint y llenar `DATABASE_URL`, `CORS_ORIGINS` y `ADMINS_SEMILLA`.
    - Generar el hash de cada admin con `python -m app.cli hash-contrasena`. Para agregar un admin, sumarlo a `ADMINS_SEMILLA` y reiniciar el servicio.
    - Límites del plan gratuito: se duerme y tiene 512 MB.
    - "Los reportes no se guardan: se descargan al generarlos".
  - `PROYECTO.md`:
    - Qué es: catálogos en la nube y reportes que se generan y descargan sin guardarse.
    - Usuarios: personas autorizadas por internet.
    - Stack: Postgres (Supabase) en producción y SQLite en local; Render + Vercel.
    - Autenticación: JWT propio, argon2, bloqueo y admins por semillas.
    - Seguridad base: las medidas 6 y 9–12, 18 y 19 dejan de ser n.a.
    - Piezas de referencia: `routers/auth.py` y `services/reporte_memoria.py`.
    - Estructura: sin `routers/reportes.py`.
- **Criterio de aceptación:** guías completas sin valores reales; gitleaks limpio.
- **Pruebas requeridas:** n.a. (documentación).

## Seguridad

| # | Medida | Aplica | Cómo se cumple / prueba |
|---|---|---|---|
| 1 | Ocultar API keys | sí | `JWT_SECRETO`, `DATABASE_URL` y `ADMINS_SEMILLA` (solo hashes) únicamente en las variables de Render. Nada de credenciales en `seeds/catalogos.json`. gitleaks. |
| 2 | Secretos fuera de Git | sí | `.env` ignorado; `render.yaml` con `sync: false`/`generateValue`. |
| 3 | Llave pública para DB | sí | El frontend no recibe llaves de Supabase. Sugerencia para un plan aparte: un rol de BD con privilegios mínimos. |
| 4 | RLS | sí | RLS sin políticas en todas las tablas (0003/0005). Prueba en Postgres. |
| 6 | Autenticación | sí | `usuario_actual` en `catalogos` y `exportar`. Pruebas de 401. |
| 7 | Acceso a registros | n.a. | Ya no hay registros por usuario; los catálogos son compartidos. |
| 8 | Manipulación de campos | sí | `extra="forbid"` en `ReporteExportar` y `LoginEntrada`. Pruebas de campo extra. |
| 9 | Cookies de sesión | n.a. | No hay cookies: Bearer en cabecera (el almacenamiento se define en la parte 2). |
| 10 | Hashear contraseñas | sí | argon2; las semillas solo aceptan hashes `$argon2`. |
| 11 | Rate limiting | sí | Bloqueo de 15 minutos tras 5 fallos por cuenta. Prueba del 429. Exportar requiere sesión y tiene tope de MB. |
| 12 | Bots | sí (parcial) | Bloqueo progresivo; sin registro público, así que no hace falta CAPTCHA. |
| 13 | Parametrizar | sí | ORM; SQL estático en migraciones. `rg -n "execute\(f|text\(f" backend` = 0. |
| 14 | Validar inputs | sí | `ReporteExportar` (6 días, letras, fotos por espacio, índices) y topes de MB. Pruebas de 422/413. |
| 15 | Sanitizar | sí | `texto_seguro` sin cambios en los Excel; prueba de fórmula conservada. |
| 16 | Restringir archivos | sí | Pillow verifica el tipo real, re-codifica a JPEG, aplica tamaño máximo por foto y en total; nada se escribe en disco. Prueba del `.exe`. |
| 17 | Datos necesarios | sí | `/yo` sin hash; exportar solo devuelve el archivo. |
| 18 | Headers | sí | Middleware de la tarea 5. |
| 19 | HTTPS | sí | Render/Vercel con HTTPS, HSTS en producción y `sslmode=require`. |
| 20 | Dependencias | sí | `psycopg`, `PyJWT` y `argon2-cffi` con versión fija; `pip-audit` limpio. |

n.a.: 5 (sin datos sensibles guardados; los reportes no se guardan), 7 y 9 (justificadas).

## Consistencia
- Se reutilizan `Settings` con validadores, `DomainError`, schemas `*Write`, `calculos.py`, `texto_seguro`, la estructura de los Excel y `cargar_semillas`.
- **Piezas nuevas, justificadas:**
  - Autenticación: no existía.
  - `reporte_memoria.py`: reemplaza el ORM de reportes, que se elimina; no es una segunda forma de hacer lo mismo.
- **Dependencias nuevas, autorizadas:** `psycopg[binary]`, `PyJWT` y `argon2-cffi`.

## Verificación final
```bash
git diff agente/actividades-dinamicas...agente/despliegue-nube --stat
docker build -t tania-api-nube backend
docker run --rm -w /srv tania-api-nube sh -c "ruff check . && ruff format --check . && pytest -q && bandit -r app -ll && pip-audit"
docker run --rm -d --name pg-prueba -e POSTGRES_PASSWORD=prueba -p 55432:5432 postgres:17-alpine
docker run --rm --network host -w /srv -e TEST_POSTGRES_URL=postgresql://postgres:prueba@localhost:55432/postgres tania-api-nube pytest -q tests/test_migraciones.py
docker stop pg-prueba
gitleaks detect --no-git -v
```
No uses el `./data` real en las pruebas. **No corras `make up` sin que Oscar haya respaldado `data/`**, porque la migración 0004 borra los reportes guardados localmente.

## Riesgos
- **Borrado de los reportes locales:** la 0004 elimina los reportes y fotos que tengas en tu SQLite local. El respaldo `data/app.db.antes-0002` no incluye lo capturado después; antes de `make up`, respalda con `cp -r data data.antes-despliegue`. Las fotos en `data/fotos/` no se borran del disco.
- **Memoria en Render gratuito:** cada descarga sube todas las fotos de la semana y LibreOffice corre en 512 MB. La parte 2 comprime las fotos en el navegador antes de subirlas (unos 300 KB cada una) y la tarea 5 mide el pico. Si falla, el plan Starter (7 USD) **no** sirve, porque tiene los mismos 512 MB. Las opciones son Standard (25 USD, 2 GB), generar el PDF con una librería de Python o quitar el PDF (plan aparte, decisión de Oscar).
- **Tiempo de respuesta:** tras dormirse, la primera petición tarda alrededor de un minuto y el PDF tarda unos segundos más. La parte 2 muestra mensajes de espera.
- **Supabase gratuito se pausa** tras 7 días sin uso.

## Supuestos y preguntas abiertas
- Supuesto: cualquier usuario autenticado puede editar catálogos y exportar (no hay roles).
- Supuesto: sin preguntas abiertas de negocio; los admins y URLs los pone Oscar en Render.
