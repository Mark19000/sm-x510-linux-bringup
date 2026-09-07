# Independent Risk Review — First Boot Preparation

Date: 2026-08-24
Target: SM-X510 Wi-Fi, physical firmware `X510XXUCEZE4` / U12 / EZE4
Current candidate: OSRC U11 kernel `X510XXSBDZB4`, Linux 5.15.180
Mode: independent risk review. Repository read-only. No scripts, code, or images were modified.

## Executive Summary

The project has a strong documentary foundation and a coherent physical gate at **NO-GO**, but the recent phase introduced three important risks:

1. **Operational contradiction between documents**: `docs/hardware-observation-plan.md` still recommends preparing `earlycon`, `ramoops`, and paths oriented toward first flashing with a more advanced tone than the current verdict of `PROJECT_STATUS.md`, `docs/12-preflight-primera-prueba.md`, and the ABI audit. Without explicitly marking it as an old document, it could be followed in error.

2. **The current plan contains an invalid `earlycon` syntax**: it proposes `earlycon=samsung,0x13800000`, but the auditable driver registers the name `exynos4210` for compatible `samsung,exynos4210-uart`. Furthermore, UART0 is `disabled`, uses USI v2 mode, and depends on prior bootloader configuration and unproven physical pins. Therefore, absence of UART cannot be interpreted as proof that the kernel failed to boot.

3. **Module signing was mischaracterized in previous reviews**: in the audited U11 tree, `CONFIG_MODULE_SIG_PROTECT=y` causes `sig_enforce` enforcement to compile as `false`. Modules lacking a valid signature are not blocked by this option; they load with a warning/taint. The true blocker remains vermagic, `MODVERSIONS` CRC, binary differences, and CFI, especially against stock U12 modules.

No guaranteed recovery path exists yet. The best available path is restoring complete official firmware from the verified local copy via Download Mode, but that procedure has not been rehearsed on this unit. Unlocking likely wipes data and may irreversibly trip the Knox Warranty Bit; exact consequences on this model and version remain unconfirmed.

While these uncertainties remain open, any premature physical attempt would convert a reversible engineering problem into an unnecessary risk of data or device loss.

## Critical Findings

### C1 — Contradiction between legacy plan and active physical gate

**Problem.**

`docs/hardware-observation-plan.md` recommends preparing:

- `earlycon=exynos4210,mmio32,0x13800000`;
- reserving a new region for `ramoops`;
- alternating experimental images;
- using USB signals/power draw to decide whether the kernel reached execution.

In contrast, the most recent documents and audits establish:

- `NO-GO` until unlocking, recovery, observability, and AVB policy are validated;
- do not add `ramoops` or new memory reservations;
- prioritize existing `sec_debug`/DSS;
- treat USB power consumption and enumeration as hypotheses to be calibrated.

Primary evidence:

- `docs/hardware-observation-plan.md`
- `reports/2026-08-23-u11-eze4-binary-abi-audit.md`
- `docs/12-preflight-primera-prueba.md`
- `reports/2026-08-24-crash-logging-audit-u11.md`
- `docs/first-boot-experiment-plan.md`

**Risk.**

An engineer reading the legacy plan first might prepare `ramoops`, enable UART console, or design a boot attempt without passing through the current safety gates.

**Classification.**

Dangerous operational hypothesis as long as the legacy document is not marked as obsolete or superseded.

**Minimal Safe Action.**

Explicitly document which parts of `hardware-observation-plan.md` remain historical and which remain valid. This is a documentation fix, not an authorization to flash.

---

### C2 — Invalid `earlycon` syntax and unproven UART channel

**Verified Fact in Source.**

In the auditable Samsung driver:

- `OF_EARLYCON_DECLARE(exynos4210, "samsung,exynos4210-uart", ...)` registers the name `exynos4210`.
- The actual UART0 node uses compatible `samsung,exynos-uart`, not the compatible registered by `OF_EARLYCON_DECLARE`.

