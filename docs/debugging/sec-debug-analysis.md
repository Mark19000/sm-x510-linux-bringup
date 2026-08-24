# Samsung sec_debug analysis — SM-X510 U12/EZE4

Date: 2026-08-24  
Scope: read-only repository audit. No image was generated and no runtime change is proposed.  
Baseline artifact: `artifacts/u11/x510xxsbdzb4-u11-clang21-20260823/`

## 1. Architecture

Samsung boot debugging has two cooperating layers:

- **sec_debug** records crash metadata in the `sec_debug_next` reserved region, classifies reset causes from PMIC/PMU state, registers panic/die hooks, and can set a bootloader upload cause through PMU.
- **Debug Snapshot (DSS)** continuously captures kernel/platform logs and structured events into separate reserved DRAM regions. It also exposes `/proc/last_kmsg` on the following boot.

In this source tree:

| Component | Config | DT wiring | Runtime path |
|---|---|---|---|
| DSS core | `CONFIG_DEBUG_SNAPSHOT=m` | `/dss`, compatible `"samsung,debug-snapshot"` | `dss.ko` |
| DSS kernel log | enabled by DSS + `last_kmsg = 1` | `log_kernel` memory region | ring buffer copied to `/proc/last_kmsg` after reboot |
| sec_debug early base | `CONFIG_SEC_DEBUG_BASE=m`, `CONFIG_SEC_DEBUG_BASE_BUILT_IN=y` | compatible `"samsung,sec_debug"` | `sec_debug_base_early.ko`; probes at `core_initcall()` |
| panic notifier | `CONFIG_SEC_DEBUG_BASE=m` | uses PMU interface | `sec_debug.ko`; registers at `subsys_initcall()` |
| reset reason | `CONFIG_SEC_DEBUG_RESET_REASON=m` | compatible `"samsung,sec_debug_reset_reason"` | `sec_debug_reset_reason.ko` |
| watchdog info | `CONFIG_SEC_DEBUG_WDD_INFO=m` | depends on platform watchdog driver | `sec_debug_wdd_info.ko` |
| ITMON | `CONFIG_EXYNOS_ITMON_V2=m` | `/exynos-itmon` | `exynos-itmon-v2.ko` |

The panic handler writes one of these upload causes to PMU (`drivers/samsung/debug/sec_debug_base.c`): `0xC8` for generic kernel panic, `0x2F` user fault, `0x66` hard reset, `0x22` forced upload, `0x74` user-forced upload, or `0xCC` CP fatal error. This is a firmware-visible signal intended to influence recovery/upload mode.

## 2. Required modules and dependencies

The U11 build installs 282 modules; 16 are under `drivers/samsung/debug`. The stock EZE4 `vendor_boot` inventory contains a separate `sec_debug_test.ko`, hence its count is 17 Samsung debug modules. The current U11 build does not include that deliberate crash-injection test module.

### Direct dependencies observed in U11 `modules.dep`

| Module | Direct dependencies |
|---|---|
| `dss.ko` | `exynos-pmu-if` |
| `hardlockup-watchdog.ko` | none |
| `ehld.ko` | large transitive closure including `hardlockup-watchdog`, DSS, sec_debug base/extra, scheduler and PMU modules |
| `sec_debug_dprt.ko` | none |
| `sec_debug_stacktrace.ko` | none |
| `sec_debug_slab_info.ko` | none |
| `sec_debug_base_early.ko` | `sec_debug_dprt`, `dss`, `exynos-pmu-if` |
| `sec_debug_mode.ko` | `dss`, `exynos-pmu-if` |
| `sec_debug_dprm.ko` | `sec_debug_base_early` closure |
| `sec_debug_extra_info.ko` | `sec_debug_base_early` closure |
| `sec_debug_reset_reason.ko` | `sec_debug_extra_info` closure |
| `sec_debug_wdd_info.ko` | `s3c2410_wdt` plus base-early closure |
| `sec_debug_dtask.ko` | DSS closure |
| `sec_debug_softdog.ko` | `sec_debug_stacktrace` |
| `sec_debug_sched_info.ko` | `sec_debug_stacktrace` plus DSS closure |
| `sec_debug_sched_report.ko` | DSS closure |
| `sec_debug_hardlockup_info.ko` | `ehld`, `hardlockup-watchdog`, extra-info and DSS closures |
| `sec_debug_hw_param.ko` | `cmupmucal`, `exynos-adv-tracer`, extra-info and platform closures |
| `sec_debug.ko` | `sec_reboot`, `hardlockup-watchdog`, `sec_debug_mode`, `sec_debug_base_early`, `sec_debug_dprt`, `exynos-reboot`, `exynos-chipid_v2`, DSS and PMU closures |

