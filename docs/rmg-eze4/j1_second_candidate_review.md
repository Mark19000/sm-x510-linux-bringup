# Second Candidate Review: `SLIDE_KSNITCH_APPENDED_FUTEXES`

This document provides an in-depth static audit of `SLIDE_KSNITCH_APPENDED_FUTEXES`, the second eligible parameter identified during the Phase J0 prioritization review. In accordance with user instructions, this review is conducted **strictly offline**, evaluating source implementation, failure mechanisms, resource limits, existing safety guards, and its readiness for future second-wave validation without proposing runtime values or execution instructions.

---

## 1. Candidate Identity and J0 Status

- **Parameter:** `SLIDE_KSNITCH_APPENDED_FUTEXES`
- **Canonical Target Value (ZG3):** `2048` (`src/targets/gts9fewifi-X510XXSEEZG3/target.h:97`)
- **Validation Group:** `G7` (`phase_h_validation_groups.csv`)
- **Classification:** `RELIABILITY_CRITICAL`
- **Failure Effect:** `RESOURCE_EXHAUSTION`
- **P0 Dependency:** `P0_INDEPENDENT` (Score: 70)
- **Dependency Closure:** `YES` (no incoming hard or soft parameter dependencies)
- **Observable Clarity:** `HIGH`
- **Attribution Quality:** `HIGH`
- **J0 Decision:** Eligible, but deferred in the first wave in favor of `DEFAULT_ATTEMPT_TIMEOUT_SEC` because `RESOURCE_EXHAUSTION` is a less contained failure mode than `TIMEOUT`.

---

## 2. Technical Investigation: Why `RESOURCE_EXHAUSTION` is a Concern

A static trace of `SLIDE_KSNITCH_APPENDED_FUTEXES` reveals how the parameter is consumed across the codebase:

### 2.1 Consumer Code Path
1. **Configuration (`src/page.c:551-558` and `src/util.c:366-400`):**
   When `payload_mode == PAGE_PAYLOAD_SLIDE`, `configure_kernelsnitch_profile()` sets:
   ```c
   appended_futexes = SLIDE_KSNITCH_APPENDED_FUTEXES; // 2048
   kernelsnitch_set_profile(ks, appended_futexes, repeat_measurement, average);
   ```
2. **Execution (`src/kernelsnitch/kernelsnitch.h:518`):**
   Inside `__measure_prepare()` / collision detection:
   ```c
   __increase(ks, ID, ks->appended_futexes);
   ```
3. **Thread Spawning Loop (`src/kernelsnitch/kernelsnitch.h:164-178`):**
   ```c
   static void __increase(struct kernelsnitch_shared_state *ks, size_t id, size_t amount)
   {
       ks->increase_tids = calloc(amount, sizeof(*ks->increase_tids));
       ASSERT_pr((ks->increase_tids != NULL), "failed to allocate futex waiter ids\n");
       ks->increase_count = amount;
       ks->increase_id = id;
       for (size_t i = 0; i < amount; ++i) {
           struct inc_arg *inc_arg = calloc(1, sizeof(struct inc_arg));
           inc_arg->id = id;
           inc_arg->ks = ks;
           SYSCHK(pthread_create(&ks->increase_tids[i], 0, __do_increase,
                                 (void *)inc_arg));
       }
       WAIT();
   }
   ```

### 2.2 Concrete Resource Demands
When `amount = 2048`, `__increase()` creates **2048 concurrent POSIX threads** via `pthread_create()`, each running `__do_increase()` and blocking in the kernel on `SYS_futex` with `FUTEX_WAIT_PRIVATE`.

This imposes four severe, simultaneous resource demands:
1. **User-Space Virtual Address Space:**
   On 64-bit Android Bionic, default thread stack size is typically 1 MB (or 2 MB). Allocating 2048 thread stacks reserves 2 GB to 4 GB of virtual memory in the process address space.
2. **Kernel Task Structures & Kernel Stacks:**
   Each thread requires a kernel `struct task_struct` and a dedicated kernel stack (16 KB on ARM64). Spawning 2048 threads permanently consumes $2048 \times 16\text{ KB} = 32\text{ MB}$ of unevictable kernel low-memory allocations.
3. **Thread and PID Limits:**
   Linux and Android enforce system-wide and cgroup-level thread limits:
   - `/proc/sys/kernel/threads-max`
   - `/proc/sys/kernel/pid_max`
   - Android cgroup v2 `pids.max` (often clamped to 512 or 1024 for standard application UIDs).
   If `amount` exceeds the available thread/PID quota, `pthread_create()` fails with `EAGAIN`.
4. **Kernel Futex Hash Bucket Memory:**
   2048 `futex_q` structures are linked into the kernel's internal futex hash bucket corresponding to `id`, increasing lock contention and memory footprint.

If thread creation fails, `SYSCHK(pthread_create(...))` terminates the process immediately. If system memory is tight, spawning 2048 threads can trigger the Linux Out-Of-Memory (OOM) killer, terminating the supervisor or target process.

---

## 3. Definite vs Conditional Consequence

