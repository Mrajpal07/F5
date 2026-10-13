
import socket
import pytest

from threading import Thread

from app.probes.tcp_probe import tcp_probe


def test_tcp_probe_success():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    def accept_connection():
        connection, _ = server.accept()
        connection.close()

    thread = Thread(target=accept_connection, daemon=True)
    thread.start()

    try:
        result = tcp_probe("127.0.0.1", port, timeout=1)
    finally:
        server.close()
        thread.join(timeout=2)

    assert result["connected"] is True
    assert result["failure_type"] is None
    assert result["error"] is None
    assert result["latency_ms"] >= 0


def test_tcp_probe_connection_refused():
    temporary_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    temporary_socket.bind(("127.0.0.1", 0))
    port = temporary_socket.getsockname()[1]
    temporary_socket.close()

    result = tcp_probe("127.0.0.1", port, timeout=1)

    assert result["connected"] is False
    assert result["failure_type"] == "connection_error"
    assert result["error"] is not None





@pytest.mark.parametrize("port", [0, -1, 65536, True, 80.5, "80"])
def test_tcp_probe_rejects_invalid_port(port):
    with pytest.raises(ValueError):
        tcp_probe("127.0.0.1", port)


@pytest.mark.parametrize("host", ["", "   ", None, 123])
def test_tcp_probe_rejects_invalid_host(host):
    with pytest.raises(ValueError):
        tcp_probe(host, 80)


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), True])
def test_tcp_probe_rejects_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        tcp_probe("127.0.0.1", 80, timeout=timeout)



def test_tcp_probe_classifies_dns_failure(monkeypatch):
    def fail_dns(*args, **kwargs):
        raise socket.gaierror(
            socket.EAI_NONAME,
            "Name or service not known"
        )

    monkeypatch.setattr(socket, "create_connection", fail_dns)

    result = tcp_probe("nonexistent.invalid", 443, timeout=1)

    assert result["connected"] is False
    assert result["failure_type"] == "dns_error"
    assert result["error"] is not None
