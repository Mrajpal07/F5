
from fastapi import FastAPI
from datetime import datetime, timezone

app = FastAPI(
    title="NetReliant",
    description="Network reliability and diagnostics lab",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "service": "NetReliant",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }
