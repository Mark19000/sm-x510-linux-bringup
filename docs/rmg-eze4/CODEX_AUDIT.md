# Codex EZE4 static audit

The readiness matrix audits 180 inventory rows from ZG3 `target.h` and `p0_fingerprint.h`. Counts are taken directly from `eze4_target_readiness.csv`:

| Status | Count |
|---|---:|
| `CONFIRMED_IDENTICAL` | 133 |
| `CONFIRMED_CHANGED` | 10 |
| `EMPIRICAL_RETEST_REQUIRED` | 31 |
| `UNRESOLVED` | 3 |
| `NOT_APPLICABLE` | 3 |
| **Total** | **180** |

The three not-applicable rows are two include guards and the inactive 32-value legacy candidate macro. The ten changed rows comprise firmware/path/fingerprint data plus eight symbol macro rows representing four unique stock symbol deltas. The matrix preserves both base offset and derived-address rows because both appear in the reference target.

Six cross-file contradiction classes were found and reconciled in `STATUS.md`: the `0x8a0`/`0x8a8` attribution, `mm_struct` size versus allocation bucket, 32 versus 125 P0 candidate spaces, rebuilt-vmlinux versus stock-Image addresses, symbol-row versus unique-symbol counts, and retry claims that did not distinguish transient oracle failures from deterministic collisions.

The P0 verdict is `COLLISIONS_REQUIRE_FURTHER_RESEARCH`. The production source has no compiled fallback; a same-boot retry cannot disambiguate the three identical NOP pages. Static evidence cannot prove that the Samsung boot chain selects or excludes those placements.

An offline draft EZE4 target is **not ready to be prepared**. Static values are sufficiently mature for continued analysis, but the unresolved collision reachability/fallback question and exact build fingerprint remain blockers, and 31 empirical parameters still require retesting under separate authorization.

## Final readiness verdict

`READY_FOR_FURTHER_STATIC_ANALYSIS`
