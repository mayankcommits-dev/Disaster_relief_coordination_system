from fastapi.testclient import TestClient

from backend.api import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["service"] == "Disaster Relief Coordination API"


def test_emergencies_endpoint():
    response = client.get("/emergencies")

    assert response.status_code == 200
    assert "emergencies" in response.json()


def test_update_emergency_status():
    response = client.patch(
        "/emergencies/TEST-001/status",
        json={"status": "RESOLVED"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "RESOLVED"