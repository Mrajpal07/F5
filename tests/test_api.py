
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()
    assert data["service"] == "NetReliant"
    assert data["status"] == "running"
    assert "timestamp" in data


def test_probe_rejects_external_target():
    response = client.post(
        "/diagnostics/probe",
        json={"url": "http://example.com/"}
    )

    assert response.status_code == 422


def test_probe_rejects_https_target():
    response = client.post(
        "/diagnostics/probe",
        json={"url": "https://localhost/health"}
    )

    assert response.status_code == 422


def test_probe_rejects_url_with_credentials():
    response = client.post(
        "/diagnostics/probe",
        json={"url": "http://user:pass@localhost/health"}
    )

    assert response.status_code == 422