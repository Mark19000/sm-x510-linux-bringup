#!/usr/bin/env python3
"""Read-only host collector for the future C2-OBS-01 stock-EZE4 probe.

The program only invokes adb get-state and adb shell read commands. It never
writes device files, changes policy, acquires wakelocks, or runs the exploit.
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

COLLECTOR_VERSION = "1.0.0"
SCHEMA_VERSION = "c2-obs-01.v1"
TRIAL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

STATIC_SOURCES = {
    "device_boottime": "/proc/uptime",
    "wakeup_count": "/sys/power/wakeup_count",
    "suspend_success": "/sys/power/suspend_stats/success",
    "suspend_fail": "/sys/power/suspend_stats/fail",
}


def classify_read(returncode: int, stderr: str) -> str:
    text = stderr.lower()
    if returncode == 0:
        return "AVAILABLE"
    if "permission denied" in text or "operation not permitted" in text:
        return "PERMISSION_DENIED"
    if "no such file" in text or "not found" in text:
        return "UNAVAILABLE"
    if "is a directory" in text or "invalid argument" in text:
        return "UNSUPPORTED"
    return "AMBIGUOUS"


class AdbReader:
    def __init__(self, serial: str | None = None):
        self.prefix = ["adb"] + (["-s", serial] if serial else [])
        self.command_count = 0
        self.command_duration_ns = 0

    def run(self, args: list[str], timeout: float = 5.0) -> tuple[int, str, str]:
        started = time.monotonic_ns()
        completed = subprocess.run(
            self.prefix + args, text=True, capture_output=True, timeout=timeout,
            check=False,
        )
        self.command_count += 1
        self.command_duration_ns += time.monotonic_ns() - started
        return completed.returncode, completed.stdout.rstrip("\n"), completed.stderr.rstrip("\n")

    def read_path(self, path: str) -> tuple[str, str | None, int]:
        # `cat -- path` is the only device-side operation used for sources.
        start = time.monotonic_ns()
        rc, out, err = self.run(["shell", "cat", "--", path])
        duration = time.monotonic_ns() - start
        return classify_read(rc, err), out if rc == 0 else None, duration


def base_record(trial_id: str, sequence: int, source: str, measurement: str,
                value: object, read_status: str, read_duration_ns: int | None,
                monotonic_ns: int | None = None, boottime_seconds: float | None = None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "trial_id": trial_id,
        "sequence": sequence,
        "timestamp_monotonic_ns": monotonic_ns if monotonic_ns is not None else time.monotonic_ns(),
        "timestamp_boottime_seconds": boottime_seconds,
        "timestamp_wall_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": source,
        "measurement": measurement,
        "value": value,
        "read_status": read_status,
        "read_duration_ns": read_duration_ns,
    }


def discover_sources(read_path: Callable[[str], tuple[str, str | None, int]],
                     trial_pid: int | None) -> dict[str, dict]:
    sources: dict[str, dict] = {}
    for name, path in STATIC_SOURCES.items():
        status, value, duration = read_path(path)
        sources[name] = {"path": path, "status": status, "initial_value": value,
                         "read_duration_ns": duration}

    # Bind the trial cgroup from the kernel's own proc record; never guess it.
    if trial_pid is None:
        sources["trial_cgroup_events"] = {
            "path": None, "status": "UNSUPPORTED", "initial_value": None,
            "read_duration_ns": None, "reason": "trial_pid_not_supplied",
        }
    else:
        proc_path = f"/proc/{trial_pid}/cgroup"
        status, value, duration = read_path(proc_path)
        if status != "AVAILABLE" or not value:
            sources["trial_cgroup_events"] = {
                "path": None, "status": status, "initial_value": None,
                "read_duration_ns": duration, "reason": "cannot_bind_trial_cgroup",
            }
        else:
            candidates = []
            for line in value.splitlines():
                parts = line.split(":", 2)
                # Android exposes legacy controller entries alongside the
                # unified cgroup-v2 membership.  cgroup.events (including the
                # freezer state) belongs to the unique `0::...` entry; treating
                # the v1 entries as equivalent paths makes real EZE4 discovery
                # spuriously ambiguous.
                if len(parts) == 3 and parts[0] == "0" and parts[1] == "":
                    rel = parts[2].lstrip("/")
                    candidates.append("/sys/fs/cgroup/" + (rel + "/" if rel else "") + "cgroup.events")
            unique = list(dict.fromkeys(candidates))
            if len(unique) != 1:
                sources["trial_cgroup_events"] = {
                    "path": None, "status": "AMBIGUOUS", "initial_value": None,
                    "read_duration_ns": duration, "reason": "cgroup_path_not_unique",
                }
            else:
                c_status, c_value, c_duration = read_path(unique[0])
                sources["trial_cgroup_events"] = {
                    "path": unique[0], "status": c_status, "initial_value": c_value,
                    "read_duration_ns": c_duration,
                }
    return sources


def read_metadata(reader: AdbReader) -> dict:
    commands = {
        "model": ["shell", "getprop", "ro.product.model"],
        "device": ["shell", "getprop", "ro.product.device"],
        "build_fingerprint": ["shell", "getprop", "ro.build.fingerprint"],
        "build_incremental": ["shell", "getprop", "ro.build.version.incremental"],
        "kernel_release": ["shell", "uname", "-r"],
        "boot_id": ["shell", "cat", "--", "/proc/sys/kernel/random/boot_id"],
    }
    result = {}
    for name, command in commands.items():
        start = time.monotonic_ns()
        rc, out, err = reader.run(command)
        result[name] = {
            "value": out if rc == 0 else None,
            "status": classify_read(rc, err),
            "read_duration_ns": time.monotonic_ns() - start,
        }
    return result


def parse_uptime(value: str | None) -> float | None:
    try:
        return float((value or "").split()[0])
    except (ValueError, IndexError):
        return None


def collect(args: argparse.Namespace) -> int:
    reader = AdbReader(args.serial)
    process_cpu_start = time.process_time_ns()
    rc, state, _ = reader.run(["get-state"])
    if rc != 0 or state != "device":
        raise RuntimeError("adb target is not uniquely available in device state")
    sources = discover_sources(reader.read_path, args.trial_pid)
    metadata = read_metadata(reader)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    interval_ns = int(args.interval_ms * 1_000_000)
    sequence = 0
    with output.open("x", encoding="utf-8") as handle:
        def emit(record: dict) -> None:
            nonlocal sequence
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            sequence += 1

        emit(base_record(args.trial_id, sequence, "collector", "metadata", {
            "collector_version": COLLECTOR_VERSION,
            "metadata": metadata,
            "interfaces": sources,
            "requested_interval_ms": args.interval_ms,
            "duration_seconds": args.duration_seconds,
            "trial_pid": args.trial_pid,
        }, "AVAILABLE", None))
        deadline = time.monotonic() + args.duration_seconds
        next_tick = time.monotonic_ns()
        while time.monotonic() < deadline:
            cycle_ns = time.monotonic_ns()
            uptime_status, uptime_value, uptime_duration = reader.read_path(STATIC_SOURCES["device_boottime"])
            boottime = parse_uptime(uptime_value)
            emit(base_record(args.trial_id, sequence, "collector", "heartbeat", None,
                             uptime_status, uptime_duration, cycle_ns, boottime))
            for name, info in sources.items():
                path = info.get("path")
                if name == "device_boottime" or not path or info["status"] != "AVAILABLE":
                    continue
                status, value, duration = reader.read_path(path)
                emit(base_record(args.trial_id, sequence, name, "raw_read", value,
                                 status, duration, time.monotonic_ns(), boottime))
            next_tick += interval_ns
            remaining = (next_tick - time.monotonic_ns()) / 1e9
            if remaining > 0:
                time.sleep(remaining)
        emit(base_record(args.trial_id, sequence, "collector", "end", {
                             "host_process_cpu_time_ns": time.process_time_ns() - process_cpu_start,
                             "adb_command_count": reader.command_count,
                             "adb_command_duration_ns": reader.command_duration_ns,
                             "jsonl_bytes_before_end": handle.tell(),
                         },
                         "AVAILABLE", None, time.monotonic_ns(), None))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trial-id", required=True)
    p.add_argument("--duration-seconds", type=float, required=True)
    p.add_argument("--interval-ms", type=int, default=200)
    p.add_argument("--trial-pid", type=int)
    p.add_argument("--serial")
    p.add_argument("--output", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not TRIAL_RE.fullmatch(args.trial_id):
        raise SystemExit("invalid --trial-id")
    if args.duration_seconds <= 0 or not 10 <= args.interval_ms <= 500 or (args.trial_pid is not None and args.trial_pid < 1):
        raise SystemExit("invalid duration, interval, or trial pid")
    try:
        return collect(args)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"C2-OBS-01 collector failed closed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
