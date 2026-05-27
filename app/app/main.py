from fastapi import FastAPI 
from datetime import datetime, timezone
import socket
import time
import os
import subprocess

app = FastAPI()

START_TIME = time.time()

# Read version from git tag, fallback to environment variable or hardcoded value
def get_version():
    try:
        return subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip().lstrip("v")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return os.getenv("APP_VERSION", "1.0.0")

VERSION = get_version()
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