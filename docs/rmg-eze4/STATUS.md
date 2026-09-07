# HISTORICAL / SUPERSEDED — DO NOT USE FOR CURRENT J2 DECISIONS

This static-analysis snapshot predates the canonical J2 closure. Use
`CANONICAL_STATUS.md` and `J2_FINAL_STATUS.md` for current J2 decisions.

# EZE4 static-analysis consolidation status

Audit scope: every Phase 1–3 report and erratum, all CSVs and generated headers in this directory, and the retained ZG3 production target under `.local-only/vendor/Root-My-Galaxy-Payloads-ZG3/`. All conclusions below are static. No payload or target binary was executed.

## CONFIRMED_GROUND_TRUTH

- The EZE4 stock kernel artifact audited here is `artifacts/stock/images/Image.stock`, SHA-256 `ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9`. The rebuilt EZE4 `vmlinux`/Image is a useful type and symbol source but is not byte-identical to stock.
- BTF/DWARF establishes `sizeof(struct task_struct) = 0x1200`. The relevant PI layout is `pi_waiters = 0x898`, `pi_waiters.rb_leftmost = 0x8a0`, `pi_top_task = 0x8a8`, and `pi_blocked_on = 0x8b0`. Thus ZG3's `FAKE_TASK_PI_TOP_TASK_OFF = 0x8a8` is correct; the earlier instruction operand `#2208` is `0x8a0` and accesses `rb_leftmost`.
- BTF/DWARF establishes `sizeof(struct mm_struct) = 0x3e0` (992 bytes). ZG3's `MM_STRUCT_SZ = 0x400` describes the `kmalloc-1k` allocation bucket/slot, not the C structure size. Both values are correct in their distinct meanings.
- The raw structural CSV contains 350 rows. Exactly 53 rows map to ZG3 target parameters, and all 53 are marked `IDENTICAL` against EZE4.
- The stock symbol map contains 54 macro rows: 46 `CONFIRMED_MATCH` and 8 `MINOR_DELTA`. The eight changed macro rows are two representations of four unique changed symbols: `KMALLOC_CACHES_OFF 0x01b04c70 -> 0x01b04bb0`, `ANON_PIPE_BUF_OPS_OFF 0x01912de0 -> 0x01912d20`, `ASHMEM_FOPS_OFF 0x01ab3c08 -> 0x01ab3b48` (each `-0xc0`), and `SLIDE_NFULNL_LOGGER_NAME_OFF 0x017fdc14 -> 0x017fdb3c` (`-0xd8`). Their four derived address macros change correspondingly.
- Values in `EZE4_REBUILT_*` columns are rebuilt-vmlinux values only. Target symbol values must use the `EZE4_STOCK_IMAGE_OFFSET`/`EZE4_STOCK_IMAGE_VA` columns. The stock image matches ZG3 for 46 symbol-map rows even where rebuilt-vmlinux addresses differ materially.
- The active ZG3 physical P0 path iterates `p0_fingerprints[]` by `sizeof`, yielding 125 entries from `0x000000` through `0x1f0000` at step `0x4000`. The 32-value `SLIDE_P0_OFFSET_CANDIDATES` macro is compiled only in the inactive `!PHYS_P0_ORACLE` legacy path.
- Independent rederivation from `Image.stock` found 0 mismatches in 1,000 EZE4 QWORD samples. The CSV and generated header each contain 125 rows/1,000 words and match each other exactly. The ZG3/EZE4 word diff is 978 identical and 22 changed words.
- P0 discrimination has 121 `PASS_STRONG`, three `FAIL`, and one `BORDERLINE` row. Slides `0x1e4000`, `0x1e8000`, and `0x1ec000` map to three byte-identical 4 KiB pages at image offsets `0x00c000`, `0x008000`, and `0x004000`, each consisting solely of ARM64 NOP QWORD `0xd503201fd503201f`. Slide `0x1f0000` maps to image offset zero and differs in one sampled word, but its margin is only 1 and the production threshold rejects it.
- The PI orientation relations in `pi_orientation_matrix.csv` are preserved under the four stock symbol changes. This is static address-order evidence only.

## INFERRED

