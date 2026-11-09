---
id: PLAN-20261108-modo-sin-almacenar
estado: aprobado        # borrador | aprobado | en_ejecucion | cerrado
rama: agente/modo-sin-almacenar
rama_base: agente/actividades-dinamicas   # o main si Oscar ya fusionó
stack: fastapi
zona_protegida: no      # sin autenticación nueva, sin migraciones, sin borrar datos
autor: claude
---

# Dos modos del sistema con `ALMACENAR`: guardar reportes o solo descargarlos

## Objetivo
Que el mismo sistema funcione de dos formas según la variable de entorno `ALMACENAR`:
- **`ALMACENAR=true`** (por defecto): como hoy. Reportes, días y fotos se guardan (SQLite y `/data/fotos`).
- **`ALMACENAR=false`**: no se guarda ningún reporte ni foto. Se captura la semana en la pantalla y cada descarga (formato, mejorado o PDF) se genera en memoria con lo que manda el navegador. **Solo los catálogos** siguen guardados.

## Decisiones de Oscar (2026-11-08)
- "Que no se almacene nada, que vayan descargando el que van creando".
- "Deja las dos versiones del sistema y manéjalo con una env, donde almacenar=False".
- En modo sin almacenar, la semana vive solo mientras la pestaña está abierta.
- Uso esperado: unas 20 fotos por semana. Medido: con 20 fotos de 1600 px, el PDF usa 316 MB de pico con un límite de 512 MB.

## Contexto
- `backend/app/config.py`: `Settings` (pydantic-settings) con `database_url`, `environment`, `cors_origins`, jornadas y `max_foto_mb`.
- `backend/app/main.py`: `include_router` de `health`, `catalogos`, `reportes` y `exportar`; `lifespan` con `cargar_semillas`.
- `backend/app/routers/reportes.py`: CRUD de reportes y días, subida, lectura y borrado de fotos en disco; `crear_reporte` calcula las fechas con `date.fromisocalendar`; `LIMITES_FOTOS` (A–J y AD = 4).
- `backend/app/routers/exportar.py`: `GET /api/reportes/{id}/exportar/{tipo}` lee de la BD.
- `backend/app/services/excel_formato.py` (`generar_formato(reporte)`) y `excel_mejorado.py` (`generar_mejorado(reporte)`):
  - Usan `object_session(reporte)` para consultar catálogos.
  - Leen las fotos con `fotos.FOTOS_DIR / Path(foto.archivo).name` y `is_file()`.
  - Usan los atributos `reporte.anio/semana/dias/elaborado_por/revisado_por`, `dia.dia_semana/fecha/observacion/texto_fotos/actividades/herramientas/materiales/fotos`, `actividad.letra/descripcion/asignaciones` y `asignacion.colaborador/horas`.
- `backend/app/services/calculos.py`: `recalcular_horas`, `totales_dia` y `jornada_dia`; trabaja por atributos.
- `backend/app/services/fotos.py`: `procesar_foto` valida con Pillow, re-codifica y **escribe en disco**.
- `backend/app/schemas/reportes.py`: `ReporteCreate` (semana ISO), `DiaWrite`, `ActividadWrite`, `AsignacionWrite`, cantidades, `Letra` y `Espacio`.
- `frontend/src/App.tsx`: rutas `/` (`Reportes`), `/reportes/:id` (`EditorReporte`) y `/catalogos`.
- `frontend/src/pages/EditorReporte.tsx` (637 líneas): consulta y guarda por día; secciones de firmas (`:295`), actividades (`:372`), herramientas y materiales (`:478`), fotos (`:495`), textos del día (`:541`) y verificaciones (`:564`).
- `frontend/src/components/SelectorFotos.tsx`: recibe `Foto[]` (id numérico, `url` del servidor) y llama a `onSubir`/`onEliminar(id: number)`.
- `frontend/nginx.conf`: `client_max_body_size 20m` en `/api/`.

## Alcance
**Dentro:** variable `ALMACENAR`, endpoint de configuración, exportación sin estado, una sola ruta de generación de Excel para los dos modos, editor de semana en memoria, compresión de fotos en el navegador y documentación.

