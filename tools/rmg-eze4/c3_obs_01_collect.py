#!/usr/bin/env python3
"""Read-only host collector for C3 thermal/frequency/CPU observations.

The collector deliberately mirrors the small JSONL/ADB design of
``c2_obs_01_collect.py``.  Discovery is performed once and the sampling loop
only reads paths that were discovered on the target.  No governor, affinity,
thermal policy, trip point, or device state is changed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from c2_obs_01_collect import (  # type: ignore[import-not-found]
    AdbReader,
    TRIAL_RE,
    classify_read,
    read_metadata,
)


COLLECTOR_VERSION = "1.0.0"
SCHEMA_VERSION = "c3-obs-01.v1"
THERMAL_ROOT = "/sys/class/thermal"
CPUFREQ_ROOT = "/sys/devices/system/cpu/cpufreq"
STATIC_PATHS = {
    "cpu_online": "/sys/devices/system/cpu/online",
    "cpu_present": "/sys/devices/system/cpu/present",
}
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
ZONE_RE = re.compile(r"^thermal_zone[0-9]+$")
POLICY_RE = re.compile(r"^policy[0-9]+$")
TRIP_RE = re.compile(r"^trip_point_([0-9]+)_(temp|type)$")


def _descriptor(path: str | None, status: str, value: str | None,
                duration_ns: int | None, *, sample: bool = False,
                unit: str | None = None) -> dict:
    result = {
        "path": path,
        "status": status,
        "initial_value": value,
        "read_duration_ns": duration_ns,
        "sample": sample,
    }
    if unit is not None:
        result["unit"] = unit
    return result


def _safe_child(root: str, child: str) -> str | None:
    """Join a discovered sysfs child without permitting path traversal."""

    if not NAME_RE.fullmatch(child) or child in {".", ".."}:
        return None
    return f"{root.rstrip('/')}/{child}"


def list_directory(reader: AdbReader, path: str) -> tuple[str, list[str], int]:
    """List one read-only device directory and retain its read status."""

    started = time.monotonic_ns()
    rc, out, err = reader.run(["shell", "ls", "-1", "--", path])
    duration = time.monotonic_ns() - started
    if rc != 0:
        return classify_read(rc, err), [], duration
    # Toybox ls may append a slash to directories.  Keep only names; all
    # later paths are rebuilt from validated names rather than trusting output.
    names = [line.strip().rstrip("/") for line in out.splitlines() if line.strip()]
    return "AVAILABLE", names, duration


def _list_with_callback(list_dir: Callable[[str], tuple[str, list[str], int]],
                        path: str) -> tuple[str, list[str], int | None]:
    try:
        status, names, duration = list_dir(path)
    except (OSError, ValueError, TypeError):
        return "AMBIGUOUS", [], None
    if status != "AVAILABLE":
        return status, [], duration
    return status, [name for name in names if isinstance(name, str)], duration


def _read_descriptor(read_path: Callable[[str], tuple[str, str | None, int]],
                     path: str | None, *, sample: bool = False,
                     unit: str | None = None) -> dict:
    if path is None:
        return _descriptor(None, "UNSUPPORTED", None, None, sample=sample, unit=unit)
    try:
        status, value, duration = read_path(path)
    except (OSError, ValueError, TypeError):
        return _descriptor(path, "AMBIGUOUS", None, None, sample=sample, unit=unit)
    return _descriptor(path, status, value, duration, sample=sample, unit=unit)


def _trip_points(read_path: Callable[[str], tuple[str, str | None, int]],
                 list_dir: Callable[[str], tuple[str, list[str], int]],
                 zone_path: str) -> tuple[str, dict[str, dict]]:
    status, names, _ = _list_with_callback(list_dir, zone_path)
    trips: dict[str, dict] = {}
    if status != "AVAILABLE":
        return status, trips
    found: dict[str, dict[str, str]] = {}
    for name in names:
        match = TRIP_RE.fullmatch(name)
        if not match:
            continue
        index, field = match.groups()
        found.setdefault(index, {})[field] = name
    for index in sorted(found, key=lambda item: int(item)):
        fields = found[index]
        trip: dict[str, dict] = {}
        for field in ("temp", "type"):
            path = _safe_child(zone_path, fields.get(field, ""))
            trip[field] = _read_descriptor(read_path, path, unit="millidegrees_celsius"
                                            if field == "temp" else None)
        trips[index] = trip
    return status, trips


def discover_sources(
    read_path: Callable[[str], tuple[str, str | None, int]],
    list_dir: Callable[[str], tuple[str, list[str], int]] | None = None,
    trial_pid: int | None = None,
) -> dict:
    """Discover EZE4 thermal, cpufreq, and optional trial-CPU sources.

    ``read_path`` and ``list_dir`` are injectable so the complete discovery
    contract can be replayed in unit tests without a device.  The returned
    structure retains missing and permission-denied sources instead of hiding
    them, which is important for avoiding false C3-absence claims.
    """

    # Keep the C2-style ``discover_sources(read_path, trial_pid)`` call shape
    # useful for small replay tests while allowing C3 to inject directory
    # discovery as its second argument.
    if list_dir is not None and not callable(list_dir):
        if trial_pid is None and isinstance(list_dir, int):
            trial_pid = list_dir
            list_dir = None
        else:
            list_dir = None
    if list_dir is None:
        list_dir = lambda _path: ("UNAVAILABLE", [], 0)

    thermal_root_status, zones, thermal_root_duration = _list_with_callback(
        list_dir, THERMAL_ROOT)
    thermal_zones: dict[str, dict] = {}
    if thermal_root_status == "AVAILABLE":
        for name in sorted({n for n in zones if ZONE_RE.fullmatch(n)},
                           key=lambda item: int(item.rsplit("e", 1)[-1])):
            zone_path = _safe_child(THERMAL_ROOT, name)
            assert zone_path is not None
            trip_status, trips = _trip_points(read_path, list_dir, zone_path)
            thermal_zones[name] = {
                "path": zone_path,
                "discovery_status": trip_status,
                "type": _read_descriptor(read_path, _safe_child(zone_path, "type")),
                "temperature": _read_descriptor(
                    read_path, _safe_child(zone_path, "temp"),
                    sample=True, unit="millidegrees_celsius"),
                "trip_points": trips,
            }

    cpufreq_root_status, policies, cpufreq_root_duration = _list_with_callback(
        list_dir, CPUFREQ_ROOT)
    cpufreq_policies: dict[str, dict] = {}
    if cpufreq_root_status == "AVAILABLE":
        for name in sorted({n for n in policies if POLICY_RE.fullmatch(n)},
                           key=lambda item: int(item.rsplit("y", 1)[-1])):
            policy_path = _safe_child(CPUFREQ_ROOT, name)
            assert policy_path is not None
            listed_status, listed_names, _ = _list_with_callback(list_dir, policy_path)

            def path_for(field: str) -> str | None:
                if listed_status != "AVAILABLE":
                    # The path is still deterministic, and retaining it lets
                    # the analyzer report the exact failed source.
                    return _safe_child(policy_path, field)
                if field not in listed_names:
                    return None
                return _safe_child(policy_path, field)

            cur = _read_descriptor(read_path, path_for("scaling_cur_freq"),
                                   sample=True, unit="khz")
            cur_name = "scaling_cur_freq"
            if cur["status"] != "AVAILABLE":
                fallback = _read_descriptor(read_path, path_for("cpuinfo_cur_freq"),
                                             sample=True, unit="khz")
                if fallback["status"] == "AVAILABLE":
                    cur = fallback
                    cur_name = "cpuinfo_cur_freq"
            cpufreq_policies[name] = {
                "path": policy_path,
                "discovery_status": listed_status,
                "affected_cpus": _read_descriptor(
                    read_path, path_for("affected_cpus")),
                "related_cpus": _read_descriptor(
                    read_path, path_for("related_cpus")),
                "governor": _read_descriptor(
                    read_path, path_for("scaling_governor")),
                "min_freq": _read_descriptor(
                    read_path, path_for("scaling_min_freq"), unit="khz"),
                "max_freq": _read_descriptor(
                    read_path, path_for("scaling_max_freq"), sample=True, unit="khz"),
                "effective_freq": cur,
                "effective_freq_name": cur_name,
            }

    # CPU topology is effectively static for this baseline and is retained at
    # discovery time.  Re-reading both files every 200 ms added two ADB
    # round-trips without improving migration observability.
    static_sources = {
        name: _read_descriptor(read_path, path, sample=False)
        for name, path in STATIC_PATHS.items()
    }

    if trial_pid is None:
        trial_cpu = _descriptor(None, "UNSUPPORTED", None, None, sample=True)
        trial_cpu["reason"] = "trial_pid_not_supplied"
    elif trial_pid < 1:
        trial_cpu = _descriptor(None, "UNSUPPORTED", None, None, sample=True)
        trial_cpu["reason"] = "invalid_trial_pid"
    else:
        trial_cpu = _read_descriptor(read_path, f"/proc/{trial_pid}/stat", sample=True)
        trial_cpu["pid"] = trial_pid

    return {
        "thermal_root": {
            "path": THERMAL_ROOT,
            "status": thermal_root_status,
            "initial_entries": zones,
            "read_duration_ns": thermal_root_duration,
        },
        "cpufreq_root": {
            "path": CPUFREQ_ROOT,
            "status": cpufreq_root_status,
            "initial_entries": policies,
            "read_duration_ns": cpufreq_root_duration,
        },
        "thermal_zones": thermal_zones,
        "cpufreq_policies": cpufreq_policies,
        "static_sources": static_sources,
        "trial_cpu": trial_cpu,
        "requested_trial_pid": trial_pid,
    }


def _sample_sources(discovery: dict) -> dict[str, dict]:
    sources: dict[str, dict] = {}
    for name, descriptor in discovery.get("static_sources", {}).items():
        if (descriptor.get("sample") and descriptor.get("path")
                and descriptor.get("status") == "AVAILABLE"):
            sources[name] = descriptor
    for zone_name, zone in discovery.get("thermal_zones", {}).items():
        descriptor = zone.get("temperature", {})
        if (descriptor.get("sample") and descriptor.get("path")
                and descriptor.get("status") == "AVAILABLE"):
            sources[f"thermal:{zone_name}:temperature"] = descriptor
    for policy_name, policy in discovery.get("cpufreq_policies", {}).items():
        for key in ("effective_freq", "max_freq"):
            descriptor = policy.get(key, {})
            if (descriptor.get("sample") and descriptor.get("path")
                    and descriptor.get("status") == "AVAILABLE"):
                sources[f"cpufreq:{policy_name}:{key}"] = descriptor
    trial_cpu = discovery.get("trial_cpu", {})
    if (trial_cpu.get("sample") and trial_cpu.get("path")
            and trial_cpu.get("status") == "AVAILABLE"):
        sources["trial_cpu"] = trial_cpu
    return sources


def base_record(trial_id: str, sequence: int, source: str, measurement: str,
                value: object, read_status: str, read_duration_ns: int | None,
                monotonic_ns: int | None = None,
                boottime_seconds: float | None = None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "trial_id": trial_id,
        "sequence": sequence,
        "timestamp_monotonic_ns": (
            monotonic_ns if monotonic_ns is not None else time.monotonic_ns()),
        "timestamp_boottime_seconds": boottime_seconds,
        "timestamp_wall_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": source,
        "measurement": measurement,
        "value": value,
        "read_status": read_status,
        "read_duration_ns": read_duration_ns,
    }


def collect(args: argparse.Namespace) -> int:
    reader = AdbReader(args.serial)
    process_cpu_start = time.process_time_ns()
    rc, state, _ = reader.run(["get-state"])
    if rc != 0 or state != "device":
        raise RuntimeError("adb target is not uniquely available in device state")

    def list_dir(path: str) -> tuple[str, list[str], int]:
        return list_directory(reader, path)

    discovery = discover_sources(reader.read_path, list_dir, args.trial_pid)
    metadata = read_metadata(reader)
    metadata["interfaces"] = discovery
    metadata["sample_sources"] = sorted(_sample_sources(discovery))
    metadata["requested_interval_ms"] = args.interval_ms
    metadata["duration_seconds"] = args.duration_seconds
    metadata["trial_pid"] = args.trial_pid
    metadata["declared_cpus"] = args.declared_cpus

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    interval_ns = int(args.interval_ms * 1_000_000)
    sequence = 0
    sources = _sample_sources(discovery)
    with output.open("x", encoding="utf-8") as handle:
        def emit(record: dict) -> None:
            nonlocal sequence
            handle.write(json.dumps(record, sort_keys=True,
                                     separators=(",", ":")) + "\n")
            handle.flush()
            sequence += 1

        emit(base_record(args.trial_id, sequence, "collector", "metadata", {
            "collector_version": COLLECTOR_VERSION,
            "metadata": metadata,
            "interfaces": discovery,
            "sample_sources": sorted(sources),
            "requested_interval_ms": args.interval_ms,
            "duration_seconds": args.duration_seconds,
            "trial_pid": args.trial_pid,
            "declared_cpus": args.declared_cpus,
        }, "AVAILABLE", None))

        deadline = time.monotonic() + args.duration_seconds
        next_tick = time.monotonic_ns()
        while time.monotonic() < deadline:
            cycle_ns = time.monotonic_ns()
            status, value, duration = reader.read_path("/proc/uptime")
            boottime = None
            if status == "AVAILABLE":
                try:
                    boottime = float(value.split()[0]) if value else None
                except (ValueError, IndexError):
                    status = "MALFORMED"
            emit(base_record(args.trial_id, sequence, "collector", "heartbeat",
                             None, status, duration, cycle_ns, boottime))
            for source, descriptor in sources.items():
                path = descriptor.get("path")
                if not path:
                    continue
                read_status, raw, read_duration = reader.read_path(path)
                emit(base_record(args.trial_id, sequence, source, "raw_read", raw,
                                 read_status, read_duration, time.monotonic_ns(),
                                 boottime))
            next_tick += interval_ns
            remaining = (next_tick - time.monotonic_ns()) / 1e9
            if remaining > 0:
                time.sleep(remaining)

        emit(base_record(args.trial_id, sequence, "collector", "end", {
            "host_process_cpu_time_ns": time.process_time_ns() - process_cpu_start,
            "adb_command_count": reader.command_count,
            "adb_command_duration_ns": reader.command_duration_ns,
            "jsonl_bytes_before_end": handle.tell(),
        }, "AVAILABLE", None, time.monotonic_ns(), None))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trial-id", required=True)
    p.add_argument("--duration-seconds", type=float, required=True)
    p.add_argument("--interval-ms", type=int, default=200)
    p.add_argument("--trial-pid", type=int)
    p.add_argument("--declared-cpus",
                   help="optional comma/range CPU stratum, e.g. 0-3")
    p.add_argument("--serial")
    p.add_argument("--output", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not TRIAL_RE.fullmatch(args.trial_id):
        raise SystemExit("invalid --trial-id")
    if (args.duration_seconds <= 0 or not 50 <= args.interval_ms <= 1000
            or (args.trial_pid is not None and args.trial_pid < 1)):
        raise SystemExit("invalid duration, interval, or trial pid")
    try:
        return collect(args)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"C3-OBS-01 collector failed closed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
