from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.errors import CredencialesInvalidasError, DemasiadosIntentosError, NoAutenticadoError
from app.models import Usuario
from app.schemas.auth import LoginEntrada, LoginSalida, UsuarioSalida
from app.services import auth

DatabaseSession = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/api/auth", tags=["auth"])
esquema_bearer = HTTPBearer(auto_error=False)
MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos"


Credenciales = Annotated[HTTPAuthorizationCredentials | None, Depends(esquema_bearer)]


def _resolver_usuario(
    session: Session, credenciales: HTTPAuthorizationCredentials | None
) -> Usuario:
    if credenciales is None or credenciales.scheme.lower() != "bearer":
        raise NoAutenticadoError("Inicia sesión para continuar")
    usuario = session.get(Usuario, auth.leer_token(credenciales.credentials))
    if usuario is None or not usuario.activo:
        raise NoAutenticadoError("Sesión inválida o expirada")
    return usuario


def usuario_actual(
    request: Request, session: DatabaseSession, credenciales: Credenciales
) -> Usuario | None:
    """Dependencia para rutas de datos: solo exige sesión con AUTENTICACION=true."""
    settings: Settings = request.app.state.settings
    if not settings.autenticacion:
        return None
    return _resolver_usuario(session, credenciales)


def usuario_obligatorio(session: DatabaseSession, credenciales: Credenciales) -> Usuario:
    return _resolver_usuario(session, credenciales)


@router.post("/login", response_model=LoginSalida)
def login(data: LoginEntrada, session: DatabaseSession) -> LoginSalida:
    usuario = session.scalar(select(Usuario).where(Usuario.correo == data.correo))
    if usuario is None or not usuario.activo:
        auth.verificar(auth.HASH_FICTICIO, data.contrasena)
        raise CredencialesInvalidasError(MENSAJE_CREDENCIALES)
    if auth.esta_bloqueado(usuario):
        raise DemasiadosIntentosError("Demasiados intentos. Espera 15 minutos.")
    if not auth.verificar(usuario.contrasena_hash, data.contrasena):
        auth.registrar_fallo(usuario)
        session.commit()
        raise CredencialesInvalidasError(MENSAJE_CREDENCIALES)
    auth.registrar_exito(usuario)
    session.commit()
    token, expira = auth.crear_token(usuario)
    return LoginSalida(access_token=token, expira_en=expira)


@router.get("/yo", response_model=UsuarioSalida)
def yo(usuario: Annotated[Usuario, Depends(usuario_obligatorio)]) -> UsuarioSalida:
    return UsuarioSalida(id=usuario.id, correo=usuario.correo)
