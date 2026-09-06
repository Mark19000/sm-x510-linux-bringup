# GEMINI TEST INDEPENDENCE & SEMANTIC INTEGRITY AUDIT
## Comprehensive Repository Audit: Root-My-Galaxy EZE4 (`tab-s9-fe-linux`)

```yaml
AUDIT: INDEPENDENT_TEST_ORACLE_AND_SEMANTIC_INTEGRITY
REPOSITORY: tab-s9-fe-linux
SCOPE: ENTIRE_REPOSITORY (docs/rmg-eze4, tools/rmg-eze4, tests/, configs/, reports/)
AUDITOR: Antigravity / Gemini Research Pair Programmer
DATE: 2026-09-06
STATUS: FORMAL_AUDIT_COMPLETE
L3_EXECUTION_PERFORMED: NO
SEMANTIC_MODIFICATIONS: NONE (Audit Only)
ARTIFACTS_PRODUCED:
  - docs/rmg-eze4/audit/GEMINI_TEST_INDEPENDENCE_AUDIT.md
  - docs/rmg-eze4/audit/DUPLICATED_TRUTH.csv
  - docs/rmg-eze4/audit/TEST_ORACLE_MAP.csv
  - docs/rmg-eze4/audit/ACTIVE_SUPERSEDED_REFERENCES.csv
```

---

## 1. EXECUTIVE SUMMARY & AUDIT CHARTER

An exhaustive repository-wide audit was conducted across `tab-s9-fe-linux` targeting five core failure classes:
1. **Self-confirming tests**: Tests whose test oracle or assertions are derived directly from the code under test or share the same helper/fixture rather than an independent authoritative truth.
2. **Duplicated critical constants**: Physical hardware identity, timing boundaries, protocol versions, and decision thresholds scattered across multiple mirrors without automated provenance enforcement.
3. **Error-cancelling bugs**: Latent defects where an erroneous implementation combined with a matching erroneous test fixture yields a false `PASS`.
4. **Active code depending on superseded J2/J2.1 semantics**: Code executed in active test suites that implements outdated Phase I or intermediate J2/J2.1 normalizations rather than canonical J2.1-R1 / R1.1 semantics.
5. **Cross-artifact inconsistencies**: Divergences across Markdown narratives, CSV decision tables, JSON Schemas, Python validators (`validator.py`), aggregators (`aggregator.py`, `engine.py`), and test fixtures.

### Key Audit Findings Summary
- **Critical Error-Cancelling Bug Identified**: `tools/rmg-eze4/tests/fixtures/phase_j2_timeout_scenarios.json` scenario `single_timeout` explicitly downgrades `evidence_level` to `"E2"` to force `tools/rmg-eze4/analysis/engine.py` to return `INCONCLUSIVE` due to `INSUFFICIENT_EVIDENCE_LEVEL`. If evaluated at the required level `"E4"`, `engine.py` would return `INCOMPATIBLE` because line 149 contains the superseded Phase I single-timeout falsification rule (`if votes[INCOMPATIBLE]: return INCOMPATIBLE`). The test suite passes with 0 failures by exploiting this error-cancelling mask.
- **Active Test Suite Uses Superseded Engine**: `tools/rmg-eze4/tests/test_phase_j2_design.py` actively runs during `python3 -m unittest discover` and imports `engine.py` (the Phase I classifier) rather than `aggregator.py` (the canonical Phase J2/J2.1-R1 campaign aggregator). It tests single-trial records that expect `COMPATIBLE` or `INCOMPATIBLE`, in direct violation of the canonical E4 contract ($3\times 2\times 2$ partition, $\ge 12$ trials, repeated-timeout falsification).
- **Self-Confirming Consistency Checker**: `tools/rmg-eze4/analysis/check_consistency.py` defines its own internal hardcoded `CANONICAL_*` constants and checks them against `validator.py` and test record generators (`make_valid_record()`, `generate_trial_record()`). Because all three files were written with copy-pasted strings, `test_phase_j2_1_r1_consistency.py` passes tautologically without checking against actual physical device files in `docs/rmg-eze4/runtime-evidence/20260906T094426Z/raw/`.
- **Schema v1 vs Schema v2 Inconsistencies**: `docs/rmg-eze4/phase_j2_observation_schema.json` (Schema v1) defines `clock_source: "DEVICE_CLOCK_MONOTONIC"`, `freezer_state: "NOT_FROZEN"`, unconstrained regex for fingerprints, and flat candidate properties. This directly conflicts with `phase_j2_observation_schema_v2.json` (Schema v2.2.1), `validator.py`, and `phase_j2_clock_model.md` which mandate `"CLOCK_MONOTONIC"`, `"THAWED"`, exact `const` physical identities, and nested `candidate_identity`.
- **Factual Discrepancy in Pipeline Test Fixture**: `tests/test_u11_repro_compare.py` mock metadata pairs `target_stock=X510XXUCEZE4` with `kernel_release=5.15.180` (rather than canonical `5.15.189-android13-3-33478785`). The test passes only because both compared mock trees share the identical erroneous fixture.

