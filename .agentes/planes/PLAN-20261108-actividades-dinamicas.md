---
id: PLAN-20261108-actividades-dinamicas
estado: en_ejecucion      # borrador | aprobado | en_ejecucion | cerrado
rama: agente/actividades-dinamicas
rama_base: agente/diseno-ui   # main todavía no tiene el código; crear la rama desde aquí
stack: fastapi
zona_protegida: sí      # la migración de bajada borra actividades y fotos D–J
autor: claude
---

# Actividades dinámicas por día (A–J)

## Objetivo
Que cada día del reporte permita capturar de 1 a 10 actividades (A–J) en lugar de tres fijas.
El editor muestra A y B de inicio y un botón agrega la siguiente letra. Las tres descargas
(formato actual, mejorado y PDF) incluyen todas las actividades.

## Contexto
- `backend/app/models/reportes.py:68-81` — `Actividad.letra` con `CheckConstraint("letra IN ('A', 'B', 'C')", name="letra_valida")`; `Foto.espacio` (`:118`) con `CheckConstraint("espacio IN ('A', 'B', 'C', 'AD')", name="espacio_valido")`.
- `backend/alembic/versions/0001_esquema_inicial.py:86` y `:150` — las mismas restricciones en la migración inicial. Es la única migración.
- `backend/app/schemas/reportes.py:6-7` — `Letra = Literal["A", "B", "C"]`, `Espacio = Literal["A", "B", "C", "AD"]`; `:93` `actividades: ... max_length=3`.
- `backend/app/routers/reportes.py:44` — `LIMITES_FOTOS = {"A": 2, "B": 4, "C": 2, "AD": 4}`; `guardar_dia` (`:217-246`) ya recorre `data.actividades` sin suponer cuántas son.
- `backend/app/services/calculos.py` — ya funciona con cualquier número de actividades. **No se toca.**
- `backend/app/services/excel_formato.py` — la plantilla `base_actividades` es fija:
  - Tabla de horas en J9:O19: letras en M10:O10, personas en fila 11 (`COUNTIF` sobre `$H$10:$H$22`), horas en fila 13, horas-hombre en fila 15 (`=+M13*M11`), total en M17 (`=+M15+N15+O15`), conteo en fila 19 (`=+IF(M11=0,0,1)`). Las columnas P–T ya están ocupadas (herramientas en Q–T), así que **no se pueden agregar columnas**.
  - Las filas 20–23 están libres en J–O; la tabla de actividades empieza en la fila 25 (encabezado).
  - Renglones de actividad: A=26, B=27–28, C=29, "Antes y después"=30–31 (alto 253.5). Están combinadas `A:C`, `D:L` y `N:T` por renglón; `M27:M28` y `M30:M31`.
  - Debajo: A32:T32 "Resumen General.", A33:T34, A35:T50 (mapa, ancla en la fila 34), A51:E51 "Observación", A52:T55 (texto), firmas en F57:I58 y R57:T58; `print_area` = `A1:T58`.
  - La hoja `Datos` suma `{Dia}!M19+N19+O19` (fila 8) y toma `{Dia}!M17` (fila 9).
- `backend/app/services/excel_mejorado.py:30-35` (`ETIQUETAS_FOTOS`) y `:364`, `:378` (`("A", "B", "C", "AD")`) — fotos por espacio fijas. Las tablas de `_hoja_dia` (`:440-472`) ya recorren `dia.actividades`.
- `frontend/src/api/reportes.ts:23` (`letra: "A" | "B" | "C"`) y `:39` (`espacio: "A" | "B" | "C" | "AD"`).
- `frontend/src/pages/EditorReporte.tsx` — `espacios` fijo (`:27-32`), `vacio` con A, B y C (`:34-44`), y otras dos veces `(["A", "B", "C"] as const).map(...)` (`:113`, `:161`). Al guardar se filtran las actividades vacías (`:145-150`). Las tarjetas plegadas "sin capturar" están en `:379-398`.
- `frontend/src/verificaciones.ts:110-121` — avisa "La actividad X no tiene fotos" usando `foto.espacio === actividad.letra`. Funciona sin cambios con letras nuevas.

