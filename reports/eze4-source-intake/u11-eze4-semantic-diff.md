# U11 ↔ EZE4 Semantic Source Differential

**Date:** 2026-09-05  
**Audit Scope:** Samsung Galaxy Tab S9 FE (SM-X510, Exynos S5E8835)  
**Baseline Source:** Samsung OSRC U11 (`X510XXSBDZB4`, base `X510XXU8DYJ4`, Linux 5.15.180)  
**New Source:** Official Samsung OSRC EZE4 (`X510XXUCEZE4`, Linux 5.15.189)  
**Methodology:** Strict non-invasive static comparative audit; SHA-256 tree inventory, per-subsystem hunk inspection, and cross-correlation with project bring-up history and stock firmware artifacts.

---

## 1. Executive Summary

The official EZE4 release (`X510XXUCEZE4`) represents a conservative upstream/vendor maintenance release over U11, not an architectural rewrite. The core kernel steps forward from Linux `5.15.180` to `5.15.189`, accompanied by selective vendor updates in UFS error handling, DWC3 USB power management, Samsung DPU display pipeline, and SCSC Wi-Fi/BT connectivity. 

Crucially for this bring-up project:
1. **Core Platform Stability:** Early boot components—including PSCI EL3 firmware interfaces, GICv3 interrupt routing, Exynos MCT hardware timers, Exynos clock trees, ACPM power management, EMS scheduler internals, and GPU runtime backend—are **byte-for-byte identical** between U11 and EZE4.
2. **Persistence of Downstream Defects:** The new source does **not** fix the downstream C syntax errors, missing type specifiers, uninitialized pointers, or incorrect enum comparisons that necessitated the project's U11 patchset. These defects remain verbatim in EZE4.
3. **Device Tree Discrepancy Resolution:** Product Device Tree overlays (`r00`, `r01`, `r04`) are 100% byte-identical. In the base SoC DTS (`s5e8835.dts`), exactly one line changed (`mfc.debug_mode = 1 -> 0`), which directly resolves the binary MFC difference previously observed in stock EZE4. The other three historical differences (`pe-list/list@0`, `pe-list/list@1`, and `scsc_wifibt.cpu_table_rps`) are proven to be artifacts of an octal escape bug in Samsung's OSRC DTS export script (`\04-7` vs `\0` + `"4-7"`), not actual hardware differences.

---

## 2. Quantitative Tree Panorama

Audit dataset based on `audit/eze4-source-intake/evidence/luna3-u11-eze4-subsystem-inventory.json`:

| Subsystem Scope | U11 Files | EZE4 Files | Unchanged | Changed | Only EZE4 | Engineering Assessment |
|---|---:|---:|---:|---:|---:|---|
| **Core Kernel** | 6,623 | 6,686 | 6,385 | 238 | 63 | Upstream 5.15.y stable updates + Samsung security additions |
| **arch/arm64** | 689 | 689 | 667 | 22 | 0 | Upstream arm64 mitigations, BPF JIT, ptrace; SoC logic unchanged |
| **Samsung Exynos Platform** | 360 | 360 | 359 | 1 | 0 | Only `exynos-chipid.c` updated; ASV/cal-if identical |
| **SoC Initialization** | 18 | 18 | 18 | 0 | 0 | S5E8835 early init and board matching byte-identical |
| **PSCI / EL3 Interfaces** | 12 | 12 | 12 | 0 | 0 | PSCI SMC handlers and wrappers byte-identical |
| **GIC / IRQ** | 231 | 231 | 227 | 4 | 0 | Exynos GICv3/combiner identical; 4 non-Exynos generic drivers changed |
| **Timers** | 34 | 34 | 34 | 0 | 0 | Exynos MCT (Multi-Core Timer) byte-identical |
| **Clocks** | 351 | 351 | 350 | 1 | 0 | Exynos CMU clock drivers 100% identical; only AM4 binding changed |
| **Power Domains / PM** | 362 | 362 | 357 | 5 | 0 | Exynos PM, ACPM IPC, CPU PM identical; generic PM fixes |
| **UFS / Storage** | 79 | 79 | 74 | 5 | 0 | Vendor UFS error recovery and UPIU head-of-queue fixes |
| **USB** | 957 | 959 | 903 | 54 | 2 | DWC3 core/gadget concurrency fixes; Exynos SUSPHY state handling |
| **Type-C** | 42 | 42 | 40 | 2 | 0 | Type-C notifier water detection; SM5714 typec driver unchanged |
| **DRM / Display** | 1,126 | 1,126 | 1,117 | 9 | 0 | Samsung DPU window allocation, HDR buffer sanitization, DQE hardening |
| **Input / Touch** | 648 | 648 | 642 | 6 | 0 | Novatek NT36523 SPI touch driver unchanged; generic drivers updated |
| **WiFi / BT (SCSC)** | 342 | 342 | 329 | 13 | 0 | SCSC release point 174 -> 180; concurrency and regulatory handling |
| **sec_debug** | 64 | 64 | 63 | 1 | 0 | `sec_debug_test.c` gates `force_error` on shipping; driver still linked |
| **DSS (Debug Snapshot)** | 14 | 14 | 14 | 0 | 0 | DSS logging, scratchpad, and panic handlers byte-identical |
| **EMS Scheduler** | 23 | 23 | 23 | 0 | 0 | Exynos Mobile Scheduler 100% identical; syntax bugs persist |
| **devfreq** | 27 | 27 | 27 | 0 | 0 | Exynos devfreq governor and profiles 100% identical |
| **GPU** | 1,221 | 1,238 | 1,221 | 0 | 17 | Mali GPU kernel runtime identical; added Android.bp build specs |
| **Build System** | 467 | 467 | 456 | 11 | 0 | Makefile SUBLEVEL 189; compiler flags; defconfig sync |
| **Device Tree (Product)** | 3 | 3 | 3 | 0 | 0 | GTS9FE WiFi overlays (`r00`, `r01`, `r04`) 100% byte-identical |
| **Modules Configuration** | 14 | 14 | 14 | 0 | 0 | Module order and load lists for S5E8835 identical |

