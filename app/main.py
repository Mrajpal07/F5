
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.diagnostics.engine import diagnose_probe_result

app = FastAPI(
    title="NetReliant",
    description="Network reliability and diagnostics lab",
    version="0.2.0",
)


class ProbeObservation(BaseModel):
    status: int | None = None
    latency_ms: float = Field(ge=0)
    error: str | None = None
    failure_type: str | None = None


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
    """Analyse a probe observation and return a structured finding."""
    result = diagnose_probe_result(observation.model_dump())
    return {
        "target_observation": observation.model_dump(),
        "diagnostic": result,
    }
