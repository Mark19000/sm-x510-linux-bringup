# P0 collision root-cause audit

## Scope and production path

This is a static trace of the retained ZG3 production source. No workaround is proposed.

The active path is `main.c:run_exploit()` -> `slide_app.c:slide_leak_kernel_base()` -> `slide_leak_physical_base()` -> `oracle.c:scan_p0_pipe_oracle()`. `PHYS_P0_ORACLE` is `1` in the ZG3 target, so the legacy `slide_p0_offsets[]` path, boot-id leak, and its 32-candidate loop are excluded at compile time. `PHYS_VIRTUAL_BASE_ORACLE` is not defined by this target, so the virtual-pointer oracle is also excluded.

`scan_p0_pipe_oracle()` scores all 125 physical fingerprints, requires exactly one changed pipe page, requires a unique winner, then applies `best >= 5` and `best - second >= 3`. A rejection returns `(uintptr_t)-1`. `slide_leak_physical_base()` restores the modified oracle pages and returns `0`; `run_exploit()` reports `slide kaslr leak failed` and exits the attempt. There is no transition to another oracle.

## Root cause

The probe relation is `image_offset = 0x1f0000 - slide`. The four affected slides therefore sample the first 64 KiB of the stock Image:

| Slide | Image page | Raw full-page result | Production score |
|---|---:|---|---|
| `0x1e4000` | `0x00c000` | 512/512 QWORDs are `0xd503201fd503201f` | 8 vs 8, reject |
| `0x1e8000` | `0x008000` | 512/512 QWORDs are `0xd503201fd503201f` | 8 vs 8, reject |
| `0x1ec000` | `0x004000` | 512/512 QWORDs are `0xd503201fd503201f` | 8 vs 8, reject |
| `0x1f0000` | `0x000000` | image header/code in part of page; seven sampled NOP QWORDs | 8 vs 7, margin 1, reject |

The three NOP pages are byte-identical across the entire 4 KiB page, so there is no additional byte within the page already read by this oracle that can distinguish those three placements. The page at image offset zero contains additional non-NOP static bytes and is intrinsically distinguishable from the NOP pages, but the existing eight-word selection and margin policy deliberately reject it. The repository contains the full stock Image and thus more offline information, but the production ZG3 target has no compiled fallback that consumes it after rejection.

ZG3 shows the same collision pattern because its corresponding early Image pages have the same padding geometry. The EZE4 problem is therefore inherited from the oracle design, not caused by the 22 changed fingerprint words elsewhere in the table.

## Answers

1. **Hardware reachability:** not provable from the retained static evidence. The target accepts `0x000000..0x1f0000` at `0x4000` alignment and includes all four rows, so the authors treated them as members of the physical placement space. The kernel source's `kaslr.c` governs virtual KASLR and does not establish Samsung bootloader physical-placement choices. The retained bootloader binary/source is absent. The slides cannot be declared unreachable.
2. **Runtime response if reachable:** the fingerprint is rejected, oracle pages are restored, the current exploit attempt returns failure, and production stages are not entered.
3. **Retry without reboot:** it does not solve these collisions. The sampled Image page is fixed by the boot's physical placement. Repeating reclaim/setup may repair a transient oracle failure, but a clean reread produces the same tie or margin.
4. **Existing fallback:** none in the compiled gts9fewifi ZG3 configuration. The legacy boot-id/trace-style route is in the `!PHYS_P0_ORACLE` branch; the virtual-base oracle requires a target macro that gts9fewifi does not define.
5. **Additional static distinguishing data:** yes for `0x1f0000` versus the NOP pages, because image page zero contains non-NOP header/code bytes. No data anywhere inside the three full NOP pages distinguishes `0x1e4000`, `0x1e8000`, and `0x1ec000`. No existing compiled fallback uses other static data.
6. **Meaning of ZG3 success:** commit `b7a854e` records success on slide `0x140000`, a strong non-collision row. It demonstrates neither tolerance nor recovery on collision boots. If a collision placement is reachable, the shipped logic tolerates it only as a failed attempt; repeated attempts in the same boot do not change the root cause.

## Verdict

`COLLISIONS_REQUIRE_FURTHER_RESEARCH`

Static evidence establishes deterministic same-boot failure and absence of a fallback, but it cannot establish whether Samsung's boot chain emits the four placements. If they are reachable, a different boot placement is required for the existing ZG3 logic to progress; that conditional result is not enough to label the collision set reachable without the missing bootloader/distribution evidence.