## Reglas de negocio (decididas por Oscar)
1. Máximo **10 actividades por día: A–J**. Las letras son fijas: una actividad conserva su letra (las fotos se ligan por letra).
2. El editor siempre muestra al menos A y B. Si el día guardado tiene letras más altas, se muestran todas, de A hasta la letra más alta guardada. Las de en medio que estén vacías aparecen plegadas ("sin capturar").
3. El botón **"Agregar actividad"** agrega la siguiente letra después de la última visible, ya abierta. Se desactiva al llegar a J.
4. El botón **"Quitar"** solo aparece en la **última** actividad visible, solo si está por encima de B, vacía (sin descripción ni personas) y sin fotos en su espacio. Solo la quita del borrador; las actividades vacías ya no se guardan hoy.
5. Fotos: **todas las actividades (A–J) admiten hasta 4 fotos**, y "Antes y después" también 4. En el editor se muestra un espacio de fotos por actividad visible, más "Antes y después".
6. **Las fotos se adaptan a su espacio** en el formato actual: con 1 foto, ocupa todo el área de imagen de la actividad; con 2, van lado a lado; con 3 o 4, van en una cuadrícula de 2×2. Cada foto se escala para caber en su casilla sin deformarse y queda centrada. El alto de los renglones de la plantilla no cambia.
7. Formato actual: por cada letra después de C (hasta la más alta del día) se inserta un renglón de actividad nuevo entre C y "Antes y después". Las letras D–J también se agregan a la tabla de horas en bandas de 3 columnas (M–O) debajo del bloque original. El total de horas-hombre (M17) y la hoja `Datos` incluyen todas las letras.

## Alcance
**Dentro:** modelo, migración, schemas, límites de fotos, Excel formato actual, Excel mejorado (y por lo tanto el PDF, que lo convierte), tipos y editor del frontend, pruebas.

**Fuera de alcance:**
- `backend/app/services/calculos.py`, `backend/app/services/pdf.py`, `backend/app/services/fotos.py` (no se cambian).
- Reordenar o renombrar letras, o arrastrar actividades.
- Modificar el archivo `backend/app/plantillas/plantilla_formato.xlsx`: todo se hace en código sobre la copia de la hoja.
- La hoja `base_sin_actividades` (sin cambios).
- Rediseño visual del editor más allá de los dos botones nuevos.
- Tocar `data/`, `.env` o `CH-RSG-*.xlsx`.

## Tareas

### Tarea 1 — Ampliar letras y espacios en modelo, migración, schemas y límites
- **Archivos:** `backend/app/models/reportes.py` (modificar), `backend/alembic/versions/0002_actividades_a_j.py` (crear), `backend/app/schemas/reportes.py` (modificar), `backend/app/routers/reportes.py` (modificar solo `LIMITES_FOTOS`), `backend/tests/test_migraciones.py` y `backend/tests/test_reportes.py` (modificar).
- **Patrón a seguir:** `backend/alembic/versions/0001_esquema_inicial.py` (encabezado, `revision`/`down_revision`, tipos); pruebas `test_migracion_ida_y_vuelta_sqlite` y `test_espacio_lleno`.
- **Seguridad:** #8, #13, #14.
- **Qué hacer:**
  1. En `models/reportes.py` define `LETRAS_ACTIVIDAD = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J")` a nivel de módulo. `Actividad`: `CheckConstraint` con nombre `letra_valida` y texto `"letra IN ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J')"` (armado desde la tupla con `", ".join(f"'{l}'" for l in LETRAS_ACTIVIDAD)`; es una constante, no entrada de usuario). Tipo `Mapped[str]` con `String(1)`. `Foto`: `espacio_valido` con las 10 letras más `'AD'`; tipo `Mapped[str]`.
  2. Migración `0002` (`revision = "0002"`, `down_revision = "0001"`). En `upgrade()` usa `op.batch_alter_table("actividades", recreate="always")`: `drop_constraint("letra_valida", type_="check")` y `create_check_constraint("letra_valida", <nueva condición>)`. Haz lo mismo en `fotos` con `espacio_valido`. Si Alembic no refleja la restricción con nombre en SQLite, pasa la definición por `table_args`/`reflect_args` del batch. Lo que manda es el criterio de aceptación.
  3. `downgrade()`: primero borra los datos que ya no cabrían, con SQL estático y sin interpolar valores de usuario: `DELETE FROM asignaciones WHERE actividad_id IN (SELECT id FROM actividades WHERE letra NOT IN ('A','B','C'))`, `DELETE FROM actividades WHERE letra NOT IN ('A','B','C')`, `DELETE FROM fotos WHERE espacio NOT IN ('A','B','C','AD')`. Después restaura las restricciones originales. Agrega un comentario: "Bajar borra actividades y fotos D–J".
  4. `schemas/reportes.py`: `Letra = Literal["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]`, `Espacio = Literal[<las mismas>, "AD"]`, `DiaWrite.actividades` con `max_length=10`.
  5. `routers/reportes.py`: `LIMITES_FOTOS = {**{letra: 4 for letra in LETRAS_ACTIVIDAD}, "AD": 4}` (importa `LETRAS_ACTIVIDAD` desde `app.models.reportes`).
