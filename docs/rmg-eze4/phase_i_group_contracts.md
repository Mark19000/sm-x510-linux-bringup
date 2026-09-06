# Phase I validation-group data contracts

All contracts consume normalized records plus immutable raw references. “Repeated” and “cross-condition” carry no invented numeric count; the assigned E-level must be justified externally.

## G1

- **PARAMETERS:** `SLIDE_KERNEL_PAGE_SETUP_ATTEMPTS`
- **REQUIRED_INPUTS:** attempt-indexed setup states, terminal reason, prerequisite/discovery state.
- **PRIMARY_OBSERVABLES:** attempts used; completion or cap exhaustion.
- **SECONDARY_OBSERVABLES:** allocator/resource context.
- **ENVIRONMENT_FIELDS:** boot, condition kind, CPU, load, memory/allocator class.
- **COMPATIBILITY_DECISION:** repeated eligible setups complete within the cap at E3.
- **INCOMPATIBILITY_DECISION:** repeated eligible setups exhaust the cap before the required state at E3.
- **INCONCLUSIVE_DECISION:** missing setup identity, terminal reason, prerequisite, attribution, or E3.
- **CONFOUNDERS:** allocator pressure, reclaim, discovery.
- **MINIMUM_EVIDENCE_LEVEL:** E3.
- **CROSS_BOOT_REQUIRED:** no.
- **CROSS_CONDITION_REQUIRED:** no for minimum; required for broader scope claims.

## G2

- **PARAMETERS:** `FOPS_KERNEL_PAGE_SETUP_ATTEMPTS`
- **REQUIRED_INPUTS:** attempt-indexed fops setup states and terminal reason.
- **PRIMARY_OBSERVABLES:** attempts used; completion or cap exhaustion.
- **SECONDARY_OBSERVABLES:** route/discovery and allocator context.
- **ENVIRONMENT_FIELDS:** boot, CPU, load, memory/allocator class.
- **COMPATIBILITY_DECISION:** repeated eligible setups complete within cap at E3.
- **INCOMPATIBILITY_DECISION:** repeated eligible setups exhaust cap before required state at E3.
- **INCONCLUSIVE_DECISION:** setup identity, terminal reason, prerequisite, attribution, or E3 absent.
- **CONFOUNDERS:** allocator state, discovery.
- **MINIMUM_EVIDENCE_LEVEL:** E3.
- **CROSS_BOOT_REQUIRED:** no.
- **CROSS_CONDITION_REQUIRED:** no for minimum.

## G3

- **PARAMETERS:** `SLIDE_WAIT_NSEC`; `SLIDE_REQUEUE_ARM_USEC`
- **REQUIRED_INPUTS:** labelled wait-start, waiter-state, expiry, requeue-arm, and dependent transitions.
- **PRIMARY_OBSERVABLES:** ordered state-transition trace.
- **SECONDARY_OBSERVABLES:** setup terminal state and timing uncertainty.
- **ENVIRONMENT_FIELDS:** boot, CPU topology/affinity, scheduler/load class, timebase.
- **COMPATIBILITY_DECISION:** required ordering holds at E4 across relevant conditions.
- **INCOMPATIBILITY_DECISION:** repeated attributable expiry/wrong order at E3.
- **INCONCLUSIVE_DECISION:** unlabelled events, unresolved setup, confounding, or insufficient level.
- **CONFOUNDERS:** scheduler, CPU, load, setup.
- **MINIMUM_EVIDENCE_LEVEL:** E4 compatible; E3 incompatible.
- **CROSS_BOOT_REQUIRED:** not categorically; E4 scope must be represented.
- **CROSS_CONDITION_REQUIRED:** yes.

## G4

- **PARAMETERS:** `FOPS_ROUTE_COARSE_DELAY_USEC`; `FOPS_ROUTE_FINE_DELAY_TICKS`
- **REQUIRED_INPUTS:** coarse baseline, per-offset identity, state-window boundaries, attempt coverage.
- **PRIMARY_OBSERVABLES:** per-offset state-labelled timing.
- **SECONDARY_OBSERVABLES:** setup and counter metadata.
- **ENVIRONMENT_FIELDS:** boot, CPU, scheduler/load, counter/timebase, condition kind.
- **COMPATIBILITY_DECISION:** coarse placement and at least one covered fine offset satisfy the window at E4.
- **INCOMPATIBILITY_DECISION:** repeated attributable window miss/out-of-sweep result at E3.
- **INCONCLUSIVE_DECISION:** aggregate-only result, uncovered offsets, missing setup, or insufficient level.
- **CONFOUNDERS:** counter source, scheduler, setup, attempt cap.
- **MINIMUM_EVIDENCE_LEVEL:** E4 compatible; E3 incompatible.
- **CROSS_BOOT_REQUIRED:** not categorical.
- **CROSS_CONDITION_REQUIRED:** yes.

