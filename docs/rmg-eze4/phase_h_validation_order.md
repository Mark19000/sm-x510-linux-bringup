# Phase H minimum future validation order

This is an abstract partial order only. A stage may be skipped only when its outputs are not prerequisites for the parameters under study.

## STAGE_0

- **PARAMETERS:** none.
- **PREREQUISITES:** canonical EZE4 model, firmware, kernel, Image digest, unchanged planned scope.
- **REQUIRED_EVIDENCE:** E1 baseline/environment observation plus confirmed availability of parameter, consumer, state, timing, resource, and terminal observables.
- **EXIT_CRITERION:** baseline matches and every intended later result can be attributed; otherwise stop.

## STAGE_1

- **PARAMETERS:** `SKB_SEND_SIZE`; `SLIDE_KSNITCH_APPENDED_FUTEXES`; `DEFAULT_ATTEMPT_TIMEOUT_SEC`.
- **PREREQUISITES:** STAGE_0.
- **REQUIRED_EVIDENCE:** direct geometry evidence for size; candidate/resource accounting for population; stage-labelled supervisor duration semantics for overall timeout.
- **EXIT_CRITERION:** geometry is interpretable, the discovery resource envelope is observable, and the overall timeout boundary is unambiguous. Compatibility promotion follows each row's E-level, not stage completion alone.

## STAGE_2

- **PARAMETERS:** `SLIDE_KSNITCH_REPEAT_MEASUREMENT`; `SLIDE_KSNITCH_AVERAGE`; `SLIDE_KSNITCH_SCREEN_REPEAT`; `SLIDE_KSNITCH_SCREEN_AVERAGE`; `SKB_RECLAIM_SENDS`; `SLIDE_KERNEL_PAGE_SETUP_ATTEMPTS`; `FOPS_KERNEL_PAGE_SETUP_ATTEMPTS`.
- **PREREQUISITES:** relevant STAGE_1 geometry/resource result; consumer-specific ground truth for discovery; observable setup terminal states.
- **REQUIRED_EVIDENCE:** raw candidate-labelled score distributions; consumer-labelled reclaim coverage; repeated setup attempt outcomes.
- **EXIT_CRITERION:** signal profiles have interpretable false-positive/false-negative metrics, general reclaim coverage is attributable, and both setup caps have repeated outcome distributions.

## STAGE_3

- **PARAMETERS:** `SLIDE_WAIT_NSEC`; `FOPS_ROUTE_COARSE_DELAY_USEC`.
- **PREREQUISITES:** their relevant setup state from STAGE_2; stable timebase and state labels.
- **REQUIRED_EVIDENCE:** repeated state-labelled waiter and coarse-route timing, progressing toward cross-condition E4 for compatibility.
- **EXIT_CRITERION:** waiter establishment/expiry and coarse window placement are separately interpretable.

## STAGE_4

- **PARAMETERS:** `SLIDE_REQUEUE_ARM_USEC`; `FOPS_ROUTE_FINE_DELAY_TICKS`.
- **PREREQUISITES:** validated/interpretable waiter and coarse timing from STAGE_3; per-offset identity and sufficient attempt coverage.
- **REQUIRED_EVIDENCE:** repeated ordered transition traces and per-offset window coverage; E4 for compatibility.
- **EXIT_CRITERION:** requeue ordering and fine-sweep coverage can be attributed independently of prerequisite failures.

## STAGE_5

- **PARAMETERS:** `P0_FINGERPRINT_MIN_BEST`; `P0_FINGERPRINT_MIN_MARGIN`; `DEFAULT_P0_ATTEMPT_TIMEOUT_SEC`.
- **PREREQUISITES:** authoritative P0 ground truth/loader-label interpretation; preserved best/second scores; STAGE_1 overall-timeout semantics; collision states treated explicitly.
- **REQUIRED_EVIDENCE:** repeated ground-truth-labelled scores and pre-P0 durations, with E4 across boots/conditions for compatibility.
- **EXIT_CRITERION:** floor, margin, and P0 timeout outcomes are distinguishable; collision rejection and loader reachability are not conflated.

## STAGE_6

- **PARAMETERS:** `SLIDE_RECLAIM_SENDS`; `DEFAULT_EXPLOIT_ATTEMPTS`.
- **PREREQUISITES:** P0 closure for slide-stage identity; validated geometry; stable per-attempt correctness observables and dirty-state disposition.
- **REQUIRED_EVIDENCE:** cross-condition slide-consumer reclaim coverage and attempt-indexed terminal distributions.
- **EXIT_CRITERION:** slide reclaim adequacy and supervisor-cap policy can be judged without attributing prerequisite or deterministic P0 failures to them.

Shared-environment relationships do not otherwise impose order. No stage authorizes or describes execution.
