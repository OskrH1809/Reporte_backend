from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import SessionLocal, get_db
from app.errors import register_error_handlers
from app.routers import catalogos, exportar, health, reportes
from app.services.semillas import cargar_semillas

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if settings.environment != "test" and get_db not in _app.dependency_overrides:
        with SessionLocal() as session:
            cargar_semillas(session)
    yield


app = FastAPI(
    title="Reportes de Servicios Generales",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
register_error_handlers(app)
app.include_router(health.router)
app.include_router(catalogos.router)
app.include_router(reportes.router)
app.include_router(exportar.router)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
