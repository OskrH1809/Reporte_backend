---
id: REPORTE-20261105-reportes-servicios
plan: PLAN-20261105-reportes-servicios
iteracion: 0
rama: agente/reportes-servicios
autor: codex
---

# Reporte de ejecución — Reportes semanales de servicios

## Resumen
Quedó implementada la aplicación local completa para capturar reportes semanales, administrar catálogos, registrar horas y fotos, y exportar el formato actual, un Excel mejorado y PDF. Las siete tareas terminaron; no quedaron bloqueos.

## Tareas
| # | Tarea | Estado | Commit | Notas |
|---|---|---|---|---|
| 1 | Esqueleto y Docker | ✅ | `46e0239`, `56a9c23`, `3e1e7c0`, `7664117` | Entorno local, controles de permisos y dependencias corregidas. |
| 2 | Catálogos y carga inicial | ✅ | `2f7a17a` | Esquema, migración, CRUD y semillas idempotentes. |
| 3 | API de reportes, horas y fotos | ✅ | `b714a5f` | Cálculos, validaciones, límites y almacenamiento local. |
| 4 | Excel con el formato actual | ✅ | `e418333` | Conserva hojas, celdas, letras y fórmulas de la plantilla. |
| 5 | Excel mejorado y PDF mejorado | ✅ | `7e108ec` | Libro mejorado y conversión real con LibreOffice. |
| 6 | Interfaz: catálogos y reportes | ✅ | `5e3fe6f` | CRUD de catálogos, listado y creación de reportes. |
| 7 | Interfaz: editor del reporte | ✅ | `c455057` | Editor diario, colaboradores, materiales, fotos y exportaciones. |

## Verificación
Salida real recortada de la verificación final:

```text
$ make up
Image proyecto_tania-api Built
Image proyecto_tania-web Built
Container proyecto_tania-api-1 Started

$ curl -fsS http://127.0.0.1:8090/api/health
{"status":"ok"}

$ make check
No new upgrade operations detected.
All checks passed!
58 files already formatted
ESLint: passed
All matched files use Prettier code style!
19 passed, 1 warning in 3.50s
Test Files  2 passed (2)
Tests       6 passed (6)
No leaks found
Bandit: No issues identified (high 0, medium 0, low 1)
No known vulnerabilities found
npm audit --audit-level=high: exit 0 (10 moderadas; 0 altas o críticas)

$ curl -fOJ http://127.0.0.1:8090/api/reportes/1/exportar/pdf
100 73817
$ file CH-RSG-52-2025_mejorado.pdf
PDF document, version 1.7, 1 page(s)
$ head -c 8 CH-RSG-52-2025_mejorado.pdf
%PDF-1.7
```

El reporte usado para la prueba HTTP fue sintético (semana 52 de 2025) y el archivo descargado quedó únicamente en `/tmp`. No se abrió ni versionó el archivo real de la raíz.

## Seguridad
| # | Medida | Implementación | Prueba |
|---|---|---|---|
| 1 | Validación de entrada | Esquemas Pydantic, semanas válidas, catálogos activos y nombres de archivo normalizados. | `test_tipo_invalido_y_nombre_vacio`, `test_reporte_duplicado_devuelve_codigo` |
| 2 | Acceso a registros | Respuestas 404 para ids inexistentes y asociación de fotos al día del reporte. | `test_exportar_reporte_inexistente`, `test_foto_invalida_y_mayor_al_maximo` |
| 3 | Subidas seguras | Lista permitida de MIME/extensiones, máximo de 10 MB y nombres generados por UUID. | `test_foto_invalida_y_mayor_al_maximo` |
| 4 | Capacidad de disco | Límite configurable y respuesta 507 antes de escribir. | `test_espacio_lleno` |
| 5 | Ejecución y exposición local | Contenedor API baja privilegios a `app`; servicio publicado solo en `127.0.0.1`; LibreOffice usa argumentos fijos sin shell. | `make up`, revisión del diff, Bandit |

Escaneos: gitleaks ✅ · bandit ✅ (sin hallazgos medios/altos) · pip-audit ✅ · npm audit ✅ para el umbral alto (10 vulnerabilidades moderadas transitivas sin corrección no disruptiva disponible).

## Consistencia
Se siguió el molde de solo lectura de `/home/oskrh/proyectos/Asistencia` para la estructura FastAPI/React, el manejo uniforme de errores y el estilo de pruebas. Los recursos se copiaron exclusivamente desde `.agentes/insumos/`; no se consultaron `.env` ni datos reales.

## Desviaciones del plan
- Se añadieron `.gitignore` y `frontend/.prettierignore` para excluir SQLite, fotos, salidas generadas, `dist` y artefactos de TypeScript de los chequeos y del versionado.
- Se ajustó `backend/Dockerfile` durante la verificación final para preparar permisos del volumen y ejecutar el proceso como usuario sin privilegios.
- Se actualizó Pillow de 12.1.1 a 13.0.0 porque `pip-audit` detectó vulnerabilidades conocidas en la versión inicial.
- La verificación aislada de la tarea 4 agotó tres intentos por contaminación entre fixtures; se corrigió el aislamiento y la suite final confirmó las dos pruebas del formato junto con las 19 pruebas backend.

## Bloqueos
Ninguno.

## Métricas
`tareas_completadas=7` · `pruebas_ok=1` · `pruebas_nuevas=25` · `lineas_cambiadas=8032` · `bloqueos=0` · `minutos_ejecucion=44`
