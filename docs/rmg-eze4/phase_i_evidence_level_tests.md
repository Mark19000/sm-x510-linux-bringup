# Phase I evidence-level enforcement tests

The library defines the strict order `E0 < E1 < E2 < E3 < E4`. `enforce_evidence_level(actual, required)` performs only this comparison; it never upgrades evidence based on a favorable result.

The Phase H compatibility minima were loaded unchanged and reproduced:

```text
E2: 0
E3: 3
E4: 16
TOTAL: 19
```

For every one of the 19 parameters, the synthetic test supplies only E1 evidence and asserts `INCONCLUSIVE`. Positive rule fixtures use exactly the Phase H minimum. Cross-boot/cross-condition contracts add identity coverage checks beyond the ordinal level. One successful observation cannot satisfy E3 or E4 merely because its criterion flag is favorable.
