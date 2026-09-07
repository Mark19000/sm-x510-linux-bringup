# 2. Device Tree (DTS/DTSI) Analysis

## Examined Sources

The physical unit uses `X510XXUCEZE4` (Android 16 / U12). We already possess the exact EUX AP package and its binary Device Trees; exact OSRC source publication remains separate. Therefore we strictly distinguish **observed EZE4 data** from **reference U3 source code**.

- SM-X510 downstream 5.15.123, commit `9a752a8...`, imported from `X510XXU3BXDG`.
- SM-X516 downstream 5.15.153, commit `56f84616...`, imported from `X516BXXU7CYE1`.
- Base EZE4 DT extracted from `vendor_boot.img` and three entries from `dtbo.img`.
- `arch/arm64/boot/dts/exynos/s5e8835.dts`: ~12,400 lines.
- Wi-Fi overlays `r00/r01/r04` and 5G overlays `r00/r01/r02/r04`.
- Linux mainline snapshot `26260251022f...`, August 21, 2026.

Regenerate mechanical data with:

```sh
make fetch VARIANT=wifi
make report VARIANT=wifi
# For X516:
make fetch VARIANT=5g
make report VARIANT=5g
```

Mechanical results are separated into `reports/generated/wifi/compatibles.md` and `reports/generated/5g/compatibles.md`.

## Revision Selection

| File | `dtbo-hw_rev` | `dtbo-hw_rev_end` |
|---|---:|---:|
| r00 | 0 | 0 |
| r01 Wi-Fi | 1 | 3 |
| r01 5G | 1 | 1 |
| r02 5G | 2 | 3 |
| r04 | 4 | 32 |

The stock EZE4 table contains exactly those three Wi-Fi ranges: 0, 1–3, and 4–32. This confirms how revisions are packaged, but does not prove which revision this specific hardware unit selected. To answer that question, we require the hwrev exposed by the bootloader or the effective tree in `/proc/device-tree`.

Between revisions, pinctrl pull-up/pull-down settings, magnetometer calibrations, display fragments, and numerous renumbered phandles vary. Do not select r04 merely because it is the highest integer. Selection belongs to the bootloader and must be confirmed via live DT or stock DTBO metadata.

## S5E8835 Base Tree

Observed blocks:

- 8 CPUs and PSCI 1.0;
- GIC-400, ARM architected timer, and PMU;
- Clock controller `samsung,s5e8835-clock` and six pinctrl controllers;
- 16 UART, 29 HSI2C, and 15 SPI nodes defined, nearly all disabled by default;
- Embedded UFS at `0x13500000` with proprietary Samsung calibration;
- DWC3 at `0x13200000` and Samsung USB PHY;
- DPU/DECON/DSIM, IOMMU v8, and downstream Mali;
- ABOX audio, cameras, NPU, sensors, SCSC Wi-Fi/BT, and reserved memory;
- S2MPU15/S2MPU16 PMICs managed via ACPM.

The downstream `/chosen` node sets an Android kernel command line and initrd ranges. UART0 is located at `0x13800000`, contains debug properties, but is marked `status = "disabled"`. It is not enabled automatically in this project: first its pins must be traced to check whether they route to an external connector or remain strictly internal.

## Galaxy Tab S9 FE Overlays

The overlays declare `SAMSUNG,GTS9FEWIFI_EUR_OPEN` or `SAMSUNG,GTS9FE_EUR_OPEN` and add or modify, among others:

- BOE HX83102J or CSOT NT36523N LCD panel, 90/60/30 Hz modes;
- Novatek or Himax touchscreen controller;
- Wacom digitizer `wacom,w9`;
- Cirrus CS35L45 audio amplifiers;
- Silicon Mitus SM5714 USB-PD/charging and SM5440 direct charger;
- S2MPU15/S2MPU16 PMICs;
- STM32 keyboard/touchpad/pogo interface;
- IMX355 and HI1337 cameras;
- Keys, Hall sensors, thermistors, and battery parameters;
- Modem/CP interfaces on cellular variants.

