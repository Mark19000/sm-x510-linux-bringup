# EZE4 Patch Migration Matrix

**Date:** 2026-09-05  
**Audit Scope:** Downstream bring-up patchset for Samsung Galaxy Tab S9 FE (SM-X510)  
**Input Series:** `patches/downstream/wifi/` (0001–0006, 0008–0011) and `patches/downstream/5g/` (0001)  
**Reference Source:** Official Samsung OSRC EZE4 (`audit/eze4-source-intake/extracted/kernel/`)  
**Methodology:** Independent inspection of code targets in EZE4 without blind patching; classification based on direct source evidence.

---

## 1. Classification Summary

Every patch maintained by the project was audited against the clean EZE4 source tree:

| Classification | Count (WiFi) | Count (Total incl. 5G) | Patches |
|---|---:|---:|---|
| **ALREADY_FIXED_BY_SAMSUNG** | 0 | 0 | None |
| **STILL_REQUIRED** | 8 | 8 | 0001, 0003, 0004, 0005, 0006, 0008, 0009, 0010 |
| **REQUIRES_ADAPTATION** | 2 | 2 | 0002, 0011 |
| **OBSOLETE** | 0 | 1 | 5G 0001 (target file absent from SM-X510 release) |
| **UNDETERMINED** | 0 | 0 | None |

> [!IMPORTANT]
> **Zero bugs were fixed by Samsung.** Every vendor C syntax violation, missing type specifier, invalid enum comparison, uninitialized variable, and build reproducibility issue present in U11 persists in EZE4. Samsung's release build succeeded solely because they compiled with an older compiler (`clang-r450784d` / Clang 14.0.6) with relaxed warning flags, whereas modern toolchains strictly reject these constructs.

---

## 2. One-by-One Patch Audit

### Patch 0001: Early Userspace Support (WiFi)
- **PATCH NAME / NUMBER:** `0001-arm64-configs-gts9fewifi-enable-linux-early-userspace.patch`
- **ORIGINAL PROBLEM:** Shipping Samsung Android defconfig deliberately disables `DEVTMPFS`, devtmpfs automount, virtual terminals (`VT`), and file handles (`FHANDLE`). A standalone diagnostic Linux initramfs cannot populate `/dev` dynamically, cannot bind a virtual terminal console (`tty1`), and panics or fails early userspace execution.
- **FILES / SYMBOLS INVOLVED:** `arch/arm64/configs/s5e8835-gts9fewifixx_defconfig`
- **WHAT U11 DID:** Enabled:
  - `CONFIG_FHANDLE=y`
  - `CONFIG_DEVTMPFS=y`
  - `CONFIG_DEVTMPFS_MOUNT=y`
  - `CONFIG_VT=y`
  - `CONFIG_CONSOLE_TRANSLATIONS=y`
  - `CONFIG_VT_CONSOLE=y`
  - `CONFIG_VT_HW_CONSOLE_BINDING=y`
- **WHAT EZE4 DOES:** EZE4 defconfig lines 234, 1782, and 2981 explicitly retain:
  - `# CONFIG_FHANDLE is not set`
  - `# CONFIG_DEVTMPFS is not set`
  - `# CONFIG_VT is not set`
- **EVIDENCE:** Direct inspection of `arch/arm64/configs/s5e8835-gts9fewifixx_defconfig:234,1782,2981`.
- **CLASSIFICATION:** `STILL_REQUIRED`
- **FUTURE ACTION:** Maintain configuration support. Recommended practice: inject via `configs/gts9fe-linux.fragment` using `merge_config.sh` rather than maintaining a fragile patch against the 8,500-line defconfig.

---

### Patch 0002: Modern Clang Compatibility
- **PATCH NAME / NUMBER:** `0002-build-fix-modern-clang.patch`
- **ORIGINAL PROBLEM:** The vendor kernel code was written for older C standards and builds with older Clang. Modern Clang (Clang 15+ through Clang 21) strictly rejects:
  1. `arch/arm64/kvm/sys_regs.c`: `struct sys_reg_desc clidr;` passed by pointer without initialization.
  2. `kernel/sched/ems/sysbusy.c`: `static cpn_next_cpu[...]` declared without type (implicit-int removed in C99/C11/C23).
  3. `mm/filemap.c`: `static void filemap_tracing_mark_end()` declared with empty parameter list `()` instead of `(void)` (deprecated non-prototype / strict prototype violation).
