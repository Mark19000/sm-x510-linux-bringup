import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/rmg-eze4"))

from c2_dual_clock_analyze import (  # noqa: E402
    MAX_GAP_NS,
    analyze,
    analyze_records,
    parse_jsonl,
)


SCHEMA = "c2-dual-clock-obs.v1"
BOOT_ID = "11111111-2222-3333-4444-555555555555"


def _common(sequence, record_type, mono, boot, previous_mono, baseline_offset,
            *, frozen=0, populated=1, boot_id=BOOT_ID,
            cgroup_status="AVAILABLE", pair_span=1_000):
    offset = boot - mono
    is_metadata = record_type == "metadata"
    record = {
        "schema": SCHEMA,
        "record_type": record_type,
        "trial_id": "TRL-C2-DUAL-001",
        "sequence": sequence,
        "clock_monotonic_ns": mono,
        "clock_boottime_ns": boot,
        "boottime_minus_monotonic_ns": offset,
        "sampling_gap_ns": None if is_metadata else mono - previous_mono,
        "elapsed_monotonic_ns": 0 if is_metadata else mono - 1_000_000_000_000,
        "elapsed_boottime_ns": 0 if is_metadata else boot - 1_000_000_005_000,
        "suspend_delta_ns": 0 if is_metadata else offset - baseline_offset,
        "pair_read_span_ns": pair_span,
        "process_cpu_ns": 2_000_000 + sequence * 100_000,
        "boot_id": boot_id,
        "boot_id_read_status": "AVAILABLE",
        "cgroup_read_status": cgroup_status,
        "cgroup_frozen": frozen if cgroup_status == "AVAILABLE" else None,
        "cgroup_populated": populated if cgroup_status == "AVAILABLE" else None,
    }
    if is_metadata:
        record.update({
            "clock_monotonic_resolution_ns": 1_000,
            "clock_boottime_resolution_ns": 1_000,
            "interval_ms": 100,
            "duration_ms": 1_000,
            "trial_pid": 4321,
            "cgroup_binding_status": "AVAILABLE",
            "cgroup_path": "/sys/fs/cgroup/apps/uid_1000/pid_4321/cgroup.events",
            "pid_starttime_ticks": 77,
        })
    return record


def make_records(extra_offsets=(), gaps=None, *, frozen_at=None,
                 cgroup_status_at=None, boot_id_at=None, pair_span=1_000):
    """Build a complete deterministic observer stream."""

    start_mono = 1_000_000_000_000
    baseline_boot = start_mono + 5_000
    baseline_offset = 5_000
    rows = [_common(0, "metadata", start_mono, baseline_boot, start_mono,
                    baseline_offset, pair_span=pair_span)]
    mono = start_mono
    boot = baseline_boot
    previous_mono = start_mono
    offsets = list(extra_offsets)
    for index in range(4):
        gap = (gaps or [100_000_000] * 4)[index]
        mono += gap
        boot += gap + (offsets[index] if index < len(offsets) else 0)
        status = cgroup_status_at.get(index, "AVAILABLE") if cgroup_status_at else "AVAILABLE"
        boot_id = boot_id_at.get(index, BOOT_ID) if boot_id_at else BOOT_ID
        rows.append(_common(index + 1, "sample", mono, boot, previous_mono,
                            baseline_offset, frozen=(1 if frozen_at == index else 0),
                            cgroup_status=status, boot_id=boot_id,
                            pair_span=pair_span))
        previous_mono = mono
    mono += 100_000_000
    boot += 100_000_000
    end = _common(5, "end", mono, boot, previous_mono, baseline_offset,
                  pair_span=pair_span)
    end.update({"sample_count": 4, "termination": "completed"})
    rows.append(end)
    return rows


