
def diagnose_probe_result(result, network_results=None):
    """Convert probe observations into an evidence-based finding."""
    status = result.get("status")
    failure_type = result.get("failure_type")

    network_results = network_results or {}
    dns_result = network_results.get("dns")
    tcp_result = network_results.get("tcp")
        # Detect contradictory network and HTTP observations.
    dns_conflict = (
        dns_result is not None
        and dns_result.get("resolved") is False
        and tcp_result is not None
        and tcp_result.get("connected") is True
        and status is not None
        and 200 <= status < 300
    )

    tcp_http_conflict = (
        tcp_result is not None
        and tcp_result.get("connected") is False
        and status is not None
        and 200 <= status < 300
    )

    if dns_conflict or tcp_http_conflict:
        if dns_conflict:
            evidence = [
                f"DNS resolution failed for {dns_result.get('host')}.",
                (
                    f"TCP connection to {tcp_result.get('host')}:"
                    f"{tcp_result.get('port')} succeeded."
                ),
                f"HTTP status: {status} indicates success.",
                "DNS, TCP, and HTTP observations conflict.",
            ]
        else:
            evidence = [
                f"HTTP status: {status} indicates success.",
                (
                    f"TCP probe to {tcp_result.get('host')}:"
                    f"{tcp_result.get('port')} reported failure."
                ),
                "TCP and HTTP observations conflict.",
            ]

        return {
            "category": "unknown",
            "severity": "medium",
            "evidence": evidence,
            "assessment": (
                "The probe observations conflict. They may reflect "
                "different times or connection attempts, so the root "
                "cause cannot be determined from this evidence alone."
            ),
            "recommended_checks": [
                "Repeat the DNS, TCP, and HTTP probes.",
                "Compare probe timestamps and individual results.",
                "Verify that the probes used the same target.",
            ],
        }
           # DNS diagnostics
    if dns_result is not None and not dns_result.get("resolved", False):
        return {
            "category": "dns_error",
            "severity": "high",
            "evidence": [
                f"Hostname: {dns_result.get('host')}.",
                dns_result.get("error") or "Hostname resolution failed.",
            ],
            "assessment": (
                "The hostname could not be resolved. The available "
                "evidence does not establish whether TCP or HTTP "
                "connectivity would otherwise work."
            ),
            "recommended_checks": [
                "Verify the hostname spelling and domain configuration.",
                "Inspect the configured DNS resolver.",
                "Check DNS records and resolver reachability.",
            ],
        }

    # Detect contradictory network and HTTP observations.
    dns_conflict = (
        dns_result is not None
        and dns_result.get("resolved") is False
        and tcp_result is not None
        and tcp_result.get("connected") is True
        and status is not None
        and 200 <= status < 300
    )

    tcp_http_conflict = (
        tcp_result is not None
        and tcp_result.get("connected") is False
        and status is not None
        and 200 <= status < 300
    )

    if dns_conflict or tcp_http_conflict:
        evidence = []

        if dns_conflict:
            evidence.append(
                f"DNS resolution failed for {dns_result.get('host')}."
            )
            evidence.append(
                (
                    f"TCP connection to {tcp_result.get('host')}:"
                    f"{tcp_result.get('port')} succeeded."
                )
            )
            evidence.append(
                "DNS, TCP, and HTTP observations conflict."
            )
        else:
            evidence.append(f"HTTP status: {status} indicates success.")
            evidence.append(
                (
                    f"TCP probe to {tcp_result.get('host')}:"
                    f"{tcp_result.get('port')} reported failure."
                )
            )
            evidence.append("TCP and HTTP observations conflict.")

        return {
            "category": "unknown",
            "severity": "medium",
            "evidence": evidence,
            "assessment": (
                "The probe observations conflict. They may reflect "
                "different times or connection attempts, so the root "
                "cause cannot be determined from this evidence alone."
            ),
            "recommended_checks": [
                "Repeat the DNS, TCP, and HTTP probes.",
                "Compare probe timestamps and individual results.",
                "Verify that the probes used the same target.",
            ],
        }
    dns_result = network_results.get("dns")
    tcp_result = network_results.get("tcp")


    # Detect contradictory DNS, TCP, and HTTP observations.
    dns_conflict = (
        dns_result is not None
        and dns_result.get("resolved") is False
        and tcp_result is not None
        and tcp_result.get("connected") is True
        and status is not None
        and 200 <= status < 300
    )

    tcp_http_conflict = (
        tcp_result is not None
        and tcp_result.get("connected") is False
        and status is not None
        and 200 <= status < 300
    )

    if dns_conflict or tcp_http_conflict:
        if dns_conflict:
            evidence = [
                f"DNS resolution failed for {dns_result.get('host')}.",
                (
                    f"TCP connection to {tcp_result.get('host')}:"
                    f"{tcp_result.get('port')} succeeded."
                ),
                f"HTTP status: {status} indicates success.",
                "DNS, TCP, and HTTP observations conflict.",
            ]
        else:
            evidence = [
                f"HTTP status: {status} indicates success.",
                (
                    f"TCP probe to {tcp_result.get('host')}:"
                    f"{tcp_result.get('port')} reported failure."
                ),
                "TCP and HTTP observations conflict.",
            ]

        return {
            "category": "unknown",
            "severity": "medium",
            "evidence": evidence,
            "assessment": (
                "The probe observations conflict. They may reflect "
                "different times or connection attempts, so the root "
                "cause cannot be determined from this evidence alone."
            ),
            "recommended_checks": [
                "Repeat the DNS, TCP, and HTTP probes.",
                "Compare probe timestamps and individual results.",
                "Verify that the probes used the same target.",
            ],
        }

    # DNS diagnostics
    if dns_result is not None and not dns_result.get("resolved", False):
        return {
            "category": "dns_error",
            "severity": "high",
            "evidence": [
                f"Hostname: {dns_result.get('host')}.",
                dns_result.get("error") or "Hostname resolution failed.",
            ],
            "assessment": (
                "The hostname could not be resolved. The available "
                "evidence does not establish whether TCP or HTTP "
                "connectivity would otherwise work."
            ),
            "recommended_checks": [
                "Verify the hostname spelling and domain configuration.",
                "Inspect the configured DNS resolver.",
                "Check DNS records and resolver reachability.",
            ],
        }



    # TCP diagnostics
    if tcp_result and not tcp_result.get("connected", False):
        tcp_failure = tcp_result.get("failure_type")

        if tcp_failure == "timeout":
            category = "timeout"
            assessment = (
                "The TCP connection attempt timed out. The destination "
                "may be unreachable, filtering traffic, or responding slowly."
            )
            checks = [
                "Verify destination reachability and routing.",
                "Inspect firewall rules and possible packet loss.",
                "Repeat the probe and compare connection latency.",
            ]
        else:
            category = "connection_error"
            assessment = (
                "The TCP connection could not be established. "
                "The destination port may be closed or the connection "
                "may have been actively rejected."
            )
            checks = [
                "Verify the destination address and port.",
                "Check whether a service is listening on the port.",
                "Inspect firewall rules and network path behavior.",
            ]

        return {
            "category": category,
            "severity": "high",
            "evidence": [
                f"TCP destination: {tcp_result.get('host')}:"
                f"{tcp_result.get('port')}.",
                f"TCP failure type: {tcp_failure}.",
                tcp_result.get("error") or "TCP connection failed.",
            ],
            "assessment": assessment,
            "recommended_checks": checks,
        }

    # Existing HTTP connection diagnostics
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

    # Existing HTTP status diagnostics
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