- **FILES / SYMBOLS INVOLVED:**
  - `arch/arm64/kvm/sys_regs.c` (`kvm_sys_reg_table_init()`, `clidr`)
  - `kernel/sched/ems/sysbusy.c` (`cpn_next_cpu`)
  - `mm/filemap.c` (`filemap_tracing_mark_end()`)
- **WHAT U11 DID:**
  - Initialized `struct sys_reg_desc clidr = { 0 };`
  - Declared `static int cpn_next_cpu[...]`
  - Added `(void)` to `filemap_tracing_mark_end(void)` declarations and stubs.
- **WHAT EZE4 DOES:**
  1. `arch/arm64/kvm/sys_regs.c:2793`: `struct sys_reg_desc clidr;` remains completely uninitialized. (Line shifted from 2784 to 2793 due to upstream KVM table validation changes).
  2. `kernel/sched/ems/sysbusy.c:43`: `static cpn_next_cpu[...]` remains untyped. (Line shifted from 40 to 43).
  3. `mm/filemap.c:3008, 3015`: `static void filemap_tracing_mark_end()` remains without `(void)`. (Lines shifted from 2978/2985 to 3008/3015 due to stable memory management backports).
- **EVIDENCE:** Direct verification of lines in EZE4 files: `sys_regs.c:2793`, `sysbusy.c:43`, `filemap.c:3008,3015`.
- **CLASSIFICATION:** `REQUIRES_ADAPTATION`
- **FUTURE ACTION:** Rebase patch hunks to match EZE4 line numbers. The fixes themselves remain 100% required when compiling with modern Clang.

---

### Patch 0003: devfreq Return Type Specification
- **PATCH NAME / NUMBER:** `0003-devfreq-add-missing-return-type.patch`
- **ORIGINAL PROBLEM:** `include/soc/samsung/exynos-devfreq.h` declared `extern exynos_devfreq_alt_mode_change(...)` omitting the return type. While the implementation returns `int`, the header relied on C's obsolete implicit-int rule, causing compiler errors under `-Werror=implicit-int`.
- **FILES / SYMBOLS INVOLVED:** `include/soc/samsung/exynos-devfreq.h` (`exynos_devfreq_alt_mode_change`)
- **WHAT U11 DID:** Added explicit `int` return type: `extern int exynos_devfreq_alt_mode_change(...);`.
- **WHAT EZE4 DOES:** Line 258 of `include/soc/samsung/exynos-devfreq.h` remains:
  ```c
  extern exynos_devfreq_alt_mode_change(unsigned int devfreq_type, int new_mode);
  ```
  The file is byte-identical to U11.
- **EVIDENCE:** SHA-256 match between U11 and EZE4 `include/soc/samsung/exynos-devfreq.h`; inspection of line 258.
- **CLASSIFICATION:** `STILL_REQUIRED`
- **FUTURE ACTION:** Keep patch without changes; hunks apply cleanly.

---

### Patch 0004: Invalid Declarations & Error-Path Dereference in Vendor Drivers
- **PATCH NAME / NUMBER:** `0004-vendor-drivers-fix-invalid-declarations.patch`
- **ORIGINAL PROBLEM:**
  1. `drivers/gpu/drm/samsung/dpu/cal_qt/rcd_reg.c`: `static void rcd_reg_check_cleanup(id)` old K&R style missing parameter type `u32 id`.
  2. `drivers/misc/samsung/scsc/pmu_cal.c`: `extern enable_hwbypass;` missing type `bool`.
  3. `drivers/soc/samsung/exynos-cpupm.c`: In `extern_idle_ip_init()`, if memory allocation fails, `pr_err` prints `name` before `of_property_read_string_index()` has populated it, causing a crash on the error path.
- **FILES / SYMBOLS INVOLVED:**
  - `drivers/gpu/drm/samsung/dpu/cal_qt/rcd_reg.c` (`rcd_reg_check_cleanup`)
  - `drivers/misc/samsung/scsc/pmu_cal.c` (`enable_hwbypass`)
  - `drivers/soc/samsung/exynos-cpupm.c` (`extern_idle_ip_init`)