class DualClockAnalyzerTests(unittest.TestCase):
    def run_rows(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observer.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows),
                            encoding="utf-8")
            return analyze(path)

    def test_equal_clocks_are_not_suspend(self):
        result = self.run_rows(make_records())
        self.assertEqual(result["status"], "NO_SUSPEND_OBSERVED")
        self.assertEqual(result["coverage"], "COVERAGE_VALID")
        self.assertEqual(result["detection_threshold_ns"], 1_000_000)

    def test_artificial_suspend_divergence_is_detected(self):
        rows = make_records(extra_offsets=[0, 0, 2_000_000, 0])
        result = self.run_rows(rows)
        self.assertEqual(result["status"], "SUSPEND_OBSERVED")
        self.assertGreater(result["max_offset_change_ns"], result["detection_threshold_ns"])

    def test_sub_threshold_jitter_is_not_suspend(self):
        result = self.run_rows(make_records(extra_offsets=[100_000, -50_000, 100_000, -50_000]))
        self.assertEqual(result["status"], "NO_SUSPEND_OBSERVED")

    def test_short_suspend_above_margin_is_detected(self):
        result = self.run_rows(make_records(extra_offsets=[0, 0, 1_500_000, 0]))
        self.assertEqual(result["status"], "SUSPEND_OBSERVED")

    def test_repeated_suspend_divergence_is_detected(self):
        result = self.run_rows(make_records(extra_offsets=[1_200_000] * 4))
        self.assertEqual(result["status"], "SUSPEND_OBSERVED")
        self.assertGreaterEqual(result["max_offset_change_ns"], 4_800_000)

    def test_sampling_stall_is_coverage_invalid(self):
        gaps = [100_000_000, MAX_GAP_NS + 1, 100_000_000, 100_000_000]
        result = self.run_rows(make_records(gaps=gaps))
        self.assertEqual(result["status"], "COVERAGE_INVALID")
        self.assertIn("SAMPLING_GAP_EXCEEDS_500MS", result["errors"])

    def test_clock_regression_is_coverage_invalid(self):
        rows = make_records()
        rows[2]["clock_monotonic_ns"] = rows[1]["clock_monotonic_ns"] - 1
        result = self.run_rows(rows)
        self.assertEqual(result["status"], "COVERAGE_INVALID")
        self.assertIn("CLOCK_MONOTONIC_REGRESSION", result["errors"])

    def test_cgroup_freeze_is_unknown_not_positive(self):
        result = self.run_rows(make_records(frozen_at=2))
        self.assertEqual(result["status"], "C2_UNKNOWN")
        self.assertIn("TRIAL_CGROUP_FROZEN", result["warnings"])

    def test_cgroup_drift_is_unknown(self):
        result = self.run_rows(make_records(cgroup_status_at={2: "CGROUP_DRIFT"}))
        self.assertEqual(result["status"], "C2_UNKNOWN")

    def test_missing_cgroup_binding_is_unknown(self):
        rows = make_records()
        rows[0]["trial_pid"] = None
        rows[0]["cgroup_binding_status"] = "NOT_REQUESTED"
        rows[0]["cgroup_path"] = None
        rows[0]["pid_starttime_ticks"] = None
        for row in rows[1:]:
            row["cgroup_read_status"] = "NOT_REQUESTED"
            row["cgroup_frozen"] = None
            row["cgroup_populated"] = None
        result = self.run_rows(rows)
        self.assertEqual(result["status"], "C2_UNKNOWN")

    def test_boot_id_change_is_coverage_invalid(self):
        result = self.run_rows(make_records(boot_id_at={2: "different"}))
        self.assertEqual(result["status"], "COVERAGE_INVALID")
        self.assertIn("BOOT_ID_CHANGED", result["errors"])

    def test_pair_read_span_outlier_is_rejected(self):
        result = self.run_rows(make_records(pair_span=100_000_001))
        self.assertEqual(result["status"], "COVERAGE_INVALID")
        self.assertIn("PAIR_READ_SPAN_EXCEEDS_100MS", result["errors"])

    def test_missing_end_and_malformed_record_fail_closed(self):
        rows = make_records()[:-1]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observer.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows) + "{bad\n",
                            encoding="utf-8")
            parsed, errors = parse_jsonl(path)
            result = analyze_records(parsed, errors)
        self.assertEqual(result["status"], "COVERAGE_INVALID")
        self.assertIn("MALFORMED_JSON_LINE_6", result["errors"])
        self.assertIn("END_RECORD_COUNT_NOT_ONE", result["errors"])

    def test_end_sample_count_is_bound(self):
        rows = make_records()
        rows[-1]["sample_count"] = 3
        result = self.run_rows(rows)
        self.assertEqual(result["status"], "COVERAGE_INVALID")
        self.assertIn("END_SAMPLE_COUNT_MISMATCH", result["errors"])


class ObserverSourceTests(unittest.TestCase):
    def test_observer_is_read_only_and_uses_required_clocks(self):
        source = (ROOT / "tools/rmg-eze4/c2_dual_clock_observer.c").read_text()
        self.assertIn("clock_gettime(CLOCK_MONOTONIC", source)
        self.assertIn("clock_gettime(CLOCK_BOOTTIME", source)
        self.assertIn("/proc/%ld/cgroup", source)
        self.assertIn("cgroup.events", source)
        for forbidden in ("sched_setaffinity", "setpriority", "SCHED_FIFO",
                          "wake_lock", "setenforce", "ioctl("):
            self.assertNotIn(forbidden, source)

    def test_observer_supports_detaching(self):
        source = (ROOT / "tools/rmg-eze4/c2_dual_clock_observer.c").read_text()
        self.assertIn("--detach", source)
        self.assertIn("setsid()", source)
        self.assertIn("dup2(dev_null_fd", source)


if __name__ == "__main__":
    unittest.main()
