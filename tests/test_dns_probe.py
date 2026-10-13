
import socket

import pytest

from app.probes.dns_probe import dns_probe


def test_dns_probe_success(monkeypatch):
    def fake_getaddrinfo(host, port, type):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.10", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.10", 0)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2001:db8::10", 0, 0, 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    result = dns_probe("example.test")

    assert result["resolved"] is True
    assert result["addresses"] == ["192.0.2.10", "2001:db8::10"]
    assert result["failure_type"] is None
    assert result["error"] is None
    assert result["latency_ms"] >= 0


def test_dns_probe_failure(monkeypatch):
    def fail_dns(*args, **kwargs):
        raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", fail_dns)

    result = dns_probe("nonexistent.invalid")

    assert result["resolved"] is False
    assert result["addresses"] == []
    assert result["failure_type"] == "dns_error"
    assert result["error"] is not None


@pytest.mark.parametrize("host", ["", "   ", None, 123])
def test_dns_probe_rejects_invalid_host(host):
    with pytest.raises(ValueError):
        dns_probe(host)
