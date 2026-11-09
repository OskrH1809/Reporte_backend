import json
from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.main import app, crear_app
from app.models import Colaborador, Foto, Reporte
from app.services import fotos


def _imagen() -> bytes:
    salida = BytesIO()
    Image.new("RGB", (120, 90), "green").save(salida, "PNG")
    return salida.getvalue()


def _datos(colaborador_id: int, cantidad_fotos: int = 2) -> dict:
    dias = []
    for dia_semana in range(6):
        actividades = []
        if dia_semana == 0:
            actividades = [
                {
                    "letra": letra,
                    "descripcion": f"Actividad sintética {letra}",
                    "asignaciones": [{"colaborador_id": colaborador_id}],
                }
                for letra in "ABCDEF"
            ]
        dias.append(
            {
                "dia_semana": dia_semana,
                "observacion": "Observación sintética",
                "texto_fotos": "Evidencia sintética",
                "actividades": actividades,
                "herramientas": [],
                "materiales": [],
                "fotos": [{"indice": indice, "espacio": "A"} for indice in range(cantidad_fotos)]
                if dia_semana == 0
                else [],
            }
        )
    return {"anio": 2026, "semana": 45, "dias": dias}


def _archivos(cantidad: int) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("fotos", (f"foto-{indice}.png", _imagen(), "image/png")) for indice in range(cantidad)]


def _conteos(session: Session) -> tuple[int, int]:
    return (
        session.scalar(select(func.count()).select_from(Reporte)) or 0,
        session.scalar(select(func.count()).select_from(Foto)) or 0,
    )


@contextmanager
def _cliente_modo(settings: Settings, session: Session) -> Iterator[TestClient]:
    aplicacion = crear_app(settings)

    def override_get_db() -> Iterator[Session]:
        yield session

    aplicacion.dependency_overrides[get_db] = override_get_db
    with TestClient(aplicacion) as client:
        yield client


def test_exporta_tres_formatos_sin_persistir(
    client: TestClient, session: Session, tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(fotos, "FOTOS_DIR", tmp_path)
    colaborador = Colaborador(nombre="Colaborador sintético", orden=900)
    session.add(colaborador)
    session.commit()
    datos = _datos(colaborador.id)
    antes = _conteos(session)

    formato = client.post(
        "/api/exportar/formato", data={"datos": json.dumps(datos)}, files=_archivos(2)
    )
    mejorado = client.post(
        "/api/exportar/mejorado", data={"datos": json.dumps(datos)}, files=_archivos(2)
    )
    pdf = client.post("/api/exportar/pdf", data={"datos": json.dumps(datos)}, files=_archivos(2))

    assert formato.status_code == 200
    assert mejorado.status_code == 200
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    lunes = load_workbook(BytesIO(formato.content))["Lunes"]
    assert len(lunes._images) - 2 == 2
    assert _conteos(session) == antes
    assert list(tmp_path.iterdir()) == []


def test_rechaza_cinco_fotos_en_un_espacio(client: TestClient, session: Session) -> None:
    colaborador = Colaborador(nombre="Colaborador cinco fotos", orden=901)
    session.add(colaborador)
    session.commit()

    response = client.post(
        "/api/exportar/formato",
        data={"datos": json.dumps(_datos(colaborador.id, cantidad_fotos=5))},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_rechaza_archivo_que_no_es_imagen(client: TestClient, session: Session) -> None:
    colaborador = Colaborador(nombre="Colaborador archivo", orden=902)
    session.add(colaborador)
    session.commit()
    datos = _datos(colaborador.id, cantidad_fotos=1)

    response = client.post(
        "/api/exportar/formato",
        data={"datos": json.dumps(datos)},
        files=[("fotos", ("programa.jpg", b"MZ ejecutable", "image/jpeg"))],
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_file"


def test_rechaza_colaborador_inexistente(client: TestClient) -> None:
    response = client.post(
        "/api/exportar/formato",
        data={"datos": json.dumps(_datos(999999, cantidad_fotos=0))},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Colaborador no encontrado"


def test_rechaza_cinco_dias(client: TestClient, session: Session) -> None:
    colaborador = Colaborador(nombre="Colaborador cinco días", orden=903)
    session.add(colaborador)
    session.commit()
    datos = _datos(colaborador.id, cantidad_fotos=0)
    datos["dias"] = datos["dias"][:5]

    response = client.post("/api/exportar/formato", data={"datos": json.dumps(datos)})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_rechaza_campo_extra(client: TestClient, session: Session) -> None:
    colaborador = Colaborador(nombre="Colaborador campo extra", orden=904)
    session.add(colaborador)
    session.commit()
    datos = _datos(colaborador.id, cantidad_fotos=0)
    datos["campo_extra"] = True

    response = client.post("/api/exportar/formato", data={"datos": json.dumps(datos)})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_rechaza_exportacion_mayor_al_maximo(
    client: TestClient, session: Session, monkeypatch
) -> None:
    colaborador = Colaborador(nombre="Colaborador límite", orden=905)
    session.add(colaborador)
    session.commit()
    monkeypatch.setattr(app.state.settings, "max_exportacion_mb", 1)

    response = client.post(
        "/api/exportar/formato",
        data={"datos": json.dumps(_datos(colaborador.id, cantidad_fotos=0))},
        files=[("fotos", ("grande.png", b"x" * (1024 * 1024 + 1), "image/png"))],
    )

    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"


def test_exportacion_funciona_con_almacenar_desactivado(session: Session) -> None:
    colaborador = Colaborador(nombre="Colaborador sin almacenar", orden=906)
    session.add(colaborador)
    session.commit()
    settings = Settings(environment="test", almacenar=False)

    with _cliente_modo(settings, session) as client:
        response = client.post(
            "/api/exportar/formato",
            data={"datos": json.dumps(_datos(colaborador.id, cantidad_fotos=0))},
        )

    assert response.status_code == 200
