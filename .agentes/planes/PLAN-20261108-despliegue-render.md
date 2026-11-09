---
id: PLAN-20261108-despliegue-render
estado: en_ejecucion      # borrador | aprobado | en_ejecucion | cerrado
rama: agente/despliegue-render
rama_base: agente/modo-sin-almacenar   # después de aceptar modo-sin-almacenar y reabrir-excel
stack: fastapi
zona_protegida: sí      # autenticación nueva
autor: claude
reemplaza: PLAN-20261108-despliegue-nube-parte1, PLAN-20261108-despliegue-nube-parte2 (descartados)
---

# Despliegue: backend en Render, catálogos en Supabase y frontend en Vercel (modo sin almacenar)

## Objetivo
Publicar el sistema en internet con `ALMACENAR=false`:
- **Backend** en Render (gratuito, Docker).
- **Catálogos y usuarios** en Postgres de Supabase.
- **Frontend** en Vercel.

Se agrega inicio de sesión con JWT (administradores inyectados por las semillas). Los reportes no se guardan: se descargan y se reabren con el Excel (planes anteriores).

## Decisiones de Oscar (2026-11-08)
- Render gratuito para el backend, Vercel para el frontend y Supabase para la base.
- En la nube no se guarda nada salvo **catálogos** (colaboradores, herramientas, materiales y firmantes) y **usuarios**, todos en Supabase.
- Inicio de sesión con JWT; las **semillas inyectan los administradores**.
- Uso esperado: unas 20 fotos por semana (medido: ~316 MB de pico con 512 MB de límite).
- En local (`make up`) todo sigue como hoy: `ALMACENAR=true`, SQLite y sin inicio de sesión.

## Contexto
- Depende de `PLAN-20261108-modo-sin-almacenar` (`ALMACENAR`, `/api/config`, `POST /api/exportar/{tipo}`, `EditorSemana`) y `PLAN-20261108-reabrir-excel` (`POST /api/importar`).
- `backend/app/config.py`: `Settings` con `database_url` (SQLite), `environment: Literal["local", "test"]`, `cors_origins`, `almacenar` y `max_exportacion_mb`.
- `backend/app/db.py`: `connect_args` solo para SQLite.
- `backend/app/main.py`: rutas sin autenticación; CORS solo con `Content-Type`; `lifespan` con `cargar_semillas`.
- `backend/app/services/semillas.py`: `cargar_semillas` idempotente (catálogos desde `seeds/catalogos.json`).
- `backend/alembic/versions/0002_actividades_a_j.py`: `batch_alter_table(recreate="always")` falla en Postgres (FK desde `asignaciones`).
- `backend/Dockerfile`: puerto fijo 8000; `pyproject.toml` no instala `plantillas/*.xlsx` como *package data*.
- `frontend/src/api/client.ts`: `fetch(`/api${path}`)` relativo, sin `Authorization`; `apiDescarga` (plan de los modos).
- `frontend/nginx.conf`: CSP y cabeceras.
- Pruebas: `backend/tests/conftest.py` (SQLite en memoria, `client`), `test_migraciones.py` (solo SQLite).
- No hay patrón de autenticación en el repo: es la **primera pieza** de su tipo.

## Alcance
**Dentro:** Postgres y migraciones compatibles, RLS, usuarios y JWT con un interruptor por variable, admins por semillas, reglas de producción, CORS y cabeceras, Docker y `render.yaml`, cliente con token y login en el frontend, `vercel.json`, medición de memoria y documentación.

**Fuera de alcance:**
- Guardar reportes en la nube (`ALMACENAR=true` en producción queda **prohibido** por validación).
- Migrar los datos locales a Supabase (la nube empieza de cero con las semillas).
- Registro público, roles, recuperación de contraseña y refresh tokens.
- Crear las cuentas de Render, Vercel o Supabase, hacer `git push` o desplegar (lo hace Oscar con la guía).
- Reducir las fotos a 800 px (plan aparte si crece el uso).

