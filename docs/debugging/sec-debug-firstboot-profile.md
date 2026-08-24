# Samsung sec_debug first-boot profile — SM-X510 U12/EZE4

Date: 2026-08-24  
Mode: read-only design audit. This document does not build an image, change scripts, flash hardware, or request a boot.  
Input artifact: `artifacts/u11/x510xxsbdzb4-u11-clang21-20260823/` and stock EZE4 extraction artifacts.

## 1. Executive summary

The first activation target should be **DSS + sec_debug base**, not the complete Samsung debug module set. The smallest useful closure is four modules:

1. `exynos-pmu-if.ko`
2. `dss.ko`
3. `sec_debug_dprt.ko`
4. `sec_debug_base_early.ko`

This activates persistent kernel-log capture and the early sec_debug base without pulling in reboot, watchdog, scheduler, ACPM, EMS, USB-notify, or other platform closures that can fail independently.

The second stage should add reset-reason support. Its minimal closure is six modules: the four above plus `sec_debug_extra_info.ko` and `sec_debug_reset_reason.ko`.

For a first boot, load stages synchronously, record each result, continue on failure, and only then decide whether to add the medium/full stages. The initramfs is preferable to stock `vendor_dlkm` for this experiment because it avoids depending on ABI-incompatible U12 modules and gives deterministic control of the exact module set.

No `sec_debug=1` command-line switch is required by this repository evidence. DT nodes plus successful driver probes are the observed activation mechanism.

## 2. Evidence found

### 2.1 Complete U11 sec_debug/DSS-related module inventory

All paths below are relative to:

```text
artifacts/u11/x510xxsbdzb4-u11-clang21-20260823/modules-installed/modules-root/lib/modules/5.15.180/
```

| Module | Exact path | Raw size |
|---|---|---:|
| `exynos-pmu-if.ko` | `kernel/drivers/soc/samsung/exynos-pmu-if.ko` | 21,745 B |
| `dss.ko` | `kernel/drivers/soc/samsung/exynos/debug/dss.ko` | 450,145 B |
| `ehld.ko` | `kernel/drivers/soc/samsung/exynos/debug/ehld.ko` | 44,632 B |
| `hardlockup-watchdog.ko` | `kernel/drivers/soc/samsung/exynos/debug/hardlockup-watchdog.ko` | 30,097 B |
| `sec_debug_base_early.ko` | `kernel/drivers/samsung/debug/sec_debug_base_early.ko` | 46,929 B |
| `sec_debug_dprm.ko` | `kernel/drivers/samsung/debug/sec_debug_dprm.ko` | 16,560 B |
| `sec_debug_dprt.ko` | `kernel/drivers/samsung/debug/sec_debug_dprt.ko` | 39,665 B |
| `sec_debug_dtask.ko` | `kernel/drivers/samsung/debug/sec_debug_dtask.ko` | 14,024 B |
| `sec_debug_extra_info.ko` | `kernel/drivers/samsung/debug/sec_debug_extra_info.ko` | 104,264 B |
| `sec_debug_hardlockup_info.ko` | `kernel/drivers/samsung/debug/sec_debug_hardlockup_info.ko` | 17,864 B |
| `sec_debug_hw_param.ko` | `kernel/drivers/samsung/debug/sec_debug_hw_param.ko` | 21,720 B |
| `sec_debug_mode.ko` | `kernel/drivers/samsung/debug/sec_debug_mode.ko` | 17,552 B |
| `sec_debug_reset_reason.ko` | `kernel/drivers/samsung/debug/sec_debug_reset_reason.ko` | 25,600 B |
| `sec_debug_sched_info.ko` | `kernel/drivers/samsung/debug/sec_debug_sched_info.ko` | 17,288 B |
| `sec_debug_sched_report.ko` | `kernel/drivers/samsung/debug/sec_debug_sched_report.ko` | 13,976 B |
| `sec_debug_slab_info.ko` | `kernel/drivers/samsung/debug/sec_debug_slab_info.ko` | 18,321 B |
| `sec_debug_softdog.ko` | `kernel/drivers/samsung/debug/sec_debug_softdog.ko` | 28,146 B |
| `sec_debug_stacktrace.ko` | `kernel/drivers/samsung/debug/sec_debug_stacktrace.ko` | 14,809 B |
| `sec_debug_wdd_info.ko` | `kernel/drivers/samsung/debug/sec_debug_wdd_info.ko` | 18,824 B |
| `sec_debug.ko` | `kernel/drivers/samsung/debug/sec_debug.ko` | 39,240 B |
| `exynos-chipid_v2.ko` | `kernel/drivers/soc/samsung/exynos/exynos-chipid_v2.ko` | 27,337 B |
| `exynos-reboot.ko` | `kernel/drivers/power/reset/exynos/exynos-reboot.ko` | 26,097 B |
| `sec_reboot.ko` | `kernel/drivers/samsung/sec_reboot.ko` | 22,584 B |
| `s3c2410_wdt.ko` | `kernel/drivers/watchdog/s3c2410_wdt.ko` | 26,872 B |

