from fastapi import FastAPI 
from datetime import datetime, timezone
import socket
import time
import os

app = FastAPI()

START_TIME = time.time()

VERSION = os.getenv("APP_VERSION", "dev")
BUILD_TIMESTAMP = os.getenv("APP_BUILD_TIMESTAMP")
if not BUILD_TIMESTAMP:
    BUILD_TIMESTAMP = datetime.now(timezone.utc).isoformat()

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
    return {
        "version": VERSION,
        "build_timestamp": BUILD_TIMESTAMP
    }

@app.get("/metrics")
def metrics():
    uptime = int(time.time() - START_TIME)

    return {
        "uptime_seconds": uptime,
        "hostname": socket.gethostname()
    }