- **WHAT U11 DID:**
  - Added `u32 id` to `rcd_reg_check_cleanup(u32 id)`.
  - Added `bool` to `extern bool enable_hwbypass;`.
  - Moved `of_property_read_string_index()` above memory allocation in `extern_idle_ip_init()`.
- **WHAT EZE4 DOES:** All three files are **100% byte-identical** to U11:
  - `rcd_reg.c:64` still has `static void rcd_reg_check_cleanup(id)`.
  - `pmu_cal.c:18` still has `extern enable_hwbypass;`.
  - `exynos-cpupm.c:1741` still prints uninitialized `name` before reading it from DT.
- **EVIDENCE:** SHA-256 checksum identity on all three files between U11 and EZE4 trees.
- **CLASSIFICATION:** `STILL_REQUIRED`
- **FUTURE ACTION:** Keep patch without changes; hunks apply cleanly.

---

### Patch 0005: GPU QoS Flag Helper Return Type
- **PATCH NAME / NUMBER:** `0005-gpu-qos-add-flag-check-return-type.patch`
- **ORIGINAL PROBLEM:** `drivers/gpu/arm/exynos/backend/gpexbe_qos_internal.h` defined `static inline pmqos_flag_check(...)` without a return type. The function evaluates a boolean expression `(type & in) == in`, but relied on implicit-int.
- **FILES / SYMBOLS INVOLVED:** `drivers/gpu/arm/exynos/backend/gpexbe_qos_internal.h` (`pmqos_flag_check`)
- **WHAT U11 DID:** Declared explicit return type: `static inline bool pmqos_flag_check(...)`.
- **WHAT EZE4 DOES:** Line 21 remains:
  ```c
  static inline pmqos_flag_check(mali_pmqos_flags type, mali_pmqos_flags in)
  ```
  The file is byte-identical to U11.
- **EVIDENCE:** SHA-256 identity between U11 and EZE4 `gpexbe_qos_internal.h`.
- **CLASSIFICATION:** `STILL_REQUIRED`
- **FUTURE ACTION:** Keep patch without changes; applies cleanly.

---

### Patch 0006: devfreq Broken Fallback Elimination
- **PATCH NAME / NUMBER:** `0006-devfreq-remove-broken-dfs-id-fallback.patch`
- **ORIGINAL PROBLEM:** In `drivers/devfreq/exynos/exynos-devfreq.c`, `exynos_devfreq_parse_dt()` attempted a fallback:
  ```c
  if (of_property_read_u32(np, "dfs_id", &data->dfs_id) &&
          of_property_match_string(np, "clock-names", buf))
      return -ENODEV;
  ```
  `buf` was an uninitialized local pointer, causing memory corruption / panic if `dfs_id` was missing. On S5E8835, every devfreq node specifies `dfs_id`, making the buggy fallback dead and hazardous.
- **FILES / SYMBOLS INVOLVED:** `drivers/devfreq/exynos/exynos-devfreq.c` (`exynos_devfreq_parse_dt`)
- **WHAT U11 DID:** Removed the invalid fallback, requiring a valid `dfs_id` directly:
  ```c
  if (of_property_read_u32(np, "dfs_id", &data->dfs_id))
      return -ENODEV;
  ```
- **WHAT EZE4 DOES:** Line 1829 contains the verbatim buggy fallback with uninitialized `buf`. The file is byte-identical to U11.
- **EVIDENCE:** SHA-256 identity on `drivers/devfreq/exynos/exynos-devfreq.c`.
- **CLASSIFICATION:** `STILL_REQUIRED`
- **FUTURE ACTION:** Keep patch without changes; applies cleanly.

---

### Note on Missing Patch 0007
- **STATUS:** Never created or committed.
- **EVIDENCE:** `configs/u11-patches.sha256` and Git commit history transition directly from `0006` to `0008`. No patch 0007 exists in the tree.

---

### Patch 0008: Disable Crash-Test Injection & Initialize Charger Event
- **PATCH NAME / NUMBER:** `0008-bringup-disable-crash-tests-and-init-charger-event.patch`
- **ORIGINAL PROBLEM:**
  1. `sec_debug_test.c`: A test module designed to intentionally induce kernel crashes, panics, and lockups. It compiles FPSIMD instructions into a kernel built with `-mgeneral-regs-only`, causing build failures or undefined instruction exceptions.
  2. `drivers/battery/charger/sm5714_charger/sm5714_charger.c`: `_check_slow_rate_charging()` passed an uninitialized `union power_supply_propval value` to `psy_do_property()`.
