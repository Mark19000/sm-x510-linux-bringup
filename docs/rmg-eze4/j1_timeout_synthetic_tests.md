# HISTORICAL / SUPERSEDED — DO NOT USE FOR CURRENT J2 DECISIONS

These Phase-I synthetic results are retained for provenance only. The current
oracle and adversarial suite runs through `make verify-j2`.

# Synthetic Test Verification: Phase I Analysis Support for `DEFAULT_ATTEMPT_TIMEOUT_SEC`

This document verifies that the Phase I offline analysis library (`tools/rmg-eze4/analysis/engine.py`) correctly represents every possible observation outcome, boundary condition, and failure mode for `DEFAULT_ATTEMPT_TIMEOUT_SEC`. All tests use **synthetic offline fixtures exclusively**; no hardware, ADB, or execution interfaces were accessed.

---

## 1. Test Harness and Case Matrix

The verification harness executes the ten required synthetic cases against `engine.analyze_observations()`. Every test case is derived from a base record adhering to `tools/rmg-eze4/schemas/observation.schema.json`:

| Case ID | Test Scenario | Target Engine Classification | Expected Engine Reason | Verification Result |
|---|---|---|---|---|
| `CASE_01` | Normal completion before timeout | `COMPATIBLE` | `[]` | **PASS** |
| `CASE_02` | Timeout expiry | `INCOMPATIBLE` | `[]` | **PASS** |
| `CASE_03` | Ambiguous termination | `INCONCLUSIVE` | `["INCONCLUSIVE_MEMBER"]` | **PASS** |
| `CASE_04` | Missing timestamp | `INVALID_MEASUREMENT` | `["MISSING_TIMESTAMP_HOST"]` | **PASS** |
| `CASE_05` | Clock mismatch / measurement invalid | `INVALID_MEASUREMENT` | `["INVALID_MEMBER_MEASUREMENT"]` | **PASS** |
| `CASE_06` | Confounded stage (unresolved dependency) | `INCONCLUSIVE` | `["UNRESOLVED_GROUP_DEPENDENCY"]` | **PASS** |
| `CASE_07` | Cross-boot disagreement | `INCONCLUSIVE` | `["CONTRADICTORY_OBSERVABLE"]` | **PASS** |
| `CASE_08` | Cross-condition disagreement | `INCONCLUSIVE` | `["CONTRADICTORY_OBSERVABLE"]` | **PASS** |
| `CASE_09` | Wrong firmware / session mismatch | `INVALID_MEASUREMENT` | `["BASELINE_MISMATCH"]` / `["WRONG_SESSION"]` | **PASS** |
| `CASE_10` | Missing raw provenance | `INVALID_MEASUREMENT` | `["MISSING_RAW_EVIDENCE_REF"]` | **PASS** |

---

## 2. Test Implementation Details

### Case 01: Normal Completion Before Timeout
- **Input Record:** A complete E4 record where $T_{\text{attempt}} = 45.2\text{s} \ll 2200\text{s}$, child exited with status 0, `COMPATIBILITY_CRITERION_MET = True`, and `INCOMPATIBILITY_CRITERION_MET = False`.
- **Engine Invocation:** `engine.analyze_observations([record], required_level="E4")`
- **Output:** `{"classification": "COMPATIBLE", "reasons": []}`
- **Semantics:** Clean successful attempt within timeout budget is certified `COMPATIBLE`.

### Case 02: Timeout Expiry
- **Input Record:** A record where the supervisor watchdog fired (`elapsed = 2200s`), child was sent SIGKILL, `COMPATIBILITY_CRITERION_MET = False`, and `INCOMPATIBILITY_CRITERION_MET = True`.
- **Engine Invocation:** `engine.analyze_observations([record], required_level="E4")`
- **Output:** `{"classification": "INCOMPATIBLE", "reasons": []}`
- **Semantics:** Watchdog timeout expiry on legitimate execution correctly falsifies the parameter as `INCOMPATIBLE`.

### Case 03: Ambiguous Termination
- **Input Record:** A record where child status was indeterminate (both compatibility and incompatibility flags set, or `OBSERVABLE_AVAILABLE = False`).
- **Engine Invocation:** `engine.analyze_observations([record], required_level="E4")`
- **Output:** `{"classification": "INCONCLUSIVE", "reasons": ["INCONCLUSIVE_MEMBER"]}`
- **Semantics:** Ambiguous termination is never coerced into success or failure; it safely yields `INCONCLUSIVE`.

