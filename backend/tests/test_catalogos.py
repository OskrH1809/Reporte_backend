from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Colaborador
from app.services.semillas import cargar_semillas


def test_crear_editar_y_desactivar_catalogo(client: TestClient, faker: Faker) -> None:
    nombre = faker.name()
    creado = client.post("/api/catalogos/colaboradores", json={"nombre": nombre})

    assert creado.status_code == 201
    registro_id = creado.json()["id"]
    editado = client.patch(
        f"/api/catalogos/colaboradores/{registro_id}", json={"nombre": faker.name()}
    )
    eliminado = client.delete(f"/api/catalogos/colaboradores/{registro_id}")

    assert editado.status_code == 200
    assert eliminado.status_code == 204
    activos = client.get("/api/catalogos/colaboradores").json()
    assert all(item["id"] != registro_id for item in activos)
    inactivos = client.get(
        "/api/catalogos/colaboradores", params={"incluir_inactivos": True}
    ).json()
    assert next(item for item in inactivos if item["id"] == registro_id)["activo"] is False


def test_material_requiere_unidad(client: TestClient, faker: Faker) -> None:
    response = client.post("/api/catalogos/materiales", json={"nombre": faker.word()})
    assert response.status_code == 422


def test_tipo_invalido_y_nombre_vacio(client: TestClient) -> None:
    assert client.get("/api/catalogos/desconocido").status_code == 404
    response = client.post("/api/catalogos/herramientas", json={"nombre": "   "})
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_semillas_son_idempotentes(session: Session) -> None:
    cargar_semillas(session)
    cantidad = session.scalar(select(func.count()).select_from(Colaborador))
    cargar_semillas(session)
    assert session.scalar(select(func.count()).select_from(Colaborador)) == cantidad
