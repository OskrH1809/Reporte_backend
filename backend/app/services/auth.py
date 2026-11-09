from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import get_settings
from app.errors import NoAutenticadoError
from app.models import Usuario

ALGORITMO = "HS256"
MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15
_hasher = PasswordHasher()
# Se verifica contra este hash cuando el correo no existe, para que el tiempo
# de respuesta no revele qué cuentas existen.
HASH_FICTICIO = _hasher.hash("contrasena-ficticia-para-tiempo-constante")


def hashear(contrasena: str) -> str:
    return _hasher.hash(contrasena)


def verificar(contrasena_hash: str, contrasena: str) -> bool:
    try:
        return _hasher.verify(contrasena_hash, contrasena)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def ahora() -> datetime:
    return datetime.now(UTC)


def crear_token(usuario: Usuario) -> tuple[str, datetime]:
    settings = get_settings()
    emitido = ahora()
    expira = emitido + timedelta(minutes=settings.jwt_minutos)
    secreto = settings.jwt_secreto.get_secret_value() if settings.jwt_secreto else ""
    token = jwt.encode(
        {"sub": str(usuario.id), "iat": emitido, "exp": expira}, secreto, algorithm=ALGORITMO
    )
    return token, expira


def leer_token(token: str) -> int:
    settings = get_settings()
    secreto = settings.jwt_secreto.get_secret_value() if settings.jwt_secreto else ""
    try:
        datos = jwt.decode(
            token, secreto, algorithms=[ALGORITMO], options={"require": ["exp", "iat", "sub"]}
        )
        return int(datos["sub"])
    except (jwt.PyJWTError, ValueError) as error:
        raise NoAutenticadoError("Sesión inválida o expirada") from error


def esta_bloqueado(usuario: Usuario) -> bool:
    if usuario.bloqueado_hasta is None:
        return False
    bloqueado_hasta = usuario.bloqueado_hasta
    # SQLite devuelve fechas sin zona horaria aunque la columna la declare.
    if bloqueado_hasta.tzinfo is None:
        bloqueado_hasta = bloqueado_hasta.replace(tzinfo=UTC)
    return bloqueado_hasta > ahora()


def registrar_fallo(usuario: Usuario) -> None:
    usuario.intentos_fallidos += 1
    if usuario.intentos_fallidos >= MAX_INTENTOS:
        usuario.bloqueado_hasta = ahora() + timedelta(minutes=MINUTOS_BLOQUEO)
        usuario.intentos_fallidos = 0


def registrar_exito(usuario: Usuario) -> None:
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
