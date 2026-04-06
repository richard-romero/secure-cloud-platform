#!/usr/bin/env bash
set -e

log() {
    echo "[BOOTSTRAP] $1"
}

log "Ensuring Docker running..."
sudo systemctl start docker

log "Configuring firewall..."

if command -v ufw >/dev/null; then
    sudo ufw allow 22
    sudo ufw allow 80
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw --force enable
fi

log "Bootstrap complete."
