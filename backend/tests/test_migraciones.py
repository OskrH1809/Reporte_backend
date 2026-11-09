import os
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.config import Settings, get_settings

TABLAS = {
    "actividades",
    "asignaciones",
    "colaboradores",
    "dia_herramientas",
    "dia_materiales",
    "dias",
    "firmantes",
    "fotos",
    "herramientas",
    "materiales",
    "reportes",
    "usuarios",
}


def _ida_y_vuelta(url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    backend = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    configuracion = Config(backend / "alembic.ini")
    configuracion.set_main_option("script_location", str(backend / "alembic"))
    motor = create_engine(get_settings().database_url)
    try:
        command.upgrade(configuracion, "head")
        assert set(inspect(motor).get_table_names()) >= TABLAS
        with motor.begin() as conexion:
            conexion.execute(text("INSERT INTO reportes (id, anio, semana) VALUES (1, 2026, 45)"))
            conexion.execute(
                text(
                    "INSERT INTO dias "
                    "(id, reporte_id, dia_semana, fecha, observacion, texto_fotos) "
                    "VALUES (1, 1, 0, '2026-11-02', '', '')"
                )
            )
            conexion.execute(
                text(
                    "INSERT INTO actividades (id, dia_id, letra, descripcion) "
                    "VALUES (1, 1, 'D', 'Actividad sintética')"
                )
            )
        with pytest.raises(IntegrityError), motor.begin() as conexion:
            conexion.execute(
                text(
                    "INSERT INTO actividades (id, dia_id, letra, descripcion) "
                    "VALUES (2, 1, 'K', 'Actividad inválida')"
                )
            )
        if motor.dialect.name == "postgresql":
            with motor.connect() as conexion:
                sin_rls = conexion.scalars(
                    text(
                        "SELECT relname FROM pg_class "
                        "WHERE relname = ANY(:tablas) AND relkind = 'r' AND NOT relrowsecurity"
                    ),
                    {"tablas": [*sorted(TABLAS), "alembic_version"]},
                ).all()
            assert sin_rls == []

        command.downgrade(configuracion, "0001")
        with motor.connect() as conexion:
            assert conexion.scalar(text("SELECT count(*) FROM actividades WHERE letra = 'D'")) == 0
        with pytest.raises(IntegrityError), motor.begin() as conexion:
            conexion.execute(
                text(
                    "INSERT INTO actividades (id, dia_id, letra, descripcion) "
                    "VALUES (2, 1, 'D', 'Actividad inválida')"
                )
            )

        command.downgrade(configuracion, "base")
        assert not TABLAS & set(inspect(motor).get_table_names())
        command.upgrade(configuracion, "head")
        assert set(inspect(motor).get_table_names()) >= TABLAS
        command.downgrade(configuracion, "base")
    finally:
        motor.dispose()
        get_settings.cache_clear()


def test_migracion_ida_y_vuelta_sqlite(tmp_path, monkeypatch) -> None:
    _ida_y_vuelta(f"sqlite:///{tmp_path / 'migraciones.db'}", monkeypatch)


@pytest.mark.skipif(not os.environ.get("TEST_POSTGRES_URL"), reason="Sin TEST_POSTGRES_URL")
def test_migracion_ida_y_vuelta_postgres(monkeypatch) -> None:
    url = os.environ["TEST_POSTGRES_URL"]
    # El Postgres temporal de prueba no tiene TLS.
    if "sslmode" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=disable"
    assert Settings(database_url=url).database_url.startswith("postgresql+psycopg://")
    _ida_y_vuelta(url, monkeypatch)