---

## 3. Subsystem-by-Subsystem Engineering Audit

### 3.1. Core Kernel (`kernel/`, `mm/`, `fs/`, `security/`, `lib/`)

- **Overview:** 238 files modified, 63 files added (predominantly under `security/samsung/`).
- **Meaningful Changes:**
  - **Upstream Stable Sync (5.15.180 -> 5.15.189):** Updates in BPF verifier, RCU callbacks, scheduler balancing (`kernel/sched/core.c`, `fair.c`), memory compaction, and page cache folio backports (`mm/filemap.c`, `memory.c`, `page_alloc.c`, `vmscan.c`).
  - **Samsung Security Framework Additions:** 63 new files introduce Samsung DEFEX LSM v2 (`security/samsung/defex_lsm/`), DSMS, FIVE, KUMIHO, and PROCA integrity monitors. Corresponding defconfig flags (`CONFIG_SECURITY_SEATD`, DEFEX IMR) are enabled.

#### Structured Change Report:
- **PATH:** `mm/filemap.c`
- **U11 BEHAVIOR:** Empty parameter list in `static void filemap_tracing_mark_end()` (lines 2978, 2985).
- **EZE4 BEHAVIOR:** Backports stable fixes shifting line numbers to 3008 and 3015. The declarations remain `static void filemap_tracing_mark_end()` without `void`.
- **WHY IT MAY MATTER:** Compiling with Clang 15+ triggers `-Wdeprecated-non-prototype` or error under modern C23 standards.
- **RELATION TO OUR PREVIOUS BRING-UP:** Patch `0002-build-fix-modern-clang.patch` addressed this in U11. The underlying issue is not resolved by Samsung; hunk offsets must be adapted for EZE4.
- **CONFIDENCE:** High (direct source verification).

---

### 3.2. arch/arm64

- **Overview:** 22 files modified.
- **Meaningful Changes:** Maintenance of CPU errata (`cputype.h`, `spectre.h`, `proton-pack.c`), ptrace register access sanitization, MMU page table attribute propagation, and arm64 BPF JIT fixes.
- **Exynos Relevance:** No changes to arch-specific Exynos platform hooks or CPU boot code.

#### Structured Change Report:
- **PATH:** `arch/arm64/kvm/sys_regs.c`
- **U11 BEHAVIOR:** `struct sys_reg_desc clidr;` declared uninitialized in `kvm_sys_reg_table_init()`.
- **EZE4 BEHAVIOR:** File contains upstream table order assertions; line shifted from 2784 to 2793. `clidr` remains completely uninitialized.
- **WHY IT MAY MATTER:** Modern Clang flags uninitialized struct passed via pointer.
- **RELATION TO OUR PREVIOUS BRING-UP:** Patch `0002-build-fix-modern-clang.patch` initialized `clidr = { 0 };`. Still required; line offset +9.
- **CONFIDENCE:** High (direct source inspection).

