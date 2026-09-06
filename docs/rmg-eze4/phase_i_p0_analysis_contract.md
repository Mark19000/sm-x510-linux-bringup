# Phase I P0 offline analysis contract

The analysis-only P0 set is `DEFAULT_P0_ATTEMPT_TIMEOUT_SEC`, `P0_FINGERPRINT_MIN_BEST`, and `P0_FINGERPRINT_MIN_MARGIN`. The contract preserves:

- loader mapping: `OPEN`;
- collision reachability: `UNKNOWN`;
- structural collision labels: `0x1e4000`, `0x1e8000`, `0x1ec000`, `0x1f0000`;
- same-boot recovery: `NONE`.

The timeout contract requires a stage-labelled pre-P0 duration and terminal reason. The threshold contract requires authoritative ground truth, raw best and second scores, read-integrity state, boot identity, and collision classification. All three require E4 for compatibility and E3 for an attributable incompatibility; compatibility is blocked while P0 ground truth is unresolved.

Machine invariants:

- ambiguous P0 evidence returns `INCONCLUSIVE`;
- table membership is coverage metadata, not reachability evidence;
- absence from logs is absence of observation, not proof of unreachability;
- one observed label is one observation, not a loader distribution;
- structural collision labels remain safe-rejection cases until reachability is independently established;
- repeated same-boot evidence is not counted as independent recovery or a cross-boot distribution.

The synthetic P0 test supplies table membership, log absence, and one synthetic label while setting `P0_ONLY` and leaving P0 unresolved. The analyzer returns `INCONCLUSIVE`. No oracle logic or threshold is redesigned.
