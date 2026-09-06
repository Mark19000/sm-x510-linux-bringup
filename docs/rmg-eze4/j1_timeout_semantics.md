# Deep Audit: `DEFAULT_ATTEMPT_TIMEOUT_SEC` Semantics and Lifecycle

This document provides a static source-level audit of the primary candidate parameter `DEFAULT_ATTEMPT_TIMEOUT_SEC` within the Samsung Exynos 1380 (EZE4) bring-up and verification framework. It traces every definition, alias, default, parser, caller, consumer, and termination path across the codebase.

---

## 1. Definitions, Aliases, Defaults, and Parsers

### 1.1 Source Definitions
`DEFAULT_ATTEMPT_TIMEOUT_SEC` is defined in two locations within the repository:

1. **Target Header (`src/targets/gts9fewifi-X510XXSEEZG3/target.h:34`):**
   ```c
   #define DEFAULT_ATTEMPT_TIMEOUT_SEC 2200
   ```
   This is the canonical target value (2200 seconds, or ~36.67 minutes) assigned to the Samsung Galaxy Tab S9 FE (ZG3 baseline target).

2. **Supervisor Fallback (`src/preload.c:7-9`):**
   ```c
   #ifndef DEFAULT_ATTEMPT_TIMEOUT_SEC
   #define DEFAULT_ATTEMPT_TIMEOUT_SEC 180
   #endif
   ```
   If no target header defines the macro, the supervisor falls back to 180 seconds. In the canonical build configuration, `target.h` is included via `common.h` -> `offset.h`, so the target definition (`2200`) precedes this check and overrides the 180-second fallback.

### 1.2 Environment Alias and Parser
The supervisor exposes an environment variable override for runtime tuning:
- **Environment Alias:** `EXPLOIT_ATTEMPT_TIMEOUT_SEC`
- **Parsing Location:** `src/preload.c:127-128`
  ```c
  int attempt_timeout_sec = env_int(
      "EXPLOIT_ATTEMPT_TIMEOUT_SEC", DEFAULT_ATTEMPT_TIMEOUT_SEC, 5, 900);
  ```

### 1.3 Parser Semantics and Bounding Behavior
The helper function `env_int` is defined in `src/preload.c:68-81`:
```c
static int env_int(const char *name, int fallback, int min, int max) {
  const char *value = getenv(name);
  if (!value || !*value) {
    return fallback;
  }

  char *end = NULL;
  errno = 0;
  long parsed = strtol(value, &end, 0);
  if (errno || end == value || *end || parsed < min || parsed > max) {
    return fallback;
  }
  return (int)parsed;
}
```

**Critical Parser Property:**
- When `EXPLOIT_ATTEMPT_TIMEOUT_SEC` is **unset** (or empty):
  `getenv()` returns `NULL`. `env_int` immediately returns `fallback` (`DEFAULT_ATTEMPT_TIMEOUT_SEC` = 2200) directly. It does **not** evaluate `parsed < min || parsed > max`.
- When `EXPLOIT_ATTEMPT_TIMEOUT_SEC` is **set**:
  The parser enforces `min = 5` and `max = 900`. If an environment string outside `[5, 900]` is supplied (e.g., `"2200"`), `parsed > max` evaluates to true, causing `env_int` to reject the override and fall back to `fallback` (`2200`).
  If a valid integer within `[5, 900]` is provided (e.g., `"600"`), that value is returned.

### 1.4 Downstream Clamping on `DEFAULT_P0_ATTEMPT_TIMEOUT_SEC`
At `src/preload.c:129-134`:
```c
int p0_attempt_timeout_sec = env_int(
    "P0_ATTEMPT_TIMEOUT_SEC", DEFAULT_P0_ATTEMPT_TIMEOUT_SEC, 5,
    attempt_timeout_sec);
if (p0_attempt_timeout_sec > attempt_timeout_sec) {
  p0_attempt_timeout_sec = attempt_timeout_sec;
}
```
`DEFAULT_ATTEMPT_TIMEOUT_SEC` acts as a hard upper bound for the pre-P0 timeout `p0_attempt_timeout_sec`. This establishes the hard prerequisite dependency edge recorded in `phase_h_dependency_edges.csv`.