**Fuera de alcance:**
- Despliegue en Render, Vercel o Supabase, inicio de sesión y Postgres. Siguen en los planes descartados `PLAN-20261108-despliegue-nube-parte1/2`; se retoman aparte si Oscar lo pide.
- Migraciones o borrar tablas. En modo sin almacenar las tablas de reportes existen pero no se usan.
- Guardar borradores en el navegador.
- Cambiar el diseño de los Excel, el PDF o el cálculo de horas.
- Reducir las fotos a 800 px (no hace falta para unas 20 fotos; queda como mejora si crece el uso).

## Tareas

### Tarea 1 — Variable `ALMACENAR`, configuración pública y rutas según el modo
- **Archivos:** `backend/app/config.py`, `backend/app/main.py`, `backend/app/routers/config.py` (crear), `backend/tests/test_config.py` (crear), `.env.example`, `docker-compose.yml`.
- **Patrón a seguir:** `routers/health.py` (router público mínimo) y los campos de `Settings`.
- **Seguridad:** #14, #17.
- **Qué hacer:**
  1. `Settings.almacenar: bool = True`, que lee `ALMACENAR` (`true`/`false`, `1`/`0`; pydantic ya lo convierte). También `max_exportacion_mb: int = Field(60, ge=5, le=200)`.
  2. `routers/config.py`: `GET /api/config` → `ConfigRead{almacenar: bool, max_fotos_por_espacio: int}` (4, tomado de `LIMITES_FOTOS["A"]`). Solo esos dos campos.
  3. `main.py`:
     - `include_router(reportes.router)` **solo si** `settings.almacenar`.
     - Dentro de `exportar`, el `GET` actual va a un router aparte (`router_guardado`) que se incluye solo si `almacenar`.
     - El `POST` de la tarea 3 (`router_memoria`) se incluye **siempre**, para probarlo en los dos modos.
     - `config` siempre.
  4. `docker-compose.yml`: `ALMACENAR: ${ALMACENAR:-true}` y `MAX_EXPORTACION_MB: ${MAX_EXPORTACION_MB:-60}` en `api`. `.env.example`: `ALMACENAR=true` con un comentario de lo que hace cada valor.
- **Criterio de aceptación:**
  - Con `ALMACENAR=true`: `GET /api/config` → `{"almacenar": true, "max_fotos_por_espacio": 4}` y `GET /api/reportes` → 200.
  - Con `ALMACENAR=false`: `{"almacenar": false, ...}`, `GET /api/reportes` → 404, `GET /api/reportes/1/exportar/pdf` → 404 y `/api/catalogos/colaboradores` → 200.
  - Construye la app con una función `crear_app(settings)` o usa `get_settings.cache_clear()` + `importlib.reload`, lo que sea más simple sin duplicar `main.py`. Documenta en la prueba cuál se usó.
- **Pruebas requeridas:** los dos modos (rutas presentes y ausentes) y las claves exactas de `/api/config`.

