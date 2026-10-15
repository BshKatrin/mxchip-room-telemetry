"""Provision InfluxDB rollups using only Python's standard library.

Run through scripts/configure-retention.sh so credentials stay in the API
container. This is an administrative command, not part of HTTP ingestion.
"""

import argparse
import csv
import io
import json
import math
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

RAW_DAYS = 30
DAILY_DAYS = 1825
TASK_NAME = "room-telemetry-daily"
MEASUREMENT = "room_environment"
FIELDS = ("temperature_c", "humidity_percent", "pressure_hpa", "light_lux", "co2_ppm")


def timestamp(value):
    return value.isoformat().replace("+00:00", "Z")


def midnight(value):
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def rollup_flux(raw, daily, org, start, stop):
    """Use stable UTC window starts and distinct fields for integer counts."""
    script = f"""
data = () => from(bucket: {json.dumps(raw)})
    |> range(start: {start}, stop: {stop})
    |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
    |> filter(fn: (r) => contains(value: r._field, set: {json.dumps(FIELDS)}))
"""
    for statistic in ("mean", "min", "max", "count"):
        script += f"""
data()
    |> aggregateWindow(every: 1d, fn: {statistic}, createEmpty: false, timeSrc: "_start")
    |> map(fn: (r) => ({{r with _field: r._field + "_{statistic}"}}))
    |> to(bucket: {json.dumps(daily)}, org: {json.dumps(org)}, tagColumns: ["device_id"])
"""
    return script


def task_flux(raw, daily, org):
    # Recompute every fully retained day, so late writes and outages up to 29
    # days are caught up. Never overwrite an older summary from a partial day.
    return f"""import "date"
option task = {{name: "{TASK_NAME}", every: 1h, offset: 10m}}
stop = date.truncate(t: now(), unit: 1d)
start = date.add(d: 1d, to: date.truncate(t: date.sub(d: {RAW_DAYS}d, from: now()), unit: 1d))
""" + rollup_flux(raw, daily, org, "start", "stop")