Stock also contains `sec_debug_test.ko`; it is absent from this U11 inventory. It is deliberately excluded from all first-boot stages.

### 2.2 Transitive dependencies from U11 `modules.dep`

Closures were derived from the installed `modules.dep`, including every unique dependency but excluding optional `modules.softdep` entries. Sizes are raw `.ko` bytes.

#### Stage A — low-risk observability

Request: `sec_debug_base_early`

```text
kernel/drivers/samsung/debug/sec_debug_base_early.ko
kernel/drivers/samsung/debug/sec_debug_dprt.ko
kernel/drivers/soc/samsung/exynos-pmu-if.ko
kernel/drivers/soc/samsung/exynos/debug/dss.ko
```

Closure: 4 modules; raw payload 558,484 bytes.

#### Stage B — reset reason

Request: `sec_debug_reset_reason`

```text
kernel/drivers/samsung/debug/sec_debug_reset_reason.ko
kernel/drivers/samsung/debug/sec_debug_extra_info.ko
kernel/drivers/samsung/debug/sec_debug_base_early.ko
kernel/drivers/samsung/debug/sec_debug_dprt.ko
kernel/drivers/soc/samsung/exynos-pmu-if.ko
kernel/drivers/soc/samsung/exynos/debug/dss.ko
```

Closure: 6 modules; raw payload 674,748 bytes.

#### Stage C — main sec_debug core (medium risk)

Request: `sec_debug`

```text
kernel/drivers/samsung/debug/sec_debug.ko
kernel/drivers/samsung/debug/sec_debug_base_early.ko
kernel/drivers/samsung/debug/sec_debug_dprt.ko
kernel/drivers/samsung/debug/sec_debug_mode.ko
kernel/drivers/samsung/sec_reboot.ko
kernel/drivers/power/reset/exynos/exynos-reboot.ko
kernel/drivers/soc/samsung/exynos-pmu-if.ko
kernel/drivers/soc/samsung/exynos/debug/dss.ko
kernel/drivers/soc/samsung/exynos/debug/hardlockup-watchdog.ko
kernel/drivers/soc/samsung/exynos/exynos-chipid_v2.ko
```

Closure: 10 modules; raw payload 758,039 bytes.

`exynos-chipid_v2` and `exynos-reboot` are included because they are hard dependencies. Their probes can fail independently; therefore Stage C must not run before Stages A/B have been recorded.

#### Optional collectors with large or risky closures

| Requested module | Closure | Raw payload | First-boot assessment |
|---|---:|---:|---|
| `sec_debug_wdd_info` | 6 | 654,110 B | Requires `s3c2410_wdt`; defer until watchdog behavior is intentionally under test. |
| `sec_debug_dtask` | 3 | 503,684 B | Small direct closure; optional after Stage B. |
| `sec_debug_sched_report` | 3 | 511,708 B | Low platform risk; optional after Stage B. |
| `sec_debug_sched_info` | 4 | 523,868 B | Adds stacktrace collector; optional after Stage B. |
| `sec_debug_stacktrace` | 1 | 14,809 B | Independent; safe candidate for later incremental testing. |
| `sec_debug_slab_info` | 1 | 18,321 B | Registers panic notifier; test separately after core evidence exists. |
| `sec_debug_softdog` | 2 | 42,955 B | Soft-watchdog diagnostic; not first-boot. |
| `sec_debug_dprm` | 5 | 579,494 B | Depends on Stage A base; defer. |
| `sec_debug_hw_param` | 17 | 2,676,930 B | Pulls ACPM/PM-QoS/platform chain; defer. |
| `ehld` | 25 | 4,488,186 B | Pulls pinctrl/MUIC/USB notify/EMS/ACPM chain; do not use in minimum profile. |
| `sec_debug_hardlockup_info` | 26 | 4,512,323 B | Superset of EHLD closure; do not use in minimum profile. |

