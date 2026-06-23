#!/usr/bin/env bash
# =============================================================
# 01-cert-guhya.sh — issue + install the TLS cert for pos.guhya.co.in.
# Mirrors your avyangah-infra/certbot/01-issue-certs.sh, for this one domain.
# Run on the server as:   sudo bash 01-cert-guhya.sh
#
# Safe: only adds a cert + a port-80 ACME block for pos.guhya.co.in.
# Touches nothing for careai / docsign / mail.
# Pre-req: DNS A record  pos.guhya.co.in -> this server's IP.
# =============================================================
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Run with sudo: sudo bash 01-cert-guhya.sh"; exit 1; }

EMAIL="praveen.moj@gmail.com"          # same address your other certs use
DOMAIN="pos.guhya.co.in"
SSL_DIR="/mnt/nvme_data/ssl"           # bind-mounted into nginx as /etc/nginx/ssl
WEBROOT="/var/www/certbot"
SITES="/home/deploy/careai/site-confs"

# 1) Bootstrap: a port-80-only block so Let's Encrypt can verify the domain.
#    (The full HTTPS block needs the cert, which we don't have yet — chicken/egg.)
if [ ! -f "${SSL_DIR}/${DOMAIN}-fullchain.pem" ]; then
  echo "=== bootstrap port-80 ACME block for ${DOMAIN} ==="
  cat > "${SITES}/pos.guhya.co.in.conf" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};
    location /.well-known/acme-challenge/ { root ${WEBROOT}; allow all; default_type "text/plain"; }
    location / { return 301 https://\$host\$request_uri; }
}
EOF
  sudo -u deploy docker exec careai-nginx nginx -t
  sudo -u deploy docker exec careai-nginx nginx -s reload
fi

# 2) Issue the cert (idempotent: keep-until-expiring skips if still fresh).
echo "=== issuing cert for ${DOMAIN} ==="
certbot certonly --webroot --webroot-path "${WEBROOT}" \
  --email "${EMAIL}" --agree-tos --no-eff-email \
  --keep-until-expiring --non-interactive -d "${DOMAIN}"

# 3) Copy into the dir nginx mounts, with the filename the site-conf expects.
echo "=== copying cert into ${SSL_DIR} ==="
cp -L "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" "${SSL_DIR}/${DOMAIN}-fullchain.pem"
cp -L "/etc/letsencrypt/live/${DOMAIN}/privkey.pem"   "${SSL_DIR}/${DOMAIN}-privkey.pem"
chown deploy:deploy "${SSL_DIR}/${DOMAIN}-"*.pem
chmod 644 "${SSL_DIR}/${DOMAIN}-fullchain.pem"
chmod 600 "${SSL_DIR}/${DOMAIN}-privkey.pem"

echo
echo "=== ✓ cert ready for ${DOMAIN} ==="
echo "Next: bash 02-deploy-guhya.sh"
echo
echo "NOTE: to auto-copy this cert on future renewals, add ${DOMAIN} to your"
echo "      certbot renew-hook the same way careai/signsimple are handled."
