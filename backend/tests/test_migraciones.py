from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

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
        command.downgrade(configuracion, "base")
        assert not TABLAS & set(inspect(motor).get_table_names())
        command.upgrade(configuracion, "head")
        assert set(inspect(motor).get_table_names()) >= TABLAS
        motor.dispose()
    finally:
        get_settings.cache_clear()
