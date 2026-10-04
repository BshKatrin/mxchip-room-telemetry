#!/bin/sh
set -eu

# systemd sets WorkingDirectory to the deployed infrastructure directory.
exec 9>/run/mxchip-cert-renew.lock
flock -n 9 || exit 0

docker compose -f docker-compose.yml -f docker-compose.https.yml \
    run --rm -T certbot renew --quiet "$@"
# A successful no-op renewal is harmless: also recheck and reload Nginx.
docker compose -f docker-compose.yml -f docker-compose.https.yml exec -T nginx nginx -t
docker compose -f docker-compose.yml -f docker-compose.https.yml exec -T nginx nginx -s reload
