---
id: PLAN-20261105-reportes-servicios
estado: aprobado
rama: agente/reportes-servicios
stack: fastapi + react
zona_protegida: no
autor: claude
---

# Plataforma de reportes de servicios generales

## Objetivo
Web local (React + FastAPI en Docker) para capturar con selectores el reporte semanal y descargar tres archivos: el Excel con el formato actual, un Excel mejorado y un PDF mejorado generado desde ese Excel. Debe quedar sencillo: el proyecto no crecerá.

## Contexto
- **No abras `CH-RSG-*.xlsx`.** Contiene datos reales. Todo lo necesario ya está en `.agentes/insumos/`:
  - `plantilla_formato.xlsx`: hojas `base_actividades` (día con actividades), `base_sin_actividades` (feriado o día sin actividades) y `Datos`, ya limpias y con estilos, combinaciones y fórmulas.
  - `logo.png`, `mapa.png`, `catalogos.json` (colaboradores, herramientas, materiales, firmantes).
- Molde de configuración y estilo: `~/proyectos/Asistencia` (solo lectura; no copies sus datos ni su `.env`). Toma de ahí `backend/Dockerfile`, `backend/app/{config,db,errors,main}.py`, `backend/alembic/`, `frontend/Dockerfile`, `frontend/nginx.conf`, configs de eslint/prettier/tsconfig/vite, `Makefile`, `frontend/src/styles.css`.
- Estructura, stack y convenciones: `.agentes/PROYECTO.md`.

## Alcance
**Dentro:** catálogos con CRUD, captura de reportes por semana, cálculo automático de horas, fotos, Excel formato actual, Excel mejorado, PDF mejorado, Docker.

**Fuera de alcance:** cuentas o login, multiusuario, Postgres, roles, dashboards, envío por correo, importar el Excel existente, marcas sobre el mapa (se harán después; el mapa va como imagen fija), actividad D, migrar reportes anteriores, despliegue en internet.

## Reglas de negocio
- Un reporte es una semana ISO: `anio` + `semana`, únicos. Código: `CH-RSG-{semana}-{anio}` (semana sin relleno). Al crearlo se generan 6 días, de lunes a sábado, con su fecha.
- Cada día tiene hasta 3 actividades: letras `A`, `B`, `C`.
- Jornada: 8 horas de lunes a viernes y 5 el sábado (`JORNADA_SEMANA`, `JORNADA_SABADO` en settings).
- **Horas automáticas:** al asignar un colaborador a actividades del día, sus horas se reparten en partes iguales entre sus actividades de ese día, hasta sumar la jornada. Oscar puede sobrescribir las horas de una asignación (`horas_manual=true`), y entonces el reparto automático ya no toca esa fila: las demás filas del colaborador se reparten el resto, nunca por debajo de 0.
- Totales, en `services/calculos.py`: `personas` = asignaciones de la actividad; `horas_hombre` = suma de sus horas; total del día y total de semana = sumas; `numero_actividades` del día = actividades con al menos una persona. Si un colaborador supera la jornada, la respuesta incluye una advertencia, pero se puede guardar.
- Fotos por espacio: `A` máx. 2, `B` máx. 4, `C` máx. 2, `AD` (antes y después) máx. 4. Cada foto se guarda como JPEG de máximo 1600 px de lado.
- El formato actual no lleva materiales: solo los lleva la versión mejorada. Es decisión de diseño para que ese Excel siga idéntico.

## Tareas

