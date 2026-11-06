---
nombre: Proyecto_Tania
perfil: personal
estado: nuevo
---

# PROYECTO — Reportes de Servicios Generales

> Decisiones fijas del proyecto. Claude y Codex las siguen en cada plan. Cambiarlas requiere un plan dedicado.

## Qué es
- **Problema que resuelve:** capturar con selectores el reporte semanal de servicios generales y generar el Excel con el formato actual, un Excel mejorado y su PDF.
- **Usuarios:** una sola persona, en su equipo (local, sin cuentas).
- **Alcance:** catálogos, captura del reporte, cálculo de horas, fotos y las tres descargas. El proyecto no crecerá: lo más simple que funcione.

## Stack
| Capa | Elección | Versión |
|---|---|---|
| Backend | FastAPI + uvicorn | las de `~/proyectos/Asistencia/backend/pyproject.toml` |
| Base de datos | SQLite en `/data/app.db` (volumen `./data`) | — |
| ORM / migraciones | SQLAlchemy 2 + Alembic | las de Asistencia |
| Validación | Pydantic 2, pydantic-settings | las de Asistencia |
| Autenticación | Ninguna: la app solo escucha en 127.0.0.1 | — |
| Excel / imágenes | openpyxl 3.1.5, Pillow (versión fijada) | — |
| PDF | LibreOffice headless en la imagen `api` (`libreoffice-calc`) | apt |
| Frontend | React + TypeScript + Vite + react-router + TanStack Query | las de `~/proyectos/Asistencia/frontend/package.json` (sin recharts) |
| Pruebas | pytest + httpx + faker · vitest + Testing Library | las de Asistencia |
| Formato / lint | ruff · eslint + prettier | las de Asistencia |
| Despliegue | docker compose: `api` + `web` (nginx) en `127.0.0.1:8090` | — |

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
| 1–2 | Secretos | `.env` + `.env.example`; la app no maneja secretos |
| 6 | Autenticación | n.a.: uso propio y local, puerto solo en 127.0.0.1 |
| 9–12 | Cookies, contraseñas, abuso | n.a.: sin cuentas, uso local (perfil personal) |
| 14, 16 | Entradas y archivos | Pydantic; fotos validadas con Pillow, tamaño máximo, nombre generado |
| 18 | Headers | `nosniff`, `X-Frame-Options`, CSP en nginx, como Asistencia |
| 19 | HTTPS | n.a.: solo localhost |
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
| Componente UI | `frontend/src/pages/Catalogos.tsx` |
