
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.history.store import DEFAULT_DB_PATH


def initialize_incident_store(db_path=DEFAULT_DB_PATH):
    """Create the incidents table if it does not exist."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                failure_count INTEGER NOT NULL DEFAULT 0,
                anomaly_count INTEGER NOT NULL DEFAULT 0,
                recovery_count INTEGER NOT NULL DEFAULT 0,
                evidence_json TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT
            )
            """
        )


        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS detection_state (
                target TEXT PRIMARY KEY,
                failure_streak INTEGER NOT NULL DEFAULT 0,
                anomaly_streak INTEGER NOT NULL DEFAULT 0,
                failure_evidence_json TEXT NOT NULL DEFAULT '[]',
                anomaly_evidence_json TEXT NOT NULL DEFAULT '[]'
            )
            """
        )




def save_incident(incident, db_path=DEFAULT_DB_PATH):
    """Insert a new incident or update it by its database ID."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(db_path) as connection:
        if incident.incident_id is not None:
            row = connection.execute(
                """
                SELECT opened_at
                FROM incidents
                WHERE id = ?
                """,
                (incident.incident_id,),
            ).fetchone()
        else:
            row = None

        resolved_at = now if incident.status == "resolved" else None

        if row:
            connection.execute(
                """
                UPDATE incidents
                SET severity = ?, status = ?, failure_count = ?,
                    anomaly_count = ?, recovery_count = ?,
                    evidence_json = ?, updated_at = ?, resolved_at = ?
                WHERE id = ?
                """,
                (
                    incident.severity,
                    incident.status,
                    incident.failure_count,
                    incident.anomaly_count,
                    incident.recovery_count,
                    json.dumps(incident.evidence),
                    now,
                    resolved_at,
                    incident.incident_id,
                ),
            )
            return incident.incident_id

        cursor = connection.execute(
            """
            INSERT INTO incidents (
                target, category, severity, status, failure_count,
                anomaly_count, recovery_count, evidence_json,
                opened_at, updated_at, resolved_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident.target,
                incident.category,
                incident.severity,
                incident.status,
                incident.failure_count,
                incident.anomaly_count,
                incident.recovery_count,
                json.dumps(incident.evidence),
                now,
                now,
                resolved_at,
            ),
        )
        incident.incident_id = cursor.lastrowid
        return incident.incident_id


def load_active_incidents(db_path=DEFAULT_DB_PATH):
    """Load active incidents as dictionaries, newest updates first."""
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, target, category, severity, status,
                   failure_count, anomaly_count, recovery_count,
                   evidence_json, opened_at, updated_at, resolved_at
            FROM incidents
            WHERE status = 'active'
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()

    return [
        {
            "id": row["id"],
            "target": row["target"],
            "category": row["category"],
            "severity": row["severity"],
            "status": row["status"],
            "failure_count": row["failure_count"],
            "anomaly_count": row["anomaly_count"],
            "recovery_count": row["recovery_count"],
            "evidence": json.loads(row["evidence_json"]),
            "opened_at": row["opened_at"],
            "updated_at": row["updated_at"],
            "resolved_at": row["resolved_at"],
        }
        for row in rows
    ]




def get_incident_history(
    db_path=DEFAULT_DB_PATH,
    status=None,
    target=None,
    limit=50,
):
    """Return incident history, optionally filtered by status and target."""
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")

    db_path = Path(db_path)

    query = """
        SELECT id, target, category, severity, status,
               failure_count, anomaly_count, recovery_count,
               evidence_json, opened_at, updated_at, resolved_at
        FROM incidents
        WHERE 1 = 1
    """
    parameters = []

    if status is not None:
        if status not in {"active", "resolved"}:
            raise ValueError("status must be 'active' or 'resolved'")
        query += " AND status = ?"
        parameters.append(status)

    if target is not None:
        query += " AND target = ?"
        parameters.append(target)

    query += " ORDER BY updated_at DESC, id DESC LIMIT ?"
    parameters.append(limit)

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, parameters).fetchall()

    return [
        {
            "id": row["id"],
            "target": row["target"],
            "category": row["category"],
            "severity": row["severity"],
            "status": row["status"],
            "failure_count": row["failure_count"],
            "anomaly_count": row["anomaly_count"],
            "recovery_count": row["recovery_count"],
            "evidence": json.loads(row["evidence_json"]),
            "opened_at": row["opened_at"],
            "updated_at": row["updated_at"],
            "resolved_at": row["resolved_at"],
        }
        for row in rows
    ]


def get_incident_by_id(incident_id, db_path=DEFAULT_DB_PATH):
    """Return one incident by ID, or None if it does not exist."""
    if incident_id < 1:
        raise ValueError("incident_id must be positive")

    db_path = Path(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT id, target, category, severity, status,
                   failure_count, anomaly_count, recovery_count,
                   evidence_json, opened_at, updated_at, resolved_at
            FROM incidents
            WHERE id = ?
            """,
            (incident_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "target": row["target"],
        "category": row["category"],
        "severity": row["severity"],
        "status": row["status"],
        "failure_count": row["failure_count"],
        "anomaly_count": row["anomaly_count"],
        "recovery_count": row["recovery_count"],
        "evidence": json.loads(row["evidence_json"]),
        "opened_at": row["opened_at"],
        "updated_at": row["updated_at"],
        "resolved_at": row["resolved_at"],
    }



def save_detection_state(
    target,
    failure_streak,
    anomaly_streak,
    failure_evidence,
    anomaly_evidence,
    db_path=DEFAULT_DB_PATH,
):
    """Persist the pre-incident detection state for a target."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO detection_state (
                target,
                failure_streak,
                anomaly_streak,
                failure_evidence_json,
                anomaly_evidence_json
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(target) DO UPDATE SET
                failure_streak = excluded.failure_streak,
                anomaly_streak = excluded.anomaly_streak,
                failure_evidence_json = excluded.failure_evidence_json,
                anomaly_evidence_json = excluded.anomaly_evidence_json
            """,
            (
                target,
                failure_streak,
                anomaly_streak,
                json.dumps(failure_evidence),
                json.dumps(anomaly_evidence),
            ),
        )


def load_detection_states(db_path=DEFAULT_DB_PATH):
    """Load persisted detection state for all targets."""
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT target, failure_streak, anomaly_streak,
                   failure_evidence_json, anomaly_evidence_json
            FROM detection_state
            """
        ).fetchall()

    return {
        row["target"]: {
            "failure_streak": row["failure_streak"],
            "anomaly_streak": row["anomaly_streak"],
            "failure_evidence": json.loads(
                row["failure_evidence_json"]
            ),
            "anomaly_evidence": json.loads(
                row["anomaly_evidence_json"]
            ),
        }
        for row in rows
    }
