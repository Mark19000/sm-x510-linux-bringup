# E4 Evidence Requirement Decomposition for `DEFAULT_ATTEMPT_TIMEOUT_SEC`

This document provides a technical rationale explaining why Phase H and Phase J0 mandate **Evidence Level E4** (`CROSS_BOOT_CROSS_CONDITION`) to certify `DEFAULT_ATTEMPT_TIMEOUT_SEC` as `COMPATIBLE`. It systematically evaluates each dimension of system variation and justifies the non-negotiability of the E4 threshold without inventing artificial sample counts.

---

## 1. Context and Canonical Evidence Levels

In the Phase H and Phase I validation architecture, evidence levels represent qualitative observation boundaries, not arbitrary sample counts:

- **E0 — STATIC ONLY:** Deductive reasoning from source, build artifacts, and headers without dynamic execution.
- **E1 — PASSIVE ENVIRONMENT OBSERVATION:** System baseline observation (uptime, kernel version, DTB) without invoking the target consumer.
- **E2 — CONTROLLED OBSERVATION OF RELEVANT CONSUMER:** Exactly one attributable execution of the relevant path.
- **E3 — REPEATED CONTROLLED OBSERVATION:** Multiple attributable executions under a single, static set of environment conditions.
- **E4 — CROSS-BOOT / CROSS-CONDITION VALIDATION:** Repeated attributable observations systematically spanning the necessary dimensions of system variation (e.g., cross-condition and cross-boot).

In `phase_h_evidence_requirements.csv`, the entry for `DEFAULT_ATTEMPT_TIMEOUT_SEC` is:
```csv
DEFAULT_ATTEMPT_TIMEOUT_SEC,E4,E3,Compatibility needs duration tails across conditions; repeated premature expiry can falsify.
```
While incompatibility can be definitively demonstrated at **E3** (if the timeout systematically truncates valid attempts under a single condition), certifying compatibility strictly demands **E4**.

---

## 2. Why E2 and E3 Are Insufficient for Compatibility

`DEFAULT_ATTEMPT_TIMEOUT_SEC` (2200 seconds) is an empirical upper bound on the duration distribution tail of an exploit attempt.

1. **Why E2 is Insufficient:**
   A single successful run ($T_{\text{attempt}} \le 2200$ s) merely demonstrates that on one specific boot, under one momentary CPU frequency, temperature, and memory layout, the path completed before the deadline. It provides zero statistical confidence regarding the variance, spread, or extreme tails of the execution time distribution.

2. **Why E3 is Insufficient:**
   Multiple runs conducted under identical laboratory conditions (e.g., immediate back-to-back executions on an idle tablet at room temperature) sample only a localized slice of execution latency. Real-world execution environments on Android devices exhibit severe latency inflation under background load, thermal throttling, and physical memory fragmentation. An empirical timeout deemed adequate at E3 can repeatedly expire under non-ideal real-world conditions, turning a viable bring-up path into systematic failure.

Therefore, `COMPATIBLE` status requires demonstrating that legitimate duration tails remain comfortably below 2200 seconds across the full operational spectrum of the device (E4).

---

## 3. Analysis of Relevant Dimensions of Variation

To satisfy E4, the measurement campaign must evaluate variation across specific physical and software dimensions. The relevance of each dimension is analyzed below:

### 3.1 Boot Identity (`BOOT_ID`)
- **Status:** **RELEVANT (SECONDARY / STRUCTURAL)**
- **Technical Basis:**
  - On each boot, the Linux kernel physical allocator initializes with different fragmentation states depending on early boot firmware reservations and hardware memory mapping.
  - Kernel Address Space Layout Randomization (KASLR) selects a distinct kernel image base offset per boot, modulating the distance between kernel text and physical map structures.
  - While `DEFAULT_ATTEMPT_TIMEOUT_SEC` is designated as `P0_INDEPENDENT` (because stage-labelled timing separates P0 search duration from overall duration), cross-boot validation ensures that boot-to-boot allocator fragmentation and daemon startup states do not shift post-boot stage latencies past the timeout threshold.