class InfluxAdmin:
    def __init__(self, url, token, org, raw):
        self.url = url.rstrip("/")
        self.token = token
        self.org = org
        self.raw = raw
        self.daily = raw + "_daily"

    def request(self, method, path, body=None, accept="application/json", missing_ok=False):
        data = None if body is None else json.dumps(body).encode()
        request = Request(self.url + "/api/v2/" + path, data=data, method=method,
                          headers={"Authorization": "Token " + self.token,
                                   "Content-Type": "application/json", "Accept": accept})
        try:
            with urlopen(request, timeout=300) as response:
                result = response.read().decode()
        except HTTPError as error:
            if missing_ok and error.code == 404:
                return None
            raise RuntimeError(f"InfluxDB {method} {path}: {error.code} {error.read().decode()}") from None
        if accept == "application/csv":
            return result
        return json.loads(result) if result else None

    def query(self, flux):
        result = self.request("POST", "query?" + urlencode({"org": self.org}),
                              {"query": flux, "dialect": {"annotations": []}}, "application/csv")
        # Influx returns a new header for tables with different schemas.
        rows, header = [], None
        for row in csv.reader(io.StringIO(result)):
            if not row:
                continue
            if "result" in row and "table" in row:
                header = row
            elif header:
                rows.append(dict(zip(header, row)))
        return rows

    def bucket(self, name):
        result = self.request("GET", "buckets?" + urlencode({"org": self.org, "name": name}), missing_ok=True)
        buckets = result["buckets"] if result else []
        if len(buckets) > 1:
            raise RuntimeError(f"Multiple buckets named {name}")
        return buckets[0] if buckets else None

    def tasks(self, org_id):
        tasks, after = [], ""
        while True:
            page = self.request("GET", "tasks?" + urlencode({"orgID": org_id, "limit": 100, "after": after}))["tasks"]
            tasks.extend(t for t in page if t["name"] == TASK_NAME)
            if len(page) < 100:
                return tasks
            after = page[-1]["id"]

    def verify_range(self, start, stop):
        """Independently check every stored statistic before expiring raw data."""
        bounds = f"range(start: {timestamp(start)}, stop: {timestamp(stop)})"
        source = self.query(f"""from(bucket: {json.dumps(self.raw)}) |> {bounds}
            |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
            |> filter(fn: (r) => contains(value: r._field, set: {json.dumps(FIELDS)}))
            |> keep(columns: ["_time", "device_id", "_field", "_value"])""")
        values = defaultdict(list)
        for row in source:
            values[(row["_time"][:10], row["device_id"], row["_field"])].append(float(row["_value"]))
        expected = {}
        for (day, device, field), readings in values.items():
            for stat, value in {"mean": math.fsum(readings) / len(readings), "min": min(readings),
                                "max": max(readings), "count": len(readings)}.items():
                expected[(day + "T00:00:00Z", device, field + "_" + stat)] = value
        actual = self.query(f"""from(bucket: {json.dumps(self.daily)}) |> {bounds}
            |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
            |> keep(columns: ["_time", "device_id", "_field", "_value"])""")
        stored = {(r["_time"], r["device_id"], r["_field"]): float(r["_value"]) for r in actual}
        if expected.keys() != stored.keys() or any(
            not math.isclose(value, stored[key], rel_tol=1e-9, abs_tol=1e-9)
            for key, value in expected.items()
        ):
            raise RuntimeError(f"Daily summary verification failed for {timestamp(start)} to {timestamp(stop)}")
        print(f"Verified {len(source)} raw field values -> {len(stored)} daily statistics "
              f"({start.date()} to {stop.date()}, exclusive)", flush=True)
        return len(stored)

    def run_task(self, task_id):
        run = self.request("POST", f"tasks/{task_id}/runs", {})
        path = f"tasks/{task_id}/runs/{run['id']}"
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            run = self.request("GET", path)
            if run["status"] == "success":
                print("Scheduled task test run succeeded", flush=True)
                return
            if run["status"] in ("failed", "canceled"):
                raise RuntimeError(f"Task run {run['status']}: {run.get('log', [])}")
            time.sleep(1)
        raise RuntimeError("Timed out waiting for the daily summary task")

    def configure(self):
        raw = self.bucket(self.raw)
        if not raw:
            raise RuntimeError(f"Raw bucket {self.raw} must already exist")
        daily = self.bucket(self.daily)
        retention = [{"type": "expire", "everySeconds": DAILY_DAYS * 86400}]
        if daily:
            self.request("PATCH", "buckets/" + daily["id"], {"retentionRules": retention})
        else:
            self.request("POST", "buckets", {"orgID": raw["orgID"], "name": self.daily,
                                             "retentionRules": retention})

        now = datetime.now(timezone.utc)
        stop = midnight(now)
        first = self.query(f"""from(bucket: {json.dumps(self.raw)})
            |> range(start: 0, stop: {timestamp(stop)})
            |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
            |> first() |> group() |> sort(columns: ["_time"]) |> limit(n: 1)""")
        if first:
            start = midnight(datetime.fromisoformat(first[0]["_time"].replace("Z", "+00:00")))
            # A rerun must not replace historical summaries using raw data that
            # has already partly expired. Also respect the destination retention.
            limits = [DAILY_DAYS * 86400]
            limits.extend(r["everySeconds"] for r in raw["retentionRules"] if r["everySeconds"])
            complete_start = midnight(now - timedelta(seconds=min(limits))) + timedelta(days=1)
            start = max(start, complete_start)
            while start < stop:
                end = min(start + timedelta(days=30), stop)
                self.query(rollup_flux(self.raw, self.daily, self.org, timestamp(start), timestamp(end)))
                self.verify_range(start, end)
                start = end

        tasks = self.tasks(raw["orgID"])
        if len(tasks) > 1:
            raise RuntimeError(f"Multiple tasks named {TASK_NAME}; resolve duplicates before changing retention")
        body = {"flux": task_flux(self.raw, self.daily, self.org), "status": "active"}
        if tasks:
            task = self.request("PATCH", "tasks/" + tasks[0]["id"], body)
        else:
            task = self.request("POST", "tasks", {**body, "orgID": raw["orgID"]})
        self.run_task(task["id"])
        start = midnight(now - timedelta(days=RAW_DAYS)) + timedelta(days=1)
        self.verify_range(start, stop)
        # Do this last: failed backfills, verification, or task runs leave the
        # raw bucket's existing retention untouched.
        self.request("PATCH", "buckets/" + raw["id"], {"retentionRules": [
            {"type": "expire", "everySeconds": RAW_DAYS * 86400}]})
        self.check()

    def check(self):
        for name, days in ((self.raw, RAW_DAYS), (self.daily, DAILY_DAYS)):
            bucket = self.bucket(name)
            if not bucket or [r["everySeconds"] for r in bucket["retentionRules"]] != [days * 86400]:
                raise RuntimeError(f"{name}: expected {days}-day retention")
            print(f"{name}: {days}-day retention", flush=True)
        tasks = self.tasks(bucket["orgID"])
        if len(tasks) != 1 or tasks[0]["status"] != "active" or tasks[0]["flux"] != task_flux(self.raw, self.daily, self.org):
            raise RuntimeError("Daily task is missing, inactive, duplicated, or differs from the configuration")
        runs = self.request("GET", f"tasks/{tasks[0]['id']}/runs?limit=10")["runs"]
        if not any(r["status"] == "success" for r in runs):
            raise RuntimeError("No successful recent daily task run found")
        print("Daily task: active, runs hourly with 10-minute offset; successful run found", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check retention and task state without making changes")
    args = parser.parse_args()
    admin = InfluxAdmin(os.environ["INFLUX_URL"], os.environ["INFLUX_TOKEN"],
                        os.environ["INFLUX_ORG"], os.environ["INFLUX_BUCKET"])
    if args.check:
        admin.check()
    else:
        admin.configure()


if __name__ == "__main__":
    main()