### Tarea 1 — Esqueleto y Docker
- **Archivos:** `docker-compose.yml`, `Makefile`, `.env.example`, `README.md`, `backend/*`, `frontend/*`, `backend/app/routers/health.py`, `backend/tests/test_health.py`.
- **Patrón a seguir:** los archivos del molde de Asistencia indicados en Contexto.
- **Seguridad:** #1, #2, #18, #20.
- **Qué hacer:** compose con `api` y `web`, sin `db`. `web` publica `127.0.0.1:8090:80`; nginx sirve el build y envía `/api/` a `api:8000`, con `client_max_body_size 20m`. `api` monta `./data:/data`. Dockerfile de `api`: agrega `libreoffice-calc`, `fonts-liberation`, `fonts-crosextra-carlito` por apt y arranca con `alembic upgrade head` seguido de uvicorn. `data/` debe ser escribible por el usuario `app`. Copia insumos: `plantilla_formato.xlsx`, `logo.png`, `mapa.png` a `backend/app/plantillas/` y `catalogos.json` a `backend/app/seeds/`. El `Makefile` conserva los objetivos `up down logs lint test audit check`.
- **Criterio de aceptación:** `make up` levanta y `curl http://127.0.0.1:8090/api/health` responde 200.
- **Pruebas requeridas:** health.

### Tarea 2 — Catálogos y carga inicial
- **Archivos:** `backend/app/models/*`, `backend/alembic/versions/*`, `backend/app/schemas/catalogos.py`, `backend/app/routers/catalogos.py`, `backend/app/services/semillas.py`, `backend/tests/test_catalogos.py`.
- **Patrón a seguir:** `~/proyectos/Asistencia/backend/app/routers/people.py` y `models/person.py`.
- **Seguridad:** #8, #13, #14, #17.
- **Qué hacer:** modelos y migración inicial con todas las tablas:
  - `colaboradores(id, nombre, orden, activo)`, `herramientas(id, nombre, orden, activo)`, `materiales(id, nombre, unidad, orden, activo)`, `firmantes(id, nombre, tipo['elabora'|'revisa'], activo)`.
  - `reportes(id, anio, semana, elaborado_por_id, revisado_por_id)`, único `(anio, semana)`.
  - `dias(id, reporte_id, dia_semana 0..5, fecha, observacion, texto_fotos)`.
  - `actividades(id, dia_id, letra, descripcion)`, único `(dia_id, letra)`.
  - `asignaciones(id, actividad_id, colaborador_id, horas, horas_manual)`, único `(actividad_id, colaborador_id)`.
  - `dia_herramientas(dia_id, herramienta_id, cantidad)`, `dia_materiales(dia_id, material_id, cantidad)`.
  - `fotos(id, dia_id, espacio, orden, archivo, nombre_original)`.
  CRUD genérico `GET/POST /api/catalogos/{tipo}`, `PATCH/DELETE /api/catalogos/{tipo}/{id}` con `tipo` en `colaboradores|herramientas|materiales|firmantes`; DELETE pone `activo=false`; `GET` acepta `?incluir_inactivos=true`. Al arrancar, `cargar_semillas()` inserta `seeds/catalogos.json` solo si el catálogo está vacío, conservando el orden del archivo y los nombres exactos.
- **Criterio de aceptación:** tras `make up`, `/api/catalogos/colaboradores` devuelve 13 filas, `herramientas` 14, `materiales` 11 y `firmantes` 2; reiniciar no duplica.
- **Pruebas requeridas:** crear, editar, desactivar, tipo inválido 404, nombre vacío 422, semillas idempotentes. Con nombres de `faker`.

