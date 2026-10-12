
import app.main as main_module
from fastapi.testclient import TestClient


def configure_test_database(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"

    original_initialize_database = main_module.initialize_database
    original_record_probe = main_module.record_probe
    original_get_reliability_summary = (
        main_module.get_reliability_summary
    )

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
        "get_reliability_summary",
        lambda target, window_hours=24: original_get_reliability_summary(
            target,
            db_path,
            window_hours=window_hours,
        ),
    )


def test_reliability_endpoint_calculates_metrics(
    monkeypatch, tmp_path
):
    configure_test_database(monkeypatch, tmp_path)

    observations = iter([
        {
            "status": 200,
            "latency_ms": 10.0,
            "error": None,
            "failure_type": None,
        },
        {
            "status": 500,
            "latency_ms": 30.0,
            "error": "HTTP error",
            "failure_type": "http_error",
        },
    ])

    monkeypatch.setattr(
        main_module,
        "probe_once",
        lambda url, timeout: next(observations),
    )

    target = "http://127.0.0.1:8000/health"

    with TestClient(main_module.app) as client:
        for _ in range(2):
            response = client.post(
                "/diagnostics/probe",
                json={"url": target, "timeout": 2},
            )
            assert response.status_code == 200

        response = client.get(
            "/diagnostics/reliability",
            params={
                "url": target,
                "window_hours": 24,
            },
        )

    assert response.status_code == 200

    result = response.json()
    assert result["target"] == target
    assert result["window_hours"] == 24
    assert result["total_probes"] == 2
    assert result["successful_probes"] == 1
    assert result["failed_probes"] == 1
    assert result["availability_percent"] == 50.0
    assert result["failure_rate_percent"] == 50.0
    assert result["average_latency_ms"] == 20.0
    assert result["p95_latency_ms"] == 30.0


def test_reliability_endpoint_handles_empty_history(
    monkeypatch, tmp_path
):
    configure_test_database(monkeypatch, tmp_path)

    target = "http://127.0.0.1:8000/health"

    with TestClient(main_module.app) as client:
        response = client.get(
            "/diagnostics/reliability",
            params={"url": target},
        )

    assert response.status_code == 200

    result = response.json()
    assert result["total_probes"] == 0
    assert result["successful_probes"] == 0
    assert result["failed_probes"] == 0
    assert result["availability_percent"] is None
    assert result["failure_rate_percent"] is None
    assert result["average_latency_ms"] is None
    assert result["p95_latency_ms"] is None


def test_reliability_endpoint_rejects_invalid_window(
    monkeypatch, tmp_path
):
    configure_test_database(monkeypatch, tmp_path)

    target = "http://127.0.0.1:8000/health"

    with TestClient(main_module.app) as client:
        for invalid_window in (0, 169):
            response = client.get(
                "/diagnostics/reliability",
                params={
                    "url": target,
                    "window_hours": invalid_window,
                },
            )

            assert response.status_code == 422
