
from dataclasses import dataclass, field

import pytest

from app.incidents.store import (
    initialize_incident_store,
    save_incident,
    get_incident_history,
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


def test_returns_active_and_resolved_incidents(tmp_path):
    db_path = tmp_path / "incidents.db"
    initialize_incident_store(db_path)

    save_incident(
        FakeIncident(
            target="http://localhost:8000/health",
            category="availability",
            severity="high",
        ),
        db_path,
    )
    save_incident(
        FakeIncident(
            target="http://localhost:8001/health",
            category="latency",
            severity="medium",
            status="resolved",
        ),
        db_path,
    )

    incidents = get_incident_history(db_path)

    assert len(incidents) == 2
    assert {item["status"] for item in incidents} == {
        "active",
        "resolved",
    }


def test_filters_history_by_status_and_target(tmp_path):
    db_path = tmp_path / "incidents.db"
    initialize_incident_store(db_path)

    target = "http://localhost:8000/health"

    save_incident(
        FakeIncident(target, "availability", "high"),
        db_path,
    )
    save_incident(
        FakeIncident(target, "latency", "medium", status="resolved"),
        db_path,
    )

    active = get_incident_history(db_path, status="active")
    resolved = get_incident_history(
        db_path,
        status="resolved",
        target=target,
    )

    assert len(active) == 1
    assert active[0]["category"] == "availability"
    assert len(resolved) == 1
    assert resolved[0]["category"] == "latency"


def test_rejects_invalid_status_and_limit(tmp_path):
    db_path = tmp_path / "incidents.db"
    initialize_incident_store(db_path)

    with pytest.raises(ValueError):
        get_incident_history(db_path, status="pending")

    with pytest.raises(ValueError):
        get_incident_history(db_path, limit=0)
