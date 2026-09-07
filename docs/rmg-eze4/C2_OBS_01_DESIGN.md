# C2-OBS-01 collector design

Status: implemented and audited offline; never executed on hardware.

## Objective and canonical semantics

C2 excludes Android cgroup freezer/suspension as a confounder while
`CLOCK_MONOTONIC` trial time is interpreted. Authority remains
`phase_j2_confounders.csv`: nominal polling is 200 ms, coverage is invalid when
any effective heartbeat gap exceeds 500 ms, any freeze/suspend evidence makes
the trial invalid, and incomplete observation remains `C2_UNKNOWN`.

## Architecture

- `tools/rmg-eze4/c2_obs_01_collect.py` is a host-side read-only collector. Its
  device operations are limited to `adb get-state`, `getprop`, `uname` and
  `cat -- <fixed-or-kernel-derived-path>`.
- `tools/rmg-eze4/c2_obs_01_analyze.py` parses/replays JSONL and alone applies
  coverage, identity and C2 observation semantics.
- The collector never writes sysfs/procfs/debugfs, changes policy, obtains a
  wakelock, changes affinity/governors/freezer state, deploys a module, or runs
  the exploit.

## Sources and discovery

| Source | Purpose | Discovery behavior |
|---|---|---|
| `/proc/uptime` | device boottime sample and heartbeat read health | direct read |
| trial `cgroup.events` | `frozen` plus trial continuity (`populated`) | derive exactly one cgroup path from `/proc/<pid>/cgroup`; ambiguity is fatal to evidence |
| `/sys/power/wakeup_count` | cumulative wake transition signal | optional direct read |
| `/sys/power/suspend_stats/success` and `fail` | cumulative suspend outcome | optional direct reads |

Every source is retained as `AVAILABLE`, `UNAVAILABLE`, `PERMISSION_DENIED`,
`UNSUPPORTED`, or `AMBIGUOUS`. `C2_ABSENT_FOR_OBSERVED_INTERVAL` requires an
available trial cgroup source plus complete coverage from at least one power
transition counter (`suspend_success` or `wakeup_count`). Other sources remain
optional corroboration; their absence is retained explicitly.

## Output and clocks

The append-only, exclusive-create JSONL stream uses schema `c2-obs-01.v1`.
Every record contains sequence, host monotonic nanoseconds, device boottime when
readable, secondary UTC metadata, source, measurement, raw value, read status
and measured read duration. Metadata binds model, device, full fingerprint,
incremental, kernel release, boot ID, discovered interfaces and requested
interval. The analyzer obtains expected identity from canonical Schema v2.2.1.

Host monotonic time is the coverage clock. Device boottime is separately
preserved; regression or a suspend-sized positive divergence cannot be treated
as clean coverage. Wall time is never used for ordering.

## Coverage analysis

The analyzer computes effective heartbeat gaps rather than trusting sleep:
sample count, requested interval, mean actual interval, maximum, p50, p95 and
p99. Exactly 500 ms is allowed; any value above 500 ms, fewer than two samples,
read failure, timestamp regression, duplicate sequence or identity mismatch
produces `COVERAGE_INVALID` and `C2_UNKNOWN` unless a positive freeze/power event
was independently observed.

## Perturbation assessment

With a 200 ms interval, the current host implementation emits five heartbeats
per second. If all four optional/required device sources are readable it may
perform approximately five device reads per cycle: about 25 `adb shell` reads
per second, plus JSONL flushes. It uses one host Python process but launches one
short-lived adb client per read. The end record measures host process CPU time,
ADB command count/aggregate duration and JSONL bytes. Approximate raw JSONL
volume is expected to be hundreds of KiB per minute, dependent on cgroup text
and latency.

This is intentionally not claimed low-perturbation. ADB activity may alter idle
or suspend behavior, and process/read overhead may itself violate 500 ms. The
future inert baseline must measure `read_duration_ns`, actual gaps, host CPU time
and output size before the data can support C2. Failure to meet the bound is a
valid negative result about collector suitability, not evidence about C2.

## Future execution

After review, bind the inert workload PID and use an unused output path:

```sh
python3 tools/rmg-eze4/c2_obs_01_collect.py --trial-id TRL-C2-BASELINE-01 --trial-pid DEVICE_PID --duration-seconds 60 --interval-ms 200 --output artifacts/c2-obs-01-baseline.jsonl
python3 tools/rmg-eze4/c2_obs_01_analyze.py artifacts/c2-obs-01-baseline.jsonl
```

Do not execute this as part of offline validation. `DEVICE_PID` must be replaced
with the inert process PID; literal or stale PIDs invalidate discovery.

## Limitations and stop conditions

- Android EZE4 permissions and actual cgroup layout remain unknown.
- ADB may prevent or perturb the state being observed.
- Cumulative power counters can prove a transition by changing; stability alone
  cannot prove that no transition occurred.
- Disconnect, boot-ID/identity mismatch, permission workaround, ambiguous
  cgroup mapping, missing trial PID, output collision, timestamp regression,
  duplicate sequence, read failure or gap above 500 ms forbids use as C2-absence
  evidence.
- This collector does not exercise P02 and cannot establish exploit feasibility.
