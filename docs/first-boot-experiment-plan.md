# First Boot Experiment Plan

> **Errata 2026-09-05:** `--flags 1` signifies `HASHTREE_DISABLED`, not disable-verification. `VERIFICATION_DISABLED` is `flags=2`; Samsung acceptance of flags 2/3 remains UNKNOWN. This earlier plan is not an operational authority; see `docs/boot-chain/minimum-first-boot-image-set.md`.

Consolidation date: 2026-08-24
Scope: Samsung Galaxy Tab S9 FE SM-X510, U12/EZE4 variant
Document mode: audit preparation. Does not authorize flashing or modify existing artifacts.

## Current State

Assertions are classified as **CONFIRMED EVIDENCE** when derived from verified static inspection or artifacts present in the repository, and as **HYPOTHESIS** when requiring physical validation.

### Boot Chain and AVB

**CONFIRMED EVIDENCE**

- `boot.img`, `init_boot.img`, `vendor_boot.img`, and `dtbo.img` have embedded footers and vbmeta signed with `SHA256_RSA4096`. Static verification with `avbtool` succeeded.
- Root vbmeta has `flags=0` and global rollback index `0`.
- Root vbmeta contains hash descriptors for `boot`, `init_boot`, `vendor_boot`, and `dtbo`; it also chains the vbmeta structs of `dtbo`, `prism`, and `optics`.
- `init_boot.img` contains no kernel. It contains the generic GKI ramdisk compressed with legacy LZ4.
- `vendor_boot.img` contains vendor ramdisk LZ4, bootconfig, and a compressed DTB with proprietary Samsung format.
- Under LOCKED bootloader, changing any partition covered by a hash invalidates the signed descriptor. In that state, custom kernel must not be considered executable.

**HYPOTHESIS**

- Samsung bootloader implements the expected AOSP policy in UNLOCKED state and tolerates a regenerated vbmeta with verification disabled.
- No relevant additional Samsung checks exist beyond AVB, Knox/RPMB, or device-specific policies.
- Bootloader selects the DTBO overlay by hardware revision and composes final command-line parameters not fully observable in stock images.

### ABI Between U11 Kernel and U12/EZE4 Vendor

**CONFIRMED EVIDENCE**

- Built U11 kernel reports vermagic `5.15.180 SMP preempt mod_unload modversions aarch64`.
- Stock inventories point to a `5.15.189-android13-3` environment; no direct vermagic compatibility exists.
- Both sides declare `CONFIG_MODVERSIONS=y`. The U11 tree has `Module.symvers`, but no comparable stock kernel CRC table nor sufficient stock binary modules exist to demonstrate ABI compatibility.
- Mixing stock U12 vendor_ramdisk with the U11 kernel is NO-GO until CRC/symbol evidence is available.
- In the current U11 build, early critical drivers `EXYNOS_CHIPID_V2`, S5E8835 clock, MCT v3, watchdog, and Samsung pinctrl are modular, not built-in. Base GIC is built-in.
- `CONFIG_MODULE_SIG_PROTECT=y`, but `CONFIG_MODULE_SIG_FORCE` is not active and `CONFIG_SECURITY_LOCKDOWN_LSM` is not active in the audited U11 build. Therefore, unconditional signature rejection is not the correct conclusion; the primary blocker is vermagic/CRC/CFI.

**HYPOTHESIS**

- Recompiling the U11 kernel with chipid, clocks, timer, pinctrl, PMU, and basic reboot support built-in may permit reaching `/init` without relying on stock vendor ramdisk ABI closure.
- CFI and binary differences may cause late failures even if symbols match.

### Device Tree and Pre-Printk Boot

**CONFIRMED EVIDENCE**

- `sec_debug_next` is defined in overlays, not in base DTB: physical address `0x91200000`, size `0x200000`, `no-map` property.
- Hardwired Samsung/DSS regions exist, including `log_kernel` at `0xFD010000`, `wdtmsg` at `0x8ADB11000`, ITMON history, and additional debug regions.
- PSCI is version 1.0 with SMC conduit. All eight CPUs use PSCI as boot/power-down method.
- Documented global interrupt controller is GIC-400/GICv2 at `0x12B00000`. No ITS.
- ARMv8 arch_timer declares `clock-frequency = <26000000>` and stock line enforces `clocksource=arch_sys_counter`.
- Declared main oscillator is 52 MHz and central CMU uses compatible `samsung,s5e8835-clock`.
- Known diff between U11 and EZE4 is limited to four properties associated with EMS, MFC, and SCSC/Wi-Fi. None belong to memory/PSCI/GIC/timer/clocks.
- Observable stock cmdline uses `console=ram` and includes no `earlycon=`. `CONFIG_SERIAL_EARLYCON=y` and `CONFIG_SERIAL_SAMSUNG=y` are built into U11.