---

### 3.3. Samsung Exynos Platform & SoC Initialization

- **Overview:** 360 files examined; 359 byte-identical.
- **Meaningful Changes:** Exactly one file updated: `drivers/soc/samsung/exynos-chipid.c`.

#### Structured Change Report:
- **PATH:** `drivers/soc/samsung/exynos-chipid.c`
- **U11 BEHAVIOR:** Single match loop comparing `(product_id & EXYNOS_MASK) == soc_ids[i].id`. Revisions extracted via fixed shifts.
- **EZE4 BEHAVIOR:** Introduces `struct exynos_chipid_variant`, helper `exynos_chipid_get_chipid_info()`, and OF match table data binding. Extracts main and sub revisions based on per-SoC variant register layouts.
- **WHY IT MAY MATTER:** Provides more reliable detection of sub-revisions of S5E8835 silicon during boot. Does not alter Device Tree board matching or boot arguments.
- **RELATION TO OUR PREVIOUS BRING-UP:** Does not conflict with any bring-up patch. Beneficial improvement.
- **CONFIDENCE:** High.

---

### 3.4. PSCI / EL3 Interfaces

- **Overview:** 12 files examined; 12 byte-identical (`drivers/firmware/psci/`, `arch/arm64/kernel/psci.c`).
- **Meaningful Changes:** Zero.
- **Implication:** The EL3 SMC call ABI (CPU_ON, SYSTEM_RESET, SYSTEM_OFF, CPU_SUSPEND) expected by the kernel has not changed between U11 and EZE4.
- **CONFIDENCE:** High.

---

### 3.5. GIC / IRQ & Timers

- **Overview:** Exynos MCT (`drivers/clocksource/exynos_mct.c`) and Exynos GICv3 implementation are 100% byte-identical.
- **Meaningful Changes:** 4 changed files in generic drivers (`irq-gic-v2m.c`, `i8253.c`, `mips-gic-timer.c`, `timer-stm32-lp.c`), none of which are compiled or used on S5E8835.
- **CONFIDENCE:** High.

---

### 3.6. Clocks & Power Management (PM / ACPM)

- **Overview:**
  - `drivers/clk/samsung/`: 100% byte-identical. All CMU drivers (`clk-exynos8835.c`, etc.) unchanged.
  - `drivers/soc/samsung/cal-if/`: 100% byte-identical.
  - `drivers/soc/samsung/exynos-cpupm.c`: 100% byte-identical.
  - `drivers/soc/samsung/exynos-pm.c`: 100% byte-identical.

#### Structured Change Report:
- **PATH:** `drivers/soc/samsung/exynos-cpupm.c`
- **U11 BEHAVIOR:** In `extern_idle_ip_init()`, `name` is printed on allocation failure before `of_property_read_string_index()` is invoked, causing a NULL/uninitialized pointer dereference.
- **EZE4 BEHAVIOR:** Verbatim copy of U11 lines 1736-1744. Bug remains unfixed by Samsung.
- **WHY IT MAY MATTER:** Kernel crash during early cpupm initialization if memory allocation fails or DT property is malformed.
- **RELATION TO OUR PREVIOUS BRING-UP:** Patch `0004-vendor-drivers-fix-invalid-declarations.patch` moved DT read before allocation. Patch remains mandatory.
- **CONFIDENCE:** High.

---

### 3.7. UFS / Storage

- **Overview:** 79 files examined; 5 changed (`ufs-sec-feature.c`, `ufs-sysfs.c`, `ufs.h`, `ufs_bsg.c`, `ufshcd.c`).

#### Structured Change Report:
- **PATH:** `drivers/scsi/ufs/ufs-sec-feature.c`
- **U11 BEHAVIOR:** Standard task attributes for security protocol commands.
- **EZE4 BEHAVIOR:** Explicitly sets `upiu_flags |= UPIU_TASK_ATTR_HEADQ` when command is `SECURITY_PROTOCOL_IN` or `SECURITY_PROTOCOL_OUT`.
- **WHY IT MAY MATTER:** Guarantees cryptographic / security commands bypass queued bulk storage transfers, preventing timeouts during RPMB / secure storage access.
- **RELATION TO OUR PREVIOUS BRING-UP:** Enhances storage stability; independent of our bring-up patchset.
- **CONFIDENCE:** High.

