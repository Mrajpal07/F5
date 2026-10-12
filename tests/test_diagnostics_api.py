
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_diagnostics_endpoint_classifies_connection_error():
    response = client.post(
        "/diagnostics/analyse",
        json={
            "status": None,
            "latency_ms": 2.0,
            "error": "Connection refused",
            "failure_type": "connection_error",
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["diagnostic"]["category"] == "connection_error"
    assert body["diagnostic"]["severity"] == "high"
    assert "Connection refused" in body["diagnostic"]["evidence"]


def test_diagnostics_endpoint_rejects_negative_latency():
    response = client.post(
        "/diagnostics/analyse",
        json={
            "status": 200,
            "latency_ms": -1,
            "failure_type": None,
        },
    )

    assert response.status_code == 422