### Tarea 2 — Un solo modelo en memoria para generar los Excel
- **Archivos:** `backend/app/services/reporte_memoria.py` (crear), `backend/app/services/excel_formato.py`, `backend/app/services/excel_mejorado.py`, `backend/app/routers/exportar.py`, `backend/tests/test_excel_formato.py`, `backend/tests/test_exportar.py`.
- **Patrón a seguir:** servicio puro como `services/calculos.py`; las firmas de `generar_formato` y `generar_mejorado`.
- **Seguridad:** #15 (conservar `texto_seguro` y la prueba de fórmula).
- **Qué hacer:**
  1. `reporte_memoria.py` con `@dataclass` (sin ORM) que tengan **los mismos nombres de atributo** que ya leen los Excel y `calculos.py`:
     - `NombreMemoria(nombre)`, para el colaborador, la herramienta, el material y el firmante (más `unidad` en el material).
     - `AsignacionMemoria(colaborador_id, colaborador, horas, horas_manual)`.
     - `ActividadMemoria(letra, descripcion, asignaciones)`.
     - `CantidadMemoria(herramienta | material, cantidad)`, con los campos que use cada exportador.
     - `FotoMemoria(espacio, orden, contenido: bytes)`.
     - `DiaMemoria(dia_semana, fecha, observacion, texto_fotos, actividades, herramientas, materiales, fotos)`.
     - `ReporteMemoria(anio, semana, elaborado_por, revisado_por, dias)`.
  2. `desde_orm(reporte: Reporte) -> ReporteMemoria` (modo guardado): copia los datos y lee los bytes de cada foto desde `fotos.FOTOS_DIR / Path(foto.archivo).name`, omitiendo las que no existan, como hoy.
  3. `generar_formato(reporte: ReporteMemoria, colaboradores, herramientas)` y `generar_mejorado(reporte: ReporteMemoria, colaboradores, herramientas, materiales)`:
     - Reciben los catálogos como parámetros; quita `object_session`.
     - Fotos con `ExcelImage(BytesIO(foto.contenido))`, sin `is_file()`.
     - La función `catalogos_exportacion(session) -> (colaboradores, herramientas, materiales)` concentra las consultas actuales (activos y ordenados para el formato, ordenados para el mejorado; conserva esa diferencia exacta).
  4. El `GET` guardado de `exportar.py` hace `generar_*(desde_orm(reporte), *catalogos)`.
  5. Ajusta las pruebas para pasar por `desde_orm`. **Todas** las comprobaciones actuales se conservan sin cambiar sus `assert`: celdas, fórmulas, bandas A–J, filas ocultas, fotos 1/2/4 sin superponerse y escape de fórmulas.
- **Criterio de aceptación:**
  - `pytest -q` pasa con el mismo número o más de pruebas que antes (42).
  - `rg -n "object_session" backend/app/services` → 0.
  - El Excel del modo guardado sale igual que antes: la prueba compara las celdas clave y el número de imágenes de un reporte A–E con fotos antes y después del cambio.
- **Pruebas requeridas:** las existentes, más `desde_orm` con una foto ausente en disco (se omite sin error).

### Tarea 3 — Exportación sin estado: `POST /api/exportar/{tipo}`
- **Archivos:** `backend/app/schemas/exportar.py` (crear), `backend/app/services/reporte_memoria.py`, `backend/app/services/fotos.py`, `backend/app/routers/exportar.py`, `backend/tests/test_exportar_memoria.py` (crear), `frontend/nginx.conf`.
- **Patrón a seguir:** schemas `extra="forbid"` de `schemas/reportes.py` (hereda de `ReporteCreate` y `DiaWrite`); `subir_foto` (lectura con tope y `procesar_foto`); `_respuesta` de `exportar.py`.
- **Seguridad:** #8, #14, #15, #16, #17.
- **Qué hacer:**
  1. `fotos.py`: separa `normalizar_foto(contenido: bytes, max_mb: int) -> bytes`, con **la misma validación** (tipo real JPEG/PNG/WebP, `verify`, `exif_transpose`, `MAX_LADO`, fondo blanco y JPEG q85), devuelve bytes y no escribe nada. `procesar_foto` pasa a ser `normalizar_foto` + guardar con nombre UUID (modo guardado, mismo comportamiento que hoy).
  2. `schemas/exportar.py`:
     - `FotoExportar{indice: int (ge=0), espacio: Espacio}`.
     - `DiaExportar(DiaWrite)` con `dia_semana: int` (0–5) y `fotos: list[FotoExportar]` (máximo 44), con validador de **4 fotos como máximo por espacio**.
     - `ReporteExportar(ReporteCreate)` con `elaborado_por_id: int | None` (ge=1), `revisado_por_id: int | None` (ge=1) y `dias: list[DiaExportar]` de **exactamente 6** elementos, `dia_semana` 0–5 sin repetir y los `indice` de foto únicos en todo el reporte.
  3. `armar_reporte(datos: ReporteExportar, contenidos: list[bytes], session) -> ReporteMemoria`:
     - Resuelve colaboradores, herramientas, materiales y firmantes con `session.get`. Si falta alguno → `NotFoundError` con los mismos mensajes que `guardar_dia`/`editar_reporte` ("Colaborador no encontrado", etc.).
     - Calcula las fechas como `crear_reporte`.
     - Si `texto_fotos` viene vacío, usa `TEXTO_FOTOS_PREDETERMINADO`.
     - Ordena las actividades por letra y aplica `recalcular_horas(dia, jornada_dia(dia))`.
     - Asigna `contenidos[indice]` a cada foto, con `orden` según su aparición por espacio. Un `indice` fuera de rango → `InvalidInputError("Foto no encontrada en la petición")`.
  4. `router_memoria`: `POST /api/exportar/{tipo}` (`tipo: Literal["formato", "mejorado", "pdf"]`) con `multipart/form-data`:
     - `datos: Annotated[str, Form()]`, validado con `ReporteExportar.model_validate_json`. Un `ValidationError` → 422 con `code="validation_error"` y el formato de error del proyecto.
     - `fotos: Annotated[list[UploadFile], File()] = []`.
     - Lee cada archivo con el tope `max_foto_mb` y la suma con el tope `max_exportacion_mb` → `FileTooLargeError`.
     - `normalizar_foto` para cada una y luego `generar_*` + `generar_pdf` como el `GET`.
     - Mismo nombre de archivo (`CH-RSG-{semana}-{anio}...`) y el mismo `Content-Disposition: attachment`.
     - **No escribe en la BD ni en disco.**
  5. `nginx.conf`: en `location /api/`, `client_max_body_size 60m` (igual al `MAX_EXPORTACION_MB` por defecto).