## Reparto (decisión de Oscar: avanzar en paralelo)
**Claude** adelanta en paralelo las partes que no dependen de los planes de los modos. Trabaja en la rama `agente/despliegue-render-base` (worktree aparte, desde `agente/actividades-dinamicas`):
- Tarea 1 completa (Postgres, `0002` según el motor, `0003` RLS y la prueba en Postgres).
- Tarea 2 **núcleo**: modelo `Usuario`, migración `0004`, `services/auth.py`, `routers/auth.py`, `cli.py`, admins por semillas y sus pruebas. **No** conecta `usuario_actual` en `main.py` ni toca `routers/config.py`.
- Tarea 4 sin la medición: *package data*, `Dockerfile` con `PORT` y `render.yaml`.
- Tarea 6 **solo** `frontend/vercel.json` y `frontend/.env.example`.

**Codex** (después de `modo-sin-almacenar` y `reabrir-excel`):
1. Integra `agente/despliegue-render-base` en `agente/despliegue-render`. Resuelve los conflictos en `config.py`/`main.py` conservando los dos lados.
2. Completa la tarea 2: conectar `usuario_actual` a los routers y `autenticacion` en `/api/config`.
3. Hace las tareas 3 y 5, la medición de la tarea 4 y la documentación de la tarea 6.

No se editan los archivos del otro mientras los dos trabajan.

## Tareas

### Tarea 1 — Postgres (Supabase) y migraciones compatibles
- **Archivos:** `backend/pyproject.toml`, `backend/app/config.py`, `backend/alembic/versions/0002_actividades_a_j.py`, `backend/alembic/versions/0003_rls_supabase.py` (crear), `backend/tests/test_migraciones.py`, `.env.example`.
- **Patrón a seguir:** `0001`/`0002`; el validador `split_cors_origins` de `config.py`.
- **Seguridad:** #1, #4, #13, #20.
- **Qué hacer:**
  1. Agrega `psycopg[binary]` con versión exacta (la estable más reciente que pase `pip-audit`).
  2. `Settings`:
     - `environment: Literal["local", "test", "production"]`.
     - Validador `normalizar_database_url` (`mode="before"`): convierte `postgres://` o `postgresql://` en `postgresql+psycopg://` y agrega `sslmode=require` si la URL es de Postgres y no lo trae.
  3. `0002` según el motor: con `op.get_bind().dialect.name == "sqlite"` se queda el `batch_alter_table` actual; en otro motor usa `op.drop_constraint(..., type_="check")` y `op.create_check_constraint(...)` directos, en `upgrade` y en `downgrade`.
  4. `0003_rls_supabase`: solo en `postgresql`, `ALTER TABLE <t> ENABLE ROW LEVEL SECURITY` (sin políticas) en cada tabla que existe en ese punto, incluidas las de reportes aunque no se usen. El `downgrade` hace `DISABLE`. En SQLite no hace nada. Así la API de datos de Supabase (`anon`/`authenticated`) no expone nada, y el backend, que se conecta como dueño, sigue funcionando.
  5. `test_migracion_ida_y_vuelta_postgres`, con `pytest.mark.skipif` si no está `TEST_POSTGRES_URL`:
     - Upgrade a head.
     - Insertar una actividad `D` (acepta) y una `K` (rechaza con `IntegrityError`).
     - `relrowsecurity = true` en `pg_class` para todas las tablas.
     - Downgrade a base y upgrade otra vez.
  6. `.env.example`: URL de Supabase con datos ficticios y la nota "usar el *session pooler* (IPv4); la conexión directa es IPv6 y Render no la alcanza".
- **Criterio de aceptación:**
  - `pytest -q` pasa en SQLite.
  - Con `docker run --rm -d -e POSTGRES_PASSWORD=prueba -p 55432:5432 postgres:17-alpine` y `TEST_POSTGRES_URL=postgresql://postgres:prueba@localhost:55432/postgres`, `pytest -q tests/test_migraciones.py` pasa.
  - `alembic check` está limpio en los dos motores.
- **Pruebas requeridas:** ida y vuelta en Postgres, restricción A–J y RLS en Postgres, y normalización de URL (Postgres → `+psycopg` con `sslmode=require`; SQLite intacta).

