from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.main import crear_app


@contextmanager
def _cliente(settings: Settings, session: Session) -> Iterator[TestClient]:
    aplicacion = crear_app(settings)

    def override_get_db() -> Iterator[Session]:
        yield session

    aplicacion.dependency_overrides[get_db] = override_get_db
    with TestClient(aplicacion) as client:
        yield client


def test_modo_almacenar_expone_config_y_reportes(session: Session) -> None:
    settings = Settings(environment="test", almacenar=True)
    with _cliente(settings, session) as client:
        config = client.get("/api/config")
        reportes = client.get("/api/reportes")

    assert config.status_code == 200
    assert config.json() == {"almacenar": True, "max_fotos_por_espacio": 4}
    assert reportes.status_code == 200


def test_modo_memoria_oculta_reportes_y_conserva_catalogos(session: Session) -> None:
    settings = Settings(environment="test", almacenar=False)
    with _cliente(settings, session) as client:
        config = client.get("/api/config")
        reportes = client.get("/api/reportes")
        exportacion = client.get("/api/reportes/1/exportar/pdf")
        colaboradores = client.get("/api/catalogos/colaboradores")

    assert config.status_code == 200
    assert config.json() == {"almacenar": False, "max_fotos_por_espacio": 4}
    assert reportes.status_code == 404
    assert exportacion.status_code == 404
    assert colaboradores.status_code == 200