The coexistence of two panels and two touchscreen controllers explains why a single hardware BOM must not be hardcoded. The kernel/DT must detect or select the component populated on the actual physical unit.

## Method for Analyzing Firmware

```sh
brew install dtc lz4                 # macOS, analysis only
./scripts/extract-stock.sh AP_....tar.md5
```

If you have the complete full firmware ZIP, do not extract the AP tarball first: on EZE4 this consumes over 11 GB and unnecessarily duplicates disk space. Use the streaming extractor:

```sh
make stock FIRMWARE=/path/to/SAMFW.COM_SM-X510_EUX_X510XXUCEZE4_....zip
```

The extractor halts if `artifacts/stock` already contains data to avoid mixing two packages. To consciously repeat extraction, use `REPLACE_STOCK_OUTPUT=1 make stock FIRMWARE=...`; this replaces only `raw/`, `images/`, `dt/`, and generated metadata.

The `ZIP -> tar` streaming pipeline extracts only `boot`, `init_boot`, `vendor_boot`, `dtbo`, `recovery`, and `vbmeta`. It deliberately omits `super.img`, computes SHA-256 digests, and performs no writes to the tablet.

The tool:

1. Extracts the tar archive into a clean directory;
2. Decompresses LZ4 image payloads;
3. Parses the Android DTBO header and separates all entries;
4. Scans for embedded FDT blobs in `boot`, `vendor_boot`, and `dtb`;
5. Uses `dtc` to decompile into DTS text when available;
6. Computes SHA-256 hashes.

To recompose an effective Device Tree, you must know which entry the bootloader selected. With correct base and overlay:

```sh
fdtoverlay -i base.dtb -o effective.dtb overlay.dtbo
dtc -I dtb -O dts -o effective.dts effective.dtb
```

If `fdtoverlay` fails due to symbols/fixups, first compare the runtime DT acquired by `collect-device.sh`; a base and overlay from mismatched firmware releases is a common failure cause.

## Measured Differences Between U3 and EZE4

All three EZE4 overlays were decompiled and compared against their U3 equivalents. Each diff spans ~85 lines and reflects consistent substantive changes:

- `battery_full_capacity` changes from `0x276a` to `0x1f40`;
- The keyboard table adds models DX725, DX720, and Neos;
- Touchpad maximum coordinates update to `0x578 × 0x324`;
- Thermal zones receive explicit names `zone_big`, `zone_lit`, `zone_g3d`, and `zone_isp` with a `zone-name` property;
- `pktproc_ul_hiprio_ack_only` changes from 1 to 0;
- The IMX355 camera adds `pinning_setfile` and `preload_setfile` parameters.

These are not cosmetic changes: battery capacity, thermal definitions, peripherals, and camera parameters demonstrate why the U3 overlay must not be reused even if it compiles cleanly.

Textual diff of the base DT shows ~5,458 lines, but most is phandle renumbering caused by decompilation. The conservative comparator `tools/dts_semantic_diff.py` matches 602 renumberings by path and isolates 37 material differences; it still leaves 10 external references unresolved, leading to the strict verdict `DIFFERENT (INCOMPLETE)`. In overlay r04, it identifies 17 material differences and 207 external references.

The complete reproducible report is in [`reports/generated/wifi/eze4-vs-u3-semantic.md`](../reports/generated/wifi/eze4-vs-u3-semantic.md). Among base changes are a reserved memory region `wdtmsg`, GPIO `gph1`, EMS/on-time/gsc/fclamp scheduler tunables, and Mali clock properties. Before porting a change, you must trace references and compare nodes by hierarchical path, not by numeric phandle. The tool does not expand DTSI or apply overlays, and never converts incomplete evidence into equivalence.

## Limitations of Automated Reports

A textual match on a `compatible` string only proves that the string exists in the repository checkout. A driver may require hardware-specific platform data not implemented upstream; and an IP block that is compatible may use a different vendor string. The automated table serves to prioritize code inspection. Technical decisions belong in the manual driver matrix in the next chapter.
