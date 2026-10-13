
import math
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.history.store import DEFAULT_DB_PATH


def calculate_percentile(values, percentile):
    """Calculate a percentile using the nearest-rank method."""
    if not values:
        return None

    if not 0 < percentile <= 100:
        raise ValueError("percentile must be greater than 0 and at most 100")

    ordered = sorted(values)
    rank = math.ceil((percentile / 100) * len(ordered))
    return ordered[rank - 1]


def get_reliability_summary(
    target,
    db_path=DEFAULT_DB_PATH,
    window_hours=24,
):
    """Summarize probe reliability within a recent time window."""

    if not 1 <= window_hours <= 168:
        raise ValueError("window_hours must be between 1 and 168")

    db_path = Path(db_path)
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=window_hours)
    ).isoformat()

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT status, latency_ms, failure_type
            FROM probe_history
            WHERE target = ? AND timestamp >= ?
            ORDER BY timestamp ASC, id ASC
            """,
            (target, cutoff),
        ).fetchall()

    total_probes = len(rows)

    successful_latencies = [
        latency_ms
        for status, latency_ms, _ in rows
        if status is not None and 200 <= status < 300
    ]

    successful_probes = len(successful_latencies)
    failed_probes = total_probes - successful_probes

    latencies = [latency_ms for _, latency_ms, _ in rows]

    failure_counts = {}

    for status, _, failure_type in rows:
        is_success = status is not None and 200 <= status < 300

        if not is_success and failure_type:
            failure_counts[failure_type] = (
                failure_counts.get(failure_type, 0) + 1
            )

    return {
        "target": target,
        "window_hours": window_hours,
        "total_probes": total_probes,
        "successful_probes": successful_probes,
        "failed_probes": failed_probes,
        "availability_percent": (
            successful_probes / total_probes * 100
            if total_probes
            else None
        ),
        "failure_rate_percent": (
            failed_probes / total_probes * 100
            if total_probes
            else None
        ),
        "average_latency_ms": (
            sum(latencies) / len(latencies)
            if latencies
            else None
        ),
        "p95_latency_ms": calculate_percentile(latencies, 95),
        "failure_counts": failure_counts,
    }
