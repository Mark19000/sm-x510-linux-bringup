# Hardware Identity SM-X510 U12/EZE4

Audit date: 2026-08-24. Mode: read-only over local artifacts and existing documentation. Neither ADB was executed nor was the unit touched.

## Executive Summary

- **Confirmed:** Target unit is `SM-X510` Wi-Fi with firmware `X510XXUCEZE4`, CSC `EUX` / `X510OXMCEZE4`, Android 16, One UI 8.5, security patch `2026-05-05`, and bootloader binary/revision recorded as U12.
- **Unconfirmed:** Exact numerical `hw_rev` value of the physical board and, consequently, which entry from `dtbo.img` the bootloader selected or would select.
- DTBO table defines three Wi-Fi ranges: overlay index `0` for revision `0`, index `1` for revisions `1–3`, and index `2`, labeled `r04`, for revisions `4–32`.
- No local evidence permits inferring physical `hw_rev` from firmware name `EZE4`, from `REV00` in the AP, or from AVB/DTBO metadata. Assuming `r04` would be an unproven decision.
- The correct method remains reading the effective tree or properties exposed by firmware on stock boot; if not possible, the project must continue treating revision as a blocking unknown for any test dependent on BOM/pinctrl/display/sensors.

## Evidence Found

### Identity Confirmed by Configuration and Firmware

| Field | Value | Evidence |
|---|---|---|
| Model | `SM-X510` | `configs/target-sm-x510.env`; `scripts/collect-device.sh` validates `ro.product.model` |
| Variant | Wi-Fi | Target config and DTBO table `GTS9FEWIFI_EUR_OPEN` |
| Android platform/build | `BP4A.251205.006` | `configs/target-sm-x510.env`; unit documentation |
| AP/PDA version | `X510XXUCEZE4` | `configs/target-sm-x510.env`; `artifacts/stock/firmware-metadata.txt` |
| CSC / multi-CSC | `EUX` / `OXM` (`X510OXMCEZE4`) | `configs/target-sm-x510.env`; documented SAOMC string |
| Bootloader binary revision | `U12` | Field `TARGET_BOOTLOADER_REVISION=12` and project documentation |
| Preserved firmware | Full ZIP with SHA-256 `45a45087...01d375` | `configs/target-sm-x510.env`; `docs/10-x510-eze4-unit.md` |
| AP entry | `AP_..._MQB109790656_REV00_user_low_ship...tar.md5` | `artifacts/stock/firmware-metadata.txt` |

### EZE4 Overlays Table

The manifest in `artifacts/stock/dt/overlays/manifest.json` records three entries. Standard `id` and `rev` fields are zero; relevant discrimination is in `custom[]`. Decompiled DTS files confirm their meaning:

| DTBO Index | File | Custom Fields | Declared Range in DTS |
|---:|---|---|---|
| `0` | `overlay-00-id-00000000-rev-00000000.dtbo` | `[0,0,0,0]` | `dtbo-hw_rev = <0x00>`, `dtbo-hw_rev_end = <0x00>` |
| `1` | `overlay-01-id-00000000-rev-00000000.dtbo` | `[1,3,0,0]` | `dtbo-hw_rev = <0x01>`, `dtbo-hw_rev_end = <0x03>` |
| `2` | `overlay-02-id-00000000-rev-00000000.dtbo` | `[4,32,0,0]` | `dtbo-hw_rev = <0x04>`, `dtbo-hw_rev_end = <0x20>` |

Base DTB in `vendor_boot` declares:

```text
dtb-hw_rev = <0x00>
dtb-hw_rev_end = <0xff>
```

This broad range describes base DT acceptance, not physical revision. The root node also contains `model = "Samsung GTS9FEWIFI EUR OPEN board based on S5E8835"` after applying the corresponding overlay.

### `chosen` Node

The `chosen` node extracted from EZE4 contains:

```text
bootargs = "console=ram printk.devkmsg=on arm64.nopauth arm64.nomte nokaslr kasan=off clocksource=arch_sys_counter clk_ignore_unused firmware_class.path=/vendor/firmware rcupdate.rcu_expedited=1 swiotlb=noforce loop.max_part=7 cgroup.memory=nokmem";
linux,initrd-start = <0x84000000>;
linux,initrd-end   = <0x8cffffff>;
```

In static DTS, no identity property like `hw-rev`, physical `board-id`, or `stdout-path` appears. Values `board-id = <0x10>` and `board-rev = <0x00>` exist inside another node in the base tree, but no local evidence exists that they represent dynamic `hw_rev` used to select DTBO nor that the bootloader updates them.

`vendor_boot.img` also includes 28 bytes of bootconfig with `buildtime_bootconfig=enable`. Its observed content provides no board identity.

### Data That Do Not Identify the Physical Board

| Field or Label | What It Identifies | Why It Does Not Resolve `hw_rev` |
|---|---|---|
| `X510XXUCEZE4` | Samsung AP/CSC release | Software label; no local mapping to PCB revision |
| `EZE4` | AP release suffix | Not demonstrably equivalent to a DTBO revision number |
| `U12` | Bootloader revision/binary recorded by owner | Different taxonomy from DTBO `hw_rev` range |
| `REV00` from AP tar | AP package label | No evidence linking it to `hw_rev` on this unit |
| AVB rollback indexes (`dtbo=1`, `prism=2`, `optics=3`) | AVB anti-rollback policy | Logical per-partition indexes, not physical revisions |
| Model/region in settings or `getprop` | Product and CSC | May not directly expose DTBO selection |

