# Phase I cross-boot aggregation model

E4 aggregation is a hierarchy: campaign → session → `BOOT_ID` → `CONDITION_ID` → `TRIAL_ID` → measurements. Each boot has its own baseline/provenance record and condition set. Conditions are compared by declared dimensions, never assumed equivalent because their labels match.

Missing expected boots are recorded as missing partitions and cannot contribute votes. A record without `BOOT_ID` is invalid for cross-boot analysis. No numeric boot count is imposed because Phase H defines none; the evidence producer must justify that its assigned E4 level represents the required scope.

Per-boot results are calculated before campaign aggregation. Opposed compatible and incompatible results surface `CONTRADICTORY_OBSERVABLE` and yield `INCONCLUSIVE`; they are not averaged away. A single success cannot dominate repeated failures because the aggregator never uses “any success” semantics. Unresolved outliers, absent condition coverage, missing ground truth, P0 blockage, or mixed attributable/non-attributable partitions keep the result inconclusive.

The final record retains every contributing measurement and raw reference, the set of boots and conditions, exclusions with reasons, and the decision rule version.
