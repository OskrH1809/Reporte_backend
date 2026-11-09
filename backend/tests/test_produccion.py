from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.main import crear_app
from app.models import Usuario
from app.services import auth

ORIGEN = "https://reportes.ejemplo.app"
POSTGRES = "postgresql://usuario:clave@localhost:5432/base"
SECRETO = "p" * 48


@contextmanager
def _cliente(settings: Settings, session: Session) -> Iterator[TestClient]:
    aplicacion = crear_app(settings)

    def override_get_db() -> Iterator[Session]:
        yield session

    aplicacion.dependency_overrides[get_db] = override_get_db
    with TestClient(aplicacion) as client:
        yield client


def _produccion(**cambios: object) -> Settings:
    valores: dict[str, object] = {
        "environment": "production",
        "almacenar": False,
        "autenticacion": True,
        "jwt_secreto": SECRETO,
        "cors_origins": ORIGEN,
        "database_url": POSTGRES,
    }
    valores.update(cambios)
    return Settings(**valores)


def test_produccion_valida_arranca() -> None:
    settings = _produccion()
    assert settings.database_url.startswith("postgresql+psycopg://")


@pytest.mark.parametrize(
    "cambio",
    [
        {"almacenar": True},
        {"autenticacion": False},
        {"cors_origins": ""},
        {"database_url": "sqlite:////data/app.db"},
        {"jwt_secreto": None},
    ],
    ids=["almacenar", "sin-login", "sin-cors", "sqlite", "sin-secreto"],
)
def test_produccion_rechaza_configuracion_insegura(cambio: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _produccion(**cambio)


def test_produccion_oculta_docs_y_agrega_cabeceras(session: Session) -> None:
    with _cliente(_produccion(), session) as client:
        docs = client.get("/api/docs")
        openapi = client.get("/api/openapi.json")
        salud = client.get("/api/health")

    assert docs.status_code == 404
    assert openapi.status_code == 404
    assert salud.headers["x-content-type-options"] == "nosniff"
    assert salud.headers["x-frame-options"] == "DENY"
    assert "max-age" in salud.headers["strict-transport-security"]


def test_cors_solo_para_el_origen_permitido(session: Session) -> None:
    preflight = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization, content-type",
    }
    with _cliente(_produccion(), session) as client:
        permitido = client.options("/api/exportar/pdf", headers={"Origin": ORIGEN, **preflight})
        ajeno = client.options(
            "/api/exportar/pdf", headers={"Origin": "https://ajeno.ejemplo", **preflight}
        )

    assert permitido.headers["access-control-allow-origin"] == ORIGEN
    assert "authorization" in permitido.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-origin" not in ajeno.headers


def test_con_login_las_rutas_de_datos_exigen_token(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("JWT_SECRETO", SECRETO)
    get_settings.cache_clear()
    usuario = Usuario(correo=f"{uuid4().hex}@ejemplo.com", contrasena_hash=auth.hashear("x" * 16))
    session.add(usuario)
    session.commit()
    settings = Settings(
        environment="test", almacenar=False, autenticacion=True, jwt_secreto=SECRETO
    )
    try:
        with _cliente(settings, session) as client:
            protegidas = [
                client.get("/api/catalogos/colaboradores"),
                client.post("/api/exportar/pdf", data={"datos": "{}"}),
                client.post("/api/importar", files={"archivo": ("a.xlsx", b"PK")}),
            ]
            publicas = [client.get("/api/health"), client.get("/api/config")]
            token, _ = auth.crear_token(usuario)
            con_token = client.get(
                "/api/catalogos/colaboradores", headers={"Authorization": f"Bearer {token}"}
            )
    finally:
        get_settings.cache_clear()

    assert [r.status_code for r in protegidas] == [401, 401, 401]
    assert all(r.json()["code"] == "no_autenticado" for r in protegidas)
    assert [r.status_code for r in publicas] == [200, 200]
    assert publicas[1].json()["autenticacion"] is True
    assert con_token.status_code == 200
