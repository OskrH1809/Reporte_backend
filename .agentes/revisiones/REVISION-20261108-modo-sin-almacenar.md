---
id: REVISION-20261108-modo-sin-almacenar
plan: PLAN-20261108-modo-sin-almacenar
rama: agente/modo-sin-almacenar
iteracion: 2
veredicto: aceptado
fecha: 2026-11-08
autor: claude
---

# Revisión — Dos modos con `ALMACENAR`

## Checklist
- [x] Cada tarea cumple su criterio de aceptación (7/7). Las tareas 5 y 6 se bloquearon por el límite de 3 intentos y se cerraron en las iteraciones 1 y 2.
- [x] Verificación final re-ejecutada por Claude:
  - Backend (imagen sin el volumen `./data`): ruff limpio, `pytest -q` 53 passed, `alembic upgrade head && alembic check` sin pendientes, bandit y pip-audit limpios.
  - Frontend: lint, format, `test` (61 passed en 13 archivos) y `build` en verde.
- [x] Solo archivos del plan: 33 archivos de código. `actividades.ts` y `verificaciones.ts` cambian una línea cada uno para el tipo `FotoVista`; Codex lo justificó en Desviaciones y es válido.
- [x] Pruebas de los casos feliz, borde y error (`test_exportar_memoria.py`: 5 fotos, `.exe`, colaborador inexistente, 5 días, campo extra, tope 413, BD sin cambios).
- [x] Sin datos reales, secretos ni logs sensibles. gitleaks limpio.
- [x] Zonas protegidas intactas: sin migraciones ni autenticación.
- [x] Medidas que aplican (#8, #13, #14, #15, #16, #17, #20) implementadas y con prueba.
- [x] Consistencia: un solo camino de generación (`ReporteMemoria` + `desde_orm`), `FormularioDia` compartido (`EditorReporte.tsx` de 637 a 346 líneas) y sin dependencias nuevas.
- [x] Commits `tipo(alcance): …` con la identidad de Oscar y sin firmas.

## Prueba de punta a punta (Claude)
Contenedores aislados (`api` + `web`, puerto 18090) con una carpeta de datos temporal; no se tocaron los contenedores ni los datos de Oscar.
- **`ALMACENAR=false`:**
  - `/api/config` devuelve `{"almacenar": false, "max_fotos_por_espacio": 4}` y `GET /api/reportes` responde 404.
  - Se envió a `POST /api/exportar/{formato,mejorado,pdf}` una semana sintética (lunes A–E, martes A) con 4 fotos de 1600 px. Las tres respuestas fueron 200, con los nombres `CH-RSG-45-2026.xlsx`, `CH-RSG-45-2026_mejorado.xlsx` y `CH-RSG-45-2026_mejorado.pdf` (4.4 MB, 4.1 MB y 1.4 MB).
  - El formato tiene A–E en sus renglones, la banda D–E, la foto de A y las 2 de D en su renglón, y las filas ocultas desplazadas.
  - Al terminar, la BD tiene **0 reportes y 0 fotos** y `/data/fotos` está vacío.
- **`ALMACENAR=true`:** `/api/config` devuelve true; listar, crear y exportar reportes guardados funciona como antes.

## Hallazgos
| Severidad | Archivo:línea | Problema | Cambio pedido |
|---|---|---|---|
| baja | `frontend/src/pages/EditorSemana.tsx:91` | El máximo de 4 fotos está fijo en el código en lugar de leer `max_fotos_por_espacio` de `/api/config`. Hoy coincide. | No bloquea; se puede tomar en `reabrir-excel` si se toca ese archivo. |

## Pendiente (Oscar)
- Prueba manual en navegador con `ALMACENAR=false`: capturar, descargar y abrir los archivos. La API ya está probada de punta a punta; falta la interacción visual.

## Veredicto
`aceptado`. Los dos modos funcionan y el modo sin almacenar no escribe nada en la BD ni en disco.

## Métricas
`primera_pasada=no` · `iteraciones=2` · `archivos_fuera_alcance=0` · `violaciones_normas=0` · `hallazgos_seguridad=0` · `inconsistencias=0`