**HYPOTHESIS**

- The four U11→EZE4 diffs are irrelevant prior to first printk. This conclusion is sound, but semantic diff analysis does not eliminate all residual uncertainty.
- Without an effective `earlycon=` parameter or other early Samsung mechanism, a live kernel may remain silent even if it passes basic initialization.
- Bootloader normally leaves UART/clock gates in a usable state, but there is no physical proof on this device.

### Samsung Observability and sec_debug

**CONFIRMED EVIDENCE**

- `sec_debug`, DSS, and `reset_reason` are represented by DT nodes and modules built in the U11 tree.
- Current USB/initramfs profile does not load the full set needed to activate sec_debug/DSS.
- Post-mortem recovery requires a secondary context: USB ACM shell, functional stock Android, accessible recovery/download mode, or subsequent storage/physical region readout.

**HYPOTHESIS**

- A reduced 12-module profile can activate sec_debug and DSS without reserving new memory or modifying DT.
- After a subsequent crash, `sec_debug_next`, `log_kernel`, `wdtmsg`, or `/proc/last_kmsg` will retain sufficient evidence to diagnose first boot.

Detailed source: [`docs/debugging/sec-debug-analysis.md`](../debugging/sec-debug-analysis.md).

### Initramfs

**CONFIRMED EVIDENCE**

- A functional MINIMAL profile of ~674 KiB LZ4 exists, compared to ~2.49 MiB stock ramdisk in `init_boot`.
- Current DEBUG/USB profile contains 45 modules and occupies ~2.9 MiB LZ4, thus exceeding stock size.
- Proposed closure for sec_debug has 12 unique modules and is under 800 KiB raw. Its final LZ4 size has not yet been measured.

**HYPOTHESIS**

- Staged sec_debug profile fits in `init_boot` alongside base busybox.
- Current USB closure can be trimmed by eliminating non-mandatory dependencies, but pruning requires incremental experimentation.

## Uncertainties

| ID | Uncertainty | Operational Impact |
|---|---|---|
| U1 | Actual bootloader state: OEM unlock enabled, UNLOCKED confirmed, and Samsung post-unlock policy. | Determines whether custom kernel can receive control. Absolute prerequisite. |
| U2 | Exact early console parameter and physical UART/USB state at handoff. | Without early signal, distinguishing AVB failure from pre-driver failure relies entirely on current draw, resets, and post-mortem. |
| U3 | Actual bootloader behavior with alternative vbmeta having `VERIFICATION_DISABLED` (`flags=2`). | Defines whether minimal experiment reaches first kernel instruction. |
| U4 | Exact runtime dependency closure of sec_debug/DSS on EZE4 DTB+overlay. | Short list may fail due to missing indirect dependency; broad list increases early panic risk. |
| U5 | Actual need for pinctrl-samsung-core and other platform drivers for sec_debug/DSS probes. | May cause silent probe failures even if `.ko` modules load. |
| U6 | Actual LZ4 size of staged sec_debug profile. | Conditions final packaging of `init_boot` or custom vendor ramdisk. |
| U7 | Final cmdline composed by bootloader and guaranteed application of correct overlay. | May alter observability and `sec_debug_next` reservation. |
| U8 | Hardware-specific USB and power draw signals on this unit. | Diagnostic matrix is experimental framework, not validated prediction. |
| U9 | CFI/binary compatibility beyond CRC and vermagic. | Risk of late failure difficult to interpret without logs. |

## Risks

### Critical

1. **C1 — Incomplete boot chain experiment:** Replacing only `boot.img` and vbmeta is insufficient. With U11 kernel, feeding incompatible stock vendor_ramdisk must also be avoided. Realistic minimal scope affects at least `boot.img`, `vendor_boot.img`, and/or `init_boot.img`, plus vbmeta.
2. **C2 — Absence of proven early console:** Stock cmdline does not enable `earlycon`. This is the single largest real-time observability blocker and must be treated as part of design, not an afterthought.
3. **C3 — Unknown bootloader state:** Without confirming UNLOCKED and its actual effect on this model, no physical attempt satisfies informational safety criteria.

