# Phase J2.1-R1 Replay Pipeline Verification Report

## 1. Replay Pipeline Architecture

The Phase J2.1-R1 offline replay pipeline tests deterministic attribution across all evidence processing stages:

```text
[RAW Session Directory]
       │
       ▼
 1. Non-recursive Manifest Closure (manifest.sha256)
       │
       ▼
 2. Ingestion & Normalizer (tools/rmg-eze4/analysis/validator.py)
       │
       ├── Schema v2.2.1 Structural Check
       ├── Event Grammar v2.1.1 Typed Payload Validation
       └── Semantic Invariants (post-fork duration, headroom, 1.1s sanity)
       │
       ▼
 3. Trial Classification (phase_j2_decision_table.csv)
       │
       ├── trial_terminal_class
       ├── trial_validity
       └── trial_evidence_vote
       │
       ▼
 4. E4 Aggregation Engine (tools/rmg-eze4/analysis/aggregator.py)
       │
       ├── 3 Boots x 2 Conditions x 2 Trials Partition Check
       ├── Invalid Trial Caps Check (<=1 per boot, <=2 total)
       ├── Falsification Gate (>=3 same-condition timeouts across >=2 boots)
       └── Compatibility Gate (100% compatible votes, 0 incompatible votes)
       │
       ▼
[Final Campaign Verdict]
```

---

## 2. Replay Scenarios & Verified Outcomes

| Scenario ID | Pipeline Input / Injected State | Expected Verdict | Verified Result |
| :--- | :--- | :--- | :--- |
| `SCN_01` | 12 valid trials ($T \le 2195\text{ s}$), 3 boots, 2 conditions, 2 per cell | `COMPATIBLE` | **PASS** |
| `SCN_02` | 11 valid passes, 1 attributable timeout ($T \ge 2200\text{ s}$) | `INCONCLUSIVE` | **PASS** |
| `SCN_03` | 3 attributable timeouts in `SETTLED_NOMINAL` across Boots 1 and 2 | `INCOMPATIBLE` | **PASS** |
| `SCN_04` | 2 attributable timeouts on Boot 1 only (fails $\ge 2$ boots) | `INCONCLUSIVE` | **PASS** |
| `SCN_05` | 1 timeout in `SETTLED_NOMINAL`, 1 in `ELEVATED_VALID` | `INCONCLUSIVE` | **PASS** |
| `SCN_06` | Boundary test: $T = 2195.000\text{ s}$ from post-fork | `COMPATIBLE_VOTE` | **PASS** |
| `SCN_07` | Mid-boundary test: $T = 2197.500\text{ s}$ from post-fork | `VALID` + `NO_VOTE` | **PASS** |
| `SCN_08` | Invalid trial cap breached: 2 invalid trials on Boot 1 | `INVALID_EXPERIMENT` | **PASS** |
| `SCN_09` | Invalid trial cap breached: 3 invalid trials across campaign | `INVALID_EXPERIMENT` | **PASS** |
| `SCN_10` | Child explicit failure (`exit_code = 1`) with intact telemetry | `VALID` + `NO_VOTE` | **PASS** |
| `SCN_11` | Child signal crash (`SIGSEGV`) with intact telemetry | `VALID` + `NO_VOTE` | **PASS** |
| `SCN_12` | $P_0$ duration ($300\text{ s}$) does not reset candidate watchdog epoch | `COMPATIBLE_VOTE` | **PASS** |
| `SCN_13` | Exact candidate watchdog boundary ($T = 2200.0\text{ s}$) | `INCOMPATIBLE_VOTE` | **PASS** |
| `SCN_14` | $C_1$ unseparated $P_0$ delay present during candidate timeout | `INVALID` + `NO_VOTE` | **PASS** |
| `SCN_15` | $C_1$ detector coverage gap ($P_0$ markers missing) | `INCONCLUSIVE` + `NO_VOTE` | **PASS** |
| `SCN_16` | $C_2$ cgroup freezer event active during trial | `INVALID` + `NO_VOTE` | **PASS** |
| `SCN_17` | $C_2$ detector monitoring gap $> 500\text{ ms}$ | `INCONCLUSIVE` + `NO_VOTE` | **PASS** |
| `SCN_18` | $C_3$ thermal throttling trip point excursion active | `INVALID` + `NO_VOTE` | **PASS** |
| `SCN_19` | $C_3$ detector monitoring gap $> 2500\text{ ms}$ | `INCONCLUSIVE` + `NO_VOTE` | **PASS** |
| `SCN_20` | Monotonic clock jump backward ($t_{\text{end}} < t_{\text{start}}$) | Rejected (`TIME_REVERSAL`) | **PASS** |
| `SCN_21` | Supervisor integer clock delta $> 1.1\text{ s}$ vs monotonic | Rejected (`CLOCK_CORRELATION`) | **PASS** |
| `SCN_22` | Boot ID mutation detected mid-trial | Rejected (`BOOT_MUTATION`) | **PASS** |
| `SCN_23` | Active event grammar version mismatch (`1.0.0` vs `2.1.1`) | Rejected (`GRAMMAR_VERSION`) | **PASS** |
| `SCN_24` | Stock Image digest mismatch | Rejected (`IMAGE_DIGEST`) | **PASS** |
| `SCN_25` | Unbound run package identity in offline design template | Accepted (`TEMPLATE_VALID`) | **PASS** |

---

## 3. Replay Conclusion
All 25 synthetic replay scenarios executed offline and verified that:
1. Canonical J2 watchdog epoch (post-fork monotonic) is strictly preserved.
2. Canonical E4 falsification threshold ($\ge 3$ timeouts in same condition across $\ge 2$ boots) and invalid caps ($\le 1$/boot, $\le 2$ total) are mechanically enforced.
3. Decoupling of lifecycle failure (`CHILD_EXPLICIT_FAILURE`, `CHILD_SIGNAL_FAILURE`) from telemetry validity is maintained.
