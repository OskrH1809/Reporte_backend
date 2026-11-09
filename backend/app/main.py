from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.db import SessionLocal, get_db
from app.errors import register_error_handlers
from app.routers import auth, catalogos, config, exportar, health, importar, reportes
from app.routers.auth import usuario_actual
from app.services.semillas import cargar_semillas


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = _app.state.settings
    if settings.environment != "test" and get_db not in _app.dependency_overrides:
        with SessionLocal() as session:
            cargar_semillas(session)
    yield


def crear_app(settings: Settings) -> FastAPI:
    produccion = settings.environment == "production"
    aplicacion = FastAPI(
        title="Reportes de Servicios Generales",
        docs_url=None if produccion else "/api/docs",
        openapi_url=None if produccion else "/api/openapi.json",
        lifespan=lifespan,
    )
    aplicacion.state.settings = settings
    register_error_handlers(aplicacion)
    protegido = [Depends(usuario_actual)]
    aplicacion.include_router(health.router)
    aplicacion.include_router(config.router)
    aplicacion.include_router(auth.router)
    aplicacion.include_router(catalogos.router, dependencies=protegido)
    aplicacion.include_router(exportar.router_memoria, dependencies=protegido)
    aplicacion.include_router(importar.router, dependencies=protegido)
    if settings.almacenar:
        aplicacion.include_router(reportes.router, dependencies=protegido)
        aplicacion.include_router(exportar.router_guardado, dependencies=protegido)

    @aplicacion.middleware("http")
    async def cabeceras_seguridad(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        respuesta = await call_next(request)
        respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
        respuesta.headers.setdefault("X-Frame-Options", "DENY")
        respuesta.headers.setdefault("Referrer-Policy", "no-referrer")
        if produccion:
            respuesta.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return respuesta

    if settings.cors_origins:
        aplicacion.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Content-Type", "Authorization"],
            expose_headers=["Content-Disposition"],
        )
    return aplicacion


app = crear_app(get_settings())