---

## 2. AUDIT DIMENSION 1: SELF-CONFIRMING TESTS

A test is self-confirming (tautological) when its expected oracle is not derived from an external specification or physical authority, but instead mirrors the internal implementation, shares identical constants, or uses mock generators written specifically to pass the assertion.

### 2.1 Analysis of `test_phase_j2_1_r1_consistency.py` (`check_consistency.py`)
- **Location**: `tools/rmg-eze4/analysis/check_consistency.py`, lines 24–35, 178–199.
- **Design Flaw**:
  `check_consistency.py` declares 10 constants (`CANONICAL_MODEL`, `CANONICAL_DEVICE`, `CANONICAL_INCREMENTAL`, `CANONICAL_BUILD_FINGERPRINT`, `CANONICAL_KERNEL_IDENTITY`, `CANONICAL_IMAGE_SHA256`, `CANONICAL_SCHEMA_VERSION`, `CANONICAL_GRAMMAR_VERSION`, `CANONICAL_SECURITY_PATCH`).
  In Step 4, it imports `validator.py` and asserts that `getattr(validator, ...)` equals its own constants.
  In Step 5, it imports `make_valid_record` from `test_phase_j2_1_r1_schema.py` and `generate_trial_record` from `test_phase_j2_1_r1_replay.py`, asserting that their dictionary outputs equal its own constants.
- **Independence Evaluation**:
  This is a closed circular loop. Neither `validator.py`, `check_consistency.py`, nor the test fixture generators verify against the physical Phase G raw evidence files (`docs/rmg-eze4/runtime-evidence/20260906T094426Z/raw/0[1-6]*.txt`). If a developer made a coordinated error across these three Python files, `test_phase_j2_1_r1_consistency.py` would report `PASS: Cross-artifact consistency verified` despite the discrepancy.

### 2.2 Analysis of `test_phase_j2_1_r1_schema.py` (`make_valid_record`)
- **Location**: `tools/rmg-eze4/tests/test_phase_j2_1_r1_schema.py`, lines 14–238.
- **Design Flaw**:
  `make_valid_record()` hardcodes:
  ```python
  t_start = 100_000_000_000
  t_end = 100_000_000_000 + 200_000_000_000
  duration_ns = t_end - t_start
  duration_sec = duration_ns / 1e9
  headroom_sec = 2200.0 - duration_sec
  ```
  Inside `validator.py` lines 172–183:
  ```python
  expected_duration_ns = t_end - t_start
  expected_duration_sec = expected_duration_ns / 1e9
  expected_headroom = 2200.0 - expected_duration_sec
  ```
- **Independence Evaluation**:
  The positive test `test_positive_canonical_record` simply asserts `validate_observation_record(make_valid_record()) == (True, [])`. Because the fixture generator faithfully mimics the implementation code line for line, it confirms only that the generator matches the validator, not that the validator correctly validates arbitrary valid schema records.
- **Positive Note**: The negative tests (`test_neg_01` through `test_neg_identity_*`) in this file DO exhibit high independence, systematically injecting single mutations to ensure rejection.

### 2.3 Analysis of `test_phase_j2_1_r1_replay.py` (`make_clean_e4_campaign`)
- **Location**: `tools/rmg-eze4/tests/test_phase_j2_1_r1_replay.py`, lines 304–327.
- **Design Flaw**:
  `make_clean_e4_campaign()` constructs a 12-element list specifically populated with:
  - 3 boots (indices 1, 2, 3)
  - 2 conditions (`SETTLED_NOMINAL`, `ELEVATED_VALID`)
  - 2 repetitions per partition
  - All durations in $[160.0\text{s}, 170.0\text{s}]$ ($< 2195.0\text{s}$)
  - `trial_evidence_vote = "COMPATIBLE_VOTE"`
  `test_scn_01_clean_compatible_campaign` asserts `aggregate_campaign(records)["verdict"] == COMPATIBLE`.
- **Independence Evaluation**:
  The test oracle is hardcoded to `COMPATIBLE`. The input data was constructed explicitly to satisfy the nested loops inside `aggregator.py`. While structurally sound as an integration smoke test, it does not challenge the aggregator with real-world distribution variance or edge-case partitions.

