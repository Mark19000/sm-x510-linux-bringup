# Phase H validation domains

This document assigns each L3 parameter exactly one primary domain. The assignment describes the property to validate, not an execution procedure.

## ALLOCATOR_GEOMETRY

Parameter: `SKB_SEND_SIZE`.

The property is whether the direct socket-buffer consumers obtain the allocation class, fragmentation, and layout assumed by the source. Reclaim counts influence observed outcomes but cannot substitute for geometry evidence. Exact direct-consumer geometry can be isolated if allocator state and reclaim policy are recorded; a final path result alone is confounded by both.

## SCHEDULER_TIMING

Parameters: `FOPS_ROUTE_COARSE_DELAY_USEC`, `FOPS_ROUTE_FINE_DELAY_TICKS`.

The property is placement of the fops route within a state-labelled timing window. Coarse placement and the fine per-attempt sweep influence one another. Aggregate success cannot distinguish them; per-offset timing and state labels can. CPU, clock/counter source, frequency behavior, affinity, scheduler policy, and load confound observations.

## RACE_ORDERING

Parameters: `SLIDE_WAIT_NSEC`, `SLIDE_REQUEUE_ARM_USEC`.

The property is the order of waiter establishment, expiry, requeue arming, and dependent state transitions. The wait is a prerequisite for interpreting requeue ordering. A trace with separately labelled events isolates expiry from wrong requeue order; final success/failure does not. Scheduler and setup state remain confounders.

## DISCOVERY_SIGNAL

Parameters: `SLIDE_KSNITCH_APPENDED_FUTEXES`, `SLIDE_KSNITCH_REPEAT_MEASUREMENT`, `SLIDE_KSNITCH_AVERAGE`, `SLIDE_KSNITCH_SCREEN_REPEAT`, `SLIDE_KSNITCH_SCREEN_AVERAGE`.

The property is adequate candidate coverage and stable separation of true candidates from misses. Population size changes resource use and may change noise. Repeat/average pairs are coupled within full measurement and screening. Raw candidate-labelled component scores can separate population, variance, averaging, and screening effects; a final selected candidate cannot. Memory pressure, scheduler load, candidate mix, and absent ground truth confound all five.

Signal/noise assumptions are: appended futexes provide enough candidate coverage within resources; full repeat count yields enough samples; full average suppresses noise without erasing separation; screen repeat is sufficient for an early decision; screen average stabilizes that decision. Relevant metrics are candidate coverage, allocation/resource failures, within-candidate variance, between-class separation, true-candidate retention, miss rejection, false-positive rate, and false-negative rate. Neither member of a repeat/average pair can be validated independently unless raw observations permit factorial attribution while its partner is fixed. The population can be evaluated for resource cost separately, but discovery adequacy still depends on the measurement profiles.

## RECLAIM_BEHAVIOR

Parameters: `SKB_RECLAIM_SENDS`, `SLIDE_RECLAIM_SENDS`.

The property is whether the configured count supplies adequate coverage at its specific consumer. Both depend on `SKB_SEND_SIZE`, allocator state, and available resources; the slide count additionally depends on identifying the slide-stage consumer. Adequacy is demonstrated by repeated attributable coverage of the required state. Repeated attributable shortfall demonstrates insufficiency. Without the actual consumer path, generic allocation activity cannot distinguish inadequate count from wrong geometry or unrelated allocator state.

## ATTEMPT_POLICY

Parameters: `SLIDE_KERNEL_PAGE_SETUP_ATTEMPTS`, `FOPS_KERNEL_PAGE_SETUP_ATTEMPTS`, `DEFAULT_EXPLOIT_ATTEMPTS`, `DEFAULT_ATTEMPT_TIMEOUT_SEC`, `DEFAULT_P0_ATTEMPT_TIMEOUT_SEC`.

The setup caps are `RELIABILITY_POLICY`: they bound opportunities for internal setup and require outcome distributions. `DEFAULT_EXPLOIT_ATTEMPTS` is `SUPERVISOR_POLICY`: it limits child opportunities and must be judged against an explicit adequacy criterion and dirty-state exits. `DEFAULT_ATTEMPT_TIMEOUT_SEC` is both `SUPERVISOR_POLICY` and `RESOURCE_BOUND`, with the former primary. `DEFAULT_P0_ATTEMPT_TIMEOUT_SEC` is a P0-specific `SUPERVISOR_POLICY` constrained by the overall timeout. None is shown to be `LOGIC_REQUIRED`; all must remain positive to provide an opportunity. Required future evidence is per-attempt terminal reason, stage-labelled duration, cap exhaustion, and dirty-state disposition. No attempt or timeout value is recommended here.

| Parameter | Audit classification | Evidence needed to judge ZG3 adequacy |
|---|---|---|
| `SLIDE_KERNEL_PAGE_SETUP_ATTEMPTS` | `RELIABILITY_POLICY` | Repeated slide setup attempts-used, completion, and cap-exhaustion distribution. |
| `FOPS_KERNEL_PAGE_SETUP_ATTEMPTS` | `RELIABILITY_POLICY` | Repeated fops setup attempts-used, completion, and cap-exhaustion distribution. |
| `DEFAULT_EXPLOIT_ATTEMPTS` | `SUPERVISOR_POLICY` | Attempt-indexed terminal outcomes, dirty-state exits, and an explicit adequacy target across conditions. |
| `DEFAULT_ATTEMPT_TIMEOUT_SEC` | `SUPERVISOR_POLICY` | Overall stage-labelled duration tails and premature-expiry evidence across conditions. |
| `DEFAULT_P0_ATTEMPT_TIMEOUT_SEC` | `SUPERVISOR_POLICY` | Pre-P0 duration tails and expiry reasons across boots after P0 outcomes are interpretable. |

## P0_ACCEPTANCE

Parameters: `P0_FINGERPRINT_MIN_BEST`, `P0_FINGERPRINT_MIN_MARGIN`.

The property is safe classification using the actual best and runner-up scores. Both thresholds act on one observation and must be assessed together, although raw scores distinguish floor rejection from margin rejection. Read integrity, row identity, loader/P0 mapping, and collision reachability confound acceptance. Ground-truth-labelled score distributions isolate threshold behavior.

## OTHER

No parameters are assigned to this domain.

## Partial ordering

The justified order is: establish baseline/observable integrity; validate `SKB_SEND_SIZE` before either reclaim count; establish KernelSnitch population/resource observability before profile conclusions; establish full candidate ground truth before screening conclusions; establish `SLIDE_WAIT_NSEC` observability before interpreting `SLIDE_REQUEUE_ARM_USEC`; establish coarse fops timing before claiming fine-sweep coverage; establish the overall timeout constraint before the nested P0 timeout; close P0 mapping/ground truth before either P0 threshold. All other ordering is partial. Shared-environment edges do not impose a topological order.
