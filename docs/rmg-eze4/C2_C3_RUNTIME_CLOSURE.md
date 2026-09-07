# C2/C3 runtime closure

These identifiers are canonical J2 measurement confounders, not exploit-chain
primitives. Historical unrelated uses of “C2/C3” outside `docs/rmg-eze4` do not
govern this investigation. Authority is `phase_j2_confounders.csv`.

## C2

- **Condition:** `ANDROID_CGROUP_FREEZER`.
- **Claim:** freezing or suspension can let `CLOCK_MONOTONIC` advance while the
  exploit process makes no progress, falsely inflating a trial duration.
- **Why required:** without continuous coverage, a timeout cannot be attributed
  to the candidate parameter or primitive.
- **Original evidence:** J2 confounder contract and gates G14; no physical
  observation was claimed.
- **Current EZE4 evidence:** the retained stock session records identity, CPU,
  memory, uptime and load only. It contains no continuous `cgroup.events` or
  suspend-marker stream.
- **Dependencies:** readable freezer signal, monotonic timestamps, trial/session
  binding, sampling at most 200 ms and maximum evidence gap 500 ms.
- **Failure modes:** inaccessible cgroup hierarchy, Android-specific path drift,
  polling gaps, suspend between samples, observer termination.
- **Static observables:** kernel cgroup/freezer support and Android hierarchy
  code; these do not prove runtime coverage.
- **Runtime observables:** frozen counter/state transitions and suspend markers
  throughout exactly one trial.
- **Pass criterion:** 100% trial coverage, zero freeze events, maximum gap at
  most 500 ms.
- **Fail criterion:** any freeze/suspend event (`C2_PRESENT`). Missing coverage
  is `C2_UNKNOWN`, not absence.
- **Unknowns:** accessible EZE4 path/interface and uninterrupted monitor behavior.

### Runtime result — 2026-09-06

`TRL-C2-BASELINE-01C` ran for 60 seconds on stock X510XXUCEZE4,
boot ID `109a1d90-2daf-4786-9617-03dc38cdaf9e`, using System UI PID 1989.
The EZE4 unified membership `0::/apps/uid_10062/pid_1989` resolved to a
readable `cgroup.events` stream (`populated 1`, `frozen 0`). All 300 samples
were present; max/p95/p99 gaps were 204.890/203.179/204.644 ms. `/proc/uptime`
was readable. `wakeup_count` and both suspend counters were
`PERMISSION_DENIED`; the run therefore cannot prove absence of suspend.

**Status: `C2_PARTIAL` — freezer observable with valid timing; suspend
absence remains unobservable in stock shell context.**

### Positive suspend-control attempt — 2026-09-07

`TRL-C2-SUSPEND-POSITIVE-001` used the detached dual-clock observer while a
stock, reversible `input keyevent 26` screen-off interval of 20 seconds was
applied. The exact EZE4 runtime identity remained valid. All 149 samples had
valid coverage, the maximum sampling gap was 203.627 ms, and the maximum
`CLOCK_BOOTTIME - CLOCK_MONOTONIC` offset change was 558 ns. No suspend was
observed. Screen-off therefore did not provide a positive suspend control on
the USB-connected stock device.

```text
C2_RUNTIME_MONITOR_VALIDATED
positive_suspend_control: unavailable under stock constraints
```

Suspend remains an explicit confounder for a P02 trial.

## C3

- **Condition:** `THERMAL_THROTTLING_CORE_MIGRATION`.
- **Claim:** thermal clamping or migration outside the declared CPU stratum can
  inflate legitimate runtime and invalidate attribution.
- **Why required:** aggregate timeout alone cannot distinguish a broken
  primitive from throttled execution.
- **Original evidence:** J2 confounder contract and gate G15; trip-point mapping
  was left for runtime binding.
- **Current EZE4 evidence:** one `cpu/online` and load snapshot; no continuous
  thermal-zone, frequency, affinity or migration trace.
- **Dependencies:** mapped thermal zones/trips, frequency baseline, CPU identity,
  monotonic timestamps and sampling at most 1000 ms with maximum gap 2500 ms.
- **Failure modes:** unreadable zones, unmapped vendor sensors, frequency-policy
  ambiguity, scheduler migration between samples, monitor gaps.
- **Static observables:** thermal/cpufreq config and source presence only.
- **Runtime observables:** temperature/trip, effective frequency and executing
  CPU bound to one trial.
- **Pass criterion:** continuous declared-stratum coverage with no critical trip
  or below-baseline clamp and maximum gap at most 2500 ms.
- **Fail criterion:** critical trip or invalid clamp/migration (`C3_PRESENT`).
  Missing coverage is `C3_UNKNOWN`.
- **Unknowns:** sensor-to-zone mapping, valid frequency floor, accessible CPU
  execution trace and observer continuity.

### Runtime result — 2026-09-06

`TRL-C3-BASELINE-02` ran for 60 seconds against PID 1989. Thermal zones 0-7
exist, but stock shell is denied their type, temperature and trip files.
Cpufreq policies 0 (CPUs 0-3) and 4 (CPUs 4-7), their effective/max
frequencies, and the trial CPU are readable. The reduced read set produced 134
complete samples with max/p95/p99 gaps 471.763/464.582/470.640 ms, no observed
max-frequency clamp and no observed migration. Those absences apply only to
the readable sources; no thermal conclusion is permitted.

**Status: `C3_PARTIAL` — frequency and CPU placement observable with valid
timing; temperatures/trips are not visible through thermal sysfs.**

Neither condition can be labelled fully observable or `PROVEN_EZE4` from
these baselines. Their raw JSONL and analyzer outputs are retained under
`artifacts/`.
