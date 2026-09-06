# Canonical EZE4 Project Status

This file is the authoritative top-level project status document. It supersedes summary conclusions in earlier Phase reports where earlier errata, intermediate normalizations, or later audits disagree.

```text
================================================================================
                    PROJECT: ROOT-MY-GALAXY EZE4 (tab-s9-fe-linux)
                       CANONICAL STATUS & GOVERNANCE MATRIX
================================================================================
Target Model:                Samsung Galaxy Tab S9 FE Wi-Fi
Model / Device Codename:     SM-X510 / gts9fewifi
Firmware Build:              X510XXUCEZE4 (CSC EUX; Multi-CSC OXM: X510OXMCEZE4)
Build Fingerprint:           samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys
Security Patch Level:        2026-05-05 (Auxiliary baseline metadata; Option B)
Kernel Release / Identity:   5.15.189-android13-3-33478785
Stock Kernel Image SHA-256:  ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9

--------------------------------------------------------------------------------
PARAMETER ACCOUNTING (180 PARAMETERS TOTAL — MUTUALLY EXCLUSIVE)
--------------------------------------------------------------------------------
Confirmed Identical:         143
Confirmed Changed:            10
Legacy Inactive:               3
Not Applicable:                3
Probably Reusable:             0
Runtime Validation Required:  20
Statically Unresolved:         1
Total Inventory:             180 (0 duplicates; 180/180 accounted for)

--------------------------------------------------------------------------------
STATIC & BINARY RECONSTRUCTION FINDINGS
--------------------------------------------------------------------------------
Stock Vulnerability Status:  CONFIRMED_PRESENT_IN_STOCK_BINARY
                             (Unpatched remove_waiter() uses current->pi_blocked_on
                             instead of waiter->task->pi_blocked_on in stock binary)
Real EZE4 Root Chain:        NOT YET EXECUTED / NOT DEMONSTRATED
Struct Compatibility:        STRONG — 53/53 target-relevant structure parameters identical
                             (Audited target subset; does NOT claim entire internal ABI)
Structure Layout Details:    sizeof(task_struct) = 0x1200
                             real_cred = 0x790, cred = 0x798
                             pi_lock = 0x884, pi_waiters = 0x898, rb_leftmost = 0x8a0
                             pi_top_task = 0x8a8, pi_blocked_on = 0x8b0
                             (Historical correction: 2208 decimal = 0x8a0 = rb_leftmost, NOT pi_top_task)
                             sizeof(mm_struct) = 0x3e0 (992 bytes)
                             MM_STRUCT_SZ = 0x400 (kmalloc-1k allocation bucket, not struct size)
Payload Synthetic Layout:    LOCK_OFF, W0_OFF, FOPS_OFF, SCRATCH_OFF, RIGHT_OFF,
                             LEFT_OFF, FAKE_TASK_OFF classified strictly as
                             PAYLOAD_SYNTHETIC_LAYOUT, not kernel struct offsets
Stock Symbol Offsets:        CONFIRMED — four firmware-specific symbol offsets changed & rederived:
                             - KMALLOC_CACHES_OFF:          EZE4 0x01b04bb0 (ZG3: 0x01b04c70; -0xc0)
                             - ANON_PIPE_BUF_OPS_OFF:       EZE4 0x01912d20 (ZG3: 0x01912de0; -0xc0)
                             - ASHMEM_FOPS_OFF:             EZE4 0x01ab3b48 (ZG3: 0x01ab3c08; -0xc0)
                             - SLIDE_NFULNL_LOGGER_NAME_OFF: EZE4 0x017fdb3c (ZG3: 0x017fdc14; -0xd8)
PI Orientation Status:       STATICALLY_CONFIRMED_COMPATIBLE (PRODUCTION_STACK_PI_RIGHT_ONLY = 0)
P0 Oracle Table Status:      CONFIRMED_GENERATED (PHYS_P0_ORACLE = 1; 125 rows x 8 QWORDs = 1000 words)
                             Domain: 0x000000 .. 0x1f0000, step = 0x4000
                             Collisions: 3 exact (0x1e4000, 0x1e8000, 0x1ec000 — NOP padding),
                             1 borderline (0x1f0000 — image header); 0 same-boot recovery
P0 Loader Mapping Status:    OPEN — relationship between P0 label (step 0x4000) and physical
                             Samsung bootloader placement granularity is UNKNOWN
NOKASLR Status:              NOKASLR_RUNTIME_STATUS = UNKNOWN (static DT hint != runtime proof)

--------------------------------------------------------------------------------
PHASE J2.1-R1 NON-SEMANTIC REMEDIATION AUDIT STATUS
--------------------------------------------------------------------------------
Phase J2.1-R1 Remediation:   COMPLETE (Zero semantic drift; all 6 audit findings resolved)
J2 Canonical Semantics:      STRONG / FROZEN (phase_j2_e4_contract.md; phase_j2_decision_table.csv)
J2 Validation Stack:         FROZEN (J2_VALIDATION_STACK_FROZEN = YES)
J2 Runtime Feasibility:      OPEN (J2_RUNTIME_FEASIBILITY_CLOSED = NO; C2/C3 observability open)
Split-Engine Architecture:   CLOSED (engine.py isolated to Phase I; aggregator.py/validator.py
                             govern canonical J2, enforced by AST guard test_no_engine_import_in_j2)
Error-Cancelling Fixtures:   CLOSED (phase_j2_timeout_scenarios.json contains 12 canonical campaigns;
                             1 timeout @ E4 asserts INCONCLUSIVE with reason
                             ATTRIBUTABLE_TIMEOUT_WITHOUT_MEETING_FALSIFICATION_THRESHOLD)
Test Oracle Independence:    STRONG (literal string assertions 'COMPATIBLE', 'INCOMPATIBLE',
                             'INCONCLUSIVE', 'INVALID_EXPERIMENT'; no circular symbol imports)
Dynamic Physical Grounding:  CLOSED (check_consistency.py extracts ground truth directly from
                             Phase G raw captures 01-06 and binary SHA256 of Image.stock)
Schema Active/Legacy Split:  CLOSED (Schema v1 marked DEPRECATED; Schema v2.2.1 is active;
                             CLOCK_MONOTONIC and THAWED enforced; validator validates freezer_state)
Repro Tooling Kernel ID:     CLOSED (u11_repro_compare.py corrected to 5.15.189-android13-3-33478785;
                             canonical alias tools/repro_compare.py exported;
                             anti-self-confirmation test test_identical_wrong_kernel_identity_rejected)
Mutation Test Sensitivity:   10 / 10 VERIFIED FOR INTENDED REASON (MUT-01 through MUT-10; MUT-10 verified on isolated 12-trial fixture)

--------------------------------------------------------------------------------
RUNTIME CONFOUNDER OBSERVABILITY STATUS
--------------------------------------------------------------------------------
C1 (Unseparated P0 delay):   PRESENT -> INVALID; UNKNOWN -> INCONCLUSIVE
                             (P0 duration is part of overall monotonic elapsed time;
                             C1 specifically detects unseparated attribution contamination)
C2 (cgroup freezer):         PRESENT -> INVALID; UNKNOWN -> INCONCLUSIVE
                             (Observability on retail stock EZE4: OPEN)
C3 (Thermal throttling):     PRESENT -> INVALID; UNKNOWN -> INCONCLUSIVE
                             (Observability on retail stock EZE4: OPEN)

--------------------------------------------------------------------------------
EXECUTION GATES & CURRENT VERDICTS
--------------------------------------------------------------------------------
J2 Controlled Execution:     DESIGN COMPLETE / VALIDATION MACHINE FROZEN
J3 Live Measurement:         HOLD (Blocked on passive stock C2/C3 confounder observability)
L3 Exploitation / Memory:    NO-GO (Strictly prohibited; real exploit not demonstrated)
Next Planned Phase:          Passive stock C2/C3 confounder observability qualification
================================================================================
```