## G5

- **PARAMETERS:** `SLIDE_KSNITCH_REPEAT_MEASUREMENT`; `SLIDE_KSNITCH_AVERAGE`
- **REQUIRED_INPUTS:** ground-truth candidate labels, component scores, averaged scores.
- **PRIMARY_OBSERVABLES:** within-candidate variance and between-class separation.
- **SECONDARY_OBSERVABLES:** candidate population and resource failures.
- **ENVIRONMENT_FIELDS:** boot, CPU/load, memory, candidate mix.
- **COMPATIBILITY_DECISION:** stable separable distributions at E4.
- **INCOMPATIBILITY_DECISION:** repeated attributable overlap/misclassification at E3.
- **INCONCLUSIVE_DECISION:** averages without components, absent ground truth, or insufficient level.
- **CONFOUNDERS:** paired profile values, load, population.
- **MINIMUM_EVIDENCE_LEVEL:** E4 compatible; E3 incompatible.
- **CROSS_BOOT_REQUIRED:** not categorical.
- **CROSS_CONDITION_REQUIRED:** yes.

## G6

- **PARAMETERS:** `SLIDE_KSNITCH_SCREEN_REPEAT`; `SLIDE_KSNITCH_SCREEN_AVERAGE`
- **REQUIRED_INPUTS:** ground-truth screen inputs, component/average scores, retained/rejected labels.
- **PRIMARY_OBSERVABLES:** true retention, miss rejection, false-positive and false-negative states.
- **SECONDARY_OBSERVABLES:** full-profile confirmation.
- **ENVIRONMENT_FIELDS:** boot, CPU/load, memory, candidate mix.
- **COMPATIBILITY_DECISION:** screening separation satisfies declared criteria at E4.
- **INCOMPATIBILITY_DECISION:** repeated true-candidate loss or excessive false retention attributable to profile at E3.
- **INCONCLUSIVE_DECISION:** no ground truth/components, unresolved full profile, or insufficient level.
- **CONFOUNDERS:** paired screen values, population, load.
- **MINIMUM_EVIDENCE_LEVEL:** E4 compatible; E3 incompatible.
- **CROSS_BOOT_REQUIRED:** not categorical.
- **CROSS_CONDITION_REQUIRED:** yes.

## G7

- **PARAMETERS:** `SLIDE_KSNITCH_APPENDED_FUTEXES`
- **REQUIRED_INPUTS:** candidate-population membership and resource accounting.
- **PRIMARY_OBSERVABLES:** coverage and resource-failure state.
- **SECONDARY_OBSERVABLES:** measurement-profile cost.
- **ENVIRONMENT_FIELDS:** boot, memory/resource class, CPU/load.
- **COMPATIBILITY_DECISION:** coverage without out-of-policy resource failure at E4.
- **INCOMPATIBILITY_DECISION:** repeated attributable insufficiency/exhaustion at E3.
- **INCONCLUSIVE_DECISION:** missing population/resource attribution or insufficient level.
- **CONFOUNDERS:** memory pressure, measurement profile.
- **MINIMUM_EVIDENCE_LEVEL:** E4 compatible; E3 incompatible.
- **CROSS_BOOT_REQUIRED:** not categorical.
- **CROSS_CONDITION_REQUIRED:** yes.

## G8

- **PARAMETERS:** `SKB_SEND_SIZE`
- **REQUIRED_INPUTS:** direct-consumer allocation class, fragment layout, exact send result.
- **PRIMARY_OBSERVABLES:** allocation/fragment geometry.
- **SECONDARY_OBSERVABLES:** allocator and socket context.
- **ENVIRONMENT_FIELDS:** boot, memory/allocator class, CPU/load, socket configuration class.
- **COMPATIBILITY_DECISION:** repeated intended geometry at E3.
- **INCOMPATIBILITY_DECISION:** one unambiguous incompatible direct geometry at E2.
- **INCONCLUSIVE_DECISION:** environment-only, generic slab data, missing consumer, or insufficient level.
- **CONFOUNDERS:** allocator state, reclaim counts, socket behavior.
- **MINIMUM_EVIDENCE_LEVEL:** E3 compatible; E2 incompatible.
- **CROSS_BOOT_REQUIRED:** no.
- **CROSS_CONDITION_REQUIRED:** no for minimum.

## G9