- **FILES / SYMBOLS INVOLVED:**
  - `drivers/samsung/debug/Makefile` (`sec_debug_test.o`)
  - `drivers/battery/charger/sm5714_charger/sm5714_charger.c` (`_check_slow_rate_charging`, `value`)
- **WHAT U11 DID:**
  - Removed `obj-$(CONFIG_SEC_DEBUG_BASE) += sec_debug_test.o` from `drivers/samsung/debug/Makefile`.
  - Initialized `union power_supply_propval value = { 0 };` in `sm5714_charger.c`.
- **WHAT EZE4 DOES:**
  1. Samsung modified `sec_debug_test.c` to conditionally omit registering the `force_error` sysfs node on product shipping builds (`#if !IS_ENABLED(CONFIG_SAMSUNG_PRODUCT_SHIP) ...`). However, `drivers/samsung/debug/Makefile:10` **still compiles and links** `sec_debug_test.o`.
  2. `sm5714_charger.c:1280` still leaves `union power_supply_propval value;` uninitialized.
- **EVIDENCE:** Direct inspection of `drivers/samsung/debug/Makefile:10` and `sm5714_charger.c:1280` in EZE4.
- **CLASSIFICATION:** `STILL_REQUIRED`
- **FUTURE ACTION:** Keep patch without changes; applies cleanly.

---

### Patch 0009: Novatek Touch IRQ Handler Return Value
- **PATCH NAME / NUMBER:** `0009-input-novatek-return-valid-irq-status.patch`
- **ORIGINAL PROBLEM:** In `drivers/input/touchscreen/novatek/nt36523_tablet_spi/nt36xxx.c`, the threaded interrupt handler `nvt_ts_work_func()` returned `SEC_ERROR` (-1) or `ret` (negative errno like `-ERESTARTSYS`) on resume wait timeouts. These are not valid `irqreturn_t` enum values.
- **FILES / SYMBOLS INVOLVED:** `drivers/input/touchscreen/novatek/nt36523_tablet_spi/nt36xxx.c` (`nvt_ts_work_func`)
- **WHAT U11 DID:** Changed error returns to `return IRQ_HANDLED;`, correctly notifying the interrupt subsystem that the interrupt was acknowledged.
- **WHAT EZE4 DOES:** Lines 2768 and 2773 still return `SEC_ERROR` and `ret`. The file is byte-identical to U11.
- **EVIDENCE:** SHA-256 identity on `nt36xxx.c` between U11 and EZE4.
- **CLASSIFICATION:** `STILL_REQUIRED`
- **FUTURE ACTION:** Keep patch without changes; applies cleanly.

---

### Patch 0010: SM5714 Type-C Power/Data Role Enum Correction
- **PATCH NAME / NUMBER:** `0010-usb-typec-use-power-port-enum.patch`
- **ORIGINAL PROBLEM:** In `drivers/usb/typec/sm/sm5714/sm5714_typec.c`, `sm5714_port_type_set()` receives argument `port_type` of type `enum typec_port_type` (values: `TYPEC_PORT_SRC`, `TYPEC_PORT_SNK`), but compared it against `TYPEC_PORT_DFP` and `TYPEC_PORT_UFP` (which belong to `enum typec_port_data`). Role switching requests were never matched.
- **FILES / SYMBOLS INVOLVED:** `drivers/usb/typec/sm/sm5714/sm5714_typec.c` (`sm5714_port_type_set`)
- **WHAT U11 DID:** Corrected comparisons to `TYPEC_PORT_SRC` and `TYPEC_PORT_SNK`.
- **WHAT EZE4 DOES:** Lines 1351 and 1356 still compare against `TYPEC_PORT_DFP` and `TYPEC_PORT_UFP`. The file is byte-identical to U11.
- **EVIDENCE:** SHA-256 identity on `sm5714_typec.c`.
- **CLASSIFICATION:** `STILL_REQUIRED`
- **FUTURE ACTION:** Keep patch without changes; applies cleanly.

---