Therefore, the variant proposed in `docs/first-boot-experiment-plan.md`:

```text
earlycon=samsung,0x13800000
```

is not the correct generic form. The form consistent with the driver would be:

```text
earlycon=exynos4210,mmio32,0x13800000
```

This was precisely the string used in `docs/hardware-observation-plan.md`, confirming a documentation regression.

**Additional Unresolved Risks.**

UART0 in stock EZE4/U12 DT:

- address `0x13800000`;
- `status = "disabled"`;
- pins `gpq0-0` and `gpq0-1`;
- property `samsung,usi-serial-v2`;
- reference to USI configuration in `sysreg_peri_usi`;
- clocks and gates dependent on the CMU.

Generic earlycon can write directly to MMIO even if the node is `disabled`, but it does not configure pinmux, USI mode, or clock gates on its own. It depends on the bootloader leaving the hardware in a usable state. Furthermore, there is no physical evidence that these pins are accessible without opening the tablet.

**Operational Conclusion.**

Even if syntax is corrected, a result with zero UART bytes will remain ambiguous. It can mean:

1. the kernel never received control;
2. the kernel died before initializing earlycon;
3. earlycon wrote correctly but the physical channel is unavailable;
4. the bootloader left UART, USI, or clocks in an unusable state.

No attempt should use "no UART" as the sole signal of pre-kernel failure.

---

### C3 — Module signing: previous risk overestimated and persistent ABI risk

**Important Correction.**

A previous review asserted that `CONFIG_MODULE_SIG_PROTECT=y` prevents loading unsigned modules under lockdown. In the auditable U11 tree, that is incorrect.

Direct evidence in `kernel.config`:

```text
CONFIG_MODULE_SIG=y
# CONFIG_MODULE_SIG_FORCE is not set
CONFIG_MODULE_SIG_PROTECT=y
```

Direct evidence in `kernel/module.c` in tree:

```c
#if defined(CONFIG_MODULE_SIG) && !defined(CONFIG_MODULE_SIG_PROTECT)
static bool sig_enforce = IS_ENABLED(CONFIG_MODULE_SIG_FORCE);
...
#else
#define sig_enforce false
#endif
```

With `CONFIG_MODULE_SIG_PROTECT=y`, enforcement of `sig_enforce` compiles as `false`. Rejection due to lack of signature does not occur through that path; modules can load with warning/taint.

**What this means.**

- Signing is currently not the primary blocker for modules built with the same U11 kernel.
- Neither is it valid to assume stock U12 modules can load: the mismatch between `5.15.180` and `5.15.189-android13-3`, `MODVERSIONS` CRCs, types under `CONFIG_CFI_CLANG=y`, and build differences remain real blockers.
- Mixing U11 kernel with U12 vendor_ramdisk remains `NO-GO`.

**Residual Risk.**

Runtime behavior may contain additional Samsung hooks. This conclusion corrects the dominant static analysis, but must be confirmed with the first actual observation of `modprobe`.

---

### C4 — Anti-rollback, Knox, and recovery treated too lightly

**Observable AVB State.**

Stock EZE4 `vbmeta.img` shows:

```text
Rollback Index: 0
Rollback Index Location: 0
Flags: 0
```

and known chained locations are:

```text
dtbo   -> Rollback Index Location 1
prism  -> Rollback Index Location 2
optics -> Rollback Index Location 3
```

With observed indices at `0`, a test vbmeta maintaining the same indices should not, by itself, raise the AVB anti-rollback floor. A failed attempt also does not raise rollback automatically: increments occur when the device accepts metadata with higher values, typically during official update.

**Samsung Unknowns Not Covered by Generic AVB.**

It is unproven whether the bootloader also enforces:

- bootloader binary counter;
- security patch date protection;
- additional RPMB storage;
- proprietary Knox validations;
- checks on `bootloader`, `ldfw`, `tzsw`, `prism`, or other signed partitions.

Stock vbmeta also exposes properties like:

