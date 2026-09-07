import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/rmg-eze4"))

from c3_obs_01_analyze import (  # noqa: E402
    analyze,
    parse_cpu_list,
    parse_frequency,
    parse_jsonl,
    parse_processor_from_stat,
    parse_temperature,
)
from c3_obs_01_collect import _sample_sources, discover_sources  # noqa: E402


IDENTITY = {
    "model": "SM-X510",
    "device": "gts9fewifi",
    "build_fingerprint": "samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys",
    "build_incremental": "X510XXUCEZE4",
    "kernel_release": "5.15.189-android13-3-33478785",
}


def descriptor(path, initial, *, sample=False, status="AVAILABLE", unit=None):
    value = {
        "path": path,
        "status": status,
        "initial_value": initial,
        "read_duration_ns": 1,
        "sample": sample,
    }
    if unit:
        value["unit"] = unit
    return value


def interfaces():
    zone_path = "/sys/class/thermal/thermal_zone0"
    policy_path = "/sys/devices/system/cpu/cpufreq/policy0"
    return {
        "thermal_root": {"path": "/sys/class/thermal", "status": "AVAILABLE"},
        "cpufreq_root": {"path": "/sys/devices/system/cpu/cpufreq", "status": "AVAILABLE"},
        "thermal_zones": {
            "thermal_zone0": {
                "path": zone_path,
                "discovery_status": "AVAILABLE",
                "type": descriptor(zone_path + "/type", "cpu-thermal"),
                "temperature": descriptor(zone_path + "/temp", "42000", sample=True,
                                            unit="millidegrees_celsius"),
                "trip_points": {
                    "0": {
                        "temp": descriptor(zone_path + "/trip_point_0_temp", "95000",
                                            unit="millidegrees_celsius"),
                        "type": descriptor(zone_path + "/trip_point_0_type", "critical"),
                    }
                },
            }
        },
        "cpufreq_policies": {
            "policy0": {
                "path": policy_path,
                "discovery_status": "AVAILABLE",
                "affected_cpus": descriptor(policy_path + "/affected_cpus", "0-3"),
                "related_cpus": descriptor(policy_path + "/related_cpus", "0-3"),
                "governor": descriptor(policy_path + "/scaling_governor", "schedutil"),
                "min_freq": descriptor(policy_path + "/scaling_min_freq", "300000", unit="khz"),
                "max_freq": descriptor(policy_path + "/scaling_max_freq", "2400000",
                                        sample=True, unit="khz"),
                "effective_freq": descriptor(policy_path + "/scaling_cur_freq", "1800000",
                                              sample=True, unit="khz"),
                "effective_freq_name": "scaling_cur_freq",
            }
        },
        "static_sources": {
            "cpu_online": descriptor("/sys/devices/system/cpu/online", "0-7", sample=True),
            "cpu_present": descriptor("/sys/devices/system/cpu/present", "0-7", sample=True),
        },
        "trial_cpu": descriptor("/proc/123/stat", "", sample=True),
        "requested_trial_pid": 123,
    }


def stat_value(cpu):
    # After the closing ')' field 3 is index 0; field 39 (processor) is 36.
    tail = ["S"] + ["0"] * 35 + [str(cpu)] + ["0"] * 16
    return "123 (inert worker) " + " ".join(tail)


