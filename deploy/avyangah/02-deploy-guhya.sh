#!/usr/bin/env bash
# =============================================================
# 02-deploy-guhya.sh — deploy/update guhya-pos on the shared careai box.
# Run on the server as:   bash 02-deploy-guhya.sh [blue|green]
#
# Safe + additive + idempotent. Re-runnable. Only ever:
#   - adds the guhya_pos database (if missing)
#   - pulls + starts the guhya container
#   - writes site-confs/pos.guhya.co.in.conf and does a GRACEFUL nginx reload
#     ONLY after `nginx -t` passes.
# Never touches careai / docsign / mail.
# =============================================================
set -euo pipefail
CAREAI="/home/deploy/careai"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # this deploy/avyangah dir
COLOUR="${1:-blue}"
CERT="/mnt/nvme_data/ssl/pos.guhya.co.in-fullchain.pem"
DC="docker compose -f docker-compose.yml -f docker-compose.guhya.yml"
cd "$CAREAI"

echo "==> 1/6 place compose overlay"
cp "$SRC/docker-compose.guhya.yml" "$CAREAI/docker-compose.guhya.yml"

echo "==> 2/6 check .env.guhya"
if [ ! -f "$CAREAI/.env.guhya" ]; then
  cp "$SRC/.env.guhya.example" "$CAREAI/.env.guhya"
  echo "    created $CAREAI/.env.guhya — set a real SECRET_KEY, then re-run."
  echo "    generate one with:  python3 -c 'import secrets; print(secrets.token_urlsafe(50))'"
  exit 1
fi
if grep -q 'replace-with' "$CAREAI/.env.guhya"; then
  echo "    .env.guhya still has the placeholder SECRET_KEY — edit it, then re-run."; exit 1
fi

echo "==> 3/6 ensure guhya_pos database exists"
docker exec careai-postgres psql -U careai -tAc \
  "SELECT 1 FROM pg_database WHERE datname='guhya_pos'" | grep -q 1 \
  || docker exec careai-postgres psql -U careai -c "CREATE DATABASE guhya_pos OWNER careai;"

echo "==> 4/6 pull + start guhya-pos-api-$COLOUR (migrate runs on startup)"
if [ "$COLOUR" = green ]; then
  $DC pull guhya-pos-api-green
  $DC --profile guhya-green up -d guhya-pos-api-green
else
  $DC pull guhya-pos-api-blue
  $DC up -d guhya-pos-api-blue
fi

echo "==> 5/6 wait for /ping"
ok=0
for i in $(seq 1 30); do
  if docker exec "guhya-pos-api-$COLOUR" curl -sf http://localhost:8000/ping >/dev/null 2>&1; then
    ok=1; echo "    healthy"; break
  fi
  sleep 2
done
if [ "$ok" != 1 ]; then
  echo "    health check FAILED. Recent logs:"; docker logs "guhya-pos-api-$COLOUR" --tail 40; exit 1
fi

echo "==> 6/6 nginx route"
if [ ! -f "$CERT" ]; then
  echo "    cert not found at $CERT"
  echo "    run:  sudo bash 01-cert-guhya.sh   then re-run this script."
  echo "    (the container is already up and healthy; only the public route is pending)"
  exit 0
fi
# point the conf at the chosen colour, install, validate, graceful reload
sed "s/guhya-pos-api-[a-z]*:8000/guhya-pos-api-$COLOUR:8000/" \
  "$SRC/pos.guhya.co.in.conf" > "$CAREAI/site-confs/pos.guhya.co.in.conf"
docker exec careai-nginx nginx -t        # gate: bad config -> stops here, live nginx untouched
docker exec careai-nginx nginx -s reload # graceful; other sites keep serving

echo
echo "==> ✓ done — guhya-pos is live on $COLOUR."
echo "Test:   curl -s https://pos.guhya.co.in/ping"
echo "Admin:  docker exec -it guhya-pos-api-$COLOUR python manage.py createsuperuser"