### Tarea 2 — Usuarios, JWT, admins por semillas e interruptor `AUTENTICACION`
- **Archivos:** `backend/pyproject.toml`, `backend/app/config.py`, `backend/app/models/usuarios.py` (crear), `backend/app/models/__init__.py`, `backend/alembic/versions/0004_usuarios.py` (crear), `backend/app/schemas/auth.py` (crear), `backend/app/services/auth.py` (crear), `backend/app/services/semillas.py`, `backend/app/routers/auth.py` (crear), `backend/app/errors.py`, `backend/app/main.py`, `backend/app/routers/config.py`, `backend/app/cli.py` (crear), `backend/tests/test_auth.py` (crear), `backend/tests/test_semillas.py` (crear), `backend/tests/conftest.py`.
- **Patrón a seguir:** modelos de `models/catalogos.py`; `cargar_semillas` (idempotente, en `lifespan`); schemas `extra="forbid"`; `routers/catalogos.py`; errores de dominio de `errors.py`.
- **Seguridad:** #1, #6, #8, #10, #11, #12, #14, #17.
- **Qué hacer:**
  1. Dependencias con versión exacta: `PyJWT` y `argon2-cffi`.
  2. `Settings`:
     - `autenticacion: bool = False`, que lee `AUTENTICACION`. Se queda en false en local, para que `make up` funcione como hoy.
     - `jwt_secreto: SecretStr | None` y `jwt_minutos: int = Field(480, ge=5, le=1440)`.
     - `admins_semilla: Annotated[list[AdminSemilla], NoDecode] = []`, desde el JSON de `ADMINS_SEMILLA`: `[{"correo": "...", "contrasena_hash": "$argon2id$..."}]`. Se usa JSON porque los hashes llevan comas y `$`. Cada hash debe empezar con `$argon2`; si no → `ValueError`, para rechazar una contraseña en claro pegada por error.
     - Si `autenticacion` es true, se exige `jwt_secreto` de al menos 32 caracteres. En `test`, si falta, se genera uno aleatorio.
  3. Modelo `Usuario` (`usuarios`): `id`, `correo` `String(254)` único en minúsculas, `contrasena_hash` `String(255)`, `activo` (por defecto true), `intentos_fallidos` (por defecto 0), `bloqueado_hasta` `DateTime(timezone=True)` nullable y `creado_en` con `server_default=func.now()`. Migración `0004` con RLS en Postgres para `usuarios`.
  4. `services/auth.py`:
     - `hashear` y `verificar` con argon2; `verificar` captura `VerifyMismatchError`.
     - `crear_token(usuario) -> (token, expira_en)`: HS256 con `sub`, `iat` y `exp`.
     - `leer_token(token) -> int`: `algorithms=["HS256"]`, exige `exp` y lanza `NoAutenticadoError` si falla.
  5. **Semillas:** `cargar_usuarios_semilla(session, admins)` en `services/semillas.py`, llamada desde `cargar_semillas`.
     - Crea cada admin cuyo correo no exista (`activo=True`).
     - Si el correo ya existe, no lo toca: no pisa contraseñas ni reactiva cuentas.
     - Es idempotente.
     - No escribe correos ni hashes en logs.
  6. Errores: `NoAutenticadoError` (401, `no_autenticado`), `CredencialesInvalidasError` (401, `credenciales_invalidas`) y `DemasiadosIntentosError` (429, `demasiados_intentos`). Los 401 incluyen `WWW-Authenticate: Bearer`.
  7. `routers/auth.py` (`/api/auth`), incluido siempre:
     - `POST /login` con `LoginEntrada{correo (max 254), contrasena (1–128)}`.
       - Usuario inexistente o inactivo → 401 genérico; verifica contra un hash ficticio para no dar pistas por tiempo de respuesta.
       - Usuario bloqueado → 429.
       - Contraseña incorrecta → suma al contador; al llegar a 5 bloquea 15 minutos y reinicia el contador.
       - Correcto → reinicia el contador y devuelve `{access_token, token_type: "bearer", expira_en}`.
     - `GET /yo` → `{id, correo}`.
  8. Dependencia `usuario_actual` (`HTTPBearer(auto_error=False)`): si `autenticacion` es false, no exige nada (devuelve `None`); si es true, exige un token válido y un usuario activo. En `main.py` se agrega `dependencies=[Depends(usuario_actual)]` a `catalogos`, `exportar` (los dos routers), `importar` y `reportes` (cuando se incluye). `health`, `config` y `auth/login` son públicos.
  9. `/api/config` agrega `autenticacion: bool`.
  10. `cli.py`: `python -m app.cli hash-contrasena` pide la contraseña dos veces con `getpass`, exige al menos 12 caracteres e imprime solo el hash. Nunca la acepta como argumento.
  11. `conftest.py`: el fixture `client` sigue sin autenticación (como hoy). Agrega el fixture `client_con_login` (`autenticacion=True`, usuario de prueba y cabecera Bearer) y `client_anonimo_con_login`.
