from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.config import get_settings

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
}


def test_migracion_ida_y_vuelta_sqlite(tmp_path, monkeypatch) -> None:
    backend = Path(__file__).resolve().parents[1]
    base = tmp_path / "migraciones.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    get_settings.cache_clear()
    configuracion = Config(backend / "alembic.ini")
    configuracion.set_main_option("script_location", str(backend / "alembic"))
    try:
        command.upgrade(configuracion, "head")
        motor = create_engine(f"sqlite:///{base}")
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
        motor.dispose()
    finally:
        get_settings.cache_clear()
