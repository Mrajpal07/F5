import argparse
import json
import time
import socket
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import urlopen




def probe_once(url, timeout):
    """Send one HTTP request and classify its outcome."""
    start = time.perf_counter()

    status = None
    error = None
    failure_type = None

    try:
        with urlopen(url, timeout=timeout) as response:
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



def analyse_results(observations):
    """Calculate summary statistics from individual request results."""
    if not observations:
        raise ValueError("At least one observation is required.")

    latencies = [item["latency_ms"] for item in observations]
    successful = sum(
        item["status"] is not None and 200 <= item["status"] < 300
        for item in observations
    )

    return {
        "total_requests": len(observations),
        "successful_requests": successful,
        "failed_requests": len(observations) - successful,
        "success_rate_pct": round(successful / len(observations) * 100, 2),
        "latency_ms": {
            "min": round(min(latencies), 3),
            "mean": round(sum(latencies) / len(latencies), 3),
            "max": round(max(latencies), 3),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Measure HTTP endpoint health and latency."
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000/health",
        help="HTTP endpoint to probe",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of requests to send",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Timeout per request in seconds",
    )
    args = parser.parse_args()

    if args.count < 1 or args.timeout <= 0:
        parser.error("--count must be at least 1 and --timeout must be positive")

    observations = []

    for number in range(1, args.count + 1):
        result = probe_once(args.url, args.timeout)
        observations.append(result)

        status = result["status"]
        status_text = str(status) if status is not None else "NO RESPONSE"

        print(
            f"Request {number}/{args.count}: "
            f"status={status_text}, "
            f"latency={result['latency_ms']:.3f} ms"
        )

        if result["error"]:
            print(f"  Error: {result['error']}")

    summary = analyse_results(observations)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target": args.url,
        "summary": summary,
        "observations": observations,
    }

    print("\n=== Diagnostic Summary ===")
    print(f"Target: {args.url}")
    print(f"Success rate: {summary['success_rate_pct']:.2f}%")
    print(f"Successful requests: {summary['successful_requests']}")
    print(f"Failed requests: {summary['failed_requests']}")
    print(f"Minimum latency: {summary['latency_ms']['min']:.3f} ms")
    print(f"Mean latency: {summary['latency_ms']['mean']:.3f} ms")
    print(f"Maximum latency: {summary['latency_ms']['max']:.3f} ms")

    print("\n=== JSON Report ===")
    print(json.dumps(report, indent=2))

    if summary["failed_requests"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
