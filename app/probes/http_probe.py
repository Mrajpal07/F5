
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler,
    HTTPHandler,
    HTTPSHandler,
    ProxyHandler,
    build_opener,
)

class NoRedirectHandler(HTTPRedirectHandler):
    """Prevent probes from automatically following HTTP redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(
            req.full_url,
            code,
            "Redirect blocked",
            headers,
            fp,
        )


def probe_once(url, timeout):
    """Send one HTTP request without following redirects."""
    start = time.perf_counter()
    status = None
    error = None
    failure_type = None

    opener = build_opener(NoRedirectHandler)

    try:
        with opener.open(url, timeout=timeout) as response:
            status = response.status

        if 200 <= status < 300:
            failure_type = None
        else:
            failure_type = "http_error"

    except HTTPError as exc:
        status = exc.code
        error = str(exc)
        failure_type = "http_error"

    except (URLError, TimeoutError, socket.timeout, OSError) as exc:
        reason = exc.reason if isinstance(exc, URLError) else exc

        if isinstance(reason, (TimeoutError, socket.timeout)):
            failure_type = "timeout"
        else:
            failure_type = "connection_error"

        error = str(exc)

    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "status": status,
        "latency_ms": round(elapsed_ms, 3),
        "error": error,
        "failure_type": failure_type,
    }