- **Criterio de aceptación:**
  - `pytest -q` pasa (todas las pruebas actuales sin cambios).
  - Con `autenticacion=True` y sin token, `GET /api/catalogos/colaboradores`, `POST /api/exportar/pdf` y `POST /api/importar` → 401; `/api/health` y `/api/config` → 200.
  - El sexto intento fallido → 429.
  - Un token expirado, firmado con otra clave o con `alg=none` → 401.
  - Un campo extra en el login → 422.
  - `/yo` devuelve exactamente las claves `{"id", "correo"}`.
  - `test_semillas.py`:
    - 2 admins → 2 usuarios, y los dos pueden iniciar sesión.
    - Repetir las semillas no duplica.
    - Un admin existente conserva su contraseña.
    - Un hash sin `$argon2` → `ValidationError`.
    - Sin la variable no se crean usuarios y los catálogos se cargan igual.
- **Pruebas requeridas:** las del criterio, más el desbloqueo pasado el tiempo (reloj parcheado) y la CLI con contraseña corta rechazada.

### Tarea 3 — Reglas de producción, CORS y cabeceras
- **Archivos:** `backend/app/config.py`, `backend/app/main.py`, `backend/tests/test_produccion.py` (crear).
- **Patrón a seguir:** el bloque CORS de `main.py` y los validadores de `Settings`.
- **Seguridad:** #6, #18, #19.
- **Qué hacer:**
  1. Validador: con `environment == "production"` se exige `almacenar is False` (el disco de Render se borra), `autenticacion is True`, `cors_origins` no vacío y `database_url` de Postgres. Si falta algo → `ValueError` con un mensaje claro.
  2. CORS: `allow_origins=settings.cors_origins` (nunca `*`), `allow_credentials=False`, `allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"]`, `allow_headers=["Content-Type", "Authorization"]` y `expose_headers=["Content-Disposition"]`.
  3. En `production`: `docs_url=None` y `openapi_url=None`.
  4. Middleware de cabeceras: `nosniff`, `X-Frame-Options: DENY` y `Referrer-Policy: no-referrer`; HSTS solo en `production`.
- **Criterio de aceptación:**
  - `production` con `ALMACENAR=true`, sin `AUTENTICACION`, sin CORS o con SQLite → `ValidationError` (4 casos).
  - Preflight con un origen permitido → `Access-Control-Allow-Origin` y `Authorization` permitidos; con un origen no permitido → sin la cabecera.
  - `/api/docs` → 404 en producción.
  - `nosniff` presente.
- **Pruebas requeridas:** las del criterio.

### Tarea 4 — Imagen para Render, `render.yaml` y medición de memoria
- **Archivos:** `backend/pyproject.toml`, `backend/Dockerfile`, `docker-compose.yml`, `render.yaml` (crear), `.env.example`.
- **Patrón a seguir:** `Dockerfile` y `docker-compose.yml` actuales.
- **Seguridad:** #1, #2, #20.
- **Qué hacer:**
  1. `pyproject.toml`: `[tool.setuptools.package-data] app = ["plantillas/*", "seeds/*.json"]`.
  2. `Dockerfile`:
     - `CMD` con `alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'`.
     - Conserva la preparación de `/data` (`mkdir` y dueño `app`) para el modo local con `ALMACENAR=true`, sin romper `make up`. Si el `chown` en tiempo de ejecución falla sin `/data` montado, hazlo condicional (`[ -d /data ] && chown …`).
  3. `render.yaml`:
     - Servicio `reportes-servicios-api`, `runtime: docker`, `plan: free`, `dockerContext: ./backend`, `dockerfilePath: ./backend/Dockerfile` y `healthCheckPath: /api/health`.
     - `envVars`:
       - `ENVIRONMENT=production`, `ALMACENAR=false` y `AUTENTICACION=true`.
       - `JWT_SECRETO` con `generateValue: true`.
       - `DATABASE_URL`, `CORS_ORIGINS` y `ADMINS_SEMILLA` con `sync: false`.
       - `JORNADA_SEMANA=8`, `JORNADA_SABADO=5`, `MAX_FOTO_MB=15` y `MAX_EXPORTACION_MB=60`.
  4. `.env.example`: `AUTENTICACION=false`, `JWT_SECRETO=`, `JWT_MINUTOS=480` y `ADMINS_SEMILLA=[]` (con un formato de ejemplo ficticio y cómo generar el hash).