### 2.4 Analysis of `test_phase_i_analysis.py` & `test_phase_j0_selection.py`
- **Location**: `tools/rmg-eze4/tests/test_phase_i_analysis.py`, lines 50, 58, 62; `test_phase_j0_selection.py`, lines 39, 44.
- **Design Flaw**:
  Expected values are referenced directly from the module under test:
  ```python
  expected = engine.INCONCLUSIVE if group == "G10" else engine.COMPATIBLE
  self.assertEqual(got["classification"], expected)
  ```
- **Independence Evaluation**:
  By binding `expected` to `engine.COMPATIBLE` and `engine.INCONCLUSIVE`, the test adopts the implementation symbols as its ground truth. If `engine.COMPATIBLE` were mutated or corrupted, the assertion would still compare identity against the corrupted symbol.

---

## 3. AUDIT DIMENSION 2: DUPLICATED CRITICAL CONSTANTS (TRUTH INVENTORY)

The repository maintains critical constants and decision rules across dozens of files. A formal audit was conducted on every critical constant, tracing the authoritative ground truth, all mirrors, whether each mirror is generated or manually duplicated, and whether any mirror diverges.

Complete tabular data is codified in `docs/rmg-eze4/audit/DUPLICATED_TRUTH.csv`. Below is the forensic analysis of the eleven critical constant families:

### 1. `DEFAULT_ATTEMPT_TIMEOUT_SEC = 2200`
- **Authoritative Source**: Upstream Samsung target exploit header (`target.h` / `preload.c`), documented in `docs/rmg-eze4/phase_h_l3_inventory.csv` (line 7).
- **Mirrors**:
  - Schemas: `docs/rmg-eze4/phase_j2_observation_schema_v2.json`, `phase_j2_observation_schema.json`
  - Gates: `docs/rmg-eze4/phase_j2_go_gates.csv` (Gate G07)
  - Contracts & Reports: `PHASE_J2.md`, `PHASE_J2_1_R1.md`, `phase_j2_attribution.md`, `runtime_parameter_criticality.csv`, `empirical_parameter_triage.csv`, `eze4_target_readiness.csv`, `eze4_target_readiness_v2.csv`
  - Python Implementation: `validator.py` (lines 79, 180), `check_consistency.py` (lines 64, 180)
  - Python Tests: `test_phase_j2_1_r1_schema.py` (lines 19, 31), `test_phase_j2_1_r1_replay.py` (lines 43, 202), `test_phase_j2_design.py` (line 23), `test_phase_j0_selection.py` (lines 17, 31)
- **Generation Method**: Manually duplicated across 16+ files.
- **Divergence**:
  - *Structural Divergence*: Schema v1 (`phase_j2_observation_schema.json`) and `test_phase_j2_design.py` define this as a flat root property (`PARAMETER = "DEFAULT_ATTEMPT_TIMEOUT_SEC"`), whereas Schema v2 (`phase_j2_observation_schema_v2.json`), `validator.py`, and `test_phase_j2_1_r1_*.py` nest it under `candidate_identity.candidate_parameter`.

### 2. Pre-Slide Threshold (`DEFAULT_P0_ATTEMPT_TIMEOUT_SEC = 1200`)
- **Authoritative Source**: Upstream target exploit header (`target.h` / `preload.c`), documented in `docs/rmg-eze4/phase_h_l3_inventory.csv` (line 8).
- **Mirrors**: `j1_timeout_semantics.md`, `j1_supervisor_state_model.md`, `j1_timeout_confounders.md`, `phase_j2_state_model.md`, `phase_j2_clock_model.md`, `phase_j2_confounders.csv`, `phase_j2_decision_table.csv`, `phase_j2_event_grammar.json`, `phase_j2_1_taxonomy.md`, `PHASE_J2_1_R1.md`.
- **Generation Method**: Manually duplicated.
- **Divergence / Enforcement Gap**:
  - In Markdown/CSV documentation, 1200s is the strict timeout for pre-P0 slide preparation before `slide_ready`.
  - **Critical Gap in Code**: Neither `validator.py`, `aggregator.py`, nor `check_consistency.py` programmatically asserts or validates the 1200s pre-slide limit. In `validator.py`, `timing_metrics.p0_duration_seconds` is stored but never compared against `<= 1200.0s`.

### 3. Affirmative Headroom Boundary (`2195.0 s`)
- **Authoritative Source**: `docs/rmg-eze4/phase_j2_clock_model.md` (Section 3), `docs/rmg-eze4/phase_j2_e4_contract.md`.
- **Mirrors**: `phase_j2_1_taxonomy.md`, `phase_j2_decision_table.csv`, `PHASE_J2.md`, `PHASE_J2_1_R1.md`, `validator.py` (line 303), `test_phase_j2_1_r1_schema.py` (line 340), `test_phase_j2_1_r1_replay.py` (lines 376, 383), `test_phase_j2_design.py` (line 30).
- **Generation Method**: Manually duplicated.
- **Divergence**:
  - In `test_phase_j2_design.py`, line 30 sets `EXPECTED_CRITERION = "QUALIFYING_TERMINAL_BY_2195_SECONDS"`, but `engine.py` completely ignores this string and never inspects durations or timestamps.

