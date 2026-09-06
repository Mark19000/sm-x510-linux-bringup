# Phase F — canonical cleanup and non-invasive observation planning

```text
TOTAL_PARAMETERS: 180
ACCOUNTING_SUMS_TO_180: YES

CONFIRMED_IDENTICAL: 143
CONFIRMED_CHANGED: 10
LEGACY_INACTIVE: 3
NOT_APPLICABLE: 3
PROBABLY_REUSABLE: 0
RUNTIME_VALIDATION_REQUIRED: 20
STATICALLY_UNRESOLVED: 1

RUNTIME_L1_PASSIVE: 1
RUNTIME_L2_BENIGN_ACTIVE: 0
RUNTIME_L3_CONTROLLED_KERNEL_PATH: 19
RUNTIME_NOT_OBSERVABLE: 0

P0_OPEN_QUESTIONS: 5 (2 OPEN, 3 PARTIAL)
P0_LOADER_MAPPING_STATUS: OPEN
COLLISION_REACHABILITY_STATUS: UNKNOWN / INSUFFICIENT_EVIDENCE

ROOT_UMH_PATH_STATUS: RUNTIME_VALIDATION_REQUIRED (firmware-independent string; deployment existence unconfirmed)

FIRST_RUNTIME_OBSERVATION_PLAN_READY: YES
```

The three missing Phase E accounting rows were `NOT_APPLICABLE`. The three runtime-validation rows omitted from its 17-row criticality subtotal were the two P0 thresholds and `ROOT_UMH_PATH`; `PHASE_E_ERRATA.md` records the correction. Canonical categories now sum exactly to 180.

The observation plan can confirm stock context, effective command line/bootconfig, exposed topology and memory prerequisites, available logs, and the helper pathname's deployment state. Those observations do not validate the 19 parameters whose consumers require the controlled kernel path. No L3 procedure is included.

The P0 label domain remains distinct from proven physical placement. The current artifacts establish the oracle's `0x4000` label step, generic arm64/boot-protocol 2 MiB alignment, four structural collision rejections, and lack of same-boot recovery. They do not establish Samsung loader selection or collision-label reachability.

## Final verdict

`READY_FOR_NON_INVASIVE_RUNTIME_OBSERVATION`