---

## 2. Semantic Meaning and Scope

### 2.1 Exact Semantic Meaning
`DEFAULT_ATTEMPT_TIMEOUT_SEC` represents the maximum allowable elapsed monotonic duration (in integer seconds) allocated to **a single child process attempt**. It is a supervisor-enforced watchdog policy that prevents an unresponsive child process from hanging indefinitely (e.g., due to deadlock, unhandled race failure, or hung syscall).

### 2.2 Exact Scope
- **One Single Attempt:**
  The timeout covers **one individual child attempt**, initiated at child `fork()` and concluded at child reaping (`waitpid()`).
- **Not the Whole Supervisor Cycle:**
  The supervisor executes an outer loop of up to `max_attempts` (default 8; `DEFAULT_EXPLOIT_ATTEMPTS`). Each iteration forks a new child, resets the monotonic timer to zero, and bounds that attempt independently by `attempt_timeout_sec`.
- **Not Restricted to One Single Stage:**
  The timeout accumulates across all sequential stages of the child attempt (page setup, P0 physical oracle scan, KASLR slide discovery, CFI stage, root promotion).

### 2.3 Dynamic Nested Scope (`p0_attempt_timeout_sec` vs `attempt_timeout_sec`)
In `src/preload.c:200-206`:
```c
int timeout_sec = attempt_timeout_sec;
#if defined(SLIDE_P0_OFFSET_CANDIDATES)
if (!getenv("SLIDE_P0_OFFSET") &&
    !atomic_load(&app_p0_state->slide_ready)) {
  timeout_sec = p0_attempt_timeout_sec;
}
#endif
```
- While `slide_ready` is false (pre-slide / P0 oracle scanning phase), the effective timeout threshold is clamped to `p0_attempt_timeout_sec` (1200 s).
- Once the child publishes `slide_ready` (via atomic store to `app_p0_state->slide_ready`), the active threshold automatically expands to `attempt_timeout_sec` (2200 s) measured from the same initial start timestamp `started`.
- Thus, `DEFAULT_ATTEMPT_TIMEOUT_SEC` is the **overall cumulative bound** from child fork to child completion.

---

## 3. Clock Source, Timing Mechanisms, and Resolution

### 3.1 Clock Source
- **Clock:** `CLOCK_MONOTONIC`
  Invoked via `SYSCHK(clock_gettime(CLOCK_MONOTONIC, &started))` (`preload.c:187`) and `SYSCHK(clock_gettime(CLOCK_MONOTONIC, &now))` (`preload.c:198`).
- **Clock Type:** Monotonic elapsed time. It is not affected by system wall-clock adjustments or discontinuous jumps (e.g., NTP updates or manual time changes).
- **Not CPU Time:** It measures real elapsed monotonic time, **not** CPU time (`CLOCK_PROCESS_CPUTIME_ID` or thread runtime). Time spent blocked on kernel waits (`futex`, `sleep`, I/O, lock contention) counts directly against the timeout.
- **Boot Uptime Distinct:** Note that the boot quiet window uses `CLOCK_BOOTTIME` (`preload.c:103`) to account for suspend time, whereas the attempt timeout strictly uses `CLOCK_MONOTONIC`.

### 3.2 Code Starting and Stopping Timing
- **Start Timing (`src/preload.c:186-187`):**
  Immediately after `fork()`, the parent process runs:
  ```c
  struct timespec started;
  SYSCHK(clock_gettime(CLOCK_MONOTONIC, &started));
  ```
- **Stopping Timing (`src/preload.c:188-217`):**
  Timing stops when either:
  1. The child terminates on its own: `waited = waitpid(child, &status, WNOHANG)` returns `waited == child`. The polling loop breaks immediately (`preload.c:190-192`).
  2. The timeout expires: `elapsed >= timeout_sec`. The parent emits a warning log, sends `SIGKILL` to the child, and blocks in `waitpid(child, &status, 0)` until the child is fully reaped (`preload.c:207-216`).

