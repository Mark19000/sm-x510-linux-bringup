# Confounder Audit: `DEFAULT_ATTEMPT_TIMEOUT_SEC`

This document identifies, analyzes, and ranks all potential factors that could render an observed timeout outcome misleading during offline validation or future empirical observation. Each confounder is evaluated for its risk level (`HIGH`, `MEDIUM`, or `LOW`) and mapped to its concrete representation within the Phase I measurement architecture.

---

## 1. Confounder Summary Table

| Confounder ID | Confounder Description | Risk Rank | Can Phase I Represent It? | Phase I Mechanism |
|---|---|---|---|---|
| `C1` | Unseparated P0 Oracle Delay | **HIGH** | **YES** | Stage-labelled observables (`X-G11-LABEL`), `p0_attempt_timeout_sec` threshold separation, `UNRESOLVED_GROUP_DEPENDENCIES`. |
| `C2` | Android Cgroup Freezing / Process Suspension | **HIGH** | **YES** | `ENVIRONMENT` condition state, `MEASUREMENT_INVALID == True`, system state precondition audit. |
| `C3` | Thermal Throttling & big.LITTLE Core Migration | **HIGH** | **YES** | `ENVIRONMENT` hardware fields (CPU load, thermal class), mandatory cross-condition partitioning. |
| `C4` | Host vs Device Timestamp Skew / ADB Transport Latency | **MEDIUM** | **YES** | Separation of `TIMESTAMP_HOST` and `TIMESTAMP_DEVICE_IF_AVAILABLE`; reliance on device `CLOCK_MONOTONIC` log. |
| `C5` | Internal Child Deadlock vs Timeout Inadequacy | **MEDIUM** | **YES** | Child terminal state logging, stack trace capture, `OUTLIER_UNRESOLVED`, `CONFOUNDERS` list. |
| `C6` | Allocator Slow-Path Direct Reclaim Latency | **MEDIUM** | **YES** | `ENVIRONMENT.memory_pressure` tracking, cross-condition coverage. |
| `C7` | Inter-Attempt Sleep and Quiet Window Contamination | **LOW** | **YES** | Attempt-indexed `TRIAL_ID`, timer reset on `fork()`, explicit 5s inter-attempt sleep observable. |
| `C8` | Integer Second Quantization / Truncation Error ($\pm 1$s) | **LOW** | **YES** | Policy headroom margin ($T_{\text{headroom}}$) in compatibility criterion evaluation. |

---

## 2. Detailed Technical Audit of Confounders

### C1: Unseparated P0 Oracle Delay
- **Risk Rank:** **HIGH**
- **Mechanism:**
  The pre-slide phase includes scanning physical oracle candidates. If the oracle scan experiences delays (e.g. searching through multiple candidates or encountering lock contention) and the observation pipeline does not separate pre-slide duration from post-slide duration, an overall timeout expiry could be falsely attributed to `DEFAULT_ATTEMPT_TIMEOUT_SEC` when it was actually caused by an unresolved P0 bottleneck.
- **Source Context:**
  In `src/preload.c:200-206`, the supervisor dynamically clamps `timeout_sec` to `p0_attempt_timeout_sec` (1200 s) prior to `slide_ready`, and expands to `attempt_timeout_sec` (2200 s) after `slide_ready`.
- **Phase I Representation:**
  **YES.** Phase I enforces stage-labelled duration records (`C-G11-OVERALL`, rule `X-G11-LABEL`). If stage timestamps are unavailable, the record is classified as `INCONCLUSIVE` due to ambiguous attribution. Furthermore, `DEFAULT_P0_ATTEMPT_TIMEOUT_SEC` is tracked in a separate contract group.

---

### C2: Android Cgroup Freezing / Process Suspension
- **Risk Rank:** **HIGH**
- **Mechanism:**
  The Android framework (`system_server`) actively manages process lifecycles via the cgroup v2 freezer subsystem (`AppFreezer`). If the target process is frozen or descheduled to background sleep during an attempt, CPU execution is suspended, but `CLOCK_MONOTONIC` continues to advance. When the process is thawed, `now.tv_sec - started.tv_sec` immediately jumps past the timeout threshold, causing the supervisor to kill the child with a false timeout expiry.
- **Source Context:**
  `preload.c` runs within an application process loaded under Zygote.
- **Phase I Representation:**
  **YES.** Phase I captures execution conditions via `ENVIRONMENT` (e.g., `app_state: "FOREGROUND_FOCUSED"` or `wakelock: "HELD"`). If an unexpected process freeze occurs, the observation is marked with `MEASUREMENT_INVALID = True` or flagged in `CONFOUNDERS`, yielding `INVALID_MEASUREMENT` or `INCONCLUSIVE`.

