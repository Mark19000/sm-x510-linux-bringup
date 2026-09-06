# Phase I attribution rules

The offline checker returns:

- `ATTRIBUTABLE`: one declared parameter/group change, complete required environment metadata, resolved prerequisites, available raw reference, valid identities, and resolved P0 state where required.
- `PARTIALLY_ATTRIBUTABLE`: the record remains useful context but multiple parameters changed or non-critical environment detail is incomplete.
- `NOT_ATTRIBUTABLE`: raw reference missing, hard prerequisite absent, group dependency unresolved, cross-boot evidence lacks boot IDs, or required P0 state is unresolved.

Machine rules are implemented in `assess_attribution()` and include `MULTIPLE_PARAMETERS_CHANGED`, `MISSING_PREREQUISITE`, `MISSING_ENVIRONMENT`, `UNRESOLVED_GROUP_DEPENDENCY`, `MISSING_BOOT_ID`, `P0_BLOCKED`, and `MISSING_RAW_EVIDENCE_REF`. A non-attributable record may be preserved but cannot support compatibility or incompatibility. Partial attribution cannot be promoted unless the governing contract explicitly permits the missing dimension.