### 4. One Timeout => `INCONCLUSIVE`
- **Authoritative Source**: `docs/rmg-eze4/phase_j2_e4_contract.md`, `docs/rmg-eze4/phase_j2_decision_table.csv` (row 5).
- **Mirrors**: `PHASE_J2_1_R1.md` (Section 28 Q3), `aggregator.py` (lines 130–134), `test_phase_j2_1_r1_replay.py` (test_scn_02).
- **Generation Method**: Manually duplicated.
- **Divergence**:
  - **Direct Contradiction**: `tools/rmg-eze4/analysis/engine.py` line 149 declares `INCOMPATIBLE` on a single timeout.
  - `j1_timeout_decision_rules.md` and `j1_timeout_synthetic_tests.md` state that single timeout expiry yields `INCOMPATIBLE`.

### 5. Incompatibility Threshold ($\ge 3$ Same-Condition Across $\ge 2$ Boots)
- **Authoritative Source**: `docs/rmg-eze4/phase_j2_e4_contract.md`, `docs/rmg-eze4/phase_j2_decision_table.csv` (row 6), `PHASE_J2_1_R1.md` (Blocker R1-03).
- **Mirrors**: `PHASE_J2_1_R1_1.md`, `aggregator.py` (lines 74–89), `test_phase_j2_1_r1_replay.py` (test_scn_03), `check_consistency.py` (lines 274–277).
- **Generation Method**: Manually duplicated.
- **Divergence**:
  - Entirely absent from `tools/rmg-eze4/analysis/engine.py`.

### 6. Invalid Trial Caps ($\le 1$ Per Boot, $\le 2$ Total)
- **Authoritative Source**: `docs/rmg-eze4/phase_j2_e4_contract.md`, `docs/rmg-eze4/phase_j2_stop_rules.csv` (rule S12).
- **Mirrors**: `phase_j2_decision_table.csv` (rows 19–20), `PHASE_J2.md`, `PHASE_J2_1_R1.md`, `PHASE_J2_1_R1_1.md`, `aggregator.py` (lines 59–71), `test_phase_j2_1_r1_replay.py` (test_scn_08, test_scn_09).
- **Generation Method**: Manually duplicated.
- **Divergence**:
  - Completely unrepresented in `engine.py`. In J2.1 pre-R1, superseded by `>25% invalid rate` before being reverted in R1.

### 7. $E4$ Partition Coverage ($\ge 3$ Boots $	imes 2$ Conditions $	imes \ge 2$ Trials = $\ge 12$ Total)
- **Authoritative Source**: `docs/rmg-eze4/phase_j2_e4_contract.md`, `docs/rmg-eze4/phase_j2_1_taxonomy.md`.
- **Mirrors**: `PHASE_J2.md`, `PHASE_J2_1_R1.md`, `PHASE_J2_1_R1_1.md`, `aggregator.py` (lines 92–127), `test_phase_j2_1_r1_replay.py` (`make_clean_e4_campaign`).
- **Generation Method**: Manually duplicated.
- **Divergence**:
  - `engine.py` only requires $\ge 2$ boots and $\ge 2$ conditions. It permits a single trial to be certified `COMPATIBLE` if cross-boot/condition flags are not set.

### 8. Exact Physical EZE4 Device Identity
- **Authoritative Source**: Phase G physical baseline captures in `docs/rmg-eze4/runtime-evidence/20260906T094426Z/raw/0[1-6]*.txt`:
  - Model: `SM-X510`
  - Codename: `gts9fewifi`
  - Incremental: `X510XXUCEZE4`
  - Fingerprint: `samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys`
  - Kernel Identity: `5.15.189-android13-3-33478785`
  - Security Patch: `2026-05-05`
- **Mirrors**: `phase_j2_runtime_identity_contract.md`, `phase_j2_observation_schema_v2.json`, `phase_j2_go_gates.csv`, `PHASE_J2_1_R1_1.md`, `configs/eze4-x510xxuceze4.env`, `validator.py`, `check_consistency.py`, `test_phase_j2_1_r1_schema.py`, `test_phase_j2_1_r1_replay.py`, `tests/test_eze4_pipeline.py`.
- **Divergence**:
  - `tests/test_u11_repro_compare.py` line 17 specifies `kernel_release=5.15.180` alongside `target_stock=X510XXUCEZE4`.
  - `docs/rmg-eze4/phase_j2_observation_schema.json` (Schema v1) defined unconstrained string patterns.
  - Pre-R1.1 documents used illustrative fingerprint `UP1A.231005.007`.