### Tarea 3 — API de reportes, horas y fotos
- **Archivos:** `backend/app/services/calculos.py`, `backend/app/services/fotos.py`, `backend/app/schemas/reportes.py`, `backend/app/routers/reportes.py`, `backend/tests/test_calculos.py`, `backend/tests/test_reportes.py`.
- **Patrón a seguir:** `backend/app/routers/catalogos.py` (Tarea 2) y `~/proyectos/Asistencia/backend/app/services/attendance_rules.py`.
- **Seguridad:** #7, #8, #14, #16, #17.
- **Qué hacer:**
  - `GET/POST /api/reportes`, `GET/PATCH/DELETE /api/reportes/{id}` (POST con `anio`, `semana`; 409 `reporte_duplicado`).
  - `GET /api/reportes/{id}/dias/{dia_semana}` y `PUT` del mismo recurso, que reemplaza en una transacción observación, `texto_fotos`, actividades, asignaciones y cantidades. Devuelve el día con horas recalculadas, totales y `advertencias`.
  - `POST /api/reportes/{id}/dias/{dia_semana}/fotos` (multipart: `archivo`, `espacio`), `GET /api/fotos/{id}/archivo`, `DELETE /api/fotos/{id}`.
  - Fotos: acepta JPEG, PNG y WebP por contenido real con Pillow, máximo `MAX_FOTO_MB=15`; 422 `espacio_lleno` al superar el límite; aplica rotación EXIF, reduce a 1600 px, guarda JPEG calidad 85 sin metadatos en `/data/fotos/{uuid}.jpg`.
- **Criterio de aceptación:** un colaborador en A y B el lunes queda con 4 + 4 horas; A con 1 persona y B con 5 personas da el total correcto.
- **Pruebas requeridas:** reparto automático, sobrescritura manual, sábado de 5 horas, advertencia por exceso, reporte duplicado, foto no imagen 422, espacio lleno 422, archivo mayor al máximo 413.

### Tarea 4 — Excel con el formato actual
- **Archivos:** `backend/app/services/excel_formato.py`, `backend/tests/test_excel_formato.py`.
- **Patrón a seguir:** `~/proyectos/Asistencia/backend/app/services/` (generación de libro de reportes).
- **Seguridad:** #14, #16.
- **Qué hacer:** `generar_formato(reporte) -> bytes`. Carga la plantilla y crea con `copy_worksheet` una hoja por día, con títulos exactos `Lunes, Martes, Miercoles, Jueves, Viernes, Sabado`, y deja `Datos` al final; borra las bases. Usa `base_actividades` si el día tiene actividades y `base_sin_actividades` si no. Define en cada hoja `print_area` (`A1:T58` o `A1:T54`).
  - Comunes: `C6` fecha, `I6` semana; `B10:B22` colaboradores activos por `orden` (máx. 13); `H` las letras del colaborador separadas por `, `; `M10:O10` ya tienen A, B, C.
  - `M11:O11` fórmula `=COUNTIF($H$10:$H$22,"*"&M$10&"*")`. `M13:O13` valor `horas_hombre/personas` (jornada si no hay personas). Conserva las fórmulas `M15:O15`, `M17`, `M19:O19` de la plantilla.
  - `Q10:Q23` cantidades y `R10:R23` nombres de las 14 primeras herramientas activas por `orden`; 0 si no se usó.
  - `base_actividades`: `D26`, `D27`, `D29` descripciones de A, B, C; `D30` `texto_fotos`; `A52` observación; `F57` elabora; `R57` revisa.
  - `base_sin_actividades`: `A48` observación; `F53`, `R53`.
  - Fotos en `base_actividades`, columnas izquierda `N` a `Q` y derecha `R` a `T`: A en fila 26, B en 27 y 28, C en 29, AD en 30 y 31. Se llenan izquierda, derecha, siguiente fila. Calcula el recuadro con anchos y altos reales y usa `OneCellAnchor`, conservando proporción, centrada y sin salirse.
  - Logo: `TwoCellAnchor` de columna índice 17, fila 0, a columna 18 con `colOff=779318`, fila 3 con `rowOff=269733`.
  - Mapa: `TwoCellAnchor` de columna 9 `colOff=484907`, a columna 17 `colOff=744681`; filas índice 34 `rowOff=154376` a 35 `rowOff=3661929` en `base_actividades`, y 30 a 31 con los mismos offsets en `base_sin_actividades`.
  - `Datos`: `E8:J8` `=+Lunes!M19+Lunes!N19+Lunes!O19` y equivalentes por día; `E9:J9` `=+Lunes!M17` y equivalentes. `K8` y `K9` se quedan.
