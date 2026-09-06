# Historical Supersession Map — RMG-EZE4 Project Audit

## Purpose

Track important historical corrections to prevent old phase reports from silently reappearing as active truth.

---

## S-001: P0 Candidate Count 32 → 125

| Field | Value |
|---|---|
| **Old claim** | 32 fingerprint candidates |
| **Corrected claim** | 125 fingerprint candidates |
| **Reason** | Original design targeted 64 KB KASLR step devices; Tab S9 FE uses 16 KB step |
| **Evidence** | `p0_oracle_algorithm.md §3`; `generate_p0_fingerprint.py L215` |
| **Files still containing old claim** | `eze4_target_readiness_v2.csv L181` ZG3 column: "[32 entries]" — **historical/reference, not active bug** |
| **Status** | CORRECTED — active P0 table uses 125 rows |

---

## S-002: pi_top_task Evidence Citation

| Field | Value |
|---|---|
| **Old claim** | 2208 decimal = pi_top_task offset |
| **Corrected claim** | 2208 decimal = 0x8a0 = rb_leftmost; pi_top_task = 0x8a8 |
| **Reason** | Decimal/hex conversion error in original justification |
| **Evidence** | `stock_rtmutex_binary_verification.md L130-131`; `eze4_struct_layout.csv L22` |
| **Files still containing old claim** | `stock_rtmutex_binary_verification.md L130-131` uses notation "2208 + 8" which is confusing — **documentation imprecision, not active bug** (final value 0x8a8 is correct) |
| **Status** | CORRECTED — value is correct, evidence citation is imprecise |

---

## S-003: sizeof(mm_struct) vs MM_STRUCT_SZ

| Field | Value |
|---|---|
| **Old claim** | sizeof(mm_struct) = MM_STRUCT_SZ |
| **Corrected claim** | sizeof(mm_struct) = 0x3e0 (992 bytes); MM_STRUCT_SZ = 0x400 (allocation bucket) |
| **Reason** | Struct size ≠ allocator bucket size |
| **Evidence** | `eze4_struct_layout.csv L2`: size=992; `eze4_target_readiness_v2.csv L7`: "0x400 allocation bucket (sizeof=0x3e0)" |
| **Files still containing old claim** | None found — all active files correctly distinguish the two |
| **Status** | CORRECTED — no residual confusion |

---

## S-004: Rebuild Address vs Stock Address

| Field | Value |
|---|---|
| **Old claim** | EZE4 rebuilt vmlinux addresses usable directly |
| **Corrected claim** | Stock Image.stock offsets are authoritative; rebuild addresses are semantic/layout evidence only |
| **Reason** | Compiler variations produce different code placement between rebuild and Samsung factory build |
| **Evidence** | `eze4_symbol_map.csv` has separate columns for EZE4_REBUILT_VMLINUX_ADDRESS and EZE4_STOCK_IMAGE_OFFSET |
| **Files still containing old claim** | None found in active files — symbol map correctly separates the two |
| **Status** | CORRECTED — no residual confusion |

---

## S-005: P0 Label = Physical KASLR Granularity

| Field | Value |
|---|---|
| **Old claim** | `0x4000` SLIDE_KASLR_STEP is Samsung physical kernel placement granularity |
| **Corrected claim** | `0x4000` is oracle commit/search granularity only; relationship to physical placement is UNPROVEN |
| **Reason** | P0 label domain is payload-internal; physical placement is loader-determined |
| **Evidence** | `kaslr_selection_analysis.md §Meaning of SLIDE_KASLR_STEP`; `eze4_target_readiness_v2.csv L38` |
| **Files still containing old claim** | `eze4_target_readiness_v2.csv L38` EVIDENCE column correctly says "confirmed as oracle commit/search granularity only; not proved as generic kernel or bootloader physical granularity" |
| **Status** | CORRECTED — consistently scoped in active files |

---

## S-006: Schema v2.1 Fingerprint/Kernel Pattern Matching

| Field | Value |
|---|---|
| **Old claim** | Schema accepted fingerprint via `minLength: 10` and kernel via `pattern: ^5\\.15\\.189.*` |
| **Corrected claim** | Schema v2.2.1 requires `const` exact equality for both |
| **Reason** | Pattern/substring matching could accept wrong firmware |
| **Evidence** | `PHASE_J2_1_R1_1.md §4`; `phase_j2_observation_schema_v2.json L62-72` |
| **Files still containing old claim** | `phase_j2_observation_schema.json` (v1) and `phase_j2_schema_migration.md` — **historical context, superseded by v2** |
| **Status** | CORRECTED — schema v2.2.1 enforces exact const |

---

## S-007: J2 Single Timeout = INCOMPATIBLE

| Field | Value |
|---|---|
| **Old claim** | One attributable timeout → INCOMPATIBLE (potential early J2 draft error) |
| **Corrected claim** | One attributable timeout → INCONCLUSIVE; requires ≥3 same-condition across ≥2 boots |
| **Reason** | Single timeout could be transient; statistical threshold needed |
| **Evidence** | `PHASE_J2_1_R1_1.md §6 L88`; `aggregator.py L129-134`; `phase_j2_decision_table.csv` |
| **Files still containing old claim** | None found in active files |
| **Status** | CORRECTED — consistently enforced |

---

## S-008: slide_ready Resets Timer

| Field | Value |
|---|---|
| **Old claim** | slide_ready event resets the candidate timeout epoch |
| **Corrected claim** | slide_ready changes active threshold but does NOT reset epoch |
| **Reason** | Timer epoch must be stable to prevent unbounded execution |
| **Evidence** | `PHASE_J2_1_R1_1.md §6 L86`; `validator.py L162-174` (epoch = post_fork only) |
| **Files still containing old claim** | None found in active files |
| **Status** | CORRECTED — consistently enforced |