**The consequence is CONDITIONAL, not definite.**

- **Under Adequate System Capacity:**
  If the host system has ample free memory ($> 1\text{ GB}$ available RAM) and the process is not restricted by a tight `pids.max` cgroup limit ($> 2048$ allowed threads), all 2048 threads are created cleanly. They sleep on the private futex, establish the necessary timing distinction in hash bucket 128, and are subsequently joined and freed by `__decrease()` without incident.
- **Under Resource Constraints:**
  The consequence manifests as `RESOURCE_EXHAUSTION` (`EAGAIN` or OOM) only when:
  1. Ambient memory pressure is elevated;
  2. The process runs under an Android cgroup with strict thread restrictions; or
  3. The value is scaled up beyond physical system capacity.

---

## 4. Existing Bounds, Guards, and Cleanup Mechanisms

Static audit confirms that substantial guards and cleanup routines are **already present** in the repository:

1. **Environment Parser Bounding (`src/util.c:390-391`):**
   ```c
   appended_futexes = rmg_profile_env_size(
       "RMG_KSNITCH_APPENDED", appended_futexes, 256, 4096);
   ```
   The supervisor provides an explicit override alias `RMG_KSNITCH_APPENDED` that enforces a minimum bound of 256 and an upper ceiling of 4096.
2. **Profile Assertion Guard (`src/kernelsnitch/kernelsnitch.h:439`):**
   ```c
   ASSERT_pr((appended_futexes > 0), "invalid appended futex count\n");
   ```
   Rejects zero or negative values at setup.
3. **Heap Allocation Guard (`src/kernelsnitch/kernelsnitch.h:167`):**
   ```c
   ASSERT_pr((ks->increase_tids != NULL), "failed to allocate futex waiter ids\n");
   ```
   Ensures the thread tracking array was allocated before spawning threads.
4. **Thread Creation Return Check (`src/kernelsnitch/kernelsnitch.h:174`):**
   ```c
   SYSCHK(pthread_create(&ks->increase_tids[i], 0, __do_increase, (void *)inc_arg));
   ```
   Traps any `pthread_create` error (`EAGAIN`, `EINVAL`, `EPERM`) immediately.
5. **Deterministic Cleanup and Reaping (`src/kernelsnitch/kernelsnitch.h:180-195`):**
   ```c
   static void __decrease(struct kernelsnitch_shared_state *ks)
   {
       if (!ks->increase_tids)
           return;
       ks->inc_futex[ks->increase_id] = 1;
       SYSCHK(__futex((unsigned int *)&ks->inc_futex[ks->increase_id],
                      FUTEX_WAKE_PRIVATE, INT_MAX, NULL, NULL, 0));
       for (size_t i = 0; i < ks->increase_count; ++i)
           SYSCHK(pthread_join(ks->increase_tids[i], NULL));
       ks->inc_futex[ks->increase_id] = 0;
       free(ks->increase_tids);
   }
   ```
   `__decrease()` safely flips the futex value, wakes all waiters simultaneously via `FUTEX_WAKE_PRIVATE` with `INT_MAX`, synchronously joins all spawned threads via `pthread_join()`, and deallocates the tracking array. This guarantees that threads do not leak across stages or attempts.

---

## 5. Observable Isolation

Can the observable for `SLIDE_KSNITCH_APPENDED_FUTEXES` be cleanly isolated?

**YES.**
- **Group G7 Contract (`phase_h_validation_groups.csv`):**
  Group G7 isolates `SLIDE_KSNITCH_APPENDED_FUTEXES` from the paired measurement parameters (`SLIDE_KSNITCH_REPEAT_MEASUREMENT` and `SLIDE_KSNITCH_AVERAGE` in G5) and screening parameters (G6).
- **Observable Metrics:**
  1. Thread creation success vs failure (`EAGAIN`).
  2. Memory and thread count changes observable in `/proc/self/status` (`Threads:`).
  3. Candidate population coverage in hash bucket 128.
- Because candidate population is established prior to running the repeat measurement loops, resource consumption can be attributed directly to `SLIDE_KSNITCH_APPENDED_FUTEXES` without confounding from statistical averaging.

---

## 6. Verdict: Promotion to Second-Wave Candidate

- **Second-Wave Suitability:** **HIGHLY SUITABLE (LEAD SECOND-WAVE CANDIDATE)**
- **Technical Justification:**
  1. Meets all mandatory eligibility requirements (P0-independent, dependency-closed, high observable clarity, high attribution).
  2. Has clear static bounds `[256, 4096]` already coded in `util.c`.
  3. Has complete lifecycle cleanup implemented via `__decrease()`.
  4. Was deferred in J0 solely due to conservative prioritization favoring `TIMEOUT` over `RESOURCE_EXHAUSTION`.
- **Recommendation:** Retain `DEFAULT_ATTEMPT_TIMEOUT_SEC` as the sole First-Wave parameter. Promote `SLIDE_KSNITCH_APPENDED_FUTEXES` to the primary candidate for the **Second Wave** controlled validation design once the First Wave execution design is finalized.
