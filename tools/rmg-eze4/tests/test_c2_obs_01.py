import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/rmg-eze4"))

from c2_obs_01_analyze import analyze, parse_jsonl  # noqa: E402
from c2_obs_01_collect import classify_read, discover_sources  # noqa: E402


IDENTITY = {
    "model": "SM-X510",
    "device": "gts9fewifi",
    "build_fingerprint": "samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys",
    "build_incremental": "X510XXUCEZE4",
    "kernel_release": "5.15.189-android13-3-33478785",
}


def record(sequence, timestamp, measurement="heartbeat", source="collector", value=None,
           status="AVAILABLE", schema="c2-obs-01.v1"):
    return {
        "schema_version": schema, "trial_id": "TRL-C2-001", "sequence": sequence,
        "timestamp_monotonic_ns": timestamp, "timestamp_boottime_seconds": timestamp / 1e9,
        "timestamp_wall_utc": "2026-09-06T00:00:00Z", "source": source,
        "measurement": measurement, "value": value, "read_status": status,
        "read_duration_ns": 1_000_000,
    }


def metadata(sequence=0, timestamp=1_000_000_000, identity=None, cgroup_status="AVAILABLE"):
    ident = identity or IDENTITY
    values = {k: {"value": v, "status": "AVAILABLE", "read_duration_ns": 1} for k, v in ident.items()}
    values["boot_id"] = {"value": "11111111-2222-3333-4444-555555555555", "status": "AVAILABLE", "read_duration_ns": 1}
    return record(sequence, timestamp, "metadata", value={
        "collector_version": "1.0.0", "metadata": values,
        "interfaces": {
            "trial_cgroup_events": {"path": "/sys/fs/cgroup/x/cgroup.events", "status": cgroup_status},
            "suspend_success": {"path": "/sys/power/suspend_stats/success", "status": "AVAILABLE"},
        },
        "requested_interval_ms": 200, "duration_seconds": 1, "trial_pid": 123,
    })


class C2AnalyzerTests(unittest.TestCase):
    def run_records(self, records):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "obs.jsonl"
            path.write_text("".join(json.dumps(r) + "\n" for r in records))
            return analyze(path, ROOT)

    def clean(self, gaps=(200_000_000, 200_000_000)):
        rows = [metadata()]
        stamp = 1_100_000_000
        sequence = 1
        for index, gap in enumerate((0,) + tuple(gaps)):
            if index:
                stamp += gap
            rows.append(record(sequence, stamp))
            sequence += 1
            rows.append(record(sequence, stamp + 1, "raw_read", "trial_cgroup_events", "populated 1\nfrozen 0"))
            sequence += 1
            rows.append(record(sequence, stamp + 2, "raw_read", "suspend_success", "4"))
            sequence += 1
        return rows

    def test_valid_sample_and_no_suspend(self):
        result = self.run_records(self.clean())
        self.assertEqual(result["coverage"], "COVERAGE_VALID")
        self.assertEqual(result["c2_status"], "C2_ABSENT_FOR_OBSERVED_INTERVAL")
        self.assertEqual(result["max_gap_ns"], 200_000_000)

    def test_exact_500ms_boundary_is_valid(self):
        self.assertEqual(self.run_records(self.clean((500_000_000,)))["coverage"], "COVERAGE_VALID")

    def test_gap_above_boundary_and_single_stall_fail(self):
        result = self.run_records(self.clean((200_000_000, 500_000_001, 200_000_000)))
        self.assertEqual(result["coverage"], "COVERAGE_INVALID")
        self.assertIn("COVERAGE_GAP_EXCEEDS_500MS_OR_INSUFFICIENT", result["errors"])

    def test_multiple_small_gaps_are_valid(self):
        self.assertEqual(self.run_records(self.clean((499_000_000,) * 5))["coverage"], "COVERAGE_VALID")

    def test_freeze_detectable(self):
        rows = self.clean()
        next(r for r in reversed(rows) if r["source"] == "trial_cgroup_events")["value"] = "populated 1\nfrozen 1"
        self.assertEqual(self.run_records(rows)["c2_status"], "C2_PRESENT")

    def test_suspend_counter_change_is_detectable(self):
        rows = self.clean()
        rows.extend([
            record(len(rows), 1_600_000_001, "raw_read", "suspend_success", "4"),
            record(len(rows) + 1, 1_600_000_002, "raw_read", "suspend_success", "5"),
        ])
        self.assertEqual(self.run_records(rows)["c2_status"], "C2_PRESENT")

    def test_ambiguous_and_insufficient_coverage_are_unknown(self):
        rows = self.clean()
        rows[1]["read_status"] = "AMBIGUOUS"
        self.assertEqual(self.run_records(rows)["c2_status"], "C2_UNKNOWN")
        self.assertEqual(self.run_records([metadata(), record(1, 1_100_000_000)])["coverage"], "COVERAGE_INVALID")

    def test_wrong_firmware_and_wrong_kernel_fail_closed(self):
        wrong_fw = dict(IDENTITY, build_incremental="X510XXSEEZG3")
        self.assertIn("IDENTITY_MISMATCH_OR_UNAVAILABLE_build_incremental", self.run_records([metadata(identity=wrong_fw), *self.clean()[1:]])["errors"])
        wrong_kernel = dict(IDENTITY, kernel_release="5.15.180")
        self.assertIn("IDENTITY_MISMATCH_OR_UNAVAILABLE_kernel_release", self.run_records([metadata(identity=wrong_kernel), *self.clean()[1:]])["errors"])

    def test_duplicate_sequence_and_timestamp_regression(self):
        rows = self.clean()
        rows[2]["sequence"] = rows[1]["sequence"]
        self.assertIn("DUPLICATE_SEQUENCE", self.run_records(rows)["errors"])
        rows = self.clean()
        rows[2]["timestamp_monotonic_ns"] = rows[1]["timestamp_monotonic_ns"] - 1
        self.assertIn("MONOTONIC_TIMESTAMP_REGRESSION", self.run_records(rows)["errors"])

    def test_malformed_missing_and_unsupported_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text("{bad json\n")
            self.assertIn("MALFORMED_JSON_LINE_1", parse_jsonl(path)[1])
            path.write_text(json.dumps({"schema_version": "c2-obs-01.v1"}) + "\n")
            self.assertIn("MISSING", parse_jsonl(path)[1][0])
            path.write_text(json.dumps(record(0, 1, schema="c2-obs-99")) + "\n")
            self.assertIn("UNSUPPORTED_SCHEMA", parse_jsonl(path)[1][0])


