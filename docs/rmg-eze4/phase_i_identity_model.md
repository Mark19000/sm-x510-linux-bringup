# Phase I identity model

- `SESSION_ID` identifies one bounded collection/analysis session and its manifest. It never implies one boot.
- `BOOT_ID` identifies one continuous boot epoch. Any restart, power cycle, or loss of proof of continuity requires a new identifier. Phase I does not prescribe how a boot occurs.
- `CONDITION_ID` identifies one declared environment tuple within a boot: condition kind, CPU-topology state, load class, memory-availability class, timebase/counter metadata, and other group-required fields. A material tuple change creates a new condition. Unknown changes require `UNKNOWN_CONDITION`, not reuse of the old ID.
- `TRIAL_ID` identifies one repeated trial under exactly one boot and condition.
- `MEASUREMENT_ID` identifies one observable record within a trial and is globally unique within the campaign.

Repeated trials under a single `CONDITION_ID` can support E3; they do not become cross-condition evidence merely by repetition. E4 requires the cross-boot or cross-condition variation justified by Phase H, represented by distinct IDs and preserved membership.

Records from different boots remain partitioned by `BOOT_ID` through normalization, analysis, and reporting. Aggregation stores a set of boot partitions rather than flattening rows. Missing or duplicate boot identity blocks cross-boot claims. A session spanning multiple boots must list each boot explicitly; evidence is never merged based only on timestamps or matching conditions.
