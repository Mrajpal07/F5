
import math
import socket
import time


def tcp_probe(host, port, timeout=2.0):
    """Test whether a TCP connection can be established."""
    if not isinstance(host, str) or not host.strip():
        raise ValueError("host must be a non-empty string")

    if isinstance(port, bool) or not isinstance(port, int):
        raise ValueError("port must be an integer")

    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be a positive finite number")

    host = host.strip()
    start = time.perf_counter()
    connected = False
    error = None
    failure_type = None

    try:
        with socket.create_connection((host, port), timeout=timeout):
            connected = True

    except (TimeoutError, socket.timeout) as exc:
        failure_type = "timeout"
        error = str(exc)

    except socket.gaierror as exc:
        failure_type = "dns_error"
        error = str(exc)

    except OSError as exc:
        failure_type = "connection_error"
        error = str(exc)

    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "host": host,
        "port": port,
        "connected": connected,
        "latency_ms": round(elapsed_ms, 3),
        "error": error,
        "failure_type": failure_type,
    }