#### Structured Change Report:
- **PATH:** `drivers/scsi/ufs/ufshcd.c`
- **U11 BEHAVIOR:** `ufshcd_err_handling_prepare()` was called outside of `host_lock` serialization.
- **EZE4 BEHAVIOR:** Locks `host_lock` around `ufshcd_set_eh_in_progress()`, unlocks for `ufshcd_err_handling_prepare()`, then re-acquires.
- **WHY IT MAY MATTER:** Resolves potential deadlock and race conditions during UFS link recovery.
- **RELATION TO OUR PREVIOUS BRING-UP:** Fixes vendor storage stability issues under high I/O.
- **CONFIDENCE:** High.

---

### 3.8. USB & Type-C Subsystem

- **Overview:** 54 files changed, 2 files added in DWC3 (`dwc3_kret.h`, `dwc3_kret_ops.c`).

#### Structured Change Report:
- **PATH:** `drivers/usb/dwc3/dwc3-exynos.c` & `dwc3-exynos-otg.c`
- **U11 BEHAVIOR:** Standard DWC3 Exynos platform glue without kernel return probe tracking; SUSPHY gating omitted in host transition.
- **EZE4 BEHAVIOR:** Integrates `dwc3_kretprobe_init()` / `exit()` for live debugging of DWC3 state machine transitions. In OTG driver, explicitly sets `dwc3_core_susphy_set(dwc, 1)` upon switching to host mode.
- **WHY IT MAY MATTER:** Low-power PHY suspension prevents excessive battery drain and bus hangs when Type-C accessories are disconnected.
- **RELATION TO OUR PREVIOUS BRING-UP:** Useful runtime improvement.
- **CONFIDENCE:** High.

#### Structured Change Report:
- **PATH:** `drivers/usb/typec/sm/sm5714/sm5714_typec.c`
- **U11 BEHAVIOR:** In `sm5714_port_type_set()`, `port_type` (type `enum typec_port_type`) is compared against `TYPEC_PORT_DFP` and `TYPEC_PORT_UFP` (which belong to `enum typec_port_data`).
- **EZE4 BEHAVIOR:** Byte-identical to U11 (lines 1351, 1356). The incorrect enum comparison remains unfixed by Samsung.
- **WHY IT MAY MATTER:** Type-C role swapping fails or behaves erratically when userspace or PDIC requests DFP/UFP transitions.
- **RELATION TO OUR PREVIOUS BRING-UP:** Fixed by `0010-usb-typec-use-power-port-enum.patch`. Patch remains strictly required.
- **CONFIDENCE:** High.

---

### 3.9. DRM / Display (DPU)

- **Overview:** 1,126 files examined; 9 changed in `drivers/gpu/drm/samsung/dpu/`.

#### Structured Change Report:
- **PATH:** `drivers/gpu/drm/samsung/dpu/exynos_drm_crtc.c`, `exynos_drm_dqe.c`, `exynos_drm_hdr.c`
- **U11 BEHAVIOR:** Window allocation lacked boundary checks during multi-plane DRM commits; DQE histogram buffer bounds unchecked.
- **EZE4 BEHAVIOR:** Adds bounds checking on HDR buffer dimensions, cleans DMA pointers on framebuffer destroy (`exynos_drm_fb.c`), and refactors CRTC window reservation state machine.
- **WHY IT MAY MATTER:** Hardens the display pipeline against crashes when modesetting or flipping buffers in userspace DRM.
- **RELATION TO OUR PREVIOUS BRING-UP:** Important for future graphical userspace (Wayland / DRM modesetting), though not critical for M2 (printk console).
- **CONFIDENCE:** High.

#### Structured Change Report:
- **PATH:** `drivers/gpu/drm/samsung/dpu/cal_qt/rcd_reg.c`
- **U11 BEHAVIOR:** `static void rcd_reg_check_cleanup(id)` omits parameter type `u32 id`.
- **EZE4 BEHAVIOR:** Byte-identical. Missing type specifier persists at line 64.
- **WHY IT MAY MATTER:** Rejected as invalid C by modern Clang.
- **RELATION TO OUR PREVIOUS BRING-UP:** Fixed by `0004-vendor-drivers-fix-invalid-declarations.patch`. Patch remains required.
- **CONFIDENCE:** High.

---

### 3.10. Input / Touch

- **Overview:** 648 files examined; Novatek touch driver byte-identical.

