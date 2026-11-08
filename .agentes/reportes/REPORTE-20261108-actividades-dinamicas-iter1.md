---
id: REPORTE-20261108-actividades-dinamicas-iter1
plan: PLAN-20261108-actividades-dinamicas
iteracion: 1
rama: agente/actividades-dinamicas
---

# Reporte de ejecución — Actividades dinámicas por día (Iteración 1)

## Resumen
Se corrigieron los tres hallazgos de la revisión: las filas insertadas conservan y desplazan correctamente el estado oculto, las fotos determinan la última actividad visible aunque no haya descripción, y el formato actual reutiliza la ruta compartida y los tipos concretos. La prueba funcional A–J produjo diez actividades visibles, 27 fotos de actividad y un PDF válido. La iteración quedó completa y sin bloqueos.

## Tareas

| # | Tarea | Estado | Commit | Notas |
|---|---|---|---|---|
| 1.1 | Corregir el desplazamiento de filas ocultas | ✅ | `d753002` | Copia `hidden` al desplazar y fuerza visibles las filas nuevas; cubre A–B, A–E y A–J. |
| 1.2 | Conservar actividades vacías que tienen fotos | ✅ | `e089013` | Frontend y Excel calculan la última actividad desde descripciones y espacios de fotos, excluyendo AD. |
| 1.3 | Reutilizar ruta compartida y tipos de fotos | ✅ | `c8ef006` | Usa `fotos.FOTOS_DIR` y `dict[str, Actividad]`; las pruebas parchean el módulo propietario. |

## Verificación

Salida real recortada del modo final:

```text
$ alembic upgrade head && alembic check  # SQLite temporal dentro del contenedor
Running upgrade  -> 0001, Esquema inicial.
Running upgrade 0001 -> 0002, Amplía las actividades y espacios de fotos hasta la letra J.
No new upgrade operations detected.

$ ruff check . && ruff format --check .
All checks passed!
36 files already formatted

$ pytest -q
..........................................                               [100%]
42 passed, 6 warnings in 16.08s

$ npm --prefix frontend run lint && npm --prefix frontend run format:check
Checking formatting...
All matched files use Prettier code style!

$ npm --prefix frontend run test
Test Files  8 passed (8)
Tests       49 passed (49)

$ npm --prefix frontend run build
✓ 153 modules transformed.
✓ built in 161ms

$ prueba funcional sintética A–J y generar_pdf
actividades_visibles=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
filas_actividad_ocultas=[]
imagenes_foto=27
pdf_valido=True bytes=740138

$ gitleaks detect --no-git -v
INF no leaks found

$ bandit -r app -ll
No issues identified.
Medium: 0 · High: 0 · #nosec: 0

$ pip-audit
No known vulnerabilities found

$ npm --prefix frontend audit --audit-level=high
exit 0 · 10 vulnerabilidades moderadas · 0 altas o críticas

$ rg -n '"A", "B", "C"\]|'"'"'A'"'"', '"'"'B'"'"', '"'"'C'"'"'\)' backend/app frontend/src
Sin coincidencias (exit 1).

$ rg -n 'FOTOS_DIR\s*=' backend/app
backend/app/services/fotos.py:9:FOTOS_DIR = Path("/data/fotos")

$ git diff 1ae0968...HEAD --shortstat
5 files changed, 85 insertions(+), 15 deletions(-)
```

No se ejecutaron literalmente los targets `make` porque `docker-compose.yml` monta `./data:/data` y la orden prohíbe tocar `data/`. Se ejecutaron sus comandos equivalentes con la imagen existente, el backend montado en solo lectura y SQLite o directorios temporales dentro del contenedor. No se abrió `.env`, no se montó `data/` y no se usaron datos reales.

## Seguridad

| # | Medida | Implementación | Prueba |
|---|---|---|---|
| 14 | Validar entradas | Los espacios que cuentan para actividades se restringen a `LETRAS_ACTIVIDAD`; AD no amplía la lista. | Pruebas frontend para foto D y AD; prueba backend para foto D sin descripción. |
| 16 | Restringir archivos | El formato actual usa exclusivamente `fotos.FOTOS_DIR`, la ruta validada y compartida por el servicio. | `rg` confirma una sola definición; fotos sintéticas viven en un directorio temporal. |
| 20 | Escanear código y dependencias | No cambiaron manifiestos ni dependencias. | gitleaks, bandit, pip-audit y npm audit ejecutados. |

Escaneos: gitleaks ✅ · bandit ✅ · pip-audit ✅ · npm audit ✅ para el umbral alto. Npm mantiene 10 vulnerabilidades moderadas transitivas de herramientas de lint. La solución propuesta requiere `--force` y un cambio incompatible de ESLint, fuera del alcance de esta iteración; no se introdujeron dependencias nuevas.

## Consistencia

- Tarea 1.1 conservó el helper `_insertar_filas` y el patrón de pruebas parametrizadas del formato actual.
- Tarea 1.2 reutilizó `LETRAS_ACTIVIDAD` en backend y `indiceActividad`/`LETRAS_ACTIVIDAD` en frontend, sin duplicar otra lista de letras.
- Tarea 1.3 siguió el patrón de `excel_mejorado.py`: importar el módulo propietario de `FOTOS_DIR` y usar el modelo `Actividad` en las firmas.
- No se añadieron librerías, capas, estilos alternativos, firmas ni cambios de dependencias.

## Desviaciones del plan

- Ningún archivo de código quedó fuera de los indicados por la Iteración 1.
- La verificación final sustituyó los targets `make` por comandos equivalentes sin el volumen `./data`, para respetar la prohibición de tocar datos reales.
- Tarea 1.1 pasó en el segundo intento tras aplicar formato; Tarea 1.2 necesitó un segundo intento backend por formato; Tarea 1.3 pasó en el tercer intento tras corregir sombreado y formato. La verificación final completa pasó.

## Bloqueos

Ninguno.

## Métricas

Iteración 1: `tareas_completadas=3` · `pruebas_ok=1` · `pruebas_nuevas=6` · `lineas_cambiadas=100` · `bloqueos=0` · `minutos_ejecucion=10`

Acumulado del plan en `.agentes/metricas.csv`: `tareas_completadas=5` · `pruebas_nuevas=28` · `lineas_cambiadas=1169` · `minutos_ejecucion=42`.
