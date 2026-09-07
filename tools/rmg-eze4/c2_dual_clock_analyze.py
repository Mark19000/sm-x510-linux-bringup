#!/usr/bin/env python3
"""Fail-closed analyzer for the local C2 dual-clock observer.

The observer records both device clocks in one process.  The analyzer never
uses the absolute ``CLOCK_BOOTTIME - CLOCK_MONOTONIC`` value as evidence: the
initial offset may already contain suspend accumulated before the trial.  It
only considers a positive change in that offset after the first record, and
requires that change to exceed a conservative, data-derived noise margin.

The four externally useful outcomes are:

``NO_SUSPEND_OBSERVED``
    The local timeline is complete, the target cgroup was observed throughout,
    and no above-threshold clock divergence was observed.
``SUSPEND_OBSERVED``
    The same validity gates hold and the relative BOOTTIME divergence crossed
    the detection margin.
``COVERAGE_INVALID``
    The JSONL/timeline is malformed, incomplete, regressed, or has a sampling
    gap beyond the C2 contract.
``C2_UNKNOWN``
    The timeline is structurally usable but cgroup binding/readout is absent,
    ambiguous, frozen, or otherwise cannot exclude a freezer confounder.

The local EZE4 source intake supports the clock interpretation: the kernel's
``include/linux/timekeeping.h`` describes CLOCK_MONOTONIC as excluding suspend
and ``ktime_get_boottime`` as including it; ``kernel/time/posix-stubs.c``
dispatches the two ``clock_gettime`` IDs to those accessors.  The analyzer does
not assume that an absolute offset is zero.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable

SCHEMA_VERSION = "c2-dual-clock-obs.v1"
MAX_GAP_NS = 500_000_000
MAX_PAIR_SPAN_NS = 100_000_000
MIN_INTERVAL_MS = 100
MAX_INTERVAL_MS = 200
MIN_DETECTION_MARGIN_NS = 1_000_000

REQUIRED_FIELDS = {
    "schema",
    "record_type",
    "trial_id",
    "sequence",
    "clock_monotonic_ns",
    "clock_boottime_ns",
    "boottime_minus_monotonic_ns",
    "sampling_gap_ns",
    "elapsed_monotonic_ns",
    "elapsed_boottime_ns",
    "suspend_delta_ns",
    "pair_read_span_ns",
    "process_cpu_ns",
    "boot_id",
    "boot_id_read_status",
    "cgroup_read_status",
    "cgroup_frozen",
    "cgroup_populated",
}


def _is_int(value: Any) -> bool:
    """Return true for JSON integers, excluding booleans."""

    return isinstance(value, int) and not isinstance(value, bool)


def _percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def parse_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse records while retaining all recoverable lines for diagnostics."""

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return [], [f"INPUT_READ_ERROR_{type(exc).__name__}"]

    for line_no, line in enumerate(lines, 1):
        if not line.strip():
            errors.append(f"BLANK_LINE_{line_no}")
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"MALFORMED_JSON_LINE_{line_no}")
            continue
        if not isinstance(item, dict):
            errors.append(f"LINE_{line_no}_NOT_OBJECT")
            continue
        missing = REQUIRED_FIELDS - set(item)
        if missing:
            errors.append(f"LINE_{line_no}_MISSING_{'_'.join(sorted(missing))}")
            continue
        if item.get("schema") != SCHEMA_VERSION:
            errors.append(f"LINE_{line_no}_UNSUPPORTED_SCHEMA_{item.get('schema')}")
        if item.get("record_type") not in {"metadata", "sample", "end"}:
            errors.append(f"LINE_{line_no}_UNKNOWN_RECORD_TYPE")
        records.append(item)
    return records, errors


def _validate_integer_fields(record: dict[str, Any], line_label: str,
                             errors: list[str]) -> None:
    for field in (
        "sequence",
        "clock_monotonic_ns",
        "clock_boottime_ns",
        "pair_read_span_ns",
    ):
        if not _is_int(record.get(field)) or record[field] < 0:
            errors.append(f"{line_label}_{field.upper()}_INVALID")
    for field in (
        "boottime_minus_monotonic_ns",
        "sampling_gap_ns",
        "elapsed_monotonic_ns",
        "elapsed_boottime_ns",
        "suspend_delta_ns",
        "process_cpu_ns",
    ):
        value = record.get(field)
        if value is not None and not _is_int(value):
            errors.append(f"{line_label}_{field.upper()}_INVALID")
        if _is_int(value) and field not in {"boottime_minus_monotonic_ns", "suspend_delta_ns"} and value < 0:
            errors.append(f"{line_label}_{field.upper()}_NEGATIVE")