### 9. Stock Kernel Image SHA-256 Digest
- **Authoritative Source**: Binary SHA-256 of `artifacts/stock/images/Image.stock` (`ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9`), extracted from `boot.img` @ offset 4096.
- **Mirrors**: `phase_j2_runtime_identity_contract.md`, `phase_j2_observation_schema_v2.json`, `phase_j2_go_gates.csv` (Gate G05), `stock_rtmutex_binary_verification.md`, `artifact_inventory.md`, `p0_fingerprint_EZE4.generated.h`, `PHASE3A.md`, `PHASE3B.md`, `PHASE_J2_1_R1.md`, `PHASE_J2_1_R1_1.md`, `validator.py`, `check_consistency.py`, `test_phase_j2_1_r1_schema.py`, `test_phase_j2_1_r1_replay.py`.
- **Divergence**:
  - `reports/2026-08-23-u11-eze4-binary-abi-audit.md` line 25 recorded payload kernel `Image` SHA-256 as `0ab39cc588c12511023a3e156a3a047a01480bb11562401245ab1d44e5224d4e`.
  - In J2.1 pre-R1, Gate G05 erroneously bound the hash to `boot.img`.

### 10. Observation Schema Version (`2.2.1`)
- **Authoritative Source**: `docs/rmg-eze4/phase_j2_observation_schema_v2.json` (`properties.schema_version.const = "2.2.1"`).
- **Mirrors**: `phase_j2_go_gates.csv` (G12), `phase_j2_preexecution_matrix.csv`, `PHASE_J2_1_R1_1.md`, `validator.py`, `check_consistency.py`, `test_phase_j2_1_r1_schema.py`, `test_phase_j2_1_r1_replay.py`.
- **Divergence**:
  - `PHASE_J2_1_R1.md` (Blocker R1-11 and Section 4 Q13) cites `Schema v2.2.0`.
  - `phase_j2_observation_schema_v2.json` line 4 title is `PhaseJ2ObservationRecordV2_2`.
  - `phase_j2_observation_schema.json` and `observation.schema.json` lack version.

### 11. Event Grammar Version (`2.1.1`)
- **Authoritative Source**: `docs/rmg-eze4/phase_j2_event_grammar.json` (`grammar_version = "2.1.1"`).
- **Mirrors**: `phase_j2_observation_schema_v2.json`, `PHASE_J2_1_R1.md`, `PHASE_J2_1_R1_1.md`, `validator.py`, `check_consistency.py`, `test_phase_j2_1_r1_schema.py`, `test_phase_j2_1_r1_replay.py`.
- **Divergence**:
  - Lacking entirely from Schema v1 (`phase_j2_observation_schema.json`) and Phase I schema (`observation.schema.json`).

---

## 4. AUDIT DIMENSION 3: ERROR-CANCELLING BUGS

An error-cancelling bug occurs when an erroneous implementation is matched with an equally erroneous or rigged test fixture, resulting in a false `PASS`.

### Detailed Analysis of Error-Cancelling Cases

#### Case EC-01: Rigged `evidence_level: "E2"` in `phase_j2_timeout_scenarios.json`
- **Implementation Under Test**: `tools/rmg-eze4/analysis/engine.py`, lines 149–150:
  ```python
  if votes[INCOMPATIBLE]:
      return {"classification": INCOMPATIBLE, "reasons": []}
  ```
- **Test Code**: `tools/rmg-eze4/tests/test_phase_j2_design.py`, line 85:
  ```python
  actual = engine.analyze_observations(records, required_level="E4")["classification"]
  self.assertEqual(scenario["expected"], actual)
  ```
- **Test Fixture**: `tools/rmg-eze4/tests/fixtures/phase_j2_timeout_scenarios.json`, line 4:
  ```json
  {"id":"single_timeout","mode":"single","evidence_level":"E2","compatible":false,"incompatible":true,"expected":"INCONCLUSIVE"}
  ```
