
from app.diagnostics.engine import diagnose_probe_result


def test_connection_error_diagnostic():
    result = diagnose_probe_result({
        "status": None,
        "latency_ms": 2.0,
        "error": "Connection refused",
        "failure_type": "connection_error",
    })

    assert result["category"] == "connection_error"
    assert result["severity"] == "high"
    assert "Connection refused" in result["evidence"]


def test_timeout_diagnostic():
    result = diagnose_probe_result({
        "status": None,
        "latency_ms": 1000.0,
        "error": "timed out",
        "failure_type": "timeout",
    })

    assert result["category"] == "timeout"
    assert result["severity"] == "high"
    assert any("1000.0 ms" in item for item in result["evidence"])


def test_http_error_diagnostic():
    result = diagnose_probe_result({
        "status": 503,
        "latency_ms": 5.0,
        "error": "HTTP Error 503",
        "failure_type": "http_error",
    })

    assert result["category"] == "http_error"
    assert result["severity"] == "medium"
    assert "HTTP status: 503." in result["evidence"]


def test_healthy_diagnostic():
    result = diagnose_probe_result({
        "status": 200,
        "latency_ms": 2.0,
        "error": None,
        "failure_type": None,
    })

    assert result["category"] == "healthy"
    assert result["severity"] == "info"
    assert "HTTP status: 200." in result["evidence"]


def test_unknown_result_requests_more_evidence():
    result = diagnose_probe_result({
        "status": None,
        "latency_ms": 0.0,
        "error": None,
        "failure_type": None,
    })

    assert result["category"] == "unknown"
    assert result["severity"] == "medium"
    assert "Collect additional evidence before drawing a conclusion." == (
        result["assessment"]
    )
