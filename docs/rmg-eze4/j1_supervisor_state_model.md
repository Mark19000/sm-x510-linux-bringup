# Supervisor / Attempt Control-Flow State Model

This document specifies the abstract static control-flow state model governing the supervisor and attempt lifecycle within `src/preload.c` and associated interfaces. In accordance with audit instructions, this model contains **no exploit mechanics**, focusing exclusively on process management, timing, stage transitions, error handling, and termination semantics.

---

## 1. Abstract Lifecycle States

| State ID | Semantic Meaning | Process Context |
|---|---|---|
| `START` | Initial execution of preload constructor; environment parsing, baseline checks, and quiet-window wait. | Supervisor (Parent) |
| `ATTEMPT_BEGIN` | Initialization of an attempt; child process forked, initial timer sampled, attempt delay applied. | Supervisor & Child |
| `STAGE_BEGIN` | Entrance into an abstract sequential processing stage within the child. | Child |
| `STAGE_END` | Clean completion of an abstract processing stage within the child; intermediate state published. | Child |
| `TIMEOUT_EXPIRED` | Supervisor watchdog timer reaches or exceeds the active threshold (`p0_attempt_timeout_sec` or `attempt_timeout_sec`). | Supervisor (Parent) |
| `SAFE_ABORT` | Controlled early termination invoked by the child upon detecting an invalid, unrecoverable, or out-of-spec condition. | Child |
| `ATTEMPT_FAILED` | Child has terminated without complete success (exit code $\ne 0$, signal termination, or supervisor `SIGKILL`). | Supervisor (Parent) |
| `ATTEMPT_SUCCEEDED` | Child has cleanly completed all required stages and exited with status 0. | Supervisor (Parent) |
| `SUPERVISOR_STOP` | Terminal state of the supervisor; constructor either returns cleanly on success or terminates via `_exit(1)`. | Supervisor (Parent) |

---

## 2. State Machine Diagram

```mermaid
stateDiagram-v2
    [*] --> START
    START --> ATTEMPT_BEGIN: T01: Boot quiet window complete; attempt=1

    state "Attempt Execution Lifecycle" as AttemptScope {
        ATTEMPT_BEGIN --> STAGE_BEGIN: T02: Child forked; run_exploit() entered
        STAGE_BEGIN --> STAGE_END: T03: Stage completed successfully
        STAGE_END --> STAGE_BEGIN: T04: Next stage entered

        STAGE_BEGIN --> TIMEOUT_EXPIRED: T05: elapsed >= timeout_sec
        STAGE_BEGIN --> SAFE_ABORT: T06: Child detects unrecoverable condition

        TIMEOUT_EXPIRED --> ATTEMPT_FAILED: T07: Supervisor sends SIGKILL; child reaped
        SAFE_ABORT --> ATTEMPT_FAILED: T08: Child calls _exit(code != 0); child reaped

        STAGE_END --> ATTEMPT_SUCCEEDED: T09: All stages done; child exits 0
    }

    ATTEMPT_FAILED --> ATTEMPT_BEGIN: T10: attempt < max_attempts; dirty=0; writer=0; sleep 5s
    ATTEMPT_FAILED --> SUPERVISOR_STOP: T11: dirty=1 OR writer=1 OR attempt == max_attempts

    ATTEMPT_SUCCEEDED --> SUPERVISOR_STOP: T12: Success reaped; constructor returns 0
    SUPERVISOR_STOP --> [*]
```

---

## 3. Transition Specifications

### Transition T01: Initialization to First Attempt
- **SOURCE_STATE:** `START`
- **DEST_STATE:** `ATTEMPT_BEGIN`
- **CONDITION:** Constructor `load()` executed; `started` flag initialized; `wait_for_boot_quiet_window()` completes (`uptime.tv_sec >= MIN_BOOT_UPTIME_SEC`); attempt loop begins at index `attempt = 1`.
- **OBSERVABLE:**
  - `pr_info("waiting for boot allocator quiet window ...")` (if uptime < 120s)
  - `pr_success("preload supervisor pid=%d attempts=%d base_delay=%d p0_timeout=%d timeout=%d\n", ...)`
- **AMBIGUITY:** None; uniquely logged at supervisor startup.
- **SOURCE_REFERENCE:** `src/preload.c:114-156`

---

### Transition T02: Fork Child and Enter Stage
- **SOURCE_STATE:** `ATTEMPT_BEGIN`
- **DEST_STATE:** `STAGE_BEGIN`
- **CONDITION:** Parent executes `SYSCHK(fork())`; child PID > 0 returned to parent; child initializes `PR_SET_PDEATHSIG` and calls `run_exploit()`. Parent records `SYSCHK(clock_gettime(CLOCK_MONOTONIC, &started))`.
- **OBSERVABLE:**
  - Parent: `pr_success("exploit attempt=%d/%d pid=%d delay=%d ...\n", attempt, max_attempts, getpid(), delay_usec)`
  - Child: Stage entry logs (e.g. `pr_info("app fops stage=prepare-return ...")`).