### Patch 0011: Deterministic Kernel and vDSO Build IDs
- **PATCH NAME / NUMBER:** `0011-build-use-reproducible-kernel-vdso-build-ids.patch`
- **ORIGINAL PROBLEM:** Top-level `Makefile`, `arch/arm64/kernel/vdso/Makefile`, and `arch/arm64/kernel/vdso32/Makefile` passed `--build-id=sha1` to the linker. Under LLD and ThinLTO, unmapped metadata ordering variations caused the SHA-1 hash to vary between builds, preventing bit-for-bit reproducible `Image` generation.
- **FILES / SYMBOLS INVOLVED:**
  - `Makefile` (`LDFLAGS_vmlinux`)
  - `arch/arm64/kernel/vdso/Makefile` (`ldflags-y`)
  - `arch/arm64/kernel/vdso32/Makefile` (`VDSO_LDFLAGS`)
- **WHAT U11 DID:** Replaced `--build-id=sha1` with explicit fixed 20-byte hexadecimal build IDs.
- **WHAT EZE4 DOES:** EZE4 still uses `--build-id=sha1` in all three files:
  - `Makefile:1141`
  - `arch/arm64/kernel/vdso/Makefile:27`
  - `arch/arm64/kernel/vdso32/Makefile:119`
  In top-level `Makefile`, the line shifted from 1126 to 1141.
- **EVIDENCE:** Direct inspection of Makefiles in EZE4.
- **CLASSIFICATION:** `REQUIRES_ADAPTATION`
- **FUTURE ACTION:** Update patch line offsets for EZE4 top-level `Makefile`. Essential for deterministic byte-identical builds.

---

### 5G Patch: Early Userspace Support for SM-X516
- **PATCH NAME / NUMBER:** `patches/downstream/5g/0001-arm64-configs-gts9fe-enable-linux-early-userspace.patch`
- **ORIGINAL PROBLEM:** Early userspace enablement for 5G cellular variant (`s5e8835-gts9fexx_defconfig`).
- **FILES / SYMBOLS INVOLVED:** `arch/arm64/configs/s5e8835-gts9fexx_defconfig`
- **WHAT U11 DID:** Enabled `CONFIG_DEVTMPFS`, `CONFIG_VT`, etc.
- **WHAT EZE4 DOES:** The target file `arch/arm64/configs/s5e8835-gts9fexx_defconfig` **does not exist** in the SM-X510 (WiFi) EZE4 OSRC archive. Samsung only included `s5e8835-gts9fewifixx_defconfig`.
- **EVIDENCE:** `test -f arch/arm64/configs/s5e8835-gts9fexx_defconfig` returns false.
- **CLASSIFICATION:** `OBSOLETE` (within the scope of SM-X510 WiFi source intake).
- **FUTURE ACTION:** Archive in historical records. Not applicable to SM-X510.

---

## 3. Recommended Migration Patchset for EZE4

When creating the EZE4 build series, the patches should be organized as follows:

```text
patches/downstream/eze4/
├── 0001-arm64-configs-gts9fewifi-enable-linux-early-userspace.patch  [STILL_REQUIRED]
├── 0002-build-fix-modern-clang.patch                                 [REQUIRES_ADAPTATION - rebased]
├── 0003-devfreq-add-missing-return-type.patch                        [STILL_REQUIRED]
├── 0004-vendor-drivers-fix-invalid-declarations.patch                [STILL_REQUIRED]
├── 0005-gpu-qos-add-flag-check-return-type.patch                     [STILL_REQUIRED]
├── 0006-devfreq-remove-broken-dfs-id-fallback.patch                 [STILL_REQUIRED]
├── 0008-bringup-disable-crash-tests-and-init-charger-event.patch     [STILL_REQUIRED]
├── 0009-input-novatek-return-valid-irq-status.patch                 [STILL_REQUIRED]
├── 0010-usb-typec-use-power-port-enum.patch                         [STILL_REQUIRED]
└── 0011-build-use-reproducible-kernel-vdso-build-ids.patch          [REQUIRES_ADAPTATION - rebased]
```

### Next Concrete Actions
1. Keep 8 patches unchanged (`0001`, `0003`, `0004`, `0005`, `0006`, `0008`, `0009`, `0010`).
2. Refresh hunk line numbers for `0002` (`sys_regs.c` +9, `sysbusy.c` +3, `filemap.c` +30).
3. Refresh hunk line numbers for `0011` (`Makefile` +15).
4. Perform baseline compilation test on clean EZE4 before applying adapted patchset.
