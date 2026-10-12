import pytest

from scripts.baseline_probe import analyse_results, probe_once
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


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



from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


def test_connection_refusal_is_classified():
    result = probe_once("http://localhost:8999/health", timeout=1)

    assert result["status"] is None
    assert result["failure_type"] == "connection_error"


def test_http_error_is_classified():
    class ErrorHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(503)
            self.end_headers()

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), ErrorHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        result = probe_once(
            f"http://127.0.0.1:{server.server_port}/health",
            timeout=2,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert result["status"] == 503
    assert result["failure_type"] == "http_error"


def test_successful_response_has_no_failure_type():
    class HealthyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), HealthyHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        result = probe_once(
            f"http://127.0.0.1:{server.server_port}/health",
            timeout=2,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert result["status"] == 200
    assert result["failure_type"] is None


def test_timeout_is_classified():
    class SlowHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            import time

            time.sleep(0.5)
            self.send_response(200)
            self.end_headers()

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), SlowHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        result = probe_once(
            f"http://127.0.0.1:{server.server_port}/health",
            timeout=0.1,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert result["status"] is None
    assert result["failure_type"] == "timeout"