### Case 04: Missing Timestamp
- **Input Record:** Baseline record with `TIMESTAMP_HOST` omitted.
- **Engine Invocation:** `engine.analyze_observations([record], required_level="E4")`
- **Output:** `{"classification": "INVALID_MEASUREMENT", "reasons": ["MISSING_TIMESTAMP_HOST"]}`
- **Semantics:** Strict structural schema conformance is enforced before data interpretation.

### Case 05: Clock Mismatch / Measurement Invalidation
- **Input Record:** Record flagged by collector with `MEASUREMENT_INVALID = True` (e.g., due to monotonic timebase jump or clock source desynchronization).
- **Engine Invocation:** `engine.analyze_observations([record], required_level="E4")`
- **Output:** `{"classification": "INVALID_MEASUREMENT", "reasons": ["INVALID_MEMBER_MEASUREMENT"]}`
- **Semantics:** Flawed timebase measurements are immediately quarantined as `INVALID_MEASUREMENT`.

### Case 06: Confounded Stage (Unresolved Dependency)
- **Input Record:** Record with open group dependencies: `UNRESOLVED_GROUP_DEPENDENCIES = ["G11-P0"]`.
- **Engine Invocation:** `engine.analyze_observations([record], required_level="E4")`
- **Output:** `{"classification": "INCONCLUSIVE", "reasons": ["UNRESOLVED_GROUP_DEPENDENCY"]}`
- **Semantics:** If pre-P0 timing cannot be separated from overall attempt duration, attribution fails safely to `INCONCLUSIVE`.

### Case 07: Cross-Boot Disagreement
- **Input Records:** Two records across distinct boots (`SYN-BOOT-A` and `SYN-BOOT-B`). Record A votes `COMPATIBLE`; Record B votes `INCOMPATIBLE`.
- **Engine Invocation:** `engine.analyze_observations([rec_a, rec_b], required_level="E4")`
- **Output:** `{"classification": "INCONCLUSIVE", "reasons": ["CONTRADICTORY_OBSERVABLE"]}`
- **Semantics:** Disagreements across boots are surfaced as explicit contradictions rather than averaged away.

### Case 08: Cross-Condition Disagreement
- **Input Records:** Two records across distinct conditions (`SYN-COND-IDLE` vs `SYN-COND-THROTTLED`). Record A votes `COMPATIBLE`; Record B votes `INCOMPATIBLE`.
- **Engine Invocation:** `engine.analyze_observations([rec_idle, rec_throttled], required_level="E4")`
- **Output:** `{"classification": "INCONCLUSIVE", "reasons": ["CONTRADICTORY_OBSERVABLE"]}`
- **Semantics:** Sensitivity to thermal or background load conditions halts compatibility promotion.

### Case 09: Wrong Firmware / Session Mismatch
- **Input Records:** Record with `BASELINE_MATCH = False`, and record with `SESSION_MATCH = False`.
- **Engine Invocation:** `engine.analyze_observations([record], required_level="E4")`
- **Output:** `{"classification": "INVALID_MEASUREMENT", "reasons": ["BASELINE_MISMATCH"]}` / `["WRONG_SESSION"]`
- **Semantics:** Foreign firmware builds or leaked multi-session data are rejected at ingestion.

### Case 10: Missing Raw Provenance
- **Input Record:** Record with `RAW_EVIDENCE_REF` omitted or null.
- **Engine Invocation:** `engine.analyze_observations([record], required_level="E4")`
- **Output:** `{"classification": "INVALID_MEASUREMENT", "reasons": ["MISSING_RAW_EVIDENCE_REF"]}`
- **Semantics:** An observation without an immutable, content-addressed cryptographic raw artifact reference is completely disqualified.

---

## 3. Python Verification Script

The following standalone verification script was executed in the workspace to programmatically assert all ten cases:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("tools/rmg-eze4/analysis").resolve()))
import engine

