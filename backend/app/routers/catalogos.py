from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import InvalidInputError, NotFoundError
from app.models import Colaborador, Firmante, Herramienta, Material
from app.schemas.catalogos import CatalogoCreate, CatalogoRead, CatalogoUpdate

TipoCatalogo = Literal["colaboradores", "herramientas", "materiales", "firmantes"]
DatabaseSession = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/api/catalogos", tags=["catalogos"])

MODELOS = {
    "colaboradores": Colaborador,
    "herramientas": Herramienta,
    "materiales": Material,
    "firmantes": Firmante,
}


def _serializar(registro: Colaborador | Herramienta | Material | Firmante) -> CatalogoRead:
    return CatalogoRead(
        id=registro.id,
        nombre=registro.nombre,
        orden=getattr(registro, "orden", None),
        activo=registro.activo,
        unidad=getattr(registro, "unidad", None),
        tipo=getattr(registro, "tipo", None),
    )


def _tipo_valido(tipo: str) -> TipoCatalogo:
    if tipo not in MODELOS:
        raise NotFoundError("Tipo de catálogo no encontrado")
    return cast(TipoCatalogo, tipo)


def _obtener(session: Session, tipo: str, registro_id: int):
    tipo_valido = _tipo_valido(tipo)
    registro = session.get(MODELOS[tipo_valido], registro_id)
    if registro is None:
        raise NotFoundError("Registro de catálogo no encontrado")
    return registro


@router.get("/{tipo}", response_model=list[CatalogoRead])
def listar_catalogo(
    tipo: str,
    session: DatabaseSession,
    incluir_inactivos: Annotated[bool, Query()] = False,
) -> list[CatalogoRead]:
    modelo = MODELOS[_tipo_valido(tipo)]
    consulta = select(modelo)
    if not incluir_inactivos:
        consulta = consulta.where(modelo.activo.is_(True))
    if hasattr(modelo, "orden"):
        consulta = consulta.order_by(modelo.orden, modelo.id)
    else:
        consulta = consulta.order_by(modelo.id)
    return [_serializar(item) for item in session.scalars(consulta)]


@router.post("/{tipo}", response_model=CatalogoRead, status_code=status.HTTP_201_CREATED)
def crear_catalogo(tipo: str, data: CatalogoCreate, session: DatabaseSession) -> CatalogoRead:
    tipo_valido = _tipo_valido(tipo)
    modelo = MODELOS[tipo_valido]
    valores: dict[str, object] = {"nombre": data.nombre}
    if tipo_valido == "materiales":
        if data.unidad is None:
            raise InvalidInputError("La unidad es obligatoria para materiales")
        valores["unidad"] = data.unidad
    elif tipo_valido == "firmantes":
        if data.tipo is None:
            raise InvalidInputError("El tipo es obligatorio para firmantes")
        valores["tipo"] = data.tipo
    if hasattr(modelo, "orden"):
        valores["orden"] = (session.scalar(select(func.max(modelo.orden))) or 0) + 1
    registro = modelo(**valores)
    session.add(registro)
    session.commit()
    session.refresh(registro)
    return _serializar(registro)


@router.patch("/{tipo}/{registro_id}", response_model=CatalogoRead)
def editar_catalogo(
    tipo: str,
    registro_id: int,
    data: CatalogoUpdate,
    session: DatabaseSession,
) -> CatalogoRead:
    registro = _obtener(session, tipo, registro_id)
    cambios = data.model_dump(exclude_unset=True)
    permitidos = {"nombre", "activo"}
    tipo_valido = _tipo_valido(tipo)
    if tipo_valido == "materiales":
        permitidos.add("unidad")
    if tipo_valido == "firmantes":
        permitidos.add("tipo")
    for campo, valor in cambios.items():
        if campo in permitidos:
            setattr(registro, campo, valor)
    session.commit()
    session.refresh(registro)
    return _serializar(registro)


@router.delete("/{tipo}/{registro_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_catalogo(tipo: str, registro_id: int, session: DatabaseSession) -> Response:
    registro = _obtener(session, tipo, registro_id)
    registro.activo = False
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
