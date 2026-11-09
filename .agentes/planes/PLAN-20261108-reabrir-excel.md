---
id: PLAN-20261108-reabrir-excel
estado: cerrado         # borrador | aprobado | en_ejecucion | cerrado
rama: agente/modo-sin-almacenar     # misma rama; se ejecuta DESPUÉS de PLAN-20261108-modo-sin-almacenar
stack: fastapi
zona_protegida: no
autor: claude
---

# Reabrir una semana subiendo el Excel descargado (modo sin almacenar)

## Objetivo
En modo `ALMACENAR=false`, que se pueda subir un Excel generado antes por la app (formato actual o mejorado) para **seguir editando esa semana en línea**:
- Se recupera la semana completa (datos y fotos) desde una copia oculta dentro del Excel.
- **Si editaron el Excel a mano**, se leen las celdas visibles y se respetan esos cambios.
- Si el Excel no tiene copia oculta (uno viejo o llenado a mano con el formato), se lee **toda la información posible** del documento y se avisa lo que no se pudo.

Requiere `PLAN-20261108-modo-sin-almacenar` aceptado: `ReporteExportar`, `armar_reporte`, `normalizar_foto`, `EditorSemana` y `semana.ts`.

## Decisiones de Oscar (2026-11-08)
- Se vuelve a subir **el mismo Excel**; no hay un archivo de respaldo aparte.
- "Si editan algo de las descripciones lo debe leer como tal; si editan algo, ellos seguirán el formato o por lo menos tratar de leer la mayor info del documento posible."

## Contexto
- `backend/app/services/excel_formato.py`: escribe por día, en la hoja del día (`Lunes`…`Sabado`):
  - Fecha en `C6` y semana en `I6`.
  - Colaborador en `B10:B22` y sus letras en `H10:H22` (`"A, B"`).
  - Cantidad de herramienta en `Q10:Q23` y su nombre en `R10:R23`.
  - Descripción por actividad en la columna `D` del renglón cuya columna `M` tiene la letra (dinámico con las bandas A–J).
  - Texto de fotos en `D{30+desplazamiento}`, observación en `A{52+desplazamiento}` y firmas en `F`/`R{57+desplazamiento}`.
  - Fotos ancladas en N–T del renglón de cada espacio.
  - Los textos pasan por `texto_seguro`, que antepone `'` a los valores que empiezan con `= + - @ \t \r` (queda **literal** en la celda).
  - La hoja `Datos` va al final.
- `backend/app/services/excel_mejorado.py`: `_tabla(hoja, fila, columnas, filas)` arma las tablas por día (actividad/descripción/personas/horas-hombre, colaborador/actividad/horas, herramienta/cantidad, material/unidad/cantidad, observación) y la hoja `Resumen`.
- `backend/app/schemas/exportar.py` (`ReporteExportar`, `DiaExportar`, `FotoExportar`) y `services/reporte_memoria.py` (`armar_reporte`), del plan de los modos.
- `backend/app/services/fotos.py` (`normalizar_foto`), del plan de los modos.
- openpyxl 3.1.5 lee las imágenes de un libro (`hoja._images` con `anchor._from.row/col`) si Pillow está instalado. `defusedxml` ya está en la imagen como dependencia indirecta y openpyxl lo usa si existe; aquí se fija explícitamente.

## Alcance
**Dentro:**
- Copia oculta en los dos Excel.
- Mapa de celdas escritas.
- Lector que combina la copia con las celdas editadas.
- Lector de respaldo del formato actual sin copia.
- Endpoint de importación.
- Botón "Abrir reporte guardado" en el editor de semana.
- Documentación.

**Fuera de alcance:**
- Importar desde el PDF.
- Importar en modo `ALMACENAR=true` (el botón solo existe en modo sin almacenar; el endpoint responde en los dos modos y no guarda nada).
- Leer las horas editadas a mano en el Excel: las horas se recalculan; se conservan las manuales que venían en la copia.
- Crear catálogos nuevos desde nombres desconocidos: se avisan y se omiten.
- Leer fórmulas modificadas de la hoja `Datos` o de los totales.

## Tareas