---

### C3: Thermal Throttling & big.LITTLE Core Migration
- **Risk Rank:** **HIGH**
- **Mechanism:**
  The Exynos 1380 contains 4 Cortex-A78 big cores and 4 Cortex-A55 LITTLE cores. If sustained background load or elevated ambient temperature triggers Samsung Thermal Engine throttling, CPU clock speeds drop from 2.4 GHz to 1.2 GHz or lower, and tasks may be forced onto Cortex-A55 cores. This stretches legitimate attempt duration tails significantly.
- **Source Context:**
  `main.c:301` pins the process to `CORE`, but kernel thermal governor overrides can throttle or force idle injection.
- **Phase I Representation:**
  **YES.** Phase I represents this through `ENVIRONMENT` metadata (capturing thermal zone temperatures, CPU frequency caps, and load states). The mandatory cross-condition requirement (`CROSS_CONDITION_REQUIRED = YES`) explicitly forces the evaluation to sample both unthrottled and thermally stressed states.

---

### C4: Host vs Device Timestamp Skew / ADB Transport Latency
- **Risk Rank:** **MEDIUM**
- **Mechanism:**
  When logs are captured over ADB USB transport, line buffering, daemon context switches, and USB host controller scheduling introduce variable latency (from milliseconds to tens of seconds under host buffer stall). Comparing host wall-clock time against supervisor time creates apparent duration discrepancies.
- **Source Context:**
  The supervisor logs: `exploit attempt=%d/%d timeout pid=%d seconds=%d`.
- **Phase I Representation:**
  **YES.** The Phase I observation schema strictly isolates `TIMESTAMP_HOST` (host receipt time) from `TIMESTAMP_DEVICE_IF_AVAILABLE` (device monotonic timestamp) and derives observed duration exclusively from device-side logs.

---

### C5: Internal Child Deadlock vs Timeout Inadequacy
- **Risk Rank:** **MEDIUM**
- **Mechanism:**
  If a child process deadlocks internally (e.g., PI futex requeue hang or unhandled lock contention), it stops executing and waits forever. The supervisor will eventually reach 2200 seconds and kill the child. Falsely attributing this timeout to "inadequate timeout budget" would be incorrect; the root cause is child deadlock, not insufficient time.
- **Source Context:**
  `slide_app.c` futex operations and `fops.c` kernel races.
- **Phase I Representation:**
  **YES.** Phase I checks whether internal stage progression occurred. If a child makes zero progress after entering a stage and terminal status indicates hang, the record includes `CONFOUNDERS: ["CHILD_INTERNAL_DEADLOCK"]` and `OUTLIER_UNRESOLVED: True`, preventing the event from counting as valid incompatibility evidence.

---

### C6: Allocator Slow-Path Direct Reclaim Latency
- **Risk Rank:** **MEDIUM**
- **Mechanism:**
  Under high physical memory fragmentation, kernel page allocations enter the direct reclaim slow-path, swapping pages or flushing dirty caches to eMMC/UFS storage. This significantly shifts setup loop durations.
- **Phase I Representation:**
  **YES.** Tracked via `ENVIRONMENT` memory availability metrics and tested under cross-boot / cross-condition partitions.

---

### C7: Inter-Attempt Sleep and Quiet Window Contamination
- **Risk Rank:** **LOW**
- **Mechanism:**
  Between attempts, the supervisor sleeps for 5 seconds (`preload.c:278: sleep(5)`). Furthermore, early boot wait sleeps for up to 120 seconds (`preload.c:109`). If inter-attempt sleep were added to child duration, measurements would be confounded.
- **Source Context:**
  In `preload.c:186-187`, `started` is sampled **after** the child is forked and after inter-attempt sleeps. Each attempt resets timing.
- **Phase I Representation:**
  **YES.** Phase I indexes observations by `TRIAL_ID` (attempt index), ensuring each trial's duration reflects solely that child's execution lifecycle.

---

### C8: Integer Second Quantization / Truncation Error
- **Risk Rank:** **LOW**
- **Mechanism:**
  `preload.c:199` computes `time_t elapsed = now.tv_sec - started.tv_sec`, dropping nanoseconds. A child starting at $T + 0.999$s and checked at $T + 1.001$s displays `elapsed = 1` after only 2 ms.
- **Source Context:**
  Maximum truncation error is strictly bounded to $< 1$ second.
- **Phase I Representation:**
  **YES.** Given the 2200-second scale, a 1-second truncation is negligible ($0.045\%$). Phase I evaluates duration tails with policy headroom ($T_{\text{headroom}} \ge 5$s), absorbing quantization error completely.