- **Criterio de aceptación:**
  - `pytest -q tests/test_migraciones.py` pasa. Con la migración en head, insertar una actividad `letra='D'` funciona y `letra='K'` lanza `IntegrityError`. Tras `downgrade("0001")` las filas D desaparecen y `letra='D'` vuelve a fallar.
  - `PUT /api/reportes/{id}/dias/0` con 10 actividades A–J → 200 y `numero_actividades` = número de actividades con personas.
  - Con 11 actividades, o con `letra: "K"` → 422 con `code: "validation_error"`.
  - `POST .../fotos` con `espacio=A` y con `espacio=D` acepta 4 fotos y la quinta → 422 `code: "espacio_lleno"`; `espacio=K` → 404. Ajusta `test_espacio_lleno` al nuevo límite.
- **Pruebas requeridas:** feliz (A–J), borde (exactamente 10), error (11 elementos, letra `K`, letra repetida → 422), migración ida y vuelta con datos D, fotos A y D (4 aceptadas, la 5.ª rechazada). Datos con `faker`.

### Tarea 2 — Insertar renglones y bandas de horas y acomodar las fotos en el Excel con formato actual
- **Archivos:** `backend/app/services/excel_formato.py` (modificar), `backend/tests/test_excel_formato.py` (modificar).
- **Patrón a seguir:** las funciones `_anclar_*` y `_llenar_*` del mismo archivo (funciones privadas con type hints, `texto_seguro` para todo texto de usuario); pruebas `test_formato_tiene_hojas_celdas_y_formulas`.
- **Seguridad:** #15 (escapar descripciones con `texto_seguro`; las fórmulas solo se arman con coordenadas que calcula el código, nunca con texto del usuario).
- **Qué hacer:**
  1. Calcula por día `extras = LETRAS_ACTIVIDAD[3 : indice_mas_alto + 1]`, donde `indice_mas_alto` es el índice en `LETRAS_ACTIVIDAD` de la letra más alta de `dia.actividades`. Con A–C, `extras` queda vacío y la hoja queda **idéntica** a hoy.
  2. Crea el helper `_insertar_filas(hoja: Worksheet, fila: int, cantidad: int) -> None`, que recorre hacia abajo todo lo que esté en `fila` o más abajo:
     - Guarda y quita (`unmerge_cells`) los rangos combinados con `min_row >= fila`.
     - `hoja.move_range(f"A{fila}:T{hoja.max_row}", rows=cantidad, translate=True)`.
     - Vuelve a combinar cada rango desplazado `cantidad` filas.
     - Recorre los altos de fila de abajo hacia arriba (`row_dimensions[n + cantidad].height = row_dimensions[n].height`).
  3. **Renglones de actividad:** si hay `extras`, llama `_insertar_filas(hoja, 30, len(extras))`. Para cada extra `i` en la fila `30 + i`:
     - Alto 253.5.
     - Copia el estilo (`copy(celda._style)`) de la fila 29 en A–T.
     - Combina `A:C`, `D:L` y `N:T`.
     - Escribe `A` = número de ítem (`4 + i`), `M` = letra y `D` = `texto_seguro(descripcion)` (vacío si la letra no existe).
     - Renumera la celda de ítem de "Antes y después" a `4 + len(extras)`.
  4. **Bandas de horas:** `bandas = ceil(len(extras) / 3)`. Si hay bandas, llama `_insertar_filas(hoja, 24, 5 * bandas)` **después** del paso 3, para que todo lo de abajo se recorra junto. Cada banda `b` ocupa las filas `r = 24 + 5*b` a `r+4`, con estilos copiados de las filas 10, 11, 13, 15 y 19 en J–O:
     - Fila r: letras en M–O.
     - Fila r+1: J = "Número de colaborador en actividad" y la fórmula `COUNTIF` igual a la de la fila 11, apuntando a la celda de letra de la banda.
     - Fila r+2: J = "Horas de actividad" y valor de horas, con la misma regla que `_llenar_comunes` (`horas / personas if personas else jornada`).
     - Fila r+3: J = "Horas hombres " y `=+M{r+2}*M{r+1}`.
     - Fila r+4: J = "Total de actividades" y `=+IF(M{r+1}=0,0,1)`.
     - Combina `J:L` en las filas con etiqueta.
  5. `M17` = `=+M15+N15+O15` más `+{col}{r+3}` por cada letra extra.
  6. Recalcula todas las filas fijas con `desplazamiento = 5 * bandas + len(extras)`: `D30` (texto de fotos), `A52`, `F57`, `R57`, la fila del mapa en `_anclar_mapa` (34) y `print_area` (`A1:T{58 + desplazamiento}`). Recalcula también las filas de fotos en `_agregar_fotos`: A, B y C se recorren `5 * bandas`; las extras van en su renglón nuevo, y "AD" se recorre `desplazamiento`. Pasa los desplazamientos como parámetros, sin variables globales.
  7. **Fotos adaptables.** Reemplaza `_anclar_foto(hoja, ruta, fila, derecha)` y el diccionario fijo de `_agregar_fotos` por:
     - `_marcador(hoja, columna: int, fila: int, x_px: int, y_px: int) -> AnchorMarker`, que avanza desde (`columna`, `fila`) restando `_pixeles_columna`/`_pixeles_fila` hasta encontrar la celda que contiene el punto, y devuelve el marcador con `colOff`/`rowOff` en EMU (`* EMU_POR_PIXEL`). Así el desplazamiento nunca rebasa su celda, que LibreOffice no respeta.
     - `_acomodar_fotos(hoja, rutas: list[Path], fila_inicio: int, fila_fin: int) -> None`: el área es N–T (columnas 14–20) × filas `fila_inicio..fila_fin`. La cuadrícula es `(1, 1)` con 1 foto, `(1, 2)` con 2 y `(2, 2)` con 3–4. Cada casilla mide `ancho_area / columnas` × `alto_area / filas`, menos un margen de 4 px por lado. Cada foto se escala con `min(ancho/w, alto/h)`, se centra en su casilla y se ancla con `OneCellAnchor(_from=_marcador(...), ext=...)`. El orden es izquierda→derecha y arriba→abajo, según `Foto.orden`.
     - `_agregar_fotos` arma las áreas por letra con los desplazamientos: A = fila 26, B = 27–28, C = 29, cada extra = su renglón y AD = las 2 filas de "Antes y después". Toma hasta 4 fotos por espacio y solo de archivos que existan (`is_file()`, como hoy).
  8. `_llenar_dia` devuelve `list[str]` con las coordenadas de todas las celdas de "Total de actividades" (las de la fila 19 más las de cada banda; para la hoja sin actividades, `["M19", "N19", "O19"]`). `generar_formato` arma `Datos!{col}8` como `"=+" + "+".join(f"{nombre}!{c}" for c in celdas)`.