### Tarea 1 — Copia oculta y mapa de celdas en los dos Excel
- **Archivos:** `backend/app/services/respaldo_excel.py` (crear), `backend/app/services/excel_formato.py`, `backend/app/services/excel_mejorado.py`, `backend/app/routers/exportar.py`, `backend/tests/test_respaldo_excel.py` (crear).
- **Patrón a seguir:** funciones privadas de `excel_formato.py`; servicio puro como `calculos.py`.
- **Seguridad:** #15, #17.
- **Qué hacer:**
  1. Cada `generar_*` acepta un parámetro opcional `respaldo: RespaldoSemana | None = None` y, durante el llenado, registra en `mapa: dict[str, str]` cada campo editable que escribe, con la clave lógica → `"Hoja!Celda"`. Claves:
     - `d{dia}.act.{letra}.descripcion`
     - `d{dia}.texto_fotos`
     - `d{dia}.observacion`
     - `d{dia}.colab.{colaborador_id}.letras` (formato: columna H)
     - `d{dia}.colab.{colaborador_id}.nombre` (formato: columna B)
     - `d{dia}.herr.{herramienta_id}.cantidad`
     - `d{dia}.mat.{material_id}.cantidad` (mejorado)
     - `firma.elaborado` y `firma.revisado`

     Cada entrada guarda también el **valor escrito** (sin el `'` de `texto_seguro`) para detectar si se editó.
  2. `RespaldoSemana{datos: ReporteExportar, contenidos: list[bytes]}`. `escribir_respaldo(libro, respaldo, mapa)` crea la hoja `_respaldo` con `sheet_state = "veryHidden"` (no se muestra en "Mostrar hojas" de Excel):
     - `A1 = "RSG-RESPALDO"` y `B1 = 1` (versión).
     - Fila 2: el JSON de `datos` (`model_dump_json`) partido en trozos de 30 000 caracteres en `A2, B2, …`.
     - Fila 3: el JSON del mapa `{clave: [celda, valor_escrito]}`, partido igual.
     - Desde la fila 4, una fila por foto: `A = indice` y desde `B`, el base64 del JPEG partido en trozos de 30 000.
     - Nada de esto pasa por `texto_seguro`: son datos de la app en una hoja oculta y se validan al leerlos.
  3. El `POST /api/exportar/{formato|mejorado}` (modo memoria) pasa el respaldo; la hoja `_respaldo` queda **después** de las hojas visibles. El PDF no lleva respaldo, porque se genera del mejorado sin él. El `GET` del modo guardado no agrega respaldo.
- **Criterio de aceptación:**
  - Un formato generado con A–E y 3 fotos tiene `_respaldo` en `veryHidden`; su JSON reconstruido es igual a `datos.model_dump()` y los 3 base64 decodificados son iguales a los bytes JPEG enviados.
  - El mapa contiene `d0.act.D.descripcion` apuntando a la celda real (`Lunes!D35` con una banda).
  - Las hojas visibles y sus `assert` actuales no cambian.
  - El PDF del mejorado sigue empezando con `%PDF` y no muestra la hoja oculta. Se comprueba que el número de páginas no cambia respecto de la versión sin respaldo.
- **Pruebas requeridas:** las del criterio, más una descripción de 70 000 caracteres partida en trozos y reconstruida.

### Tarea 2 — Lector: copia oculta + cambios hechos a mano
- **Archivos:** `backend/app/services/importar_excel.py` (crear), `backend/tests/test_importar_excel.py` (crear).
- **Patrón a seguir:** `armar_reporte` (resolución de catálogos con `session`, errores de dominio).
- **Seguridad:** #14, #15, #16.
- **Qué hacer:**
  1. `leer_excel(contenido: bytes, session) -> Importacion{datos: ReporteExportar, contenidos: list[bytes], avisos: list[str], origen: Literal["respaldo", "formato"]}`.
  2. Si existe `_respaldo` con `A1 == "RSG-RESPALDO"` y versión 1:
     - Reconstruye los trozos, valida con `ReporteExportar.model_validate_json` y decodifica cada foto con `base64.b64decode(validate=True)` + `normalizar_foto`.
     - Si algo es inválido → `InvalidFileError("El respaldo del archivo está dañado")`.
  3. **Superpone las ediciones a mano.** Para cada clave del mapa, lee la celda (`load_workbook(..., data_only=False)`), quita un `'` inicial, aplica `strip()` y la compara con `valor_escrito`. Si cambió, aplica:
     - `descripcion`, `texto_fotos`, `observacion` → el texto nuevo (truncado al `max_length` del schema, con aviso si se truncó).
     - `colab.{id}.letras` → reparte de nuevo ese colaborador en las letras leídas (separadas por coma o espacio, normalizadas a mayúsculas A–J). Lo quita de las actividades que ya no aparecen y lo agrega con horas automáticas en las nuevas. Conserva `horas_manual` donde la pareja colaborador-actividad ya existía. Si una letra no tiene actividad, crea la actividad vacía con aviso.
     - `colab.{id}.nombre` → si el nombre cambió y coincide con **otro** colaborador del catálogo (comparación sin acentos, sin mayúsculas y sin espacios dobles), mueve sus asignaciones a ese colaborador. Si no coincide → aviso y se conserva el original.
     - `herr.{id}.cantidad` / `mat.{id}.cantidad` → número ≥ 0; con 0 o vacío se quita. Si no es número → aviso y se conserva.
     - `firma.*` → buscar el firmante por nombre normalizado; si no existe → aviso.
     - Cada cambio aplicado genera un aviso informativo: "Lunes: se tomó la descripción editada de la actividad B".
  4. El resultado final se vuelve a validar con `ReporteExportar`, así que cualquier dato leído pasa por la misma validación que una exportación.
