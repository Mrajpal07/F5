
from dataclasses import dataclass, field

from app.incidents.store import (
    initialize_incident_store,
    save_incident,
    load_active_incidents,
)


@dataclass
class FakeIncident:
    target: str
    category: str
    severity: str
    status: str = "active"
    failure_count: int = 0
    anomaly_count: int = 0
    recovery_count: int = 0
    evidence: list[dict] = field(default_factory=list)
    incident_id: int | None = None


def test_save_and_load_active_incident(tmp_path):
    db_path = tmp_path / "incidents.db"
    initialize_incident_store(db_path)

    incident = FakeIncident(
        target="http://localhost:8000/health",
        category="availability",
        severity="high",
        failure_count=3,
        evidence=[{"status": None, "failure_type": "connection_error"}],
    )

    incident_id = save_incident(incident, db_path)
    active = load_active_incidents(db_path)

    assert incident_id > 0
    assert len(active) == 1
    assert active[0]["target"] == incident.target
    assert active[0]["category"] == "availability"
    assert active[0]["severity"] == "high"
    assert active[0]["failure_count"] == 3
    assert active[0]["evidence"] == incident.evidence


def test_resolved_incident_is_not_listed_as_active(tmp_path):
    db_path = tmp_path / "incidents.db"
    initialize_incident_store(db_path)

    incident = FakeIncident(
        target="http://localhost:8000/health",
        category="availability",
        severity="high",
        status="resolved",
        recovery_count=2,
    )

    save_incident(incident, db_path)

    assert load_active_incidents(db_path) == []


def test_saving_incident_again_updates_existing_record(tmp_path):
    db_path = tmp_path / "incidents.db"
    initialize_incident_store(db_path)

    incident = FakeIncident(
        target="http://localhost:8000/health",
        category="availability",
        severity="high",
        failure_count=3,
    )

    first_id = save_incident(incident, db_path)

    incident.failure_count = 4
    incident.evidence.append({"status": None, "failure_type": "timeout"})
    second_id = save_incident(incident, db_path)

    assert first_id == second_id
    active = load_active_incidents(db_path)
    assert len(active) == 1
    assert active[0]["failure_count"] == 4
    assert len(active[0]["evidence"]) == 1