- **Criterio de aceptación:** `pytest -q tests/test_excel_formato.py` pasa, incluyendo:
  - La prueba actual sin cambios en sus `assert` (solo A y B → `print_area` `$A$1:$T$58`, `Datos E8 == "=+Lunes!M19+Lunes!N19+Lunes!O19"`).
  - Una prueba nueva con A–E: los renglones nuevos quedan en 30 y 31 y luego la banda los recorre 5 filas, así que `M35 == "D"`, `M36 == "E"`, `D35` = descripción de D y "Antes y después" queda en A37 con ítem `6`. La banda está en M24 = "D" y N24 = "E". `M17` contiene `M27` y `N27`. `print_area == "...$A$1:$T$65"`. `Datos E8` incluye `Lunes!M28` y `Lunes!N28`. Hay un rango combinado `D35:L35`. Las firmas están en `F64`.
  - Una prueba con una descripción que empieza con `=` en la actividad D → la celda queda con `'` al inicio.
  - Prueba de fotos (imágenes sintéticas creadas con Pillow en `tmp_path`, con `FOTOS_DIR`/ruta parcheada con `monkeypatch`, como en `test_mejorado_distribuye_fotos_y_formulas_sin_superposicion`). Con 1, 2 y 4 fotos en A: la hoja tiene ese número de imágenes de foto (`len(hoja._images)` menos logo y mapa). Ninguna imagen se sale del área N–T de su renglón. Con 4 fotos, ninguna se superpone (compara los rectángulos en píxeles a partir de `anchor._from` + `ext`). Con 4 en una actividad de una sola fila, cada foto mide como máximo la mitad del alto del renglón.
