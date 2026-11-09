import json
from uuid import uuid4

import pytest
from faker import Faker
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import AdminSemilla, Settings, get_settings
from app.models import Colaborador, Usuario
from app.services import auth
from app.services.semillas import cargar_semillas, cargar_usuarios_semilla


def _admins(faker: Faker, cantidad: int) -> tuple[list[dict], list[str]]:
    contrasenas = [faker.password(length=16) for _ in range(cantidad)]
    admins = [
        {"correo": f"{uuid4().hex}@ejemplo.com", "contrasena_hash": auth.hashear(contrasena)}
        for contrasena in contrasenas
    ]
    return admins, contrasenas


def test_semillas_crean_admins_desde_la_variable(
    session: Session, faker: Faker, monkeypatch: pytest.MonkeyPatch
) -> None:
    admins, contrasenas = _admins(faker, 2)
    monkeypatch.setenv("ADMINS_SEMILLA", json.dumps(admins))
    get_settings.cache_clear()
    try:
        cargar_semillas(session)
        cargar_semillas(session)
    finally:
        get_settings.cache_clear()

    for admin, contrasena in zip(admins, contrasenas, strict=True):
        usuario = session.scalar(select(Usuario).where(Usuario.correo == admin["correo"].lower()))
        assert usuario is not None and usuario.activo
        assert auth.verificar(usuario.contrasena_hash, contrasena)
    total = session.scalar(
        select(func.count())
        .select_from(Usuario)
        .where(Usuario.correo.in_([a["correo"].lower() for a in admins]))
    )
    assert total == 2


def test_admin_existente_conserva_su_contrasena(session: Session) -> None:
    correo = f"{uuid4().hex}@ejemplo.com"
    original = auth.hashear("contrasena-original-larga")
    session.add(Usuario(correo=correo, contrasena_hash=original, activo=False))
    session.commit()

    creados = cargar_usuarios_semilla(
        session,
        [AdminSemilla(correo=correo, contrasena_hash=auth.hashear("otra-contrasena-larga"))],
    )

    usuario = session.scalar(select(Usuario).where(Usuario.correo == correo))
    assert creados == 0
    assert usuario.contrasena_hash == original
    assert usuario.activo is False


def test_hash_que_no_es_argon2_se_rechaza(faker: Faker) -> None:
    with pytest.raises(ValidationError):
        Settings(admins_semilla=json.dumps([{"correo": faker.email(), "contrasena_hash": "1234"}]))


def test_sin_variable_no_crea_usuarios_y_carga_catalogos(session: Session) -> None:
    antes = session.scalar(select(func.count()).select_from(Usuario))
    cargar_semillas(session)

    assert session.scalar(select(func.count()).select_from(Usuario)) == antes
    assert session.scalar(select(func.count()).select_from(Colaborador)) > 0


def test_produccion_con_login_exige_secreto() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", autenticacion=True, jwt_secreto=None)
    with pytest.raises(ValidationError):
        Settings(autenticacion=True, jwt_secreto="corto")


@pytest.mark.parametrize(
    ("entrada", "esperada"),
    [
        (
            "postgres://u:p@aws-0-x.pooler.supabase.com:5432/postgres",
            "postgresql+psycopg://u:p@aws-0-x.pooler.supabase.com:5432/postgres?sslmode=require",
        ),
        (
            "postgresql://u:p@localhost:5432/db?sslmode=disable",
            "postgresql+psycopg://u:p@localhost:5432/db?sslmode=disable",
        ),
        ("sqlite:////data/app.db", "sqlite:////data/app.db"),
    ],
)
def test_normaliza_database_url(entrada: str, esperada: str) -> None:
    assert Settings(database_url=entrada).database_url == esperada
