# InfluxDB

InfluxDB state is stored in the `influxdb-data` Docker volume declared by
`infra/docker-compose.yml`.

## Retention and daily summaries

- `room_telemetry`: original readings, retained for 30 days.
- `room_telemetry_daily`: daily mean, minimum, maximum, and count for each
  device and sensor field, retained for 1825 days (five 365-day years).
- Measurement: `room_environment`; tag: `device_id`. Summary field names append
  `_mean`, `_min`, `_max`, or `_count` to the original field name. Count is an
  integer; the other summary values retain the sensor's units.
- Days and summary timestamps use UTC. A point at midnight summarizes the UTC
  day starting at that timestamp. Empty days produce no summaries. Counts are
  per field, so missing optional pressure readings do not affect temperature
  coverage. For longer-period means use `sum(mean * count) / sum(count)`.

From the deployed infrastructure directory on EC2:

```sh
sudo sh scripts/configure-retention.sh
sudo sh scripts/configure-retention.sh --check
```

The administrative command uses the running API image's standard-library Python
and existing InfluxDB credentials, without adding dependencies or changing API
ingestion. The token must have permission to manage buckets and tasks and to
read/write both buckets (the existing setup token does). `INFLUX_BUCKET` selects
the raw bucket; its summary bucket appends `_daily`. The provisioned dashboard
uses the default `room_telemetry` names.

Provisioning creates/updates the summary bucket, backfills completed UTC days in
30-day batches, and independently checks all four statistics against raw values.
It then creates/updates one InfluxDB task, requires a successful test run, and
verifies recent summaries before applying raw retention. Failures before that
last step leave the existing raw retention unchanged. Already expired data cannot
be recovered. Rerunning updates the existing resources rather than duplicating
them and skips partly expired days to preserve their previously stored summaries.

The task runs hourly, ten minutes after the hour, and recomputes the last 29
completed UTC days. Stable device/field/day keys overwrite earlier summaries,
allowing late writes and catching up after downtime within that window. It
does not process today's incomplete day. Tasks, credentials, and buckets persist
in InfluxDB's Docker volume and run entirely on EC2 without a laptop or cron.
Outages beyond the raw retention window can lose unsummarized data; monitor
task failures in the InfluxDB UI or with `influx task runs list --task-id <id>`.
`--check` requires the expected retention, task configuration, active status,
and a successful run among the ten most recent runs.

Grafana joins daily means before the first fully retained UTC day with raw
readings from that boundary onward. The boundary lies between 29 and 30 days
ago, keeping each day at one resolution. Minimum, maximum, and count remain
available in the summary bucket for additional queries. The day at a retention
boundary is deliberately read from summaries even if some raw readings remain.

`DOCKER_INFLUXDB_INIT_RETENTION: 30d` applies only to a newly initialized volume;
existing deployments must run the provisioning command. InfluxDB deletes expired
shard groups asynchronously, so disk usage does not drop exactly at 30 days.
Changing retention affects stored data; back up the volume before migration if
you need to retain the original readings beyond this policy.

## Integration tests

From the repository root, with `INFLUX_URL`, `INFLUX_TOKEN`, and `INFLUX_ORG`
set for a reachable InfluxDB 2.7 instance, run:

```sh
RUN_INFLUX_INTEGRATION=1 uv run --no-project --python 3.13 python infra/tests/test_retention.py
```

Tests create uniquely named disposable buckets and tasks, never use the
production bucket, and delete their test resources on completion.
