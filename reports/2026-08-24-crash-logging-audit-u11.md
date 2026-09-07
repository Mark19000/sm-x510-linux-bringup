# Comprehensive Crash Logging Infrastructure Audit — Samsung Exynos S5E8835 U11 / SM-X510

Date: 2026-08-24
Audited artifact: `artifacts/u11/x510xxsbdzb4-u11-clang21-20260823/`
Phase: offline analysis, **no flashing**

## 1. Executive Summary

The U11 kernel already incorporates **two complete crash capture pillars**:

1. **Samsung `sec_debug`** (modules + DT + reserved region), which logs panic / reset reason / watchdog and prepares the "upload cause" for the bootloader.
2. **Upstream `pstore`/`ramoops`** compiled in (`=y`) but **without active DT node or cmdline**, meaning it currently persists nothing on its own.

Additionally, Samsung **Debug Snapshot (DSS)** exists with dedicated DRAM regions for log_kernel, wdtmsg, ITMON, etc., already declared in the base DT.

Remaining steps for first boot without UART:
- Ensure that modules `sec_debug_base_early.ko`, `debug-snapshot.ko`, and `debug-snapshot-debug-kinfo.ko` load **before** any risk point, ideally from minimal initramfs or as future built-ins.
- Decide whether to use upstream `ramoops` (new DT node) or rely solely on Samsung `sec_debug`/DSS. Initial recommendation: use DSS/sec_debug first; add ramoops only as a secondary, independent mechanism.

## 2. Detailed Inventory

### CONFIG_PSTORE / CONFIG_PSTORE_RAM

| Option | State | Comment |
|---|---|---|
| `CONFIG_PSTORE=y` | active | Base backend available. |
| `CONFIG_PSTORE_RAM=y` | active | Ramoops driver ready for use. |
| `CONFIG_PSTORE_CONSOLE=y` | active | Would persist console if backend existed. |
| `CONFIG_PSTORE_PMSG=y` | active | Userspace messages. |
| `CONFIG_PSTORE_DEFLATE_COMPRESS=y` | active | Default compression. |
| `CONFIG_PSTORE_BLK=n` | inactive | No block backend; irrelevant now. |

**Actual State:** pstore is compiled in but **has no associated DT node or cmdline parameters**. Without `ramoops.mem_address/mem_size`, the driver does nothing. It is dead capacity until deliberately activated.

### ramoops in Device Tree

- In `/tmp/u11-base.dts` (decompiled from U11 DTB), **no node appears** compatible with `"ramoops"` or `"persistentram"`, nor any reference to `ramoops.mem_address`.
- Neither does it exist in the three Wi-Fi DTBOs r00/r01/r04.

Conclusion: upstream ramoops is **compiled in but unwired**.

### reserved-memory Existing in U11 DTB

Relevant regions already present in `s5e8835.dtb`:

| Node | Physical Address | Size | Purpose |
|---|---|---|---|
| `header` | 0xFD000000 | 0x10000 | Debug Snapshot header |
| `log_kernel` | 0xFD010000 | 0x200000 | DSS kernel log |
| `log_s2d` | 0xFD210000 | 0x600000 | Scan-to-dump |
| `wdtmsg` | 0x8ADB11000 | 0x1000 | Last watchdog messages |
| `log_itmon` | 0xFFFE0000 | 0x20000 | ITMON history |
| `log_itmon_history` | 0x8ADB10000 | 0x1000 | Ditto |
| `sec_debug_next` (in DTBO) | 0x91200000 | 0x200000 | Main sec_debug GEN3 buffer |
| `seclog_mem` | 0xC3000000 | 0x80000 | exynos-seclog secure log |
| `debug_kinfo_reserved@fcfff000` | 0xFCFFF000 | 0x1000 | debug-kinfo |

These regions are **already reserved** (`no-map` where applicable) and consistent with stock firmware. There is no known conflict with normal memory as long as these exact addresses are used.

### Samsung sec_debug

State in `.config`:

```text
CONFIG_SEC_DEBUG=m
CONFIG_SEC_DEBUG_BASE=m
CONFIG_SEC_DEBUG_BASE_BUILT_IN=y
CONFIG_SEC_DEBUG_RESET_REASON=m
CONFIG_SEC_DEBUG_MEMTAB=y
CONFIG_SEC_DEBUG_AUTO_COMMENT=y
CONFIG_SEC_DEBUG_LOCKUP_INFO=y
CONFIG_SEC_DEBUG_WORKQUEUE_LOCKUP_PANIC=y
...
```

Relevant source code:

- `drivers/samsung/debug/sec_debug_base_early.c`: platform driver compatible with `"samsung,sec_debug"`. Looks for `memory-region` named `"sec_debug_next"`, maps memory as non-cacheable, cleans SDN, and exposes APIs to other modules (`secdbg_base_get_buf_base`, etc.).
- `sec_debug_base.c`: registers panic handler writing `UPLOAD_CAUSE_KERNEL_PANIC` (0xC8) or other causes to PMU via `exynos_pmu_write(SEC_DEBUG_PANIC_INFORM, ...)`.
- `sec_debug_reset_reason.c`: reads PMIC/RST_STAT registers to classify reset (WDTRESET, SWRESET, PORESET, etc.) and exposes corresponding `/proc`.

