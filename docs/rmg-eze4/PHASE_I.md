# Phase I — measurement architecture and synthetic validation harness

Phase I implements and tests a pure offline evidence pipeline. It consumes only caller-supplied normalized records, synthetic fixtures, and repository files. It contains no collection, device, privilege, compilation, or payload interface.

```text
L3_PARAMETERS_TOTAL: 19
VALIDATION_GROUPS: 12

OBSERVATION_SCHEMA_READY: YES
IDENTITY_MODEL_READY: YES
GROUP_CONTRACTS_READY: YES
ANALYSIS_LIBRARY_READY: YES
SYNTHETIC_FIXTURES_READY: YES
ATTRIBUTION_CHECKER_READY: YES
STOP_RULES_READY: YES
CROSS_BOOT_MODEL_READY: YES

PARAMETER_RULES_TESTED: 19
GROUPS_TESTED: 12

SYNTHETIC_TESTS_TOTAL: 133
SYNTHETIC_TESTS_PASSED: 133
SYNTHETIC_TESTS_FAILED: 0

E2_ENFORCEMENT_TOTAL: 0
E3_ENFORCEMENT_TOTAL: 3
E4_ENFORCEMENT_TOTAL: 16

P0_UNCERTAINTY_PRESERVED: YES
RAW_PROVENANCE_MODEL_READY: YES

STATIC_MODEL_CONTRADICTIONS: 0
PHASE_H_CONTRADICTIONS: 0
```

The 133 logical synthetic classification cases comprise 36 group cases, 38 parameter-rule cases, 30 must-validate guard cases, 10 malformed/edge cases, and 19 below-minimum evidence cases. The Python runner contains nine test methods with subtests for those cases and passed without failure. Structural CSV/JSON checks also passed.

The Phase H audit reproduced exactly: 19 L3 parameters; 12 groups; no `ROOT_UMH_PATH`; 7 correctness-critical, 9 reliability-critical, and 3 policy-only parameters; 9 P0-independent, 7 P0-dependent, and 3 P0-only parameters; compatibility minima E2=0, E3=3, and E4=16. No Phase H classification was changed.

Key behavior demonstrated:

- raw references and session/boot/condition provenance survive normalization and aggregation;
- evidence below a Phase H minimum cannot produce `COMPATIBLE`;
- contradictions, outliers, missing observables, condition drift, and wrong baseline/session evidence are surfaced rather than averaged away;
- partially or non-attributable records cannot support a validation conclusion;
- E4 aggregation keeps boot and condition partitions distinct;
- table membership, log absence, one label, and unresolved loader mapping cannot resolve P0 reachability or compatibility;
- all five must-validate parameters remain inconclusive under environment-only evidence.

Principal artifacts are the observation JSON schema, pure analysis library under `tools/rmg-eze4/analysis/`, synthetic fixtures/tests under `tools/rmg-eze4/tests/`, the 19-row measurement map, 12 group contracts, rule-test matrices, synthetic campaign report, and example 19-parameter campaign state.

No ADB command, hardware interaction, target generation, compilation, payload execution, vulnerable-path execution, kernel action, boot modification, flash, or reboot was performed.

## Final verdict

`MEASUREMENT_ARCHITECTURE_VALIDATED`
