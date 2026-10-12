
import sqlite3
from pathlib import Path

from app.history.store import DEFAULT_DB_PATH
from app.analytics.reliability import calculate_percentile


def detect_latency_anomaly(
    target,
    db_path=DEFAULT_DB_PATH,
    baseline_limit=50,
    minimum_latency_ms=100.0,
    anomaly_multiplier=2.0,
):
    """Compare the latest successful probe against a latency baseline."""
    if not 5 <= baseline_limit <= 500:
        raise ValueError("baseline_limit must be between 5 and 500")

    if minimum_latency_ms <= 0:
        raise ValueError("minimum_latency_ms must be positive")

    if anomaly_multiplier <= 1:
        raise ValueError("anomaly_multiplier must be greater than 1")

    db_path = Path(db_path)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, timestamp, status, latency_ms, failure_type
            FROM probe_history
            WHERE target = ?
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (target, baseline_limit + 1),
        ).fetchall()

    if not rows:
        return {
            "target": target,
            "status": "insufficient_data",
            "reason": "No probe history exists for this target.",
            "baseline_samples": 0,
            "baseline_p95_ms": None,
            "latest_latency_ms": None,
            "threshold_ms": None,
            "is_anomaly": None,
        }

    latest = rows[0]
    latest_id, latest_timestamp, latest_status, latest_latency, latest_failure = (
        latest
    )

    if latest_status is None or not 200 <= latest_status < 300:
        return {
            "target": target,
            "status": "latest_probe_failed",
            "reason": "The latest probe was not a successful HTTP response.",
            "latest_probe_id": latest_id,
            "latest_timestamp": latest_timestamp,
            "latest_latency_ms": latest_latency,
            "baseline_samples": 0,
            "baseline_p95_ms": None,
            "threshold_ms": None,
            "is_anomaly": None,
        }

    baseline = [
        latency
        for _, _, status, latency, failure_type in rows[1:]
        if status is not None and 200 <= status < 300
    ]

    if len(baseline) < 5:
        return {
            "target": target,
            "status": "insufficient_data",
            "reason": "At least 5 earlier successful probes are required.",
            "latest_probe_id": latest_id,
            "latest_timestamp": latest_timestamp,
            "latest_latency_ms": latest_latency,
            "baseline_samples": len(baseline),
            "baseline_p95_ms": (
                calculate_percentile(baseline, 95) if baseline else None
            ),
            "threshold_ms": None,
            "is_anomaly": None,
        }

    baseline_p95 = calculate_percentile(baseline, 95)
    threshold = max(
        minimum_latency_ms,
        baseline_p95 * anomaly_multiplier,
    )
    is_anomaly = latest_latency > threshold

    return {
        "target": target,
        "status": "anomaly_detected" if is_anomaly else "normal",
        "reason": (
            "Latest latency exceeds the configured threshold."
            if is_anomaly
            else "Latest latency is within the configured threshold."
        ),
        "latest_probe_id": latest_id,
        "latest_timestamp": latest_timestamp,
        "latest_latency_ms": latest_latency,
        "baseline_samples": len(baseline),
        "baseline_p95_ms": baseline_p95,
        "threshold_ms": threshold,
        "is_anomaly": is_anomaly,
    }
