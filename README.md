# NetReliant

**Network Diagnostics and Reliability Monitoring Platform**

NetReliant is a network reliability engineering project designed to investigate service connectivity, classify failures, maintain probe history, and track incidents through a tested API.

The project combines application-level health checks with DNS resolution and TCP connectivity probes to provide evidence that helps distinguish network and service failures.

## Why NetReliant?

A failed HTTP request does not always tell you where a failure occurred. The underlying issue could involve hostname resolution, TCP connectivity, or the application itself.

NetReliant collects multiple observations and uses a diagnostic engine to classify failures. When observations contradict one another, it avoids making an unsupported root-cause claim and instead requests additional evidence.

## Current Features

- **HTTP health probing:** Collects HTTP status, response latency, and failure information.
- **DNS diagnostics:** Resolves hostnames and records returned addresses, resolution latency, and errors.
- **TCP connectivity checks:** Tests whether a connection to a target host and port succeeds.
- **Evidence-based diagnostics:** Classifies observations into categories such as healthy, DNS error, connection error, timeout, HTTP error, and unknown.
- **Conflict detection:** Identifies contradictory probe observations and recommends further investigation.
- **Probe history:** Persists probe observations and associated diagnostic results.
- **Incident management:** Tracks incidents arising from observed service failures.
- **REST API:** Exposes health, probing, diagnostic, and history functionality through FastAPI.
- **Automated tests:** Covers API behaviour, probe logic, diagnostics, history, and incident management.

## Architecture

```text
                 Client
                   |
                   v
              FastAPI API
                   |
          +--------+--------+
          |        |        |
          v        v        v
         HTTP     DNS      TCP
         Probe    Probe    Probe
          |        |        |
          +--------+--------+
                   |
                   v
           Diagnostic Engine
                   |
          +--------+--------+
          |                 |
          v                 v
     Probe History    Incident Manager
          |                 |
          v                 v
       SQLite          Incident Store
```

The diagram illustrates the logical components and their responsibilities.

## Technology Stack

- Python
- FastAPI
- Pydantic
- SQLite
- Pytest
- Docker and Docker Compose

## Getting Started

### Prerequisites

- Python 3.12 or compatible
- Git
- Docker Desktop with Docker Compose, if using the containerized setup

### Clone the repository

```bash
git clone https://github.com/Mrajpal07/F5.git
cd F5
```

### Run with Docker Compose

```bash
docker compose up -d --build api
```

Check the service health:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"healthy"}
```

### Run the tests

If your virtual environment is available:

```bash
.venv/bin/python -m pytest -q
```

## Example API Request

Submit a probe for a permitted local HTTP target:

```bash
curl -X POST http://localhost:8000/diagnostics/probe \
  -H "Content-Type: application/json" \
  -d '{"url":"http://localhost:8000/health","timeout":2}'
```

The response includes the probe record ID, network results, HTTP observation, diagnostic assessment, latency-anomaly information, and any incident event.

## Safety and Scope

The diagnostic probe API currently restricts HTTP targets to `localhost` and `127.0.0.1`. This keeps the current API focused on controlled local testing.

DNS and TCP observations should be interpreted as evidence from individual probes, not definitive proof of a root cause. Results can differ across attempts or points in time.

## Testing

The current test suite has passed **99 tests** in the development environment.

To reproduce the result, run the test command above. Test counts may change as the project evolves.

## Roadmap

Potential future development includes:

- Reliability analytics, including availability and latency percentiles
- Service-level objective (SLO) reporting
- Improved time-correlated diagnostic evidence
- Richer observability and network troubleshooting workflows
- Reproducible network failure scenarios
- Continuous integration and deployment automation

These are planned improvements, not claims about currently implemented functionality.

## Project Goal

NetReliant is being developed as a hands-on network engineering project to deepen understanding of network protocols, systematic troubleshooting, service reliability, and backend engineering.

The goal is to make network failures easier to investigate through measurable evidence, repeatable tests, and clear diagnostic reasoning.