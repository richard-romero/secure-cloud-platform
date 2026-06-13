#!/usr/bin/env bash
set -eo pipefail

IMAGE=$1
CONTAINER_NAME=$2
HOST_PORT=80
CONTAINER_PORT=8000
STAGING_PORT=8080
STAGING_NAME="${CONTAINER_NAME}-new"

RETRIES=15
DELAY=2

if [ -z "$IMAGE" ] || [ -z "$CONTAINER_NAME" ]; then
    echo "Usage: $0 <image> <container_name>"
    exit 1
fi

log() {
    echo "[DEPLOY] $1"
}

wait_for_health() {
    local health_url=$1
    local container_for_logs=$2

    for i in $(seq 1 $RETRIES); do
        if curl -s -f "$health_url" > /dev/null; then
            log "Health check passed for ${health_url}"
            return 0
        fi
        log "Health check failed ($i/$RETRIES) for ${health_url}. Retrying in ${DELAY}s..."
        sleep $DELAY
    done

    log "ERROR: Health check failed after $RETRIES attempts for ${health_url}. Dumping container logs:"
    sudo docker logs --tail 50 "$container_for_logs"
    return 1
}

remove_container() {
    local name=$1
    sudo docker stop "$name" >/dev/null 2>&1 || true
    sudo docker rm "$name" >/dev/null 2>&1 || true
}

container_exists() {
    sudo docker inspect "$1" >/dev/null 2>&1
}

run_container() {
    local name=$1
    local host_port=$2

    local image_tag="${IMAGE##*:}"
    local deployed_at
    deployed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    log "Starting container ${name} on port ${host_port} (image tag: ${image_tag})..."
    sudo docker run -d \
        --name "$name" \
        -p "${host_port}:${CONTAINER_PORT}" \
        -e "APP_IMAGE_VERSION=${image_tag}" \
        -e "APP_DEPLOYED_AT=${deployed_at}" \
        --restart unless-stopped \
        "$IMAGE"
}

if ! sudo systemctl list-unit-files | grep -q '^docker\.service'; then
    log "Docker service not found. Installing Docker..."
    sudo dnf install -y docker
fi

sudo systemctl enable --now docker

if ! command -v curl >/dev/null; then
    log "ERROR: curl is required for health checks but is not installed."
    exit 1
fi

log "Pulling image: $IMAGE"
sudo docker pull "$IMAGE"

remove_container "$STAGING_NAME"

if container_exists "$CONTAINER_NAME"; then
    log "Existing container detected. Starting rolling update..."

    run_container "$STAGING_NAME" "$STAGING_PORT"

    if ! wait_for_health "http://localhost:${STAGING_PORT}/health" "$STAGING_NAME"; then
        log "Rolling update aborted. Removing staging container and leaving production untouched."
        remove_container "$STAGING_NAME"
        exit 1
    fi

    log "Staging container healthy. Swapping to production..."
    remove_container "$CONTAINER_NAME"
    run_container "$CONTAINER_NAME" "$HOST_PORT"
    remove_container "$STAGING_NAME"

    if ! wait_for_health "http://localhost:${HOST_PORT}/health" "$CONTAINER_NAME"; then
        exit 1
    fi

    log "Rolling update complete."
    exit 0
fi

log "No existing container found. Performing first deploy..."
run_container "$CONTAINER_NAME" "$HOST_PORT"

if ! wait_for_health "http://localhost:${HOST_PORT}/health" "$CONTAINER_NAME"; then
    exit 1
fi

log "First deploy complete."
exit 0