def _percentile_margin(metadata: dict[str, Any], points: Iterable[dict[str, Any]]) -> tuple[int, dict[str, int | None]]:
    """Derive a positive divergence margin from resolution and read span.

    The pair is sampled as MONOTONIC-before, BOOTTIME, MONOTONIC-after.  The
    measured pair span bounds the clock-pair alignment error.  A minimum 1 ms
    margin is deliberately much larger than the normal nanosecond resolution
    and microsecond-scale vDSO/read-pair cost, while still detecting ordinary
    suspend intervals.  The p95, rather than the largest outlier, keeps one
    scheduler outlier from making all later evidence invisible.
    """

    resolutions = [
        value
        for value in (
            metadata.get("clock_monotonic_resolution_ns"),
            metadata.get("clock_boottime_resolution_ns"),
        )
        if _is_int(value) and value > 0
    ]
    max_resolution = max(resolutions) if resolutions else None
    spans = [
        item["pair_read_span_ns"]
        for item in points
        if _is_int(item.get("pair_read_span_ns")) and item["pair_read_span_ns"] >= 0
    ]
    p95_span = _percentile(spans, 0.95)
    if max_resolution is None:
        return MIN_DETECTION_MARGIN_NS, {
            "max_clock_resolution_ns": None,
            "p95_pair_read_span_ns": p95_span,
        }
    alignment_margin = 2 * (p95_span or 0) + 4 * max_resolution
    threshold = max(MIN_DETECTION_MARGIN_NS, alignment_margin * 4)
    return threshold, {
        "max_clock_resolution_ns": max_resolution,
        "p95_pair_read_span_ns": p95_span,
    }