- **Criterio de aceptación:** `pytest -q tests/test_importar_excel.py` pasa:
  - Ida y vuelta sin ediciones → datos idénticos y fotos iguales.
  - Editar `Lunes!D{fila de B}` con openpyxl → la descripción nueva se toma, con aviso.
  - Cambiar `H10` de `"A"` a `"A, C"` → el colaborador aparece en C con horas recalculadas.
  - Poner `Q10 = 0` → la herramienta desaparece.
  - Una descripción editada que empieza con `=` → se toma como texto (`=SUMA…` literal), sin evaluarse.
  - Un colaborador renombrado a un nombre que no existe → aviso y sin cambio.
  - El mismo flujo con el **mejorado** para descripción, cantidades y observación.
- **Pruebas requeridas:** las del criterio. Usa datos sintéticos (`faker`) para los nombres del catálogo de prueba.

### Tarea 3 — Lector de respaldo: formato actual sin copia oculta
- **Archivos:** `backend/app/services/importar_excel.py`, `backend/tests/test_importar_excel.py`.
- **Patrón a seguir:** las posiciones que escribe `excel_formato.py` (leer exactamente donde se escribe).
- **Seguridad:** #14, #16.
- **Qué hacer:** si no hay `_respaldo` pero existen hojas con los nombres `Lunes`…`Sabado`, se lee con `origen = "formato"`:
  1. Semana y año: `C6` del lunes (fecha o texto `dd/mm/aaaa`) → `isocalendar()`. Si falta, usa `I6` + el año actual, con aviso. Si no hay fecha válida → `InvalidFileError("No se reconoce el formato del reporte")`.
  2. Por cada hoja de día:
     - Busca la fila del encabezado `ITEM` en la columna A y `ACTIVIDAD` en M.
     - Debajo, cada fila con letra A–J en M define la actividad, con su descripción en D.
     - La fila cuya D empieza con el texto de fotos o que no tiene letra en M es "Antes y después".
     - Busca la etiqueta `Observación` en la columna A; la observación está en la fila siguiente.
     - Firmas junto a `Elaborado por:` / `Revisado por:`.
  3. Colaboradores: en `B10:B22` el nombre (comparado con el catálogo normalizado) y en `H` las letras → asignaciones con horas automáticas.
  4. Herramientas: en `R10:R23` el nombre comparado con el catálogo y en `Q` la cantidad (> 0).
  5. Fotos: `hoja._images` cuya columna de anclaje esté entre N y T (índices 13–19). Se asignan al espacio cuyo rango de filas contiene `anchor._from.row` y se ordenan por (fila, columna). Las imágenes del logo y el mapa (fuera de N–T o fuera de la tabla) se ignoran. Cada imagen pasa por `normalizar_foto`; como máximo 4 por espacio, las sobrantes generan aviso.
  6. Materiales: el formato no los tiene → aviso "Los materiales no están en el formato actual; agrégalos de nuevo".
  7. Los nombres sin coincidencia → aviso por cada uno ("No se encontró el colaborador «…» en el catálogo").
  8. Un archivo que no es ni respaldo ni formato (p. ej. el mejorado sin copia) → `InvalidFileError("Este archivo no tiene datos para reabrir; usa un Excel descargado desde la app")`.
- **Criterio de aceptación:**
  - Un formato generado **sin** respaldo (modo guardado, `GET`) se importa: actividades, descripciones, asignaciones, cantidades de herramientas, observación, firmas y fotos en su espacio, con el aviso de materiales.
  - Un formato con un colaborador desconocido → aviso.
  - Un `.xlsx` cualquiera (libro vacío) → 422 `invalid_file`.
- **Pruebas requeridas:** las del criterio, más el caso de bandas A–J (actividades en filas desplazadas).

