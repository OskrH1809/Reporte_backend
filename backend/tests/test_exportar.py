from io import BytesIO

from faker import Faker
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy.orm import Session

from app.models import Colaborador, Material


def _crear_datos(
    client: TestClient, session: Session, faker: Faker, semana: int = 45
) -> tuple[int, str]:
    colaborador = Colaborador(nombre=faker.name(), orden=100 + semana)
    material = Material(nombre=faker.word(), unidad="unidad", orden=100 + semana)
    session.add_all([colaborador, material])
    session.commit()
    response = client.post("/api/reportes", json={"anio": 2026, "semana": semana})
    assert response.status_code == 201
    reporte_id = response.json()["id"]
    guardado = client.put(
        f"/api/reportes/{reporte_id}/dias/0",
        json={
            "actividades": [
                {
                    "letra": "A",
                    "descripcion": faker.sentence(),
                    "asignaciones": [{"colaborador_id": colaborador.id}],
                }
            ],
            "materiales": [{"material_id": material.id, "cantidad": 2}],
        },
    )
    assert guardado.status_code == 200
    return reporte_id, material.nombre


def _valores(libro: Workbook) -> set[object]:
    return {
        celda.value
        for hoja in libro.worksheets
        for fila in hoja.iter_rows()
        for celda in fila
        if celda.value is not None
    }


def test_descargas_tienen_nombres_y_contenido(
    client: TestClient, session: Session, faker: Faker
) -> None:
    reporte_id, material = _crear_datos(client, session, faker)
    formato = client.get(f"/api/reportes/{reporte_id}/exportar/formato")
    mejorado = client.get(f"/api/reportes/{reporte_id}/exportar/mejorado")

    assert formato.status_code == 200
    assert "CH-RSG-45-2026.xlsx" in formato.headers["content-disposition"]
    assert "CH-RSG-45-2026_mejorado.xlsx" in mejorado.headers["content-disposition"]
    libro_formato = load_workbook(BytesIO(formato.content))
    libro_mejorado = load_workbook(BytesIO(mejorado.content))
    assert material not in _valores(libro_formato)
    assert material in _valores(libro_mejorado)
    assert libro_mejorado.sheetnames == ["Resumen", "Lunes"]


def test_pdf_es_valido(client: TestClient, session: Session, faker: Faker) -> None:
    reporte_id, _material = _crear_datos(client, session, faker, semana=46)

    response = client.get(f"/api/reportes/{reporte_id}/exportar/pdf")

    assert response.status_code == 200
    assert "CH-RSG-46-2026_mejorado.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000


def test_exportar_reporte_inexistente(client: TestClient) -> None:
    response = client.get("/api/reportes/999999/exportar/mejorado")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
