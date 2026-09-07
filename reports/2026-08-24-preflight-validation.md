# Pre-Flight Validation Report

> **Errata 2026-09-05:** references in this report to `flags=1` as disable-verification are incorrect. In AVB, `flags=1` is `HASHTREE_DISABLED` and `flags=2` is `VERIFICATION_DISABLED`. This report is preserved as historical record and does not authorize a physical probe.

**Date:** 2026-08-24
**Project:** Samsung Galaxy Tab S9 FE Linux Bring-Up
**Device:** SM-X510 Wi-Fi, U12/EZE4, Android 16
**Kernel:** U11 Linux 5.15.180 (OSRC X510XXSBDZB4)
**Role:** Principal Engineer — pre-physical contact validation

---

## 1. Current Project State

### 1.1 What is confirmed and documented

| Area | State | Evidence |
|------|--------|-----------|
| U11 kernel compilation | ✅ Complete | 9 builds fixed1–fixed9 PASS, Clang 21 ARM64 |
| Compiled DTB/DTBO | ✅ Complete | 3 overlays byte-identical to EZE4 (verified with `cmp`) |
| Reproducible initramfs | ✅ Complete | minimal/ufs/usb profiles in artifacts/ |
| U11→U12 audit | ✅ Complete | reports/2026-08-23-u11-eze4-* |
| Android boot chain understood | ✅ Complete | docs/boot-chain/*, docs/debugging/earlycon-analysis.md |
| sec_debug available | ✅ Complete | docs/debugging/sec-debug-firstboot-profile.md (530 lines) |
| First boot plan | ✅ Created | docs/first-boot-experiment-plan-v2.md |
| Risks identified | ✅ Complete | reports/first-boot-risk-review.md (366 lines) |

### 1.2 What is NOT resolved

| Area | State | Blocker |
|------|--------|-----------|
| Unlock/Knox owner decision | ❌ Pending | Requires irreversible human decision |
| Actual physical hw_rev | ❌ Unknown | Cannot be determined without boot |
| Stock USB power consumption baseline | ❌ Not measured | Requires tablet powered on |
| Final runtime cmdline | ❌ Not captured | Requires ADB on stock |
| Actual LZ4 size of SEC_DEBUG profile | ❌ Not packaged | Only estimate (~0.9–1.2 MiB) |
| Rehearsed restoration procedure | ❌ Untested | Local official firmware exists but unverified path |
| Bootloader behavior on vbmeta flags=1 | ❌ Hypothesis | Only observable in Phase 1 |

---

## 2. Verdict: Conditioned NO-GO

The project **is NOT ready for first physical contact today**.

However, the gap is narrow and well defined. With 3 concrete actions (described in §5), status can transition to GO in an offline work session without hardware.

### Justification

**What prevents GO:**

1. **No measured stock baseline exists.** Without baseline data (power consumption, boot time, USB enumeration), we cannot distinguish "kernel crashes" from "bootloader rejects" or "kernel works but is invisible." The experiment would be blind.
2. **No rehearsed recovery procedure exists.** We have official firmware downloaded, but no one has verified that the Odin/Download Mode flow works for this specific unit. If something goes wrong, we do not know if we can return.
3. **Unlock decision is neither made nor documented.** Knox tripping may be irreversible. Data wipe is probable. This decision belongs to the owner and must be recorded before touching anything.
4. **Unknown hw_rev.** If the bootloader applies the wrong overlay for our physical revision, DT nodes might not match real hardware. This affects everything downstream.

**What is already resolved:**

- We know exactly which images to modify and which to leave stock.
- We have an AVB protocol in abortable phases.
- We have sec_debug infrastructure designed to capture failures.
- Risks are identified and classified.

---

## 3. Critical Missing Information

If another engineer receives this repository tomorrow, these are the gaps that would prevent reproducing the experiment:

| # | Missing Information | Where It Belongs | Impact |
|---|---------------------|------------------|--------|
| I1 | SHA256 hash of modified images to be flashed | Trial sheet in each phase | Cannot verify post-flash integrity |
| I2 | Exact instruction on generating vbmeta with flags=1 (full avbtool command) | docs/boot-chain/avb-experiment-plan.md | New engineer would not know which command to use |
| I3 | Actual LZ4 size of SEC_DEBUG initramfs | docs/debugging/sec-debug-firstboot-profile.md | Does it fit or not? Only estimates exist |
| I4 | Screenshot of Samsung unlock warning | N/A until device is available | What does the prompt say exactly? |
| I5 | Confirmation of whether Download Mode remains accessible after failed flash | reports/first-boot-risk-review.md | Escape route |
| I6 | Exact Odin/Heimdall version compatible with this bootloader | docs/06-bring-up.md or similar | Correct tool for restoration |
| I7 | List of built-in modules in U11 kernel covering first 15 stock modules.load entries | docs/debugging/sec-debug-firstboot-profile.md | Determines if stock vendor_boot is viable |

---

## 4. Recommended First Experiment Plan

### Experiment 0 — Stock Baseline

**Estimated duration:** 30 minutes
**Risk:** ZERO (read-only)

Record:
- [ ] Model/CSC/AP/bootloader confirmed via ADB
- [ ] Complete `/proc/cmdline` captured
- [ ] `/proc/device-tree/model` captured
- [ ] USB idle power consumption (mA) — inline meter
- [ ] USB power consumption during full boot — temporal pattern
- [ ] Time from power-on to lock screen
- [ ] VID/PID in normal mode vs Download Mode
- [ ] Download Mode behavior: enumeration, response, timeout
- [ ] hw_rev if visible via getprop or device-tree
- [ ] Screenshots of any warning/unlock prompt

### Experiment 1 — Kernel Marker

**Objective:** prove that U11 kernel receives control from bootloader.

**Minimal Surface:**
- Modifies: `boot.img` (U11 kernel + stock cmdline) + `vbmeta.img` (flags=1)
- Stock: `init_boot.img`, `vendor_boot.img`, `dtbo.img`

**Precondition:** Experiment 0 completed. Device unlocked. Owner decision documented.

**Sought Evidence:**
- Change in USB pattern: bootloader enumeration disappears → handoff occurred
- Change in electrical power draw: transition from flat to variable pattern
- Any console output (if earlycon functions)
- Any visual change (black screen vs persistent warning)

**Interpretation:**
- Normal boot / yellow warning → kernel executed, possibly reached userspace with stock ramdisk → SUCCESS
- Red warning / reboot loop → bootloader still blocks → investigate AVB
- Stable hang without changes → kernel crashes early → activate sec_debug (Exp 3)
- Total silence identical to before → AVB still rejects modified boot → check flags/vbmeta

### Experiment 2 — Minimal Initramfs

**Objective:** prove that kernel reaches userspace (/init).

**Surface:**
- Modifies: `boot.img` + `init_boot.img` (MINIMAL ramdisk ~674 KiB) + `vbmeta.img`
- Stock: `vendor_boot.img`, `dtbo.img`

**Initramfs Content:**
- Static BusyBox AArch64
- Script `/init`: mount proc/sys/devtmpfs, echo marker, interactive shell
- Zero modules

**Success Criterion:**
- Message `[gts9fe-init] userspace reached` on visible console, OR
- Sustained change in power consumption pattern (>100 mA fluctuating = active scheduler), OR
- USB gadget enumeration (if configfs ACM is included in future version)

**Interpretable Failure Criterion:**
- Reboot loop → panic in kernel or init → move to Exp 3
- Stable hang → possible GIC/timer/memory failure → review DT/config
- No change relative to Exp 1 → initramfs not handed over → check init_boot v4 header

### Experiment 3 — SEC_DEBUG Bring-Up

**Objective:** obtain post-mortem crash evidence using existing Samsung infrastructure.

**Surface:**
- Modifies: same set as Exp 2, but init_boot contains SEC_DEBUG ramdisk

**Extended Initramfs:**
- Base MINIMAL +
- Phase A modules (low risk): `exynos-pmu-if.ko`, `dss.ko`
- Phase B modules: `sec_debug_dprt.ko`, `sec_debug_base_early.ko`
- Load order per modules.dep
- Script `/init` listing `/sys/kernel/sec_debug/*`

**Protocol:**
1. Boot normally → verify modules load without error
2. Verify sysfs nodes present
3. Trigger deliberate crash: `echo c > /proc/sysrq-trigger`
4. After automatic reboot, read sec_debug_next region (0x91200000):
   - Via ADB in stock Android (recovery boot)
   - Via direct read if physical access exists
   - Via second boot with initramfs that reads and exports over console

**Success Signal:** non-zero data in region 0x91200000 after post-crash reboot = captured evidence.

---

## 5. Pre-Hardware Checklist

### Offline (without tablet)

- [ ] Package SEC_DEBUG initramfs and measure actual LZ4 size
- [ ] Document exact avbtool command to regenerate vbmeta flags=1
- [ ] Generate candidate boot.img with U11 kernel and calculate hash
- [ ] Generate candidate MINIMAL init_boot and calculate hash
- [ ] Verify kernel Image has correct ARM64 entry point
- [ ] Confirm list of built-in drivers in U11 covering critical stock ones
- [ ] Prepare immutable trial sheet with all hashes
- [ ] Rehearse restoration procedure in VM/emulator if possible
- [ ] Document exact tool (Odin vX.X or Heimdall vX.X) and source

### Owner

- [ ] Read and understand unlock consequences (Knox, data wipe, warranty)
- [ ] Sign/confirm unlock decision
- [ ] Confirm data backup exists if any
- [ ] Establish abort condition and timeout

### Hardware (experiment day)

- [ ] Tablet battery >80%
- [ ] Verified quality USB-C cable
- [ ] Inline USB meter connected
- [ ] Second machine ready with official firmware
- [ ] Time/power/enumeration log from minute 0
- [ ] Clear abort condition: "if X does not occur in Y minutes, STOP"

---

## 6. Risk Table

| Risk | Probability | Impact | Mitigation |
|--------|-------------|---------|------------|
| AVB rejects modified boot even unlocked | Medium | High — no progress | Phase 1 vbmeta-only probe before touching boot |
| Rollback index rises permanently | Low | Critical — permanent brick | Observed RI = 0; do not flash images with higher RI |
| Infinite bootloop after custom kernel | Medium | Medium — recoverable via Download Mode | Keep Vol- accessible; official firmware prepared |
| U11 kernel incompatible with stock vendor_boot DLKM | High | Low for M2/M3 — modules fail but boot proceeds | Built-in kernel drivers; DLKM modules only needed post-init |
| Wrong DTBO applied (hw_rev mismatch) | Low-Medium | High — probes fail silently | Capture effective DT in Exp 0; compare with expected |
| sec_debug modules crash upon loading | Medium | Medium — debug channel lost | Staged load: pmu-if+dss alone first, verify, then expand |
| No visible logs (earlycon inactive, no UART) | High | High — blind experiment | Use USB power draw as proxy + sec_debug as post-mortem |
| Device fails to recover after bad flash | Low | Critical — total brick | Local official firmware + Download Mode + verified Odin/Heimdall |
| Unlock wipes data without prior warning | Low | Low — only if important data existed | Prior backup; confirm in prompt |
| Knox efuse trips irreversibly | High (upon unlock) | Medium — loss of warranty / Samsung Pay | Documented; informed owner decision |

---

## 7. Final GO/NO-GO Criteria

### GO when ALL following conditions are met:

1. ✅ Experiment 0 (baseline) executed and data saved
2. ✅ All candidate image hashes calculated and recorded on trial sheet
3. ✅ Actual LZ4 size of SEC_DEBUG initramfs measured (not estimated)
4. ✅ Step-by-step restoration procedure documented with verified tool
5. ✅ Owner confirms in writing understanding of unlock/Knox/data wipe
6. ✅ Abort condition defined with numeric timeout
7. ✅ Second machine available with cable and loaded official firmware
8. ✅ hw_rev determined (or incorrect overlay risk accepted with justification)

### NO-GO if any of these situations exists:

1. ❌ Official firmware not available locally or corrupted
2. ❌ Tablet has unstable battery or visible physical damage
3. ❌ Owner hesitates regarding unlock
4. ❌ Any candidate image lacks verified hash
5. ❌ No documented escape route exists
6. ❌ Changing more than one variable simultaneously is proposed

---

## 8. Documentation Audit

### Can another engineer reproduce this tomorrow?

**Partially.** Technical documentation has excellent depth (DT, ABI, AVB, sec_debug audits). But the following would be missing:

1. Exact commands to generate candidate images (scripts exist but are not referenced from plan v2).
2. avbtool version and precise command for flags=1.
3. A step-by-step guide for experiment day that does not require reading 10 prior documents.
4. Connection between agent reports and plan v2 decisions (e.g. why SEC_DEBUG was selected over USB console).

### Additional Documentation Recommendations

| Priority | Suggested Document |
|-----------|-------------------|
| High | `docs/runbook-first-boot.md`: single-file operational guide for experiment day |
| High | Update `docs/hardware-observation-plan.md` (contradicts active NO-GO — Risk Reviewer C1) |
| Medium | `docs/tooling/avb-vbmeta-regeneration.md`: exact avbtool command |
| Medium | `docs/initramfs/sec-debug-size-audit.md`: real LZ4 measurement result |
| Low | Consolidate agent reports into a navigable index |

---

## Executive Summary

The project has a solid and well-documented technical foundation. Agents have produced high-quality audits. However, **NO-GO** because:

1. No stock baseline exists (we cannot interpret results without it)
2. No rehearsed recovery path exists (unacceptable risk)
3. Unlock decision is not made (legal/ethical prerequisite)
4. Actual SEC_DEBUG initramfs has not been measured (estimate ≠ fact)

With 1 offline session (package, measure, generate hashes) + 1 session with tablet powered on (baseline + unlock decision), the project can transition to **conditioned GO** for Phase 1 (vbmeta-only).

The next concrete step is: **package SEC_DEBUG initramfs locally and measure its actual LZ4 size.**