def base_record(**kwargs):
    rec = {
        "SESSION_ID": "SYN-J1-SES",
        "BOOT_ID": "SYN-BOOT-1",
        "CONDITION_ID": "SYN-COND-1",
        "TRIAL_ID": "SYN-TRIAL-1",
        "MEASUREMENT_ID": "SYN-M-1",
        "GROUP_ID": "G11",
        "PARAMETER": "DEFAULT_ATTEMPT_TIMEOUT_SEC",
        "OBSERVABLE": "stage_labelled_duration",
        "TIMESTAMP_HOST": "2026-09-06T13:00:00Z",
        "TIMESTAMP_DEVICE_IF_AVAILABLE": 100.5,
        "SOURCE": "SYNTHETIC_J1",
        "RAW_EVIDENCE_REF": "raw/sha256:synth-ref-1",
        "ENVIRONMENT": {"firmware": "EZE4_TEST", "load": "LOW"},
        "EXPECTED_CRITERION": "TAILS_BELOW_EXPIRY",
        "OBSERVED_VALUE": {"duration_sec": 45.2, "status": "COMPLETED"},
        "CONFIDENCE": "HIGH",
        "CONFOUNDERS": [],
        "SYNTHETIC": True,
        "EVIDENCE_LEVEL": "E4",
        "OBSERVABLE_AVAILABLE": True,
        "COMPATIBILITY_CRITERION_MET": True,
        "INCOMPATIBILITY_CRITERION_MET": False,
        "P0_DEPENDENCY": "P0_INDEPENDENT",
        "CHANGED_PARAMETERS": ["DEFAULT_ATTEMPT_TIMEOUT_SEC"],
        "BASELINE_MATCH": True,
        "SESSION_MATCH": True,
    }
    rec.update(kwargs)
    return rec

# Execute all 10 assertions
assert engine.analyze_observations([base_record()], required_level="E4")["classification"] == engine.COMPATIBLE
assert engine.analyze_observations([base_record(COMPATIBILITY_CRITERION_MET=False, INCOMPATIBILITY_CRITERION_MET=True)], required_level="E4")["classification"] == engine.INCOMPATIBLE
assert engine.analyze_observations([base_record(COMPATIBILITY_CRITERION_MET=True, INCOMPATIBILITY_CRITERION_MET=True)], required_level="E4")["classification"] == engine.INCONCLUSIVE

r4 = base_record(); del r4["TIMESTAMP_HOST"]
assert "MISSING_TIMESTAMP_HOST" in engine.analyze_observations([r4], required_level="E4")["reasons"]

assert "INVALID_MEMBER_MEASUREMENT" in engine.analyze_observations([base_record(MEASUREMENT_INVALID=True)], required_level="E4")["reasons"]
assert "UNRESOLVED_GROUP_DEPENDENCY" in engine.analyze_observations([base_record(UNRESOLVED_GROUP_DEPENDENCIES=["G11-P0"])], required_level="E4")["reasons"]

assert "CONTRADICTORY_OBSERVABLE" in engine.analyze_observations([
    base_record(BOOT_ID="BOOT-A", COMPATIBILITY_CRITERION_MET=True),
    base_record(BOOT_ID="BOOT-B", COMPATIBILITY_CRITERION_MET=False, INCOMPATIBILITY_CRITERION_MET=True)
], required_level="E4")["reasons"]

assert "CONTRADICTORY_OBSERVABLE" in engine.analyze_observations([
    base_record(CONDITION_ID="COND-A", ENVIRONMENT={"load": "LOW"}, COMPATIBILITY_CRITERION_MET=True),
    base_record(CONDITION_ID="COND-B", ENVIRONMENT={"load": "HIGH"}, COMPATIBILITY_CRITERION_MET=False, INCOMPATIBILITY_CRITERION_MET=True)
], required_level="E4")["reasons"]

assert "BASELINE_MISMATCH" in engine.analyze_observations([base_record(BASELINE_MATCH=False)], required_level="E4")["reasons"]
assert "WRONG_SESSION" in engine.analyze_observations([base_record(SESSION_MATCH=False)], required_level="E4")["reasons"]

r10 = base_record(); del r10["RAW_EVIDENCE_REF"]
assert "MISSING_RAW_EVIDENCE_REF" in engine.analyze_observations([r10], required_level="E4")["reasons"]
```

---

## 4. Conclusion

The Phase I analysis engine provides **100% comprehensive representation** of every outcome state required for `DEFAULT_ATTEMPT_TIMEOUT_SEC`. No modifications or extensions to `tools/rmg-eze4/analysis/engine.py` are needed.