### 3.3 Polling Granularity and Arithmetic
- **Polling Loop Delay:** The supervisor polls using non-blocking waitpid followed by `usleep(100000)` (100 milliseconds).
- **Elapsed Calculation:**
  ```c
  time_t elapsed = now.tv_sec - started.tv_sec;
  ```
- **Quantization:** Only whole seconds (`tv_sec`) are subtracted; `tv_nsec` is ignored.
  - Worst-case quantization error is $\pm 1$ second.
  - Over a 2200-second window, 1 second represents an error margin of $\approx 0.045\%$, which is negligible.
  - Polling jitter introduces an additional latency of at most 100 ms before `elapsed >= timeout_sec` is evaluated.

---

## 4. Exit States and Distinguishability

### 4.1 Exhaustive Inventory of Attempt Exit States

| Exit State ID | Condition | Mechanism | Observable Log | Next Action |
|---|---|---|---|---|
| `EXIT_SUCCESS` | Child completes all stages cleanly. | Child exits via `_exit(0)` (`run_exploit()` returns 0). Supervisor sees `WIFEXITED(status) && WEXITSTATUS(status) == 0`. | `pr_success("exploit completed attempt=%d/%d\n", attempt, max_attempts)` | Supervisor `load()` returns; exploit succeeded. |
| `EXIT_SAFE_ABORT_CHILD` | Child encounters unrecoverable failure (e.g. page setup failed, bad oracle gate). | Child calls `_exit(code)` with code $\ne 0$. Supervisor sees `WIFEXITED(status) && WEXITSTATUS(status) != 0`. | `pr_warning("exploit attempt=%d/%d failed status=%d\n", attempt, max_attempts, code)` | Evaluates `dirty` state. If clean and $i < \text{max}$, sleeps 5s and retries. |
| `EXIT_CHILD_CRASH` | Child faults (e.g., SIGSEGV, SIGBUS). | Child dies by uncaught signal. Supervisor sees `WIFSIGNALED(status)`. | `pr_warning("exploit attempt=%d/%d terminated signal=%d\n", attempt, max_attempts, sig)` | Evaluates `dirty` state; retries if clean. |
| `EXIT_TIMEOUT_PRE_P0` | $T_{\text{elapsed}} \ge p0\_attempt\_timeout\_sec$ before `slide_ready`. | Supervisor sends `SIGKILL` to child, reaps with `waitpid(child, &status, 0)`. | `pr_warning("exploit attempt=%d/%d timeout pid=%d seconds=%d\n", attempt, max_attempts, child, p0_timeout)` | Supervisor logs signal 9; retries if clean. |
| `EXIT_TIMEOUT_OVERALL` | $T_{\text{elapsed}} \ge attempt\_timeout\_sec$ after `slide_ready`. | Supervisor sends `SIGKILL` to child, reaps with `waitpid(child, &status, 0)`. | `pr_warning("exploit attempt=%d/%d timeout pid=%d seconds=%d\n", attempt, max_attempts, child, timeout)` | Supervisor logs signal 9; retries if clean. |
| `EXIT_DIRTY_ABORT` | Attempt fails after `app_publish_p0_dirty()`. | Supervisor inspects `atomic_load(&app_p0_state->dirty)` after child death. | `pr_error("p0 oracle state dirty or uncertain; refusing unsafe retry\n")` | Loop breaks; supervisor exits with code 1. |
| `EXIT_WRITER_ABORT` | Attempt fails after `app_publish_writer_started()`. | Supervisor inspects `atomic_load(&app_p0_state->writer_started)`. | `pr_error("stack writer ran; refusing retry on this boot\n")` | Loop breaks; supervisor exits with code 1. |
| `EXIT_MAX_ATTEMPTS` | All `max_attempts` exhausted without success. | Loop index exceeds `max_attempts`. | `pr_error("exploit failed after %d independent attempts\n", max_attempts)` | Supervisor calls `_exit(1)`. |

### 4.2 Distinguishability Matrix

- **Explicit Failure vs Timeout Expiry:**
  - **Distinguishable:** YES. Explicit failure produces `WIFEXITED(status)` with non-zero exit status, without emitting the `"exploit attempt=... timeout ..."` string. Timeout expiry emits the `"timeout"` string, sends `SIGKILL`, and yields `WIFSIGNALED` with signal 9.