#### Structured Change Report:
- **PATH:** `drivers/input/touchscreen/novatek/nt36523_tablet_spi/nt36xxx.c`
- **U11 BEHAVIOR:** `nvt_ts_work_func()` returns `SEC_ERROR` (-1) or `ret` (negative errno) from a threaded IRQ handler returning `irqreturn_t`.
- **EZE4 BEHAVIOR:** Byte-identical (lines 2768, 2773). Invalid enum return persists.
- **WHY IT MAY MATTER:** Returning invalid integer from IRQ handler can cause kernel warnings or disable the interrupt line if the core IRQ layer treats it as unhandled storm.
- **RELATION TO OUR PREVIOUS BRING-UP:** Fixed by `0009-input-novatek-return-valid-irq-status.patch` to return `IRQ_HANDLED`. Patch remains required.
- **CONFIDENCE:** High.

---

### 3.11. Wi-Fi / Bluetooth (SCSC)

- **Overview:** 342 files examined; 13 changed.
- **Meaningful Changes:** `include/scsc/scsc_release.h` bumps `SCSC_RELEASE_POINT` from 174 to 180, and `CUSTOMER` from 0 to 1.
- **Key Technical Fixes:**
  - Spinlock added to protect packet transport queue in `mxmgmt_transport.c`.
  - Removed obsolete firmware config load `common_sw.hcf` in `mxfwconfig.c`.
  - Added support for SAE-to-PSK downgrade signaling in `cfg80211_ops.c`.
  - Fixed regulatory country code multi-domain update races in `mgt.c` and `mlme.c`.
  - Null BSSID pointer guard in `nl80211_vendor.c`.
- **CONFIDENCE:** High.

---

### 3.12. sec_debug & DSS (Debug Snapshot)

- **Overview:** 64 files examined; 1 changed (`sec_debug_test.c`). DSS files 100% identical.

#### Structured Change Report:
- **PATH:** `drivers/samsung/debug/sec_debug_test.c` & `drivers/samsung/debug/Makefile`
- **U11 BEHAVIOR:** `sec_debug_test.o` compiled into kernel under `CONFIG_SEC_DEBUG_BASE`. Provides sysfs/module parameter `force_error` to deliberately trigger kernel panics, null dereferences, and watchdog resets. Contains floating-point / SIMD instructions compiled with `-mgeneral-regs-only`.
- **EZE4 BEHAVIOR:** Samsung marked `sec_debug_force_error_ops` as `__maybe_unused` and wrapped `module_param_cb(force_error, ...)` inside `#if !IS_ENABLED(CONFIG_SAMSUNG_PRODUCT_SHIP) || IS_ENABLED(CONFIG_SEC_FACTORY)`. However, `drivers/samsung/debug/Makefile:10` **still compiles and links** `sec_debug_test.o`.
- **WHY IT MAY MATTER:** The test object still gets linked into the kernel binary, risking FPSIMD instruction traps on arm64.
- **RELATION TO OUR PREVIOUS BRING-UP:** Patch `0008-bringup-disable-crash-tests-and-init-charger-event.patch` cleanly removed `sec_debug_test.o` from `Makefile`. Patch remains required.
- **CONFIDENCE:** High.

---

### 3.13. EMS Scheduler, devfreq & GPU

- **Overview:**
  - `kernel/sched/ems/`: 23 files, **all 23 unchanged**.
  - `drivers/devfreq/exynos/`: 27 files, **all 27 unchanged**.
  - `drivers/gpu/arm/`: 1,221 runtime files, **all 1,221 unchanged** (only 17 `build.bp` blueprint files added).

#### Structured Change Report:
- **PATH:** `kernel/sched/ems/sysbusy.c`
- **U11 BEHAVIOR:** Line 40 has `static cpn_next_cpu[VENDOR_NR_CPUS] = ...` omitting `int`.
- **EZE4 BEHAVIOR:** Line 43 has identical untyped declaration.
- **RELATION TO BRING-UP:** Patch `0002` required.
- **CONFIDENCE:** High.

#### Structured Change Report:
- **PATH:** `include/soc/samsung/exynos-devfreq.h` & `drivers/devfreq/exynos/exynos-devfreq.c`
- **U11 BEHAVIOR:** Prototype missing `int` at line 258; unsafe fallback with uninitialized `buf` in `exynos_devfreq_parse_dt()` at line 1829.
- **EZE4 BEHAVIOR:** Both files byte-identical to U11.
- **RELATION TO BRING-UP:** Patches `0003` and `0006` required.
- **CONFIDENCE:** High.