### Important

1. **I1 — Signature overestimated, ABI underestimated:** Primary issue is CRC/vermagic/CFI, not automatic signature rejection in the audited U11 build.
2. **I2 — Monolithic sec_debug load hazardous:** Loading all 12 modules at once can lose evidence if a driver with `panic()` in probe fails. Loading must be staged.
3. **I3 — Hidden platform dependencies:** Short static closure may omit modules needed for actual probes.
4. **I4 — Unvalidated signals:** USB/current matrix is structured hypothesis and must first be calibrated against stock firmware.
5. **I5 — pinctrl contradiction:** ABI report identifies pinctrl as modular blocker while sec_debug draft did not include it. Must be resolved with closure audit prior to final packaging.
6. **I6 — Reserved regions and firmware:** Using fixed addresses without knowing live map may confuse driver failure with collision or invalid access.

### Minor

1. Correct inherited typographical references, such as `ignore_loglevel`, when transcribing operational commands.
2. Avoid including `sec_class` without justifying concrete necessity in final closure.
3. Do not present U11→EZE4 diff as absolute when derived from partially automated comparison.

## Minimal Experiment

This is the target design. The current session generates no images or final scripts. Blockers listed at the end must be resolved before physical attempt.

### Single Objective of First Boot

Determine whether U11 kernel receives control from bootloader and reaches minimal userspace, maximizing probability of obtaining post-mortem evidence via existing Samsung infrastructure.

Having USB, display, full storage, or standard Linux is not an objective for the first attempt.

### Mandatory Preconditions

1. Visually confirm OEM unlocking is enabled and device is in UNLOCKED state.
2. Record visible boot warning and stable access to Download Mode on stock firmware.
3. Measure stock baseline with zero modifications:
   - USB current during boot;
   - approximate timing of visible phases;
   - observable USB enumerations;
   - backlight/screen behavior;
   - total time to Android or reset.
4. Preserve intact copies of all stock images and corresponding hashes.

### Scope of Images

The experiment requires a coherent set, not a single replacement:

| Image | Target Content | Rationale |
|---|---|---|
| `boot.img` | Reproducible U11 kernel. Preferably with chipid, S5E8835 clocks, MCT v3, PMU, pinctrl core, and basic reboot support built-in. | Reduces critical dependency on stock vendor ramdisk and attempts to reach `/init`. |
| `vendor_boot.img` | Minimal or controlled empty custom vendor ramdisk; preserved stock EZE4 DTB; controlled bootconfig. | Eliminates incompatible U12 vendor_ramdisk without discarding base/overlay DT delivered by bootloader. |
| `init_boot.img` | MINIMAL profile + staged, measured, self-contained sec_debug package. | Provides userspace markers and activates post-mortem observability. |
| `vbmeta.img` | Audit generation with verification disabled or test key, per policy confirmed post-unlock. | Enables modified images to be accepted under UNLOCKED. |

`dtbo.img` must remain stock unless subsequent findings demonstrate incompatibility. Unnecessarily changing DT would contaminate results.

### Staged sec_debug Initramfs

Use existing MINIMAL profile as reference, creating a new experimental profile without modifying current scripts.

Proposed boot phase inside `/init`:

1. Mount `proc`, `sysfs`, and `devtmpfs`.
2. Emit phase markers across all available outputs.
3. Load low-risk Group A:
   - `exynos-pmu-if`;
   - `dss`;
   - `sec_debug_dprt`;
   - `sec_debug_base_early`.
4. Short pause, log success/failure, and check created sysfs/procs.
5. Only if Group A causes no reboot, load Group B:
   - `exynos-chipid_v2`;
   - `pinctrl-samsung-core` if final closure confirms;
   - `sec_debug_mode`;
   - `sec_debug_extra_info`.
6. Only if Group B survives, load Group C:
   - `sec_debug_reset_reason`;
   - `exynos-reboot`;
   - `hardlockup-watchdog`;
   - `sec_reboot`;
   - `sec_debug`.
7. Dump detected state to console/buffer and enter rescue shell or controlled wait.