- **Safe Abort vs Timeout Expiry:**
  - **Distinguishable:** YES. Safe abort terminates from within the child process before the timeout window is exhausted, logging stage-specific abort reasons and exiting with a specific exit status.
- **External Cancellation vs Timeout Expiry:**
  - **Distinguishable:** YES (for child-targeted cancellation). If an external entity sends `SIGKILL` to the child, the supervisor reaps `signal=9`, but **does not** emit the preceding `"timeout ... seconds=%d"` log because `elapsed < timeout_sec`. If an external entity terminates the supervisor process itself, all supervisor logging ceases prematurely, distinguishable by lack of terminal logs.
- **P0 Failure vs Timeout Expiry:**
  - **Distinguishable:** YES. A P0 failure results in either an immediate clean exit (`status=1`) or a dirty-state declaration (`app_publish_p0_dirty()`). Timeout during P0 logs `seconds=1200` (`p0_attempt_timeout_sec`), whereas overall timeout logs `seconds=2200` (`attempt_timeout_sec`).
- **Stage Failure vs Timeout Expiry:**
  - **Distinguishable:** YES. Stage failures produce explicit error logs from `main.c`, `page.c`, `fops.c`, etc., and return immediately.
- **Successful Completion vs Timeout Expiry:**
  - **Distinguishable:** YES. Successful completion emits `exploit completed attempt=%d/%d` and `status=0`.

---

## 5. Nested Timeouts and Internal Delays

Within the child execution path, several fine-grained timeouts and delays exist beneath the supervisor's macroscopic attempt timeout:

1. `SLIDE_WAIT_NSEC` (`2000000000L` = 2.0 s; `src/slide_app.c:174`):
   Passed as `timeout` to `futex_op(&slide_f_wait, FUTEX_WAIT_REQUEUE_PI, ...)`. Bounded to 2 seconds.
2. `DEFAULT_PSELECT_DELAY_USEC` (`20000` = 20 ms; `src/preload.c:6`):
   Microsecond delay before `pselect`.
3. `FOPS_ROUTE_COARSE_DELAY_USEC` (`50000` = 50 ms; `target.h:28`):
   Coarse delay for scheduling synchronization.
4. `attempt_delay_usec` (`src/preload.c:83-99`):
   Per-attempt incremental delay (up to 30 ms).

All internal child waits and delays sum to a few seconds per stage, well within the 2200-second overall attempt ceiling.

---

## 6. Overflow, Truncation, and Arithmetic Hazards

1. **`time_t` representation:** On 64-bit ARM Linux (`aarch64`), `time_t` is a signed 64-bit integer (`int64_t`). No arithmetic overflow or Year 2038 rollover hazard exists.
2. **`int` range:** `attempt_timeout_sec` is stored in a 32-bit signed integer (`int`). The value `2200` is well within $[-2^{31}, 2^{31}-1]$.
3. **Sub-second truncation:** `now.tv_sec - started.tv_sec` drops fractional seconds. As verified in Section 3.3, maximum truncation error is $< 1$ s, representing $< 0.05\%$ of the bound.

---

## 7. Confounding Factors in Timeout Measurement

1. **Host-vs-Device Skew:** Host log collection latency over ADB USB serial transport can delay host timestamping. Verification must rely on device-side monotonic timestamps and supervisor-emitted `seconds=%d` logs.
2. **Unseparated P0 Stalls:** If P0 scanning hangs without stage labels, the timeout may expire in the supervisor, confounding overall attempt timeout adequacy with pre-P0 oracle delays. Stage labeling (`slide_ready`) separates these phases.
3. **Android Cgroup Freezer:** If the target application is paused or frozen by Android's `ProcessList` / `AppFreeze` policy, `CLOCK_MONOTONIC` continues to advance while CPU execution halts, triggering an artificial timeout upon thaw.
4. **Thermal Throttling:** Sustained CPU load on Exynos 1380 can drop core frequencies from 2.4 GHz to lower power states, shifting duration distributions toward the tail. E4 cross-condition observation must span thermal states.