- **Mechanism of Cancellation**:
  The scenario is titled `single_timeout`. In canonical Phase J2 semantics, a single timeout must produce `INCONCLUSIVE` because falsification requires $\ge 3$ timeouts across $\ge 2$ boots.
  However, `engine.py` implements the superseded Phase I logic where a single timeout at `E4` produces `INCOMPATIBLE`.
  If the test fixture had set `evidence_level: "E4"`, `engine.py` would have returned `INCOMPATIBLE`, and `self.assertEqual("INCONCLUSIVE", "INCOMPATIBLE")` would have **FAILED**.
  To force `engine.py` to output `INCONCLUSIVE`, the test fixture was rigged with `evidence_level: "E2"`. In `engine.py` line 133:
  ```python
  if not enforce_evidence_level(supplied, required_level):
      return {"classification": INCONCLUSIVE, "reasons": ["INSUFFICIENT_EVIDENCE_LEVEL"]}
  ```
  Because `"E2"` is lower than `"E4"`, `engine.py` returns `INCONCLUSIVE` due to insufficient evidence level, completely bypassing the vote evaluation!
  The test passes, masking the critical bug in `engine.py`.

#### Case EC-02: `clean_incompatible` in `phase_j2_timeout_scenarios.json`
- **Implementation**: `engine.py` line 149 (`if votes[INCOMPATIBLE]: return INCOMPATIBLE`).
- **Fixture**: `phase_j2_timeout_scenarios.json` line 3:
  ```json
  {"id":"clean_incompatible","mode":"single","evidence_level":"E4","compatible":false,"incompatible":true,"expected":"INCOMPATIBLE"}
  ```
- **Mechanism of Cancellation**:
  A single trial record is submitted with `incompatible: true`. The fixture expects `INCOMPATIBLE`.
  Under canonical J2 E4 rules, a single trial record CANNOT certify incompatibility.
  Because both `engine.py` and the fixture share this obsolete single-record falsification rule, the test passes with exit code 0.

#### Case EC-03: `clean_compatible` in `phase_j2_timeout_scenarios.json`
- **Implementation**: `engine.py` line 154 (`if votes[COMPATIBLE]: return COMPATIBLE`).
- **Fixture**: `phase_j2_timeout_scenarios.json` line 2:
  ```json
  {"id":"clean_compatible","mode":"single","evidence_level":"E4","compatible":true,"incompatible":false,"expected":"COMPATIBLE"}
  ```
- **Mechanism of Cancellation**:
  A single trial record is submitted with `compatible: true`. The fixture expects `COMPATIBLE`.
  Under the canonical E4 contract, a campaign cannot be certified `COMPATIBLE` without 12 valid trials across 3 boots $	imes$ 2 conditions $	imes$ 2 trials.
  Because both implementation and fixture ignore partition coverage, the test passes.

#### Case EC-04: Replicated Headroom Formula in Test Helper and Validator
- **Implementation**: `tools/rmg-eze4/analysis/validator.py`, lines 180–182:
  ```python
  expected_headroom = 2200.0 - expected_duration_sec
  if abs(tm.get("canonical_headroom_seconds", 0.0) - expected_headroom) > 1e-6:
      errors.append("CANONICAL_HEADROOM_MISMATCH")
  ```
- **Test Code**: `tools/rmg-eze4/tests/test_phase_j2_1_r1_schema.py`, line 19:
  ```python
  headroom_sec = 2200.0 - duration_sec
  ```
- **Mechanism of Cancellation**:
  Both hardcode `2200.0` directly rather than querying `candidate_identity.candidate_value`. If `candidate_value` in the record were modified, both the helper and the validator would continue evaluating against `2200.0`, masking any discrepancy between candidate value and headroom calculation.

#### Case EC-05: Mock Metadata in `tests/test_u11_repro_compare.py`
- **Implementation**: `tools/u11_repro_compare.py::compare`.
- **Test Code**: `tests/test_u11_repro_compare.py`, lines 16–17:
  ```python
  "target_stock=X510XXUCEZE4", "kernel_release=5.15.180"
  ```
- **Mechanism of Cancellation**:
  The test helper `populate()` populates both `run-a` and `run-b` with identical mock metadata strings.
  The test asserts `result["reproducible"] == True`.
  Although `kernel_release=5.15.180` is factually inaccurate for EZE4 (which is `5.15.189`), the comparison passes because both directories share the identical wrong constant.

---

## 5. AUDIT DIMENSION 4: ACTIVE CODE DEPENDING ON SUPERSEDED J2/J2.1 SEMANTICS

Complete tabular records are codified in `docs/rmg-eze4/audit/ACTIVE_SUPERSEDED_REFERENCES.csv`. Below is the architectural breakdown:

### 5.1 The Split-Engine Architecture
The repository maintains two completely disjoint analysis engines:
1. `tools/rmg-eze4/analysis/engine.py` (`analyze_observations`):
   - Implements Phase I / early J1 semantics.
   - Expects flat uppercase schema fields (`SESSION_ID`, `BOOT_ID`, `GROUP_ID`, `OBSERVABLE`, etc.).
   - Falsifies the campaign on any single incompatible trial (`votes[INCOMPATIBLE]`).
   - Requires only 2 boots and 2 conditions; has no partition cells or invalid-trial caps.
