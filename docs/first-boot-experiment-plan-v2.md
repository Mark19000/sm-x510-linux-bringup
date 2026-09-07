# First Boot Experiment Plan v2

> **SUPERSEDED — HISTORICAL, NON-OPERATIONAL, DOES NOT AUTHORIZE FLASH.** This plan uses U11, ambiguous observability, and unvalidated recovery. Current EZE4 authority is `docs/boot-chain/first-custom-kernel-experiment.md`; USB, current draw, backlight, or an altered reboot pattern do not by themselves prove kernel execution.

**Date:** 2026-08-24
**Project:** Samsung Galaxy Tab S9 FE Linux Bring-Up
**Device:** SM-X510 Wi-Fi, U12/EZE4, Android 16, SoC S5E8835 (Exynos 1380)
**Candidate Kernel:** U11 Linux 5.15.180 (OSRC X510XXSBDZB4)

---

## 1. What We Know

### 1.1 Confirmed Evidence

| # | Finding | Source |
|---|----------|--------|
| F1 | All boot/init_boot/vendor_boot/dtbo images signed SHA256_RSA4096 with same key (`b6924fd4...4029`). Flags=0 across all. Global rollback index = 0. | AVB Agent, `avbtool info_image` |
| F2 | `boot.img`: 39.36 MB kernel, empty ramdisk, **empty** cmdline header. | Earlycon Agent |
| F3 | `init_boot.img`: no kernel, 2.49 MB LZ4 ramdisk, **empty** cmdline header. | Earlycon Agent |
| F4 | `vendor_boot.img`: 18 MB vendor_ramdisk (281 DLKM 5.15.189 modules), Samsung compressed DTB, actual bootconfig = **0 bytes** (the 28B was table padding). | Earlycon Agent |
| F5 | DT `chosen.bootargs` = `console=ram printk.devkmsg=on arm64.nopauth ...`. No `earlycon=` or `stdout-path`. | Earlycon Agent |
| F6 | Legacy driver `samsung_tty.c` registers earlycon for `exynos4210-uart`; current driver `exynos_tty.c` (`samsung,exynos-uart`) **HAS NO `OF_EARLYCON_DECLARE`**. | Earlycon Agent, sources/ |
| F7 | DTBO overlays U11 vs EZE4: all three byte-identical verified with `cmp`. | Image Architecture Agent |
| F8 | `sec_debug_next @ 0x91200000`, 2 MiB, no-map — present in overlay, NOT in base DTB. | sec_debug Agent, DT audit |
| F9 | U11 sec_debug modules available: minimal reset_reason closure = 6 modules (~675 KiB raw); full core = 10 modules (~725 KiB raw). | sec_debug Integration Agent |
| F10 | `CONFIG_MODULE_SIG_PROTECT=y` but `sig_enforce` compiles to `false` → unsigned modules load with taint, are NOT rejected via that path. | Risk Reviewer C3 |
| F11 | Vermagic U11 5.15.180 ≠ stock 5.15.189-android13-3 → stock DLKM modules incompatible with U11 kernel due to CRC/vermagic. | Prior ABI audit |
| F12 | PSCI 1.0 smc; GIC-400; arch_timer 26 MHz; oscclk 52 MHz — identical between U11 and EZE4. | DT audit |
| F13 | The 4 DT diffs U11→EZE4 (EMS×2, mfc debug_mode, scsc cpu_table_rps) are post-printk. They do not affect pre-printk. | DT audit |
| F14 | Physical unit hw_rev: **unknown**. The names U12/EZE4/REV00 do not permit inferring actual physical revision. | Hardware Identity Agent |
| F15 | MINIMAL initramfs profile already exists: ~674 KiB LZ4, ~1.8 MiB positive margin over stock init_boot ramdisk. | Prior initramfs design |

### 1.2 Risk Reviewer Corrections

| # | Correction | Impact |
|---|-----------|---------|
| R1 | `earlycon=samsung,...` is invalid; registered form is `exynos4210` | Plan v1 contained incorrect command |
| R2 | UART0 is `disabled` in DT and uses USI v2 — physical accessibility unproven | earlycon may yield no output even if enabled |
| R3 | Signature risk overestimated — actual issue is CRC/vermagic | Reduces a perceived barrier for loading custom modules |
| R4 | `hardware-observation-plan.md` contradicts active NO-GO by recommending new ramoops | Older document requires revision |

---

## 2. What We Do Not Know

