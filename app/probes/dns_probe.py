
import socket
import time


def dns_probe(host):
    """Resolve a hostname and report DNS resolution results."""
    if not isinstance(host, str) or not host.strip():
        raise ValueError("host must be a non-empty string")

    host = host.strip()
    start = time.perf_counter()

    resolved = False
    addresses = []
    error = None
    failure_type = None

    try:
        results = socket.getaddrinfo(
            host,
            None,
            type=socket.SOCK_STREAM,
        )

        addresses = list(
            dict.fromkeys(result[4][0] for result in results)
        )
        resolved = bool(addresses)

        if not resolved:
            failure_type = "dns_error"
            error = "No addresses returned"

    except socket.gaierror as exc:
        failure_type = "dns_error"
        error = str(exc)

    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "host": host,
        "resolved": resolved,
        "addresses": addresses,
        "latency_ms": round(elapsed_ms, 3),
        "error": error,
        "failure_type": failure_type,
    }