- **Criterio de aceptación:** el libro abre sin errores, tiene 7 hojas y LibreOffice no deja ningún `#REF!` ni `#NAME?` al recalcular.
- **Pruebas requeridas:** valores por celda, `A, B` cuenta en ambas actividades, `H` con letra correcta, día feriado usa la otra base, `Datos` suma lo esperado tras convertir con `soffice --headless --convert-to xlsx`.

### Tarea 5 — Excel mejorado y PDF mejorado
- **Archivos:** `backend/app/services/excel_mejorado.py`, `backend/app/services/pdf.py`, `backend/app/routers/exportar.py`, `backend/tests/test_exportar.py`.
- **Patrón a seguir:** `backend/app/services/excel_formato.py`.
- **Seguridad:** #14, #15, #17.
- **Qué hacer:** `generar_mejorado(reporte) -> bytes` con fuente Arial, paleta verde del logo (`#2DB34A`, tablas con encabezado verde oscuro y filas alternas), tamaño carta vertical, `fitToWidth=1`, `fitToHeight=0`, sin cuadrícula y márgenes de 0.4":
  - Hoja `Resumen`: logo, título, semana y fechas; bloque de 4 indicadores (horas-hombre, actividades, días trabajados, personas); tabla por día (actividades, personas, horas-hombre); tabla colaborador por día con horas y total; herramientas y materiales usados en la semana con cantidad total.
  - Una hoja por cada día con actividades, en formato de lectura: encabezado con fecha; tabla de actividades (letra, descripción, personas, horas-hombre); tabla de colaboradores (nombre, actividad, horas); herramientas y materiales solo con cantidad mayor que 0, con unidad; fotos en cuadrícula de 2 columnas con título por espacio; mapa; observación; firmas.
  - Los días sin actividades aparecen en `Resumen` con su observación, sin hoja propia.
  - Totales con fórmulas de Excel donde sea una suma de la misma hoja.
  `generar_pdf(xlsx: bytes) -> bytes`: guarda en un directorio temporal, corre `soffice --headless --convert-to pdf` con `subprocess.run` en forma de lista, sin `shell`, con `timeout=120` y `-env:UserInstallation` en el temporal. Si falla, error 500 con código `pdf_error`.
  Endpoints `GET /api/reportes/{id}/exportar/formato`, `/mejorado` y `/pdf`, con `Content-Disposition`: `CH-RSG-38-2026.xlsx`, `CH-RSG-38-2026_mejorado.xlsx`, `CH-RSG-38-2026_mejorado.pdf`.
- **Criterio de aceptación:** las tres descargas funcionan en el contenedor; el PDF empieza por `%PDF`; ninguna tabla queda cortada a lo ancho.
- **Pruebas requeridas:** nombres de archivo, hojas esperadas, materiales presentes solo en el mejorado, día sin actividades, 404 de reporte inexistente, PDF no vacío.

### Tarea 6 — Interfaz: catálogos y reportes
- **Archivos:** `frontend/src/App.tsx`, `frontend/src/api/*`, `frontend/src/pages/Catalogos.tsx`, `frontend/src/pages/Reportes.tsx`, sus pruebas.
- **Patrón a seguir:** `~/proyectos/Asistencia/frontend/src` (estructura, TanStack Query, `styles.css`).
- **Seguridad:** #15.
- **Qué hacer:** rutas `/` (reportes), `/reportes/:id` (editor), `/catalogos`.
  - Catálogos: pestañas Colaboradores, Herramientas, Materiales y Firmantes; tabla con agregar, editar en línea y desactivar. Materiales incluye `unidad`.
  - Reportes: lista con semana, fechas, horas totales y botones de descarga; formulario con año y semana, por defecto la semana actual; elimina con confirmación.
- **Criterio de aceptación:** se puede agregar un material y aparece en el editor sin recargar.
- **Pruebas requeridas:** render de catálogos, agregar, error de API visible.

