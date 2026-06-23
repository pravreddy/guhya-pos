# Deploy guhya-pos on the shared Hetzner box (the "careai" stack)

guhya-pos runs as another app behind the existing `careai-nginx`, reusing the
shared `careai-postgres`, `careai-redis`, and the `careai-net` network — exactly
like docsign. Every step is additive and gated by `nginx -t`, so it never
touches Care AI, SignSimple, or mail.

## What's here
- `docker-compose.guhya.yml`  — the blue/green container overlay
- `pos.guhya.co.in.conf`      — the nginx route (blue/green switch variable)
- `.env.guhya.example`        — env template (SECRET_KEY etc.)
- `01-cert-guhya.sh`          — issues + installs the TLS cert (run with sudo)
- `02-deploy-guhya.sh`        — DB + image + container + nginx route (run as deploy)

## One-time prerequisites
1. The GitHub Action (`.github/workflows/build.yml`) has pushed
   `ghcr.io/pravreddy/guhya-pos-api:latest`. (Check the Actions tab is green.)
2. DNS: an A record  pos.guhya.co.in -> the server IP.

## Deploy (on the server)

```
# get the repo (or: cd ~/guhya-pos && git pull)
cd ~ && git clone git@github.com:pravreddy/guhya-pos.git
cd ~/guhya-pos/deploy/avyangah

# 1. cert for pos.guhya.co.in (needs sudo; mirrors your 01-issue-certs.sh)
sudo bash 01-cert-guhya.sh

# 2. deploy: creates guhya_pos DB, pulls image, starts container,
#    installs the nginx route, validates, reloads.
bash 02-deploy-guhya.sh
#    -> first run will create .env.guhya and stop; set a real SECRET_KEY:
#       nano ~/careai/.env.guhya     # SECRET_KEY=...  (generate one below)
#       python3 -c "import secrets; print(secrets.token_urlsafe(50))"
#    then run  bash 02-deploy-guhya.sh  again.

# 3. admin login
docker exec -it guhya-pos-api-blue python manage.py createsuperuser
```

Test: `curl -s https://pos.guhya.co.in/ping` -> `{"status":"ok"}`, then
`/admin/` and `/api/` in a browser.

## Updating later (new code)
Push to main -> the Action builds a fresh image -> on the server just:
```
cd ~/guhya-pos && git pull && cd deploy/avyangah && bash 02-deploy-guhya.sh
```

## Blue/green (zero-downtime)
`bash 02-deploy-guhya.sh green` brings up the green container, repoints the
nginx route to it, validates and reloads. Then stop the old colour:
`docker compose -f ~/careai/docker-compose.yml -f ~/careai/docker-compose.guhya.yml stop guhya-pos-api-blue`

## Safety / rollback
- Bad nginx conf -> `nginx -t` fails -> the script stops BEFORE reload, so the
  running nginx keeps serving every site untouched.
- Bad app build -> only the guhya container is affected; stop it and the other
  apps are unaffected.
