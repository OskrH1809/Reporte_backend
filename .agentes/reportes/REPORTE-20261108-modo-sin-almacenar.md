---
id: REPORTE-20261108-modo-sin-almacenar
plan: PLAN-20261108-modo-sin-almacenar
iteracion: 2
rama: agente/modo-sin-almacenar
---

# Reporte de ejecución — Modo sin almacenar

## Resumen

Las siete tareas quedaron completas: la aplicación conserva el modo guardado y añade un modo en memoria controlado por `ALMACENAR=false`, con captura semanal, fotos locales y descargas del formato actual, Excel mejorado y PDF sin persistir reportes ni fotos. La verificación automatizada final pasó y no hay bloqueos.

## Tareas

| # | Tarea | Estado | Commit | Notas |
|---|---|---|---|---|
| 1 | Variable `ALMACENAR`, configuración y rutas | ✅ | `951f5ff` | Dos modos probados; rutas guardadas ausentes con `ALMACENAR=false`. |
| 2 | Modelo único en memoria para Excel | ✅ | `8be3dfe` | Sin `object_session`; foto ausente se omite. |
| 3 | `POST /api/exportar/{tipo}` sin estado | ✅ | `536b736` | Tres formatos sin escrituras en BD o disco. |
| 4 | Frontend según `/api/config` | ✅ | `d9b7017` | Rutas, navegación y cliente de descargas probados. |
| 5 | Formulario compartido del día | ✅ | `64d7775` | 54 pruebas; editor guardado conserva su comportamiento y queda en 346 líneas. |
| 6 | Editor semanal en memoria | ✅ | `224b0c3` | Semana ISO, fotos, confirmación, descargas y aviso de salida; 61 pruebas frontend. |
| 7 | Documentación | ✅ | `437ed58` | README y proyecto describen modos, límites y piezas de referencia. |

## Verificación

Salida real recortada del modo final:

```text
$ git diff agente/actividades-dinamicas...agente/modo-sin-almacenar --stat
37 files changed, 2243 insertions(+), 476 deletions(-)

$ docker build -t tania-api-modos backend
#10 naming to docker.io/library/tania-api-modos:latest done
#10 DONE 0.0s

$ docker run --rm -w /srv tania-api-modos sh -c "ruff check . && ruff format --check . && pytest -q && alembic upgrade head && alembic check && bandit -r app -ll && pip-audit"
All checks passed!
68 files already formatted
.....................................................                    [100%]
53 passed, 5 warnings in 17.66s
Running upgrade  -> 0001, Esquema inicial.
Running upgrade 0001 -> 0002, Amplía las actividades y espacios de fotos hasta la letra J.
No new upgrade operations detected.
No issues identified.
Medium: 0 · High: 0 · #nosec: 0
No known vulnerabilities found

$ npm --prefix frontend run lint && npm --prefix frontend run format:check
All matched files use Prettier code style!

$ npm --prefix frontend run test && npm --prefix frontend run build
Test Files  13 passed (13)
Tests       61 passed (61)
✓ 158 modules transformed.
✓ built in 137ms

$ npm --prefix frontend audit --audit-level=high
exit 0 · 10 vulnerabilidades moderadas · 0 altas o críticas

$ gitleaks detect --no-git -v --source <copia temporal de git archive HEAD>
INF scanned ~529189 bytes (529.19 KB)
INF no leaks found

$ patrones peligrosos sobre git diff agente/actividades-dinamicas...HEAD
Sin coincidencias de secretos, SQL armado, XSS, any, logs de depuración o firmas en código/commits.
```

La comprobación manual con `make up` en ambos modos no se ejecutó porque la Iteración 2 indica preservar la versión anterior levantada y el respaldo local no versionado. Queda pendiente para la revisión. La verificación automatizada cubre ambos valores de `ALMACENAR`, los tres formatos, PDF válido y ausencia de escrituras en la exportación en memoria.