Each step must record module name, return code, and observed sysfs paths before continuing.

### Experimental Command Line

Run two local audit variants before deciding physical package:

**Variant A — maximum compatibility:**

```text
console=ram clocksource=arch_sys_counter ignore_loglevel
```

**Variant B — early console probe:**

```text
console=ram clocksource=arch_sys_counter ignore_loglevel earlycon=samsung,0x13800000
```

The address `0x13800000` corresponds to the UART node documented in the audited DT, but the exact format accepted by the U11 driver must be confirmed in source/build before flashing. If unvalidated, first physical test must use Variant A and rely on sec_debug/power draw.

Add custom parameters with stable prefix, e.g. `gts9fe.first_boot=1`, to identify experiment in runtime/post-mortem.

### Observation Protocol

During first boot:

1. Record continuous video of screen/backlight.
2. Capture USB traffic/enumeration with timestamped Linux host log.
3. Measure USB current with resolution sufficient to distinguish coarse phases.
4. Define maximum timeout without signal and return to Download Mode using documented physical key combination.
5. After each reset, attempt recovery via available secondary context: stock Android, recovery, download tools, or subsequent persistent region readout.
6. Always record relative timestamps from cable insertion or power button press.

## Expected Signals

All signals are **EXPERIMENTAL HYPOTHESES** until calibrated on this specific hardware.

| Observed Signal | Probable Interpretation | Confidence | Diagnostic Action |
|---|---|---|---|
| Orange/red warning persists and never clears. | Failure/rejection in boot chain; kernel likely does not receive control. | High conceptually, medium in Samsung. | Verify UNLOCKED state, vbmeta, and descriptors. |
| Download Mode remains consistently accessible. | Healthy bootloader independent of kernel. | High. | Repeat with logging and change one variable at a time. |
| Bootloader UI appears and disappears; nothing follows. | Handoff occurred; very early failure or live silent kernel. | Medium. | Compare power draw and test Variant A/B cmdline. |
| Stable ACM gadget appears. | Kernel, UDC/PHY, and userspace reached USB configuration. | Medium-high if USB profile present; low in minimal sec_debug profile. | Open shell and extract logs/loaded modules. |
| USB device appears briefly and disappears. | Kernel progressed toward gadget and crashed/reset. | Medium-low. | Prioritize sec_debug/DSS recovery and correlate power draw. |
| Flat power draw matching bootloader. | Likely no effective handoff. | Hypothesis. | Stock baseline mandatory to compare pattern. |
| Spike followed by drop/reset. | Early execution followed by panic/watchdog/memory fault. | Hypothesis. | Recover reset_reason, wdtmsg, and last_kmsg. |
| Cyclic reset with stable period. | Automatic panic, watchdog, or deterministic early crash. | Medium. | Vary cmdline/initramfs and measure period shift. |
| Backlight abruptly turns on and off. | Display phase reached or reset; ambiguous without logs. | Low. | Do not use as sole signal. |
| No symptom changes between variants. | Possible pre-kernel rejection or inactive console/driver. | Medium. | Review boot chain before continuing kernel debugging. |

## Result Interpretation

```text
Does device enter Download Mode?
├─ NO
│  └─ Halt. Bootloader/power/storage failure or incorrect protocol.
│     Action: recover with official key combination and document brick level.
│
└─ YES
   Does stock baseline boot reproduce known pattern?
   ├─ NO
   │  └─ Resolve measurement environment or device state before testing kernel.
   │
   └─ YES
      Does UNLOCKED warning appear with experimental set?
      ├─ NO
      │  └─ Boot chain/vbmeta/Samsung policy failure.
      │     Action: audit vbmeta, slots, and unlock policy; do not blame kernel yet.
      │
      └─ YES
         Is there a distinct transition after warning?
         ├─ NO
         │  └─ Kernel did not receive control or halted in initial instructions.
         │     Action: verify entry/load addresses, delivered DTB, and EL1/EL2 state.
         │
         └─ YES
            Does power draw/enumeration show new phase?
            ├─ NO
            │  └─ Pre-printk failure or silent kernel.
            │     Action: recover sec_debug/DSS; repeat altering only earlycon/cmdline.
            │
            ├─ BRIEF PHASE + RESET
            │  └─ Kernel ran and failed prior to userspace/stable gadget.
            │     Action: classify with wdtmsg/reset_reason/last_kmsg and review timers/GIC/DT.
            │
            ├─ STABLE ACM GADGET
            │  └─ High partial success: userspace/USB controller reached.
            │     Action: extract dmesg, cmdline, iomem, modules, and sec_debug state.
            │
            └─ RESET AFTER INITRAMFS MARKERS
               └─ Userspace reached; failure during phase/module probe.
                  Action: isolate last loaded group and validate closure/pinctrl/DT.
```

