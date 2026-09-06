# Phase J0 — first-wave controlled-validation candidate selection

Phase J0 scores the canonical 19 L3 parameters and selects the smallest first wave using only repository evidence and the Phase I offline analyzer. It performs no validation.

```text
L3_PARAMETERS_CONSIDERED: 19
P0_INDEPENDENT: 9
FIRST_WAVE_ELIGIBLE: 2
FIRST_WAVE_SELECTED: 1

SELECTED_1: DEFAULT_ATTEMPT_TIMEOUT_SEC
SELECTED_2: NONE
SELECTED_3: NONE

E3_SELECTED: 0
E4_SELECTED: 1

MUST_VALIDATE_DEFERRED: 5
P0_DEPENDENT_DEFERRED: 10
DEPENDENCY_BLOCKED: 13
ATTRIBUTION_BLOCKED: 16
FAILURE_SEMANTICS_BLOCKED: 12

PHASE_I_SYNTHETIC_GUARDS_PASS: YES
```

Counts may overlap because they are independent filters, not disjoint accounting buckets. `P0_DEPENDENT_DEFERRED` includes seven `P0_DEPENDENT` and three `P0_ONLY` parameters. `DEPENDENCY_BLOCKED` counts unresolved incoming hard or soft parameter dependencies that prevent clean interpretation. `ATTRIBUTION_BLOCKED` counts rows below `HIGH`. `FAILURE_SEMANTICS_BLOCKED` counts `WRONG_STATE`, `FALSE_CLASSIFICATION`, `RESOURCE_EXHAUSTION`, or `UNKNOWN` consequences.

The score is an offline prioritization aid, not a Phase H reclassification. It rewards P0 independence, closed dependencies, high observable clarity/attribution, preferred containment, and lower evidence burden; mandatory eligibility remains the controlling decision. `DEFAULT_ATTEMPT_TIMEOUT_SEC` ranks first because it is P0-independent, dependency-closed, policy-only, directly observable through stage-labelled duration/expiry, and has the preferred `TIMEOUT` consequence. Its E4 requirement remains unchanged.

`SLIDE_KSNITCH_APPENDED_FUTEXES` also satisfies the mandatory eligibility predicates, but is not selected: `RESOURCE_EXHAUSTION` is explicitly disfavored and a more contained candidate exists. The five must-validate parameters, every P0-dependent/P0-only parameter, coupled KernelSnitch profiles, reclaim counts with unresolved geometry, and the attempt cap with unresolved per-attempt attribution are deferred.

The Phase I analyzer was run against six synthetic guards for the selected parameter. It accepted compatible E4 evidence, rejected incompatible E4 evidence, returned `INCONCLUSIVE` below E4, rejected missing provenance, detected multi-parameter attribution failure, and enforced cross-condition coverage. All six passed. The complete Phase I suite also passed; no real evidence was created.

Consistency checks preserved the Phase H/I model: 19 rows, 9 P0-independent parameters, unchanged criticality/failure/evidence classifications, no lowered evidence requirement, and no hidden inclusion of `ROOT_UMH_PATH`.

No device interaction, vulnerable-path execution, payload action, target generation, compilation, parameter tuning, or state change occurred.

## Final verdict

`FIRST_WAVE_CANDIDATES_READY_FOR_DESIGN`
