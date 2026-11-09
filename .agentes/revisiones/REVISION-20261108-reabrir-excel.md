---
id: REVISION-20261108-reabrir-excel
plan: PLAN-20261108-reabrir-excel
rama: agente/modo-sin-almacenar
iteracion: 0
veredicto: aceptado
fecha: 2026-11-08
autor: claude
---

# Revisión — Reabrir una semana subiendo el Excel

## Ejecución
- Tareas 1–5: Codex (`e7048a1`, `a80aa5f`, `618d7d1`, `28e5a66` y `01941ba`).
- Codex se quedó sin tokens durante la tarea 6, con la documentación escrita pero sin commit y sin reporte. Oscar pidió que Claude continuara: Claude revisó y confirmó la documentación (`a20fa5d`), hizo la verificación y la prueba de punta a punta. Esta revisión sustituye al reporte que faltó.

## Checklist
- [x] Criterios de aceptación de las 6 tareas.
- [x] Verificación re-ejecutada por Claude:
  - Backend: ruff limpio, `pytest -q` 70 passed, bandit y pip-audit limpios.
  - Frontend: lint, format, `test` (66 passed) y `build` en verde.
- [x] Archivos: 21, todos del plan. `exportar.py`, `schemas/exportar.py`, `actividades.ts` y `FormularioDia.tsx` cambian para pasar el respaldo y los avisos; están previstos en las tareas 1 y 5.
- [x] Seguridad: `defusedxml==0.7.1` fijado; `_validar_zip` comprueba la firma `PK\x03\x04`, un máximo de 2 000 entradas, 300 MB descomprimido y rutas absolutas o con `..`; hay tope de MB, `load_workbook(..., data_only=False, keep_vba=False)` y nada se escribe a disco ni en la BD. Las fotos del respaldo se validan con `normalizar_foto`; las fórmulas editadas se leen como texto.
- [x] El respaldo va en una hoja `veryHidden` (`_respaldo`) y no aparece en el PDF.
- [x] Sin datos reales ni secretos. Commits sin firmas.

## Prueba de punta a punta (Claude)
Contenedor aislado con `ALMACENAR=false`:
1. Se exportó el formato de una semana sintética (A–E y 4 fotos de 1600 px): 8.4 MB con el respaldo.
2. Reabrir **sin editar**: `origen=respaldo`, 4 fotos, datos idénticos y sin avisos.
3. Se editaron a mano la descripción de B, una descripción de C con `=SUMA(1;2)` y la cantidad `Q10` de 2 a 5. Después se **guardó con LibreOffice** (`soffice --convert-to xlsx`).
4. Reabrir el editado: la hoja oculta sobrevivió al guardado; se tomaron B y la cantidad 5, C quedó como texto literal (sin evaluar) y hubo 3 avisos informativos ("Lunes: se tomó la descripción editada de la actividad B", etc.).

## Hallazgos
| Severidad | Archivo:línea | Problema | Cambio pedido |
|---|---|---|---|
| baja | `backend/app/services/importar_excel.py:278` | Las fotos del respaldo se validan con `normalizar_foto`, pero se devuelven los bytes originales y no los normalizados. No es riesgoso: el respaldo lo escribe la app, se valida que sea imagen y al exportar se vuelve a normalizar. | No bloquea. |
| info | — | El hallazgo bajo de la revisión anterior (máximo de fotos fijo) quedó resuelto: `EditorSemana` recibe `maxFotosPorEspacio` desde `/api/config`. | — |

## Pendiente (Oscar)
- Prueba visual en el navegador: botón "Abrir reporte guardado", confirmación y lista de avisos.

## Veredicto
`aceptado`.

## Métricas
`primera_pasada=sí` · `iteraciones=0` · `archivos_fuera_alcance=0` · `violaciones_normas=0` · `hallazgos_seguridad=0` · `inconsistencias=0` (tarea 6 completada por Claude porque Codex se quedó sin tokens)