### 2.3 Stock ordering evidence

EZE4 `artifacts/stock/vendor-ramdisk-audit/modules.load` contains this relevant order:

```text
01 exynos-chipid_v2.ko
02 exynos-reboot.ko
03 sec_debug_base_early.ko
07 sec_debug_mode.ko
24 dss.ko
28 hardlockup-watchdog.ko
48 exynos-pmu-if.ko
205 sec_reboot.ko
216 sec_debug.ko
217 sec_debug_test.ko
218 sec_debug_dprm.ko
219 sec_debug_dprt.ko
220 sec_debug_extra_info.ko
221 sec_debug_hw_param.ko
222 sec_debug_reset_reason.ko
223 sec_debug_wdd_info.ko
224 sec_debug_dtask.ko
225 sec_debug_softdog.ko
226 sec_debug_sched_info.ko
227 sec_debug_stacktrace.ko
228 sec_debug_hardlockup_info.ko
229 sec_debug_sched_report.ko
230 sec_debug_slab_info.ko
```

This proves stock loads debug support from the vendor DLKM ramdisk, while also showing that its literal order cannot be copied into an isolated rescue initramfs: `modules.dep` requires `dss` before `sec_debug_base_early` in the reduced U11 closure.

### 2.4 Device Tree wiring

Confirmed in all three stock overlays and recovery DT variants:

```dts
sec_debug_next {
    reg = <0x00 0x91200000 0x200000>;
    no-map;
};

sec_debug {
    compatible = "samsung,sec_debug";
    status = "okay";
    memory-region = <&sec_debug_next>;
    bdev_path = "/dev/block/by-name/debug";
};

sec_debug_built {
    compatible = "samsung,sec_debug_built";
    status = "okay";
    memory-region = <&sec_debug_next>;
};
```

The vendor-boot base DTS wires DSS as follows:

```dts
dss {
    compatible = "samsung,debug-snapshot";
    panic_to_wdt = <0x00>;
    last_kmsg = <0x01>;
    hold-key = <0x72>;
    trigger-key = <0x74>;
    memory-region = <&header>, <&log_kernel>, <&log_s2d>,
                    <&log_first>, <&log_arrdumpreset>,
                    <&log_platform>, <&log_kevents>,
                    <&log_backtrace>, <&log_kevents_small>, <&wdtmsg>;
};
```

Key fixed regions remain:

| Region | Address | Size |
|---|---:|---:|
| `header` | `0xFD000000` | 64 KiB |
| `log_kernel` | `0xFD010000` | 2 MiB |
| `wdtmsg` | `0x8ADB11000` | 4 KiB |
| `sec_debug_next` | `0x91200000` | 2 MiB |

The stock chosen node contains no `sec_debug=` parameter:

```text
console=ram printk.devkmsg=on arm64.nopauth arm64.nomte nokaslr kasan=off
clocksource=arch_sys_counter clk_ignore_unused
firmware_class.path=/vendor/firmware rcupdate.rcu_expedited=1
swiotlb=noforce loop.max_part=7 cgroup.memory=nokmem
```

### 2.5 Module parameters

Only these relevant parameters were found in the inspected `.ko` metadata:

| Module | Parameter | Meaning from module metadata |
|---|---|---|
| `sec_debug_reset_reason` | `reset_reason:int` | Overrides/receives reset reason from command line. |
| `sec_debug_reset_reason` | `pwrsrc:long` | Receives power-source state from command line. |
| `sec_debug_reset_reason` | `rstcnt_rs:long` | Referenced by cmdline parser strings. |
| `s3c2410_wdt` | `tmr_margin`, `tmr_atboot`, `nowayout`, `soft_noboot` | Watchdog behavior; irrelevant to Stage A/B. |

