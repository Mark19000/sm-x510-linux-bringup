# Phase H future stop / no-go conditions

These are methodological gates for any separately authorized future research. They contain no trigger mechanics.

Stop before collecting or interpreting L3 evidence if:

- the model, firmware, CSC, build fingerprint, kernel release/build, or stock Image digest does not match the canonical EZE4 baseline;
- any unplanned device, boot, bootloader, filesystem, kernel, privilege, or persistence state change is detected;
- the required observable, ground truth, monotonic timebase, consumer identity, parameter identity, or terminal reason is unavailable;
- instrumentation changes the property being measured or its effect has not been bounded;
- a hard prerequisite in `phase_h_dependency_edges.csv` is not validated to its required evidence level;
- a grouped observation cannot distinguish the member-specific criteria stated in `phase_h_validation_groups.csv`;
- environment variables, defaults, build provenance, or effective values cannot be reconciled with the canonical inventory;
- repeated observations are internally inconsistent beyond a predeclared tolerance and the inconsistency cannot be attributed;
- a result can be explained equally by an uncontrolled parameter, allocator state, scheduler/load state, resource ceiling, or measurement error;
- resource pressure, timeout, or safe-abort behavior prevents observing the intended consumer;
- a P0-dependent or P0-only result is being interpreted without an authoritative P0 label/ground-truth mapping;
- a collision-label observation is ambiguous, or deterministic same-boot collision behavior would make retries non-independent;
- the baseline crosses a boot or condition boundary without recording it, invalidating within-condition attribution;
- the observation count is below the minimum E-level requirement in `phase_h_evidence_requirements.csv`;
- any outcome falls outside the predeclared safe and reversible research scope.

When a stop condition occurs, preserve the evidence as inconclusive, do not promote the parameter, and return to design/provenance review.
