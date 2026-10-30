"""Integration tests against InfluxDB 2.7 using isolated, disposable resources.

Run with RUN_INFLUX_INTEGRATION=1 and INFLUX_URL/TOKEN/ORG configured.
No production bucket or task is changed. Python standard library only.
"""

import base64
import importlib.util
import json
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

spec = importlib.util.spec_from_file_location(
    "retention", Path(__file__).resolve().parents[1] / "influxdb/configure-retention.py")
retention = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retention)


@unittest.skipUnless(os.getenv("RUN_INFLUX_INTEGRATION") == "1", "requires isolated Influx integration run")
class RetentionIntegration(unittest.TestCase):
    def setUp(self):
        self.name = "retention-test-" + uuid.uuid4().hex[:12]
        retention.TASK_NAME = self.name + "-task"
        self.admin = retention.InfluxAdmin(os.environ["INFLUX_URL"], os.environ["INFLUX_TOKEN"],
                                           os.environ["INFLUX_ORG"], self.name)
        orgs = self.admin.request("GET", "orgs?" + urlencode({"org": self.admin.org}))["orgs"]
        self.org_id = orgs[0]["id"]
        self.admin.request("POST", "buckets", {"orgID": self.org_id, "name": self.name,
                                               "retentionRules": [{"type": "expire", "everySeconds": 0}]})
        self.today = retention.midnight(datetime.now(timezone.utc))

    def tearDown(self):
        for task in self.admin.tasks(self.org_id):
            self.admin.request("DELETE", "tasks/" + task["id"])
        for name in (self.name, self.admin.daily):
            bucket = self.admin.bucket(name)
            if bucket:
                self.admin.request("DELETE", "buckets/" + bucket["id"])

    def write(self, records):
        lines = []
        for day, minute, device, fields in records:
            instant = self.today + timedelta(days=day, minutes=minute)
            fields = ",".join(f"{name}={float(value)}" for name, value in fields.items())
            lines.append(f"room_environment,device_id={device} {fields} {int(instant.timestamp())}")
        path = "write?" + urlencode({"org": self.admin.org, "bucket": self.name, "precision": "s"})
        request = Request(self.admin.url + "/api/v2/" + path, data="\n".join(lines).encode(),
                          headers={"Authorization": "Token " + self.admin.token,
                                   "Content-Type": "text/plain"})
        with urlopen(request, timeout=30) as response:
            self.assertEqual(response.status, 204)

    def daily_rows(self):
        return self.admin.query(f'from(bucket: "{self.admin.daily}") |> range(start: 0)')

    def test_backfill_late_writes_and_repeat_provisioning(self):
        # Include pre-retention history, missing optional fields, device grouping,
        # exact midnight, and an incomplete current day.
        self.write([
            (-35, 60, "a", {"temperature_c": 10}),
            (-35, 90, "a", {"temperature_c": 20}),
            (-2, 0, "a", {"temperature_c": 16, "humidity_percent": 40, "pressure_hpa": 1000,
                            "light_lux": 10, "co2_ppm": 500}),
            (-2, 30, "a", {"temperature_c": 24, "humidity_percent": 60}),
            (-2, 30, "b", {"temperature_c": 30}),
            (-1, 0, "a", {"temperature_c": 22}),
            (0, 0, "a", {"temperature_c": 23}),
        ])
        self.admin.configure()
        rows = self.daily_rows()
        self.assertEqual(len(rows), 32)
        self.assertFalse(any(r["_time"][:10] == self.today.date().isoformat() for r in rows))
        old_day = (self.today - timedelta(days=35)).date().isoformat()
        old = {r["_field"]: float(r["_value"]) for r in rows if r["_time"].startswith(old_day)}
        self.assertEqual(old, {"temperature_c_mean": 15, "temperature_c_min": 10,
                               "temperature_c_max": 20, "temperature_c_count": 2})
        summary = {r["_field"]: float(r["_value"]) for r in rows
                   if r["_time"].startswith((self.today - timedelta(days=2)).date().isoformat())
                   and r["device_id"] == "a"}
        self.assertEqual(summary["temperature_c_mean"], 20)
        self.assertEqual(summary["pressure_hpa_count"], 1)
        dashboard = json.loads((Path(__file__).resolve().parents[1] /
                                "grafana/provisioning/dashboards/mxchip-room.json").read_text())
        for panel in dashboard["panels"]:
            for start, stop in ((-36, -34), (-36, 1), (-2, 1)):
                flux = (panel["targets"][0]["query"]
                        .replace('"room_telemetry"', json.dumps(self.name))
                        .replace('"room_telemetry_daily"', json.dumps(self.admin.daily))
                        .replace("v.timeRangeStart", retention.timestamp(self.today + timedelta(days=start)))
                        .replace("v.timeRangeStop", retention.timestamp(self.today + timedelta(days=stop))))
                result = self.admin.query(flux)
                if panel["id"] == 1:
                    self.assertEqual(len(result), 1 if stop == -34 else 6 if start == -36 else 5)
                    if stop == -34:
                        self.assertEqual(float(result[0]["_value"]), 15)
                elif stop == -34:
                    self.assertEqual(result, [])
                else:
                    self.assertTrue(result)
        self.write([(-2, 60, "a", {"temperature_c": 32})])
        task_id = self.admin.tasks(self.org_id)[0]["id"]
        self.admin.run_task(task_id)
        self.admin.verify_range(self.today - timedelta(days=2), self.today)
        self.admin.configure()
        self.assertEqual(self.admin.tasks(self.org_id)[0]["id"], task_id)
        self.assertEqual(len(self.daily_rows()), len(rows))
        # Rerunning cannot erase old summaries, even after raw expiration.
        self.assertEqual({r["_field"]: float(r["_value"]) for r in self.daily_rows()
                          if r["_time"].startswith(old_day)}, old)

    def test_failed_verification_preserves_raw_retention(self):
        self.write([(-1, 30, "a", {"temperature_c": 20})])
        def fail(*args):
            raise RuntimeError("injected summary verification failure")
        self.admin.verify_range = fail
        with self.assertRaisesRegex(RuntimeError, "injected"):
            self.admin.configure()
        self.assertEqual(self.admin.bucket(self.name)["retentionRules"][0]["everySeconds"], 0)

    @unittest.skipUnless(os.getenv("GRAFANA_URL"), "requires Grafana for frame-schema regression")
    def test_grafana_frames_use_sample_time(self):
        # Direct Flux checks miss Grafana choosing the first returned time field
        # (_start after regrouping) instead of the actual reading timestamp.
        fields = {"temperature_c": 20, "humidity_percent": 45, "pressure_hpa": 1000}
        self.write([(-35, 60, "a", fields), (-2, 60, "a", fields),
                    (-1, 60, "a", fields), (-1, 90, "b", fields), (0, 0, "a", fields)])
        self.admin.configure()
        dashboard = json.loads((Path(__file__).resolve().parents[1] /
                                "grafana/provisioning/dashboards/mxchip-room.json").read_text())
        credentials = base64.b64encode(
            (os.environ["GRAFANA_USER"] + ":" + os.environ["GRAFANA_PASSWORD"]).encode()).decode()
        for start, stop in ((-36, -34), (-36, 1), (-2, 1)):
            begin, end = (self.today + timedelta(days=d) for d in (start, stop))
            queries, expected = [], {}
            for panel in dashboard["panels"]:
                ref = str(panel["id"])
                flux = (panel["targets"][0]["query"]
                        .replace('"room_telemetry"', json.dumps(self.name))
                        .replace('"room_telemetry_daily"', json.dumps(self.admin.daily)))
                queries.append({"refId": ref, "datasource": {"type": "influxdb", "uid": "InfluxDB"},
                                "query": flux, "maxDataPoints": 1000, "intervalMs": 60000})
                rows = self.admin.query(flux.replace("v.timeRangeStart", retention.timestamp(begin))
                                        .replace("v.timeRangeStop", retention.timestamp(end)))
                expected[ref] = {}
                for row in rows:
                    instant = datetime.fromisoformat(row["_time"].replace("Z", "+00:00"))
                    expected[ref].setdefault(row["device_id"], []).append(
                        (int(instant.timestamp() * 1000), float(row["_value"])))
            request = Request(os.environ["GRAFANA_URL"].rstrip("/") + "/api/ds/query",
                              data=json.dumps({"from": str(int(begin.timestamp() * 1000)),
                                               "to": str(int(end.timestamp() * 1000)),
                                               "queries": queries}).encode(),
                              headers={"Authorization": "Basic " + credentials,
                                       "Content-Type": "application/json"})
            with urlopen(request, timeout=60) as response:
                results = json.load(response)["results"]
            self.assertEqual(set(results), set(expected))
            for ref, result in results.items():
                self.assertFalse(result.get("error"), result.get("error"))
                actual = {}
                for frame in result["frames"]:
                    schema = frame["schema"]["fields"]
                    time_columns = [v for f, v in zip(schema, frame["data"]["values"])
                                    if f["type"] == "time"]
                    self.assertEqual(len(time_columns), 1, schema)
                    for field, values in zip(schema, frame["data"]["values"]):
                        if field["type"] == "number":
                            device = field["labels"]["device_id"]
                            actual.setdefault(device, []).extend(
                                (t, v) for t, v in zip(time_columns[0], values) if v is not None)
                self.assertEqual(actual, expected[ref])
                self.assertEqual(sum(map(len, actual.values())), 1 if stop == -34 else 5 if start == -36 else 4)

    def test_empty_bucket_can_be_provisioned(self):
        self.admin.configure()
        self.assertEqual(self.daily_rows(), [])

    def test_partly_expired_boundary_day_keeps_complete_summary(self):
        self.write([(-30, 0, "a", {"temperature_c": 10}),
                    (-30, 1410, "a", {"temperature_c": 30}),
                    (-29, 0, "a", {"temperature_c": 20})])
        self.admin.configure()
        # Model expiration of the first part of the oldest raw day.
        day = self.today - timedelta(days=30)
        self.admin.request("POST", "delete?" + urlencode({"org": self.admin.org, "bucket": self.name}),
                           {"start": retention.timestamp(day),
                            "stop": retention.timestamp(day + timedelta(seconds=1)),
                            "predicate": '_measurement="room_environment" AND device_id="a"'})
        self.admin.configure()
        summary = {r["_field"]: float(r["_value"]) for r in self.daily_rows()
                   if r["_time"].startswith(day.date().isoformat())}
        self.assertEqual(summary["temperature_c_mean"], 20)
        self.assertEqual(summary["temperature_c_count"], 2)
        dashboard = json.loads((Path(__file__).resolve().parents[1] /
                                "grafana/provisioning/dashboards/mxchip-room.json").read_text())
        flux = (dashboard["panels"][0]["targets"][0]["query"]
                .replace('"room_telemetry"', json.dumps(self.name))
                .replace('"room_telemetry_daily"', json.dumps(self.admin.daily))
                .replace("v.timeRangeStart", retention.timestamp(day))
                .replace("v.timeRangeStop", retention.timestamp(self.today)))
        rows = self.admin.query(flux)
        self.assertEqual(len(rows), 2)
        self.assertEqual([float(r["_value"]) for r in rows], [20, 20])


if __name__ == "__main__":
    unittest.main(verbosity=2)
