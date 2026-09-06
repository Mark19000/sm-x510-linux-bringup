# Closure of the three previously unresolved rows

## BUILD_VARIANT_LABEL

- **Category:** `BUILD_METADATA`
- **Why unresolved:** the Phase C matrix proposed `gts9fewifi-X510XXUCEZE4-app`, but no EZE4 target directory exists and no source artifact canonically assigns that label.
- **References/usages:** ZG3 `target.h:7`; `src/util.c:125` prints it in startup diagnostics. It does not select an address, layout, oracle, or control-flow branch.
- **Needed on active EZE4 production path:** required only if the existing diagnostic build expects the macro; semantically irrelevant to target correctness.
- **Static resolution:** the firmware identity is known, but the exact label remains a naming choice rather than a value derivable from Image, BTF, DWARF, or source data flow.
- **Final status:** `STATICALLY_UNRESOLVABLE`.

## PHYS_P0_ORACLE

- **Category:** `EXPLOIT_ALGORITHM_CONSTANT`
- **Why unresolved:** Phase C tied its readiness to the collision limitation rather than separating route selection from oracle completeness.
- **References/usages:** ZG3 `target.h:8`; compile-time branches in `oracle.c`, `pipe.c`, `fops.c`, `page.c`, `slide_app.c`, `pselect.c`, `main.c`, and declarations in `common.h`.
- **Needed on active EZE4 production path:** yes. It selects the physical P0 implementation and excludes the legacy 32-candidate path.
- **Static resolution:** yes. The EZE4 fingerprint artifact is a 125-row physical P0 table generated from stock Image, the retained production control flow is the physical branch, and all Phase D analysis is scoped to that branch. Collision completeness is a separate readiness blocker and does not make the macro value unknown.
- **EZE4 value:** `1`.
- **Final status:** `CONFIRMED_IDENTICAL`.

## BUILD_FINGERPRINT

- **Category:** `FIRMWARE_FINGERPRINT`
- **Why unresolved:** the exact EZE4 `ro.build.fingerprint` property is not retained; only the platform build and firmware identity are documented.
- **References/usages:** ZG3 `target.h:11-14`. A repository-wide source search outside target definitions found no consumer in the payload, supervisor, oracle, or production path.
- **Needed on active EZE4 production path:** no, based on the retained source. It is metadata for external target selection/build packaging, not an input to active payload control flow.
- **Static resolution:** the exact string cannot be reconstructed without guessing, but it is unnecessary for the audited active path.
- **Final status:** `NOT_APPLICABLE` to active-path static readiness. Preserve it as an external packaging unknown if a future target registry requires it.

## Closure count

One row is confirmed identical, one is not applicable to the active path, and one remains statically unresolvable because it is a naming convention. No runtime measurement is required for these three rows.