### Tarea 7 — Interfaz: editor del reporte
- **Archivos:** `frontend/src/pages/EditorReporte.tsx`, `frontend/src/components/{SelectorColaboradores,TablaCantidades,SelectorFotos}.tsx`, sus pruebas.
- **Patrón a seguir:** `frontend/src/pages/Catalogos.tsx` (Tarea 6).
- **Seguridad:** #15, #16.
- **Qué hacer:** arriba, selectores de elabora y revisa y las 3 descargas. Pestañas de lunes a sábado, cada una con:
  - Actividades A, B, C: descripción y `SelectorColaboradores` (multiselección con chips). Las horas se muestran por persona y se pueden editar; muestra personas y horas-hombre.
  - `TablaCantidades` para herramientas y otra para materiales: selector del catálogo activo, cantidad y unidad cuando aplique; se agregan y quitan filas.
  - `SelectorFotos`, por espacio (A, B, C, Antes y después): elegir archivos, vista previa, eliminar, y contador `2/4`.
  - Observación, texto de fotos y panel de totales con advertencias.
  - Botón Guardar y aviso si hay cambios sin guardar al cambiar de pestaña.
- **Criterio de aceptación:** en el navegador se captura un día completo, se guarda, y las horas y descargas reflejan lo capturado.
- **Pruebas requeridas:** selección de colaborador, agregar material con cantidad, contador de fotos.

## Seguridad
| # | Medida | Aplica | Cómo se cumple |
|---|---|---|---|
| 1, 2 | Secretos | sí | `.env` ignorado, `.env.example`, `CH-RSG-*.xlsx` ignorado |
| 7 | Acceso a registros | sí | 404 si el id no existe; la foto debe pertenecer al día |
| 8 | Campos | sí | Schemas de entrada con lista blanca |
| 13 | Queries | sí | Solo ORM |
| 14 | Inputs | sí | Pydantic: rangos, longitudes, enums |
| 15 | Contenido | sí | Sin `dangerouslySetInnerHTML`; `<img>` solo a la API |
| 16 | Archivos | sí | Contenido real con Pillow, tamaño máximo, nombre UUID, reconversión a JPEG |
| 17 | Datos de salida | sí | `response_model` explícito |
| 18 | Headers | sí | nginx como Asistencia |
| 20 | Dependencias | sí | Versiones fijadas, `pip-audit`, `npm audit` |

n.a.: 3, 4, 5, 6, 9, 10, 11, 12, 19 (uso local, sin cuentas ni secretos; el perfil personal lo permite y la app solo escucha en 127.0.0.1).

## Consistencia
- Se reutilizan los patrones de Asistencia. Nuevo respecto a Asistencia: SQLite, Pillow y LibreOffice, ya definidos en `PROYECTO.md`.

## Verificación final
```bash
make up && curl -f http://127.0.0.1:8090/api/health
make check
curl -fOJ http://127.0.0.1:8090/api/reportes/1/exportar/pdf   # con un reporte de prueba sintético
```

## Riesgos
- LibreOffice aumenta el tamaño de la imagen: es aceptado.
- Fuente Calibri: el PDF no la usa porque el mejorado es Arial; `fonts-liberation` cubre el render.
- Si se agregan más de 13 colaboradores o 14 herramientas activas, el formato actual solo muestra los primeros; el mejorado los muestra todos. La UI no tiene que avisarlo en esta versión.

## Iteración 1
Origen: `.agentes/revisiones/REVISION-20261105-reportes-servicios.md`. Ejecuta solo estas tareas, con un commit por tarea. Prueba siempre con datos sintéticos y, al terminar, borra por la API todo reporte de prueba de la base local, incluido `CH-RSG-52-2025`: la lista de reportes debe quedar vacía.

