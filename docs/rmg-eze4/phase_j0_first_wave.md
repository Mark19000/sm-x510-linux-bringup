# Phase J0 first-wave candidate selection

## Selection result

One parameter is selected. The matrix has two parameters that satisfy the mandatory eligibility predicates, but the failure-containment preference removes the resource-exhaustion candidate from this first wave.

| Rank | Parameter | Dependency closed | Decision |
|---:|---|---|---|
| 1 | `DEFAULT_ATTEMPT_TIMEOUT_SEC` | YES | Selected. |
| — | `SLIDE_KSNITCH_APPENDED_FUTEXES` | YES | Eligible but deferred because `RESOURCE_EXHAUSTION` is explicitly disfavored while a more contained candidate exists. |

## Rank 1 — `DEFAULT_ATTEMPT_TIMEOUT_SEC`

- **PARAMETER:** `DEFAULT_ATTEMPT_TIMEOUT_SEC`
- **WHY_SELECTED:** P0-independent, no incoming hard or soft parameter prerequisite, high observable clarity, high attribution, complete G11 contract, and a documented `TIMEOUT` wrong-value consequence. Stage-labelled overall duration can be interpreted without resolving P0 when P0-specific time is kept as a separate state.
- **P0_DEPENDENCE:** `P0_INDEPENDENT`.
- **CRITICALITY:** `POLICY_ONLY`.
- **FAILURE_EFFECT:** `TIMEOUT`.
- **MINIMUM_EVIDENCE:** E4; the requirement is not lowered.
- **PREREQUISITES:** canonical EZE4 baseline; complete session/boot/condition/provenance identities; stage-labelled start, transition, expiry, and terminal reason; no simultaneous parameter change. Parameter dependency closure is `YES`.
- **REQUIRED_OBSERVABLE:** overall stage-labelled duration and expiry/terminal reason, with condition identity and immutable raw evidence reference.
- **COMPATIBILITY_CRITERION:** legitimate duration tails remain below expiry across the Phase H-required condition scope with policy headroom.
- **INCOMPATIBILITY_CRITERION:** repeated legitimate attempts are terminated before the relevant terminal transition and the result is attributable to this timeout.
- **INCONCLUSIVE_CRITERION:** stage timestamps or terminal labels are unavailable; E4/cross-condition scope is unmet; results contradict; attribution is partial; or P0-specific delay cannot be separated.
- **STOP_CONDITIONS:** baseline mismatch, missing raw reference, unavailable stage observable, unresolved attribution, condition drift, contradiction, insufficient evidence level, or any result outside the separately reviewed scope.

## Observation sharing

Conclusion: `MUST_VALIDATE_SEPARATELY`.

Only one candidate is selected, so no multi-candidate observation is needed. It must not be combined with the eligible-but-deferred KernelSnitch population parameter: their observables and failure semantics differ, and simultaneous variation would destroy high attribution. Environment identity records may be reused as provenance context, but they are not a shared validation observation.

## Go / no-go gates

| Gate | Requirement | J0 offline status |
|---|---|---|
| GATE_A | Baseline still matches canonical EZE4. | PASS as a required future predicate; no runtime claim made. |
| GATE_B | Parameter and measurement prerequisites are satisfied. | PASS at design level; no unresolved parameter prerequisite. |
| GATE_C | Required stage-labelled observable is available. | PASS at contract level; actual availability must be re-established later. |
| GATE_D | Attribution is preserved. | PASS at design level if this is the sole changed parameter. |
| GATE_E | E4 evidence is achievable without lowering the requirement. | PASS at architecture level; actual evidence is not claimed. |
| GATE_F | No unresolved P0 dependency. | PASS; parameter is P0-independent and P0-specific durations must remain separately labelled. |
| GATE_G | Stop conditions are understood. | PASS; Phase H/I stop rules are incorporated above. |

Status: `READY_FOR_CONTROLLED_VALIDATION_DESIGN`. This is a design-readiness statement only, not authorization to execute validation.

## Mandatory deferrals

The five must-validate parameters are excluded from the first wave:

| Parameter | Deferral reason |
|---|---|
| `SKB_SEND_SIZE` | Direct allocator geometry is correctness-critical and a wrong value can produce `WRONG_STATE`; it requires its dedicated later design. |
| `SLIDE_WAIT_NSEC` | Correctness-critical race ordering, P0 dependence, and setup coupling prevent first-wave attribution. |
| `SLIDE_REQUEUE_ARM_USEC` | Correctness-critical ordering depends on unresolved waiter validation and P0 state. |
| `FOPS_ROUTE_COARSE_DELAY_USEC` | Correctness-critical timing is P0-dependent and coupled to unresolved setup/fine-window interpretation. |
| `FOPS_ROUTE_FINE_DELAY_TICKS` | Correctness-critical sweep depends on the unresolved coarse baseline and P0 state. |

All P0-dependent and P0-only parameters are deferred because the P0-label/Samsung-loader-placement relation is unresolved:

`SLIDE_KERNEL_PAGE_SETUP_ATTEMPTS`, `FOPS_KERNEL_PAGE_SETUP_ATTEMPTS`, `FOPS_ROUTE_COARSE_DELAY_USEC`, `FOPS_ROUTE_FINE_DELAY_TICKS`, `DEFAULT_P0_ATTEMPT_TIMEOUT_SEC`, `SLIDE_WAIT_NSEC`, `SLIDE_REQUEUE_ARM_USEC`, `SLIDE_RECLAIM_SENDS`, `P0_FINGERPRINT_MIN_BEST`, and `P0_FINGERPRINT_MIN_MARGIN`.

No replacement values, tuning, commands, trigger mechanics, or execution procedure are defined.