- **Criterio de aceptación:**
  - `test_exportar_memoria.py` pasa:
    - 6 días, A–F y 2 fotos sintéticas (Pillow en memoria) en A → `formato` 200 con 2 imágenes en el renglón A.
    - `mejorado` 200.
    - `pdf` empieza con `%PDF`.
    - 5 fotos en un espacio → 422.
    - Un `.exe` renombrado a `.jpg` → 422 `invalid_file`.
    - Colaborador inexistente → 404.
    - 5 días → 422.
    - Un campo extra en `datos` → 422.
    - `max_exportacion_mb` parcheado a 1 → 413.
    - Antes y después de exportar, el conteo de `reportes` y `fotos` en la BD **no cambia** y no aparecen archivos nuevos en `FOTOS_DIR` (parcheado a `tmp_path`).
  - Funciona igual con `ALMACENAR=true` y con `false`.
- **Pruebas requeridas:** las del criterio.

### Tarea 4 — Frontend: modo según `/api/config`, cliente de descarga y rutas
- **Archivos:** `frontend/src/api/config.ts` (crear), `frontend/src/api/client.ts`, `frontend/src/App.tsx`, `frontend/src/api/client.test.ts` (crear o ampliar), `frontend/src/App.test.tsx` (crear).
- **Patrón a seguir:** `api/catalogos.ts` (llamadas con `apiRequest`); `pages/Reportes.test.tsx` (montaje con QueryClient y `fetch` simulado).
- **Seguridad:** #15.
- **Qué hacer:**
  1. `config.ts`: `verConfig()` → `GET /config`; `useConfig()` con `useQuery(["config"], verConfig, { staleTime: Infinity })`.
  2. `client.ts`: `apiDescarga(path, body: FormData): Promise<{blob, nombre?}>` hace POST, aplica el mismo manejo de `ApiError` y lee el nombre de `Content-Disposition`.
  3. `App.tsx`:
     - Mientras carga la configuración, muestra "Cargando…"; si falla, muestra un error con "Reintentar".
     - Con `almacenar=true`, las rutas son las de hoy.
     - Con `almacenar=false`, `/` → `EditorSemana` (tarea 6) y `/catalogos`. `/reportes/:id` redirige a `/`. En la barra lateral, "Reportes" pasa a decir "Nuevo reporte".
- **Criterio de aceptación:** `npm --prefix frontend run test` y `build` pasan.
- **Pruebas requeridas:**
  - Con `/config` simulado en `true` se ve la lista de reportes; en `false`, el editor de semana.
  - `apiDescarga` extrae `CH-RSG-45-2026.xlsx` del encabezado y propaga el `detail` de un 413.