| # | Unknown | Impact on Experiment |
|---|-----------|----------------------|
| U1 | Does Samsung bootloader respect `VERIFICATION_DISABLED` (`flags=2`) under UNLOCKED? | `flags=1` only disables hashtree; Samsung policy remains unknown |
| U2 | Does unlocking erase data? Does it irreversibly trip Knox? | Owner decision required prior to any flash |
| U3 | Does bootloader append parameters to final cmdline at runtime? | Could enable earlycon automatically or add restrictions |
| U4 | Actual physical hw_rev (r00, r01, or r04?) | Determines which overlay bootloader applies |
| U5 | Is UART0 physically accessible? (USI v2, disabled in DT) | If not, earlycon produces no visible output |
| U6 | Actual LZ4 ratio of SEC_DEBUG initramfs profile | Does it fit within init_boot? |
| U7 | Bootloader behavior upon early kernel crash (reboot loop? hang?) | Affects interpretation of USB signals |
| U8 | Exact sysfs paths exposed by sec_debug modules on this kernel | Requires runtime observation |

---

## 3. Minimal Experiment

### Definition

The minimal experiment is NOT "flashing a custom kernel". It is a **sequence of controlled probes** where each phase isolates exactly one variable.

### Phase 0 — Stock Baseline (Read-Only)

**Objective:** Document normal behavior to establish reference.

**Actions (zero modifications):**
1. Connect powered-on tablet via USB-C with inline power meter.
2. Document current draw in idle, during charging, during standard use.
3. Enter Download Mode (Vol- + connect cable): document VID/PID, current draw, stabilization time.
4. From ADB (if available), collect:
   - `getprop ro.hw_revision` / `ro.board.platform`
   - `/proc/device-tree/model`
   - `/proc/cmdline`
   - `/sys/firmware/fdt` (if accessible read-only)
5. Document total time from power-on to full Android boot.

**Criterion:** Quantitative data recorded in experiment log sheet.

### Phase 1 — vbmeta-Only Probe (Under UNLOCKED)

**Objective:** Isolate Samsung bootloader policy with modified vbmeta.

**Precondition:** Device unlocked (owner decision documented).

**Actions:**
1. Unproven hypothesis: vbmeta with `VERIFICATION_DISABLED` (`flags=2`). `flags=1` signifies `HASHTREE_DISABLED`; do not use names interchangeably.
2. Flash ONLY vbmeta.img. DO NOT touch boot/init_boot/vendor_boot/dtbo.
3. Observe boot.

**Possible Outcomes and Interpretation:**

| Outcome | Interpretation | Next Step |
|-----------|---------------|---------------|
| Normal Android boot | Bootloader tolerates specific tested policy; do not generalize to other flags or images | Revalidate before Phase 2 |
| Orange warning + slow but functional boot | Standard unlocked AOSP behavior | Advance to Phase 2 |
| Red warning / reboot loop / download mode | Samsung rejects modified vbmeta even unlocked → major blocker | STOP, investigate alternative |
| Brick / unresponsive to Download Mode | Worst-case scenario | Official recovery procedure |

### Phase 2 — Kernel Marker (boot + vbmeta)

**Objective:** Confirm bootloader hands over control to U11 kernel.

**Actions:**
1. Prepare boot.img with compiled U11 kernel + minimal cmdline (`console=ram` matching stock).
2. Retain stock init_boot and stock vendor_boot.
3. Flash boot.img + vbmeta.img (already modified).
4. Observe.

**Expected Outcome:** U11 kernel receives control. It may crash early due to incompatibility with stock vendor_boot, but that IS ALREADY INFORMATION: it confirms bootloader passed control.

**Minimal Success Signal:** Any USB transition (enumeration clears after bootloader handoff), shift in current draw pattern, or reboot distinct from warning screen.

### Phase 3 — MINIMAL Initramfs (boot + init_boot + vbmeta)

**Objective:** Demonstrate kernel reaches userspace (/init).

**Actions:**
1. Use existing MINIMAL profile (~674 KiB LZ4) as ramdisk in init_boot.img.
2. Flash boot + init_boot + vbmeta.
3. Observe.

**Success Signal:** If visible console, message `[gts9fe-init] userspace reached`. If not, electrical pattern shift (kernel executing scheduler vs flat bootloader).

### Phase 4 — SEC_DEBUG BRING-UP (boot + init_boot + vbmeta)

**Objective:** Activate Samsung crash/debug infrastructure to obtain post-mortem evidence.

**Actions:**
1. Extend MINIMAL initramfs with the first 4 sec_debug modules:
   - `exynos-pmu-if.ko`
   - `dss.ko`
   - `sec_debug_dprt.ko`
   - `sec_debug_base_early.ko`
2. /init script that loads modules in sequence and lists `/sys/kernel/sec_debug/*`.
3. Flash and observe.
4. If failure: trigger deliberate crash (`echo c > /proc/sysrq-trigger`) and verify whether `sec_debug_next @ 0x91200000` contains data post-reboot.

---

## 4. Participating Images

