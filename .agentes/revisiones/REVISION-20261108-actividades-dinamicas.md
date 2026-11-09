---
id: REVISION-20261108-actividades-dinamicas
plan: PLAN-20261108-actividades-dinamicas
rama: agente/actividades-dinamicas
iteracion: 1
veredicto: aceptado
fecha: 2026-11-08
autor: claude
---

# Revisión — Actividades dinámicas por día (A–J)

## Checklist
- [ ] Cada tarea cumple su criterio de aceptación: las pruebas pasan, pero T2 falla en el resultado real (ver hallazgo 1).
- [x] Verificación final re-ejecutada por Claude y en verde. Imagen construida desde la rama y corrida **sin** el volumen `./data`:
  - `ruff check`/`format --check`: limpio.
  - `pytest -q`: 38 passed.
  - `alembic upgrade head && alembic check` sobre SQLite temporal: sin operaciones pendientes.
  - Frontend: `lint`, `format:check`, `test` (47 passed) y `build` en verde.
- [x] Solo se tocaron archivos del plan: 17 archivos, todos listados (más el reporte y la fila de métricas).
- [x] Las pruebas nuevas cubren los casos feliz, borde y error (22 nuevas).
- [x] Sin datos personales reales, secretos ni logs sensibles: `rg` sin `print`/`console.log`/`token` en el diff.
- [x] Zona protegida aprobada por Oscar. `downgrade` borra D–J con SQL estático y lo indica en un comentario. Respaldo en `data/app.db.antes-0002`.
- [x] Medidas que aplican (#8, #13, #14, #15, #16, #17, #20) implementadas y con prueba.
- [x] Escaneos: gitleaks sin fugas; bandit sin hallazgos; pip-audit sin vulnerabilidades (solo el paquete local no auditable); `npm audit --audit-level=high` con exit 0.
- [x] Código consistente con los patrones citados, salvo los hallazgos 3 y 4.
- [x] Formateadores sin cambios ajenos.
- [x] 6 commits `tipo(alcance): …` con la identidad de Oscar, sin firmas ni `Co-authored-by`.

## Prueba funcional (Claude)
Reporte sintético en un contenedor aislado (sin `./data`): lunes con A–J; fotos A=1, B=4, C=2, D=4, E=3, J=4 y AD=2; martes solo con A. Se exportaron el formato actual, el mejorado y los dos PDF.
- **Mejorado y su PDF:** correctos. Las tablas tienen A–J, las fotos de cada actividad se acomodan de 2 en 2 con su etiqueta y el resumen suma 11 actividades.
- **Formato actual, martes (solo A):** idéntico al de antes.
- **Formato actual, lunes (A–J):** **incorrecto**. Solo se ven la tercera banda (cortada), el renglón J y "Antes y después". Las fotos de A–I se ven apiladas sobre el renglón J. Causa: las filas 41–50 tienen `hidden=True`.

## Hallazgos
| Severidad | Archivo:línea | Problema | Cambio pedido |
|---|---|---|---|
| alta (funcional) | `backend/app/services/excel_formato.py:152` | `_insertar_filas` copia `height` pero no `hidden`. La plantilla oculta las filas 37–50 (debajo del mapa), así que esas marcas se quedan fijas y tapan los renglones recorridos. Con A–J se ocultan las actividades A–I y sus fotos en el Excel y el PDF. Las pruebas no lo detectaron porque no revisan `hidden`. | Iteración 1, tarea 1.1 |
| media | `frontend/src/actividades.ts:3`, `backend/app/services/excel_formato.py:276` | Una actividad agregada con fotos pero sin descripción ni personas no se guarda. Al recargar desaparece con sus fotos, que quedan inaccesibles en el editor y fuera del formato actual. | Iteración 1, tarea 1.2 |
| baja (inconsistencia) | `backend/app/services/excel_formato.py:24` | Segunda definición de `FOTOS_DIR`; `excel_mejorado.py` ya usa `fotos.FOTOS_DIR`. | Iteración 1, tarea 1.3 |
| baja | `backend/app/services/excel_formato.py:156`, `:177` | `dict[str, object]` en lugar de `dict[str, Actividad]`: oculta el tipo real (`.descripcion` sobre `object`). | Iteración 1, tarea 1.3 |

## Fuera de este plan (para plan aparte)
- La imagen instala el paquete `app` en `site-packages` **sin** `plantillas/plantilla_formato.xlsx` (falta como *package data* en `pyproject.toml`). Hoy funciona porque uvicorn corre desde `/srv` y toma la carpeta fuente, pero cualquier ejecución con `python -I` o desde otro directorio falla con `FileNotFoundError`.
- La migración no se probó sobre una copia de la base real porque no hubo permiso. Está cubierta con datos sintéticos (ida y vuelta) y hay respaldo antes de aplicarla.

## Veredicto
`cambios`. Backend, API, mejorado y editor están bien. El formato actual oculta las actividades cuando hay más de tres, que es justo el caso que pide el plan. Las correcciones van en "Iteración 1" del plan.

## Métricas
`primera_pasada=no` · `iteraciones=1` · `archivos_fuera_alcance=0` · `violaciones_normas=0` · `hallazgos_seguridad=0` · `inconsistencias=1`

## Iteración 1 — veredicto: aceptado
Commits `d753002` (filas ocultas), `e089013` (espacios con fotos), `c8ef006` (tipos y `fotos.FOTOS_DIR`) y el reporte `REPORTE-20261108-actividades-dinamicas-iter1.md`. Solo se tocaron archivos de la iteración (5).

### Verificación re-ejecutada por Claude
- Backend: ruff limpio; `pytest -q` 42 passed; `alembic upgrade head && alembic check` sin pendientes; bandit y pip-audit limpios.
- Frontend: lint, format, `test` (49 passed) y `build` en verde; `npm audit --audit-level=high` exit 0. gitleaks sin fugas.
- Prueba funcional con el mismo reporte sintético:
  - Formato actual, lunes A–J: los 10 renglones de actividad se ven con sus descripciones y letras.
  - Fotos acomodadas según su número: A=1 completa, C=2 lado a lado, B, D y J=4 en 2×2, E=3, AD=2.
  - Las 3 bandas de horas son visibles y el mapa, la observación y las firmas quedan debajo, sin encimarse.
  - Martes (solo A) igual que antes.

### Hallazgos
- Los cuatro hallazgos de la iteración 0 están resueltos.
- Observación (no bloquea): la hoja está configurada con "ajustar a 1 página". Con A–J, el día completo se encoge para caber en una hoja carta y el texto queda pequeño. Si Oscar lo pide, va en un plan aparte permitir varias páginas de alto (`fitToHeight = 0`).

### Métricas
`primera_pasada=no` · `iteraciones=1` · `archivos_fuera_alcance=0` · `violaciones_normas=0` · `hallazgos_seguridad=0` · `inconsistencias=1`
