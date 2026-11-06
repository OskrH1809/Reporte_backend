from io import BytesIO

import pytest
from faker import Faker
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Colaborador, Dia, Foto, Material
from app.services import fotos


def _crear_datos(
    client: TestClient, session: Session, faker: Faker, semana: int = 45
) -> tuple[int, str]:
    colaborador = Colaborador(nombre=faker.name(), orden=100 + semana)
    material = Material(nombre=f"Material-{faker.uuid4()}", unidad="unidad", orden=100 + semana)
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


def test_mejorado_distribuye_fotos_y_formulas_sin_superposicion(
    client: TestClient,
    session: Session,
    faker: Faker,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(fotos, "FOTOS_DIR", tmp_path)
    colaboradores = [Colaborador(nombre=faker.name(), orden=200 + indice) for indice in range(7)]
    session.add_all(colaboradores)
    session.commit()
    response = client.post("/api/reportes", json={"anio": 2026, "semana": 47})
    reporte_id = response.json()["id"]
    guardado = client.put(
        f"/api/reportes/{reporte_id}/dias/0",
        json={
            "actividades": [
                {
                    "letra": "A",
                    "descripcion": faker.paragraph(nb_sentences=8),
                    "asignaciones": [
                        {"colaborador_id": colaborador.id} for colaborador in colaboradores
                    ],
                }
            ],
            "observacion": faker.paragraph(nb_sentences=6),
            "texto_fotos": faker.sentence(),
        },
    )
    assert guardado.status_code == 200
    dia = session.scalar(select(Dia).where(Dia.reporte_id == reporte_id, Dia.dia_semana == 0))
    assert dia is not None
    espacios = ["A"] * 2 + ["B"] * 4 + ["C"] * 2 + ["AD"] * 4
    for indice, espacio in enumerate(espacios):
        nombre = f"sintetica-{indice}.jpg"
        tamano = (400, 200) if indice % 2 == 0 else (180, 360)
        Image.new("RGB", tamano, (20 + indice, 120, 60)).save(tmp_path / nombre, "JPEG")
        session.add(
            Foto(
                dia_id=dia.id,
                espacio=espacio,
                orden=indice + 1,
                archivo=nombre,
                nombre_original=nombre,
            )
        )
    session.commit()

    mejorado = client.get(f"/api/reportes/{reporte_id}/exportar/mejorado")
    pdf = client.get(f"/api/reportes/{reporte_id}/exportar/pdf")

    assert mejorado.status_code == 200
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    libro = load_workbook(BytesIO(mejorado.content))
    hoja = libro["Lunes"]
    valores = [
        celda.value
        for hoja_libro in libro.worksheets
        for fila in hoja_libro.iter_rows()
        for celda in fila
        if celda.value is not None
    ]
    assert not any(isinstance(valor, str) and valor.startswith("'=") for valor in valores)
    assert any(isinstance(valor, str) and valor.startswith("=SUM(") for valor in valores)
    for hoja_libro in libro.worksheets:
        assert hoja_libro.print_area
        for fila in hoja_libro.iter_rows():
            if any(celda.value is not None for celda in fila):
                assert hoja_libro.row_dimensions[fila[0].row].height is not None
            for celda in fila:
                if celda.value is not None:
                    assert celda.font.name == "Arial"
    fila_evidencia = next(
        celda.row
        for fila in hoja.iter_rows()
        for celda in fila
        if celda.value == "Evidencia fotográfica"
    )
    filas_fotos = [imagen.anchor._from.row + 1 for imagen in hoja._images[1:-1]]
    assert len(filas_fotos) == 12
    assert min(filas_fotos) > fila_evidencia
    assert any(salto.id < min(filas_fotos) for salto in hoja.row_breaks.brk)
    for imagen in hoja._images:
        proporcion_real = imagen.width / imagen.height
        proporcion_anclada = imagen.anchor.ext.cx / imagen.anchor.ext.cy
        assert proporcion_anclada == pytest.approx(proporcion_real, rel=0.01)