### Tarea 4 — Endpoint `POST /api/importar` con protecciones de archivo
- **Archivos:** `backend/app/routers/exportar.py` (o `backend/app/routers/importar.py`, crear), `backend/app/schemas/exportar.py`, `backend/pyproject.toml`, `backend/app/main.py`, `backend/tests/test_importar_api.py` (crear).
- **Patrón a seguir:** `router_memoria` de exportación (lectura con tope y errores de dominio).
- **Seguridad:** #14, #16, #17, #20.
- **Qué hacer:**
  1. Fija `defusedxml` con versión exacta en `dependencies`; openpyxl lo usa para evitar XXE y entidades XML expansivas.
  2. `POST /api/importar` con `archivo: UploadFile`:
     - Lee como máximo `max_exportacion_mb` → `FileTooLargeError`.
     - Debe empezar con `PK\x03\x04` y abrirse con `zipfile.ZipFile`. Rechaza si hay más de 2 000 entradas, si la suma de `file_size` descomprimido supera 300 MB (protección contra zip bomb) o si una entrada tiene ruta absoluta o `..` → `InvalidFileError("Archivo de Excel no válido")`.
     - `load_workbook(BytesIO(...), read_only=False, data_only=False, keep_vba=False)`.
     - **No escribe en la BD ni en disco.**
  3. Respuesta `ImportacionRead{datos: ReporteExportar, fotos: list[FotoImportada{indice: int, espacio: Espacio, dia_semana: int, contenido_base64: str}], avisos: list[str], origen: Literal["respaldo", "formato"]}`.
  4. El router se incluye siempre, en los dos modos.
- **Criterio de aceptación:**
  - Un formato con respaldo → 200 con `origen="respaldo"`, las mismas fotos y `avisos` vacíos.
  - Un archivo `.txt` renombrado a `.xlsx` → 422 `invalid_file`.
  - Un zip con un `xl/x.xml` de 400 MB declarados → 422 sin descomprimirlo (se crea con `ZipInfo` y `file_size` falso, o con un archivo de ceros muy comprimido).
  - Un XML con una entidad externa (XXE) dentro del xlsx → 422, sin leer `/etc/passwd`.
  - Con un tope parcheado a 1 MB → 413.
  - El conteo de `reportes` no cambia.
- **Pruebas requeridas:** las del criterio.

### Tarea 5 — Botón "Abrir reporte guardado" en el editor de semana
- **Archivos:** `frontend/src/api/importar.ts` (crear), `frontend/src/semana.ts`, `frontend/src/semana.test.ts`, `frontend/src/pages/EditorSemana.tsx`, `frontend/src/pages/EditorSemana.test.tsx`.
- **Patrón a seguir:** `BotonDescarga` y `apiDescarga` (plan de los modos); `Confirmar` y `useAvisos`.
- **Seguridad:** #15, #16.
- **Qué hacer:**
  1. `importarExcel(archivo: File)` hace POST multipart a `/importar` y devuelve `ImportacionRead`.
  2. `semanaDesdeImportacion(imp): SemanaLocal`:
     - Arma los 6 días con `armarActividades`.
     - Convierte cada `contenido_base64` en un `Blob` `image/jpeg` con su `URL.createObjectURL`.
     - Asigna cada foto a su día y espacio.
  3. En `EditorSemana`, el botón **"Abrir reporte guardado"** usa `<input type="file" accept=".xlsx">`:
     - Si hay datos capturados, pide confirmación ("Se reemplazará la semana actual").
     - Al cargar, revoca las URLs anteriores y reemplaza la semana.
     - Si hay `avisos`, los muestra en una lista desplegable "Revisa estos puntos" en la tarjeta de verificaciones, con un `useAvisos` de resumen ("Se abrió la semana 45 con 3 avisos").
     - Si `origen = "formato"`, muestra además: "Se leyó el formato sin respaldo; revisa horas y materiales."
     - Los errores (422/413) se muestran con su `detail`.
- **Criterio de aceptación:** `test`, `lint`, `format:check` y `build` pasan.
- **Pruebas requeridas:**
  - `semanaDesdeImportacion` con 2 fotos en días distintos → cada una en su lugar con su URL.
  - Subir con datos ya capturados pide confirmación.
  - Los avisos se muestran.
  - Un error 422 se muestra.