### Tarea I1 — Guardar un día más de una vez
- **Archivos:** `backend/app/routers/reportes.py`, `backend/tests/test_reportes.py`.
- **Problema:** `PUT /api/reportes/{id}/dias/{dia}` responde 500 la segunda vez. En `guardar_dia`, `dia.actividades.clear()` no se envía a la base antes de insertar, y choca con `UNIQUE(dia_id, letra)`. Lo mismo aplica a herramientas y materiales.
- **Qué hacer:** llama a `session.flush()` después de los `clear()` y antes de crear filas nuevas.
- **Criterio de aceptación:** dos `PUT` iguales seguidos responden 200 y los totales no cambian; un `PUT` con horas manuales las conserva.
- **Pruebas requeridas:** `test_guardar_dia_dos_veces` con actividades, herramientas y materiales; `test_guardar_dia_conserva_horas_manuales`.

### Tarea I2 — Editor: no perder capturas, fotos y horas en vivo
- **Archivos:** `frontend/src/pages/EditorReporte.tsx`, `frontend/src/components/SelectorFotos.tsx`, `frontend/src/components/EditorComponents.test.tsx`, `frontend/src/api/reportes.ts`, y `frontend/src/calculos.ts` (nuevo) con `frontend/src/calculos.test.ts` (nuevo).
- **Problema 1:** subir o borrar una foto invalida la consulta `dia`; el `useEffect` reescribe `borrador` y borra lo que se había escrito sin guardar.
- **Qué hacer:** el borrador solo se reinicia desde el servidor al cambiar `diaActual`, en la primera carga y al guardar con éxito. Las fotos se leen siempre de `dia.data`. El botón Guardar sigue activo si había cambios.
- **Problema 2:** los errores de subir o borrar foto no se muestran, y solo se puede elegir una foto cada vez.
- **Qué hacer:** agrega `multiple` al input. Sube los archivos en orden, uno por uno, sin superar el espacio libre. Muestra el error de la API en el `role="alert"` y un estado "Subiendo…" que desactive el input.
- **Problema 3:** las horas y totales solo aparecen después de guardar.
- **Qué hacer:** `calcularHoras(actividades, jornada)` en `calculos.ts` replica `recalcular_horas`. Úsalo para mostrar en vivo las horas de cada persona, las horas-hombre por actividad y los totales del día, con jornada 5 el sábado y 8 los demás días. Las filas con `horas_manual=true` no se tocan.
- **Criterio de aceptación:** al escribir una descripción, subir una foto y guardar, la descripción se conserva. Al marcar una persona, sus horas aparecen sin guardar.
- **Pruebas requeridas:** borrador conservado tras subir foto; error de subida visible; `calcularHoras` con 1 actividad, 2 actividades, manual y sábado.

