# guhya-pos — Hetzner deploy (blue/green via Caddy)

Same pattern as care-ai: Caddy auto-HTTPS, two API colours (blue/green),
and a deploy.sh that flips between them after a /ping health check.

## First time
1. Point your domain's A record at the server IP.
2. On a fresh Ubuntu host (as root):  bash server-setup.sh
3. Copy this `hetzner/` folder to the server (e.g. /opt/guhya-pos).
4. cp .env.template .env   and fill it in (domain, SECRET_KEY, DB password).
5. ./deploy.sh

## Every release
./deploy.sh
  builds the idle colour, migrates, health-checks /ping, flips Caddy,
  stops the old colour. Near-zero downtime.

## Database migrations (important)
Blue and green share ONE Postgres. Keep migrations backward-compatible
(expand/contract): add new columns/tables first and deploy; remove old ones
only in a later release — so the still-running old colour keeps working during
cutover. For a risky migration, take a short maintenance window instead.