def analyze_records(records: list[dict[str, Any]], parse_errors: list[str] | None = None) -> dict[str, Any]:
    """Analyze already parsed records; this is also the synthetic-test API."""

    errors = list(parse_errors or [])
    warnings: list[str] = []
    if not records:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "COVERAGE_INVALID",
            "c2_status": "COVERAGE_INVALID",
            "coverage": "COVERAGE_INVALID",
            "sample_count": 0,
            "errors": errors or ["NO_RECORDS"],
            "warnings": warnings,
        }

    for index, record in enumerate(records, 1):
        _validate_integer_fields(record, f"RECORD_{index}", errors)

    sequences = [record.get("sequence") for record in records]
    if any(not _is_int(value) for value in sequences):
        errors.append("SEQUENCE_NON_INTEGER")
    else:
        expected = list(range(len(records)))
        if sequences != expected:
            errors.append("SEQUENCE_NOT_CONTIGUOUS_FROM_ZERO")
        if len(set(sequences)) != len(sequences):
            errors.append("DUPLICATE_SEQUENCE")
        if sequences != sorted(sequences):
            errors.append("SEQUENCE_REGRESSION")

    trial_ids = {record.get("trial_id") for record in records}
    if len(trial_ids) != 1 or None in trial_ids:
        errors.append("TRIAL_ID_MISMATCH")

    metadata_records = [record for record in records if record.get("record_type") == "metadata"]
    end_records = [record for record in records if record.get("record_type") == "end"]
    sample_records = [record for record in records if record.get("record_type") == "sample"]
    if len(metadata_records) != 1:
        errors.append("METADATA_RECORD_COUNT_NOT_ONE")
        metadata: dict[str, Any] = {}
    else:
        metadata = metadata_records[0]
    if len(end_records) != 1:
        errors.append("END_RECORD_COUNT_NOT_ONE")
    end = end_records[0] if len(end_records) == 1 else None
    if records[0].get("record_type") != "metadata":
        errors.append("METADATA_NOT_FIRST")
    if records[-1].get("record_type") != "end":
        errors.append("END_NOT_LAST")
    if end is not None and end.get("termination") != "completed":
        errors.append("END_NOT_COMPLETED")

    points = [*sample_records, *([end] if end is not None else [])]
    timeline = [*([metadata] if metadata else []), *points]
    for left, right in zip(timeline, timeline[1:]):
        left_mono = left.get("clock_monotonic_ns")
        right_mono = right.get("clock_monotonic_ns")
        left_boot = left.get("clock_boottime_ns")
        right_boot = right.get("clock_boottime_ns")
        if all(_is_int(value) for value in (left_mono, right_mono)):
            if right_mono < left_mono:
                errors.append("CLOCK_MONOTONIC_REGRESSION")
        if all(_is_int(value) for value in (left_boot, right_boot)):
            if right_boot < left_boot:
                errors.append("CLOCK_BOOTTIME_REGRESSION")
            if _is_int(right.get("sampling_gap_ns")) and all(
                _is_int(value) for value in (left_mono, right_mono)
            ):
                expected_gap = right_mono - left_mono
                if right["sampling_gap_ns"] != expected_gap:
                    errors.append("SAMPLING_GAP_FIELD_MISMATCH")
        pair_span = right.get("pair_read_span_ns")
        if _is_int(pair_span) and pair_span > MAX_PAIR_SPAN_NS:
            errors.append("PAIR_READ_SPAN_EXCEEDS_100MS")

    gap_values: list[int] = []
    offset_values: list[int] = []
    for record in timeline:
        mono = record.get("clock_monotonic_ns")
        boot = record.get("clock_boottime_ns")
        offset = record.get("boottime_minus_monotonic_ns")
        if _is_int(mono) and _is_int(boot):
            expected_offset = boot - mono
            if offset != expected_offset:
                errors.append("CLOCK_OFFSET_FIELD_MISMATCH")
            offset_values.append(expected_offset)
        if record.get("record_type") in {"sample", "end"}:
            gap = record.get("sampling_gap_ns")
            if not _is_int(gap) or gap < 0:
                errors.append("SAMPLING_GAP_MISSING_OR_INVALID")
            else:
                gap_values.append(gap)
                if gap > MAX_GAP_NS:
                    errors.append("SAMPLING_GAP_EXCEEDS_500MS")

    if len(sample_records) < 2:
        errors.append("INSUFFICIENT_SAMPLES")

    interval_ms = metadata.get("interval_ms")
    if not _is_int(interval_ms) or not MIN_INTERVAL_MS <= interval_ms <= MAX_INTERVAL_MS:
        errors.append("INTERVAL_OUTSIDE_100_200MS")

    for field in ("clock_monotonic_resolution_ns", "clock_boottime_resolution_ns"):
        if not _is_int(metadata.get(field)) or metadata[field] <= 0:
            errors.append(f"{field.upper()}_MISSING_OR_INVALID")

    threshold_ns, threshold_inputs = _percentile_margin(metadata, timeline)
    baseline_offset = offset_values[0] if offset_values else None
    max_offset_change = (
        max((value - baseline_offset for value in offset_values), default=None)
        if baseline_offset is not None
        else None
    )
    for previous_offset, current_offset in zip(offset_values, offset_values[1:]):
        if current_offset - previous_offset < -threshold_ns:
            errors.append("CLOCK_OFFSET_STEP_REGRESSION")
    if max_offset_change is not None and max_offset_change < -threshold_ns:
        errors.append("CLOCK_OFFSET_LARGE_REGRESSION")

    if baseline_offset is not None:
        for record in points:
            mono = record.get("clock_monotonic_ns")
            boot = record.get("clock_boottime_ns")
            if not (_is_int(mono) and _is_int(boot)):
                continue
            expected_elapsed_mono = mono - metadata.get("clock_monotonic_ns", mono)
            expected_elapsed_boot = boot - metadata.get("clock_boottime_ns", boot)
            if record.get("elapsed_monotonic_ns") != expected_elapsed_mono:
                errors.append("ELAPSED_MONOTONIC_FIELD_MISMATCH")
            if record.get("elapsed_boottime_ns") != expected_elapsed_boot:
                errors.append("ELAPSED_BOOTTIME_FIELD_MISMATCH")
            expected_delta = (boot - mono) - baseline_offset
            if record.get("suspend_delta_ns") != expected_delta:
                errors.append("SUSPEND_DELTA_FIELD_MISMATCH")
    if end is not None and end.get("sample_count") != len(sample_records):
        errors.append("END_SAMPLE_COUNT_MISMATCH")

    boot_unknown = metadata.get("boot_id_read_status") != "AVAILABLE"
    baseline_boot_id = metadata.get("boot_id")
    if not isinstance(baseline_boot_id, str) or not baseline_boot_id:
        boot_unknown = True
    for record in points:
        boot_status = record.get("boot_id_read_status")
        record_boot_id = record.get("boot_id")
        if boot_status == "MISMATCH":
            errors.append("BOOT_ID_CHANGED")
        elif boot_status != "AVAILABLE" or not isinstance(record_boot_id, str):
            boot_unknown = True
        elif baseline_boot_id is not None and record_boot_id != baseline_boot_id:
            errors.append("BOOT_ID_CHANGED")

    cgroup_binding_status = metadata.get("cgroup_binding_status")
    cgroup_path = metadata.get("cgroup_path")
    trial_pid = metadata.get("trial_pid")
    pid_starttime_ticks = metadata.get("pid_starttime_ticks")
    cgroup_unknown = (
        not _is_int(trial_pid)
        or trial_pid <= 0
        or cgroup_binding_status != "AVAILABLE"
        or not isinstance(cgroup_path, str)
        or not cgroup_path
        or not _is_int(pid_starttime_ticks)
        or pid_starttime_ticks < 0
    )
    cgroup_frozen = False
    cgroup_not_populated = False
    cgroup_samples = 0
    for record in points:
        if record.get("cgroup_read_status") != "AVAILABLE":
            cgroup_unknown = True
            continue
        frozen = record.get("cgroup_frozen")
        populated = record.get("cgroup_populated")
        if frozen not in (0, 1) or populated not in (0, 1):
            cgroup_unknown = True
            continue
        cgroup_samples += 1
        cgroup_frozen |= frozen == 1
        cgroup_not_populated |= populated == 0
    if cgroup_samples < len(points):
        errors.append("CGROUP_EVENTS_INCOMPLETE_COVERAGE")
    if cgroup_frozen:
        warnings.append("TRIAL_CGROUP_FROZEN")
    if cgroup_not_populated:
        warnings.append("TRIAL_CGROUP_NOT_POPULATED")
    if cgroup_unknown:
        warnings.append("CGROUP_BINDING_OR_READ_UNKNOWN")
    if boot_unknown:
        warnings.append("BOOT_ID_BINDING_OR_READ_UNKNOWN")

    cpu_delta_ns: int | None = None
    if metadata.get("process_cpu_ns") is not None and end is not None:
        if _is_int(metadata.get("process_cpu_ns")) and _is_int(end.get("process_cpu_ns")):
            cpu_delta_ns = end["process_cpu_ns"] - metadata["process_cpu_ns"]
            if cpu_delta_ns < 0:
                warnings.append("PROCESS_CPU_REGRESSION")
                cpu_delta_ns = None
    elapsed_boottime_ns = end.get("elapsed_boottime_ns") if end else None
    cpu_utilization_pct: float | None = None
    if cpu_delta_ns is not None and _is_int(elapsed_boottime_ns) and elapsed_boottime_ns > 0:
        cpu_utilization_pct = round(100.0 * cpu_delta_ns / elapsed_boottime_ns, 6)

    # Cgroup and boot readout uncertainty is a non-affirmative C2 result, but
    # it is distinct from a malformed or gapped clock timeline.  A changed
    # boot ID remains a structural invalidation because the clocks span a
    # reboot boundary.
    coverage_errors = [
        error for error in errors
        if not error.startswith("CGROUP_")
        and error not in {"CGROUP_EVENTS_INCOMPLETE_COVERAGE"}
    ]
    coverage_invalid = bool(coverage_errors)
    suspend_observed = (
        max_offset_change is not None and max_offset_change > threshold_ns
    )
    if coverage_invalid:
        status = "COVERAGE_INVALID"
    elif cgroup_unknown or cgroup_frozen or cgroup_not_populated or boot_unknown:
        status = "C2_UNKNOWN"
    elif suspend_observed:
        status = "SUSPEND_OBSERVED"
    else:
        status = "NO_SUSPEND_OBSERVED"

    return {
        "schema_version": SCHEMA_VERSION,
        "trial_id": next(iter(trial_ids)) if len(trial_ids) == 1 else None,
        "status": status,
        "c2_status": status,
        "coverage": "COVERAGE_INVALID" if coverage_invalid else "COVERAGE_VALID",
        "sample_count": len(sample_records),
        "timeline_count": len(timeline),
        "trial_pid": trial_pid,
        "cgroup_path": cgroup_path,
        "cgroup_sample_count": cgroup_samples,
        "cgroup_frozen": cgroup_frozen,
        "cgroup_not_populated": cgroup_not_populated,
        "suspend_observed": suspend_observed,
        "detection_threshold_ns": threshold_ns,
        "threshold_inputs": threshold_inputs,
        "max_offset_change_ns": max_offset_change,
        "max_sampling_gap_ns": max(gap_values) if gap_values else None,
        "p95_sampling_gap_ns": _percentile(gap_values, 0.95),
        "process_cpu_delta_ns": cpu_delta_ns,
        "process_cpu_utilization_pct": cpu_utilization_pct,
        "errors": errors,
        "warnings": warnings,
    }


def analyze(path: Path) -> dict[str, Any]:
    records, errors = parse_jsonl(path)
    return analyze_records(records, errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    result = analyze(Path(args.jsonl))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if result["status"] in {"NO_SUSPEND_OBSERVED", "SUSPEND_OBSERVED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