Los comandos backend finales se ejecutaron dentro de una imagen aislada sin volúmenes del host. Para evitar recorrer `data.antes-actividades/`, gitleaks analizó una copia temporal construida solo con `git archive HEAD`. No se abrió `.env`, no se accedió a `data/` o `data.antes-actividades/`, y no se tocó el worktree paralelo.

## Seguridad

| # | Medida | Implementación | Prueba |
|---|---|---|---|
| 8 | Bloquear manipulación de campos | `ReporteExportar`, `DiaExportar` y `FotoExportar` rechazan campos desconocidos. | `test_rechaza_campo_extra`. |
| 13 | Parametrizar consultas | Resolución mediante ORM (`session.get`/`select`), sin SQL construido con texto dinámico. | Patrón peligroso sin coincidencias. |
| 14 | Validar entradas | Se validan seis días únicos, A–J/AD, cuatro fotos por espacio, índices y límites por archivo/total. | Pruebas de cinco días, cinco fotos, índice/entidad inexistente y 413. |
| 15 | Sanitizar contenido | Los dos Excel conservan `texto_seguro`; React no inserta HTML crudo. | Pruebas de fórmulas conservadas y patrón XSS sin coincidencias. |
| 16 | Restringir archivos | `normalizar_foto` valida el tipo real con Pillow, limita dimensiones y re-codifica JPEG sin escribir. | Archivo ejecutable renombrado rechazado y conteos/archivo sin cambios. |
| 17 | Respuestas mínimas | `/api/config` expone solo modo y límite por espacio; exportar devuelve únicamente el archivo. | Prueba de claves exactas en ambos modos. |
| 20 | Dependencias | No se añadieron dependencias. | `pip-audit` limpio; npm audit sin altas/críticas. |

Escaneos: gitleaks ✅ · bandit ✅ · pip-audit ✅ · npm audit ✅ para el umbral alto. Npm reporta 10 vulnerabilidades moderadas transitivas en herramientas de lint; la solución propuesta exige `--force` y un cambio incompatible de ESLint, fuera del alcance.

## Consistencia

- Tarea 1 siguió `routers/health.py`, `Settings` y las pruebas con dependencia de BD reemplazada.
- Tarea 2 siguió el servicio puro `calculos.py` y conservó las comprobaciones de ambos Excel.
- Tarea 3 siguió los schemas `*Write`, `subir_foto`, el formato de errores y `_respuesta`.
- Tarea 4 siguió `api/catalogos.ts`, React Query y el montaje de `Reportes.test.tsx`.
- Tarea 5 siguió los componentes controlados `SelectorColaboradores` y `TablaCantidades`.
- Tarea 6 siguió las funciones puras de `actividades.ts`/`calculos.ts`, el encabezado del editor y `useAvisos`/`Confirmar`.
- Tarea 7 respetó las secciones existentes del README y la tabla de piezas de referencia.
- No se añadieron librerías, capas alternativas, firmas, `any`, excepciones de lint ni cambios de dependencias.

## Desviaciones del plan

- La Tarea 5 ajustó `frontend/src/actividades.ts` y `frontend/src/verificaciones.ts`, autorizados explícitamente por la Iteración 1 para compatibilizar `FotoVista`.
- La Tarea 6 actualizó `frontend/src/App.tsx` y su prueba para sustituir la vista temporal de la Tarea 4 por el editor real; es la conexión prevista entre ambas tareas.
- La prueba manual con `make up` se omitió por instrucción expresa de la Iteración 2 y queda pendiente de revisión.
- El escaneo gitleaks se ejecutó sobre una copia temporal de los archivos versionados para no recorrer la carpeta de respaldo prohibida.

## Bloqueos

Ninguno.

## Métricas

Acumulado: `tareas_completadas=7` · `pruebas_ok=1` · `pruebas_nuevas=23` · `lineas_cambiadas=2712` · `bloqueos=0` · `minutos_ejecucion=41`

Iteración 2: `tareas_completadas=2` · `pruebas_ok=1` · `pruebas_nuevas=7` · `lineas_cambiadas=872` · `bloqueos=0` · `minutos_ejecucion=8`
