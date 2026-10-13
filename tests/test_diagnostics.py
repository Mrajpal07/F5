
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



def test_redirect_diagnostic():
    result = diagnose_probe_result({
        "status": 302,
        "latency_ms": 5.0,
        "error": "HTTP Error 302: Redirect blocked",
        "failure_type": "http_error",
    })

    assert result["category"] == "http_error"
    assert "HTTP status: 302." in result["evidence"]
    assert any("redirect" in item.lower() for item in result["evidence"])
    assert "redirected" in result["assessment"].lower()


def test_client_error_diagnostic():
    result = diagnose_probe_result({
        "status": 404,
        "latency_ms": 5.0,
        "error": "HTTP Error 404: Not Found",
        "failure_type": "http_error",
    })

    assert result["category"] == "http_error"
    assert "HTTP status: 404." in result["evidence"]
    assert "4xx" in result["assessment"]


def test_server_error_diagnostic():
    result = diagnose_probe_result({
        "status": 503,
        "latency_ms": 5.0,
        "error": "HTTP Error 503: Service Unavailable",
        "failure_type": "http_error",
    })

    assert result["category"] == "http_error"
    assert "HTTP status: 503." in result["evidence"]
    assert "5xx" in result["assessment"]



def test_connection_error_includes_recommended_checks():
    result = diagnose_probe_result({
        "status": None,
        "latency_ms": 2.0,
        "error": "Connection refused",
        "failure_type": "connection_error",
    })

    checks = result["recommended_checks"]
    assert len(checks) > 0
    assert any("listening" in check for check in checks)


def test_timeout_includes_recommended_checks():
    result = diagnose_probe_result({
        "status": None,
        "latency_ms": 1000.0,
        "error": "timed out",
        "failure_type": "timeout",
    })

    checks = result["recommended_checks"]
    assert len(checks) > 0
    assert any("response times" in check.lower() for check in checks)


def test_redirect_includes_recommended_checks():
    result = diagnose_probe_result({
        "status": 302,
        "latency_ms": 5.0,
        "error": "HTTP Error 302: Redirect blocked",
        "failure_type": "http_error",
    })

    checks = result["recommended_checks"]
    assert any("location" in check.lower() for check in checks)


def test_server_error_includes_recommended_checks():
    result = diagnose_probe_result({
        "status": 503,
        "latency_ms": 5.0,
        "error": "HTTP Error 503: Service Unavailable",
        "failure_type": "http_error",
    })

    checks = result["recommended_checks"]
    assert any("logs" in check.lower() for check in checks)


def test_healthy_result_includes_recommended_checks():
    result = diagnose_probe_result({
        "status": 200,
        "latency_ms": 2.0,
        "error": None,
        "failure_type": None,
    })

    checks = result["recommended_checks"]
    assert len(checks) > 0
    assert any("monitoring" in check.lower() for check in checks)



def test_dns_failure_diagnostic():
    result = diagnose_probe_result(
        {
            "status": None,
            "latency_ms": 0.0,
            "error": "Name or service not known",
            "failure_type": "connection_error",
        },
        network_results={
            "dns": {
                "host": "nonexistent.invalid",
                "resolved": False,
                "addresses": [],
                "error": "Name or service not known",
                "failure_type": "dns_error",
            }
        },
    )

    assert result["category"] == "dns_error"
    assert result["severity"] == "high"
    assert any("nonexistent.invalid" in item for item in result["evidence"])
    assert any("resolver" in item.lower() for item in result["recommended_checks"])


def test_tcp_connection_failure_diagnostic():
    result = diagnose_probe_result(
        {
            "status": None,
            "latency_ms": 0.0,
            "error": "Connection refused",
            "failure_type": "connection_error",
        },
        network_results={
            "dns": {
                "host": "example.test",
                "resolved": True,
                "addresses": ["192.0.2.10"],
                "error": None,
                "failure_type": None,
            },
            "tcp": {
                "host": "example.test",
                "port": 443,
                "connected": False,
                "latency_ms": 1.0,
                "error": "Connection refused",
                "failure_type": "connection_error",
            },
        },
    )

    assert result["category"] == "connection_error"
    assert result["severity"] == "high"
    assert any("443" in item for item in result["evidence"])
    assert any("listening" in item.lower() for item in result["recommended_checks"])


def test_tcp_timeout_diagnostic():
    result = diagnose_probe_result(
        {
            "status": None,
            "latency_ms": 0.0,
            "error": "Connection timed out",
            "failure_type": "timeout",
        },
        network_results={
            "tcp": {
                "host": "example.test",
                "port": 443,
                "connected": False,
                "latency_ms": 1000.0,
                "error": "Connection timed out",
                "failure_type": "timeout",
            }
        },
    )

    assert result["category"] == "timeout"
    assert result["severity"] == "high"
    assert any("routing" in item.lower() for item in result["recommended_checks"])


def test_conflicting_tcp_and_http_results_request_more_evidence():
    result = diagnose_probe_result(
        {
            "status": 200,
            "latency_ms": 12.0,
            "error": None,
            "failure_type": None,
        },
        network_results={
            "dns": {
                "host": "example.test",
                "resolved": True,
                "addresses": ["192.0.2.10"],
                "error": None,
                "failure_type": None,
            },
            "tcp": {
                "host": "example.test",
                "port": 443,
                "connected": False,
                "latency_ms": 1000.0,
                "error": "Connection refused",
                "failure_type": "connection_error",
            },
        },
    )

    assert result["category"] == "unknown"
    assert any(
        "conflict" in item.lower()
        for item in result["evidence"]
    )
    assert any(
        "repeat" in item.lower()
        for item in result["recommended_checks"]
    )

def test_conflicting_dns_and_successful_tcp_http_results_request_more_evidence():
    result = diagnose_probe_result(
        {
            "status": 200,
            "latency_ms": 12.0,
            "error": None,
            "failure_type": None,
        },
        network_results={
            "dns": {
                "host": "example.test",
                "resolved": False,
                "addresses": [],
                "error": "Name or service not known",
                "failure_type": "dns_error",
            },
            "tcp": {
                "host": "example.test",
                "port": 443,
                "connected": True,
                "latency_ms": 5.0,
                "error": None,
                "failure_type": None,
            },
        },
    )

    assert result["category"] == "unknown"
    assert any(
        "conflict" in item.lower()
        for item in result["evidence"]
    )
    assert any(
        "repeat" in item.lower()
        for item in result["recommended_checks"]
    )