### Stock EZE4 load order

The stock `vendor_boot` fragment named `dlkm` contains 281 module entries. Its relevant order is:

1. `exynos-chipid_v2.ko`
2. `exynos-reboot.ko`
3. `sec_debug_base_early.ko`
4. clock/timer/watchdog infrastructure
5. `s3c2410_wdt.ko`
6. `sec_debug_mode.ko`
7. scheduler/storage/core platform modules
8. `dss.ko`
9. `debug-snapshot-debug-kinfo.ko`, ITMON, tracer, EHLD
10. later platform drivers
11. `sec_reboot.ko`, crash-key/hard-reset helpers
12. all remaining `sec_debug*.ko` modules near positions 216–230

This proves that stock Android loads sec_debug support from the vendor DLKM ramdisk, not only from Android userspace.

### Current U11 rescue initramfs

Observed list `/etc/gts9fe-modules` contains only:

```text
phy-exynos-usbdrd-super
dwc3-exynos-usb
```

The staged USB profile contains several debug `.ko` files, but modprobe is driven only by the two entries above. Therefore no sec_debug module is requested by the current minimal boot. This is the central first-boot observability gap.

### Initramfs versus vendor DLKM

Both locations are technically viable if the matching module tree is present:

- **Initramfs**: earliest possible load; best for a rescue kernel whose vendor ramdisk may not match ABI or may not contain a complete DLKM payload.
- **Stock-style vendor DLKM**: matches Android boot flow and avoids enlarging the rescue ramdisk, but it cannot help before vendor ramdisk extraction/mounting succeeds.

For a first Linux bring-up where the failure may occur during early userspace, the evidence favors explicit early loading of at least the minimum sec_debug/DSS chain in the initramfs.

A minimum functional request should include `sec_debug_base_early`, `dss`, and `sec_debug_reset_reason`; modprobe will resolve their closures. A fuller diagnostic set adds `sec_debug`, `hardlockup-watchdog`, `ehld`, ITMON, `sec_debug_wdd_info` and the optional task/scheduler collectors. The exact minimum must be validated by experiment because some collectors depend on platform modules not currently listed in the rescue config.

## 3. Reserved-memory regions

Values below were read directly from decompiled stock EZE4/U12 DTB and DTBO artifacts.

### Base DTB / Debug Snapshot

| Node | Physical address | Size | Purpose |
|---|---:|---:|---|
| `reserved-memory/debug_snapshot/header` | `0xFD000000` | `0x10000` (64 KiB) | DSS header |
| `reserved-memory/debug_snapshot/log_kernel` | `0xFD010000` | `0x200000` (2 MiB) | kernel printk ring used by `last_kmsg` |
| `reserved-memory/debug_snapshot/log_s2d` | `0xFD210000` | `0x600000` (6 MiB) | scan-to-dump |
| `reserved-memory/log_backtrace` | dynamic in `0x80000000..0xE7FFFFFF` range | `0x2000` | backtrace |
| `reserved-memory/log_itmon_history` | `0x8ADB10000` | `0x1000` | ITMON history |
| `reserved-memory/wdtmsg` | `0x8ADB11000` | `0x1000` (4 KiB) | watchdog message |
| `reserved-memory/log_itmon` | `0xFFFE0000` | `0x20000` | ITMON data |
| `reserved-memory/debug_kinfo_reserved@fcfff000` | `0xFCFFF000` | `0x1000` | debug-kinfo |
| `reserved-memory/seclog_mem` | `0xC3000000` | `0x80000` | Exynos secure log |
| `reserved-memory/sec_rdx_bootdev` | `0x8B0000000` | `0x7E00000` | RAM-backed boot-device dump staging; marked `no-ship` |

