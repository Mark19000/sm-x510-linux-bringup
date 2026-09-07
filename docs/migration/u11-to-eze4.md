# Canonical Migration: From U11 (5.15.180) to EZE4 (5.15.189)

- **Device**: Samsung Galaxy Tab S9 FE WiFi (`SM-X510`)
- **SoC**: Samsung Exynos S5E8835 (Exynos 1380)
- **Historical Baseline**: `X510XXSBDZB4` (Android 16 / Bootloader U11 / Linux 5.15.180)
- **Active Canonical Baseline**: `X510XXUCEZE4` (Android 16 / Bootloader U12 / Linux 5.15.189)
- **Migration Date**: 2026-09-05
- **Status**: **PROMOTION COMPLETED (`EZE4_READY_TO_PROMOTE`)**

---

## 1. Context and Historical Role of U11

The use of the **U11 (`X510XXSBDZB4`)** source was not an error, but an indispensable and deliberate technical stage in the safe bring-up methodology:

1. **Initial Availability**: When Android 16 research began for the SM-X510, Samsung OSRC had only published package `X510XXSBDZB4` (Bootloader 11 / binary B). The project's physical tablet had already received the OTA update to `X510XXUCEZE4` (Bootloader 12 / binary C).
2. **Environment Maturation**: The entire engineering infrastructure was developed with U11:
   - Lima Linux container/VM (`gts9fe-build`) on ext4 to avoid 38 case-folding name collisions on macOS APFS.
   - Clang 21 / LLD toolchain with debug path normalization (`/build/eze4`).
   - Deep understanding of downstream version generation in `scripts/setlocalversion` (`sec_scm_version`).
   - Development of the downstream 11-patch set to enable clean compilation with modern compilers.
3. **Zero Hardware Risk Principle**: Because U11 used Linux 5.15.180 compared to 5.15.189 on the tablet's stock firmware, the project enforced a strict safety gate: **flashing prohibited as long as any version gap or uncertainty in `CONFIG_MODVERSIONS` parity remained**.

---

## 2. Technical Gaps Identified in U11

During U11 preflight, insurmountable barriers to safe flashing were identified:

| Vector | Status in U11 | Tablet Reality | Technical Impact |
| :--- | :--- | :--- | :--- |
| **Kernel Version** | `5.15.180` | `5.15.189` | 9 intermediate LTS updates with changes in `mm`, `rcu`, `net`. |
| **Bootloader** | Revision 11 (B) | Revision 12 (C) | Risk of incompatibility in boot headers and `boot_control`. |
| **ABI Parity** | Not demonstrated | Required by 281 modules | `CONFIG_MODVERSIONS=y` would reject any module if CRCs diverge. |
| **Device Tree** | U11 DTS source | Stock EZE4 DTBO | Octal escape labels and potential pin divergences. |

For these reasons, U11 was maintained as a **compilation testbed**, protecting the tablet against bootloops and kernel panics.

---

## 3. Official Release of EZE4 by Samsung

In late August 2026, Samsung Open Source Release Center (OSRC) released the official package corresponding to the tablet's exact firmware:
- **Archive**: `SM-X510_EUR_16_Opensource.zip` / `Kernel.tar.gz`
- **SHA-256**: `2f3e18626011311a1450138e19b2091f7c177a5f8be6400a091f216800969b0f`
- **Official Sublevel**: `VERSION = 5`, `PATCHLEVEL = 15`, `SUBLEVEL = 189`.
- **Full Match**: The source code matches Samsung's production build for Android 16 U12 point-for-point.

---

## 4. Semantic Audit and Patchset Evolution

23 kernel subsystems were evaluated comparing U11 vs EZE4. Differences corresponded to the progression from Linux 5.15.180 to 5.15.189 plus minor Samsung optimizations in camera drivers and power management.

### Downstream Patchset Status

The project patchset was audited and adapted for EZE4, going from 11 to **10 active patches**:

| Patch | Action in EZE4 | Technical Justification |
| :--- | :---: | :--- |
| `0001-kbuild-clang-disable-unknown-warning-options.patch` | **Retained** | Applies clean; silences unknown Clang 21 options. |
| `0002-compiler-clang21-cleanups.patch` | **Rebased** | Updated lines in `arch/arm64/kvm/sys_regs.c`, `sysbusy.c`, `filemap.c`. |
| `0003-scripts-setlocalversion-support-kmi-generation-and-l.patch` | **Retained** | Required to fix exactly `-33478785` in `kernelrelease`. |
| `0004-vendor-drivers-fix-invalid-declarations.patch` | **Retained** | Resolves void returns in non-void functions in proprietary drivers. |
| `0005-soc-samsung-ems-remove-unused-declaration.patch` | **Retained** | Eliminates type conflict in EMS prototypes. |
| `0006-video-fbdev-exynos-fix-array-bounds-warning.patch` | **Retained** | Fixes array bounds warnings in fbdev. |
| `0007-init-samsung-kconfig-platform-version-guard.patch` | **OBSOLETE** | **Removed**: Samsung incorporated the guard natively in EZE4. |
| `0008-fs-fuse-fix-missing-fuse_abort_conn-prototype.patch` | **Retained** | Adds prototype required under `-Werror`. |
| `0009-drivers-sensorhub-suppress-unreachable-break-warning.patch` | **Retained** | Eliminates unreachable break in sensorhub. |
| `0010-drivers-usb-dwc3-fix-unannotated-switch-fallthrough.patch` | **Retained** | Adds `fallthrough;` attribute. |
| `0011-Makefile-allow-custom-kbuild-build-version.patch` | **Rebased** | Line updated in root Makefile (1138). |

The new canonical manifest is located at [`configs/eze4-patches.sha256`](file:///Users/markpi/tab-s9-fe-linux/configs/eze4-patches.sha256).

---

## 5. Empirical Demonstration of ABI Parity

Unlike the U11 stage where compatibility was a hypothesis, in EZE4 a **definitive mathematical and binary proof** was achieved:

1. **Binary Cross-Check**: The DLKM fragment was extracted from the tablet's official `vendor_boot.img` partition (281 `.ko` modules).
2. **Symbol Audit**: Using [`scripts/verify-eze4-abi.py`](file:///Users/markpi/tab-s9-fe-linux/scripts/verify-eze4-abi.py), the CRCs in the `__versions` section of the 281 stock modules were checked against the newly compiled `Module.symvers`:
   - **Audited Modules**: 281 / 281 (100.00% perfect match).
   - **Symbol References**: 15,123.
   - **Exact Matching CRCs**: **15,123 (100.00%)**.
   - **Discrepancies**: **0**.
   - **Missing Symbols**: **0**.
3. **DTBO Identity**: The generated `.dtbo` binaries for revisions `r00`, `r01`, and `r04` proved **byte-for-byte identical** to those extracted from stock firmware.

---

## 6. Historical Preservation Policy

To ensure scientific traceability and avoid rewriting history:
- **EZE4 is the active canonical baseline**: All production scripts (`scripts/build-eze4-in-lima.sh`), configurations (`configs/eze4-x510xxuceze4.env`), and reports point to EZE4.
- **U11 is frozen as historical reference**: Its configurations (`configs/u11-x510xxsbdzb4.env`, `configs/u11-patches.sha256`), artifacts in `artifacts/u11/`, and unit tests are preserved. Previous commits and branches are not removed.
- **Zero ambiguity**: The pipeline actively builds only EZE4 unless a regression audit on U11 is explicitly requested.
