
import app.main as main_module
from fastapi.testclient import TestClient


def test_anomaly_endpoint_handles_insufficient_history(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "test.db"

    original_initialize_database = main_module.initialize_database
    original_detect_latency_anomaly = (
        main_module.detect_latency_anomaly
    )

    monkeypatch.setattr(
        main_module,
        "initialize_database",
        lambda: original_initialize_database(db_path),
    )

    monkeypatch.setattr(
        main_module,
        "detect_latency_anomaly",
        lambda target, **kwargs: original_detect_latency_anomaly(
            target,
            db_path,
            **kwargs,
        ),
    )

    target = "http://127.0.0.1:8000/health"

    with TestClient(main_module.app) as client:
        response = client.get(
            "/diagnostics/anomaly",
            params={"url": target},
        )

    assert response.status_code == 200

    result = response.json()
    assert result["target"] == target
    assert result["status"] == "insufficient_data"
    assert result["baseline_samples"] == 0
    assert result["is_anomaly"] is None


def test_anomaly_endpoint_rejects_invalid_configuration():
    with TestClient(main_module.app) as client:
        response = client.get(
            "/diagnostics/anomaly",
            params={
                "url": "http://127.0.0.1:8000/health",
                "baseline_limit": 1,
            },
        )

    assert response.status_code == 422