- **AMBIGUITY:** If the child process is immediately descheduled or hangs before emitting its first stage log, the transition occurs in control flow but cannot be distinguished by child output until subsequent logs appear.
- **SOURCE_REFERENCE:** `src/preload.c:156-187`, `src/main.c:300-305`

---

### Transition T03: Complete Internal Stage
- **SOURCE_STATE:** `STAGE_BEGIN`
- **DEST_STATE:** `STAGE_END`
- **CONDITION:** Processing within a stage completes without error; shared atomic state published (e.g., `slide_ready`, `p0_ready`, or stage completion flags).
- **OBSERVABLE:**
  - `app_publish_p0_offset()`: `atomic_store(&app_p0_state->p0_ready, 1)`
  - `app_publish_slide_ready()`: `atomic_store(&app_p0_state->slide_ready, 1)`
  - `pr_info("slide pi stage=wait-timeout-accepted ...")`
  - `pr_info("app fops stage=trigger-return ...")`
- **AMBIGUITY:** Low; atomic variables provide immediate synchronization visible to the supervisor polling loop.
- **SOURCE_REFERENCE:** `src/preload.c:34-65`, `src/slide_app.c:192`, `src/main.c:364`

---

### Transition T04: Advance to Subsequent Stage
- **SOURCE_STATE:** `STAGE_END`
- **DEST_STATE:** `STAGE_BEGIN`
- **CONDITION:** Intermediate state verified; child advances execution to the next sequential stage without terminating.
- **OBSERVABLE:**
  - Child emits next stage initialization message (e.g., transition from slide phase to fops phase).
  - Supervisor sees `atomic_load(&app_p0_state->slide_ready) == 1`, dynamically expanding the active timeout ceiling from `p0_attempt_timeout_sec` (1200 s) to `attempt_timeout_sec` (2200 s).
- **AMBIGUITY:** None; evidenced by dynamic timeout threshold switch in supervisor polling.
- **SOURCE_REFERENCE:** `src/preload.c:201-206`, `src/main.c:300-365`

---

### Transition T05: Watchdog Timeout Expiry
- **SOURCE_STATE:** `STAGE_BEGIN`
- **DEST_STATE:** `TIMEOUT_EXPIRED`
- **CONDITION:** In supervisor polling loop: `waitpid(child, &status, WNOHANG)` does not return child; `SYSCHK(clock_gettime(CLOCK_MONOTONIC, &now))`; `time_t elapsed = now.tv_sec - started.tv_sec`; and `elapsed >= timeout_sec` (where `timeout_sec` is either `p0_attempt_timeout_sec` if pre-slide, or `attempt_timeout_sec` if post-slide).
- **OBSERVABLE:**
  - `pr_warning("exploit attempt=%d/%d timeout pid=%d seconds=%d\n", attempt, max_attempts, child, timeout_sec)`
- **AMBIGUITY:** None between pre-P0 and overall timeout, because the log string explicitly prints `seconds=%d`, showing whether 1200 or 2200 expired.
- **SOURCE_REFERENCE:** `src/preload.c:197-210`

---

### Transition T06: Child Controlled Abort
- **SOURCE_STATE:** `STAGE_BEGIN`
- **DEST_STATE:** `SAFE_ABORT`
- **CONDITION:** Child detects an unrecoverable condition, assertion failure, or invalid prerequisite state (e.g., page unavailable, pipe reset failed, or gate verification failure) and executes `_exit(code)` with `code != 0`. If the failure compromised kernel state, the child executes `app_publish_p0_dirty()` prior to exiting.
- **OBSERVABLE:**
  - Child emits specific warning/error log (e.g., `pr_warning("diagnostic stop after fops prepare...")` or `pr_error("app p0 shared state mmap failed...")`).
  - Child process terminates voluntarily.
- **AMBIGUITY:** If logging fails or stdout is blocked, non-zero exit status alone cannot indicate which specific stage aborted without inspecting exit code.
- **SOURCE_REFERENCE:** `src/preload.c:45-53, 144`, `src/main.c:309, 320, 340`

---