def make_records(gaps=(200_000_000, 200_000_000), *, wrong_fw=False,
                 temp_values=None, temp_status=None, migration=(2, 2, 2)):
    iface = interfaces()
    metadata_props = {
        key: {"value": ("X510XXSEEZG3" if key == "build_incremental" and wrong_fw else value),
              "status": "AVAILABLE", "read_duration_ns": 1}
        for key, value in IDENTITY.items()
    }
    metadata_props["interfaces"] = iface
    metadata_props["sample_sources"] = [
        "cpu_online", "cpu_present", "thermal:thermal_zone0:temperature",
        "cpufreq:policy0:effective_freq", "cpufreq:policy0:max_freq", "trial_cpu",
    ]
    metadata_props["requested_interval_ms"] = 200
    metadata_props["trial_pid"] = 123
    metadata_props["declared_cpus"] = "0-3"
    value = {
        "collector_version": "1.0.0",
        "metadata": metadata_props,
        "interfaces": iface,
        "sample_sources": metadata_props["sample_sources"],
        "requested_interval_ms": 200,
        "trial_pid": 123,
        "declared_cpus": "0-3",
    }
    rows = []
    sequence = 0
    stamp = 1_000_000_000

    def record(source, measurement, item, status="AVAILABLE", when=None):
        nonlocal sequence
        result = {
            "schema_version": "c3-obs-01.v1",
            "trial_id": "TRL-C3-001",
            "sequence": sequence,
            "timestamp_monotonic_ns": stamp if when is None else when,
            "timestamp_boottime_seconds": stamp / 1e9,
            "timestamp_wall_utc": "2026-09-06T00:00:00Z",
            "source": source,
            "measurement": measurement,
            "value": item,
            "read_status": status,
            "read_duration_ns": 1,
        }
        rows.append(result)
        sequence += 1

    record("collector", "metadata", value)
    temperatures = temp_values or ("42000", "42000", "42000")
    for index, gap in enumerate((0,) + tuple(gaps)):
        if index:
            stamp += gap
        record("collector", "heartbeat", None)
        raw = {
            "cpu_online": "0-7",
            "cpu_present": "0-7",
            "thermal:thermal_zone0:temperature": temperatures[index],
            "cpufreq:policy0:effective_freq": "1800000",
            "cpufreq:policy0:max_freq": "2400000",
            "trial_cpu": stat_value(migration[index]),
        }
        for source, item in raw.items():
            status = "AVAILABLE"
            if source == "thermal:thermal_zone0:temperature" and temp_status:
                status = temp_status[index]
            record(source, "raw_read", item, status=status, when=stamp + 1)
    return rows


class C3AnalyzerTests(unittest.TestCase):
    def run_records(self, records):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "obs.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in records),
                            encoding="utf-8")
            return analyze(path, ROOT)

    def test_parsers_cover_frequency_cpu_migration_and_malformed_input(self):
        self.assertEqual(parse_temperature("42000"), 42.0)
        self.assertEqual(parse_frequency("1800000"), 1_800_000_000)
        self.assertEqual(parse_frequency("1.8GHz"), 1_800_000_000)
        self.assertEqual(parse_cpu_list("0-3,6"), {0, 1, 2, 3, 6})
        self.assertEqual(parse_processor_from_stat(stat_value(6)), 6)
        self.assertIsNone(parse_frequency("not-a-frequency"))
        self.assertIsNone(parse_processor_from_stat("1 (unterminated"))

    def test_clean_observation_is_observable_but_does_not_claim_c3(self):
        result = self.run_records(make_records())
        self.assertEqual(result["coverage"], "COVERAGE_VALID")
        self.assertEqual(result["c3_status"], "C3_OBSERVABLE")
        self.assertEqual(result["classification"], "C3_ABSENT")
        self.assertEqual(result["migration_count"], 0)

    def test_sensor_disappearance_is_unknown_not_absent(self):
        result = self.run_records(make_records(temp_status=("AVAILABLE", "UNAVAILABLE", "AVAILABLE")))
        self.assertEqual(result["classification"], "C3_UNKNOWN")
        self.assertEqual(result["c3_status"], "C3_PARTIAL")
        self.assertTrue(any("THERMAL_SENSOR_DISAPPEARED" in error for error in result["errors"]))

    def test_malformed_thermal_reading_is_unknown(self):
        result = self.run_records(make_records(temp_values=("42000", "bad", "42000")))
        self.assertEqual(result["classification"], "C3_UNKNOWN")
        self.assertIn("MALFORMED_READING_thermal:thermal_zone0:temperature", result["errors"])

    def test_timestamp_gap_above_500ms_invalidates_coverage(self):
        result = self.run_records(make_records(gaps=(200_000_000, 500_000_001)))
        self.assertEqual(result["coverage"], "COVERAGE_INVALID")
        self.assertIn("COVERAGE_GAP_EXCEEDS_500MS_OR_INSUFFICIENT", result["errors"])

    def test_wrong_firmware_fails_closed(self):
        result = self.run_records(make_records(wrong_fw=True))
        self.assertEqual(result["c3_status"], "C3_BLOCKED")
        self.assertIn("IDENTITY_MISMATCH_OR_UNAVAILABLE_build_incremental", result["errors"])

    def test_cpu_migration_is_reported_and_declared_stratum_is_enforced(self):
        result = self.run_records(make_records(migration=(2, 4, 2)))
        self.assertEqual(result["migration_count"], 2)
        self.assertEqual(result["classification"], "C3_UNKNOWN")
        self.assertIn("CPU_MIGRATION_OUTSIDE_DECLARED_STRATUM", result["errors"])

    def test_frequency_cap_drop_is_positive_c3_evidence(self):
        rows = make_records()
        cap_samples = [row for row in rows
                       if row["source"] == "cpufreq:policy0:max_freq"]
        cap_samples[1]["value"] = "1200000"
        result = self.run_records(rows)
        self.assertEqual(result["classification"], "C3_PRESENT")
        self.assertGreaterEqual(result["frequency_clamp_count"], 1)

    def test_malformed_and_unsupported_json_are_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text("{bad json\n", encoding="utf-8")
            self.assertIn("MALFORMED_JSON_LINE_1", parse_jsonl(path)[1])
            path.write_text(json.dumps({"schema_version": "c3-obs-01.v1"}) + "\n",
                            encoding="utf-8")
            self.assertIn("MISSING", parse_jsonl(path)[1][0])
            row = make_records()[0]
            row["schema_version"] = "c3-obs-99"
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            self.assertIn("UNSUPPORTED_SCHEMA", parse_jsonl(path)[1][0])


