# Phase 2B Report — BTF/DWARF Struct Ground Truth and Reclassification

- **Device**: Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510` / `gts9fewifi`)
- **SoC**: Samsung Exynos 1380 (`s5e8835`)
- **Target Base Firmware**: `X510XXUCEZE4` (Kernel Linux 5.15.189)
- **Reference Firmware**: `X510XXSEEZG3` (Kernel Linux 5.15.189)
- **Execution Status**: **PHASE 2B COMPLETED**
- **Date**: 2026-09-06

---

## 1. Correction of Phase 2A Errata

The attribution of operand `#2208` in the disassembly of `remove_waiter()` in `Image.stock` was formally identified and corrected:
- **Detected discrepancy**: $2208_{10} = \mathbf{0x8a0}_{16}$, not `0x8a8`.
- **Ground Truth**:
  - `0x898` (2200): `task_struct.pi_waiters.rb_root` (`struct rb_node *`)
  - `0x8a0` (2208): `task_struct.pi_waiters.rb_leftmost` (`struct rb_node *`)
  - `0x8a8` (2216): `task_struct.pi_top_task` (`struct task_struct *`)
  - `0x8b0` (2224): `task_struct.pi_blocked_on` (`struct rt_mutex_waiter *`)
- **Verdict**: The ZG3 macro `FAKE_TASK_PI_TOP_TASK_OFF 0x8a8` is **100% correct** for `pi_top_task`. The stock instruction `ldr x8, [x21, #2208]` accessed `owner->pi_waiters.rb_leftmost`.
- Full documentation in [`docs/rmg-eze4/PHASE2A_ERRATA.md`](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/PHASE2A_ERRATA.md).

---

## 2. Ground Truth Extraction (BTF and DWARF in EZE4 `vmlinux`)

Exact sizes and offsets of the 12 fundamental kernel structures were extracted using `bpftool btf dump` and `pahole -F btf` over `/home/markpi.guest/osrc-eze4-work/runs/eze4-fixed2/build-source/out-eze4/vmlinux`:

1. `struct task_struct`: size 4608 bytes (`0x1200`), 216 members.
   - `usage` = `0x38`
   - `prio` = `0x7c`
   - `normal_prio` = `0x84`
   - `sched_task_group` = `0x400`
   - `real_cred` = `0x790`
   - `cred` = `0x798`
   - `pi_lock` = `0x884`
   - `pi_waiters` = `0x898`
   - `pi_top_task` = `0x8a8`
   - `pi_blocked_on` = `0x8b0`
2. `struct rt_mutex_waiter`: size 88 bytes (`0x58`), 8 members.
   - `tree_entry` = `0x00`
   - `pi_tree_entry` = `0x18`
   - `task` = `0x30`
   - `lock` = `0x38`
   - `wake_state` = `0x40`
   - `prio` = `0x44`
   - `deadline` = `0x48`
   - `ww_ctx` = `0x50`
3. `struct rt_mutex_base`: size 32 bytes (`0x20`), `waiters` @ `0x08`, `owner` @ `0x18`.
4. `struct rt_mutex`: size 32 bytes (`0x20`).
5. `struct rb_node`: size 24 bytes (`0x18`).
6. `struct rb_root_cached`: size 16 bytes (`0x10`).
7. `struct file_operations`: size 288 bytes (`0x120`), 36 members.
8. `struct file`: size 264 bytes (`0x108`), 23 members.
9. `struct page`: size 64 bytes (`0x40`), `compound_head` @ `0x08`, `slab_cache` @ `0x18`, `page_type` @ `0x30`.
10. `struct mm_struct`: size 992 bytes (`0x3e0`), corresponding to slab bucket `kmalloc-1k` (`0x400`).
11. `struct work_struct`: size 48 bytes (`0x30`), `data` @ `0x00`, `entry` @ `0x08`, `func` @ `0x18`.
12. `struct cred`: size 176 bytes (`0xb0`), 26 members.
13. Additional substructures (`workqueue_struct`, `pool_workqueue`, `worker_pool`, `configfs_buffer`).

All 350 audited fields have been dumped in [`docs/rmg-eze4/eze4_struct_layout.csv`](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/eze4_struct_layout.csv).

---

## 3. Comprehensive Reclassification of Target ZG3 (v2)

Real kernel members were rigorously separated from synthetic payload layouts in [`docs/rmg-eze4/zg3_target_inventory_v2.csv`](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/zg3_target_inventory_v2.csv):

