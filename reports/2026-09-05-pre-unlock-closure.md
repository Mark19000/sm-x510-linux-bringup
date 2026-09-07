# SM-X510 U12/EZE4 — Pre-Unlock Closure

Date: 2026-09-05. Tablet was not unlocked/flashed and no payloads were generated.

## A. Executive state

| Area | State |
|---|---|
| Kernel | **CONFIRMED** — EZE4 5.15.189, exact stock release |
| ABI | **CONFIRMED** — 281/281 and 15,123/15,123, 0 differences |
| DT | **CONFIRMED** — r00/r01/r04 byte-identical |
| Pipeline | **CONFIRMED** — 95/95, functional determinism |
| Warning Screen | **CONFIRMED** — captured in `IMG_2113.HEIC` |
| Normal Odin Mode Screen | **CONFIRMED** — captured in `IMG_2114.HEIC` (`RP SWREV B:12`, `HW REV 4`, `DDR 8G`, `KG Completed (00)`, `WARRANTY 0`, `EUX`) |
| Unlock capability | **STRONGLY_SUPPORTED** |
| Unlock entry path | **CONFIRMED AS ADVERTISED** on Warning Screen (Chinese localization) |
| Unlock confirmation screen | **UNKNOWN / NOT CAPTURED** |
| Bootloader | **LOCKED** (`CURRENT BINARY: Samsung Official`, `WARRANTY VOID: 0`) |
| Recovery | **PARTIALLY VALIDATED** (access/USB yes; tools/handshake/PIT/restore no) |
| AVB graph | **PARTIAL; mechanically exact for available images** |
| Minimum image set | **CANNOT_YET_BE_DETERMINED** |
| First custom boot | **NOT READY** |

Physical captures confirm the blue warning screen (`IMG_2113.HEIC`, where Chinese text announces long-press Vol+ for Device Unlock Mode) and standard Odin Mode screen (`IMG_2114.HEIC`, confirming `RP SWREV B:12`, `BUILD X510XXUCEZE4`, and `HW REV 4`). Fields `OEM LOCK` and `FRP LOCK` do not appear printed in this version of Odin Mode (`NOT DISPLAYED`), without implying an unlocked state. Device continues to be governed by `LOCKED` and `WARRANTY VOID: 0`.

## B. Remaining unknowns

### BLOCKER

1. Photographing final Device Unlock Mode dialog and its unequivocal cancellation option, without confirming, remains pending.
2. For any custom flash: complete EZE4 firmware, host client, handshake, and PIT are missing.

### HIGH

3. Unlocked Samsung U12 policy regarding modified `boot` or alternate vbmeta.
4. Prism/optics, PIT, and Samsung verifications outside AVB.

### MEDIUM

5. Exact timing of Warranty Bit tripping.
6. sec_debug persistence/readout after first failure.

### LOW

7. Meaning of D2.

## Unlock boundary

Complete AVB and custom minimum are not prerequisites for deciding unlock. The prerequisites are: understanding the exact dialog, accepting wipe/Knox risk, backup and credentials, and archiving locked baseline. Host recovery is mandatory before first flash; since the final screen is still missing, executing unlock today is not recommended.

## AVB/minimum/recovery

Root HASH-protects boot/init_boot/vendor_boot/recovery and others; HASHTREE protects logicals; CHAIN protects dtbo/prism/optics. Child dtbo auto-HASHes itself. Prism/optics/PIT/super are missing. Flags 1/2 are hashtree-disabled/verification-disabled; Samsung acceptance is unknown.

After unlock, `boot-only` is mechanically the minimal candidate for an EZE4 marker and leaves stock init_boot/vendor_boot/dtbo; breaks root/self-HASH. It is unproven that Samsung tolerates this. Modifying vbmeta is not automatically necessary or safer.

Recovery: Download Mode and USB `04e8:685d` yes; tool, protocol/PIT, complete package, and restore no. Lima functions, but lacks demonstrated client or passthrough.

## Post-unlock/first boot design

Following a future unlock, first boot stock and capture lock/AVB/Warranty/KG/cmdline/bootconfig/Download fields. First custom boot must use EZE4 with fixed marker verifiable in `/proc/version`; USB/current/backlight do not prove execution. Do not assume sec_debug pre-handover.

## C. Unlock verdict

```text
NOT_READY_FOR_OWNER_UNLOCK_DECISION
```

Sole pending reason: entry path confirmed, but final dialog / cancellation not yet observed. Capturing it can immediately change this verdict without waiting for kernel or AVB work.

## D. Custom-flash verdict

```text
NOT_READY_FOR_FIRST_CUSTOM_FLASH
```

## One next action

Enter Device Unlock Mode only using the long-press shown in `IMG_2113.HEIC`, release button when screen changes, photograph complete dialog, and **do not confirm**. Exit only via unequivocally indicated cancellation; if none exists, press nothing and submit photo.

Sources: [AOSP unlock](https://source.android.com/docs/core/architecture/bootloader/locking_unlocking), [AOSP AVB boot flow](https://source.android.com/docs/security/features/verifiedboot/boot-flow), [Samsung KG](https://docs.samsungknox.com/admin/knox-guard/get-started/knox-guard-status-flow/), [Samsung Warranty FAQ](https://docs.samsungknox.com/admin/knox-platform-for-enterprise/faq/), [Heimdall](https://github.com/Benjamin-Dobell/Heimdall).