class C3DiscoveryTests(unittest.TestCase):
    def test_sampling_excludes_sources_denied_during_discovery(self):
        iface = interfaces()
        iface["thermal_zones"]["thermal_zone0"]["temperature"]["status"] = "PERMISSION_DENIED"
        sources = _sample_sources(iface)
        self.assertNotIn("thermal:thermal_zone0:temperature", sources)
        self.assertIn("cpufreq:policy0:effective_freq", sources)

    def test_missing_and_permission_sources_are_retained(self):
        def list_dir(path):
            if path == "/sys/class/thermal":
                return "AVAILABLE", ["thermal_zone0"], 1
            if path.endswith("thermal_zone0"):
                return "AVAILABLE", ["type", "temp", "trip_point_0_temp", "trip_point_0_type"], 1
            if path == "/sys/devices/system/cpu/cpufreq":
                return "PERMISSION_DENIED", [], 1
            return "UNAVAILABLE", [], 1

        def read_path(path):
            if path.endswith("/temp"):
                return "PERMISSION_DENIED", None, 1
            if path.endswith("/type"):
                return "AVAILABLE", "cpu-thermal", 1
            if path.endswith("trip_point_0_temp"):
                return "AVAILABLE", "95000", 1
            if path.endswith("trip_point_0_type"):
                return "AVAILABLE", "critical", 1
            return "UNAVAILABLE", None, 1

        result = discover_sources(read_path, list_dir, 123)
        self.assertEqual(result["thermal_zones"]["thermal_zone0"]["temperature"]["status"],
                         "PERMISSION_DENIED")
        self.assertEqual(result["cpufreq_root"]["status"], "PERMISSION_DENIED")
        self.assertEqual(result["thermal_zones"]["thermal_zone0"]["trip_points"]["0"]["type"]["status"],
                         "AVAILABLE")

    def test_collector_source_is_read_only(self):
        source = (ROOT / "tools/rmg-eze4/c3_obs_01_collect.py").read_text(encoding="utf-8")
        for forbidden in ["adb push", "adb install", "su -c", "setenforce",
                          "sched_setaffinity", "wake_lock", "echo "]:
            self.assertNotIn(forbidden, source)
        self.assertIn('["shell", "ls", "-1", "--", path]', source)


if __name__ == "__main__":
    unittest.main()