```text
com.android.build.boot.os_version = '13'
com.android.build.system.os_version = '16'
com.android.build.*.security_patch = '2026-05-05'
```

If generating an experimental vbmeta, preserving indices and avoiding dropping or lowering relevant properties is a mandatory precaution until the model's actual policy is understood.

**Knox / eFuse / Unlocking.**

The repository's own documentation correctly affirms that unlocking normally wipes data and can irreversibly trip the Knox Warranty Bit. What is not confirmed is:

- whether this SM-X510 Wi-Fi permits unlocking in this region/build;
- the exact procedure on Android 16 / One UI 8.5;
- whether a mandatory waiting timer exists;
- which Knox features are permanently lost;
- how the bootloader reacts after unlock with regenerated vbmeta.

Without explicit owner consent and recorded consequences, no unlocking step is acceptable.

**Current Recovery Path.**

Complete official firmware exists locally with verified hashes, but that is not a guaranteed route. What is missing is rehearsing, in read-only or controlled conditions:

1. reproducible entry into Download Mode;
2. device identification by the host machine;
3. tool and protocol compatible with U12/EZE4;
4. complete official restoration procedure with coherent BL/AP/CSC;
5. post-restoration device validation.

Furthermore, an experimental kernel may not manage battery/charging. A long session could drain the battery precisely into a state where the device cannot enter Download Mode. This thermal/electrical risk is not sufficiently highlighted in the active plan.

**Derived Rule.**

There is no "guaranteed" recovery; there is only a probable, un-rehearsed recovery path. As long as this is the case, the first physical attempt remains blocked.

## Important Findings

### I1 — Initramfs profiles: sizes and closures not yet finalized

Measured facts show tensions between goals:

- the current USB profile does not fit in the stock `init_boot` ramdisk space;
- the SEC_DEBUG profile estimated between ~0.9 and ~1.2 MiB LZ4 has not been measured;
- short closures can omit platform dependencies;
- staged groups include modules like chipid, pinctrl, or reboot whose probe may fail visibly or even cause a reset.

This does not authorize building images yet. Before any GO, local audits must be completed:

1. full static closure per group;
2. real measurement of cpio/LZ4 in temporary directories;
3. simulation of `modprobe` order;
4. explicit decision on `pinctrl-samsung-core` and PMU/DSS dependencies.

### I2 — sec_debug is not a universal safety net

The Samsung system is valuable, but its actual reach is limited:

- DSS and handlers begin capturing after modules load and probe;
- a crash before userspace may leave nothing recoverable;
- recovering DRAM requires a second live context;
- `/dev/block/by-name/debug` exists as a DT path, but its presence, permissions, and write semantics are unproven;
- `panic_to_wdt=0` is present by default in the current analysis.

Therefore, sec_debug improves diagnostic probability, but does not turn an early crash into guaranteed evidence.

### I3 — The U11→EZE4 DT diff is solid, but not absolute

The three Wi-Fi overlays r00/r01/r04 are byte-for-byte identical between U11 and stock EZE4. That is strong evidence.

However, the base DTB semantic comparator reports incomplete status, with 14 unresolved external references and automated extraction limitations. Saying "no difference affects pre-printk" is a well-founded hypothesis, not a complete formal equivalence.

The prudent strategy remains keeping stock DTB and DTBO unless necessity is proven, rather than generalizing equivalence.

### I4 — USB/power signals are hypotheses, not calibrated predictions

Thresholds such as "under ~20 mA" or "over 100 mA sustained" do not come from measurements of this unit. Neither has been observed yet:

- actual Download Mode pattern;
- bootloader→kernel transition;
- appearance or disappearance of the ACM gadget;
- effect of an early crash on USB enumeration;
- backlight/display behavior with custom kernel.

Only after a repeatable stock baseline can the same signals be interpreted during an experimental boot.

### I5 — Partition operations, slots, and vbmeta insufficiently specified

Before any future attempt, the plan must define:

