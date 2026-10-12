
def diagnose_probe_result(result):
    """Convert one probe observation into an evidence-based finding."""
    status = result.get("status")
    failure_type = result.get("failure_type")

    if failure_type == "connection_error":
        return {
            "category": "connection_error",
            "severity": "high",
            "evidence": [
                "No HTTP response was received.",
                result.get("error") or "Connection attempt failed.",
            ],
            "assessment": (
                "The client could not establish a usable connection "
                "to the requested endpoint."
            ),
        }

    if failure_type == "timeout":
        return {
            "category": "timeout",
            "severity": "high",
            "evidence": [
                "The request exceeded its configured timeout.",
                f"Observed latency: {result.get('latency_ms')} ms.",
            ],
            "assessment": (
                "The endpoint did not respond within the configured "
                "time limit. Further checks are needed to locate the cause."
            ),
        }

    if failure_type == "http_error" or (
        status is not None and not 200 <= status < 300
    ):
        return {
            "category": "http_error",
            "severity": "medium",
            "evidence": [f"HTTP status: {status}."],
            "assessment": (
                "An HTTP response indicated an unsuccessful request. "
                "Inspect the server and application logs."
            ),
        }

    if status is not None and 200 <= status < 300:
        return {
            "category": "healthy",
            "severity": "info",
            "evidence": [f"HTTP status: {status}."],
            "assessment": "The endpoint returned a successful HTTP response.",
        }

    return {
        "category": "unknown",
        "severity": "medium",
        "evidence": ["The observation did not match a known diagnostic rule."],
        "assessment": "Collect additional evidence before drawing a conclusion.",
    }
