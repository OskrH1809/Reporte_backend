from fastapi.testclient import TestClient


def test_health_responde_estado_exacto(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