- **Pruebas requeridas:** sin extras (regresión), 2 extras (D–E), 7 extras (D–J, 3 bandas), hueco (A y D sin C → se crea el renglón C vacío), inyección de fórmula en extra, fotos 1/2/4 en una actividad de una fila (A) y de dos filas (B), y 4 fotos en una extra (D).

### Tarea 3 — Fotos y etiquetas de A–J en el Excel mejorado
- **Archivos:** `backend/app/services/excel_mejorado.py` (modificar), `backend/tests/test_exportar.py` (modificar).
- **Patrón a seguir:** `_seccion_fotos` del mismo archivo y `test_mejorado_distribuye_fotos_y_formulas_sin_superposicion`.
- **Seguridad:** #15 (sin cambios en el escape existente).
- **Qué hacer:** `ETIQUETAS_FOTOS = {**{letra: f"Actividad {letra}" for letra in LETRAS_ACTIVIDAD}, "AD": "Antes y después"}`. Reemplaza las dos tuplas `("A", "B", "C", "AD")` por una constante `ESPACIOS_FOTOS = (*LETRAS_ACTIVIDAD, "AD")`. Lo demás ya recorre `dia.actividades`.
- **Criterio de aceptación:** `pytest -q tests/test_exportar.py` pasa. Una prueba nueva con actividad D y 4 fotos en el espacio D genera la hoja del día con la etiqueta "Actividad D", una fila de tabla con letra D y 2 filas de fotos (2 por fila; el diseño actual ya acomoda N fotos de 2 en 2, así que no se cambia).
- **Pruebas requeridas:** feliz (D con foto), regresión (las pruebas actuales siguen pasando).

### Tarea 4 — Tipos y funciones puras de actividades en el frontend
- **Archivos:** `frontend/src/api/reportes.ts` (modificar), `frontend/src/actividades.ts` (crear), `frontend/src/actividades.test.ts` (crear).
- **Patrón a seguir:** `frontend/src/calculos.ts` + `frontend/src/calculos.test.ts` (funciones puras exportadas, pruebas vitest en el mismo nivel).
- **Seguridad:** #14 (el límite A–J y el máximo de fotos también se validan en el backend; esto es solo UX).
- **Qué hacer:**
  1. En `reportes.ts`: `export const LETRAS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"] as const;`, `export type Letra = (typeof LETRAS)[number];`, `Actividad.letra: Letra`, `Foto.espacio: Letra | "AD"`.
  2. En `actividades.ts`:
     - `armarActividades(guardadas: Actividad[]): Actividad[]` devuelve de A hasta la letra más alta guardada (mínimo hasta B), con las guardadas en su lugar y vacías en los huecos.
     - `siguienteLetra(actividades: Actividad[]): Letra | undefined` devuelve la letra que sigue a la última, o `undefined` si la última es J.
     - `puedeQuitar(actividad: Actividad, esUltima: boolean, fotos: Foto[]): boolean` aplica la regla 4.
     - `espaciosFotos(actividades: Actividad[]): [Letra | "AD", string, number][]` devuelve `[letra, "Actividad X", 4]` por cada actividad visible y al final `["AD", "Antes y después", 4]`.