### Primary Evidence Tracing
- **Firmware identity & artifact provenance**: Grounded dynamically in `docs/rmg-eze4/runtime-evidence/20260906T094426Z/raw/01_product_model.txt` through `06_uname.txt`.
- **Stock kernel digest**: Dynamically computed from `artifacts/stock/images/Image.stock` SHA-256 (`ca56baf4...`).
- **Parameter inventory**: 180 mutually exclusive rows in `docs/rmg-eze4/eze4_target_readiness_v2.csv` (143 identical, 10 changed, 3 legacy inactive, 3 not applicable, 20 runtime-required, 1 statically unresolved; `PROBABLY_REUSABLE = 0`).
- **Structure layouts**: BTF/DWARF extracted in `docs/rmg-eze4/eze4_struct_layout.csv`.
- **Symbol map**: Stock kernel offsets extracted in `docs/rmg-eze4/eze4_symbol_map.csv`.
- **P0 table & collisions**: Generated via `tools/rmg-eze4/generate_p0_fingerprint.py` into `docs/rmg-eze4/p0_fingerprint_EZE4.generated.h` and analyzed in `docs/rmg-eze4/p0_collision_analysis.md`.
- **J2 Campaign Decision Contract**: Governed by `docs/rmg-eze4/phase_j2_e4_contract.md`, `docs/rmg-eze4/phase_j2_decision_table.csv`, and Schema v2.2.1 (`docs/rmg-eze4/phase_j2_observation_schema_v2.json`).
- **Validation implementation**: Implemented in `tools/rmg-eze4/analysis/validator.py` and `tools/rmg-eze4/analysis/aggregator.py`.
- **Test independence & mutation kills**: Documented in `docs/rmg-eze4/audit/J2_AUDIT_REMEDIATION_REPORT.md` and `docs/rmg-eze4/audit/J2_MUTATION_KILL_MATRIX.csv`.
- **Consistency enforcement**: Executed via `tools/rmg-eze4/analysis/check_consistency.py` (7 cross-artifact invariant checks passing).
