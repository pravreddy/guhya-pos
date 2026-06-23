#!/bin/bash
# Provision a fresh Ubuntu host for guhya-pos (run once, as root).
set -euo pipefail
apt-get update && apt-get upgrade -y
curl -fsSL https://get.docker.com | sh
apt-get install -y ufw
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
echo "Docker + firewall ready."
echo "Next: copy deploy/hetzner to the server, fill .env, run ./deploy.sh"
