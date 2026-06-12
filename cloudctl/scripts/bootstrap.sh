#!/usr/bin/env bash
set -e

log() {
    echo "[BOOTSTRAP] $1"
}

log "Ensuring Docker installed and running..."

if ! command -v curl >/dev/null; then
    log "Installing curl..."
    sudo dnf install -y curl
fi

if ! sudo systemctl list-unit-files | grep -q '^docker\.service'; then
    log "Docker service not found. Installing Docker..."
    sudo dnf install -y docker
fi

sudo systemctl enable --now docker

log "Configuring firewall..."

if command -v ufw >/dev/null; then
    sudo ufw allow 22
    sudo ufw allow 80
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw --force enable
fi

log "Bootstrap complete."