- **PARAMETERS:** `SKB_RECLAIM_SENDS`; `SLIDE_RECLAIM_SENDS`
- **REQUIRED_INPUTS:** validated geometry, consumer-labelled per-send coverage, terminal reclaim state.
- **PRIMARY_OBSERVABLES:** per-consumer coverage.
- **SECONDARY_OBSERVABLES:** resource consumption and allocator state.
- **ENVIRONMENT_FIELDS:** boot, memory/allocator class, CPU/load, consumer identity.
- **COMPATIBILITY_DECISION:** repeated attributable coverage at E4.
- **INCOMPATIBILITY_DECISION:** repeated attributable coverage shortfall at E3.
- **INCONCLUSIVE_DECISION:** geometry/consumer unavailable, P0 unresolved for slide consumer, or insufficient level.
- **CONFOUNDERS:** geometry, allocator pressure, discovery.
- **MINIMUM_EVIDENCE_LEVEL:** E4 compatible; E3 incompatible.
- **CROSS_BOOT_REQUIRED:** not categorical.
- **CROSS_CONDITION_REQUIRED:** yes.

## G10

- **PARAMETERS:** `P0_FINGERPRINT_MIN_BEST`; `P0_FINGERPRINT_MIN_MARGIN`
- **REQUIRED_INPUTS:** authoritative P0 ground truth, best and second scores, read-integrity state, collision classification.
- **PRIMARY_OBSERVABLES:** ground-truth-labelled best/second distribution.
- **SECONDARY_OBSERVABLES:** safe-rejection reason and table row.
- **ENVIRONMENT_FIELDS:** boot, condition, read-integrity class, loader/P0 mapping status.
- **COMPATIBILITY_DECISION:** true states pass and weak/ambiguous states reject at E4 with P0 resolved.
- **INCOMPATIBILITY_DECISION:** repeated attributable false acceptance/rejection at E3.
- **INCONCLUSIVE_DECISION:** loader mapping open, membership/log absence/one label only, missing runner-up, or insufficient level.
- **CONFOUNDERS:** loader mapping, collision reachability, read integrity.
- **MINIMUM_EVIDENCE_LEVEL:** E4 compatible; E3 incompatible.
- **CROSS_BOOT_REQUIRED:** yes.
- **CROSS_CONDITION_REQUIRED:** yes.

## G11

- **PARAMETERS:** `DEFAULT_ATTEMPT_TIMEOUT_SEC`; `DEFAULT_P0_ATTEMPT_TIMEOUT_SEC`
- **REQUIRED_INPUTS:** stage-labelled start/transition/expiry times and terminal reason.
- **PRIMARY_OBSERVABLES:** overall and pre-P0 duration tails.
- **SECONDARY_OBSERVABLES:** supervisor state and P0 readiness.
- **ENVIRONMENT_FIELDS:** boot, CPU/load, condition, P0 status.
- **COMPATIBILITY_DECISION:** legitimate tails remain below bounds at E4.
- **INCOMPATIBILITY_DECISION:** repeated premature expiry at E3.
- **INCONCLUSIVE_DECISION:** unlabelled timeout, unresolved P0 for P0 bound, or insufficient level.
- **CONFOUNDERS:** load, stalls, nested timeout, P0 ambiguity.
- **MINIMUM_EVIDENCE_LEVEL:** E4 compatible; E3 incompatible.
- **CROSS_BOOT_REQUIRED:** yes for P0 timeout; otherwise scope-dependent.
- **CROSS_CONDITION_REQUIRED:** yes.

## G12

- **PARAMETERS:** `DEFAULT_EXPLOIT_ATTEMPTS`
- **REQUIRED_INPUTS:** attempt-indexed terminal outcomes, dirty-state disposition, declared policy target.
- **PRIMARY_OBSERVABLES:** cap exhaustion and terminal-outcome distribution.
- **SECONDARY_OBSERVABLES:** per-attempt prerequisite failure reasons.
- **ENVIRONMENT_FIELDS:** boot, condition, P0/collision state, CPU/load/memory class.
- **COMPATIBILITY_DECISION:** policy target is met within cap at E4.
- **INCOMPATIBILITY_DECISION:** policy target is repeatedly missed solely because cap ends opportunities at E4.
- **INCONCLUSIVE_DECISION:** no policy target, deterministic collision, mixed prerequisite failures, or insufficient level.
- **CONFOUNDERS:** all per-attempt parameters, dirty state, P0 collision.
- **MINIMUM_EVIDENCE_LEVEL:** E4.
- **CROSS_BOOT_REQUIRED:** yes where boot-specific state affects opportunities.
- **CROSS_CONDITION_REQUIRED:** yes.
