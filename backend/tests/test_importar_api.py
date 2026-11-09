import json
import struct
from collections.abc import Iterator
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient
from openpyxl import Workbook
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.main import app, crear_app
from app.models import Colaborador, Foto, Reporte
from app.schemas.exportar import ReporteExportar


def _imagen() -> bytes:
    salida = BytesIO()
    Image.new("RGB", (48, 36), "orange").save(salida, "PNG")
    return salida.getvalue()


def _datos(colaborador_id: int) -> dict:
    return {
        "anio": 2026,
        "semana": 45,
        "dias": [
            {
                "dia_semana": dia,
                "actividades": [
                    {
                        "letra": "A",
                        "descripcion": "Actividad de importación",
                        "asignaciones": [{"colaborador_id": colaborador_id}],
                    }
                ]
                if dia == 0
                else [],
                "fotos": [{"indice": 0, "espacio": "A"}] if dia == 0 else [],
            }
            for dia in range(6)
        ],
    }


def _conteos(session: Session) -> tuple[int, int]:
    return (
        session.scalar(select(func.count()).select_from(Reporte)) or 0,
        session.scalar(select(func.count()).select_from(Foto)) or 0,
    )


def test_importa_formato_con_respaldo_sin_persistir(client: TestClient, session: Session) -> None:
    colaborador = Colaborador(nombre="Persona para importar", orden=980)
    session.add(colaborador)
    session.commit()
    antes = _conteos(session)
    exportado = client.post(
        "/api/exportar/formato",
        data={"datos": json.dumps(_datos(colaborador.id))},
        files=[("fotos", ("foto.png", _imagen(), "image/png"))],
    )

    response = client.post(
        "/api/importar",
        files={
            "archivo": (
                "reporte.xlsx",
                exportado.content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    cuerpo = response.json()
    assert set(cuerpo) == {"datos", "fotos", "avisos", "origen"}
    assert cuerpo["origen"] == "respaldo"
    assert cuerpo["avisos"] == []
    assert cuerpo["datos"] == ReporteExportar.model_validate(_datos(colaborador.id)).model_dump(
        mode="json"
    )
    assert cuerpo["fotos"][0]["dia_semana"] == 0
    assert cuerpo["fotos"][0]["espacio"] == "A"
    assert _conteos(session) == antes


def test_rechaza_texto_renombrado_como_excel(client: TestClient) -> None:
    response = client.post(
        "/api/importar", files={"archivo": ("falso.xlsx", b"texto", "application/octet-stream")}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_file"


def test_rechaza_zip_con_tamano_descomprimido_excesivo(client: TestClient) -> None:
    salida = BytesIO()
    with ZipFile(salida, "w", ZIP_DEFLATED) as archivo:
        archivo.writestr("xl/x.xml", b"x")
    contenido = bytearray(salida.getvalue())
    central = contenido.index(b"PK\x01\x02")
    contenido[central + 24 : central + 28] = struct.pack("<I", 400 * 1024 * 1024)

    response = client.post(
        "/api/importar",
        files={"archivo": ("bomba.xlsx", bytes(contenido), "application/octet-stream")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_file"


def test_rechaza_entidad_externa_en_xml(client: TestClient) -> None:
    libro = Workbook()
    original = BytesIO()
    libro.save(original)
    entrada = ZipFile(BytesIO(original.getvalue()))
    salida = BytesIO()
    with entrada, ZipFile(salida, "w", ZIP_DEFLATED) as destino:
        for info in entrada.infolist():
            contenido = entrada.read(info.filename)
            if info.filename == "xl/workbook.xml":
                contenido = contenido.replace(
                    b"<workbook ",
                    b'<!DOCTYPE workbook [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><workbook ',
                ).replace(
                    b"</workbook>",
                    b'<definedNames><definedName name="x">&xxe;'
                    b"</definedName></definedNames></workbook>",
                )
            destino.writestr(info, contenido)

    response = client.post(
        "/api/importar",
        files={"archivo": ("xxe.xlsx", salida.getvalue(), "application/octet-stream")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_file"
    assert "root:" not in response.text


def test_rechaza_archivo_mayor_al_tope(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(app.state.settings, "max_exportacion_mb", 1)

    response = client.post(
        "/api/importar",
        files={"archivo": ("grande.xlsx", b"x" * (1024 * 1024 + 1), "application/octet-stream")},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"


def test_endpoint_tambien_existe_sin_almacenar(session: Session) -> None:
    aplicacion = crear_app(Settings(environment="test", almacenar=False))

    def override_get_db() -> Iterator[Session]:
        yield session

    aplicacion.dependency_overrides[get_db] = override_get_db
    with TestClient(aplicacion) as cliente:
        response = cliente.post(
            "/api/importar",
            files={"archivo": ("falso.xlsx", b"texto", "application/octet-stream")},
        )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_file"
