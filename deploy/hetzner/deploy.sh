#!/bin/bash
# =============================================================
# guhya-pos blue/green deploy — same pattern as care-ai deploy.sh
# Usage: ./deploy.sh
#   1. ensures infra (postgres/redis/caddy) is up
#   2. reads the live colour from active_guhya_pos.conf
#   3. builds/pulls + starts the OTHER colour
#   4. migrates (shared DB) + collectstatic on the new colour
#   5. health-checks /ping
#   6. flips Caddy to the new colour, reloads, stops the old colour
# =============================================================
set -euo pipefail
cd "$(dirname "$0")"

BASE="-f docker-compose.yml"
APPF="-f docker-compose.guhya-pos.yml"

# optional: pull prebuilt images from ghcr (like care-ai). Skip if building locally.
if [ -n "${GITHUB_TOKEN:-}" ] && [ -n "${GITHUB_USER:-}" ]; then
  echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin
fi

echo "=== guhya-pos deploy $(date '+%F %T') ==="
docker compose $BASE up -d postgres redis caddy

if grep -q "guhya-pos-api-green" active_guhya_pos.conf; then LIVE=green; else LIVE=blue; fi
if [ "$LIVE" = blue ]; then TARGET=green; else TARGET=blue; fi
echo "live=$LIVE  ->  deploying $TARGET"

docker compose $BASE $APPF build "guhya-pos-api-$TARGET" 2>/dev/null \
  || docker compose $BASE $APPF pull "guhya-pos-api-$TARGET" || true
docker compose $BASE $APPF up -d "guhya-pos-api-$TARGET"

docker compose $BASE $APPF exec -T "guhya-pos-api-$TARGET" python manage.py migrate --noinput
docker compose $BASE $APPF exec -T "guhya-pos-api-$TARGET" python manage.py collectstatic --noinput

echo "health checking guhya-pos-api-$TARGET ..."
ok=0
for i in $(seq 1 30); do
  if docker compose $BASE $APPF exec -T "guhya-pos-api-$TARGET" curl -sf http://localhost:8000/ping >/dev/null 2>&1; then
    ok=1; echo "  healthy"; break
  fi
  sleep 2
done
if [ "$ok" != 1 ]; then
  echo "  health check FAILED — keeping $LIVE live"
  docker compose $BASE $APPF logs "guhya-pos-api-$TARGET" --tail=40
  exit 1
fi

sed -i.bak "s/guhya-pos-api-[a-z]*:8000/guhya-pos-api-$TARGET:8000/g" active_guhya_pos.conf
rm -f active_guhya_pos.conf.bak
docker compose $BASE exec caddy caddy reload --config /etc/caddy/Caddyfile
echo "  Caddy now points to $TARGET"

docker compose $BASE $APPF stop "guhya-pos-api-$LIVE" || true
echo "=== done: $TARGET is live ==="
docker compose $BASE $APPF ps