- actual active slot;
- whether one slot, both, or slot manipulation is avoided;
- exact preservation of partition size and padding;
- handling of `vendor_boot` bootconfig;
- preservation of rollback index and relevant properties in experimental vbmeta;
- explicit prohibition of touching `bootloader`, `tzsw`, `ldfw`, `prism`, `optics`, or other trust partitions.

Ambiguity here can turn a recoverable experiment into a confusing boot state.

## Minor Findings

### M1 — Legacy typo in crash logging report

`reports/2026-08-24-crash-logging-audit-u11.md` transiently mentions `ignore_logline`; the correct parameter is `ignore_loglevel`. The text itself acknowledges this, but it should be corrected before using it as an operational reference.

### M2 — Poorly justified inclusion of `sec_class`

Some proposals place it first for being Samsung infrastructure, but it was not proven to be part of the minimal hard closure. It should be included only if dependency auditing requires it.

### M3 — Old ramoops recommendation still active in legacy document

Already covered by C1, but deserves specific mention because it directly contradicts the current decision not to create new reservations.

### M4 — DWC3 Exynos state must be described accurately

The U11 `.config` shows `CONFIG_USB_DWC3_EXYNOS=y`. Some intermediate notes describe the controller as a module. For the final design, a clear distinction must be made between built-in glue, generic layers, and gadget functions.

## Critical Missing Information

Before converting the plan into a physical attempt, concrete data is missing:

1. actual state of OEM unlocking and exact unlock policy on this unit;
2. visual warning and exact text after unlock;
3. Samsung behavior after regenerated vbmeta or with verification disabled;
4. final cmdline delivered by the bootloader;
5. active slot and partition map at runtime;
6. hardware revision and DTBO actually applied;
7. physical accessibility of UART0/USI without disassembly;
8. VID/PID and enumeration timing in Download Mode;
9. calibrated stock electrical pattern;
10. charging/battery behavior under rescue kernel;
11. existence and permissions of `/dev/block/by-name/debug`;
12. actual `modprobe` response to U11 modules without valid signature;
13. additional Samsung policy on rollback/security patch/RPMB.

## Operational Recommendations

### Mandatory Gates Before Reconsidering NO-GO

1. Reconcile documentation: mark `docs/hardware-observation-plan.md` as historical or explicitly supersede it.
2. Correct all future earlycon references to the source-validatable form:

   ```text
   earlycon=exynos4210,mmio32,0x13800000
   ```

3. Record in writing that zero UART does not prove pre-kernel failure.
4. Measure actual LZ4 size of the staged MINIMAL + SEC_DEBUG profile in temporary artifacts, without generating a flashable image.
5. Validate full closures of each module group with `modules.dep` and simulated order.
6. Calibrate stock baseline: video, USB enumeration, power draw, timing, and temperature.
7. Document owner consent regarding data wipe and possible irreversible Knox loss.
8. Identify specific unlock procedure for the model/region/build before executing it.
9. Rehearse recovery path: Download Mode entry, host detection, and complete official restoration with verified hashes.
10. Define minimum battery condition, maximum session duration, and thermal stop criteria.
11. Always preserve rollback index `0` and relevant properties in any laboratory vbmeta.
12. Explicitly prohibit writes to trust partitions and downgrades.

### Interpretation Rule

No negative result should be considered conclusive as long as:

- no comparable stock baseline exists;
- unlock state and AVB policy remain unconfirmed;
- the observability channel has not been validated;
- the recovery path has not been rehearsed.

A silent boot is not sufficient information. It is an ambiguous variable until it is proven which channels function.

## Verdict

Offline preparation should continue, but first physical contact remains **NO-GO**.

The most valuable next steps are documentary and safe laboratory tasks:

1. reconcile legacy and new plans;
2. correct earlycon and its interpretation;
3. measure SEC_DEBUG initramfs;
4. calibrate stock baseline;
5. investigate and record unlock/Knox/recovery for this exact unit.

Only after closing these evidence items does discussing a minimal physical experiment make sense.
