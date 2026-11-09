from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.db import SessionLocal, get_db
from app.errors import register_error_handlers
from app.routers import catalogos, config, exportar, health, reportes
from app.services.semillas import cargar_semillas


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = _app.state.settings
    if settings.environment != "test" and get_db not in _app.dependency_overrides:
        with SessionLocal() as session:
            cargar_semillas(session)
    yield


def crear_app(settings: Settings) -> FastAPI:
    aplicacion = FastAPI(
        title="Reportes de Servicios Generales",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    aplicacion.state.settings = settings
    register_error_handlers(aplicacion)
    aplicacion.include_router(health.router)
    aplicacion.include_router(catalogos.router)
    aplicacion.include_router(config.router)
    aplicacion.include_router(exportar.router_memoria)
    if settings.almacenar:
        aplicacion.include_router(reportes.router)
        aplicacion.include_router(exportar.router_guardado)

    if settings.cors_origins:
        aplicacion.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Content-Type"],
        )
    return aplicacion


app = crear_app(get_settings())
