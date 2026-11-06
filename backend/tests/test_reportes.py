from io import BytesIO

from faker import Faker
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.models import Colaborador
from app.services import fotos


def _colaborador(session: Session, faker: Faker) -> Colaborador:
    registro = Colaborador(nombre=faker.name(), orden=1)
    session.add(registro)
    session.commit()
    return registro


def _crear_reporte(client: TestClient, anio: int = 2026, semana: int = 38) -> int:
    response = client.post("/api/reportes", json={"anio": anio, "semana": semana})
    assert response.status_code == 201
    return response.json()["id"]


def _imagen_bytes() -> bytes:
    salida = BytesIO()
    Image.new("RGB", (20, 20), "green").save(salida, "PNG")
    return salida.getvalue()


def test_reporte_duplicado_devuelve_codigo(client: TestClient) -> None:
    _crear_reporte(client)
    response = client.post("/api/reportes", json={"anio": 2026, "semana": 38})

    assert response.status_code == 409
    assert response.json()["code"] == "reporte_duplicado"


def test_guardar_dia_reparte_horas_y_calcula_totales(
    client: TestClient, session: Session, faker: Faker
) -> None:
    reporte_id = _crear_reporte(client, semana=39)
    colaborador = _colaborador(session, faker)
    payload = {
        "actividades": [
            {
                "letra": "A",
                "descripcion": faker.sentence(),
                "asignaciones": [{"colaborador_id": colaborador.id}],
            },
            {
                "letra": "B",
                "descripcion": faker.sentence(),
                "asignaciones": [{"colaborador_id": colaborador.id}],
            },
        ]
    }

    response = client.put(f"/api/reportes/{reporte_id}/dias/0", json=payload)

    assert response.status_code == 200
    horas = [
        item["horas"]
        for actividad in response.json()["actividades"]
        for item in actividad["asignaciones"]
    ]
    assert horas == [4, 4]
    assert response.json()["horas_hombre"] == 8
    assert response.json()["numero_actividades"] == 2


def test_guardar_sabado_y_advertencia_manual(
    client: TestClient, session: Session, faker: Faker
) -> None:
    reporte_id = _crear_reporte(client, semana=40)
    colaborador = _colaborador(session, faker)
    sabado = client.put(
        f"/api/reportes/{reporte_id}/dias/5",
        json={
            "actividades": [
                {
                    "letra": "A",
                    "descripcion": faker.sentence(),
                    "asignaciones": [{"colaborador_id": colaborador.id}],
                }
            ]
        },
    )
    exceso = client.put(
        f"/api/reportes/{reporte_id}/dias/0",
        json={
            "actividades": [
                {
                    "letra": "A",
                    "descripcion": faker.sentence(),
                    "asignaciones": [
                        {"colaborador_id": colaborador.id, "horas": 9, "horas_manual": True}
                    ],
                }
            ]
        },
    )

    assert sabado.json()["actividades"][0]["asignaciones"][0]["horas"] == 5
    assert exceso.json()["advertencias"]


def test_foto_invalida_y_mayor_al_maximo(client: TestClient) -> None:
    reporte_id = _crear_reporte(client, semana=41)
    invalida = client.post(
        f"/api/reportes/{reporte_id}/dias/0/fotos",
        data={"espacio": "A"},
        files={"archivo": ("foto.png", b"no es imagen", "image/png")},
    )
    grande = client.post(
        f"/api/reportes/{reporte_id}/dias/0/fotos",
        data={"espacio": "A"},
        files={"archivo": ("foto.jpg", b"x" * (15 * 1024 * 1024 + 1), "image/jpeg")},
    )

    assert invalida.status_code == 422
    assert grande.status_code == 413


def test_espacio_lleno(client: TestClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(fotos, "FOTOS_DIR", tmp_path)
    reporte_id = _crear_reporte(client, semana=42)
    for indice in range(2):
        response = client.post(
            f"/api/reportes/{reporte_id}/dias/0/fotos",
            data={"espacio": "A"},
            files={"archivo": (f"foto-{indice}.png", _imagen_bytes(), "image/png")},
        )
        assert response.status_code == 201

    response = client.post(
        f"/api/reportes/{reporte_id}/dias/0/fotos",
        data={"espacio": "A"},
        files={"archivo": ("foto-3.png", _imagen_bytes(), "image/png")},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "espacio_lleno"
