# Project Status

Canonical cutoff date: September 6, 2026.

This file governs the overall bring-up status. Specific closure for RMG/EZE4/J2 is governed in `docs/rmg-eze4/CANONICAL_STATUS.md`; completing J2 does not demonstrate recovery readiness, unlocking, or flashing capability.

## Completed in the Workspace

- Confirmed physical target: SM-X510 Wi-Fi, `BP4A.251205.006` / `X510XXUCEZE4`, Android 16, One UI 8.5, U12 binary, CSC `EUX` within multi-CSC `OXM` (`X510OXMCEZE4`);
- Downstream stock sources separated for X510 (`X510XXU3BXDG`) and X516 (`X516BXXU7CYE1`), plus mainline, downloaded in sparse checkouts;
- Base DT and overlay inventory (X510 Wi-Fi: r00/r01/r04; X516 5G reference: r00/r01/r02/r04);
- Reasoned driver matrix;
- DTBO container extractor and embedded FDT scanner;
- Read-only ADB collector;
- Early userspace Kconfig patch and configuration fragment;
- Reproducible ARM64 Lima VM (Ubuntu 26.04, ext4), toolchain scripts, kernel, and BusyBox;
- Downstream reference kernel fully compiled with Clang 21: `Image`, BTF, signed and installed modules, and all three Wi-Fi overlays;
- Nine documented compatibility/correction patches for the vendor tree;
- Static ARM64 BusyBox 1.36.1 with verified minimal configuration;
- Reproducible initramfs in minimal, UFS (28 modules), and USB (45 modules) profiles; USB demonstrates genuine dependencies but exceeds `init_boot` capacity, while persistent root mounts read-only;
- DTBO builder preserving stock revision ranges and verified via hash round-trip tests;
- Build, bring-up, and mainline roadmap documentation;
- Specific target sheet and test log for the EZE4 unit, with model/version guards across extraction, ADB inventory, and compilation;
- EUX/EZE4 firmware downloaded; ZIP verified via archive structure, published MD5 `255c0e65e2ec62b0ba723612c1ece5a4`, and local SHA-256;
- Streaming ZIP -> AP -> partition extractor to avoid duplicating 11+ GB on host;
- Extracted and analyzed EZE4 `boot`, `init_boot`, `vendor_boot`, `dtbo`, and `vbmeta`; Android v4 headers, sizes, compression, and AVB footers recorded;
- Unsigned `boot`/`init_boot` candidate images reconstructed and verified by unpacking; AVB correctly detects that Samsung hash no longer matches;
- End-to-end Lima pipeline (`reference-all`), deterministic Kbuild metadata, relative hashes, and anti-stale-artifact guards on failure;
- Full pipeline run end-to-end with exit code 0; extended test suite covers 88 host-only tests, including OSRC U11 guards, tree comparisons, safety/adversarial tests, DTS semantics, and image tool tests;
- OSRC Android 16/U11 delivery confirmed internally: `X510XXU8DYJ4` base plus `X510XXSBDZB4` supplement, kernel 5.15.180, extracted cleanly onto ext4 without modifying U3 or stock EZE4;
- Systematic U3 -> U11 -> EZE4 comparison generated: U11 overlay shows no observable material differences from stock EZE4 r04 (though unresolved external references remain), while base DT differs materially in `mfc/debug_mode` within observable nodes;
- U11 compiled fully with Clang 21 ARM64 and the nine active patches: Image, BTF/LTO, DTB, three DTBOs, and 282 modules built and installed; negative tests confirm failures reappearing upon removing each relevant compatibility patch;
- Fixed U11 pipeline without arbitrary commands, featuring nine patch hashes, deterministic metadata, and rejection of absolute host paths in Image/modules;
- Binary audit of compiled U11 -> EZE4 DTBs: four observable differences (EMS, MFC, and SCSC) and 14 unresolved references; none justify claiming complete equivalence;
- Audit of 282 U11 modules against 281 stock modules: 280 common modules retain relative order, hard dependencies and UFS/USB closures are satisfied;
- U11 preflight and initramfs separated from U3 pipeline, strictly enforcing physical `NO-GO` gate.

## Canonical Update 2026-09-05 — EZE4 & Physical Unlock Evidence

The historical U11 block below is retained as history, but no longer describes the active baseline. Samsung OSRC EZE4 (`5.15.189`) is the canonical pipeline baseline:
- Exact stock `kernelrelease`: `5.15.189-android13-3-33478785`
- Exact stock `vermagic`: `5.15.189-android13-3-33478785 SMP preempt mod_unload modversions aarch64`
- ABI Compatibility: 100.00% (281/281 stock proprietary modules verified, 15,123/15,123 CRC symbols exact, 0 discrepancies).
- Regression Test Suite: 98/98 tests passing on host (incorporating anti-self-confirmation physical identity guards for 5.15.189-android13-3-33478785 and repro_compare aliases).
- Root-My-Galaxy EZE4 Project: Phase J2.1-R1 Non-Semantic Remediation COMPLETED; J2 validation stack frozen (71/71 tests passing); canonical invalid trial caps ($\le 1/\text{boot}$, $\le 2\,\text{total}$); canonical confounders ($C_1 = \text{unseparated P0 contamination}$, $C_2 = \text{Android freezer / suspension}$, $C_3 = \text{thermal throttling / core migration}$); J2 checkpoint hygiene: COMPLETE; overall repository working tree: DIRTY BY DESIGN; J3 on HOLD; L3 on NO-GO; real exploit not demonstrated.