2. `tools/rmg-eze4/analysis/aggregator.py` (`aggregate_campaign`):
   - Implements canonical Phase J2/J2.1-R1 semantics.
   - Expects normalized Schema v2.2.1 records.
   - Requires $\ge 3$ verified boots, both conditions per boot, $\ge 2$ valid trials per cell (12 minimum).
   - Enforces invalid trial caps ($\le 1$ per boot, $\le 2$ total).
   - Enforces repeated-attributable falsification ($\ge 3$ same-condition timeouts across $\ge 2$ boots; single timeout is `INCONCLUSIVE`).

### 5.2 Active Test Invocation of Superseded Code
`tools/rmg-eze4/tests/test_phase_j2_design.py` actively imports and tests `engine.py`!
When `python3 -m unittest discover -s tools/rmg-eze4/tests` is executed, `test_phase_j2_design.py` runs and passes 14 test cases against `engine.py`.
This means:
- The active repository test suite is testing and confirming superseded Phase I logic under the name of "Phase J2 Synthetic Design Tests".
- The canonical aggregator `aggregator.py` is tested only in `test_phase_j2_1_r1_replay.py`.

### 5.3 Active Documentation Citing Superseded Engine
- `docs/rmg-eze4/j1_timeout_synthetic_tests.md` claims that `engine.py` provides "100% comprehensive representation" of every outcome state for `DEFAULT_ATTEMPT_TIMEOUT_SEC`.
- `docs/rmg-eze4/PHASE_J2.md` Section O and `phase_j2_synthetic_dry_run.md` claim that Phase J2 design validation was achieved by passing the 14 fixtures through `engine.py`.

---

## 6. AUDIT DIMENSION 5: CROSS-ARTIFACT INCONSISTENCIES

| Category | Artifact A (Authoritative / Current) | Artifact B (Divergent / Superseded) | Nature of Inconsistency |
| :--- | :--- | :--- | :--- |
| **Schema Version** | `phase_j2_observation_schema_v2.json` (`2.2.1`), `validator.py` (`2.2.1`) | `PHASE_J2_1_R1.md` lines 37, 95 cites `Schema v2.2.0` | Narrative refers to pre-R1.1 version v2.2.0 |
| **Schema Title** | `phase_j2_observation_schema_v2.json` line 26 (`const: "2.2.1"`) | Line 4: `"title": "PhaseJ2ObservationRecordV2_2"` | Title lacks patch suffix `.1` |
| **Schema Structure** | `phase_j2_observation_schema_v2.json` (nested `candidate_identity`) | `phase_j2_observation_schema.json` (flat root property `candidate_parameter`) | Schema v1 is structurally incompatible with Schema v2 |
| **Clock Source** | `phase_j2_clock_model.md` (`CLOCK_MONOTONIC`), `validator.py` (`CLOCK_MONOTONIC`) | `phase_j2_observation_schema.json` (`DEVICE_CLOCK_MONOTONIC`) | Schema v1 diverges from clock contract and validator |
| **Freezer State** | `phase_j2_observation_schema_v2.json` (`THAWED`), `phase_j2_1_taxonomy.md` (`THAWED`) | `phase_j2_observation_schema.json` (`NOT_FROZEN`) | Schema v1 diverges from Schema v2 and taxonomy |
| **Single Timeout** | `phase_j2_decision_table.csv` row 5 (`INCONCLUSIVE`), `aggregator.py` (`INCONCLUSIVE`) | `engine.py` line 149 (`INCOMPATIBLE`), `j1_timeout_decision_rules.md` (`INCOMPATIBLE`) | Engine and J1 docs directly contradict J2 decision table |
| **Incompatibility** | `phase_j2_e4_contract.md` ($\ge 3$ same-condition across $\ge 2$ boots) | `engine.py` (1 timeout falsifies campaign), `phase_j2_timeout_scenarios.json` (`clean_incompatible`) | Engine and fixture contradict canonical E4 contract |
| **Invalid Caps** | `phase_j2_stop_rules.csv` S12 ($\le 1$/boot, $\le 2$ total) | `engine.py` (no invalid trial caps or accumulation) | Engine fails to enforce invalid trial limits |
| **Boot ID Format** | `phase_j2_observation_schema_v2.json` (`pattern: "^[a-f0-9]{64}$"`) | `test_phase_j2_design.py` (`"SYN-J2-B1"`), `test_phase_i_analysis.py` (`"SYN-BOOT-A"`) | Old test fixtures use non-SHA256 boot IDs |
| **Stock Image Hash** | `phase_j2_go_gates.csv` G05 (`ca56baf428...` for `Image.stock`) | `reports/2026-08-23-u11-eze4-binary-abi-audit.md` (`0ab39cc588...`) | Historical ABI report records divergent Image hash |
| **Kernel Release** | `configs/eze4-x510xxuceze4.env` (`5.15.189-android13-3-33478785`) | `tests/test_u11_repro_compare.py` line 17 (`kernel_release=5.15.180`) | Test fixture uses wrong kernel release string |

