# 0. Safety, Models, and the Rule of Not Losing Android

## Before Starting

Unlocking the bootloader on a Samsung device typically wipes all data and can permanently and irreversibly trip the Knox Warranty Bit status. Bootloader unlocking availability depends on region, carrier, and device version. This project does not attempt to bypass these restrictions.

Do not unlock or flash yet. First, complete the read-only analysis:

```sh
./scripts/collect-device.sh
./scripts/extract-stock.sh AP_DE_TU_VERSION.tar.md5
```

The second command operates on a local copy of the firmware. The first uses ADB to read information; some queries will be denied on a production Android build, which is normal.

## Identity You Must Record

The target unit for this project is identified as follows:

| Field | Value |
|---|---|
| Model | `SM-X510` |
| Variant | Wi-Fi / `gts9fewifi` |
| Android Build | `BP4A.251205.006` |
| AP/PDA Version | `X510XXUCEZE4` |
| System | Android 16 / One UI 8.5 |
| Bootloader Binary | `C` = U12 |
| Active CSC | `EUX` |
| Multi-CSC Family | `OXM` |
| CSC Version | `X510OXMCEZE4` |

In `X510XXUCEZE4`, `X510` identifies the model family, `XX` the international release branch, `U` a feature update, and `C` is the bootloader binary generation counter (12). The remainder encodes build generation and date. The prefix `BP4A.251205.006` belongs to the Android base platform and does not replace the Samsung AP identifier.

The observed raw string `SAOMC_SM-x510_oxm_eux_16_0001EUX/EUX/` confirms the active CSC `EUX`, multi-CSC family `OXM`, and Android 16. It is not part of the kernel, but is necessary for selecting a coherent full stock firmware package and an appropriate restore image.

Record in your testing log:

- Full model designation (`SM-X510...` or `SM-X516...`);
- Region / CSC;
- Bootloader version and build number;
- Hardware revision if exposed by Android;
- SHA-256 hash of the original AP package;
- Output of `getprop`, `/proc/cmdline`, and partition map.

Two separate base source trees are maintained:

- SM-X510 Wi-Fi: `underdog54/android_kernel_samsung_gts9fewifi`, `stock` branch, commit `9a752a83347461b3785711760ba925fcabea3071`, `X510XXU3BXDG` import, kernel 5.15.123;
- SM-X516 5G: `Fede2782/android_kernel_samsung_gts9fe`, commit `56f84616c0263aa85ccbbfb77f69af2fe4aa4bb6`, `X516BXXU7CYE1` import, kernel 5.15.153.

Neither source tree proves by itself that it matches your installed firmware. When an exact OSRC source release exists for your build, it must be compared and prioritized.

In this case we already know they **do not match**: `X510XXU3BXDG` is U3/Android 14 while the tablet runs `X510XXUCEZE4`, U12/Android 16. Do not downgrade the bootloader or treat a U3 kernel as a U12 boot image.

## Variants

| Model | Connectivity | Specific Risk |
|---|---|---|
| SM-X510 | Wi-Fi | Must not receive modem overlays or modem configuration |
| SM-X516/B/N | Wi-Fi + 5G | Adds modem, reserved memory, and CP interfaces |

`gts9fewifi` and `gts9fe` share substantial code, but are not interchangeable. An incorrect Device Tree can assign two drivers to the same register range, GPIO pin, or clock.

## Testing Policy

1. Maintain full official stock firmware and a known working procedure to restore it.
2. Never flash `boot`, `vendor_boot`, `dtbo`, `vbmeta`, or `super` without verifying model, partition size, and hash.
3. Generate new images derived from the stock image; do not invent header parameters, offsets, or AVB descriptors.
4. On the first test boot, do not mount UFS read-write. The initramfs uses `ro`.
5. Change only a single variable per attempt and preserve the complete serial/system log.
6. Do not test charging or battery management with incomplete drivers: use stable external power and monitor temperature externally from experimental software.

There are no flashing scripts in this repository. This is intentional: transitioning from M1 (built artifacts) to M2 (first hardware boot) requires knowing your actual physical unit.
