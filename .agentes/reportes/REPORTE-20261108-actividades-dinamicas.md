---
id: REPORTE-20261108-actividades-dinamicas
plan: PLAN-20261108-actividades-dinamicas
iteracion: 0
rama: agente/actividades-dinamicas
---

# Reporte de ejecución — Actividades dinámicas por día (A–J)

## Resumen
Se implementaron actividades A–J en backend, migración, ambos Excel, PDF y editor React, con hasta cuatro fotos por espacio y filas/bandas dinámicas en el formato actual. Las cinco tareas quedaron completas, verificadas y sin bloqueos.

## Tareas
| # | Tarea | Estado | Commit | Notas |
|---|---|---|---|---|
| 1 | Ampliar letras y espacios en modelo, migración, schemas y límites | ✅ | `93f3736` | Restricciones A–J/AD, máximo 10 y cuatro fotos por espacio. |
| 2 | Insertar renglones, bandas y fotos en el formato actual | ✅ | `47dd546` | Hasta tres bandas, filas desplazadas, fórmulas y cuadrículas 1/2/4. |
| 3 | Fotos y etiquetas A–J en el Excel mejorado | ✅ | `376f94a` | Espacios derivados de la constante compartida y D con cuatro fotos. |
| 4 | Tipos y funciones puras de actividades en frontend | ✅ | `bd13184` | Tipos A–J y helpers para armar, agregar, quitar y listar fotos. |
| 5 | Botones Agregar actividad y Quitar en el editor | ✅ | `ab92366` | Editor A–B inicial, carga hasta J y eliminación segura de la última vacía. |

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

$ npm --prefix frontend run lint && npm --prefix frontend run format:check
All matched files use Prettier code style!

$ pytest -q
38 passed, 5 warnings in 12.35s

$ npm --prefix frontend run test
Test Files  8 passed (8)
Tests       47 passed (47)

$ npm --prefix frontend run build
✓ 153 modules transformed.
✓ built in 139ms

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

$ git diff agente/diseno-ui...HEAD --shortstat
15 files changed, 910 insertions(+), 159 deletions(-)
```

No se ejecutaron literalmente los targets `make migrations-check`, `make lint`, `make test` y `make audit` porque `docker-compose.yml` monta `./data:/data`, y la orden prohibió tocar `data/`. Se ejecutaron sus comandos equivalentes con la misma imagen, el backend actual montado en `/srv` y una SQLite temporal dentro del contenedor. No se levantó la aplicación contra la base real.

## Seguridad
| # | Medida | Implementación | Prueba |
|---|---|---|---|
| 8 | Bloquear manipulación de campos | Los schemas conservan `extra="forbid"`; los campos de lectura siguen fuera de la entrada. | `test_guardar_dia_rechaza_actividades_invalidas` incluye campo extra. |
| 13 | Parametrizar queries | La migración usa SQL estático; la aplicación conserva ORM SQLAlchemy. | Patrón `execute(f`/`text(f` sin coincidencias en el diff. |
| 14 | Validar inputs | `Literal` A–J, máximo 10 actividades y límites backend de cuatro fotos. | A–J feliz; 11, K y duplicadas devuelven 422; foto K devuelve 404. |
| 15 | Sanitizar contenido | Las descripciones extras pasan por `texto_seguro`; React renderiza texto sin HTML crudo. | `test_formato_escapa_formula_en_actividad_extra`; patrón XSS sin coincidencias. |
| 16 | Restringir archivos | Los espacios nuevos reutilizan `procesar_foto` y toman solo archivos existentes en Excel. | A y D aceptan cuatro fotos y rechazan la quinta; cuadrículas usan imágenes sintéticas. |
| 17 | Devolver datos necesarios | No se añadieron campos de salida ni serializers genéricos. | Schemas explícitos; patrón `__all__` de campos sin coincidencias. |
| 20 | Escanear dependencias | No cambiaron manifiestos ni dependencias. | gitleaks, bandit, pip-audit y npm audit ejecutados. |

Escaneos: gitleaks ✅ · bandit ✅ · pip-audit ✅ · npm audit ✅ para el umbral alto. Npm reporta 10 vulnerabilidades moderadas transitivas en herramientas de lint; la corrección ofrecida exige `--force` y un cambio incompatible de ESLint, fuera del alcance. Como no cambiaron dependencias, no son introducidas por este plan.

## Consistencia
- Tarea 1 siguió `0001_esquema_inicial.py`, `test_migracion_ida_y_vuelta_sqlite` y `test_espacio_lleno`.
- Tarea 2 siguió los helpers privados de `excel_formato.py`, `texto_seguro` y `test_formato_tiene_hojas_celdas_y_formulas`.
- Tarea 3 siguió `_seccion_fotos` y amplió `test_mejorado_distribuye_fotos_y_formulas_sin_superposicion`.
- Tarea 4 siguió `calculos.ts` y `calculos.test.ts`, con funciones puras en el mismo nivel.
- Tarea 5 reutilizó las clases de botones existentes y el montaje de página con QueryClient de las pruebas actuales.
- No se añadieron librerías, capas, estilos alternativos, `any`, firmas ni cambios de dependencias.

## Desviaciones del plan
- Ningún archivo de código quedó fuera de la lista del plan.
- La verificación final sustituyó los targets `make` por comandos equivalentes sin el volumen `./data`, como exige la orden de no tocar datos reales.
- Las semanas sintéticas de las pruebas nuevas del formato se movieron a 1–11 para no colisionar con semanas usadas por otros módulos en la suite completa.
- Tarea 1 necesitó correcciones de sintaxis y formato; Tarea 2 agotó tres intentos por formato y fixtures; Tarea 3 agotó tres intentos de estilo; Tarea 4 requirió aplicar Prettier; Tarea 5 pasó en el segundo intento tras ajustar selectores asíncronos. La verificación final completa pasó.

## Bloqueos
Ninguno.

## Métricas
`tareas_completadas=5` · `pruebas_ok=1` · `pruebas_nuevas=22` · `lineas_cambiadas=1069` · `bloqueos=0` · `minutos_ejecucion=32`
