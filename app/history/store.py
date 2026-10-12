
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB_PATH = Path("data/netreliant.db")


def initialize_database(db_path=DEFAULT_DB_PATH):
    """Create the database and probe history table if they do not exist."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS probe_history (
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
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_probe_history_target_timestamp
            ON probe_history (target, timestamp)
            """
        )


def record_probe(target, observation, diagnostic, db_path=DEFAULT_DB_PATH):
    """Persist one probe observation and its diagnostic finding."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO probe_history (
                target,
                timestamp,
                status,
                latency_ms,
                failure_type,
                observation_json,
                diagnostic_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                target,
                timestamp,
                observation.get("status"),
                observation["latency_ms"],
                observation.get("failure_type"),
                json.dumps(observation),
                json.dumps(diagnostic),
            ),
        )
        record_id = cursor.lastrowid

    return record_id


def get_probe_history(target, limit=50, db_path=DEFAULT_DB_PATH):
    """Return recent probe records for one target, newest first."""
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, target, timestamp, status, latency_ms,
                   failure_type, observation_json, diagnostic_json
            FROM probe_history
            WHERE target = ?
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (target, limit),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "target": row["target"],
            "timestamp": row["timestamp"],
            "status": row["status"],
            "latency_ms": row["latency_ms"],
            "failure_type": row["failure_type"],
            "observation": json.loads(row["observation_json"]),
            "diagnostic": json.loads(row["diagnostic_json"]),
        }
        for row in rows
    ]