### Tarea 5 — Extraer el formulario del día para reutilizarlo en los dos modos
- **Archivos:** `frontend/src/components/FormularioDia.tsx` (crear), `frontend/src/components/SelectorFotos.tsx`, `frontend/src/pages/EditorReporte.tsx`, `frontend/src/components/EditorComponents.test.tsx`.
- **Patrón a seguir:** los componentes existentes (`SelectorColaboradores`, `TablaCantidades`) con props controladas `valor`/`onChange`.
- **Seguridad:** #15.
- **Qué hacer:**
  1. `SelectorFotos` acepta `fotos: FotoVista[]` con `interface FotoVista { id: string | number; espacio: Letra | "AD"; url: string; nombre_original: string }`, y `onEliminar(id: string | number)`. `Foto` del API ya cumple esa forma.
  2. `FormularioDia` recibe por props:
     - `dia: DiaInput`, `onChange(dia)`, `jornada`, `catalogos` (colaboradores, herramientas y materiales).
     - `fotos: FotoVista[]`, `subiendoEspacio?`, `onSubirFotos(espacio, archivos)`, `onEliminarFoto(id)`.
     - `actividadesAbiertas` + `setActividadesAbiertas`.

     Renderiza **exactamente** las secciones que hoy están en `EditorReporte.tsx` (actividades con agregar y quitar, herramientas y materiales, fotos, textos del día y verificaciones) y expone `hayErrores` por `onVerificacion?(hayErrores)`. La pestaña de días, el encabezado, las firmas y las descargas se quedan en cada página.
  3. `EditorReporte.tsx` (modo guardado) usa `FormularioDia` **sin cambiar su comportamiento**: sigue con guardar por día, subir y borrar fotos en el servidor, y los avisos.
- **Criterio de aceptación:**
  - Todas las pruebas actuales del editor pasan sin cambiar sus `assert`.
  - `EditorReporte.tsx` baja a menos de 350 líneas.
  - `lint`, `format:check` y `build` en verde.
- **Pruebas requeridas:** las existentes, más una de `FormularioDia` (agregar actividad y avisar el cambio por `onChange`).

### Tarea 6 — Editor de semana en memoria con descargas por POST
- **Archivos:** `frontend/src/semana.ts` (crear), `frontend/src/semana.test.ts` (crear), `frontend/src/pages/EditorSemana.tsx` (crear), `frontend/src/pages/EditorSemana.test.tsx` (crear), `frontend/src/components/BotonDescarga.tsx` (crear) y su prueba.
- **Patrón a seguir:** `actividades.ts`/`calculos.ts` (funciones puras con prueba); el encabezado, pestañas y firmas de `EditorReporte.tsx`; `useAvisos`/`Confirmar`.
- **Seguridad:** #14 (UX), #15, #16 (comprimir no reemplaza la validación del backend).
- **Qué hacer:**
  1. `semana.ts`:
     - Tipos `FotoLocal{id: string; espacio; archivo: Blob; url: string; nombre_original: string}`, `DiaLocal = DiaInput & {dia_semana: number; fecha: string; fotos: FotoLocal[]}` y `SemanaLocal{anio; semana; elaborado_por_id: number | null; revisado_por_id: number | null; dias: DiaLocal[]}`.
     - `semanaISO(fecha: Date) -> {anio, semana}`.
     - `crearSemana(anio, semana)`: 6 días de lunes a sábado, `actividades = armarActividades([])` y `texto_fotos = "Fotos antes y después de la actividad realizada"`.
     - `armarFormData(semana): FormData`: el JSON `datos` tiene la forma exacta de `ReporteExportar`. Filtra las actividades vacías igual que `guardar` en el editor y usa `serializarDia`. Los blobs se agregan a `fotos` en orden con `indice` correlativo.
     - `comprimirFoto(file): Promise<Blob>`: `createImageBitmap` + `canvas`, lado máximo 1600 px, `toBlob("image/jpeg", 0.82)`. Si falla, devuelve el archivo original.
  2. `BotonDescarga({tipo, etiqueta, obtenerDatos: () => FormData, deshabilitado})`:
     - Llama a `apiDescarga(`/exportar/${tipo}`, …)`, crea un `<a download>` temporal con el nombre del servidor y revoca la URL al terminar.
     - "Generando…" mientras trabaja; errores con `useAvisos`, usando el `detail`.
  3. `EditorSemana.tsx`:
     - Selector de año y semana (por defecto la semana ISO de hoy) y "Nueva semana", que pide confirmación con `Confirmar` si hay datos.
     - Pestañas de días, firmas (selects de firmantes) y `FormularioDia` para el día activo.
     - Fotos: al subir, comprime, crea `URL.createObjectURL` y respeta el máximo de 4 por espacio con el mismo aviso de exceso. Al eliminar, quita la foto y revoca la URL. Al desmontar o con "Nueva semana", revoca todas.
     - Tres `BotonDescarga` (formato, mejorado y PDF), deshabilitados si alguna verificación del día activo tiene errores, igual que hoy "Guardar".
     - Texto fijo: "Este reporte no se guarda: descarga los archivos antes de cerrar la pestaña." Aviso `beforeunload` si hay cualquier dato.