A fourth reset-reason string (`rstcnt_rs`) appears in code/metadata even though the concise `parm` table found locally exposed two typed parameters. Its exact handling remains source-level/runtime unknown.

## 3. What this means

- DSS is the earliest valuable component because it owns kernel-log capture and `/proc/last_kmsg`.
- `sec_debug_base_early` depends directly on DSS, so loading DSS first both satisfies dependencies and creates a checkpoint before enabling sec_debug base.
- Reset reason is a separate six-module capability and should be validated independently from panic hooks/upload behavior.
- The full `sec_debug.ko` core introduces reboot/chip-id/hardlockup dependencies and belongs in Stage C, not in the first observable checkpoint.
- Large EHLD/hardlockup closures contradict the “minimum” objective and increase the number of unrelated subsystems that can mask the actual failure.

## 4. Initramfs versus vendor_dlkm

| Criterion | Rescue initramfs | Stock-style vendor_dlkm/vendor ramdisk |
|---|---|---|
| Earliest availability | Before pivot-root | Later, after DLKM mount logic |
| Module ABI control | Exactly matches booted U11 Image if populated from U11 artifact tree | U12 stock modules target `5.15.189-android13-3`; cross-loading is unproven/high risk |
| Failure isolation | Only explicitly requested modules are attempted | Hundreds of modules may be processed depending on userspace policy |
| Space pressure | Must fit modified initramfs budget; Stage B adds only ~116 KiB over Stage A | Avoids initramfs growth but imports much larger compatibility risk |
| Recovery value | Best for custom-kernel first boot | Better only when running the matched stock ecosystem |

**Decision for first boot:** put Stage A/B modules and their dependency index in the rescue initramfs. Keep vendor DLKM untouched and absent from the decision path until ABI compatibility has separate proof.

## 5. Risks

1. **Probe failure can still be silent.** Without earlycon/serial output, module-load success must be inferred from later sysfs/proc interfaces or post-mortem memory.
2. **Stage A is not total observability.** If execution dies before module load, DSS will have produced no new capture.
3. **DTBO application is assumed, not runtime-proven.** `sec_debug_next` lives in overlays; wrong overlay selection could remove the reservation.
4. **Reserved-region access may fail despite correct addresses.** Firmware/TrustZone permissions are unknown at EL1.
5. **`bdev_path=/dev/block/by-name/debug` is not a guarantee.** Device existence, partition naming, and write semantics require live verification.
6. **Signature behavior needs runtime confirmation.** `CONFIG_MODULE_SIG_PROTECT=y` with `CONFIG_MODULE_SIG_FORCE` unset suggests taint rather than unconditional rejection, but lockdown state and Samsung-specific enforcement are not yet observed.
7. **CFI and MODVERSIONS remain ABI constraints.** Every loaded module must come from exactly the same reproducible U11 build as the running Image.
8. **Panic-to-watchdog is disabled in stock DT.** A panic may stop rather than automatically reboot unless another mechanism intervenes.
9. **Stage C can create new resets.** Chip-id, reboot, and watchdog-adjacent drivers probe hardware directly; their failures must not destroy Stage A/B results.

## 6. Hypotheses

### Confirmed by repository evidence

- The listed files, sizes, direct dependencies, transitive closures, DT properties, and stock order exist in audited artifacts.
- Stock DT enables `last_kmsg=1`, sets `panic_to_wdt=0`, and maps DSS regions.
- No stock chosen/bootconfig parameter named `sec_debug=1` was observed.

### Engineering hypotheses requiring runtime proof

- H1: Loading `exynos-pmu-if`, `dss`, `sec_debug_dprt`, then `sec_debug_base_early` produces working DSS and base-early probes.
- H2: After one subsequent reboot/crash, `/proc/last_kmsg` exposes the prior kernel ring captured through `log_kernel`.
- H3: Loading Stage B creates `/proc/reset_reason`, and its content changes predictably across software reset, watchdog reset, and forced power removal.
- H4: Stage C completes without changing reset behavior and registers the main sec_debug panic path.
- H5: `/dev/block/by-name/debug` exists and can later be used as a persistence sink without writing it during the first experiment.
- H6: Unmatched-stock signature enforcement permits self-built U11 modules with taint, provided CRC/vermagic match.