### Transition T07: Supervisor Terminating Timed-Out Child
- **SOURCE_STATE:** `TIMEOUT_EXPIRED`
- **DEST_STATE:** `ATTEMPT_FAILED`
- **CONDITION:** Supervisor issues `SYSCHK(kill(child, SIGKILL))`, then enters synchronous wait: `do { waited = waitpid(child, &status, 0); } while (waited < 0 && errno == EINTR)`. Child exit status reflects termination by `SIGKILL` (`WIFSIGNALED(status)` is true, `WTERMSIG(status) == 9`).
- **OBSERVABLE:**
  - `pr_warning("exploit attempt=%d/%d terminated signal=%d\n", attempt, max_attempts, WTERMSIG(status))` with `WTERMSIG == 9`.
- **AMBIGUITY:** Distinguishable from external `kill -9` by the mandatory preceding supervisor timeout warning emitted in T05.
- **SOURCE_REFERENCE:** `src/preload.c:210-215, 269-272`

---

### Transition T08: Reaping Aborted Child
- **SOURCE_STATE:** `SAFE_ABORT`
- **DEST_STATE:** `ATTEMPT_FAILED`
- **CONDITION:** Supervisor reaps the child via `waitpid(child, &status, WNOHANG)`. Status indicates voluntary exit with non-zero exit code: `WIFEXITED(status)` is true and `WEXITSTATUS(status) != 0`.
- **OBSERVABLE:**
  - `pr_warning("exploit attempt=%d/%d failed status=%d\n", attempt, max_attempts, WEXITSTATUS(status))`
- **AMBIGUITY:** None; exit status is logged directly.
- **SOURCE_REFERENCE:** `src/preload.c:273-276`

---

### Transition T09: Clean Attempt Completion
- **SOURCE_STATE:** `STAGE_END`
- **DEST_STATE:** `ATTEMPT_SUCCEEDED`
- **CONDITION:** All stages executed successfully; `run_exploit()` returns 0; child calls `_exit(0)`. Supervisor reaps child with `waited == child && WIFEXITED(status) && WEXITSTATUS(status) == 0`.
- **OBSERVABLE:**
  - Child: `pr_success("pipe-physrw-summary pid=%d done=%d root=%d ...")`
  - Supervisor: `pr_success("exploit completed attempt=%d/%d\n", attempt, max_attempts)`
- **AMBIGUITY:** None; explicit zero exit status and success log.
- **SOURCE_REFERENCE:** `src/preload.c:222-225`, `src/main.c:439-466`

---

### Transition T10: Clean Failure Retry
- **SOURCE_STATE:** `ATTEMPT_FAILED`
- **DEST_STATE:** `ATTEMPT_BEGIN`
- **CONDITION:** `attempt < max_attempts`, AND `atomic_load(&app_p0_state->writer_started) == 0`, AND `atomic_load(&app_p0_state->dirty) == 0`. Supervisor executes `sleep(5)` quiet delay and increments `attempt`.
- **OBSERVABLE:**
  - `pr_info("safe retry quiet delay seconds=5\n")`
  - Subsequent `pr_success("exploit attempt=%d/%d pid=%d ...")` with incremented attempt counter.
- **AMBIGUITY:** None.
- **SOURCE_REFERENCE:** `src/preload.c:277-281`

---

### Transition T11: Unsafe Failure or Exhaustion Stop
- **SOURCE_STATE:** `ATTEMPT_FAILED`
- **DEST_STATE:** `SUPERVISOR_STOP`
- **CONDITION:** Any of the following terminal conditions:
  1. `atomic_load(&app_p0_state->writer_started) != 0`: Stack writer was triggered; state cannot be cleanly reset.
  2. `atomic_load(&app_p0_state->dirty) != 0`: P0 oracle state was corrupted/dirtied.
  3. `attempt == max_attempts`: All retry opportunities exhausted.
- **OBSERVABLE:**
  - Condition 1: `pr_error("stack writer ran; refusing retry on this boot\n")`
  - Condition 2: `pr_error("p0 oracle state dirty or uncertain; refusing unsafe retry\n")`
  - Condition 3: `pr_error("exploit failed after %d independent attempts\n", max_attempts)`
  - Followed by supervisor process calling `_exit(1)`.
- **AMBIGUITY:** None; each stop reason emits a distinct error string before exiting.
- **SOURCE_REFERENCE:** `src/preload.c:228-232, 262-266, 283-285`

---

### Transition T12: Supervisor Normal Return
- **SOURCE_STATE:** `ATTEMPT_SUCCEEDED`
- **DEST_STATE:** `SUPERVISOR_STOP`
- **CONDITION:** `ATTEMPT_SUCCEEDED` achieved; supervisor `load()` constructor returns, allowing target application or process initialization to proceed normally.
- **OBSERVABLE:**
  - Execution returns from `load()`; target process continues normal runtime flow.
- **AMBIGUITY:** None.
- **SOURCE_REFERENCE:** `src/preload.c:224`
