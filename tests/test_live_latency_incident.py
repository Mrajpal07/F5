
import app.main as main_module
from fastapi.testclient import TestClient

from app.incidents.manager import IncidentManager


def test_three_live_latency_anomalies_open_incident(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "latency-test.db"

    original_initialize_database = main_module.initialize_database

    monkeypatch.setattr(
        main_module,
        "initialize_database",
        lambda: original_initialize_database(db_path),
    )
    monkeypatch.setattr(
        main_module,
        "IncidentManager",
        lambda: IncidentManager(db_path),
    )
    monkeypatch.setattr(
        main_module,
        "probe_once",
        lambda url, timeout: {
            "status": 200,
            "latency_ms": 150.0,
            "error": None,
            "failure_type": None,
        },
    )
    monkeypatch.setattr(
        main_module,
        "record_probe",
        lambda *args: 1,
    )
    monkeypatch.setattr(
        main_module,
        "detect_latency_anomaly",
        lambda target: {
            "target": target,
            "status": "anomaly_detected",
            "is_anomaly": True,
            "latest_latency_ms": 150.0,
            "threshold_ms": 100.0,
        },
    )

    target = "http://127.0.0.1:8000/health"

    with TestClient(main_module.app) as client:
        first = client.post(
            "/diagnostics/probe",
            json={"url": target},
        )
        second = client.post(
            "/diagnostics/probe",
            json={"url": target},
        )
        third = client.post(
            "/diagnostics/probe",
            json={"url": target},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200

    assert first.json()["incident_event"] is None
    assert second.json()["incident_event"] is None

    event = third.json()["incident_event"]
    assert event["category"] == "latency"
    assert event["severity"] == "medium"
    assert event["status"] == "active"
    assert event["incident_id"] is not None

    # Verify all three triggering observations were retained.
    manager = main_module.app.state.incident_manager
    incident = manager.active_incidents[(target, "latency")]

    assert len(incident.evidence) == 3
    assert all(
        item["latency_ms"] == 150.0
        for item in incident.evidence
    )