| Phase | boot.img | init_boot.img | vendor_boot.img | dtbo.img | vbmeta.img |
|------|----------|--------------|----------------|----------|-----------|
| 0 | Stock | Stock | Stock | Stock | Stock |
| 1 | Stock | Stock | Stock | Stock | **Hypothetical** (`flags=2`; unauthorized) |
| 2 | **U11 kernel** | Stock | Stock | Stock | Modified |
| 3 | **U11 kernel** | **MINIMAL ramdisk** | Stock | Stock | Modified |
| 4 | **U11 kernel** | **SEC_DEBUG ramdisk** | Stock | Stock | Modified |

**vendor_boot remains stock across all initial phases.**

Known risk: its 281 DLKM modules are incompatible with U11 kernel (F11). However, if the U11 kernel has sufficient built-in drivers to reach /init, DLKM modules simply will not load (fail with dmesg error) and the system remains functional in limited mode. This is acceptable for first-boot.

**dtbo.img remains stock** because U11 and EZE4 overlays are identical (F7).

---

## 5. Target Evidence

| Type | Method | Phase |
|------|--------|------|
| Samsung AVB policy under UNLOCKED | Visual/USB outcome after flashing only vbmeta | F1 |
| Control transferred to kernel | USB transition (bootloader clears) + current shift | F2+ |
| Kernel reached userspace | /init console message OR sustained electrical pattern shift | F3+ |
| sec_debug operational | sysfs nodes present post-module loading | F4 |
| Crash captured | Data in region 0x91200000 after deliberate reboot | F4 |
| Physical hw_rev | getprop /proc/device-tree in stock Android | F0 |
| Actual final cmdline | cat /proc/cmdline in stock Android | F0 |

---

## 6. Interpretation of Results

### Decision Tree

```
Phase 1 (vbmeta-only):
├── Normal boot / yellow warning → tolerates specific tested policy → REVIEW before proceeding
├── Red warning / reboot → Samsung blocks → ESCALATE (investigate alternatives)
└── Brick → RECOVER via official firmware → RE-EVALUATE project

Phase 2 (kernel marker):
├── Observable USB/current shift → kernel received control → CONTINUE
├── Red warning / immediate reboot → AVB still blocks boot.img → verify flags/vbmeta
└── Total silence without shift → kernel crashes pre-printk → investigate PSCI/GIC/timer

Phase 3 (minimal initramfs):
├── Shell / visible message → M3 reached → proceed to UFS/rootfs
├── Fluctuating current without console → live kernel, missing channel → prioritize USB ACM
├── Reboot loop → early panic → activate sec_debug (Phase 4) to capture cause
└── Stable hang → possible GIC/timer failure → review U11 kernel config

Phase 4 (sec_debug):
├── Modules load, sysfs present → infrastructure operational → trigger crash test
├── Invalid module format → CRC mismatch between U11 modules and U11 kernel (unexpected) → verify hashes
├── Required key not available → sig_enforce=true at runtime (contradicts F10) → investigate
├── Probe fails silently → DTBO not applied properly → verify selected overlay
└── Reset during load → memory region / TZ hazard → reduce module set
```

---

## 7. Next Step After Each Scenario

| Scenario | Next Action |
|-----------|-----------------|
| Phases 1-4 all successful | Proceed to read-only persistent rootfs (UFS), then USB ACM console, then display |
| Phase 1 succeeds, Phase 2 fails | Verify boot.img was properly repacked (v4 header, size, hash); audit kernel Image entry point |
| Phase 2 succeeds, Phase 3 hang | Kernel runs but does not reach userspace → investigate initramfs format, devtmpfs, console setup |
| Phase 3 succeeds without visible console | Build DEBUG USB profile with serial ACM gadget to obtain interactive channel |
| Phase 4 reveals capturable crash | Analyze sec_debug_next dump to identify root cause of original failure |
| Any phase produces brick | Restore complete official firmware (AP_X510XXUCEZE4 tar.md5) via Odin/Download Mode |

---

## Pending Blockers Prior to Hardware

| # | Blocker | Status |
|---|-----------|--------|
| B1 | Owner decision on unlock/Knox/data wipe | Pending user |
| B2 | Actual LZ4 measurement of SEC_DEBUG initramfs (pack locally) | Pending offline |
| B3 | Stock baseline capture (current draw, cmdline, hw_rev) | Requires powered-on tablet |
| B4 | Test official restore procedure in safe environment | Pending |
| B5 | Investigate whether bootloader appends cmdline parameters at runtime | Phase 0 |

---

## References

- `docs/debugging/earlycon-analysis.md` — earlycon analysis
- `docs/debugging/sec-debug-firstboot-profile.md` — SEC_DEBUG profile design
- `docs/boot-chain/minimal-modification-set.md` — image architecture
- `docs/boot-chain/avb-experiment-plan.md` — staged AVB protocol
- `docs/hardware/device-identity.md` — hardware identity
- `reports/first-boot-risk-review.md` — independent risk review
- `docs/debugging/sec-debug-analysis.md` — prior sec_debug audit
- `docs/first-boot-experiment-plan.md` — plan v1 (superseded by this document)
