from fastapi import FastAPI 
from datetime import datetime, timezone
import socket
import time
import os

app = FastAPI()

START_TIME = time.time()

def _short_commit(sha: str) -> str:
    if len(sha) > 7:
        return sha[:7]
    return sha


def _default_deployed_at() -> str:
    deployed_at = os.getenv("APP_DEPLOYED_AT")
    if deployed_at:
        return deployed_at

    build_timestamp = os.getenv("APP_BUILD_TIMESTAMP")
    if build_timestamp:
        return build_timestamp

    return datetime.now(timezone.utc).isoformat()

@app.get("/")
def root():
    return {
        "service": "cloud-status-api",
        "status": "running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }

@app.get("/version")
def version():
    build_sha = os.getenv("APP_BUILD_SHA", "unknown")
    return {
        "version": os.getenv("APP_IMAGE_VERSION", "dev"),
        "commit": _short_commit(build_sha),
        "deployed_at": _default_deployed_at(),
    }

@app.get("/metrics")
def metrics():
    uptime = int(time.time() - START_TIME)

    return {
        "uptime_seconds": uptime,
        "hostname": socket.gethostname()
    }