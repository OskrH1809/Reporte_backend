from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.config import Settings
from app.routers.reportes import LIMITES_FOTOS

router = APIRouter(prefix="/api", tags=["configuracion"])


class ConfigRead(BaseModel):
    almacenar: bool
    autenticacion: bool
    max_fotos_por_espacio: int


@router.get("/config", response_model=ConfigRead)
def ver_config(request: Request) -> ConfigRead:
    settings: Settings = request.app.state.settings
    return ConfigRead(
        almacenar=settings.almacenar,
        autenticacion=settings.autenticacion,
        max_fotos_por_espacio=LIMITES_FOTOS["A"],
    )
