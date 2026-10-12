
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.diagnostics.engine import diagnose_probe_result
from app.probes.http_probe import probe_once
from contextlib import asynccontextmanager
from app.analytics.reliability import get_reliability_summary

from app.history.store import (
    initialize_database,
    record_probe,
    get_probe_history,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="NetReliant",
    description="Network reliability and diagnostics lab",
    version="0.3.0",
    lifespan=lifespan,
)


class ProbeObservation(BaseModel):
    status: int | None = None
    latency_ms: float = Field(ge=0)
    error: str | None = None
    failure_type: str | None = None


class ProbeRequest(BaseModel):
    url: str
    timeout: float = Field(default=2.0, gt=0, le=5.0)

    @field_validator("url")
    @classmethod
    def restrict_to_local_targets(cls, value: str) -> str:
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError as exc:
            raise ValueError("Invalid target URL") from exc

        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"localhost", "127.0.0.1"}
            or parsed.username is not None
            or parsed.password is not None
            or not parsed.path
            or port == 0
        ):
            raise ValueError(
                "Only HTTP URLs targeting localhost or 127.0.0.1 are allowed"
            )

        return value


@app.get("/")
def root():
    return {
        "service": "NetReliant",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/diagnostics/analyse")
def analyse(observation: ProbeObservation):
    result = diagnose_probe_result(observation.model_dump())
    return {
        "target_observation": observation.model_dump(),
        "diagnostic": result,
    }


@app.post("/diagnostics/probe")
def probe_and_diagnose(request: ProbeRequest):
    observation = probe_once(request.url, request.timeout)
    diagnostic = diagnose_probe_result(observation)

    record_id = record_probe(
        request.url,
        observation,
        diagnostic,
    )

    return {
        "record_id": record_id,
        "target": request.url,
        "observation": observation,
        "diagnostic": diagnostic,
    }

@app.get("/diagnostics/history")
def probe_history(
    url: str,
    limit: int = 50,
):
    try:
        records = get_probe_history(url, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "target": url,
        "count": len(records),
        "records": records,
    }

@app.get("/diagnostics/reliability")
def reliability_summary(
    url: str,
    window_hours: int = 24,
):
    try:
        summary = get_reliability_summary(
            url,
            window_hours=window_hours,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return summary