class C2DiscoveryTests(unittest.TestCase):
    def test_status_classification_is_lossless(self):
        self.assertEqual(classify_read(0, ""), "AVAILABLE")
        self.assertEqual(classify_read(1, "Permission denied"), "PERMISSION_DENIED")
        self.assertEqual(classify_read(1, "No such file or directory"), "UNAVAILABLE")
        self.assertEqual(classify_read(1, "Invalid argument"), "UNSUPPORTED")
        self.assertEqual(classify_read(1, "transport error"), "AMBIGUOUS")

    def test_available_missing_permission_and_partial_discovery(self):
        def fake(path):
            if path == "/proc/123/cgroup":
                return "AVAILABLE", "0::/uid_1000/pid_123", 1
            if path.endswith("uid_1000/pid_123/cgroup.events"):
                return "AVAILABLE", "populated 1\nfrozen 0", 1
            if path == "/proc/uptime":
                return "AVAILABLE", "10.00 2.00", 1
            if "wakeup_count" in path:
                return "PERMISSION_DENIED", None, 1
            return "UNAVAILABLE", None, 1
        result = discover_sources(fake, 123)
        self.assertEqual(result["device_boottime"]["status"], "AVAILABLE")
        self.assertEqual(result["wakeup_count"]["status"], "PERMISSION_DENIED")
        self.assertEqual(result["suspend_success"]["status"], "UNAVAILABLE")
        self.assertEqual(result["trial_cgroup_events"]["status"], "AVAILABLE")

    def test_missing_pid_is_unsupported_not_unavailable(self):
        result = discover_sources(lambda path: ("UNAVAILABLE", None, 1), None)
        self.assertEqual(result["trial_cgroup_events"]["status"], "UNSUPPORTED")

    def test_android_mixed_hierarchies_select_unified_cgroup(self):
        expected = "/sys/fs/cgroup/apps/uid_10062/pid_1989/cgroup.events"

        def fake(path):
            if path == "/proc/1989/cgroup":
                return "AVAILABLE", "5:freezer:/\n2:cpu:/top-app\n0::/apps/uid_10062/pid_1989", 1
            if path == expected:
                return "AVAILABLE", "populated 1\nfrozen 0", 1
            return "UNAVAILABLE", None, 1

        result = discover_sources(fake, 1989)
        self.assertEqual(result["trial_cgroup_events"]["path"], expected)
        self.assertEqual(result["trial_cgroup_events"]["status"], "AVAILABLE")

    def test_collector_source_contains_no_device_write_operations(self):
        source = (ROOT / "tools/rmg-eze4/c2_obs_01_collect.py").read_text()
        for forbidden in ["adb push", "adb install", "su -c", "setenforce", "sched_setaffinity", "wake_lock"]:
            self.assertNotIn(forbidden, source)
        self.assertIn('["shell", "cat", "--", path]', source)


if __name__ == "__main__":
    unittest.main()