- **Criterio de aceptación:**
  - `test`, `lint`, `format:check` y `build` pasan.
  - Con `ALMACENAR=false` y `make up`: capturar el lunes y el martes con 3 fotos, descargar los tres archivos y abrirlos (el Excel trae las fotos y el PDF abre).
  - `SELECT count(*) FROM reportes` y la carpeta `data/fotos` quedan **sin cambios**: se comprueba sobre el conteo, sin abrir datos personales.
- **Pruebas requeridas:**
  - `crearSemana(2026, 45)` → del 2026-11-02 al 2026-11-07.
  - `armarFormData` (forma exacta, filtrado, índices).
  - Conservar el lunes al cambiar de día y volver.
  - Quinta foto → aviso.
  - "Nueva semana" con datos pide confirmación.
  - `BotonDescarga` usa el nombre del servidor y avisa del error.

### Tarea 7 — Documentación
- **Archivos:** `README.md`, `.agentes/PROYECTO.md`.
- **Patrón a seguir:** secciones actuales del README.
- **Seguridad:** n.a.
- **Qué hacer:**
  - README, sección "Modos":
    - `ALMACENAR=true` guarda; `false` solo descarga y la semana se pierde al cerrar la pestaña.
    - Cómo cambiar el modo (`.env` + `make up`).
    - Los catálogos se guardan en los dos modos.
    - Límite `MAX_EXPORTACION_MB`.
    - Memoria medida: unas 20 fotos de 1600 px → ~316 MB de pico.
  - `PROYECTO.md`: en "Qué es" y "Alcance", los dos modos; en "Piezas de referencia", `services/reporte_memoria.py` (generación de Excel) y `components/FormularioDia.tsx`.
- **Criterio de aceptación:** documentación coherente con el código; gitleaks limpio.
- **Pruebas requeridas:** n.a.

## Seguridad

| # | Medida | Aplica | Cómo se cumple / prueba |
|---|---|---|---|
| 8 | Bloquear manipulación de campos | sí | `ReporteExportar` con `extra="forbid"` (heredado). Prueba de campo extra → 422. |
| 13 | Parametrizar queries | sí (sin cambio) | Solo ORM (`session.get`, `select`). `rg -n "execute\(f|text\(f" backend/app` = 0. |
| 14 | Validar inputs | sí | 6 días, letras A–J, 4 fotos por espacio, índices válidos, topes por foto y en total. Pruebas de 422/413. |
| 15 | Sanitizar contenido | sí | `texto_seguro` en los Excel (las pruebas de fórmula se conservan); React sin HTML crudo (`rg dangerouslySetInnerHTML` = 0). |
| 16 | Restringir archivos | sí | `normalizar_foto` verifica el tipo real con Pillow, re-codifica a JPEG y limita el tamaño; en modo memoria nada se escribe a disco. Prueba del `.exe`. |
| 17 | Devolver datos necesarios | sí | `/api/config` solo con `almacenar` y `max_fotos_por_espacio` (prueba de claves exactas); exportar solo devuelve el archivo. |
| 20 | Escanear dependencias | sí | Sin dependencias nuevas; `pip-audit` y `npm audit --audit-level=high`. |