General rule: a negative result is considered conclusive only if stock baseline, unlock state, used images, and recovery method were recorded.

## Next Decision After First Attempt

### Result 1 — Evident Boot Chain Rejection

Priority:

1. Audit actual Samsung policy in UNLOCKED.
2. Test known-valid test vbmeta under this policy.
3. Confirm active slot and which image bootloader actually reads.

Do not continue tuning kernel until a marker image can receive control.

### Result 2 — Handoff but Total Silence

Priority:

1. Recover any sec_debug/DSS/reset_reason content.
2. Repeat with Variant A/B cmdline, changing only that field.
3. Audit exact `earlycon` format and UART clock state in U11 kernel.
4. Consider minimal additional instrumentation only if post-mortem yields no data.

### Result 3 — Early Reset Prior to Userspace

Priority:

1. Classify reset reason/watchdog.
2. Validate applied DTB/DTBO and live reserved regions.
3. Reduce variables: kernel without optional initramfs, then MINIMAL, then sec_debug.
4. Convert critical modular drivers to built-in if `.ko` modules prevent early phase.

### Result 4 — Userspace Reached

Priority:

1. Extract full evidence: `dmesg`, `cmdline`, `/proc/iomem`, sysfs, loaded modules, and errors.
2. Confirm whether sec_debug became active and where it exposes data.
3. Progress from MINIMAL to full sec_debug profile incrementally.
4. Only then tackle USB ACM as permanent channel.

### Result 5 — Module Loading Failure

Priority:

1. Separate format/vermagic, symbol/CRC, signature, probe, or dependency error.
2. Reconstruct closure with full `modules.dep` and test smaller groups.
3. Correct pinctrl contradiction with actual probe evidence.

## Pending Blockers

These items prevent proceeding to physical first attempt today:

1. **Confirm and record UNLOCKED/OEM unlock state**, including visible warning and Download Mode access.
2. **Resolve early console mechanism**: validate exact `earlycon` syntax in U11 driver and determine whether useful Samsung alternative exists.
3. **Define full three-piece composition**: final kernel/config, custom vendor_boot with stock DT, and custom `init_boot`. Do not use stock U12 vendor_ramdisk with U11 kernel.
4. **sec_debug/DSS closure audit**: include actual platform dependencies, resolve pinctrl, and eliminate unverified assumptions.
5. **Actual LZ4 size measurement** of MINIMAL + staged sec_debug profile, without generating flashable image yet.
6. **Calibrate stock baseline** for power draw, USB, and screen with repeatable method and timestamps.
7. **Validate vbmeta policy post-unlock** on this model before assuming `flags=2/3` is sufficient or allowed; `flags=1` only disables hashtree.
8. **Prepare safe recovery procedure** for any outcome: timeout, Download Mode entry, and hash-verified stock restore.
9. **Document experiment log template** with separated hypotheses, variables, observations, and conclusion.

## References

- [`docs/debugging/sec-debug-analysis.md`](debugging/sec-debug-analysis.md) — sec_debug, DSS, DT, and recovery audit.
- [`reports/2026-08-24-crash-logging-audit-u11.md`](../reports/2026-08-24-crash-logging-audit-u11.md) — prior logging and crash recovery audit.
- [`docs/hardware-observation-plan.md`](hardware-observation-plan.md) — prior hardware observation plan.

Consolidated session verbal reports:

- Agent 2 — AVB/boot chain and USB diagnostic matrix.
- Agent 3 — U11/U12 ABI, critical modules, and signature.
- Agent 4 — reserved-memory, PSCI, GIC, timers, clocks, and DT diffs.
- Agent 5 — MINIMAL, DEBUG/USB, and SEC_DEBUG initramfs profiles.
- Agent 6/9 — independent review and critical C1/C2 and I1–I5 corrections.
