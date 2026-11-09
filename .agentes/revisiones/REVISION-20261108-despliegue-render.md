---
id: REVISION-20261108-despliegue-render
plan: PLAN-20261108-despliegue-render
rama: agente/despliegue-render
iteracion: 0
veredicto: aceptado
fecha: 2026-11-08
autor: claude
---

# Revisión — Despliegue: Render + Supabase + Vercel

## Ejecución
Codex se quedó sin tokens antes de empezar este plan. Por instrucción de Oscar ("continúa tú"), **Claude ejecutó las 6 tareas**: la parte en paralelo en `agente/despliegue-render-base` y la integración en `agente/despliegue-render`. No hubo un segundo agente que revisara, así que esta revisión la hizo Claude sobre su propio trabajo, con verificación completa y pruebas reales.

| Tarea | Commit |
|---|---|
| 1 Postgres, `0002` según el motor, RLS | `71ed99d`, `86490e8` |
| 2 Usuarios, JWT, admins por semillas, `AUTENTICACION` | `ceed6f8` + conexión a rutas en `a1619ed` |
| 3 Reglas de producción, CORS y cabeceras | `a1619ed` (merge) |
| 4 Imagen para Render y `render.yaml` | `f8a18e9` + medición (abajo) |
| 5 Frontend: URL de la API, sesión y login | `81af617` |
| 6 `vercel.json`, guía y `PROYECTO.md` | `f8a18e9` + commit de documentación |

## Verificación
- Backend: ruff limpio, **102 passed** (incluye `test_migracion_ida_y_vuelta_postgres` contra `postgres:17-alpine`), `alembic check` sin pendientes, bandit y pip-audit limpios.
- Frontend: lint, format, **74 passed**, `build` (también con `VITE_API_URL`), `npm audit --audit-level=high` con exit 0 y `vercel.json` válido.
- gitleaks: sin hallazgos (un falso positivo en `.env.example` se corrigió reordenando líneas).

## Pruebas reales (contenedor como Render: `--memory=512m`, `ENVIRONMENT=production`, Postgres, login)
- Arranca, migra (0001→0004), crea el admin semilla y RLS queda en las 13 tablas, incluida `alembic_version`.
- Login correcto → 200; incorrecto → 401; catálogos sin token → 401.
- Semana A–F con fotos sintéticas de 1600 px (~386 KB):

| Fotos | Formato | Mejorado | PDF | Importar | Pico de memoria |
|---|---|---|---|---|---|
| 20 | 16.0 MB · 1.6 s | 16.0 MB · 1.0 s | 4.5 MB · 3.6 s | 0.9 s, 20 fotos | **349 MB** (sin OOM) |
| 30 | 23.7 MB · 2.1 s | 23.7 MB · 1.3 s | 6.5 MB · 4.7 s | 1.1 s, 30 fotos | **441 MB** (sin OOM) |

- En reposo usa 79 MB. El tope práctico es de unas 30 fotos por semana; se documenta en el README.
- Modo local (SQLite, sin login) sin cambios: arranca y sirve catálogos y reportes sin token.

## Decisiones durante la ejecución
- **Sesión vencida sin perder la semana:** si un 401 llega a mitad del trabajo, el login aparece encima sin desmontar el editor (en modo sin almacenar, redirigir habría borrado la semana). "Cerrar sesión" pide confirmación. Se desvía del plan, que pedía redirigir a `/login`; está justificado por la regla de no perder datos.
- `usuario_actual` lee `request.app.state.settings` (el patrón de `crear_app` de los modos) en lugar de `get_settings()`.
- `0003` también activa RLS en `alembic_version`: en Supabase, el rol `anon` podría modificarla.

## Hallazgos
| Severidad | Archivo:línea | Problema | Cambio pedido |
|---|---|---|---|
| baja | `backend/tests/conftest.py` | El fixture `session` no aísla del todo los datos entre pruebas en SQLite (savepoints de pysqlite). Las pruebas nuevas usan correos únicos para no depender de eso. | Plan aparte si se quiere un aislamiento estricto. |
| baja | `render.yaml` / `frontend/vercel.json` | `connect-src` asume que el servicio se llama `reportes-servicios-api`; si Render asigna otro nombre hay que editarlo. Está documentado en el README. | — |

## Pendiente (Oscar)
- Crear las cuentas y desplegar con la guía del README; Claude no tiene acceso a las cuentas.
- Prueba visual en el navegador: login, captura, descargas y reabrir.
- Fusionar la cadena de ramas a `main` (comandos en el resumen).

## Veredicto
`aceptado`.

## Métricas
`primera_pasada=sí` · `iteraciones=0` · `archivos_fuera_alcance=0` · `violaciones_normas=0` · `hallazgos_seguridad=0` · `inconsistencias=0` (ejecutado y autorevisado por Claude)
