#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
# Use the running image's standard-library Python and existing container secrets.
# Both Compose files are needed for administration of the HTTPS deployment.
docker compose -f docker-compose.yml -f docker-compose.https.yml \
    exec -T api python - "$@" < influxdb/configure-retention.py
