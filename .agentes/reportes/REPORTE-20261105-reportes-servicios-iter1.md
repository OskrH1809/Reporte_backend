---
id: REPORTE-20261105-reportes-servicios-iter1
plan: PLAN-20261105-reportes-servicios
iteracion: 1
rama: agente/reportes-servicios
autor: codex
---

# Reporte de ejecución — Reportes semanales de servicios, Iteración 1

## Resumen
Se corrigieron los cinco hallazgos de la revisión: guardado repetido, persistencia y cálculo en vivo del editor, diseño del Excel/PDF mejorado, migración explícita y ajustes de jornadas, advertencias y texto inicial. No quedaron bloqueos ni reportes de prueba en la base local.

## Tareas
| # | Tarea | Estado | Commit | Notas |
|---|---|---|---|---|
| I1 | Guardar un día más de una vez | ✅ | `d51ec5d` | `flush()` antes de reemplazar hijos; conserva horas manuales. |
| I2 | Editor: capturas, fotos y horas en vivo | ✅ | `d3b2440` | Borrador estable, carga múltiple secuencial, errores visibles y cálculo local. |
| I3 | Rehacer el diseño del Excel mejorado | ✅ | `19c72e0` | Rejilla A:L, tablas, fórmulas, alturas, saltos y anclajes proporcionales. |
| I4 | Migración explícita | ✅ | `b17ac8c` | Once tablas con `op.create_table` y `drop_table` inverso. |
| I5 | Ajustes menores | ✅ | `6b1e04b` | Jornada configurable, nombres en advertencias, texto predeterminado y reporte corregido. |

## Verificación
Salida real recortada del modo final:

```text
$ make up && curl --retry 20 --retry-all-errors -fsS http://127.0.0.1:8090/api/health
Image proyecto_tania-api Built
Image proyecto_tania-web Built
Container proyecto_tania-api-1 Started
Container proyecto_tania-web-1 Started
{"status":"ok"}

$ make check
No new upgrade operations detected.
All checks passed!
59 files already formatted
All matched files use Prettier code style!
25 passed, 4 warnings in 5.20s
Test Files  3 passed (3)
Tests       12 passed (12)
no leaks found
Bandit: No issues identified (high 0, medium 0, low 1; #nosec 0)
No known vulnerabilities found
npm audit --audit-level=high: exit 0 (10 moderadas; 0 altas o críticas)

$ curl -fOJ http://127.0.0.1:8090/api/reportes/1/exportar/pdf
100 78840
$ file CH-RSG-51-2026_mejorado.pdf
PDF document, version 1.7, 1 page(s)
$ head -c 8 CH-RSG-51-2026_mejorado.pdf
%PDF-1.7

$ curl -fsS -X DELETE http://127.0.0.1:8090/api/reportes/1
$ curl -fsS http://127.0.0.1:8090/api/reportes
[]
```

La prueba HTTP usó únicamente la semana sintética 51 de 2026 y descargó el PDF en `/tmp`. Antes se eliminó por API `CH-RSG-52-2025`; la lista final quedó vacía. No se abrió ni versionó `CH-RSG-38-2026.xlsx`.

## Seguridad
| # | Medida | Implementación | Prueba |
|---|---|---|---|
| 7, 8 | Integridad al reemplazar registros | El reemplazo del día elimina y vacía hijos antes de insertar, dentro de la misma transacción. | `test_guardar_dia_dos_veces`, `test_guardar_dia_conserva_horas_manuales` |
| 14 | Validación y cálculos | El frontend replica el reparto sin alterar horas manuales; el backend sigue siendo la fuente al guardar. | `frontend/src/calculos.test.ts`, `backend/tests/test_calculos.py` |
| 15 | Salidas Excel seguras | `Formula` separa fórmulas internas de texto de usuario, que continúa pasando por `texto_seguro`. | `test_mejorado_distribuye_fotos_y_formulas_sin_superposicion` |
| 16 | Fotos | Selección múltiple respeta el espacio libre y sube secuencialmente; el backend conserva sus validaciones de contenido y tamaño. | `conserva el borrador después de subir una foto`, `muestra el error al subir una foto` |
| 20 | Dependencias | No se añadieron dependencias; se repitieron auditorías Python y Node. | `pip-audit`, `npm audit --audit-level=high` |

Escaneos: gitleaks ✅ · bandit ✅ · pip-audit ✅ · npm audit ✅ para el umbral alto. Quedan 10 vulnerabilidades moderadas transitivas de herramientas de desarrollo, cuya corrección disponible requiere un cambio incompatible de ESLint.

## Consistencia
- I1 siguió `backend/app/routers/reportes.py` y sus pruebas existentes.
- I2 siguió React Query y el manejo de errores de `frontend/src/pages/Catalogos.tsx`; el cálculo puro refleja `backend/app/services/calculos.py`.
- I3 conservó el servicio y endpoint existentes y reutilizó el patrón `OneCellAnchor` de `excel_formato.py`.
- I4 refleja exactamente los modelos SQLAlchemy actuales mediante operaciones Alembic explícitas.
- I5 centralizó la regla en el servicio existente, sin crear otra capa ni añadir librerías.
- Las coincidencias finales de patrones fueron justificadas: `http://api:8000` es el upstream interno de nginx y `autor: codex/claude` pertenece a metadatos obligatorios de `.agentes/`, no a código ni firmas de commits.

## Desviaciones del plan
- Se añadió `backend/tests/test_migraciones.py`, no listado en I4, porque la tarea exigía una prueba automatizada de `upgrade → downgrade → upgrade`.
- En I5 se ajustaron `backend/tests/test_exportar.py` y `backend/tests/test_excel_formato.py` para que nombres y órdenes sintéticos no colisionaran con la plantilla ni con semillas creadas por otras pruebas.
- I3 necesitó tres intentos: primero falló la copia de fuente Arial y después un largo de línea; el tercero pasó completo.
- I4 necesitó dos intentos por cuatro correcciones automáticas de estilo; el segundo pasó completo.
- I5 agotó tres intentos aislados por contaminación entre fixtures y un formato pendiente. Tras aplicar el formateador, la verificación final completa pasó con 25 pruebas backend y 12 frontend.

## Bloqueos
Ninguno.

## Métricas
`tareas_completadas=5` · `pruebas_ok=1` · `pruebas_nuevas_o_modificadas=13` · `lineas_cambiadas_iteracion=1252` · `bloqueos=0` · `minutos_ejecucion=36`
