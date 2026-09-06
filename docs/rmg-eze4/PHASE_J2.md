# Phase J2 — controlled execution design

Phase J2 specifies, but does not authorize or perform, an E4 measurement campaign for `DEFAULT_ATTEMPT_TIMEOUT_SEC=2200`. It is designed to prevent a real execution from being mistaken for valid evidence.

## A. Validation question

The precise question and exclusions are in `phase_j2_validation_question.md`. Adequacy means a qualifying, attributable supervisor-managed lifecycle reaches a recognized terminal event by 2195 device-monotonic seconds in every required E4 partition, with no overall watchdog expiry. The experiment does not test exploit/root success, P0 compatibility, or any other parameter.

## B. Experimental unit

One trial is one child PID from the parent's post-fork monotonic sample through reap. Experiment, boot, session, trial, attempt ordinal and PID identities mechanically distinguish every unit. Exact boundaries and pre/post-state are in `phase_j2_experimental_unit.md`.

## C. State machine

`phase_j2_state_model.md` defines gated, ready, pre-slide, overall, timeout, terminal, reaped, retry and session-terminal states. It separately classifies successful completion, expected pre-P0 timeout, overall supervisor timeout, explicit child failure, signal failure, wrong-state termination, external interruption and measurement failure. Signal 9 without the ordered timeout event is never inferred to be a supervisor timeout.

## D. Minimal observable set

`phase_j2_observables.csv` selects 8 logical observables from J1's exact 14: supervisor configuration, attempt start, `slide_ready`, timeout event, child terminal/reap, completion, lifecycle progress, and unsafe-retry disposition. These are sufficient to bind the configured value, distinguish 1200 vs 2200 seconds, prove qualifying progress, identify the terminal mechanism and prevent unsafe continuation. The six excluded observables are optional details or are subsumed without weakening attribution; each exclusion is justified in the CSV.

## E. Clock model

The sole authoritative duration clock is device `CLOCK_MONOTONIC`; no cross-domain subtraction is permitted. `phase_j2_clock_model.md` specifies nanosecond storage, implementation quantization, 100 ms polling, calibration tuples, ordering, skew limits and corruption thresholds. `CLOCK_BOOTTIME`, device/kernel log time and host wall/monotonic clocks remain secondary.

## F. HIGH-risk confounders

The exact J1 HIGH confounders are preserved in `phase_j2_confounders.csv`: unseparated P0 delay, Android cgroup freezing/suspension, and thermal throttling/core migration. Each has explicit presence/absence proof and deterministic invalid/inconclusive handling. None may be averaged away.

## G. Condition dimensions

`phase_j2_condition_dimensions.csv` includes only dimensions with a causal timing or attribution role: boot, declared condition class, attempt ordinal, foreground/freezer state, uptime, thermal/load/memory state, transport and scheduler context. Boot and two condition classes are intentionally varied; foreground/nonfrozen state and configuration are held constant; the rest are observed covariates.

## H. E4 coverage

`phase_j2_e4_contract.md` requires at least 3 boots, both declared conditions per boot, and 2 valid qualifying trials per boot/condition: 12 valid qualifying trials minimum. No more than 1 invalid trial per boot or 2 total is tolerated. A compatibility result requires every qualifying duration at or below 2195 seconds and no unresolved outlier or timeout. One attributable overall timeout is inconclusive; at least 3 in one condition across at least 2 boots establishes incompatibility. Cross-partition disagreement is surfaced, never averaged.

## I. GO gates

The 18 gates in `phase_j2_go_gates.csv` cover document, device, firmware, kernel, stock Image, real artifact, configuration, boot, pipeline, clock, storage, naming, transport, confounder detection, baseline, recoverability, isolation and independent-review prerequisites. Every gate is hard. Failure prevents execution.

## J. STOP rules

`phase_j2_stop_rules.csv` separates trial, session and experiment STOP. It covers unexpected transitions, missing evidence, HIGH confounders, transport/logging loss, resource exhaustion, unsafe state, repeated malformed evidence, identity mismatch, reboot, device instability/new behavior, clock corruption, invalid caps and unrelated changes. Evidence is preserved; continuation always requires the specified review/gate reset.

## K. Result taxonomy

Every trial receives exactly one validity class:

- `VALID`: identity, provenance, clocks, required observables, condition stability and attribution all pass. It contributes `COMPATIBLE_VOTE`, `INCOMPATIBLE_VOTE`, or `NO_VOTE` according to lifecycle coverage and terminal outcome.
- `INVALID`: measurement hygiene or hard identity/clock/condition rules fail. It is retained and counts against invalid caps; it is not a failed parameter trial.
- `INCONCLUSIVE`: the record is structurally honest but cannot answer the candidate question, for example pre-P0 timeout, incomplete qualifying progress, partial logs, external signal, or unresolved confounder.

