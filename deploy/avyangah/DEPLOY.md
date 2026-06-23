# Deploy guhya-pos on the shared Hetzner box (the "careai" stack)

guhya-pos runs as another app behind the existing `careai-nginx`, reusing the
shared `careai-postgres`, `careai-redis`, and the `careai-net` network — exactly
like docsign. Nothing here touches Care AI, SignSimple, or mail; every step is
additive and gated by `nginx -t`.

Files in this folder:
- `docker-compose.guhya.yml` -> goes to `~/careai/docker-compose.guhya.yml`
- `pos.guhya.co.in.conf`     -> goes to `~/careai/site-confs/pos.guhya.co.in.conf`
- `.env.guhya.example`       -> copy to `~/careai/.env.guhya` and fill in

## One-time: image

The GitHub Actions workflow (`.github/workflows/build.yml`) builds and pushes
`ghcr.io/pravreddy/guhya-pos-api:latest` on every push to main. Make sure that
workflow has run green once before deploying, so the image exists to pull.

## Go-live (run on the server, in ~/careai)

1) DNS: add an A record  pos.guhya.co.in -> <server IP>.

2) Put the two files in place (clone guhya-pos on the server, or scp them):
     cp <guhya-pos>/deploy/avyangah/docker-compose.guhya.yml  ~/careai/
     cp <guhya-pos>/deploy/avyangah/pos.guhya.co.in.conf      ~/careai/site-confs/   # don't reload yet
     cp <guhya-pos>/deploy/avyangah/.env.guhya.example        ~/careai/.env.guhya
     # edit ~/careai/.env.guhya: set a real SECRET_KEY

3) Create the database in the shared Postgres:
     docker exec careai-postgres psql -U careai -c "CREATE DATABASE guhya_pos OWNER careai;"

4) Provision the TLS cert for pos.guhya.co.in with the SAME tool you used for
   guhya.co.in. The nginx block expects the files at:
     /mnt/nvme_data/ssl/pos.guhya.co.in-fullchain.pem
     /mnt/nvme_data/ssl/pos.guhya.co.in-privkey.pem

5) Pull + start the API (migrate runs automatically against guhya_pos):
     docker login ghcr.io -u pravreddy           # if not already logged in
     docker compose -f docker-compose.yml -f docker-compose.guhya.yml pull guhya-pos-api-blue
     docker compose -f docker-compose.yml -f docker-compose.guhya.yml up -d guhya-pos-api-blue
     docker compose -f docker-compose.yml -f docker-compose.guhya.yml logs -f guhya-pos-api-blue   # watch migrate

6) Test the route + reload nginx (the conf was already copied in step 2):
     docker exec careai-nginx nginx -t            # MUST say "test is successful"
     docker exec careai-nginx nginx -s reload     # graceful; other sites unaffected

7) Admin user:
     docker exec -it guhya-pos-api-blue python manage.py createsuperuser

Then: https://pos.guhya.co.in/ping -> {"status":"ok"}, /admin/, /api/.

## Blue/green (later, for zero-downtime updates)

- start green:   docker compose -f docker-compose.yml -f docker-compose.guhya.yml --profile guhya-green up -d guhya-pos-api-green
- flip the conf: edit ~/careai/site-confs/pos.guhya.co.in.conf, change
                 `set $guhya_backend "guhya-pos-api-blue:8000";` to green, then
                 docker exec careai-nginx nginx -t && docker exec careai-nginx nginx -s reload
- stop blue:     docker compose ... stop guhya-pos-api-blue
(A small deploy-guhya.sh can automate this later, mirroring deploy-docsign.sh.)

## Rollback / safety
- Bad nginx conf? `nginx -t` fails -> DON'T reload; fix or `rm` the file. The
  running nginx keeps serving until a successful reload, so other sites are safe.
- Bad app? `docker compose ... stop guhya-pos-api-blue` — only guhya is affected.
