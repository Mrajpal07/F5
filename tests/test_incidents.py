
from app.incidents.manager import IncidentManager


def observation(status=200, failure_type=None, latency_ms=20.0):
    return {
        "status": status,
        "failure_type": failure_type,
        "latency_ms": latency_ms,
    }



def test_opens_availability_incident_after_three_failures(tmp_path):
    manager = IncidentManager(tmp_path / "incidents.db")
    target = "http://localhost:8000/health"

    assert manager.process_observation(
        target, observation(None, "connection_error")
    ) is None

    assert manager.process_observation(
        target, observation(None, "connection_error")
    ) is None

    incident = manager.process_observation(
        target, observation(None, "connection_error")
    )

    assert incident.category == "availability"
    assert incident.severity == "high"
    assert incident.status == "active"
    assert len(incident.evidence) == 3


def test_does_not_open_incident_for_isolated_failure(tmp_path):
    manager = IncidentManager(tmp_path / "incidents.db")
    target = "http://localhost:8000/health"

    incident = manager.process_observation(
        target, observation(None, "connection_error")
    )

    assert incident is None
    assert manager.active_incidents == {}


def test_resolves_incident_after_two_successes(tmp_path):
    manager = IncidentManager(tmp_path / "incidents.db")
    target = "http://localhost:8000/health"

    for _ in range(3):
        manager.process_observation(
            target, observation(None, "connection_error")
        )

    manager.process_observation(target, observation())
    resolved = manager.process_observation(target, observation())

    assert resolved.status == "resolved"
    assert manager.active_incidents == {}


def test_does_not_duplicate_active_incident(tmp_path):
    manager = IncidentManager(tmp_path / "incidents.db")
    target = "http://localhost:8000/health"

    for _ in range(5):
        manager.process_observation(
            target, observation(None, "connection_error")
        )

    assert len(manager.active_incidents) == 1


def test_opens_latency_incident_after_three_anomalies(tmp_path):
    manager = IncidentManager(tmp_path / "incidents.db")
    target = "http://localhost:8000/health"

    assert manager.process_observation(
        target, observation(), is_anomaly=True
    ) is None

    assert manager.process_observation(
        target, observation(), is_anomaly=True
    ) is None

    incident = manager.process_observation(
        target, observation(), is_anomaly=True
    )

    assert incident.category == "latency"
    assert incident.severity == "medium"
    assert incident.status == "active"


def test_active_incident_survives_manager_restart(tmp_path):
    db_path = tmp_path / "incidents.db"
    target = "http://localhost:8000/health"

    first_manager = IncidentManager(db_path)

    for _ in range(3):
        first_manager.process_observation(
            target, observation(None, "connection_error")
        )

    assert len(first_manager.active_incidents) == 1

    # Simulate an application restart by creating a new manager.
    second_manager = IncidentManager(db_path)

    assert len(second_manager.active_incidents) == 1

    incident = second_manager.active_incidents[(target, "availability")]
    assert incident.status == "active"
    assert incident.severity == "high"
    assert incident.incident_id is not None
    assert len(incident.evidence) == 3



def test_latency_incident_evidence_survives_manager_restart(tmp_path):
    db_path = tmp_path / "latency-incidents.db"
    target = "http://localhost:8000/health"

    first_manager = IncidentManager(db_path)

    # Three consecutive latency anomalies should open an incident.
    for _ in range(3):
        first_manager.process_observation(
            target,
            {
                "status": 200,
                "failure_type": None,
                "latency_ms": 150.0,
            },
            is_anomaly=True,
        )

    assert len(first_manager.active_incidents) == 1

    incident = first_manager.active_incidents[(target, "latency")]
    assert len(incident.evidence) == 3

    # Simulate a restart by loading the same SQLite database.
    second_manager = IncidentManager(db_path)

    assert len(second_manager.active_incidents) == 1

    restored = second_manager.active_incidents[(target, "latency")]
    assert restored.status == "active"
    assert restored.severity == "medium"
    assert restored.incident_id == incident.incident_id
    assert len(restored.evidence) == 3
    assert all(
        item["latency_ms"] == 150.0
        for item in restored.evidence
    )

def test_unknown_latency_does_not_resolve_latency_incident(tmp_path):
    manager = IncidentManager(tmp_path / "incidents.db")
    target = "http://localhost:8000/health"

    # Three consecutive anomalies open a latency incident.
    for _ in range(3):
        manager.process_observation(
            target, observation(), is_anomaly=True
        )

    incident = manager.active_incidents[(target, "latency")]
    assert incident.status == "active"
    assert incident.recovery_count == 0

    # A successful HTTP response with unknown latency classification
    # must not count toward latency recovery.
    manager.process_observation(
        target, observation(), is_anomaly=None
    )

    incident = manager.active_incidents[(target, "latency")]
    assert incident.status == "active"
    assert incident.recovery_count == 0

    # Even repeated unknown classifications must not resolve it.
    manager.process_observation(
        target, observation(), is_anomaly=None
    )

    incident = manager.active_incidents[(target, "latency")]
    assert incident.status == "active"
    assert incident.recovery_count == 0



def test_unknown_latency_still_allows_availability_recovery(tmp_path):
    manager = IncidentManager(tmp_path / "incidents.db")
    target = "http://localhost:8000/health"

    for _ in range(3):
        manager.process_observation(
            target, observation(None, "connection_error")
        )

    incident = manager.active_incidents[(target, "availability")]

    manager.process_observation(
        target, observation(), is_anomaly=None
    )
    assert incident.status == "active"
    assert incident.recovery_count == 1

    resolved = manager.process_observation(
        target, observation(), is_anomaly=None
    )

    assert resolved.status == "resolved"
    assert manager.active_incidents == {}



def test_failure_streak_survives_manager_restart(tmp_path):
    db_path = tmp_path / "failure-streak.db"
    target = "http://localhost:8000/health"

    first_manager = IncidentManager(db_path)

    for _ in range(2):
        first_manager.process_observation(
            target, observation(None, "connection_error")
        )

    # Restart before the third consecutive failure.
    second_manager = IncidentManager(db_path)

    second_manager.process_observation(
        target, observation(None, "connection_error")
    )

    incident = second_manager.active_incidents.get(
        (target, "availability")
    )

    assert incident is not None
    assert incident.status == "active"
    assert len(incident.evidence) == 3


def test_anomaly_streak_survives_manager_restart(tmp_path):
    db_path = tmp_path / "anomaly-streak.db"
    target = "http://localhost:8000/health"

    first_manager = IncidentManager(db_path)

    for _ in range(2):
        first_manager.process_observation(
            target,
            {
                "status": 200,
                "failure_type": None,
                "latency_ms": 150.0,
            },
            is_anomaly=True,
        )

    # Restart before the third consecutive latency anomaly.
    second_manager = IncidentManager(db_path)

    second_manager.process_observation(
        target,
        {
            "status": 200,
            "failure_type": None,
            "latency_ms": 150.0,
        },
        is_anomaly=True,
    )

    incident = second_manager.active_incidents.get(
        (target, "latency")
    )

    assert incident is not None
    assert incident.status == "active"
    assert len(incident.evidence) == 3