Campaign outputs are only `COMPATIBLE`, `INCOMPATIBLE`, `INCONCLUSIVE`, or `INVALID_EXPERIMENT`. Valid compatible votes reach `COMPATIBLE` only under the complete E4 contract. Valid attributable repeated overall timeouts reach `INCOMPATIBLE` only under the deterministic falsification rule. Missing coverage/disagreement yields `INCONCLUSIVE`; identity corruption or exceeded invalid caps yields `INVALID_EXPERIMENT`.

## L. Decision table

`phase_j2_decision_table.csv` deterministically covers clean completion, variance, missing headroom, confounded/unconfounded timeouts, cross-boot/condition disagreement, insufficient/invalid evidence, clock disagreement, unexpected state, reboot, ADB/host timing loss, partial logs, wrong identity, pre-P0 timeout and early child failure.

## M. Normalized record

`phase_j2_observation_schema.json` (Schema v1, deprecated; superseded by Schema v2.2.1 `phase_j2_observation_schema_v2.json`) defines the initial machine-readable trial record, including all requested identity, condition, timestamp, duration, state, observable, confounder, validity, outcome, raw-reference and note fields. Active J2.1-R1 evaluations are governed by Schema v2.2.1. Its `phase_i_projection` retains compatibility with the existing Phase I analyzer. Every derived value must cite raw SHA-256 evidence.

## N. Raw evidence

`phase_j2_raw_evidence_contract.md` specifies per-session/trial identity, boot, clock, condition, stdout, stderr, structured events, process status, system log, transport and manifest artifacts; naming, capture boundaries, producers, hashes and normalization are explicit. The immutable chain remains `RAW -> SHA256 -> NORMALIZED -> ANALYSIS -> REPORT`.

## O. Synthetic dry-run

Fourteen required J2 fixtures passed through the existing Phase I analyzer. The complete Phase I/J0/J2 invocation passed all 16 test methods. Details are in `phase_j2_synthetic_dry_run.md`; fixtures and their test are under `tools/rmg-eze4/tests/`. Any future regression blocks execution.

## P. Attribution

`phase_j2_attribution.md` lists held, intentionally varied, observed and contaminating variables. Causal attribution fails on configuration drift, unseparated P0 time, freezer/external interruption/deadlock, unplanned thermal drift, evidence/clock loss, reboot, unsafe retry or concurrent experimentation.

## Q. Parameter isolation

This campaign validates only `DEFAULT_ATTEMPT_TIMEOUT_SEC`. Evidence concerning `SLIDE_KSNITCH_APPENDED_FUTEXES` or any protected MUST_VALIDATE parameter is tagged `INCIDENTAL_OBSERVATION_ONLY`, excluded from compatibility flags and sent to a separate future review.

## R. Human checklist

`phase_j2_preexecution_checklist.md` supplies the requested explicit checkboxes without any exploit command. It includes separate authorization and independent approval checks.

## S. Pre-execution matrix and blockers

`phase_j2_preexecution_matrix.csv` records design completeness and execution blockers. Two run-specific contracts cannot truthfully be completed during design-only J2: the exact real payload/collector/configuration hash manifest does not yet exist, and device-specific sensor/load thresholds for the two condition classes have not been independently frozen. Real L3 authorization is also explicitly absent. These do not make the measurement design ambiguous; they correctly prevent execution until a separately reviewed runbook binds concrete artifacts and thresholds.

```yaml
PHASE: J2

PRIMARY_CANDIDATE:
  DEFAULT_ATTEMPT_TIMEOUT_SEC

DESIGN_ONLY:
  YES

REAL_L3_EXECUTION_PERFORMED:
  NO

VALIDATION_QUESTION_DEFINED:
  YES

EXPERIMENTAL_UNIT_DEFINED:
  YES

STATE_MODEL_COMPLETE:
  YES

MINIMAL_OBSERVABLE_SET_COMPLETE:
  YES

CLOCK_MODEL_COMPLETE:
  YES

HIGH_RISK_CONFOUNDERS_ACCOUNTED:
  3/3

E4_COVERAGE_CONTRACT_COMPLETE:
  YES

GO_GATES_COMPLETE:
  YES

STOP_RULES_COMPLETE:
  YES

DECISION_TABLE_COMPLETE:
  YES

RAW_EVIDENCE_CONTRACT_COMPLETE:
  YES

ATTRIBUTION_MODEL_COMPLETE:
  YES

SYNTHETIC_DRY_RUN:
  PASS

REAL_EVIDENCE_ACCEPTANCE_CONTRACT:
  COMPLETE

SECOND_CANDIDATE_ISOLATED:
  YES

BLOCKERS:
  - APPROVED_REAL_ARTIFACT_MANIFEST_NOT_YET_BOUND
  - DEVICE_SPECIFIC_CONDITION_THRESHOLDS_NOT_YET_FROZEN
  - REAL_L3_EXECUTION_NOT_AUTHORIZED

FINAL_VERDICT:
  PRIMARY_VALIDATION_EXPERIMENT_DESIGNED_WITH_BLOCKERS
```