#### Structured Change Report:
- **PATH:** `drivers/gpu/arm/exynos/backend/gpexbe_qos_internal.h`
- **U11 BEHAVIOR:** Line 21 omits `bool` return type on `pmqos_flag_check()`.
- **EZE4 BEHAVIOR:** Byte-identical.
- **RELATION TO BRING-UP:** Patch `0005` required.
- **CONFIDENCE:** High.

---

### 3.14. Device Tree Sources

- **Overview:**
  - Product DTS: `gts9fewifi_eur_open_w00_r00.dts`, `r01.dts`, `r04.dts` are **100% byte-identical**.
  - SoC base DTS: `arch/arm64/boot/dts/exynos/s5e8835.dts` contains exactly one line difference across 12,512 lines.

#### Structured Change Report:
- **PATH:** `arch/arm64/boot/dts/exynos/s5e8835.dts`
- **U11 BEHAVIOR:** `/mfc` node: `debug_mode = <0x01>;` (line 8142).
- **EZE4 BEHAVIOR:** `/mfc` node: `debug_mode = <0x00>;` (line 8142).
- **WHY IT MAY MATTER:** Disables verbose kernel logging in MFC video decoder. Exactly matches stock decompiled EZE4 DTB.
- **RELATION TO OUR PREVIOUS BRING-UP:** Confirms that EZE4 source aligns with the stock DTB on MFC.
- **CONFIDENCE:** High (direct hunk verification).

---

### 3.15. Build System & Configuration

- **Overview:** 11 files changed in build system and scripts.
- **Key Changes:**
  - Top-level `Makefile`: `SUBLEVEL = 189`. Added warning suppressions for `-Wno-default-const-init-var-unsafe` and `-Wno-default-const-init-field-unsafe`. Linker build-id rule remains `--build-id=sha1` at line 1141.
  - `arch/arm64/configs/s5e8835-gts9fewifixx_defconfig`:
    - Synchronized to 5.15.189.
    - Samsung DEFEX LSM v2, FIVE, and PROCA options enabled.
    - `CONFIG_DEVTMPFS`, `CONFIG_VT`, and `CONFIG_FHANDLE` remain **disabled**.
- **CONFIDENCE:** High.

---

## 4. Synthesis of Bring-up Failures & Workarounds

| Historical Bring-Up Defect | U11 Status | EZE4 Status | Migration Consequence |
|---|---|---|---|
| Modern Clang implicit-int / missing prototypes | Triggered build errors on Clang 15+ | Unchanged in EZE4 source | Patches 0002, 0003, 0004, 0005 still needed |
| Devfreq unsafe uninitialized buffer fallback | DT parsing crash risk | Unchanged in EZE4 source | Patch 0006 still needed |
| sec_debug crash test injection & FPSIMD traps | Build error & crash risk | `force_error` gated in shipping, but object still compiled | Patch 0008 still needed |
| Novatek touch IRQ invalid return type | Returned -1 / negative errno | Unchanged in EZE4 source | Patch 0009 still needed |
| Type-C SM5714 incorrect port enum comparison | Broke role switching | Unchanged in EZE4 source | Patch 0010 still needed |
| Non-deterministic vmlinux/vDSO build IDs | Image sha256 changed between identical runs | Makefile still uses `--build-id=sha1` | Patch 0011 still needed (adapted for line 1141) |
| Missing devtmpfs / virtual terminals for Linux /init | Headless panic without userspace | Defconfig still disables them | Fragment `gts9fe-linux.fragment` still needed |
| 5.15.180 vs 5.15.189 nominal kernel version mismatch | Blocked stock module loading | **Resolved** (Both are 5.15.189) | Eliminates core version mismatch |

---

## 5. Conclusion

The transition from U11 to EZE4 source is a clean, low-risk upgrade. It solves the nominal kernel version mismatch (`5.15.180` -> `5.15.189`) and incorporates valuable vendor bugfixes in UFS, USB, Display, and Wi-Fi, without introducing any regressions or rewrites in early boot subsystems. 

However, because Samsung did not address the downstream vendor code quality issues, **the project's downstream patchset remains essential**. None of the bring-up work done for U11 is rendered obsolete by EZE4; rather, it provides the exact foundation required to successfully build and run EZE4.
