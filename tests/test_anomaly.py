
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from app.analytics.anomaly import detect_latency_anomaly


def create_test_database(db_path, observations):
    now = datetime.now(timezone.utc)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE probe_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status INTEGER,
                latency_ms REAL NOT NULL,
                failure_type TEXT,
                observation_json TEXT NOT NULL,
                diagnostic_json TEXT NOT NULL
            )
            """
        )

        connection.executemany(
            """
            INSERT INTO probe_history (
                target, timestamp, status, latency_ms,
                failure_type, observation_json, diagnostic_json
            )
            VALUES (?, ?, ?, ?, ?, '{}', '{}')
            """,
            [
                (
                    target,
                    (
                        now - timedelta(minutes=len(observations) - index)
                    ).isoformat(),
                    status,
                    latency,
                    failure_type,
                )
                for index, (target, status, latency, failure_type)
                in enumerate(observations)
            ],
        )


def test_detects_latency_anomaly(tmp_path):
    db_path = tmp_path / "test.db"
    target = "http://localhost:8000/health"

    observations = [
        (target, 200, 20.0, None),
        (target, 200, 25.0, None),
        (target, 200, 30.0, None),
        (target, 200, 35.0, None),
        (target, 200, 40.0, None),
        (target, 200, 150.0, None),
    ]
    create_test_database(db_path, observations)

    result = detect_latency_anomaly(
        target,
        db_path,
        minimum_latency_ms=100,
        anomaly_multiplier=2,
    )

    assert result["status"] == "anomaly_detected"
    assert result["latest_latency_ms"] == 150.0
    assert result["baseline_samples"] == 5
    assert result["threshold_ms"] == 100.0
    assert result["is_anomaly"] is True


def test_normal_latency_is_not_an_anomaly(tmp_path):
    db_path = tmp_path / "test.db"
    target = "http://localhost:8000/health"

    observations = [
        (target, 200, 20.0, None),
        (target, 200, 25.0, None),
        (target, 200, 30.0, None),
        (target, 200, 35.0, None),
        (target, 200, 40.0, None),
        (target, 200, 45.0, None),
    ]
    create_test_database(db_path, observations)

    result = detect_latency_anomaly(target, db_path)

    assert result["status"] == "normal"
    assert result["is_anomaly"] is False


def test_insufficient_history_is_reported(tmp_path):
    db_path = tmp_path / "test.db"
    target = "http://localhost:8000/health"

    create_test_database(
        db_path,
        [(target, 200, 20.0, None)],
    )

    result = detect_latency_anomaly(target, db_path)

    assert result["status"] == "insufficient_data"
    assert result["is_anomaly"] is None


def test_latest_failed_probe_is_not_latency_anomaly(tmp_path):
    db_path = tmp_path / "test.db"
    target = "http://localhost:8000/health"

    observations = [
        (target, 200, 20.0, None),
        (target, 200, 25.0, None),
        (target, 200, 30.0, None),
        (target, 200, 35.0, None),
        (target, 200, 40.0, None),
        (target, None, 10.0, "connection_error"),
    ]
    create_test_database(db_path, observations)

    result = detect_latency_anomaly(target, db_path)

    assert result["status"] == "latest_probe_failed"
    assert result["is_anomaly"] is None


def test_invalid_configuration_is_rejected(tmp_path):
    db_path = tmp_path / "test.db"
    create_test_database(db_path, [])

    with pytest.raises(ValueError, match="baseline_limit"):
        detect_latency_anomaly(
            "http://localhost:8000/health",
            db_path,
            baseline_limit=1,
        )