### Tarea 6 — Documentación y prueba de punta a punta
- **Archivos:** `README.md`, `.agentes/PROYECTO.md`.
- **Patrón a seguir:** sección "Modos" del README (plan de los modos).
- **Seguridad:** n.a.
- **Qué hacer:**
  - README: cómo reabrir una semana.
    - Usar el Excel **formato** o **mejorado** descargado desde la app; el PDF no sirve.
    - Qué se lee si se editó a mano: descripciones, texto de fotos, observación, personas por actividad (columna "# actividad"), cantidades y firmas.
    - Qué no se lee: horas editadas a mano y fórmulas o totales.
    - Que el archivo pesa más por la copia oculta (unos 0.4 MB por foto).
  - `PROYECTO.md`: "Piezas de referencia" con `services/importar_excel.py`.
- **Criterio de aceptación:** prueba manual con `ALMACENAR=false` y `make up`:
  1. Capturar una semana con 3 fotos y descargar el formato.
  2. Abrirlo en LibreOffice, cambiar una descripción y una cantidad, y guardarlo.
  3. "Abrir reporte guardado" → se ven los cambios con sus avisos y las fotos.
  4. Descargar de nuevo.

  Documentado en el reporte.
- **Pruebas requeridas:** la prueba manual.

## Seguridad

| # | Medida | Aplica | Cómo se cumple / prueba |
|---|---|---|---|
| 14 | Validar inputs | sí | Todo lo leído (copia o celdas) se valida otra vez con `ReporteExportar`; las cantidades son numéricas y ≥ 0; los textos se truncan a `max_length`. Pruebas de la tarea 2. |
| 15 | Sanitizar contenido | sí | Los textos leídos se tratan como texto literal (`data_only=False`, sin evaluar fórmulas) y al exportar vuelven a pasar por `texto_seguro`. Prueba con `=`. React sin HTML crudo. |
| 16 | Restringir archivos | sí | `.xlsx` con firma ZIP, tope de MB, máximo de entradas y de tamaño descomprimido (zip bomb), rutas sin `..`, `defusedxml` (XXE) y nada escrito a disco. Las fotos extraídas pasan por `normalizar_foto`. Pruebas de la tarea 4. |
| 17 | Datos necesarios | sí | La importación devuelve solo `datos`, `fotos`, `avisos` y `origen` (prueba de claves). |
| 20 | Dependencias | sí | `defusedxml` fijado (ya venía indirectamente); `pip-audit`. |

n.a.: 1–13 y 18–19 (sin secretos, autenticación, SQL nuevo ni cabeceras; la app sigue siendo local según `PROYECTO.md`).

## Consistencia
- Se reutilizan `ReporteExportar`, `armar_reporte`, `normalizar_foto`, los errores de dominio, `texto_seguro` (solo al escribir), `apiDescarga`/`ApiError`, `Confirmar`/`useAvisos` y `semana.ts`.
- **Sin una segunda forma de lo mismo:** la lectura usa las **mismas coordenadas** que registra la escritura (mapa de celdas). El lector de respaldo del formato (tarea 3) es el único que parte de posiciones fijas, y lo justifica la decisión de Oscar de "leer la mayor info posible".
- **Dependencia fijada:** `defusedxml` (seguridad, ya presente de forma indirecta).

## Verificación final
```bash
docker build -t tania-api-modos backend
docker run --rm -w /srv tania-api-modos sh -c "ruff check . && ruff format --check . && pytest -q && bandit -r app -ll && pip-audit"
npm --prefix frontend run lint && npm --prefix frontend run format:check
npm --prefix frontend run test && npm --prefix frontend run build
npm --prefix frontend audit --audit-level=high
gitleaks detect --no-git -v
```
Más la prueba manual de la tarea 6 con `ALMACENAR=false`. No toques `data/`.

## Riesgos
- **Tamaño del Excel:** la copia oculta guarda las fotos en base64, así que con 20 fotos el archivo crece unos 8–10 MB. Aceptado para no depender de un segundo archivo.
- **Ediciones que rompen el formato** (filas insertadas, celdas movidas): el mapa apunta a celdas que ya no corresponden. Se mitiga comparando con el valor escrito: si la celda tiene algo inesperado, se toma como edición y se avisa. En el peor caso se usa la copia y los avisos lo dicen.
- **LibreOffice/Excel al guardar:** conservan las hojas `veryHidden` y las imágenes. Se verifica en la prueba manual guardando con LibreOffice.
- **Nombres escritos a mano** con variaciones: la comparación es normalizada; lo que no coincide se avisa.

## Supuestos y preguntas abiertas
- Supuesto: el botón de reabrir solo aparece en modo sin almacenar, como pediste. En modo guardado no hace falta, porque la semana ya está guardada.
- Supuesto: las horas editadas a mano en el Excel no se leen; se recalculan, salvo las manuales que ya venían en la copia.
- Sin preguntas abiertas.