- **Criterio de aceptación:**
  - Imagen: `docker run --rm --memory=512m --memory-swap=512m -e ENVIRONMENT=production -e ALMACENAR=false -e AUTENTICACION=true -e JWT_SECRETO=<32+> -e CORS_ORIGINS=https://ejemplo.vercel.app -e DATABASE_URL=<postgres temporal> -e ADMINS_SEMILLA='[...]' -e PORT=10000 -p 10000:10000 <imagen>` → arranca, migra, `/api/health` 200 y el login con el admin semilla funciona.
  - **Medición:** con 6 días, A–F y **20 fotos sintéticas de 1600 px**, `POST /api/exportar/formato`, `mejorado` y `pdf`, y después `POST /api/importar` con el formato descargado, todos responden 200 sin `oom_kill`. Anota en el reporte el pico de `memory.peak` (cgroup) de cada uno y el tamaño de los archivos.
  - Dentro de la imagen, `python -I -c "import app.services.excel_formato as m; print((m.PLANTILLAS_DIR/'plantilla_formato.xlsx').is_file())"` → `True`.
  - `make up` local sigue funcionando con `ALMACENAR=true` y sin login.
- **Pruebas requeridas:** las del criterio, documentadas con su salida en el reporte.

### Tarea 5 — Frontend: URL de API, sesión y login
- **Archivos:** `frontend/src/api/client.ts`, `frontend/src/api/sesion.ts` (crear), `frontend/src/api/auth.ts` (crear), `frontend/src/vite-env.d.ts`, `frontend/src/pages/Login.tsx` (crear), `frontend/src/App.tsx`, y las pruebas `client.test.ts` y `Login.test.tsx`.
- **Patrón a seguir:** `client.ts` (`apiRequest`, `apiDescarga`, `ApiError`); `pages/Catalogos.tsx` (formulario, `useMutation`, `useAvisos`); pruebas de páginas existentes.
- **Seguridad:** #1, #6, #9, #11, #15.
- **Qué hacer:**
  1. `API_URL = import.meta.env.VITE_API_URL ?? ""`; las peticiones van a `${API_URL}/api${path}`. Vacío en local, así que sigue usando el proxy de nginx.
  2. `sesion.ts`: `obtenerToken`, `guardarToken(token, expiraEn)`, `cerrarSesion` y `alCerrarSesion(cb)`. Se guarda en `sessionStorage` (`sg_sesion`); un token expirado no se usa. Todo con `try/catch`.
  3. `apiRequest`, `apiDescarga` y la importación agregan `Authorization: Bearer` si hay token; un 401 llama a `cerrarSesion()`.
  4. `Login.tsx`:
     - Campos con `autoComplete` `username` y `current-password`.
     - Mensajes según el `code`: `credenciales_invalidas` → "Correo o contraseña incorrectos."; `demasiados_intentos` → "Demasiados intentos. Espera 15 minutos."; error de red → "No se pudo conectar con el servidor."
     - Si tarda más de 3 s: "Conectando con el servidor… (puede tardar hasta un minuto)", porque Render se duerme.
  5. `App.tsx`:
     - Si `/api/config` dice `autenticacion: true`, `RequerirSesion` redirige a `/login`.
     - `alCerrarSesion` → navega a `/login` y hace `queryClient.clear()`. **Antes**, si hay una semana capturada en memoria, pide confirmación con `Confirmar` para no perderla en silencio.
     - La barra lateral muestra el correo y "Cerrar sesión" (solo con autenticación) y quita el texto "Uso local · 127.0.0.1" cuando `almacenar` es false.
     - Si `autenticacion` es false, todo funciona como hoy.
