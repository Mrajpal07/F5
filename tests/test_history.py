
import json
import sqlite3

from app.history.store import (
    get_probe_history,
    initialize_database,
    record_probe,
)


def test_initialize_database_creates_history_table(tmp_path):
    db_path = tmp_path / "test.db"

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()

    assert ("probe_history",) in tables


def test_record_probe_persists_observation_and_diagnostic(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    observation = {
        "status": 200,
        "latency_ms": 12.5,
        "error": None,
        "failure_type": None,
    }
    diagnostic = {
        "category": "healthy",
        "severity": "info",
        "evidence": ["HTTP status: 200."],
        "assessment": "The endpoint returned a successful HTTP response.",
        "recommended_checks": ["Continue monitoring endpoint availability."],
    }

    record_id = record_probe(
        "http://localhost:8000/health",
        observation,
        diagnostic,
        db_path,
    )

    history = get_probe_history(
        "http://localhost:8000/health",
        db_path=db_path,
    )

    assert record_id == 1
    assert len(history) == 1
    assert history[0]["status"] == 200
    assert history[0]["latency_ms"] == 12.5
    assert history[0]["observation"] == observation
    assert history[0]["diagnostic"] == diagnostic
    assert history[0]["timestamp"]


def test_history_is_filtered_by_target(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    observation = {
        "status": 200,
        "latency_ms": 5.0,
        "error": None,
        "failure_type": None,
    }
    diagnostic = {"category": "healthy"}

    record_probe("http://localhost:8000/health", observation, diagnostic, db_path)
    record_probe("http://localhost:8000/", observation, diagnostic, db_path)

    history = get_probe_history(
        "http://localhost:8000/health",
        db_path=db_path,
    )

    assert len(history) == 1
    assert history[0]["target"] == "http://localhost:8000/health"


def test_history_limit_is_enforced(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    observation = {
        "status": 200,
        "latency_ms": 5.0,
        "error": None,
        "failure_type": None,
    }
    diagnostic = {"category": "healthy"}

    for _ in range(3):
        record_probe("http://localhost:8000/health", observation, diagnostic, db_path)

    history = get_probe_history(
        "http://localhost:8000/health",
        limit=2,
        db_path=db_path,
    )

    assert len(history) == 2


def test_invalid_history_limit_is_rejected(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    try:
        get_probe_history("http://localhost:8000/health", limit=0, db_path=db_path)
    except ValueError as exc:
        assert "between 1 and 500" in str(exc)
    else:
        raise AssertionError("Expected invalid history limit to be rejected")