### Tarea I3 — Rehacer el diseño del Excel mejorado
- **Archivos:** `backend/app/services/excel_mejorado.py`, `backend/tests/test_exportar.py`.
- **Problemas vistos en el PDF real:** las fotos tapan las tablas de colaboradores, herramientas y materiales, porque se ubican por filas de alto desconocido; una foto queda partida entre páginas; fotos y mapa deformados por `width`/`height` fijos (el mapa mide 475×416 y se pinta 600×230); `texto_seguro` convierte los totales en texto `'=SUM(...)`; descripción y observación en una columna angosta; fechas ISO; logo encima del texto; fuentes que no son Arial.
- **Qué hacer:**
  - Rejilla fija de 12 columnas A a L, ancho 9.5, con `print_area` en todas las hojas. Las tablas combinan columnas por fila con un helper: `_tabla(hoja, fila, columnas, filas)`, donde `columnas` es `[(encabezado, col_ini, col_fin, alineacion)]`.
  - **Alto de fila explícito en todas las filas:** `max(18, 15 * lineas)` con `lineas = ceil(len(texto) / caracteres_por_ancho)`, tomando la celda de texto más larga. Nunca dejes el alto en automático.
  - Distribución: encabezado de 3 filas con logo proporcional (`125×53`) en A1 y título desde la columna D; bloque de 4 indicadores como tarjetas combinadas con fondo `#EAF7ED`.
  - `Resumen`: tablas de ancho completo. La tabla por día y la de colaboradores llevan una fila final `Total` con `=SUM(...)`.
  - Hojas por día: descripción de actividad combinada en unas 8 columnas; colaboradores, herramientas y materiales a ancho completo.
  - Una clase `Formula(str)`: `_tabla` escribe esos valores sin pasar por `texto_seguro`, que se sigue aplicando a todo texto del usuario.
  - Números con formato: fechas `dd/mm/yyyy`, horas `0.##`, cantidades `0.##`; números a la derecha, texto a la izquierda.
  - Fotos en sección "Evidencia fotográfica", después de todas las tablas, en una página nueva: `Break` en `hoja.row_breaks`. Cada fila de fotos es una sola fila de Excel con alto fijo de 195 pt, con 2 recuadros de 340×255 px; conserva proporción, centra con `OneCellAnchor` como `_anclar_foto` de `excel_formato.py` y agrupa por espacio con su título. Máximo 3 filas de fotos por página, y luego otro `Break`.
  - Mapa en una fila con alto explícito, sin deformar: ancho 420 px y alto proporcional, centrado, junto con observación y firmas. Si no cabe en la página de fotos, va tras un `Break`.
  - Todas las celdas con texto en Arial, incluidas semana, fechas y firmas.
- **Criterio de aceptación:** en el PDF de un reporte con 12 fotos y 7 colaboradores ninguna imagen se superpone a una tabla ni queda partida entre páginas, y los totales se muestran calculados.
- **Pruebas requeridas:** ninguna celda contiene `'=`; fórmulas `=SUM` presentes; proporción de cada imagen dentro de ±1 % de la real; toda fila con texto tiene alto explícito; hay `Break` antes de las fotos; la fila ancla de cada imagen es mayor que la última fila con tabla.

### Tarea I4 — Migración explícita
- **Archivos:** `backend/alembic/versions/0001_esquema_inicial.py`.
- **Problema:** usa `Base.metadata.create_all`, que depende del modelo actual. Al agregar las marcas del mapa, una base nueva crearía la columna en `0001` y fallaría `0002`.
- **Qué hacer:** reemplázala por `op.create_table` explícitos para las 11 tablas, con sus restricciones únicas, y `downgrade` con `op.drop_table` en orden inverso. Conserva `revision = "0001"`.
- **Criterio de aceptación:** `alembic check` sin cambios, y `upgrade head` → `downgrade base` → `upgrade head` funcionan sobre una base vacía.
- **Pruebas requeridas:** prueba de ida y vuelta sobre SQLite temporal.

### Tarea I5 — Ajustes menores
- **Archivos:** `backend/app/services/excel_formato.py`, `backend/app/services/excel_mejorado.py`, `backend/app/services/calculos.py`, `backend/app/routers/reportes.py`, `backend/app/models/reportes.py`, `backend/tests/test_calculos.py`, `backend/tests/test_reportes.py`, `.agentes/reportes/REPORTE-20261105-reportes-servicios.md`.
- **Qué hacer:**
  - La jornada escrita a mano (`5 if ... else 8`) en los exportadores se reemplaza por una función `jornada_dia(dia)` en `calculos.py`, que lee settings; el router la reutiliza.
  - La advertencia muestra el nombre, no el id: `Pedro X supera la jornada de 8 horas`.
  - `texto_fotos` de un día nuevo arranca con `Fotos antes y después de la actividad realizada`. No cambies el esquema: se asigna al crear el reporte.
  - Corrige el reporte: dice 10 MB (son 15) y 507 con `test_espacio_lleno` (es 422 `espacio_lleno`).
- **Criterio de aceptación:** `make check` pasa.
- **Pruebas requeridas:** advertencia con nombre; día nuevo con texto por defecto.