- **Criterio de aceptación:** `npm --prefix frontend run test` pasa; `npm --prefix frontend run build` compila sin errores de tipos.
- **Pruebas requeridas:**
  - `armarActividades([])` → A y B.
  - Con A y D guardadas → A, B, C y D, con B y C vacías.
  - `siguienteLetra` con A–J → `undefined`.
  - `puedeQuitar` es falso para B, para una actividad con descripción, con personas o con una foto en su espacio, y para una que no es la última.
  - `espaciosFotos` con A–C → 4 espacios (A, B, C, AD), todos con máximo 4.

### Tarea 5 — Botones "Agregar actividad" y "Quitar" en el editor
- **Archivos:** `frontend/src/pages/EditorReporte.tsx` (modificar), `frontend/src/editor.css` (modificar solo si hace falta espaciado), `frontend/src/components/EditorComponents.test.tsx` o `frontend/src/pages/EditorReporte.test.tsx` (crear, siguiendo `frontend/src/pages/Reportes.test.tsx`).
- **Patrón a seguir:** los botones existentes `btn-secondary btn-sm` (`EditorReporte.tsx:385-396`); `frontend/src/pages/Reportes.test.tsx` para montar páginas con Query y simular la API.
- **Seguridad:** #15 (sin `dangerouslySetInnerHTML`; las letras y descripciones se muestran como texto de React).
- **Qué hacer:**
  1. Quita la constante `espacios` y las tres listas `(["A", "B", "C"] as const)`. `vacio.actividades = armarActividades([])`. En la carga (`useEffect`) y en `onSuccess` de `guardar`, usa `armarActividades(datos.actividades)`.
  2. Debajo de `.actividades-stack` agrega `<button type="button" className="btn-secondary">Agregar actividad</button>`. Al hacer clic, agrega `{ letra: siguienteLetra(...), descripcion: "", asignaciones: [] }` al borrador, la marca abierta en `actividadesAbiertas` y pone `sucio` en true. Si `siguienteLetra` es `undefined`, el botón queda `disabled` con `title="Máximo 10 actividades por día"`.
  3. En el encabezado de cada tarjeta abierta (`card-header`) y en la tarjeta plegada, muestra `Quitar` (`btn-secondary btn-sm`) solo si `puedeQuitar(...)` es verdadero. Quita la última del borrador y la saca de `actividadesAbiertas`.
  4. Fotos: `espaciosFotos(borrador.actividades).map(...)` en lugar de `espacios.map(...)`.
  5. El filtro de actividades vacías al guardar (`:145-150`) se queda igual.
- **Criterio de aceptación:** `npm --prefix frontend run test`, `npm --prefix frontend run lint`, `npm --prefix frontend run format:check` y `npm --prefix frontend run build` pasan. Con la app levantada (`make up`), un día nuevo muestra solo A y B. "Agregar actividad" muestra C abierta y su espacio de fotos "Actividad C". Al guardar con D capturada y recargar, se ven A–D.
- **Pruebas requeridas:**
  - El día vacío renderiza "Actividad A" y "Actividad B" y no "Actividad C".
  - Clic en "Agregar actividad" → aparece "Actividad C".
  - Con A–J cargadas, el botón está deshabilitado.
  - "Quitar" no aparece en B, y en C vacía la quita.

## Seguridad

