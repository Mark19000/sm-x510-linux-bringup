# Phase J2.1-R1 Result Taxonomy

This document establishes the four-layer normalized taxonomy for the `DEFAULT_ATTEMPT_TIMEOUT_SEC = 2200` compatibility campaign, strictly adhering to canonical J1/J2 semantics.

```text
Raw Lifecycle / Observation
            │
            ├─── 1. trial_terminal_class  (What happened to the child process?)
            │
            ├─── 2. trial_validity        (Was the measurement uncorrupted?)
            │
            ▼
   3. trial_evidence_vote                 (Does it vote affirmative, incompatible, or neutral?)
            │
            ▼
   4. campaign_verdict                    (Aggregated result across E4 partitions)
```

---

## 1. `trial_terminal_class` (Lifecycle Disposition)

Represents what physically occurred to the child attempt under supervisor management.

| Terminal Class | Description |
| :--- | :--- |
| `QUALIFYING_COMPLETION` | Child process exited voluntarily (`exit_code == 0`) within the candidate watchdog budget ($T \le 2200\text{ s}$). |
| `EXPECTED_P0_TIMEOUT` | Child process was terminated because pre-slide preparation ($P_0$) exceeded the separate $1200\text{ s}$ pre-slide watchdog prior to `slide_ready`. |
| `SUPERVISOR_OVERALL_TIMEOUT` | Supervisor candidate overall watchdog ($2200\text{ s}$ from post-fork) expired while child was executing overall candidate slide. |
| `CHILD_EXPLICIT_FAILURE` | Child process exited voluntarily with non-zero exit code (`exit_code != 0`) prior to watchdog expiration. |
| `CHILD_SIGNAL_FAILURE` | Child process terminated abnormally due to an unhandled signal (`SIGSEGV`, `SIGBUS`, `SIGABRT`, etc.) prior to supervisor watchdog. |
| `WRONG_STATE_TERMINATION` | Child process exited or signaled while supervisor was in an unexpected or out-of-protocol lifecycle state. |
| `EXTERNAL_INTERRUPTION` | External agent, transport disconnect (ADB drop), or system power event aborted the trial. |
| `MEASUREMENT_FAILURE` | Sensor loss, clock discontinuity, log truncation, corrupted pipe, or missing raw evidence invalidated trial telemetry. |

---

## 2. `trial_validity` (Measurement & Attribution Hygiene)

Represents whether trial telemetry is mathematically and empirically trustworthy.

| Validity Class | Definition |
| :--- | :--- |
| `VALID` | Measurement integrity verified: device monotonic clock unbroken, required observables present, raw SHA-256 provenance complete, and zero active destructive confounders ($C_1, C_2, C_3$). Note: Process failures (`CHILD_EXPLICIT_FAILURE`, `CHILD_SIGNAL_FAILURE`) are VALID if telemetry is intact. |
| `INVALID` | Measurement integrity failed: clock jump backwards, supervisor clock desync $> 1.1\text{ s}$, missing raw evidence, boot mutation mid-trial, or active destructive confounder ($C_1, C_2, C_3$ Present) destroyed causal attribution. Counts against invalid trial caps. |
| `INCONCLUSIVE` | Measurement was mechanically intact, but detector coverage gaps occurred ($C_1, C_2, C_3$ Unknown), preventing affirmative absence proof. Excluded from valid trial quotas; does not count against invalid caps. |

---

## 3. `trial_evidence_vote` (Candidate Evidence Contribution)

Represents how a trial contributes to the E4 candidate compatibility decision.

| Evidence Vote | Criteria |
| :--- | :--- |
| `COMPATIBLE_VOTE` | `trial_validity == VALID` AND `trial_terminal_class == QUALIFYING_COMPLETION` AND candidate elapsed duration $T \le 2195.000\text{ s}$ from post-fork. |
| `INCOMPATIBLE_VOTE` | `trial_validity == VALID` AND `trial_terminal_class == SUPERVISOR_OVERALL_TIMEOUT` AND duration $T \ge 2200.000\text{ s}$ from post-fork AND zero confounders. |
| `NO_VOTE` | Trial carries neither affirmative nor falsifying evidence. Includes: durations in $(2195.0\text{ s}, 2200.0\text{ s})$, pre-$P_0$ timeouts, child failures/crashes, invalid trials, and inconclusive confounder gaps. |

---

## 4. `campaign_verdict` (E4 Aggregation Output)

| Campaign Verdict | Canonical E4 Decision Rules |
| :--- | :--- |
| `COMPATIBLE` | Minimum 12 valid qualifying trials across $\ge 3$ verified boots; both `SETTLED_NOMINAL` and `ELEVATED_VALID` present on every boot; $\ge 2$ valid trials per boot $\times$ condition cell; $100\%$ `COMPATIBLE_VOTE` ($T \le 2195\text{ s}$); 0 `INCOMPATIBLE_VOTE`; 0 unresolved outliers; invalid trials $\le 1$ per boot and $\le 2$ total. |
| `INCOMPATIBLE` | $\ge 3$ valid attributable overall timeouts (`INCOMPATIBLE_VOTE`) in the **SAME defined condition** across **$\ge 2$ distinct verified boots**. (An isolated single timeout yields `INCONCLUSIVE`). |
| `INVALID_EXPERIMENT` | Exceeding invalid caps ($> 1$ invalid on any boot, or $> 2$ invalid total across campaign), or systemic raw manifest/cryptographic corruption, or unhandled state machine divergence. |
| `INCONCLUSIVE` | Campaign does not violate invalid caps and does not meet the $3 \times 2$ timeout threshold for incompatibility, but fails to satisfy complete E4 partition coverage or exhibits unresolvable partition disagreement. |