The DSS node references header, kernel log, S2D, first log, array-dump-reset, platform, kevents, backtrace and `wdtmsg`. It sets `last_kmsg = <1>` and `panic_to_wdt = <0>`.

### DTBO-applied sec_debug region

| Node | Physical address | Size | Attribute |
|---|---:|---:|---|
| `reserved-memory/sec_debug_next` | `0x91200000` | `0x200000` (2 MiB) | `no-map` |

Overlay fragments add:

```text
/sec_debug:
  compatible = "samsung,sec_debug"
  status = "okay"
  memory-region = <&sec_debug_next>
  bdev_path = "/dev/block/by-name/debug"

/sec_debug_built:
  compatible = "samsung,sec_debug_built"
  status = "okay"
  memory-region = <&sec_debug_next>

/sec_debug_reset_reason:
  compatible = "samsung,sec_debug_reset_reason"
  power_off_src / power_on_src / rst_stat string tables
```

`bdev_path` names `/dev/block/by-name/debug`, but device availability and writable access have not been observed in this repository.

## 4. Cmdline requirements

Confirmed facts:

- `debug` is an upstream `early_param`; it increases console verbosity but is not required to initialize sec_debug.
- `sec_debug_reset_reason` exposes three module parameters: `reset_reason`, `pwrsrc`, and `rstcnt_rs`.
- `sec_dump_sink.c` contains `early_param("sec_debug.upload_count", ...)`, although the corresponding call site is disabled by `#if 0` in the audited source.
- `sec_debug_mode` exposes `force_upload`; `sec_debug_hw_param` exposes `dram_size` and `dram_info`; `sec_debug_extra_info` exposes `rr_pwrsrc`.
- No `sec_debug=1` parameter exists in the audited downstream source.
- No DT node or cmdline parameter activates upstream ramoops despite `CONFIG_PSTORE_RAM=y`.

Inference: normal initialization appears driven primarily by DT-compatible nodes and module loading, not by a global `sec_debug=1` switch. Bootloader-provided values such as reset reason may populate the module parameters above, but the exact stock cmdline has not been captured here.

Experiment necessary: collect `/proc/cmdline` and module parameter values from a live stock EZE4 boot before assuming any parameter is mandatory.

For observation-only Linux experiments, useful non-sec_debug flags would be `loglevel=8 ignore_logline=...` only if corrected to `ignore_loglevel`; however, they do not substitute for sec_debug persistence. `panic_timeout=0` is an experiment-control hypothesis that must be tested separately because it changes reboot behavior.

## 5. Post-crash recovery without UART

Recovery requires a second execution context: either a working Linux rescue shell over USB ACM, fastboot/ADB access to stock Android, or physical extraction/readback. Without any second context, DRAM contents cannot be retrieved reliably.

### Preferred sequence after reboot into rescue shell

1. Mount `procfs`.
2. Preserve text immediately:
   - `cat /proc/reset_reason`
   - `cat /proc/pwrsrc`
   - `cat /proc/extra`
   - `cat /proc/last_kmsg`
   - `cat /proc/dss_kmsg`
   - `cat /proc/first_kmsg`, when exposed
   - `cat /proc/sec_log`
3. Record DSS layout and state:
   - `dmesg`
   - `cat /proc/iomem`
   - inspect DSS sysfs attributes, especially `dss_panic_to_wdt`, `dss_logging_item` and DPM mode.
4. Only then attempt block-device export/copy of `/dev/block/by-name/debug` if it exists and is readable. Do not write it during evidence collection.
5. Hash every captured file and preserve timestamps.

If USB ACM reaches userspace, copy these outputs through `/dev/ttyGS0` before doing anything else. If stock Android boots instead, use ADB read-only collection and avoid writing debug partitions.

### Expected interpretation