| # | Medida | Aplica | Cómo se cumple en este cambio / prueba que lo demuestra |
|---|---|---|---|
| 8 | Bloquear manipulación de campos | sí | `DiaWrite`/`ActividadWrite` conservan `extra="forbid"`; `id` y horas calculadas siguen asignándose en el servidor. Prueba de la tarea 1: payload con campo extra → 422. |
| 13 | Parametrizar queries | sí | La migración usa SQL estático sin datos de usuario; el resto va por ORM. `rg -n "execute\(f\|text\(f" backend` = 0. |
| 14 | Validar inputs | sí | `Letra` Literal A–J, `max_length=10`, `LIMITES_FOTOS` en el backend; el frontend solo como UX. Pruebas de la tarea 1 (K, 11 elementos, foto D extra). |
| 15 | Sanitizar contenido | sí | `texto_seguro` en las descripciones nuevas del formato actual (prueba con `=`); el mejorado conserva su escape; React sin HTML crudo. |
| 16 | Restringir archivos | sí (sin cambio) | Las fotos de los espacios nuevos pasan por el mismo `procesar_foto` (Pillow, tamaño máximo, nombre generado). La prueba de espacio lleno cubre A y D con el límite de 4. |
| 17 | Devolver datos necesarios | sí (sin cambio) | `DiaRead`/`ActividadRead` no agregan campos. |
| 20 | Escanear dependencias | sí | Sin dependencias nuevas; `make audit`. |

n.a.: 1, 2, 3 (sin secretos nuevos), 4, 6, 7, 9, 10, 11, 12 (sin cuentas, uso local, según PROYECTO.md), 5 (sin datos sensibles nuevos), 18, 19 (sin cambios de nginx/HTTPS).

## Consistencia
- Se reutilizan: los schemas Pydantic con `extra="forbid"`, el manejador de errores de `errors.py` (`SpaceFullError`, `NotFoundError`), `texto_seguro`, el patrón `calculos.ts` y su prueba, y las clases CSS existentes (`btn-secondary`, `btn-sm`, `card`).
- ¿Patrón, librería o capa nueva? **No.** `math.ceil` y `copy.copy` son de la biblioteca estándar.

## Verificación final
```bash
git diff agente/diseno-ui...agente/actividades-dinamicas --stat
make migrations-check
make lint
make test
npm --prefix frontend run build
make audit
rg -n "\"A\", \"B\", \"C\"\]|'A', 'B', 'C'\)" backend/app frontend/src   # solo debe quedar el downgrade de 0002
```

## Riesgos
- **Migración sobre la base real:** al reiniciar el contenedor, `alembic upgrade head` corre solo. Antes de `make up`, Oscar (o Claude al revisar) respalda `data/app.db` (`cp data/app.db data/app.db.antes-0002`). Subir la migración no borra nada; bajarla sí borra D–J.
- **`move_range` y celdas combinadas en openpyxl:** si se recorre mal, se rompen los rangos combinados o el mapa se encima. Lo detectan las pruebas de la tarea 2 (coordenadas exactas, rangos combinados, firmas recorridas) y la revisión visual del PDF con A–J en la revisión.
- **PDF largo:** con 10 actividades la hoja del formato crece 7 renglones de 253.5 pt más 3 bandas. Se valida con `test_pdf_es_valido` y abriendo el PDF en la revisión.
- **Fotos pequeñas:** con 4 fotos en una actividad de un solo renglón, cada foto queda de unos 160 px de alto. Se revisa en el PDF durante la revisión.
- **Fotos huérfanas:** una foto en el espacio D cuya actividad D se vacía sigue existiendo, igual que hoy con C. La regla de "Quitar" impide ocultar el espacio mientras tenga fotos.

## Supuestos y preguntas abiertas
- Resuelto con Oscar (2026-11-08): filas nuevas en el formato actual, máximo A–J, **hasta 4 fotos en todas las actividades**, acomodadas según cuántas haya.
- Supuesto: la rama sale de `agente/diseno-ui` porque `main` todavía no tiene el código. Si Oscar fusiona antes, la base es `main`.
- Supuesto: en el formato actual, A, C y las extras conservan un solo renglón de 253.5 pt (4 fotos en 2×2 quedan a la mitad del alto). B y "Antes y después" siguen con 2 renglones. Si se quieren las fotos más grandes, la alternativa es darle 2 renglones a cada actividad (la hoja crece el doble).
- Sin preguntas abiertas.

## Iteración 1
Origen: `REVISION-20261108-actividades-dinamicas.md`. Mismas reglas, mismas medidas de seguridad. Un commit por tarea.

