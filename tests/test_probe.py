import pytest

from scripts.baseline_probe import analyse_results


def test_all_requests_successful():
    observations = [
        {"status": 200, "latency_ms": 2.0, "error": None},
        {"status": 200, "latency_ms": 4.0, "error": None},
    ]

    summary = analyse_results(observations)

    assert summary["total_requests"] == 2
    assert summary["successful_requests"] == 2
    assert summary["failed_requests"] == 0
    assert summary["success_rate_pct"] == 100.0
    assert summary["latency_ms"]["mean"] == 3.0


def test_failed_request_is_counted():
    observations = [
        {"status": 200, "latency_ms": 2.0, "error": None},
        {"status": None, "latency_ms": 100.0, "error": "connection refused"},
    ]

    summary = analyse_results(observations)

    assert summary["successful_requests"] == 1
    assert summary["failed_requests"] == 1
    assert summary["success_rate_pct"] == 50.0


def test_server_error_is_not_successful():
    observations = [
        {"status": 500, "latency_ms": 5.0, "error": None},
    ]

    summary = analyse_results(observations)

    assert summary["successful_requests"] == 0
    assert summary["failed_requests"] == 1
    assert summary["success_rate_pct"] == 0.0


def test_empty_observations_are_rejected():
    with pytest.raises(ValueError):
        analyse_results([])