DTBOs apply nodes:

```dts
fragment@sec_debug {
    target-path = "/";
    __overlay__ {
        sec_debug {
            compatible = "samsung,sec_debug";
            status = "okay";
            memory-region = <&sec_debug_next>;
            bdev_path = "/dev/block/by-name/debug";
        };
    };
};
fragment@sec_debug_built { ... memory-region = <&sec_debug_next>; };
fragment@sec_debug_reset_reason { ... strings power_on_src/rst_stat ... };
```

and reserve region:

```dts
fragment@1 {
    target = <0xffffffff>; /* /reserved-memory */
    __overlay__ {
        sec_debug_next {
            reg = <0x00 0x91200000 0x200000>;
            no-map;
            phandle = <0x55>;
        };
    };
};
```

Built modules (present in `modules.order`):

```text
drivers/samsung/debug/sec_debug.ko
drivers/samsung/debug/sec_debug_base_early.ko
drivers/samsung/debug/sec_debug_reset_reason.ko
drivers/samsung/debug/sec_debug_extra_info.ko
... (17 sec_debug modules)
```

**Actual State:** complete infrastructure ready, but dependent on loading these modules at boot time. Currently **they do not appear in `configs/initramfs-modules.conf`** or USB config, so in a minimal boot with the current initramfs **they would not load** and sec_debug would be inactive.

### last_kmsg / watchdog reset reason

- `last_kmsg = <0x01>` is already declared in `dss` (Debug Snapshot) node of base DTB.
- `wdtmsg` reserved region at 0x8ADB11000 (4 KiB).
- `hardlockup-watchdog` compatible with `"samsung,hardlockup-watchdog"` present.
- `CONFIG_SEC_DEBUG_SOFTDOG=m`, `CONFIG_SEC_DEBUG_WATCHDOGD_FOOTPRINT=m`.
- `sec_debug_reset_reason.ko` built and ready; needs to be loaded.

All "why did it reset" support exists; only module loading is missing.

## 3. What Actually Remains to Be Added

To capture evidence automatically on first boot without UART:

1. **Load sec_debug modules from minimal initramfs**, prior to any experiment:
   - `sec_debug_base_early`
   - `sec_debug_reset_reason`
   - `sec_debug`
   - optionally `debug-snapshot-debug-kinfo`
   This requires adding them to the calculated modprobe closure in `configs/initramfs-modules.conf` (future step, not now).
2. **Verify cmdline does not disable DSS/sec_debug** (no indication that it does; confirm in `/proc/cmdline` once physical access is available).
3. **Decision on upstream ramoops**: initial recommendation is **do not add yet**. Reasons:
   - We already have two native Samsung systems (sec_debug + DSS) with memory reserved by stock firmware.
   - Adding ramoops would entail reserving another new DRAM region, risking collisions with firmware/TZ/other peripherals not 100% understood.
   - For M2/M3, sec_debug/DSS covers the exact failure case we wish to observe (panic/hang/reset).
   If ramoops is desired later, the node would be:

   ```dts
   / {
       reserved-memory {
           #address-cells = <2>;
           #size-cells = <1>;
           ranges;

           ramoops_region: ramoops_region@91400000 {
               compatible = "ramoops";
               reg = <0x00 0x91400000 0x00100000>;
               no-map;
           };
       };

       ramoops {
           compatible = "ramoops";
           memory-region = <&ramoops_region>;
           record-size = <0x20000>;
           console-size = <0x80000>;
           pmsg-size = <0x20000>;
           ecc-size = <16>;
       };
   };
   ```

   with address chosen outside all regions listed above. Address 0x91400000 is adjacent to `sec_debug_next` (which ends at 0x91400000). It must be validated against full physical map before use.

## 4. Risks of Incorrect Memory Reservation

Incorrectly reserving DRAM can cause:

1. **Collision with TrustZone / EL3 firmware.** Upper regions (0xFC000000–0xFFFFFFFF) are filled with secure zones. An error here can trigger a synchronous abort in EL3, causing an instant reboot without logs.
2. **Corruption of coprocessor firmware buffers** (CP/GNSS/NPU/Audio), which already have their own reserved regions. Overlapping can cause firmware to write into our buffer or vice versa, generating false panics.
3. **Conflict with CMA / kernel memblock.** Marking `no-map` on a zone Linux already dynamically allocated yields silent corruption or BUG_ON.
4. **Inconsistency between bootloader and kernel.** If the bootloader expects a certain address to remain free (e.g. to pass reset reason data), and we reserve it for another purpose, original evidence is lost.

Practical rule for this phase:

- **Do not create any new reservation.** Use solely addresses already present in stock DTB/DTBO.
- If adding ramoops in the future, choose an address after obtaining the actual physical map (`/proc/iomem`, `memblock_dump_all`) on a live boot, never guessed offline.

## 5. Operational Conclusion

Samsung crash logging infrastructure in U11 is **far more complete than expected**: sec_debug, Debug Snapshot, reset reason, and watchdog footprint are compiled in and have memory pre-reserved by firmware.

The only real gap for first boot without UART is **ensuring these modules load in minimal initramfs**. That change belongs to the next phase, alongside physical verification that `/dev/block/by-name/debug` is accessible and PMU accepts upload cause writes.
