# 10. SM-X510 / EZE4 Target Unit Logbook

This chapter translates device identifiers into concrete technical decisions. The primary principle is straightforward: **model, AP version, CSC, and bootloader binary generation are distinct data points**. It is not sufficient that a file simply says "Tab S9 FE".

## What Is Confirmed

The physical Android UI displayed:

```text
BP4A.251205.006.x510xxuceze4
```

This decomposes into:

- `BP4A.251205.006`: Android platform baseline build;
- `X510XXUCEZE4`: Samsung AP/PDA release version, normalized to uppercase;
- `X510`: SM-X510 model family (Wi-Fi variant);
- `C`: U12 bootloader binary generation counter;
- Shipping operating system: Android 16 / One UI 8.5.

The reproducible specification resides in `configs/target-sm-x510.env`. Verify it via:

```sh
make target
```

## Confirmed CSC

The tablet displays:

```text
SAOMC_SM-x510_oxm_eux_16_0001EUX/EUX/
```

Preserve exact case and whitespace. The technical interpretation for this project is:

- `EUX`: Active European Union CSC;
- `OXM`: Multi-CSC package family containing EUX;
- `16`: Android major version;
- `EUX/EUX/`: All active regional slots match EUX.

The complete software release pair to maintain is:

```text
AP/PDA: X510XXUCEZE4
CSC:    X510OXMCEZE4
```

CSC identifies the distribution region/channel and cannot be inferred from AP alone. To verify in the on-device UI:

```text
Settings -> About tablet -> Software information
-> Service provider software version
```

Via ADB (without root):

```sh
adb shell getprop ro.boot.sales_code
adb shell getprop ro.csc.sales_code
adb shell getprop ro.bootloader
```

ADB queries may return empty properties on production builds; the SAOMC string from the Android UI is authoritative here.

## Status of the Two Input Materials

The port requires two distinct deliverables:

1. The exact stock firmware package `SM-X510 / EUX / X510XXUCEZE4`, CSC `X510OXMCEZE4`. **Acquired and extracted**.
2. Official GPL source code published by Samsung for SM-X510 / Android 16. Searched on Samsung Open Source Release Center under `SM-X510` and `X510XXUCEZE4`. If absent, submit an "Inquiry -> Request for source codes" specifying model, AP version, Android 16, and region/CSC.

Firmware supplies real binary images; OSRC supplies source code that can be compiled and audited. One does not replace the other. As of this logbook entry, the former is secured, while the latter is actively tracked and requested.

Public searches on August 23, 2026 did not yield an exact EZE4 entry. The owner submitted an official inquiry for SM-X510 / X510XXUCEZE4 / Android 16, which Samsung confirmed was escalated to the responsible department. If no response is received within 24 hours, the request will be resent from the same account. The project integrates incoming source code only upon receiving and archiving complete materials with timestamp, filename, and SHA-256.

Suggested text for "Request for source codes":

```text
Subject: Complete corresponding source request for SM-X510 / X510XXUCEZE4

Hello,

I own a Samsung Galaxy Tab S9 FE Wi-Fi, model SM-X510, with software version
X510XXUCEZE4 (Android 16), CSC X510OXMCEZE4 / EUX and build
BP4A.251205.006.

Please provide the complete corresponding source code for the GPL-licensed
Linux kernel and kernel modules shipped in this exact software release,
including the configuration, Device Tree sources, build scripts and any other
scripts used to control compilation and installation.

This request is for the corresponding open-source material; I am not asking
for Samsung signing keys or proprietary firmware.

Thank you.
```

When a response arrives, retain the original email, archive filename, timestamp, URL, and SHA-256. Do not overwrite `sources/wifi-kernel`: extract the delivery to an isolated path and compare commit, kernel release, defconfig, DTS, and build scripts first.

Do not use third-party "root" packages, patched `vbmeta`, or prebuilt kernels for this phase. Maintain a clean, verified original.

## Exact Firmware Validated and Extracted

The retained archive is:

```text
SAMFW.COM_SM-X510_EUX_X510XXUCEZE4_fac.zip
MD5:    255c0e65e2ec62b0ba723612c1ece5a4
SHA256: 45a450875ce753e74d8183aa085837ada91cabe2832d9725a1567aa29b01d375
AP:     AP_X510XXUCEZE4_X510XXUCEZE4_MQB109790656_REV00_user_low_ship_MULTI_CERT_meta_OS16.tar.md5
```

Extracted images reside under `artifacts/stock/images/`; hashes and provenance are stored in `artifacts/stock/SHA256SUMS`, `FIRMWARE_SHA256SUM`, and `firmware-metadata.txt`.

To reproduce extraction from the downloaded archive:

```sh
make stock FIRMWARE=/path/to/SAMFW.COM_SM-X510_EUX_X510XXUCEZE4_....zip
```

This saves over 11 GB by streaming AP contents directly into `tar` to extract only boot-chain partitions. The monolithic `super.img` is not copied.

Name checks only validate the file string; cryptographic hashes validate content integrity. `extract-stock.sh` operates entirely locally and performs no writes to the tablet.

## Observed EZE4 Image Layout

`tools/bootimg_info.py` recorded exact layout values in `artifacts/stock/boot-layout.json`:

| Image | Header | Content Breakdown |
|---|---:|---|
| `boot.img` | Android v4 | Kernel 39,356,928 B, ramdisk 0 B |
| `init_boot.img` | Android v4 | Legacy LZ4 ramdisk 2,486,802 B |
| `vendor_boot.img` | Android v4 | Vendor ramdisk 18,077,432 B, DTB 239,652 B, two fragments |
| `dtbo.img` | DTBO Table | Three overlays, followed by AVB footer/padding up to 8 MiB |

The `os_version` field in the boot header reports 13.0.0 even though Android userspace is 16; this is inherited GKI header metadata and does not contradict the tablet's OS version.

The reference `Image` measures 995,328 bytes smaller than stock. Both the minimal initramfs and compressed UFS profile fit within partition capacity, but this addresses only mechanical sizing: it does not resolve ABI compatibility, AVB enforcement, or anti-rollback counters.

## Why U3 Source Remains Valuable

`X510XXU3BXDG` teaches Device Tree hierarchy, board identifiers, and S5E8835 peripheral drivers. It also automates reports and exercises build pipelines. However, between U3 / Android 14 and U12 / Android 16, Kconfig flags, module ABI symbols, DTBOs, boot headers, and AVB policies may have shifted.

Therefore two distinct workflows exist:

```sh
make report VARIANT=wifi

# Compilation dry run only; output not targeted at the device:
./scripts/build-reference-in-lima.sh
```

On native Linux: `ALLOW_REFERENCE_BUILD=1 make build VARIANT=wifi`; on macOS use the Lima wrapper above.

Standard builds remain locked until a compatible source release is validated. Never attempt to downgrade the bootloader from U12 to U3.

## Bring-up Gate Criteria

Before milestone M2, the following must be documented:

- CSC `EUX` / multi-CSC `OXM` confirmed;
- SHA-256 hashes of exact firmware package and extracted images (complete);
- Extracted DTB/DTBO (complete) and identified hardware revision (pending on physical device);
- Compatible kernel source or documented, justified diffs;
- Restorable official firmware copy;
- Observation interface (UART or USB) and actual OEM unlock state.

Until then, safe work consists of static analysis, reference compilation, initramfs design, and offline candidate repacking labeled `UNSIGNED`; never flashing.
