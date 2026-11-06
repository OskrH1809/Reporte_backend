---
id: REVISION-20261105-reportes-servicios
plan: PLAN-20261105-reportes-servicios
iteracion: 0
veredicto: cambios
autor: claude
---

# Revisión — Plataforma de reportes de servicios generales

## Verificación repetida
- `make check`: sin fallos en lint, pruebas, gitleaks, bandit ni pip-audit; `npm audit` con 10 moderadas transitivas de la cadena de eslint, que no llegan al build de producción.
- Catálogos en vivo: 13, 14, 11 y 2.
- Prueba de punta a punta por nginx con la semana 38 y 18 fotos reales: creación, horas (`A, B` da 4 + 4), feriado, tres descargas con nombres correctos. Reporte de prueba borrado después.
- Render de original y generado con LibreOffice: el formato actual coincide en estructura, 8 páginas y anchos de columna. Sin marcas de mapa, por decisión de Oscar.

## Hallazgos
| # | Severidad | Archivo | Problema |
|---|---|---|---|
| 1 | Alta | `backend/app/routers/reportes.py` `guardar_dia` | Segundo `PUT` del mismo día responde 500 por `UNIQUE(dia_id, letra)`. Impide editar. |
| 2 | Alta | `frontend/src/pages/EditorReporte.tsx` | Subir o borrar foto descarta el borrador sin guardar. |
| 3 | Alta | `backend/app/services/excel_mejorado.py` | Fotos sobre tablas, foto partida entre páginas, mapa e imágenes deformados, totales como texto, diseño poco legible. |
| 4 | Media | `frontend/src/components/SelectorFotos.tsx`, `EditorReporte.tsx` | Errores de foto invisibles; una foto cada vez. |
| 5 | Media | `EditorReporte.tsx` | Horas y totales solo tras guardar. |
| 6 | Media | `backend/alembic/versions/0001_esquema_inicial.py` | `create_all` en la migración rompe la siguiente migración. |
| 7 | Baja | exportadores, `calculos.py`, reporte | Jornada escrita a mano, advertencia con id, texto de fotos vacío, datos erróneos en el reporte (10 MB, 507). |

## Seguridad
Medidas 1, 2, 7, 8, 13, 14, 15, 16, 17, 18 y 20: implementadas y con prueba. Sin hallazgos de seguridad. `texto_seguro` evita inyección de fórmulas en Excel. Revisión de n.a.: la app solo publica 127.0.0.1.

## Veredicto
`cambios`: ver Iteración 1 del plan.

## Iteración 1 — revisión y relevo
Codex aplicó I1 a I5 y se quedó sin límite. Oscar pidió a Claude terminar lo pendiente, por lo que Claude corrigió directamente en la rama:

| Tarea | Commit | Hallazgo |
|---|---|---|
| I6 | `aef335c` + formato | Título de fotos separado de sus imágenes, tira de imagen en la página anterior, encabezado "Miércoles" cortado |
| I7 | `b03c3f7` | **Alta:** Guardar respondía 422 desde el navegador con cualquier persona seleccionada: enviaba campos de lectura y la API usa `extra="forbid"`. Las pruebas simulaban la API |
| I8 | `e895f5b` | Selector fuera de su tarjeta, pestaña activa sin resaltar, lista centrada verticalmente |

Verificación final: `make check` con salida 0 (25 pruebas backend, 13 frontend, gitleaks, bandit y pip-audit sin hallazgos; `npm audit` con 10 moderadas de la cadena de eslint, sin altas). Prueba en Chromium real: selección de personas, horas en vivo, foto sin perder borrador, guardar, recargar y guardar de nuevo, sin errores de consola. PDF de la semana 38 revisado página por página.

Lección: las pruebas de componentes con la API simulada no detectaron que Guardar estaba roto; un flujo de interfaz requiere prueba en navegador contra la API real.

## Veredicto final
`aceptado`. Rama lista para que Oscar decida el merge. Fuera de alcance acordado: marcas del mapa.