- **Criterio de aceptación:** `test`, `lint`, `format:check` y `build` pasan.
- **Pruebas requeridas:**
  - Prefijo de `VITE_API_URL`.
  - `Authorization` con token y sin él.
  - Un 401 cierra la sesión.
  - Un token expirado no se envía.
  - Con `autenticacion` true y sin sesión → `/login`; con false → sin login.
  - Login correcto, mensaje del 401 y mensaje del 429.

### Tarea 6 — Vercel, guía de despliegue y documentación
- **Archivos:** `frontend/vercel.json` (crear), `frontend/.env.example` (crear), `README.md`, `.agentes/PROYECTO.md`.
- **Patrón a seguir:** las cabeceras de `frontend/nginx.conf`.
- **Seguridad:** #1, #2, #18, #19.
- **Qué hacer:**
  1. `vercel.json`:
     - SPA con `rewrites: [{ "source": "/(.*)", "destination": "/index.html" }]`.
     - `headers` iguales a `nginx.conf` con `connect-src 'self' https://reportes-servicios-api.onrender.com`, `img-src 'self' data: blob:` y HSTS.
  2. `frontend/.env.example`: `VITE_API_URL=https://reportes-servicios-api.onrender.com`.
  3. README, sección "Despliegue", paso a paso:
     1. **Supabase**: crear el proyecto y copiar la URL del *session pooler*.
     2. **Hash del admin**: `docker compose run --rm api python -m app.cli hash-contrasena`.
     3. **Render**: crear desde Blueprint (`render.yaml`) y llenar `DATABASE_URL`, `ADMINS_SEMILLA` y, por ahora, `CORS_ORIGINS`.
     4. **Vercel**: raíz `frontend`, Vite, `npm run build`, salida `dist` y `VITE_API_URL` con la URL real de Render. Si Render asignó otro nombre, ajustar `connect-src` en `vercel.json`.
     5. Poner la URL de Vercel en `CORS_ORIGINS` de Render y reiniciar.
     6. Para agregar un admin, sumarlo a `ADMINS_SEMILLA` y reiniciar.
     7. Límites del plan gratuito: Render se duerme a los 15 minutos (la primera carga tarda cerca de un minuto) y tiene 512 MB (unas 20–40 fotos por semana); Supabase se pausa tras 7 días sin uso.
  4. `PROYECTO.md`:
     - Usuarios: personas autorizadas por internet (producción) o uso local.
     - Stack: Postgres (Supabase) en producción y SQLite en local; Render + Vercel.
     - Autenticación: JWT, argon2, bloqueo y admins por semillas (`AUTENTICACION`).
     - Seguridad base: las medidas 6, 9–12, 18 y 19 aplican en producción.
     - Piezas de referencia: `routers/auth.py`.
- **Criterio de aceptación:**
  - `vercel.json` es JSON válido.
  - La guía no tiene valores reales (solo marcadores).
  - gitleaks limpio.
  - `npm --prefix frontend run build` con `VITE_API_URL=https://ejemplo.onrender.com` funciona.
- **Pruebas requeridas:** n.a. (documentación y configuración).

## Seguridad

