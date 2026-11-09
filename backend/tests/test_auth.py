from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import register_error_handlers
from app.models import Usuario
from app.routers.auth import usuario_actual
from app.services import auth

SECRETO = "s" * 48
CONTRASENA = "una-contrasena-larga-de-prueba"


def correo_unico() -> str:
    # faker reinicia su semilla en cada prueba y el correo es único en la tabla.
    return f"{uuid4().hex}@ejemplo.com"


@pytest.fixture
def con_login(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("AUTENTICACION", "true")
    monkeypatch.setenv("JWT_SECRETO", SECRETO)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def usuario(session: Session) -> Usuario:
    registro = Usuario(correo=correo_unico(), contrasena_hash=auth.hashear(CONTRASENA))
    session.add(registro)
    session.commit()
    return registro


@pytest.fixture
def cliente_protegido(session: Session) -> Iterator[TestClient]:
    """App mínima con una ruta protegida por `usuario_actual`."""
    app = FastAPI()
    app.state.settings = get_settings()
    register_error_handlers(app)

    @app.get("/protegida")
    def protegida(actual: Annotated[Usuario | None, Depends(usuario_actual)]) -> dict:
        return {"usuario": actual.id if actual else None}

    def override_get_db() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as cliente:
        yield cliente


def _login(client: TestClient, correo: str, contrasena: str = CONTRASENA):
    return client.post("/api/auth/login", json={"correo": correo, "contrasena": contrasena})


def test_login_correcto_y_yo(client: TestClient, usuario: Usuario, con_login: None) -> None:
    respuesta = _login(client, usuario.correo.upper())

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"  # noqa: S105 - tipo de token, no contraseña
    yo = client.get("/api/auth/yo", headers={"Authorization": f"Bearer {cuerpo['access_token']}"})
    assert yo.status_code == 200
    assert set(yo.json()) == {"id", "correo"}
    assert yo.json()["correo"] == usuario.correo


def test_contrasena_incorrecta_y_usuario_inexistente_responden_igual(
    client: TestClient, usuario: Usuario, con_login: None
) -> None:
    incorrecta = _login(client, usuario.correo, "otra-contrasena-cualquiera")
    inexistente = _login(client, correo_unico())

    assert incorrecta.status_code == inexistente.status_code == 401
    assert incorrecta.json() == inexistente.json()
    assert incorrecta.json()["code"] == "credenciales_invalidas"
    assert incorrecta.headers["www-authenticate"] == "Bearer"


def test_usuario_inactivo_no_entra(
    client: TestClient, session: Session, usuario: Usuario, con_login: None
) -> None:
    usuario.activo = False
    session.commit()

    assert _login(client, usuario.correo).status_code == 401


def test_bloqueo_tras_cinco_fallos_y_desbloqueo(
    client: TestClient, session: Session, usuario: Usuario, monkeypatch: pytest.MonkeyPatch
) -> None:
    for _ in range(5):
        assert _login(client, usuario.correo, "contrasena-equivocada").status_code == 401

    bloqueado = _login(client, usuario.correo)
    assert bloqueado.status_code == 429
    assert bloqueado.json()["code"] == "demasiados_intentos"

    futuro = datetime.now(UTC) + timedelta(minutes=16)
    monkeypatch.setattr(auth, "ahora", lambda: futuro)
    assert _login(client, usuario.correo).status_code == 200
    session.refresh(usuario)
    assert usuario.intentos_fallidos == 0


def test_login_rechaza_campos_extra(client: TestClient, usuario: Usuario) -> None:
    respuesta = client.post(
        "/api/auth/login",
        json={"correo": usuario.correo, "contrasena": CONTRASENA, "rol": "admin"},
    )

    assert respuesta.status_code == 422


def test_hash_es_argon2_y_no_guarda_la_contrasena(usuario: Usuario) -> None:
    assert usuario.contrasena_hash.startswith("$argon2")
    assert CONTRASENA not in usuario.contrasena_hash


def test_ruta_protegida_sin_token_con_token_y_sin_autenticacion(
    con_login: None, cliente_protegido: TestClient, usuario: Usuario
) -> None:
    sin_token = cliente_protegido.get("/protegida")
    assert sin_token.status_code == 401
    assert sin_token.json()["code"] == "no_autenticado"

    token, _ = auth.crear_token(usuario)
    con_token = cliente_protegido.get("/protegida", headers={"Authorization": f"Bearer {token}"})
    assert con_token.status_code == 200
    assert con_token.json() == {"usuario": usuario.id}


def test_sin_autenticacion_la_ruta_queda_abierta(cliente_protegido: TestClient) -> None:
    assert cliente_protegido.get("/protegida").json() == {"usuario": None}


@pytest.mark.parametrize(
    "token",
    [
        jwt.encode({"sub": "1", "iat": 1, "exp": 2}, SECRETO, algorithm="HS256"),
        jwt.encode(
            {"sub": "1", "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(hours=1)},
            "otra-clave-distinta-de-al-menos-32-caracteres",
            algorithm="HS256",
        ),
        jwt.encode(
            {"sub": "1", "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(hours=1)},
            None,
            algorithm="none",
        ),
        "no-es-un-token",
    ],
    ids=["expirado", "otra-clave", "alg-none", "basura"],
)
def test_tokens_invalidos(con_login: None, cliente_protegido: TestClient, token: str) -> None:
    respuesta = cliente_protegido.get("/protegida", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 401


def test_usuario_desactivado_pierde_la_sesion(
    con_login: None, cliente_protegido: TestClient, session: Session, usuario: Usuario
) -> None:
    token, _ = auth.crear_token(usuario)
    usuario.activo = False
    session.commit()

    respuesta = cliente_protegido.get("/protegida", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 401


def test_cli_rechaza_contrasena_corta_e_imprime_solo_el_hash(capsys) -> None:
    from app.cli import main

    assert main(["hash-contrasena"], leer=lambda _mensaje: "corta") == 1
    assert "12 caracteres" in capsys.readouterr().err

    assert main(["hash-contrasena"], leer=lambda _mensaje: CONTRASENA) == 0
    salida = capsys.readouterr().out.strip()
    assert salida.startswith("$argon2")
    assert CONTRASENA not in salida