### Physical State and Diagnostic Evidence (Updated via `IMG_2113.HEIC` and `IMG_2114.HEIC`)

Direct photographic evidence was obtained of the pre-download Warning Screen (`IMG_2113.HEIC`) and standard Odin Mode screen (`IMG_2114.HEIC`, public transcript with device-unique identifiers redacted in `docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md`):
- **Warning Screen**: **CONFIRMED** (physically photographed in `IMG_2113.HEIC`).
- **Route to Device Unlock Mode**: **CONFIRMED** (explicitly advertised in bootloader microcode under Chinese localization: `长按音量增加键：设备解锁模式`, omitted in English).
- **Standard Odin Mode Screen**: **CONFIRMED** (reached via short press of Vol Up from Warning Screen, photographed in `IMG_2114.HEIC`).
- **CURRENT BINARY**: `Samsung Official` (**CONFIRMED** in bootloader UI).
- **KG STATE**: `Completed (00)` (**CONFIRMED** in bootloader UI).
- **Secure Download**: `Enabled` (**CONFIRMED** in bootloader UI).
- **Sales code / CID / AID**: `EUX//` (**CONFIRMED** in bootloader UI).
- **WARRANTY VOID**: `0 (0x0000)` (**CONFIRMED** in bootloader UI).
- **RP SWREV (Bootloader)**: `B:12` (**CONFIRMED** in bootloader UI; physically confirms rollback index 12).
- **HW REV**: `4` (**CONFIRMED** in bootloader UI; matches DTBO `r04`).
- **DDR SIZE**: `8G` (**CONFIRMED** in bootloader UI).
- **BUILD VERSION**: `X510XXUCEZE4` (**CONFIRMED** in bootloader UI).
- **Fields Not Displayed in Odin Mode**: `OEM LOCK`, `FRP LOCK`, `SYSTEM STATUS` (**`NOT DISPLAYED`**; state must not be inferred from absence).
- **Safe Reboot/Cancel Sequence**: `Volume Down Key + Side key for more than 7 secs` (**CONFIRMED** in UI).
- **Practical Owner Unlock Capability**: **STRONGLY_SUPPORTED** (advertised in SBOOT/LOKE UI on carrier-free Exynos EUX hardware).
- **Device Unlock Mode Screen (2B)**: **NOT YET CAPTURED / NOT YET OBSERVED**.
- **Successful Unlock Completed**: **NOT YET TESTED / LOCKED** (physical device remains strictly `ro.boot.flash.locked=1`, `ro.boot.vbmeta.device_state=locked`, `ro.boot.verifiedbootstate=green`, `ro.boot.warranty_bit=0`).
- **Owner Decision State**: **`NOT_READY_FOR_OWNER_UNLOCK_DECISION`**. Evidence supports the existence of an unlock path, but does not close recovery/PIT/restoration readiness; J2 does not alter this NO-GO.
- **First Custom Flash State**: **`NOT_READY_FOR_FIRST_CUSTOM_FLASH`** (recovery is only partially validated and multi-partition AVB is untested).
- **Recovery**: **PARTIALLY VALIDATED** (Download Mode access, visual diagnostics, and USB `04e8:685d` enumeration confirmed; macOS host tools, LOKE handshake, PIT read, and full restoration remain pending).
- **Meaning of `[Reboot Device - D2]`**: strictly **UNKNOWN** (community hypothesis of lock screen presence remains unproven conjecture).
- **AVB 2.0 Flags**: formal distinction between `flags=1` (`HASHTREE_DISABLED`) and `flags=2` (`VERIFICATION_DISABLED`).
- **Physical Evidence Documents**: `docs/boot-chain/unlock-evidence-matrix.md`, `docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md`, `docs/hardware/evidence/2026-09-05-download-warning-device-unlock-mode.md`. Their presence does not convert these unversioned documents into canonical evidence of the current commit.

## Pending Physical Data (Historical U11; Superseded)

- Receive official Samsung OSRC response for exact `SM-X510` / `X510XXUCEZE4` source; U11 is best current reference, not EZE4;
- Obtain live runtime DT and partition map;
- Locate observable console;
- Identify physical revision / overlay actually selected by bootloader;
- Replicate / adapt patches onto EZE4 source once released by Samsung;
- Decide and validate unlocking, signing/AVB, and rollback procedures without endangering data or anti-rollback state;
- Execute M2-M5 on hardware and capture logs.

## Active Safety Interlock

`scripts/build-downstream.sh` compares the known reference source (`X510XXU3BXDG`) with target (`X510XXUCEZE4`) and halts. `ALLOW_REFERENCE_BUILD=1` may be used solely to practice/diagnose compilation; it does not make the output compatible or authorize flashing.

## Explicit Non-Claims

It is not claimed that mainline boots, that the reference kernel is compatible with EZE4, that unsigned candidates are flashable, or that display, UFS, Wi-Fi, or charging function. Such claims will only be made accompanied by hardware logs and reproducible hashes.