Each hypothesis is falsifiable independently; no fix should be applied based solely on plausibility.

## 7. Recommended staged `/init` design

The following is a design contract, not a patch. Existing scripts must not be changed by this audit.

Requirements:

1. Mount `proc`, `sysfs`, and `devtmpfs`.
2. Open a durable marker/log file in tmpfs if available; duplicate markers to console when present.
3. Load each stage with explicit module names/files, not a wildcard.
4. Continue after every individual failure and save exit status/message.
5. Inspect expected interfaces immediately after each stage.
6. Enter a rescue/idle state after collecting evidence.
7. Never write to `/dev/block/by-name/debug` in the first experiment.

### Phase 0 — preflight

Record:

```sh
cat /proc/cmdline
cat /proc/device-tree/model 2>/dev/null
find /proc/device-tree/reserved-memory -maxdepth 2 -type d -print
cat /proc/iomem
ls -l /dev/block/by-name/debug
```

Expected uncertainty: device-tree paths may differ under the mounted representation; list first, never assume.

### Phase 1 — low-risk Stage A

Load in dependency-safe order:

```text
exynos-pmu-if
dss
sec_debug_dprt
sec_debug_base_early
```

Suggested synchronous invocation pattern:

```sh
for module in exynos-pmu-if dss sec_debug_dprt sec_debug_base_early; do
    echo "[stage-A] loading $module"
    modprobe "$module" 2>&1
    echo "[stage-A] $module status=$?"
done
```

Inspect:

```text
/sys/kernel/debug or /sys/kernel/dss (actual root unknown)
/proc/dss_kmsg
/proc/iomem entries for header/log_kernel/wdtmsg
dmesg markers emitted by DSS/base-early probes
```

Pass criteria:

- All four modules return zero.
- DSS reports/maps its reserved regions or exposes a proc/sysfs interface.
- No immediate reboot occurs.

If any Stage A module fails, stop staged expansion and preserve the error plus current memory/reset state.

### Phase 2 — Stage B

Load:

```text
sec_debug_extra_info
sec_debug_reset_reason
```

Then inspect:

```text
/proc/reset_reason
/proc/pwrsrc
/proc/reset_rwc
/proc/store_lastkmsg
/sys/module/sec_debug_reset_reason/parameters/*
```

Do not pass reset parameters on the first run. Let the driver read PMU/firmware-provided state so the observation reflects the real previous reset.

Pass criteria:

- Both modules return zero.
- At least `/proc/reset_reason` exists.
- Values are recorded verbatim, even if classified as unknown.

### Phase 3 — Stage C, only after A/B pass

Load:

```text
exynos-chipid_v2
exynos-reboot
hardlockup-watchdog
sec_reboot
sec_debug_mode
sec_debug
```

`modprobe sec_debug` resolves the hard closure, but listing the components makes partial-failure diagnosis explicit.

Inspect:

```text
/sys/kernel/sec_debug/* (exact hierarchy unknown)
/sys/module/sec_debug/parameters/*
/proc/sys/kernel/* related to panic/tainted state
cat /proc/sys/kernel/tainted
dmesg tail
```

Pass criteria:

- All Stage C modules load.
- Main sec_debug sysfs appears.
- Taint/status values are recorded before and after.

Failure interpretation:

| Observation | Most specific conclusion supported |
|---|---|
| Stage A fails at `exynos-pmu-if` | Platform/PMU interface failed before debug activation. |
| Stage A fails at `dss` | DT region mapping/probe failed; sec_debug base cannot be meaningful yet. |
| Stage A fails at base-early | Base dependency/probe issue; DSS may already be active. Preserve that fact. |
| Stage B fails at extra-info | Extra-info ABI/binding failed; reset-reason may still be possible only if requested alone in a later controlled run. |
| Stage B fails at reset-reason | PMU/reset classification unavailable; DSS evidence remains valid. |
| Stage C fails at chipid/reboot | Hardware identity/reset binding failed; do not proceed to full core. |
| Stage C fails at `sec_debug` | Panic-hook/upload registration failed; earlier observability remains usable. |