| New Category | Quantity | Description and Examples |
| :--- | :---: | :--- |
| **KERNEL_STRUCT_MEMBER** | **51** | Real structure members (`task_struct.cred`, `rt_mutex_waiter.lock`, `fops.read`). |
| **RUNTIME_TUNING** | **27** | Race attempts, delays, timeouts, and oracle thresholds. |
| **KERNEL_SYMBOL** | **25** | Absolute virtual symbols derived from `KIMAGE_TEXT_BASE + offset`. |
| **EXPLOIT_ALGORITHM_CONSTANT** | **16** | Route and algorithm control constants (`SLIDE_ROUTE_FPSIMD`, `PRODUCTION_STACK_PI_RIGHT_ONLY`, `MM_STRUCT_SZ`, `P0_FINGERPRINT_MIN_*`). |
| **PAYLOAD_SYNTHETIC_LAYOUT** | **15** | Artificial page internal offsets (`W0_OFF`, `LOCK_OFF`, `SCRATCH_OFF`, `FOPS_OFF`, `BANK_*`). |
| **KERNEL_TEXT_OFFSET** | **15** | Text-relative offsets for executable functions (`commit_creds`, `ashmem_mmap`). |
| **KERNEL_DATA_SYMBOL** | **14** | Text-relative offsets for global variables and tables (`init_task`, `kmalloc_caches`). |
| **KERNEL_MEMORY_LAYOUT** | **8** | MMU regions (`KIMAGE_TEXT_BASE`, direct map, vmemmap, KASLR step `0x4000`). |
| **UNKNOWN** | **2** | Preprocessor include guards (`OFFSET_H`, `P0_FINGERPRINT_H`). |
| **BUILD_METADATA** | **2** | Variant label (`BUILD_VARIANT_LABEL`) and header path. |
| **FIRMWARE_FINGERPRINT** | **2** | Android `ro.build.fingerprint` and 32-entry KASLR fingerprint table. |
| **SOC_CONSTANT** | **2** | Exynos 1380 DRAM load physical address (`0x80000000`). |
| **KERNEL_STRUCT_SIZE** | **1** | `STRUCT_PAGE_SIZE` (`0x40`). |
| **TOTAL** | **180** | **100% reclassified with derivation source.** |

---

## 4. Structural Comparison ZG3 vs EZE4 and Cross-Check with `Image.stock`

- **Comparison Result**: **53/53 target-relevant structural parameters audited are identical between ZG3 target and EZE4.**
- **Cross-check with `Image.stock`**: All directly observable accesses in the disassembly of `remove_waiter()` in `Image.stock` match 100% with BTF and DWARF:
  - `task_struct.pi_lock` (`0x884`): **THREE-WAY MATCH**
  - `task_struct.pi_blocked_on` (`0x8b0`): **THREE-WAY MATCH**
  - `task_struct.pi_waiters.rb_root` (`0x898`): **THREE-WAY MATCH**
  - `task_struct.pi_waiters.rb_leftmost` (`0x8a0`): **THREE-WAY MATCH**
  - `rt_mutex_base.waiters` (`0x08`): **THREE-WAY MATCH**
  - `rt_mutex_base.owner` (`0x18`): **THREE-WAY MATCH**
  - `rt_mutex_waiter.lock` (`0x38`): **THREE-WAY MATCH**
  - `rt_mutex_waiter.prio` (`0x44`): **THREE-WAY MATCH**
  - `rt_mutex_waiter.deadline` (`0x48`): **THREE-WAY MATCH**
- Full documentation in [`docs/rmg-eze4/zg3_eze4_struct_diff.md`](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/zg3_eze4_struct_diff.md).

---

## 5. Closure and Metrics of Phase 2B

- **Number of reclassified macros**: **180 / 180 (100%)**
- **Number of audited structural parameters identical ZG3 / EZE4**: **53 / 53 (100.00%)**
- **Number of structural offsets that changed**: **0**
- **Number of remaining UNKNOWN**: **2** (exclusively preprocessor include guards: `OFFSET_H`, `P0_FINGERPRINT_H`)
- **BTF vs DWARF contradictions**: **0**
- **BTF/DWARF vs Image.stock contradictions**: **0**
- **Structural Verdict**: **53/53 target-relevant structural parameters audited are identical between ZG3 target and EZE4.**
- **Pending Factors for Phase 2C**: Mapping and verification of symbol addresses and offsets in `System.map`, `vmlinux`, and `Image.stock`.
