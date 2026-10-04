#!/bin/sh
set -eu

if [ "$(id -u)" != 0 ]; then
    echo "Run with sudo from the deployed infrastructure directory." >&2
    exit 1
fi
runtime_dir=$(pwd -P)
test -f docker-compose.https.yml
docker compose -f docker-compose.yml -f docker-compose.https.yml exec -T nginx nginx -t

install -m 755 scripts/renew-certificate.sh /usr/local/sbin/mxchip-renew-certificate
install -m 644 systemd/mxchip-cert-renew.service /etc/systemd/system/
install -m 644 systemd/mxchip-cert-renew.timer /etc/systemd/system/
mkdir -p /etc/systemd/system/mxchip-cert-renew.service.d
printf '[Service]\nWorkingDirectory=%s\n' "$runtime_dir" \
    > /etc/systemd/system/mxchip-cert-renew.service.d/runtime.conf
systemctl daemon-reload
systemctl enable --now mxchip-cert-renew.timer
systemctl start mxchip-cert-renew.service
systemctl list-timers mxchip-cert-renew.timer --no-pager