### 3.2 Condition Identity (`CONDITION_ID`)
- **Status:** **CRITICALLY RELEVANT (MANDATORY)**
- **Technical Basis:**
  - The Samsung Exynos 1380 operates in a highly dynamic mobile OS environment where background services (`system_server`, Google Play Services, DEX optimization, media indexing) intermittently consume significant CPU and memory bandwidth.
  - The condition model must define distinct execution conditions:
    1. **Baseline / Idle Condition:** System settled, CPU load low, background services quiet.
    2. **Stressed / Background Load Condition:** Active background threads, high I/O throughput, or concurrent processes competing for execution resources.
  - Cross-condition coverage (`CROSS_CONDITION_REQUIRED = YES` in `phase_i_parameter_measurement_map.csv`) is an absolute requirement for G11.

### 3.3 CPU and Load Variation
- **Status:** **CRITICALLY RELEVANT (MANDATORY)**
- **Technical Basis:**
  - **Heterogeneous CPU Topology:** Exynos 1380 has an octa-core big.LITTLE configuration consisting of:
    - 4x ARM Cortex-A78 performance cores (up to 2.4 GHz)
    - 4x ARM Cortex-A55 efficiency cores (up to 2.0 GHz)
  - If child or supervisor threads migrate between Cortex-A78 and Cortex-A55 cores (or if core pinning is preempted by scheduler throttling), execution throughput drops substantially.
  - **Thermal Throttling:** Under sustained workload or elevated ambient temperature, Samsung's Thermal Engine actively scales down core frequencies and shuts down big cores. This dramatically inflates stage duration tails. Compatibility requires verifying that the 2200-second ceiling accommodates throttled CPU states.

### 3.4 Memory Availability and Allocator Pressure
- **Status:** **HIGHLY RELEVANT**
- **Technical Basis:**
  - Exploit stages perform substantial kernel memory grooming, socket buffer allocation, and page spraying (e.g. `SKB_SEND_SIZE`, `SLIDE_RECLAIM_SENDS`).
  - When system memory is constrained, kernel page allocation enters slow-path direct reclaim (`alloc_pages` slowpath), increasing allocation latency by orders of magnitude.
  - The duration of setup and reclaim loops is directly sensitive to memory pressure.

### 3.5 Attempt History (First Attempt vs Retries)
- **Status:** **RELEVANT**
- **Technical Basis:**
  - The supervisor runs up to `max_attempts` (default 8).
  - Attempt 1 executes in a cold process state.
  - If Attempt 1 fails cleanly after discovering P0, the supervisor stores the discovered offset in the environment (`SLIDE_P0_OFFSET = 0x...`), allowing Attempt 2 to skip the physical oracle scan entirely.
  - Conversely, failed attempts that groomed memory leave behind allocated or dirty pages, altering the memory allocation landscape for subsequent attempts.
  - Evaluating durations across both first-attempt and retry contexts is necessary to ensure the timeout accommodates cold-start Grooming.

### 3.6 Scheduler Variability
- **Status:** **RELEVANT**
- **Technical Basis:**
  - CFS (Completely Fair Scheduler) runqueue latencies vary based on the number of runnable tasks.
  - Priority Inheritance (PI) futex waits (`SLIDE_WAIT_NSEC`) and thread synchronization points depend on timely kernel scheduling.
  - Latency spikes directly extend the elapsed monotonic clock time (`now.tv_sec - started.tv_sec`).

### 3.7 Other Environmental State (Android Lifecycle & Cgroup Freezing)
- **Status:** **HIGHLY RELEVANT (POTENTIAL CONFOUNDER)**
- **Technical Basis:**
  - Android utilizes the cgroup v2 freezer subsystem to freeze background processes. If the target application enters a frozen state during an attempt, CPU execution halts while `CLOCK_MONOTONIC` continues ticking.
  - Test conditions must maintain a valid execution state (e.g., holding wake locks or maintaining foreground process state) so that system freeze anomalies are not erroneously attributed to timeout policy inadequacy.

---

## 4. Exclusion of Arbitrary Sample Counts

In strict adherence to Phase H and Phase I architecture principles:
- **No sample count is invented or prescribed.**
- Rather than declaring an arbitrary number of trials (e.g. "run 50 times"), the validity of an E4 campaign is defined by **structural coverage of the relevant partitions**:
  1. At least two distinct, verified operational conditions (`len(conditions) >= 2`).
  2. Distinct boot sessions where boot-level variation is being tested (`len(boots) >= 2`).
  3. Continuous capture of device monotonic duration across all observed attempts.
  4. Zero unexplained outliers or contradictory results.
- If duration observations across all tested valid condition partitions demonstrate that empirical completion tails fall below the 2200-second threshold with adequate safety margin, the parameter is validated as `COMPATIBLE`.