n.a.:
- 1–3: sin secretos nuevos; `ALMACENAR` no es secreto.
- 4–7, 9–12: sin autenticación; la app sigue siendo local en 127.0.0.1 según `PROYECTO.md`. Si se despliega en internet, aplica el plan de despliegue con login.
- 5: no se guardan datos sensibles nuevos.
- 18 y 19: sin cambios de cabeceras; solo cambia `client_max_body_size` en nginx.

## Consistencia
- Se reutilizan `Settings`, los schemas `*Write` y `ReporteCreate`, `calculos.py`, `texto_seguro`, el formato de errores, `apiRequest`/`ApiError`, React Query, `useAvisos`/`Confirmar`, `actividades.ts`, `verificaciones.ts` y los componentes de captura.
- **Sin dos formas de lo mismo:** los dos modos generan los Excel por un solo camino (`ReporteMemoria`) y comparten `FormularioDia`. El modo guardado solo agrega `desde_orm`.
- Sin dependencias nuevas.

## Verificación final
```bash
git diff agente/actividades-dinamicas...agente/modo-sin-almacenar --stat
docker build -t tania-api-modos backend
docker run --rm -w /srv tania-api-modos sh -c "ruff check . && ruff format --check . && pytest -q && alembic upgrade head && alembic check && bandit -r app -ll && pip-audit"
npm --prefix frontend run lint && npm --prefix frontend run format:check
npm --prefix frontend run test && npm --prefix frontend run build
npm --prefix frontend audit --audit-level=high
gitleaks detect --no-git -v
```
Prueba manual en los dos modos con `make up`: primero `ALMACENAR=true` (todo como hoy) y después `ALMACENAR=false` (tarea 6). No borres ni modifiques `data/`; en modo `false` solo se comprueba que no cambie.

## Riesgos
- **Regresión del modo guardado** por el refactor de los Excel (tarea 2) y del editor (tarea 5). Se mitiga conservando todas las pruebas y sus `assert`, y probando `make up` con `ALMACENAR=true`.
- **Pérdida de la semana** en modo sin almacenar si se cierra la pestaña (decisión de Oscar). Se mitiga con el aviso `beforeunload` y el texto fijo.
- **Muchas fotos:** con más de unas 40 fotos de 1600 px, el PDF puede no caber en 512 MB (medido: 84 fotos fallan). Para uso local no aplica; para Render, la mejora es reducir a 800 px (plan aparte).
- **Cada descarga vuelve a subir las fotos:** aceptable con unas 20 fotos; las fotos comprimidas en el navegador pesan unos 300 KB cada una.

## Supuestos y preguntas abiertas
- Supuesto: `ALMACENAR` es **true por defecto**, para que tu instalación local siga como hoy.
- Supuesto: el modo se decide al arrancar el backend (cambiarlo requiere reiniciar), y el frontend se adapta solo leyendo `/api/config`, con una sola versión compilada.
- Sin preguntas abiertas.

## Iteración 1
Origen: el bloqueo del reporte (la tarea 5 agotó 3 intentos con las correcciones aplicadas pero sin verificar). Oscar autoriza continuar.

- **Tarea 5 (cerrar):** verifica las correcciones que ya están en el árbol de trabajo (`FormularioDia.tsx`, `SelectorFotos.tsx`, `EditorReporte.tsx`, `actividades.ts`, `verificaciones.ts` y `EditorComponents.test.tsx`) con `npm --prefix frontend run test`, `lint`, `format:check` y `build`. Si pasan, haz el commit de la tarea 5. Tienes **3 intentos nuevos** para esta tarea. El criterio de aceptación no cambia: el comportamiento del modo guardado es idéntico y `EditorReporte.tsx` queda por debajo de 350 líneas.
- **Tareas 6 y 7:** ejecútalas como dice el plan, con 3 intentos cada una.
- **Git:** solo `git add` y `git commit` locales en `agente/modo-sin-almacenar`. Prohibido `push`, `pull`, `fetch`, `merge` a otras ramas, `gh` o cualquier acción contra GitHub.
- No toques `data/`, `data.antes-actividades/` ni el worktree `../Proyecto_Tania-claude`.
- Actualiza el mismo reporte (`REPORTE-20261108-modo-sin-almacenar.md`, con `iteracion: 1`).