| Observation | Meaning |
|---|---|
| `/proc/reset_reason` reports `CLUSTER*_WDTRESET` | watchdog reset reached PMU/RST_STAT classification |
| `/proc/last_kmsg` ends with a panic trace | kernel progressed far enough for DSS logging and panic path |
| `/proc/last_kmsg` is empty/truncated very early | failure occurred before DSS probe or before meaningful logging |
| reset reason changes between panic and forced power-off | helps distinguish software panic from manual/power intervention |
| upload cause enters download/recovery behavior | PMU write path and bootloader reaction worked, even without log visibility |

Watchdog-specific evidence comes from three sources: reset-reason bit decoding, DSS `wdtmsg`, and `sec_debug_wdd_info` last ping metadata. The latter requires the watchdog ping notifier and collector modules actually to run.

## 6. Known limitations

1. **No retrieval path from total pre-userspace failure.** sec_debug and DSS preserve data, but something must later read DRAM, a block partition, or expose USB.
2. **Current initramfs does not request the modules.** Files being present in the stage directory is not activation.
3. **Early module-load window is not guaranteed.** `core_initcall()` runs only after module load; a crash before that point leaves no new sec_debug record.
4. **DSS itself is modular.** Until `dss.ko` probes, persistent kernel-log capture is not active.
5. **`panic_to_wdt=0` means panic-to-watchdog conversion is disabled by DT.** Runtime sysfs can change it, but changing behavior belongs to a controlled experiment, not default evidence collection.
6. **Block-device persistence is unproven.** `/dev/block/by-name/debug` is configured as a path; existence, partition table, permissions and write semantics remain unverified.
7. **Bootloader upload-mode behavior is not proven for custom kernels.** The source writes known cause codes, but reaction under unlocked/modified AVB state needs observation.
8. **Upstream ramoops remains inactive.** `CONFIG_PSTORE_RAM=y` alone creates no backend.
9. **Module ABI/version mismatch can silently remove diagnostics.** All modules must come from exactly the same kernel build as the booted Image.
10. **DRAM forensic extraction is out of scope here** and must be treated as a separate hardware procedure.

## 7. Evidence classification

### Confirmed repository facts

- Exact configs, DT addresses/sizes, compatibles, module files, dependency strings and stock load order listed above.
- DSS copies prior kernel ring content into allocated memory and creates `/proc/last_kmsg`, `/proc/dss_kmsg`, and conditionally `/proc/first_kmsg`.
- Reset-reason driver creates `/proc/reset_reason`, `/proc/store_lastkmsg`, `/proc/extra`, `/proc/pwrsrc`, and `/proc/reset_rwc`.
- Panic handler writes PMU cause codes.
- Current rescue module lists contain only the two USB entries.
- Stock EZE4 loads sec_debug modules from a vendor DLKM ramdisk containing 281 entries.
- Upstream pstore/ramoops is compiled but has no DT or cmdline backend in the audited artifacts.

### Reasonable engineering inferences

- sec_debug is designed to work without `sec_debug=1`; DT plus loaded modules are the primary activation mechanism.
- Loading the minimum DSS/base/reset chain in the rescue initramfs is more robust for first-boot diagnosis than depending on an unmatched or absent vendor DLKM.
- Stock module ordering reflects intended dependency precedence and should guide future experiment design.
- Missing `/proc/last_kmsg` after a failed boot suggests either DSS did not probe, the kernel did not reach module load, or no second context was available to read it.

These inferences do not replace runtime validation.

### Experiments still required

1. Capture stock `/proc/cmdline`, module parameters and `/sys/firmware/devicetree/base` from a healthy EZE4 boot.
2. In a controlled rescue-kernel experiment, load only `sec_debug_base_early` and verify its probe message and DSS dependency resolution.
3. Load `dss.ko`, confirm the printed physical/virtual memory layout matches the DT regions above, then generate a deliberate late panic only after preserving a rollback path.
4. Reboot into the same rescue environment and verify `/proc/last_kmsg`, `/proc/reset_reason` and DSS sysfs contents.
5. Verify presence and read-only accessibility of `/dev/block/by-name/debug`; defer any write test until the preceding steps pass.
6. Compare reset reasons after (a) deliberate panic, (b) long hang/watchdog timeout, and (c) forced power removal, recording each result separately.

No fix should be applied until these observations distinguish “mechanism absent” from “mechanism active but unread.”