## What It Means

1. The project possesses a product and firmware identity sufficiently sound to select packages and compare stock images.
2. Fine-grained physical identity is incomplete: knowing SM-X510/U12/EZE4 does not prove which of the three effective trees the tablet uses.
3. DTBO selection belongs to the bootloader. The `custom[]` ranges represent a very strong candidate table, but not a direct device observation.
4. Overlay `r04` covers a broad interval (`4–32`) precisely because it aggregates several possible revisions. This simplifies firmware packaging, but does not prove `r04` is the actual value of this unit.

## Risks

- **High risk:** Building or validating an initramfs/kernel against `r04` when the unit is actually `r00` or `r01–r03`. Documented differences affect pinctrl, magnetometer calibration, and display/touch fragments.
- **Medium risk:** Conflating `U12`, `EZE4`, `REV00`, or rollback index with `hw_rev`, introducing a false assumption into downstream reports.
- **Medium risk:** Using unverified properties such as `board-rev = <0x00>` without knowing what produces them or if firmware updates them.
- **Low risk for early boot, high for peripherals:** Base DT and CPU/GIC/PSCI/timers blocks may be identical across overlays, while display, charging, sensors, or GPIO remain misdescribed.

## Hypotheses

| Hypothesis | Status | Required Test |
|---|---|---|
| `hw_rev ∈ {0..32}` and selection is by range `[start,end]` of `custom[0],custom[1]` | Strong, consistent with DTS/manifest, but unproven against real bootloader | Compare `/proc/device-tree` or `/sys/firmware/fdt` with each overlay |
| This specific unit applies index `2` / `r04` | Unconfirmed | Read effective tree in stock |
| `TARGET_BOOTLOADER_REVISION=12` implies `hw_rev >= 4` | Unconfirmed | Correlate observed `hw_rev` with bootloader on real units |
| `getprop` exposes some property derived from `hw_rev` | Possible, dependent on Samsung/Android build | Run read-only inventory on stock and inspect all properties |
| Bootloader appends `androidboot.*` parameters with revision | Possible | Capture `/proc/cmdline` and `dmesg` in stock |

## Recommended Experiments (Read-Only)

### Experiment H1 — ADB Inventory in Stock Android

Precondition: Android boots normally and ADB authorized.

1. Execute existing script `./scripts/collect-device.sh`; do not modify it.
2. Additionally retain, in a new report directory:
   - `adb shell getprop`
   - `adb shell cat /proc/cmdline`
   - `adb exec-out cat /sys/firmware/fdt`
   - `adb shell cat /proc/device-tree/model`
   - listings of `/proc/device-tree` and `/sys/firmware/devicetree/base`
3. Decompile received FDT with `dtc -I dtb -O dts`.

Success criterion: Accurately identify which final tree properties match overlay `0`, `1`, or `2`.

Interpretation:

- If final `dtbo-hw_rev`/`dtbo-hw_rev_end` appear, record applied range.
- If bootloader added properties or cmdline with revision, quote them verbatim.
- If FDT cannot be read due to permissions, proceed to H2/H3 without assuming outcome.

### Experiment H2 — Correlation via Visible Properties Without Root

Objective: Find reproducible indirect signals before depending on FDT.

1. Search full `getprop` output for keys containing `rev`, `revision`, `hw`, `boot.hw`, `board`, `platform`, and `product`.
2. Save `dmesg` if build permits and search for Samsung driver lines printing `hw_rev`, BOM, panel, touch, or battery.
3. Record exact panel/touch controller model from sysfs only if accessible without root.

Interpretation: These signals may discriminate overlay family, but must be marked as indirect evidence until correlated with FDT.

### Experiment H3 — Download Mode Observation Without Writing

Objective: Determine whether bootloader environment exposes readable identity.

1. Enter Download Mode following standard device procedure.
2. Enumerate USB from host and capture descriptors/VID/PID/serial string.
3. Document screen and any visible identifiers.
4. Exit without flashing.

Interpretation: If `hw_rev` does not appear, this experiment closes one path and documents that dead end.

## Provisional Decision

- Do not assume `r04`.
- For offline analysis, compare all three overlays and classify conclusions by whether they are common to all or exclusive to one.
- For any physical experiment sensitive to revision, enforce H1 as prerequisite gate.
- If H1 fails due to permissions, use H2 as partial evidence and treat revision as unknown in plan v2.

## Proposed Documentation

- Update `docs/first-boot-experiment-plan-v2.md` with "hw_rev unknown" as explicit risk and H1 as mandatory preflight when safe ADB access exists.
- Add to physical trial template separate fields: `firmware=EZE4`, `bootloader_revision=U12`, `hw_rev=<unknown|number>`, `dtbo_index=<unknown|0|1|2>`.
- In future DT audits, label each finding as common to all three overlays or specific to `r00`, `r01–r03`, or `r04–r32`.
