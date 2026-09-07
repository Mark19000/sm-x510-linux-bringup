# EZE4 runtime probe plan

The C2 and C3 stock baselines were executed on 2026-09-06. The investigation
stopped before combining primitives or attempting privilege escalation because
neither observer closed all required sources.

## C2-OBS-01 — freezer/suspend observability

**Implementation:** `tools/rmg-eze4/c2_obs_01_collect.py`; offline analyzer:
`tools/rmg-eze4/c2_obs_01_analyze.py`; integrity gate: `make verify-c2-obs`.
The concrete design and JSONL schema are documented in `C2_OBS_01_DESIGN.md`.
Hardware discovery selected the unique unified `0::` cgroup entry. Baseline
`TRL-C2-BASELINE-01C` met the 500 ms timing bound, but stock permissions denied
all suspend counters; verdict `C2_PARTIAL`.

- **Hypothesis:** the stock app/ADB context can continuously observe an EZE4
  freezer or suspension signal with J2-required timing coverage.
- **Required privilege:** ordinary read-only shell/app context; no root.
- **Inputs:** one inert timed workload and a monitor that timestamps the
  applicable `cgroup.events`/suspend signal every at most 200 ms.
- **Expected PASS:** interface bound, 100% interval coverage, maximum gap at most
  500 ms, and explicit event count.
- **Expected FAIL:** a freeze/suspend event. Inaccessible interface or gaps yield
  `UNKNOWN`, not FAIL.
- **Side effects:** read-only sampling and temporary logs.
- **Crash/persistence/recovery:** no intended crash; no persistent modification;
  no reboot or recovery requirement.
- **Artifacts:** raw timestamped samples, resolved cgroup path, monotonic clock
  metadata, start/end hashes and coverage summary.
- **Stop conditions:** permission denial, device disconnect, gap over 500 ms or
  any command that would write cgroup state.

## C3-OBS-01 — thermal/frequency/CPU observability

**Implementation:** `tools/rmg-eze4/c3_obs_01_collect.py`; analyzer:
`tools/rmg-eze4/c3_obs_01_analyze.py`. Baseline `TRL-C3-BASELINE-02` met the
500 ms critical-path timing bound after removing redundant topology reads.
Cpufreq and trial-CPU placement are visible; thermal sysfs values and trips are
permission-denied. Verdict `C3_PARTIAL`.

- **Hypothesis:** thermal zones, trip mapping, effective CPU frequency and the
  executing CPU can be sampled continuously enough to classify C3.
- **Required privilege:** ordinary read-only shell/app context; no root.
- **Inputs:** one inert timed workload; read-only thermal/cpufreq/CPU monitor at
  most every 1000 ms.
- **Expected PASS:** mapped zones and frequency policy, 100% interval coverage,
  maximum gap at most 2500 ms, no critical trip or invalid clamp/migration.
- **Expected FAIL:** critical trip or departure from the predeclared stratum.
  Missing/unmapped data yields `UNKNOWN`.
- **Side effects:** read-only sampling and temporary logs.
- **Crash/persistence/recovery:** none intended; no persistent modification; no
  reboot or recovery requirement.
- **Artifacts:** raw samples, zone/type/trip mapping, cpufreq policy, CPU samples,
  monotonic metadata and coverage summary.
- **Stop conditions:** permission denial, disconnect, excessive gap or any
  attempt to alter governors, affinity, trips or thermal policy.

# MINIMAL NEXT EZE4 RUNTIME EXPERIMENT

**Goal:** add one continuous, low-perturbation, read-only suspend marker to C2.
Do not run P02 until that source is independently shown to close the blind spot;
`dumpsys power` snapshots alone are not sufficient evidence of absence.
