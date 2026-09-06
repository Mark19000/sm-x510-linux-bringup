# Phase H P0 threshold analysis

## Established boundary

The generated table contains 125 rows and 1000 sampled words. Four labels (`0x1e4000`, `0x1e8000`, `0x1ec000`, `0x1f0000`) are problematic: three tie at 8 versus 8 and one scores 8 versus 7. Current production logic safely rejects them, restores sampled pages, and has no same-boot fallback. Their loader reachability and the authoritative mapping between loader placement and P0 labels remain unknown.

## `P0_FINGERPRINT_MIN_BEST = 5`

This threshold protects against accepting a candidate whose absolute match count is too weak. It is evaluated before acceptance together with uniqueness and margin. Offline clean-Image analysis constrains the possible clean scores and proves table/collision behavior, but it cannot characterize runtime read degradation or false-candidate scores. Runtime evidence must retain ground truth and the actual best score across repeated boots and relevant conditions, including read-integrity failures. Raising or lowering the threshold could change both true-state rejection and safe rejection of weak observations; this report recommends no change.

## `P0_FINGERPRINT_MIN_MARGIN = 3`

This threshold protects against accepting a winner insufficiently separated from its runner-up. Offline analysis proves that the four known problematic rows are rejected at the current margin, including the 8-versus-7 case, and that the three identical NOP pages cannot be distinguished within the sampled page. It does not establish reachability or runtime score separation elsewhere. Runtime evidence must preserve ground-truth row identity plus best and second scores across boots/conditions. Changing the margin could alter the safe-rejection behavior, particularly for `0x1f0000`, and could trade false positives against false negatives; this report recommends no change and does not redesign the oracle.

## Cross-cutting conclusion

Neither threshold can be called compatible until P0 label/ground-truth interpretation is available. Unresolved loader mapping does not prevent isolated direct-consumer validation of geometry, KernelSnitch signal, general reclaim, or supervisor mechanics, but it blocks interpretation of the P0 thresholds and downstream observations whose identity depends on a correct P0 result.