| # | Medida | Aplica | Cómo se cumple / prueba |
|---|---|---|---|
| 1 | API keys | sí | `JWT_SECRETO`, `DATABASE_URL` y `ADMINS_SEMILLA` (solo hashes) únicamente en las variables de Render; el frontend solo recibe `VITE_API_URL` (pública). gitleaks. |
| 2 | Secretos fuera de Git | sí | `.env` ignorado; `render.yaml` con `sync: false`/`generateValue`; nada en `seeds/catalogos.json`. |
| 3 | Llave pública para DB | sí | El frontend no recibe llaves de Supabase. Sugerencia para un plan aparte: un rol de BD con privilegios mínimos. |
| 4 | RLS | sí | RLS sin políticas en todas las tablas (0003/0004). Prueba en Postgres. |
| 6 | Autenticación | sí | `usuario_actual` obligatorio en producción (validador). Pruebas de 401. |
| 7 | Acceso a registros | n.a. | No hay registros por usuario; los catálogos son compartidos. |
| 8 | Manipulación de campos | sí | `extra="forbid"` en `LoginEntrada` (y en los schemas existentes). Prueba de campo extra. |
| 9 | Sesión | sí | Bearer en cabecera, `sessionStorage` y expiración de 8 h; sin cookies porque los dominios son distintos. XSS mitigado con CSP estricta. |
| 10 | Contraseñas | sí | argon2; las semillas solo aceptan hashes `$argon2`. |
| 11 | Rate limiting | sí | Bloqueo de 15 minutos tras 5 fallos por cuenta. Prueba del 429. Exportar e importar requieren sesión y tienen tope de MB. |
| 12 | Bots | sí (parcial) | Bloqueo progresivo; sin registro público, así que no hace falta CAPTCHA. |
| 13 | Parametrizar | sí | ORM; SQL estático en migraciones. `rg -n "execute\(f|text\(f" backend` = 0. |
| 14 | Validar inputs | sí | Login con longitudes; el resto ya validado en los planes anteriores. |
| 17 | Datos necesarios | sí | `/yo` sin hash; `/config` con claves exactas. |
| 18 | Headers | sí | Middleware en el backend y `vercel.json` en el frontend. |
| 19 | HTTPS | sí | Render/Vercel con HTTPS, HSTS y `sslmode=require`. |
| 20 | Dependencias | sí | `psycopg`, `PyJWT` y `argon2-cffi` con versión fija; `pip-audit` y `npm audit`. |

n.a.: 5 (no se guardan datos sensibles; los reportes no se guardan), 7, 15 y 16 (sin cambios; ya cubiertos por los planes anteriores).

## Consistencia
- Se reutilizan `Settings` con validadores, `DomainError`, `cargar_semillas`, schemas `extra="forbid"`, `apiRequest`/`apiDescarga`, `useAvisos`/`Confirmar` y las clases CSS.
- **Pieza nueva, justificada:** autenticación (no existía); queda como referencia en `PROYECTO.md`. El interruptor `AUTENTICACION` sigue el mismo patrón que `ALMACENAR`.
- **Dependencias nuevas, autorizadas:** `psycopg[binary]`, `PyJWT` y `argon2-cffi`.

## Verificación final
```bash
git diff agente/modo-sin-almacenar...agente/despliegue-render --stat
docker build -t tania-api-render backend
docker run --rm -w /srv tania-api-render sh -c "ruff check . && ruff format --check . && pytest -q && bandit -r app -ll && pip-audit"
docker run --rm -d --name pg-prueba -e POSTGRES_PASSWORD=prueba -p 55432:5432 postgres:17-alpine
docker run --rm --network host -w /srv -e TEST_POSTGRES_URL=postgresql://postgres:prueba@localhost:55432/postgres tania-api-render pytest -q tests/test_migraciones.py
docker stop pg-prueba
npm --prefix frontend run lint && npm --prefix frontend run format:check
npm --prefix frontend run test && npm --prefix frontend run build
npm --prefix frontend audit --audit-level=high
gitleaks detect --no-git -v
```
Más la medición de memoria de la tarea 4 y `make up` local. No toques `data/`.

## Riesgos
- **Memoria:** el respaldo oculto (fotos en base64) hace más pesados la exportación y la importación; se mide en la tarea 4. Si pasa de unos 450 MB con 20 fotos, la mejora es reducir las fotos a 800 px (plan aparte).
- **Render gratuito se duerme:** la primera petición tarda cerca de un minuto; el login y las descargas lo avisan.
- **Supabase gratuito se pausa** tras 7 días sin uso; se reactiva desde su panel (va en la guía).
- **Pérdida de la semana** si la sesión expira (8 h) o se cierra la pestaña: se mitiga con la confirmación al cerrar sesión, el aviso `beforeunload` y el Excel reabrible.
- **Nombre del servicio en Render:** si no queda `reportes-servicios-api`, hay que ajustar `connect-src` y `VITE_API_URL`.

## Supuestos y preguntas abiertas
- Supuesto: cualquier usuario con sesión puede editar catálogos y exportar (no hay roles).
- Supuesto: en local, `AUTENTICACION=false` por defecto; puedes activarlo en tu `.env` con `ADMINS_SEMILLA` para probar el login.
- Sin preguntas abiertas.
