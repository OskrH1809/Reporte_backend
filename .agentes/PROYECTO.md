---
nombre: Proyecto_Tania
perfil: personal
estado: nuevo
---

# PROYECTO — Reportes de Servicios Generales

> Decisiones fijas del proyecto. Claude y Codex las siguen en cada plan. Cambiarlas requiere un plan dedicado.

## Qué es
- **Problema que resuelve:** capturar con selectores el reporte semanal de servicios generales y generar el Excel con el formato actual, un Excel mejorado y su PDF, guardándolo o manteniéndolo solo en memoria según `ALMACENAR`.
- **Usuarios:** en local, una sola persona sin cuentas (`AUTENTICACION=false`). En la nube, personas autorizadas con cuenta (`AUTENTICACION=true`; administradores creados por las semillas desde `ADMINS_SEMILLA`).
- **Alcance:** catálogos persistentes, captura del reporte, cálculo de horas, fotos y las tres descargas. Con `ALMACENAR=true` se guardan reportes y fotos; con `false`, la semana vive solo en la pestaña y las exportaciones se generan en memoria. El proyecto no crecerá: lo más simple que funcione.

## Stack
| Capa | Elección | Versión |
|---|---|---|
| Backend | FastAPI + uvicorn | las de `~/proyectos/Asistencia/backend/pyproject.toml` |
| Base de datos | Local: SQLite en `/data/app.db` (volumen `./data`). Nube: Postgres de Supabase (session pooler, RLS en todas las tablas) | psycopg[binary] 3.3.8 |
| ORM / migraciones | SQLAlchemy 2 + Alembic | las de Asistencia |
| Validación | Pydantic 2, pydantic-settings | las de Asistencia |
| Autenticación | `AUTENTICACION`: apagada en local; en la nube JWT HS256 (8 h) + argon2 + bloqueo de 15 min tras 5 fallos | PyJWT 2.15.1, argon2-cffi 25.1.0 |
| Excel / imágenes | openpyxl 3.1.5, Pillow (versión fijada) | — |
| PDF | LibreOffice headless en la imagen `api` (`libreoffice-calc`) | apt |
| Frontend | React + TypeScript + Vite + react-router + TanStack Query | las de `~/proyectos/Asistencia/frontend/package.json` (sin recharts) |
| Pruebas | pytest + httpx + faker · vitest + Testing Library | las de Asistencia |
| Formato / lint | ruff · eslint + prettier | las de Asistencia |
| Despliegue | Local: docker compose `api` + `web` (nginx) en `127.0.0.1:8090`. Nube: backend en Render (`render.yaml`, plan gratuito, `ALMACENAR=false`) y frontend en Vercel (`frontend/vercel.json`) | — |

## Estructura de carpetas
```
backend/
  alembic/  alembic.ini  Dockerfile  pyproject.toml
  app/
    config.py db.py errors.py main.py
    models/ schemas/ routers/ services/
    plantillas/  plantilla_formato.xlsx logo.png mapa.png
    seeds/       catalogos.json
  tests/
frontend/  Dockerfile nginx.conf  src/{api,pages,components}
docker-compose.yml  Makefile  .env.example  README.md
```

## Convenciones
- Idioma del código, de la API y de la UI: español.
- Formato de error: `{"detail": "...", "code": "..."}` (igual que Asistencia).
- Fechas: ISO-8601 en la API. IDs: entero autoincremental.
- Borrado de catálogos: lógico (`activo=false`), porque los reportes viejos los referencian.

## Seguridad base
| # | Medida | Decisión |
|---|---|---|
| 1–2 | Secretos | `.env` + `.env.example`; en la nube `JWT_SECRETO`, `DATABASE_URL` y `ADMINS_SEMILLA` solo en el panel de Render (`sync: false` / `generateValue`) |
| 3–4 | Llaves de BD y RLS | El frontend no recibe llaves de Supabase; RLS sin políticas en todas las tablas (incluida `alembic_version`) |
| 6 | Autenticación | Local: n.a. (127.0.0.1). Nube: `usuario_actual` en todas las rutas de datos; solo `health`, `config` y `auth/login` son públicas |
| 9 | Sesión | Bearer en cabecera, token en `sessionStorage`, 8 h; sin cookies (dominios distintos) |
| 10–12 | Contraseñas y abuso | argon2; las semillas solo aceptan hashes; bloqueo de 15 min tras 5 fallos; sin registro público |
| 14, 16 | Entradas y archivos | Pydantic; fotos validadas con Pillow, tamaño máximo, nombre generado; Excel importado con límites de ZIP y `defusedxml` |
| 18 | Headers | `nosniff`, `X-Frame-Options`, CSP en nginx y en `vercel.json`; HSTS en producción |
| 19 | HTTPS | Local: n.a. Nube: Render/Vercel con HTTPS, HSTS y `sslmode=require` hacia Supabase |
| 20 | Dependencias | versiones fijadas, `pip-audit`, `npm audit` |

## Datos reales
- `CH-RSG-*.xlsx` está en `.gitignore` y nadie lo abre: todo lo necesario está en `backend/app/plantillas/` y `backend/app/seeds/`.
- `seeds/catalogos.json` contiene los nombres reales que Oscar pidió cargar. Las pruebas usan datos sintéticos.

## Piezas de referencia (se llenan tras el plan de esqueleto)
| Tipo | Archivo |
|---|---|
| Endpoint | `backend/app/routers/catalogos.py` |
| Modelo + migración | `backend/app/models/` + `backend/alembic/versions/` |
| Servicio | `backend/app/services/calculos.py` |
| Generación de Excel | `backend/app/services/reporte_memoria.py` |
| Importación de Excel | `backend/app/services/importar_excel.py` |
| Componente UI | `frontend/src/pages/Catalogos.tsx` |
| Formulario de día | `frontend/src/components/FormularioDia.tsx` |
| Autenticación | `backend/app/routers/auth.py` + `backend/app/services/auth.py` |
| Sesión en el cliente | `frontend/src/api/sesion.ts` |