---

## 7. AUDIT QUESTIONS & CRITICAL CLAIMS CHECKLIST

| Claim / Constant to Track | Canonical Authoritative Value | Audited Status | Divergence or Error-Cancelling Finding |
| :--- | :--- | :--- | :--- |
| `DEFAULT_ATTEMPT_TIMEOUT_SEC` | `2200` | **CONFIRMED** | Flat vs nested schema divergence; numerical value 2200 is consistent. |
| Pre-slide threshold | `1200` | **CONFIRMED** | Documented consistently; programmatic validation check missing from validator. |
| Affirmative boundary | `2195` | **CONFIRMED** | Enforced in `validator.py`; ignored by `engine.py`. |
| One timeout => INCONCLUSIVE | `INCONCLUSIVE` | **CONTRADICTION** | `aggregator.py` enforces `INCONCLUSIVE`; `engine.py` asserts `INCOMPATIBLE`. Rigged in `phase_j2_timeout_scenarios.json`. |
| Incompatibility threshold | $\ge 3$ same condition across $\ge 2$ boots | **CONTRADICTION** | Present in `aggregator.py`, absent from `engine.py`. |
| Invalid caps | $\le 1$ per boot, $\le 2$ total | **CONTRADICTION** | Enforced in `aggregator.py`, completely absent from `engine.py`. |
| E4 partition coverage | $\ge 3$ boots $	imes 2$ conds $	imes \ge 2$ trials | **CONTRADICTION** | Enforced in `aggregator.py`; `engine.py` allows single-trial certification. |
| Exact EZE4 identity | `SM-X510`, `gts9fewifi`, `X510XXUCEZE4`, `BP4A...`, `5.15.189...` | **CONFIRMED** | Ground truth verified against Phase G raw captures; `test_u11_repro_compare.py` uses `5.15.180`. |
| `Image.stock` SHA256 | `ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9` | **CONFIRMED** | Bound strictly to `Image.stock` in G05, schema v2.2.1, and validator. |
| Schema version | `2.2.1` | **MINOR DISCREPANCY** | `PHASE_J2_1_R1.md` mentions `2.2.0`; schema title says `V2_2`; active schema is `2.2.1`. |
| Event grammar version | `2.1.1` | **CONFIRMED** | Consistent across Schema v2.2.1, Event Grammar, and validator. |

---

## 8. NON-SEMANTIC REMEDIATION RECOMMENDATIONS

In accordance with the prompt ("Do not modify semantics initially"), the following recommendations provide a non-semantic cleanup plan for future execution:

1. **Retire or Re-target `test_phase_j2_design.py`**:
   `test_phase_j2_design.py` should be updated to test `aggregator.py` using canonical Schema v2.2.1 fixtures, or renamed/isolated to `test_phase_i_legacy_j2_projection.py` to make clear that it exercises Phase I compatibility rather than canonical J2 campaign aggregation.
2. **Eliminate Rigged `evidence_level: "E2"`**:
   Replace the rigged `single_timeout` scenario in `phase_j2_timeout_scenarios.json` with a genuine multi-trial campaign scenario that tests `aggregator.py` and correctly asserts that 1 timeout produces `INCONCLUSIVE` at `E4`.
3. **Harmonize Schema Versions in Documentation**:
   Update `PHASE_J2_1_R1.md` (Blocker R1-11 and Section 4 Q13) to reference `Schema v2.2.1` rather than `Schema v2.2.0`, and fix the title in `phase_j2_observation_schema_v2.json` to `PhaseJ2ObservationRecordV2_2_1`.
4. **Archive Superseded Schema v1**:
   Mark `docs/rmg-eze4/phase_j2_observation_schema.json` as `DEPRECATED_SUPERSEDED_BY_V2_2_1` to prevent developers or scripts from validating against `DEVICE_CLOCK_MONOTONIC` or `NOT_FROZEN`.
5. **Harmonize Mock Metadata in Root Tests**:
   Update `tests/test_u11_repro_compare.py` line 17 to specify `kernel_release=5.15.189-android13-3-33478785` instead of `5.15.180`.
6. **Add Independent Raw Evidence Check to `check_consistency.py`**:
   Enhance `check_consistency.py` to parse the actual physical baseline text files in `docs/rmg-eze4/runtime-evidence/20260906T094426Z/raw/` rather than relying solely on its internal hardcoded constants.

---
