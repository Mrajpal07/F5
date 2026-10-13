
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
        json={"url": "http://example.com/"},
    )

    assert response.status_code == 422


def test_probe_rejects_https_target():
    response = client.post(
        "/diagnostics/probe",
        json={"url": "https://localhost/health"},
    )

    assert response.status_code == 422


def test_probe_rejects_url_with_credentials():
    response = client.post(
        "/diagnostics/probe",
        json={"url": "http://user:pass@localhost/health"},
    )

    assert response.status_code == 422


def test_probe_reports_dns_failure(monkeypatch):
    from app import main
    main.app.state.incident_manager = main.IncidentManager()

    monkeypatch.setattr(
        main,
        "record_probe",
        lambda *args, **kwargs: 123,
    )
    monkeypatch.setattr(
        main,
        "detect_latency_anomaly",
        lambda *args, **kwargs: {"is_anomaly": False},
    )
    monkeypatch.setattr(
        main.IncidentManager,
        "process_observation",
        lambda self, *args, **kwargs: None,
    )

    monkeypatch.setattr(
        main,
        "dns_probe",
        lambda host: {
            "host": host,
            "resolved": False,
            "addresses": [],
            "latency_ms": 1.0,
            "error": "Name or service not known",
            "failure_type": "dns_error",
        },
    )

    monkeypatch.setattr(
        main,
        "tcp_probe",
        lambda host, port, timeout=2.0: {
            "host": host,
            "port": port,
            "connected": False,
            "latency_ms": 1.0,
            "error": "Name or service not known",
            "failure_type": "dns_error",
        },
    )

    monkeypatch.setattr(
        main,
        "probe_once",
        lambda url, timeout: {
            "status": None,
            "latency_ms": 1.0,
            "error": "Name or service not known",
            "failure_type": "connection_error",
        },
    )

    response = client.post(
        "/diagnostics/probe",
        json={"url": "http://localhost:8000/health"},
    )


    assert response.status_code == 200
    data = response.json()

    assert data["network_results"]["dns"]["resolved"] is False
    assert data["network_results"]["tcp"]["connected"] is False

    assert data["diagnostic"]["category"] == "dns_error"
    assert data["diagnostic"]["severity"] == "high"



def test_probe_reports_tcp_connection_failure(monkeypatch):
    from app import main
    main.app.state.incident_manager = main.IncidentManager()

    monkeypatch.setattr(
        main,
        "record_probe",
        lambda *args, **kwargs: 123,
    )
    monkeypatch.setattr(
        main,
        "detect_latency_anomaly",
        lambda *args, **kwargs: {"is_anomaly": False},
    )
    monkeypatch.setattr(
        main.IncidentManager,
        "process_observation",
        lambda self, *args, **kwargs: None,
    )

    monkeypatch.setattr(
        main,
        "dns_probe",
        lambda host: {
            "host": host,
            "resolved": True,
            "addresses": ["127.0.0.1"],
            "latency_ms": 1.0,
            "error": None,
            "failure_type": None,
        },
    )

    monkeypatch.setattr(
        main,
        "tcp_probe",
        lambda host, port, timeout=2.0: {
            "host": host,
            "port": port,
            "connected": False,
            "latency_ms": 1.0,
            "error": "Connection refused",
            "failure_type": "connection_error",
        },
    )

    monkeypatch.setattr(
        main,
        "probe_once",
        lambda url, timeout: {
            "status": None,
            "latency_ms": 1.0,
            "error": "Connection refused",
            "failure_type": "connection_error",
        },
    )

    response = client.post(
        "/diagnostics/probe",
        json={"url": "http://localhost:8000/health"},
    )


    assert response.status_code == 200
    data = response.json()

    assert data["network_results"]["dns"]["resolved"] is True
    assert data["network_results"]["tcp"]["connected"] is False
    assert data["network_results"]["tcp"]["port"] == 8000

    assert data["diagnostic"]["category"] == "connection_error"
    assert data["diagnostic"]["severity"] == "high"
    assert any(
        "8000" in item for item in data["diagnostic"]["evidence"]
    )
