# Canonical Terminology — RMG-EZE4 Project Audit

## Offset / Address Terminology

| Term | Definition | Example | NEVER confuse with |
|---|---|---|---|
| **struct member offset** | Byte position of a field within a C struct, from struct base. Source: BTF/DWARF. | `task_struct.pi_lock` at offset `0x884` | symbol offset, allocation bucket |
| **symbol offset** | File offset of a symbol within the uncompressed kernel Image, relative to `KIMAGE_TEXT_BASE`. Source: `Image.stock` disassembly. | `INIT_TASK_OFF = 0x0239fd80` | struct member offset, KASLR offset |
| **virtual address** | Runtime kernel virtual address = `KIMAGE_TEXT_BASE + symbol_offset + KASLR_slide`. | `0xffffffc00a39fd80` (at slide=0) | physical address, P0 label |
| **allocation bucket** | kmalloc slab cache size enclosing a struct. Always >= `sizeof(struct)`. | `MM_STRUCT_SZ = 0x400` for `sizeof(mm_struct) = 0x3e0` | sizeof, struct member offset |
| **payload synthetic offset** | Layout constant defined by payload source, not derived from kernel. | `LOCK_OFF = 0x2210`, `FOPS_OFF = 0x7000` | kernel symbol offset, struct offset |
| **P0 label** | Oracle search/commit index in the P0 fingerprint table. Range `0x000000..0x1f0000` at `0x4000` step. | `0x140000` (from ZG3 success log) | KASLR virtual offset, physical placement |
| **KASLR virtual offset** | Generic arm64 virtual displacement from `kaslr_early_init()`. Always 2 MiB aligned. Disabled by `nokaslr`. | Zero when `nokaslr` is in effect | P0 label, physical placement |
| **physical kernel Image placement** | Physical DRAM address where bootloader loads the kernel Image before entry. Determined by Samsung `sboot`, not by kernel. | `0x80000000 + placement_offset` | P0 label, virtual KASLR offset |
| **loader reachability** | Whether a given P0 label corresponds to a physically possible bootloader placement. | `INSUFFICIENT_EVIDENCE` for collision labels | collision, label |

## P0 Oracle Terminology

| Term | Definition |
|---|---|
| **candidate** | A single P0 label/slide value in the fingerprint table |
| **fingerprint row** | One entry: `{ slide, words[8] }` extracted from Image at `probe_offset - slide` |
| **collision** | Two or more candidates producing identical or indistinguishable fingerprint rows |
| **score** | Integer 0-8: count of matching qwords between observed page and fingerprint row |
| **margin** | `best_score - second_best_score`; must be >= `P0_FINGERPRINT_MIN_MARGIN` (3) |
| **rejection** | Oracle returns -1 when score < `MIN_BEST` (5) or margin < `MIN_MARGIN` (3) |

## Runtime / Experiment Terminology

| Term | Definition | NEVER confuse with |
|---|---|---|
| **trial** | One complete child process lifecycle from ATTEMPT_SPAWN to terminal event | campaign, boot |
| **trial validity** | VALID, INVALID, or INCONCLUSIVE — structural/confounder quality of the observation | evidence vote, terminal class |
| **terminal class** | How the trial ended (QUALIFYING_COMPLETION, SUPERVISOR_OVERALL_TIMEOUT, etc.) | validity, vote |
| **evidence vote** | COMPATIBLE_VOTE, INCOMPATIBLE_VOTE, or NO_VOTE — the trial's contribution to verdict | validity, terminal class |
| **campaign verdict** | Final E4 aggregation: COMPATIBLE, INCOMPATIBLE, INCONCLUSIVE, INVALID_EXPERIMENT | trial vote |
| **qualifying trial** | VALID trial with an evidence vote (not NO_VOTE) | invalid trial |
| **invalid trial caps** | Maximum $\le 1$ invalid trial per boot, maximum $\le 2$ invalid trials total across campaign | "per cell" caps |
| **confounder present** | Detector positively identifies interfering condition (freezer, thermal, etc.) | confounder unknown |
| **confounder unknown** | Detector cannot determine confounder state (e.g., no access to sysfs) | confounder absent |
| **condition class** | SETTLED_NOMINAL or ELEVATED_VALID — the environmental partition for the trial | confounder |
| **run package** | Frozen set of binaries/scripts deployed for execution | raw evidence |
| **raw evidence manifest** | SHA256-hashed inventory of all observation output files from a session | run package |
| **boot** | One distinct device boot cycle identified by cryptographic boot_id | session |

## Confounders (C1, C2, C3)

| Confounder | Canonical Name | Canonical Definition | Canonical Attribution Distinction |
|---|---|---|---|
| **C1** | `UNSEPARATED_P0_DELAY` | **unseparated P0 contamination** | P0 consuming time != C1 contamination. C1 means that the state or elapsed contribution of P0 cannot be separated or attributed correctly from the post-fork candidate lifecycle. Verified `P0_EXIT_SLIDE_READY` prior to 1200s establishes separation. |
| **C2** | `ANDROID_CGROUP_FREEZER` | **Android freezer / suspension** | Android cgroup freezer or kernel suspend halts user process execution while monotonic clock advances, artificially inflating elapsed duration. |
| **C3** | `THERMAL_THROTTLING_CORE_MIGRATION` | **thermal throttling / core migration** | Thermal governor clamps CPU frequency below valid baseline or migrates workload across core types, inflating duration tails. |

## Parameter Classification

| Term | Definition |
|---|---|
| **correctness-critical** | Wrong value causes incorrect kernel state or path failure |
| **reliability-critical** | Wrong value reduces success probability but doesn't corrupt state |
| **policy-only** | Value controls retry/timeout behavior; wrong value causes safe abort |
| **runtime-required** | Cannot be validated from static analysis alone; needs device execution |
| **must-validate** | Subset of runtime-required that is explicitly protected from environment-similarity reasoning |

## Forbidden Ambiguous Usages

- Do NOT use "offset" without qualifying which kind (struct, symbol, synthetic, P0)
- Do NOT use "address" to mean "offset" or vice versa
- Do NOT use "confirmed" to mean "inferred" or "probably reusable"
- Do NOT use "collision reachable" or "collision unreachable" — only "INSUFFICIENT_EVIDENCE"
- Do NOT conflate P0 label with KASLR virtual offset or physical placement
- Do NOT say "validated" for a parameter that has only environmental evidence
- Do NOT say "absent" when you mean "not observed" or "access denied"
- Do NOT say "not applicable" for parameters that are merely "legacy inactive"
- Do NOT define C1 as "ambient interference"; C1 is strictly **unseparated P0 contamination** (`P0 consuming time != C1 contamination`)
- Do NOT define C2 as simply "freezer desync"; C2 is strictly **Android freezer / suspension**
- Do NOT define C3 as simply "thermal throttle"; C3 is strictly **thermal throttling / core migration**
- Do NOT state invalid trial caps as "per cell"; invalid caps are strictly **$\le 1$ per boot** and **$\le 2$ total**
- Do NOT declare repository hygiene "fully restored" while unrelated untracked work intentionally remains in the working tree (`J2 checkpoint hygiene: COMPLETE`; `overall repository working tree: DIRTY BY DESIGN`)
