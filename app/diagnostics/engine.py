
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
            "recommended_checks": [
                "Verify that a service is listening on the destination port.",
                "Check destination address and port configuration.",
                "Investigate the network path and any applicable firewall rules.",
            ],
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
            "recommended_checks": [
                "Compare response times across repeated probes.",
                "Check service responsiveness and resource utilization.",
                "Investigate packet loss or delays along the network path.",
            ],
        }

    if failure_type == "http_error" or (
        status is not None and not 200 <= status < 300
    ):
        evidence = [f"HTTP status: {status}."]

        if status is not None and 300 <= status < 400:
            evidence.append(
                "The server returned a redirect response. "
                "The probe did not follow the redirect."
            )
            assessment = (
                "The endpoint redirected the request. Verify whether "
                "the redirect is expected and whether the client should "
                "follow it."
            )
            checks = [
                "Inspect the Location response header.",
                "Verify that the redirect destination is expected.",
            ]

        elif status is not None and status >= 500:
            assessment = (
                "The server returned a 5xx response, indicating a "
                "server-side failure. Inspect server and application logs."
            )
            checks = [
                "Inspect server and application logs.",
                "Check upstream dependencies and service health.",
            ]

        elif status is not None and status >= 400:
            assessment = (
                "The server returned a 4xx response. Check the request, "
                "authentication requirements, and endpoint configuration."
            )
            checks = [
                "Verify the request path and HTTP method.",
                "Check authentication and authorization requirements.",
                "Inspect the response body for additional details.",
            ]

        else:
            assessment = (
                "An HTTP response indicated an unsuccessful request. "
                "Inspect the endpoint configuration and response."
            )
            checks = [
                "Inspect the HTTP status and response headers.",
                "Verify the endpoint configuration.",
            ]

        return {
            "category": "http_error",
            "severity": "medium",
            "evidence": evidence,
            "assessment": assessment,
            "recommended_checks": checks,
        }

    if status is not None and 200 <= status < 300:
        return {
            "category": "healthy",
            "severity": "info",
            "evidence": [f"HTTP status: {status}."],
            "assessment": "The endpoint returned a successful HTTP response.",
            "recommended_checks": [
                "Continue monitoring endpoint availability.",
                "Track latency over time to identify performance degradation.",
            ],
        }

    return {
        "category": "unknown",
        "severity": "medium",
        "evidence": [
            "The observation did not match a known diagnostic rule."
        ],
        "assessment": "Collect additional evidence before drawing a conclusion.",
        "recommended_checks": [
            "Repeat the probe and compare observations.",
            "Collect additional connection and application-level evidence.",
        ],
    }
