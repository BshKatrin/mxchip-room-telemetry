# Infrastructure

Remote EC2 runtime: FastAPI, InfluxDB, Grafana, Nginx, and an on-demand Certbot
container. Backend source is not required on the running instance.

## Public routes and firewall

- FastAPI: `http://<public-ip>/` or `https://<public-ip>/`
- Device ingestion: `http://<public-ip>/api/v1/telemetry` (no redirect)
- Dashboard: `https://<public-ip>/grafana/` (Grafana login required)
- HTTP dashboard requests redirect to HTTPS after TLS is enabled.

Allow inbound TCP 80 and 443 from clients; use `0.0.0.0/0` for access from
anywhere. Restrict SSH port 22 to your public IP. Do not expose ports 3000,
8080, or 8086. Allow outbound TCP 443 continuously for certificate issuance and
renewal, plus HTTP/HTTPS for package/image downloads. A temporary SSH download
proxy cannot provide unattended renewal.

For an IPv4 dashboard URL, the HTTPS source must include `0.0.0.0/0`.
An IPv6-only `::/0` rule does not allow access to an IPv4 address. Check the
security group attached to the instance, rather than an unrelated group.

InfluxDB binds to host loopback only. For administrative access:

```bash
ssh -N -L 8086:127.0.0.1:8086 ec2-aws
```

## Telemetry history in Grafana

The dashboard opens with the last 24 hours and all panels query the time range
selected in Grafana. Choose a longer or absolute range to view older readings.
`room_telemetry` retains original readings for 30 days. Older history uses UTC
daily means from `room_telemetry_daily`, retained for 1825 days. Daily minimum,
maximum, and per-field sample counts are stored alongside those means.
See [InfluxDB retention and provisioning](influxdb/README.md) for the schema,
late-data handling, and verification commands.

## Build and transfer

Build the API image from the repository root and push or copy it to EC2:

```bash
docker build -t mxchip-room-telemetry-api:latest backend
```

Copy the `infra/` runtime directory to EC2, excluding private `.env` unless
transferring it securely. On macOS, disable AppleDouble metadata in tar transfers
with `COPYFILE_DISABLE=1`; `._*.yml` files break Grafana provisioning.
The deployment directory used here is `/home/ubuntu/mxchip-room-telemetry`.

## First deployment and certificate issuance

Use Docker Compose >= 2.24.4 (`!override` support). All commands below run on EC2,
from the deployed runtime directory. Set `PUBLIC_HOST` to its public IPv4 address,
`BACKEND_IMAGE` to the available image, and real passwords/token in private `.env`:

```bash
cp .env.example .env
chmod 600 .env
# Edit .env before starting the stack.
sudo docker compose up -d
sudo docker compose --profile tls pull certbot
```

The base stack provides HTTP ingestion, the ACME HTTP-01 webroot on port 80,
and a loopback dashboard for bootstrap. Request the production IP certificate:

```bash
sudo docker compose run --rm -T --entrypoint /bin/sh certbot -c '
  exec certbot certonly --non-interactive --agree-tos \
    --register-unsafely-without-email \
    --preferred-profile shortlived \
    --webroot --webroot-path /var/www/certbot \
    --ip-address "$PUBLIC_HOST" --cert-name mxchip-dashboard
'
```

Certbot is pinned to v5.8.0, which supports IP webroot validation. The certificate
and ACME account are persisted in the `letsencrypt` Docker volume; challenges use
`certbot-webroot`. No contact email is registered by this command. An optional
email can instead be supplied with `--email you@example.com`.

Enable TLS only after issuance succeeds, so Nginx never starts with missing keys:

```bash
sudo docker compose -f docker-compose.yml -f docker-compose.https.yml up -d
sudo docker compose -f docker-compose.yml -f docker-compose.https.yml exec -T nginx nginx -t
sudo sh scripts/configure-retention.sh
curl --fail "https://<public-ip>/grafana/api/health"
```

Use both Compose files for subsequent `up`, `exec`, and configuration changes.
For an existing deployment, copy the updated `influxdb/`, retention script, and
Grafana provisioning, then run `sudo sh scripts/configure-retention.sh` before
installing the updated dashboard. This backfills and verifies summaries before
changing the existing raw bucket to 30-day retention; changing Compose's init
retention alone does not update an existing bucket.
Plain `docker compose up` returns the dashboard to the HTTP bootstrap setup.
After TLS activation the loopback dashboard port is removed; normal browser
access uses the public HTTPS URL. The admin password is `GRAFANA_ADMIN_PASSWORD`
from private `.env`; changing that variable alone does not reset an existing
Grafana account password in its persistent volume.

## Automatic renewal

Let's Encrypt IP certificates last approximately six days. Install the remote
systemd timer and verify a staging renewal before declaring setup complete:

```bash
sudo sh scripts/install-renewal-timer.sh
sudo /usr/local/sbin/mxchip-renew-certificate --dry-run --no-random-sleep-on-renew
sudo systemctl is-enabled mxchip-cert-renew.timer
sudo systemctl list-timers mxchip-cert-renew.timer --no-pager
sudo journalctl -u mxchip-cert-renew.service --no-pager -n 30
```

The timer checks at 00:00 and 12:00 in the host timezone, with up to one hour of
random delay. `Persistent=true` catches missed checks after reboot. Certbot renews
only when due. On a successful check the script validates and gracefully reloads
Nginx; failed renewal exits nonzero and appears in the service journal. A dry run
uses staging and does not replace the trusted certificate. Renewal does not stop
HTTP ingestion and needs no local machine or interactive SSH connection.

The installer records the deployment directory as the service working directory;
rerun it if that directory moves. Docker is required and must be enabled at boot.
Keep the certificate volume: never use `docker compose down -v` on this deployment.
If the instance's public IP changes, update `PUBLIC_HOST`, explicitly reissue the
certificate for the new address, update the firmware endpoint, and redeploy TLS.

This timer renews certificates. Container versions remain pinned and are upgraded
deliberately rather than automatically replacing the production stack.

References: [Let's Encrypt IP certificates with Certbot](https://letsencrypt.org/2026/03/11/shorter-certs-certbot)
and [Certbot renewal](https://eff-certbot.readthedocs.io/en/stable/using.html#renewing-certificates).
