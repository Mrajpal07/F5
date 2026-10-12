
import app.main as main_module
from fastapi.testclient import TestClient


def test_probe_records_history(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"


    original_initialize_database = main_module.initialize_database
    original_record_probe = main_module.record_probe
    original_get_probe_history = main_module.get_probe_history

    monkeypatch.setattr(
        main_module,
        "initialize_database",
        lambda: original_initialize_database(db_path),
    )

    monkeypatch.setattr(
        main_module,
        "record_probe",
        lambda target, observation, diagnostic: original_record_probe(
            target, observation, diagnostic, db_path
        ),
    )

    monkeypatch.setattr(
        main_module,
        "get_probe_history",
        lambda target, limit=50: original_get_probe_history(
            target, limit, db_path
        ),
    )

    monkeypatch.setattr(
        main_module,
        "probe_once",
        lambda url, timeout: {
            "status": 200,
            "latency_ms": 12.5,
            "error": None,
            "failure_type": None,
        },
    )

    with TestClient(main_module.app) as client:
        target = "http://127.0.0.1:8000/health"

        probe_response = client.post(
            "/diagnostics/probe",
            json={"url": target, "timeout": 2},
        )

        assert probe_response.status_code == 200
        probe_body = probe_response.json()
        assert probe_body["record_id"] == 1
        assert probe_body["observation"]["status"] == 200

        history_response = client.get(
            "/diagnostics/history",
            params={"url": target},
        )

        assert history_response.status_code == 200
        history_body = history_response.json()
        assert history_body["target"] == target
        assert history_body["count"] == 1
        assert history_body["records"][0]["id"] == 1
        assert history_body["records"][0]["diagnostic"]["category"] == "healthy"


def test_history_rejects_invalid_limit():
    from app.main import app

    with TestClient(app) as client:
        response = client.get(
            "/diagnostics/history",
            params={
                "url": "http://127.0.0.1:8000/health",
                "limit": 0,
            },
        )

    assert response.status_code == 422