### Tarea 1.1 — Recorrer también las filas ocultas al insertar filas
- **Archivos:** `backend/app/services/excel_formato.py` (modificar `_insertar_filas`, línea ~152), `backend/tests/test_excel_formato.py` (modificar).
- **Problema:** la plantilla `base_actividades` trae **ocultas las filas 37–50** (debajo del mapa combinado A35:T50). `_insertar_filas` solo copia `height`, así que la marca `hidden` se queda en 37–50 y tapa los renglones recorridos. Con A–J, las actividades A–I y sus fotos no se ven en el Excel ni en el PDF; con D–E, quedan ocultas partes de la tabla.
- **Qué hacer:** en el ciclo de abajo hacia arriba de `_insertar_filas`, copia por fila `height` **y** `hidden` (`hoja.row_dimensions[n + cantidad].hidden = hoja.row_dimensions[n].hidden`). Después, para las filas que quedan libres (`fila .. fila + cantidad - 1`), pon `hidden = False`; quien inserta ya fija su alto.
- **Criterio de aceptación:** una prueba nueva `test_formato_no_oculta_filas_insertadas` con A–J (y otra con A–E) comprueba:
  - Ninguna fila entre 24 y `31 + desplazamiento` (bandas, encabezado, renglones de actividad y "Antes y después") tiene `hidden=True`.
  - Las filas ocultas son exactamente `37 + desplazamiento .. 50 + desplazamiento`.
  - Con solo A–B, las ocultas siguen siendo 37–50 (regresión).
- **Pruebas requeridas:** A–B (regresión), A–E (1 banda), A–J (3 bandas).

### Tarea 1.2 — No perder una actividad vacía que ya tiene fotos
- **Archivos:** `frontend/src/actividades.ts`, `frontend/src/actividades.test.ts`, `frontend/src/pages/EditorReporte.tsx` (las dos llamadas a `armarActividades`), `backend/app/services/excel_formato.py:276`, `backend/tests/test_excel_formato.py`.
- **Problema:** si el usuario agrega D, sube fotos a D y no captura descripción ni personas, D no se guarda (las actividades vacías se filtran). Al recargar, D desaparece del editor y sus fotos ya no se ven ni se pueden borrar. Además, el formato actual no las exporta, porque `extras` solo mira `dia.actividades`.
- **Qué hacer:**
  1. `armarActividades(guardadas: Actividad[], fotos: Foto[] = [])`: la letra más alta se calcula sobre las actividades guardadas **y** los `foto.espacio` que sean letra (se ignora `"AD"`). En `EditorReporte.tsx` pasa `datos.fotos` y `resultado.fotos`.
  2. En `_llenar_dia`, `indice_mas_alto` considera también `foto.espacio` de `dia.fotos` que esté en `LETRAS_ACTIVIDAD`, para que el renglón exista y las fotos se exporten.
- **Criterio de aceptación:**
  - `armarActividades([A], [foto espacio D])` → A, B, C, D.
  - `armarActividades([A], [foto AD])` → A, B.
  - En el backend, un día con actividad A y una foto en D genera el renglón D (`M` = "D", descripción vacía) con 1 imagen en su área.
- **Pruebas requeridas:** los tres casos anteriores.

### Tarea 1.3 — Tipos y constante de ruta de fotos
- **Archivos:** `backend/app/services/excel_formato.py`.
- **Qué hacer:**
  - Cambia `actividades: dict[str, object]` (líneas 156 y 177) por `dict[str, Actividad]`, importando `Actividad` desde `app.models`.
  - Elimina `FOTOS_DIR = Path("/data/fotos")` (línea 24) y usa `fotos.FOTOS_DIR` de `app.services.fotos`, como ya hace `excel_mejorado.py`. Si alguna prueba parchea `excel_formato.FOTOS_DIR`, que parchee `app.services.fotos.FOTOS_DIR`.
- **Criterio de aceptación:** `rg -n 'Path\("/data/fotos"\)' backend/app` → solo `services/fotos.py`; `ruff check .` y `pytest -q` pasan.

### Verificación de la iteración
Los mismos comandos de "Verificación final". Además, genera con datos sintéticos un día A–J con fotos (1, 2, 3 y 4 por espacio), conviértelo a PDF y confirma en el reporte que la hoja del lunes muestra los 10 renglones de actividad.
