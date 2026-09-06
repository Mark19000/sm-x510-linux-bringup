# Phase H — controlled validation design for the 19 L3 parameters

Phase H converts the canonical L3 set into a dependency-ordered, falsifiable validation specification. It performs no validation and authorizes no runtime transition.

```text
L3_PARAMETERS_TOTAL: 19

CORRECTNESS_CRITICAL: 7
RELIABILITY_CRITICAL: 9
POLICY_ONLY: 3
UNKNOWN: 0

VALIDATION_DOMAINS: 7
VALIDATION_GROUPS: 12
HARD_DEPENDENCY_EDGES: 8
SOFT_DEPENDENCY_EDGES: 5

MIN_EVIDENCE_E2: 0
MIN_EVIDENCE_E3: 3
MIN_EVIDENCE_E4: 16

P0_INDEPENDENT_PARAMETERS: 9
P0_DEPENDENT_PARAMETERS: 7
P0_ONLY_PARAMETERS: 3

MUST_VALIDATE_PARAMETERS: 5

PARAMETERS_WITH_CLEAR_COMPATIBILITY_CRITERION: 19
PARAMETERS_WITH_CLEAR_INCOMPATIBILITY_CRITERION: 19
PARAMETERS_STILL_EXPERIMENTALLY_AMBIGUOUS: 4

STATIC_MODEL_CONTRADICTIONS_FOUND: 0
```

The four experimentally ambiguous parameters are `DEFAULT_EXPLOIT_ATTEMPTS`, whose adequacy requires an explicit supervisor policy target, and the three P0-only parameters (`DEFAULT_P0_ATTEMPT_TIMEOUT_SEC`, `P0_FINGERPRINT_MIN_BEST`, `P0_FINGERPRINT_MIN_MARGIN`), whose interpretation remains blocked by P0/loader ground truth. This ambiguity does not erase their compatibility criteria; it prevents present evidence from satisfying them.

The seven used primary domains are allocator geometry, scheduler timing, race ordering, discovery signal, reclaim behavior, attempt policy, and P0 acceptance. `OTHER` has no assigned parameter. The graph is deliberately partial: `SHARED_ENVIRONMENT`, `INDEPENDENT`, and `UNKNOWN` relationships do not create topological constraints.

Evidence levels are canonical:

- **E0 — STATIC ONLY:** source, artifact, and model reasoning without environment observation.
- **E1 — PASSIVE ENVIRONMENT OBSERVATION:** baseline and prerequisite context without the relevant consumer.
- **E2 — CONTROLLED OBSERVATION OF RELEVANT CONSUMER:** one attributable direct-consumer observation.
- **E3 — REPEATED CONTROLLED OBSERVATION:** repeated attributable observations under one defined condition set.
- **E4 — CROSS-BOOT / CROSS-CONDITION VALIDATION:** repeated observations spanning the condition or boot variation needed by the claim.

The E2/E3/E4 totals above use the minimum level for `VALIDATED_COMPATIBLE`. Incompatibility can sometimes be established at a lower level when a direct contradiction is uniquely attributable, as recorded per parameter. One success is never promoted to general compatibility where repetition or cross-condition evidence is logically required.

Artifacts produced:

- `phase_h_l3_inventory.csv`
- `phase_h_dependency_edges.csv`
- `phase_h_validation_domains.md`
- `phase_h_validation_questions.csv`
- `phase_h_validation_groups.csv`
- `phase_h_failure_semantics.csv`
- `phase_h_must_validate.md`
- `phase_h_p0_threshold_analysis.md`
- `phase_h_evidence_requirements.csv`
- `phase_h_stop_conditions.md`
- `phase_h_p0_dependency.csv`
- `phase_h_validation_order.md`

No Phase G action was repeated. No device interaction, ADB use, compilation, target generation, payload execution, kernel-path execution, kernel modification, boot modification, flashing, reboot, or bootloader change occurred.

## Final verdict

`CONTROLLED_VALIDATION_DESIGN_COMPLETE`
