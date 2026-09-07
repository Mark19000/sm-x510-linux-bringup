#!/usr/bin/env python3
"""Offline analyzer for C3-OBS-01 JSONL observations.

The analyzer is intentionally conservative.  It can report that a thermal,
frequency, or CPU signal was observed, but it never turns a missing or
malformed signal into evidence that C3 was absent.  A C3 presence verdict is
only emitted when identity, coverage, and the relevant readings are all
valid.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path


SCHEMA_VERSION = "c3-obs-01.v1"
# The runtime critical path requires the same conservative gap bound used by
# C2.  The older J2 template allowed 2500 ms for a thermal-only monitor, but a
# combined C2/C3/P02 trial must not silently accept a >500 ms blind interval.
MAX_GAP_NS = 500_000_000
TEMPLATE_MAX_GAP_NS = 2_500_000_000


def canonical_identity(root: Path) -> dict[str, str]:
    schema = json.loads(
        (root / "docs/rmg-eze4/phase_j2_observation_schema_v2.json").read_text(
            encoding="utf-8"))
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


def parse_temperature(value: object) -> float | None:
    """Parse a thermal sysfs reading and return degrees Celsius.

    Linux thermal sysfs exposes integer millidegrees Celsius.  Human-readable
    ``42C``/``42.0 C`` forms are accepted for replay fixtures, while a bare
    decimal is still interpreted as millidegrees to avoid mixing units.
    """

    text = str(value).strip()
    match = re.fullmatch(r"([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))\s*(m?c)?",
                         text, re.IGNORECASE)
    if not match:
        return None
    try:
        number = float(match.group(1))
    except ValueError:
        return None
    unit = (match.group(2) or "mc").lower()
    return number if unit == "c" else number / 1000.0


def parse_frequency(value: object, default_unit: str = "khz") -> int | None:
    """Parse a cpufreq value and normalize it to integer Hz.

    ``scaling_*_freq`` and ``cpuinfo_cur_freq`` are normally kHz.  A suffix is
    accepted in synthetic fixtures and makes the unit explicit.
    """

    text = str(value).strip().lower().replace(" ", "")
    match = re.fullmatch(r"([+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))(hz|khz|mhz|ghz)?",
                         text)
    if not match:
        return None
    try:
        number = float(match.group(1))
    except ValueError:
        return None
    unit = (match.group(2) or default_unit).lower()
    multiplier = {"hz": 1, "khz": 1_000, "mhz": 1_000_000,
                  "ghz": 1_000_000_000}.get(unit)
    if multiplier is None or number < 0:
        return None
    result = number * multiplier
    return int(result) if result.is_integer() else None


def parse_cpu_list(value: object) -> set[int] | None:
    """Parse Linux CPU-list syntax (for example ``0-3,6``)."""

    text = str(value).strip()
    if not text or text.lower() == "none":
        return set() if text.lower() == "none" else None
    result: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if not re.fullmatch(r"[0-9]+(?:-[0-9]+)?", part):
            return None
        if "-" in part:
            first, last = (int(item) for item in part.split("-", 1))
            if last < first:
                return None
            result.update(range(first, last + 1))
        else:
            result.add(int(part))
    return result


def parse_processor_from_stat(value: object) -> int | None:
    """Extract field 39 (processor) from Linux ``/proc/<pid>/stat``.

    The comm field is parenthesized and may itself contain spaces or ``)``;
    using the final close parenthesis avoids the common split-at-first-error.
    """

    text = str(value).strip()
    close = text.rfind(")")
    if close < 0:
        return None
    tail = text[close + 1:].strip().split()
    # tail[0] is field 3 (state), so field 39 is tail[36].
    if len(tail) <= 36 or not re.fullmatch(r"[0-9]+", tail[36]):
        return None
    return int(tail[36])


def parse_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    errors: list[str] = []
    required = {
        "schema_version", "trial_id", "sequence", "timestamp_monotonic_ns",
        "timestamp_boottime_seconds", "timestamp_wall_utc", "source",
        "measurement", "value", "read_status", "read_duration_ns",
    }
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"MALFORMED_JSON_LINE_{line_no}")
            continue
        if not isinstance(item, dict):
            errors.append(f"LINE_{line_no}_NOT_OBJECT")
            continue
        missing = required - item.keys()
        if missing:
            errors.append(f"LINE_{line_no}_MISSING_{'_'.join(sorted(missing))}")
            continue
        if item["schema_version"] != SCHEMA_VERSION:
            errors.append(f"LINE_{line_no}_UNSUPPORTED_SCHEMA_{item['schema_version']}")
        records.append(item)
    return records, errors


def _descriptor_unit(descriptor: dict, default: str) -> str:
    value = descriptor.get("unit")
    return value if isinstance(value, str) and value else default


def _metadata_parts(metadata_record: dict) -> tuple[dict, dict]:
    value = metadata_record.get("value") or {}
    if not isinstance(value, dict):
        return {}, {}
    metadata = value.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    interfaces = metadata.get("interfaces")
    if not isinstance(interfaces, dict):
        interfaces = value.get("interfaces")
    if not isinstance(interfaces, dict):
        interfaces = {}
    # Keep collector-level controls (sample_sources, declared_cpus and the
    # requested cadence) alongside the nested getprop map.  This lets replay
    # fixtures use either the exact collector shape or a compact equivalent.
    merged = dict(metadata)
    for key, item in value.items():
        if key not in {"metadata", "interfaces"}:
            merged.setdefault(key, item)
    return merged, interfaces


def _source_descriptors(interfaces: dict) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict], dict]:
    thermal: dict[str, dict] = {}
    frequency: dict[str, dict] = {}
    static: dict[str, dict] = {}
    zones = interfaces.get("thermal_zones", {})
    if isinstance(zones, dict):
        for zone_name, zone in zones.items():
            if not isinstance(zone, dict):
                continue
            descriptor = zone.get("temperature")
            if isinstance(descriptor, dict):
                thermal[f"thermal:{zone_name}:temperature"] = descriptor
    policies = interfaces.get("cpufreq_policies", {})
    if isinstance(policies, dict):
        for policy_name, policy in policies.items():
            if not isinstance(policy, dict):
                continue
            for key in ("effective_freq", "max_freq"):
                descriptor = policy.get(key)
                if isinstance(descriptor, dict):
                    frequency[f"cpufreq:{policy_name}:{key}"] = descriptor
    raw_static = interfaces.get("static_sources", {})
    if isinstance(raw_static, dict):
        static = {name: descriptor for name, descriptor in raw_static.items()
                  if isinstance(descriptor, dict)}
    trial_cpu = interfaces.get("trial_cpu")
    if isinstance(trial_cpu, dict):
        static["trial_cpu"] = trial_cpu
    return thermal, frequency, static, zones if isinstance(zones, dict) else {}


def _critical_trip_thresholds(zones: dict) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    for zone_name, zone in zones.items():
        if not isinstance(zone, dict):
            continue
        trips = zone.get("trip_points", {})
        if not isinstance(trips, dict):
            continue
        for index, trip in trips.items():
            if not isinstance(trip, dict):
                continue
            type_desc = trip.get("type", {})
            temp_desc = trip.get("temp", {})
            trip_type = str(type_desc.get("initial_value") or "").lower()
            if "critical" not in trip_type:
                continue
            temp = parse_temperature(temp_desc.get("initial_value"))
            if temp is not None:
                thresholds[f"{zone_name}:{index}"] = temp
    return thresholds


def _initial_max_frequencies(policies: dict) -> dict[str, int]:
    result: dict[str, int] = {}
    for policy_name, policy in policies.items():
        if not isinstance(policy, dict):
            continue
        desc = policy.get("max_freq", {})
        if not isinstance(desc, dict):
            continue
        value = parse_frequency(desc.get("initial_value"),
                                _descriptor_unit(desc, "khz"))
        if value is not None:
            result[policy_name] = value
    return result


def analyze(path: Path, root: Path) -> dict:
    records, errors = parse_jsonl(path)
    if not records:
        return {
            "schema_version": SCHEMA_VERSION,
            "c3_status": "C3_BLOCKED",
            "classification": "C3_UNKNOWN",
            "coverage": "COVERAGE_INVALID",
            "errors": errors or ["NO_RECORDS"],
        }

    sequences = [record.get("sequence") for record in records]
    if len(sequences) != len(set(sequences)):
        errors.append("DUPLICATE_SEQUENCE")
    if sequences != sorted(sequences):
        errors.append("SEQUENCE_REGRESSION")
    trial_ids = {record.get("trial_id") for record in records}
    if len(trial_ids) != 1:
        errors.append("TRIAL_ID_MISMATCH")
    stamps = [record.get("timestamp_monotonic_ns") for record in records]
    if any(not isinstance(value, int) or isinstance(value, bool) for value in stamps):
        errors.append("NON_INTEGER_MONOTONIC_TIMESTAMP")
    elif any(second < first for first, second in zip(stamps, stamps[1:])):
        errors.append("MONOTONIC_TIMESTAMP_REGRESSION")

    metadata_records = [record for record in records if record.get("measurement") == "metadata"]
    if len(metadata_records) != 1:
        errors.append("METADATA_RECORD_COUNT_NOT_ONE")
        metadata, interfaces = {}, {}
    else:
        metadata, interfaces = _metadata_parts(metadata_records[0])

    try:
        expected = canonical_identity(root)
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        expected = {}
        errors.append(f"CANONICAL_IDENTITY_UNAVAILABLE_{type(exc).__name__}")
    observed = metadata.get("metadata", {}) if isinstance(metadata.get("metadata"), dict) else metadata
    # ``metadata`` is the nested getprop map in collector output.  A fixture
    # may place it directly in the metadata record; accept both forms.
    for key, wanted in expected.items():
        entry = observed.get(key, {}) if isinstance(observed, dict) else {}
        if not isinstance(entry, dict) or entry.get("status") != "AVAILABLE" or entry.get("value") != wanted:
            errors.append(f"IDENTITY_MISMATCH_OR_UNAVAILABLE_{key}")

    heartbeats = [record for record in records
                  if record.get("measurement") == "heartbeat"]
    heartbeat_stamps = [record.get("timestamp_monotonic_ns") for record in heartbeats
                        if isinstance(record.get("timestamp_monotonic_ns"), int)
                        and not isinstance(record.get("timestamp_monotonic_ns"), bool)]
    gaps = [second - first for first, second in zip(heartbeat_stamps, heartbeat_stamps[1:])]
    max_gap = max(gaps) if gaps else None
    if len(heartbeats) < 2 or max_gap is None or max_gap > MAX_GAP_NS:
        errors.append("COVERAGE_GAP_EXCEEDS_500MS_OR_INSUFFICIENT")
    if any(record.get("read_status") != "AVAILABLE" for record in heartbeats):
        errors.append("HEARTBEAT_READ_FAILURE")

    thermal, frequency, static, zones = _source_descriptors(interfaces)
    sample_sources = metadata.get("sample_sources", [])
    if not isinstance(sample_sources, list):
        sample_sources = []
    all_expected = {name: descriptor for name, descriptor in
                    {**thermal, **frequency, **static}.items()
                    if descriptor.get("sample") and descriptor.get("path")}
    if sample_sources:
        # Keep only names actually bound by discovery; an unbound name in the
        # metadata is itself evidence of an incomplete discovery contract.
        for name in sample_sources:
            if name not in all_expected:
                errors.append(f"SAMPLE_SOURCE_NOT_BOUND_{name}")
        all_expected = {name: all_expected[name] for name in sample_sources
                        if name in all_expected}
    if not thermal:
        errors.append("THERMAL_ZONE_SOURCE_MISSING")
    if not frequency:
        errors.append("CPUFREQ_SOURCE_MISSING")

    raw_by_source: dict[str, list[dict]] = {}
    for record in records:
        if record.get("measurement") == "raw_read":
            raw_by_source.setdefault(str(record.get("source")), []).append(record)

    malformed_sources: set[str] = set()
    unavailable_sources: set[str] = set()
    parsed_temperatures: dict[str, list[tuple[int, float]]] = {}
    parsed_frequencies: dict[str, list[tuple[int, int]]] = {}
    parsed_processors: list[tuple[int, int]] = []
    for source, descriptor in all_expected.items():
        source_records = raw_by_source.get(source, [])
        if len(source_records) < len(heartbeats):
            errors.append(f"SOURCE_INCOMPLETE_COVERAGE_{source}")
        for record in source_records:
            status = record.get("read_status")
            if status != "AVAILABLE":
                unavailable_sources.add(source)
                errors.append(f"SOURCE_READ_{status}_{source}")
                if source.startswith("thermal:"):
                    errors.append(f"THERMAL_SENSOR_DISAPPEARED_{source}")
                continue
            timestamp = record.get("timestamp_monotonic_ns")
            value = record.get("value")
            parsed: int | float | None = None
            if source.startswith("thermal:"):
                parsed = parse_temperature(value)
                if parsed is not None and isinstance(timestamp, int):
                    parsed_temperatures.setdefault(source, []).append((timestamp, parsed))
            elif source.startswith("cpufreq:"):
                parsed = parse_frequency(value, _descriptor_unit(descriptor, "khz"))
                if parsed is not None and isinstance(timestamp, int):
                    parsed_frequencies.setdefault(source, []).append((timestamp, parsed))
            elif source == "trial_cpu":
                parsed = parse_processor_from_stat(value)
                if parsed is not None and isinstance(timestamp, int):
                    parsed_processors.append((timestamp, parsed))
            elif source in {"cpu_online", "cpu_present"}:
                parsed = parse_cpu_list(value)
            if parsed is None:
                malformed_sources.add(source)
                errors.append(f"MALFORMED_READING_{source}")

    # A critical thermal excursion is meaningful only if all identity and
    # coverage checks are sound.  Otherwise the safe answer is UNKNOWN.
    thermal_thresholds = _critical_trip_thresholds(zones)
    thermal_excursions = 0
    for source, values in parsed_temperatures.items():
        zone_name = source.split(":")[1] if ":" in source else ""
        thresholds = [value for key, value in thermal_thresholds.items()
                      if key.startswith(zone_name + ":")]
        if thresholds:
            thermal_excursions += sum(1 for _stamp, temp in values
                                      if any(temp >= threshold for threshold in thresholds))

    policies = interfaces.get("cpufreq_policies", {})
    initial_max = _initial_max_frequencies(policies if isinstance(policies, dict) else {})
    frequency_clamps = 0
    for source, values in parsed_frequencies.items():
        parts = source.split(":")
        if len(parts) < 3 or parts[2] != "max_freq":
            continue
        policy_name = parts[1]
        baseline = initial_max.get(policy_name)
        if baseline is not None:
            frequency_clamps += sum(1 for _stamp, value in values if value < baseline)

    migration_count = 0
    for (_first_stamp, first), (_second_stamp, second) in zip(parsed_processors, parsed_processors[1:]):
        if first != second:
            migration_count += 1
    declared_cpus = metadata.get("declared_cpus")
    declared_set: set[int] | None = None
    if declared_cpus is not None:
        declared_set = (parse_cpu_list(declared_cpus) if isinstance(declared_cpus, str)
                        else set(declared_cpus) if isinstance(declared_cpus, list)
                        else None)
        if declared_set is None:
            errors.append("MALFORMED_DECLARED_CPU_STRATUM")
    out_of_stratum = 0
    if declared_set is not None:
        out_of_stratum = sum(1 for _stamp, cpu in parsed_processors if cpu not in declared_set)
        if out_of_stratum:
            errors.append("CPU_MIGRATION_OUTSIDE_DECLARED_STRATUM")

    identity_errors = [error for error in errors if error.startswith("IDENTITY_")]
    coverage_errors = [error for error in errors if error.startswith("COVERAGE_")
                       or error in {"HEARTBEAT_READ_FAILURE", "MONOTONIC_TIMESTAMP_REGRESSION",
                                    "NON_INTEGER_MONOTONIC_TIMESTAMP"}]
    thermal_bound = bool(thermal) and all(
        isinstance(zone, dict)
        and isinstance(zone.get("type"), dict)
        and zone.get("type", {}).get("status") == "AVAILABLE"
        and isinstance(zone.get("temperature"), dict)
        and zone.get("temperature", {}).get("status") == "AVAILABLE"
        and bool(zone.get("trip_points"))
        for zone in zones.values()) if zones else False
    frequency_bound = bool(frequency) and any(
        name.endswith(":effective_freq") and descriptor.get("status") == "AVAILABLE"
        for name, descriptor in frequency.items())
    cpu_bound = "trial_cpu" in static and static["trial_cpu"].get("status") == "AVAILABLE"
    complete = (not errors and thermal_bound and frequency_bound and cpu_bound
                and bool(parsed_temperatures) and bool(parsed_frequencies)
                and len(parsed_processors) >= len(heartbeats))

    if identity_errors or not records or (not thermal and not frequency):
        c3_status = "C3_BLOCKED"
    elif complete:
        c3_status = "C3_OBSERVABLE"
    else:
        c3_status = "C3_PARTIAL"

    clean_for_positive = not errors and bool(heartbeat_stamps)
    if clean_for_positive and (thermal_excursions or frequency_clamps or out_of_stratum):
        classification = "C3_PRESENT"
    elif complete:
        classification = "C3_ABSENT"
    else:
        classification = "C3_UNKNOWN"

    return {
        "schema_version": SCHEMA_VERSION,
        "trial_id": next(iter(trial_ids)) if len(trial_ids) == 1 else None,
        "c3_status": c3_status,
        "classification": classification,
        "coverage": "COVERAGE_INVALID" if errors else "COVERAGE_VALID",
        "requested_interval_ms": metadata.get("requested_interval_ms"),
        "sample_count": len(heartbeats),
        "thermal_sample_count": sum(len(values) for values in parsed_temperatures.values()),
        "frequency_sample_count": sum(len(values) for values in parsed_frequencies.values()),
        "cpu_sample_count": len(parsed_processors),
        "thermal_zone_count": len(zones),
        "mapped_thermal_zone_count": sum(1 for zone in zones.values()
                                          if isinstance(zone, dict)
                                          and zone.get("temperature", {}).get("status") == "AVAILABLE"),
        "frequency_policy_count": len(policies) if isinstance(policies, dict) else 0,
        "max_gap_ns": max_gap,
        "canonical_template_max_gap_ns": TEMPLATE_MAX_GAP_NS,
        "actual_interval_mean_ns": round(sum(gaps) / len(gaps)) if gaps else None,
        "p50_gap_ns": percentile(gaps, 0.50),
        "p95_gap_ns": percentile(gaps, 0.95),
        "p99_gap_ns": percentile(gaps, 0.99),
        "thermal_excursion_count": thermal_excursions,
        "frequency_clamp_count": frequency_clamps,
        "migration_count": migration_count,
        "migration_outside_declared_stratum_count": out_of_stratum,
        "thermal_sources": sorted(thermal),
        "frequency_sources": sorted(frequency),
        "cpu_source_available": cpu_bound,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    result = analyze(Path(args.jsonl), Path(args.repo_root))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if result["coverage"] == "COVERAGE_VALID" and result["c3_status"] != "C3_BLOCKED" else 1


if __name__ == "__main__":
    sys.exit(main())