- `SLIDE_ROUTE_FPSIMD` remains architecturally compatible with EZE4 because the relevant AArch64 signal-frame ABI and audited layouts are unchanged. Operational success on EZE4 remains untested.
- `PRODUCTION_STACK_PI_RIGHT_ONLY = 0` is supported by the unchanged relevant virtual-address ordering. The inference does not validate race timing or allocator behavior.
- The common `-0xc0` delta for three data objects likely reflects binary layout/build differences. The private Samsung build inputs needed to prove the cause are absent, so the cause is not ground truth.
- The expected EZE4 Android fingerprint contains `X510XXUCEZE4`, but the exact `ro.build.fingerprint` string is not retained in the audited evidence.

## EMPIRICAL_ONLY

- All race counts, reclaim counts, timeouts, delay tables, CPU affinity, attempt limits, and page-search/setup limits inherited from ZG3.
- P0 acceptance thresholds `MIN_BEST = 5` and `MIN_MARGIN = 3`. Static analysis proves their present outcomes, not that alternative values would be safe or effective.
- FPSIMD route selection under the device's live SELinux and scheduler behavior.
- ZG3's successful attempt at commit `b7a854e` (slide `0x140000`) proves one non-collision boot succeeded; it does not establish behavior across the full placement space.

## UNRESOLVED

- Whether Samsung's gts9fewifi boot chain can select each of the four collision placements. The retained kernel source describes virtual KASLR, while the physical placement selector/bootloader evidence is absent.
- Exact frequency/distribution of physical P0 placements across boots.
- A safe production response for the three byte-identical NOP pages and the borderline image-header page. No fallback is compiled for the ZG3 target.
- Exact EZE4 `ro.build.fingerprint` and final target label/path conventions.
- EZE4 runtime behavior for all empirical tuning values.

## KNOWN_ERRATA

- `PHASE2A_ERRATA.md`: decimal 2208 is `0x8a0` (`pi_waiters.rb_leftmost`), not evidence for `pi_top_task`; `pi_top_task` remains `0x8a8` by BTF/DWARF.
- `PHASE2B_ERRATA2.md`: replaces the overbroad "internal ABI 100% compatible" claim with 53/53 relevant structural parameters identical; separates `mm_struct` size `0x3e0` from bucket `0x400`; corrects P0 macro classifications.
- `PHASE3A_ERRATA.md`: distinguishes 32 legacy candidates from the active 125-entry physical fingerprint table.
- `PHASE3A.md`: the claimed cause of stock symbol deltas was downgraded to hypothesis; only the stock offsets and measured deltas are confirmed.

## CROSS_FILE_CONTRADICTIONS

- `zg3_target_inventory_v2.csv` still describes `p0_fingerprints` as `[32 entries]`; the actual ZG3 header has 125 entries. This is a stale inventory value superseded by `PHASE3A_ERRATA.md` and direct counting.
- Early Phase 1 symbol comparisons treated rebuilt-vmlinux offsets as firmware changes. `PHASE2C.md` and `eze4_symbol_map.csv` supersede that comparison with stock-Image addresses: only four unique stock symbols change.
- The original Phase 2A prose attributed `ldr [x21,#2208]` to `pi_top_task`. BTF/DWARF proves the instruction addresses `pi_waiters.rb_leftmost` at `0x8a0`.
- Early Phase 2B wording said the internal ABI was wholly compatible. The evidence covers only 53 target-relevant parameters.
- Some reports count 50 unique symbol objectives while the CSV has 54 macro rows; four derived address macros account for the difference. Likewise, eight `MINOR_DELTA` rows represent four unique changed symbols.
- Statements that a clean retry resolves any P0 rejection conflate transient reclaim/read failures with deterministic fingerprint collisions. The ZG3 collision result does not change within the same boot.

## NEXT_BLOCKERS

- Establish physical-placement reachability/distribution from bootloader source, authoritative platform documentation, or separately authorized empirical boot observations.
- Resolve the collision oracle limitation before any production target preparation.
- Capture the exact EZE4 Android build fingerprint.
- Retest the 31 parameters classified `EMPIRICAL_RETEST_REQUIRED` in the readiness matrix under a separately authorized hardware-validation plan.
