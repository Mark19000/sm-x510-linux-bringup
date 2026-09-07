#!/usr/bin/env python3
"""Offline analyzer for C2-OBS-01 JSONL observations."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

SCHEMA_VERSION = "c2-obs-01.v1"
MAX_GAP_NS = 500_000_000


def canonical_identity(root: Path) -> dict[str, str]:
    schema = json.loads((root / "docs/rmg-eze4/phase_j2_observation_schema_v2.json").read_text())
    props = schema["properties"]["artifact_identity"]["properties"]
    return {
        "model": props["device_model"]["const"],
        "device": props["device_name"]["const"],
        "build_fingerprint": props["build_fingerprint"]["const"],
        "build_incremental": props["incremental_version"]["const"],
        "kernel_release": props["kernel_identity"]["const"],
    }


def percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(fraction * len(ordered)) - 1]


def parse_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    records, errors = [], []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"MALFORMED_JSON_LINE_{line_no}")
            continue
        required = {"schema_version", "trial_id", "sequence", "timestamp_monotonic_ns",
                    "timestamp_boottime_seconds", "timestamp_wall_utc", "source", "measurement", "value",
                    "read_status", "read_duration_ns"}
        missing = required - item.keys() if isinstance(item, dict) else required
        if missing:
            errors.append(f"LINE_{line_no}_MISSING_{'_'.join(sorted(missing))}")
            continue
        if item["schema_version"] != SCHEMA_VERSION:
            errors.append(f"LINE_{line_no}_UNSUPPORTED_SCHEMA_{item['schema_version']}")
        records.append(item)
    return records, errors


def analyze(path: Path, root: Path) -> dict:
    # C2-OBS-02 runs locally on the device and emits a different, richer
    # schema.  Keep the legacy host collector intact, but route its JSONL
    # through the dual-clock analyzer when the schema advertises that source.
    try:
        first_line = next(
            line for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        first_record = json.loads(first_line)
    except (OSError, UnicodeError, StopIteration, json.JSONDecodeError):
        first_record = None
    if isinstance(first_record, dict) and first_record.get("schema") == "c2-dual-clock-obs.v1":
        from c2_dual_clock_analyze import analyze as analyze_dual_clock

        return analyze_dual_clock(path)
    records, errors = parse_jsonl(path)
    if not records:
        return {"c2_status": "C2_UNKNOWN", "coverage": "COVERAGE_INVALID", "errors": errors or ["NO_RECORDS"]}
    sequences = [r["sequence"] for r in records]
    if len(sequences) != len(set(sequences)):
        errors.append("DUPLICATE_SEQUENCE")
    if sequences != sorted(sequences):
        errors.append("SEQUENCE_REGRESSION")
    if len({r["trial_id"] for r in records}) != 1:
        errors.append("TRIAL_ID_MISMATCH")
    stamps = [r["timestamp_monotonic_ns"] for r in records]
    if any(not isinstance(v, int) for v in stamps) or any(b < a for a, b in zip(stamps, stamps[1:])):
        errors.append("MONOTONIC_TIMESTAMP_REGRESSION")

    metadata_records = [r for r in records if r["measurement"] == "metadata"]
    if len(metadata_records) != 1:
        errors.append("METADATA_RECORD_COUNT_NOT_ONE")
        metadata = {}
    else:
        metadata = metadata_records[0]["value"] or {}
    expected = canonical_identity(root)
    observed = metadata.get("metadata", {})
    for key, wanted in expected.items():
        entry = observed.get(key, {})
        if entry.get("status") != "AVAILABLE" or entry.get("value") != wanted:
            errors.append(f"IDENTITY_MISMATCH_OR_UNAVAILABLE_{key}")

    heartbeats = [r for r in records if r["measurement"] == "heartbeat"]
    heartbeat_stamps = [r["timestamp_monotonic_ns"] for r in heartbeats if isinstance(r["timestamp_monotonic_ns"], int)]
    gaps = [b - a for a, b in zip(heartbeat_stamps, heartbeat_stamps[1:])]
    max_gap = max(gaps) if gaps else None
    if len(heartbeats) < 2 or max_gap is None or max_gap > MAX_GAP_NS:
        errors.append("COVERAGE_GAP_EXCEEDS_500MS_OR_INSUFFICIENT")
    if any(r["read_status"] != "AVAILABLE" for r in heartbeats):
        errors.append("HEARTBEAT_READ_FAILURE")

    interfaces = metadata.get("interfaces", {})
    cgroup = interfaces.get("trial_cgroup_events", {})
    if cgroup.get("status") != "AVAILABLE":
        errors.append(f"CGROUP_EVENTS_{cgroup.get('status', 'MISSING')}")
    cgroup_samples = [r for r in records if r["source"] == "trial_cgroup_events"]
    if len(cgroup_samples) < len(heartbeats) or any(r["read_status"] != "AVAILABLE" for r in cgroup_samples):
        errors.append("CGROUP_EVENTS_INCOMPLETE_COVERAGE")
    power_sources = [name for name in ("suspend_success", "wakeup_count")
                     if interfaces.get(name, {}).get("status") == "AVAILABLE"]
    power_samples = [r for r in records if r["source"] in power_sources]
    if not power_sources or all(
        len([r for r in power_samples if r["source"] == name and r["read_status"] == "AVAILABLE"]) < len(heartbeats)
        for name in power_sources
    ):
        errors.append("POWER_TRANSITION_SOURCE_INCOMPLETE_COVERAGE")

    freeze_detected = False
    power_transition_detected = False
    ambiguous = False
    counter_values: dict[str, list[int]] = {"wakeup_count": [], "suspend_success": []}
    for r in records:
        if r["source"] == "trial_cgroup_events" and r["read_status"] == "AVAILABLE":
            text = str(r["value"] or "")
            for line in text.splitlines():
                if line.strip() in {"frozen 1", "populated 0"}:
                    freeze_detected = True
        if r["source"] in {"wakeup_count", "suspend_success"} and r["read_status"] == "AVAILABLE":
            try:
                counter_values[r["source"]].append(int(str(r["value"]).strip()))
            except ValueError:
                errors.append(f"NON_INTEGER_COUNTER_{r['source']}")
        if r["read_status"] == "AMBIGUOUS":
            ambiguous = True

    for values in counter_values.values():
        if values and any(value != values[0] for value in values[1:]):
            power_transition_detected = True

    # Device boottime includes suspend while host monotonic measures collector
    # scheduling. A large positive divergence is suspicious, never proof of
    # absence; retain it as C2-present power discontinuity evidence.
    timed = [r for r in heartbeats if isinstance(r.get("timestamp_boottime_seconds"), (int, float))]
    for first, second in zip(timed, timed[1:]):
        host_delta = (second["timestamp_monotonic_ns"] - first["timestamp_monotonic_ns"]) / 1e9
        boot_delta = second["timestamp_boottime_seconds"] - first["timestamp_boottime_seconds"]
        if boot_delta < 0:
            errors.append("BOOTTIME_TIMESTAMP_REGRESSION")
        elif boot_delta - host_delta > 0.5:
            power_transition_detected = True

    coverage = "COVERAGE_INVALID" if errors else "COVERAGE_VALID"
    if freeze_detected or power_transition_detected:
        c2_status = "C2_PRESENT"
    elif errors or ambiguous:
        c2_status = "C2_UNKNOWN"
    else:
        c2_status = "C2_ABSENT_FOR_OBSERVED_INTERVAL"
    return {
        "schema_version": SCHEMA_VERSION,
        "trial_id": records[0]["trial_id"],
        "c2_status": c2_status,
        "coverage": coverage,
        "requested_interval_ms": metadata.get("requested_interval_ms"),
        "sample_count": len(heartbeats),
        "cgroup_sample_count": len(cgroup_samples),
        "power_sample_count": len(power_samples),
        "max_gap_ns": max_gap,
        "actual_interval_mean_ns": round(sum(gaps) / len(gaps)) if gaps else None,
        "p50_gap_ns": percentile(gaps, 0.50),
        "p95_gap_ns": percentile(gaps, 0.95),
        "p99_gap_ns": percentile(gaps, 0.99),
        "power_transition_detected": power_transition_detected,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("jsonl")
    p.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    p.add_argument("--output")
    args = p.parse_args(argv)
    result = analyze(Path(args.jsonl), Path(args.repo_root))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if result["coverage"] == "COVERAGE_VALID" else 1


if __name__ == "__main__":
    sys.exit(main())