### Post-crash retrieval phase

After any controlled crash/reset, boot the same known-good rescue environment, load only Stage B, and collect:

```text
/proc/last_kmsg
/proc/dss_kmsg
/proc/reset_reason
/proc/pwrsrc
/proc/reset_rwc
/proc/store_lastkmsg
hexdump of /sys/module/sec_debug_reset_reason/parameters/*
```

Copy outputs to external storage/network only through an already-working host channel. Do not write the Samsung debug block partition during this phase.

## 8. Recommended experiments

### Experiment S0 — static packaging rehearsal (no flash)

Create a disposable local staging calculation outside tracked scripts:

1. Copy only Stage B files into a temporary root.
2. Generate/regenerate dependency metadata using the same tooling in a scratch directory.
3. Build cpio/LZ4 only to measure size.
4. Delete the scratch result.

Decision gate: measured compressed Stage-B payload plus existing minimal initramfs must fit the intended image budget.

### Experiment S1 — Stage A live checkpoint

Boot the approved custom rescue image once with Stage A only.

Signals:

- Module return codes.
- Presence/absence of DSS proc interfaces.
- Whether device survives to userspace.

Outcome:

- PASS → run Stage B next.
- FAIL → capture available logs/consumption/reset state; do not enable Stage B/C.

### Experiment S2 — Stage B live checkpoint

Add reset-reason support without overriding parameters.

Signals:

- Existence/content of `/proc/reset_reason` family.
- Any new taint/probe errors.

Outcome:

- PASS → proceed to controlled reboot/retrieval test.
- FAIL → keep Stage A as the observability baseline.

### Experiment S3 — persistence round-trip

From a passed Stage B environment, trigger the least destructive agreed reset method, re-enter rescue, and read `/proc/last_kmsg` plus reset fields.

Interpretation matrix:

| Result | Meaning |
|---|---|
| Last KMSG contains prior ring; reset reason is coherent | DSS + reset pipeline works end-to-end. |
| Last KMSG empty; reset reason coherent | Reset classifier works, but DSS did not retain/copy prior log. |
| Last KMSG present; reset reason unknown/missing | DSS works; PMU/reset classification needs investigation. |
| Neither present | Failure occurred before probes, DTBO/reservation was absent, or retrieval environment differs. |

### Experiment S4 — Stage C core

Run only after S3 succeeds. Record whether `sec_debug.ko` registers panic hooks and whether a late controlled panic changes the next reset reason/upload cause.

Do not combine S4 with first introduction of watchdog, USB, display, or storage changes.

## 9. Proposed documentation

- Preserve this file as the operational profile for sec_debug bring-up.
- Add a companion measurement note after S0 containing exact compressed sizes and checksums; do not overwrite this analysis.
- After each physical run, append a dated incident record with command outputs, module statuses, reset reason, last-KMSG length/hash, and photographs/consumption observations where relevant.
- Update `docs/first-boot-experiment-plan-v2.md` only after reviewer consolidation; this profile should remain evidence-first.
- Correct the typo `ignore_logline` to `ignore_loglevel` in the earlier analysis only as part of an explicitly reviewed documentation patch.

## 10. Evidence classification

### Confirmed facts

- Module inventory, exact paths, and raw sizes.
- Direct and transitive hard-dependency closures from installed metadata.
- DT compatibles, addresses, sizes, `no-map`, `bdev_path`, and DSS options.
- Stock load positions and absence of `sec_debug=1` in visible stock boot arguments.
- Relevant module parameters found in binary metadata.

### Inferences

- Four-module Stage A is the smallest useful activation sequence.
- Six-module Stage B is the smallest reset-reason sequence.
- Literal stock order is unsuitable for an isolated U11 rescue closure.
- Signature enforcement likely permits tainted load because force mode is unset, subject to runtime confirmation.

### Required experiments

- Verify actual sysfs/proc roots created by each driver.
- Confirm DTBO selection and runtime presence of `sec_debug_next` via `/proc/iomem` or device-tree inspection.
- Prove module signature/vermagic behavior on target.
- Measure packaged Stage B size.
- Validate last-KMSG/reset round-trip and only then extend to the full core.
