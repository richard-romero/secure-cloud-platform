#!/usr/bin/env bash
set -eo pipefail

IMAGE=$1
CONTAINER_NAME=$2
HOST_PORT=80
CONTAINER_PORT=8000

if [ -z "$IMAGE" ] || [ -z "$CONTAINER_NAME" ]; then
    echo "Usage: $0 <image> <container_name>"
    exit 1
fi

log() {
    echo "[DEPLOY] $1"
}

if ! sudo systemctl list-unit-files | grep -q '^docker\.service'; then
    log "Docker service not found. Installing Docker..."
    sudo dnf install -y docker
fi

sudo systemctl enable --now docker

log "Pulling image: $IMAGE"
sudo docker pull "$IMAGE"

log "Stopping old container..."
sudo docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true

log "Removing old container..."
sudo docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true

log "Running new container..."
sudo docker run -d --name "$CONTAINER_NAME" -p "${HOST_PORT}:${CONTAINER_PORT}" --restart unless-stopped "$IMAGE"

log "Waiting for application to become healthy..."

if ! command -v curl >/dev/null; then
    log "ERROR: curl is required for health checks but is not installed."
    exit 1
fi

RETRIES=15
DELAY=2
HEALTH_URL="http://localhost:${HOST_PORT}/health"

for i in $(seq 1 $RETRIES); do
    if curl -s -f "$HEALTH_URL" > /dev/null; then
        log "Health check passed!"
        exit 0
    fi
    log "Health check failed ($i/$RETRIES). Retrying in ${DELAY}s..."
    sleep $DELAY
done

log "ERROR: Health check failed after $RETRIES attempts. Dumping container logs:"
sudo docker logs --tail 50 "$CONTAINER_NAME"
exit 1
