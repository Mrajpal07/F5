
import sqlite3
from datetime import datetime, timedelta, timezone

from app.analytics.reliability import (
    calculate_percentile,
    get_reliability_summary,
)


def create_test_database(db_path, observations):
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
        now = datetime.now(timezone.utc)

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
                    (now - timedelta(minutes=len(observations) - index)).isoformat(),
                    status,
                    latency,
                    failure_type,
                )
                for index, (
                    target,
                    status,
                    latency,
                    failure_type,
                ) in enumerate(observations)
            ],
        )


def test_reliability_summary_calculates_metrics(tmp_path):
    db_path = tmp_path / "test.db"
    target = "http://localhost:8000/health"

    create_test_database(
        db_path,
        [
            (target, 200, 10.0, None),
            (target, 204, 20.0, None),
            (target, 500, 30.0, "http_error"),
            (target, None, 40.0, "connection_error"),
        ],
    )

    result = get_reliability_summary(target, db_path)

    assert result["total_probes"] == 4
    assert result["successful_probes"] == 2
    assert result["failed_probes"] == 2
    assert result["availability_percent"] == 50.0
    assert result["failure_rate_percent"] == 50.0
    assert result["average_latency_ms"] == 25.0
    assert result["p95_latency_ms"] == 40.0


def test_reliability_summary_handles_empty_history(tmp_path):
    db_path = tmp_path / "test.db"
    create_test_database(db_path, [])

    result = get_reliability_summary(
        "http://localhost:8000/health",
        db_path,
    )

    assert result["total_probes"] == 0
    assert result["successful_probes"] == 0
    assert result["failed_probes"] == 0
    assert result["availability_percent"] is None
    assert result["failure_rate_percent"] is None
    assert result["average_latency_ms"] is None
    assert result["p95_latency_ms"] is None


def test_nearest_rank_percentile():
    assert calculate_percentile([10, 20, 30, 40], 95) == 40
    assert calculate_percentile([40, 10, 30, 20], 50) == 20
    assert calculate_percentile([], 95) is None


def test_reliability_summary_rejects_invalid_window(tmp_path):
    db_path = tmp_path / "test.db"
    create_test_database(db_path, [])

    import pytest

    with pytest.raises(ValueError, match="window_hours"):
        get_reliability_summary(
            "http://localhost:8000/health",
            db_path,
            window_hours=0,
        )
