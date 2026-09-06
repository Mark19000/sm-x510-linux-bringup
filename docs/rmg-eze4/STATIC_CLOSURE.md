# Phase D static closure

## Required summary

```text
UNRESOLVED_BEFORE: 3
UNRESOLVED_AFTER: 1
EMPIRICAL_BEFORE: 31
STATICALLY_RESOLVED: 9
LEGACY_OR_INACTIVE: 2
GENUINELY_RUNTIME_DEPENDENT: 17
STILL_UNKNOWN: 3

CHANGED_DEPENDENCY_STALE_COUNT: 0

P0_COLLISION_RUNTIME_BEHAVIOR: scan returns -1; caller restores pages and fails; shared dirty remains set; supervisor refuses another child attempt on that boot
P0_COLLISION_REACHABILITY: UNKNOWN for all 125 EZE4 placements from retained static evidence
P0_EXISTING_FALLBACK: NONE in the compiled gts9fewifi PHYS_P0_ORACLE path
P0_RESEARCH_STATUS: control flow closed; reachability remains blocked by absent Samsung physical-placement selector/bootloader evidence
```

`UNRESOLVED_AFTER` counts the provisional build label, which is a naming decision and is `STATICALLY_UNRESOLVABLE`; it does not affect target semantics. `STILL_UNKNOWN` in the empirical triage counts three values classified `PROBABLY_REUSABLE_FROM_ZG3`, which remain deliberately unconfirmed.

## P0 collision deep-audit result

For the active app target, `scan_p0_pipe_oracle()` returns `(uintptr_t)-1` on ties, non-unique winners, low scores, or insufficient margins. `slide_leak_physical_base()` invokes both restore slots and then returns failure. `run_exploit()` returns status 1 before any later production stage.

Although the supervisor is configured for eight independent attempts, the child calls `app_publish_p0_dirty()` before the fingerprint scan. Restoration does not clear the shared flag. After the child fails, `preload.c` sees `dirty=1`, prints that the oracle state is dirty or uncertain, breaks the attempt loop, and exits. Therefore this collision path performs one P0 scan in the boot/session managed by this supervisor, not eight.

A retry would sample the same physical Image page because the placement is fixed for the boot. Only a reboot could potentially select a different placement, but the retained repository does not establish the Samsung bootloader's selection range or distribution. The legacy boot-id path is excluded by `PHYS_P0_ORACLE=1`; the virtual-base oracle is excluded because this target does not define `PHYS_VIRTUAL_BASE_ORACLE`.

The current mechanism reads one redirected 4 KiB page up to offset `0xe07`. The three collision pages at Image offsets `0x004000`, `0x008000`, and `0x00c000` are byte-identical full-page NOP padding, so unused bytes in those pages cannot distinguish them. Image page zero contains additional non-NOP data, but the existing eight-word/margin policy rejects it and no compiled follow-up consumes those extra bytes. No other physical page is sampled after rejection.

Historical ZG3 evidence records success at slide `0x140000`, not at any collision slide. No retained log demonstrates collision recovery or proves the four placements reachable.

## Reachability conclusion

`p0_slide_reachability.csv` records all 125 rows as `UNKNOWN`. The kernel's `arch/arm64/kernel/kaslr.c` derives a randomized virtual offset aligned to 2 MiB. It does not describe the separate 0x4000-granular physical P0 placement observed by this oracle. Kernel configuration confirms KASLR is enabled, but the Samsung bootloader/physical loader algorithm is absent. Fingerprint-table membership cannot supply that missing proof.

## Final verdict

`READY_FOR_MORE_STATIC_ANALYSIS`

An offline target draft remains premature while collision-placement reachability is unknown and 17 active parameters are genuinely runtime dependent. Further static closure is possible only if the missing bootloader/loader artifact or authoritative placement description is added to the repository.
