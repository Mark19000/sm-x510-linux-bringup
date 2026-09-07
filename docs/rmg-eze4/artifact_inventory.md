# Technical Artifact Inventory — SM-X510 (EZE4)

- **Device**: Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510`)
- **Codename**: `gts9fewifi`
- **SoC**: Samsung Exynos 1380 (`s5e8835`)
- **Target Firmware**: `X510XXUCEZE4` (Android 16 / One UI 8.5 / Bootloader U12 / REV00)
- **Stock Kernel Release**: `5.15.189-android13-3-33478785`
- **Stock Vermagic**: `5.15.189-android13-3-33478785 SMP preempt mod_unload modversions aarch64`
- **Hardware State**: Bootloader locked (`ro.boot.flash.locked=1`, `SWREV B:12`, `WARRANTY VOID: 0`)
- **Audit Date**: 2026-09-06

---

## 1. Master Artifact Table

| Category | PATH (Relative to `tab-s9-fe-linux/` or Guest) | TYPE | VERSION | HASH (SHA-256) | PURPOSE |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Kernel Source** | `audit/eze4-source-intake/packages/base/Kernel.tar.gz` | Tar Gzip | 5.15.189 | `2f3e18626011311a1450138e19b2091f7c177a5f8be6400a091f216800969b0f` | Official downstream Samsung OSRC source code for EZE4. |
| **Kernel Source** | `audit/eze4-source-intake/wrapper/SM-X510_EUR_16_Opensource.zip` | Zip | 5.15.189 | `72378f3be5c38344d52d231f85ee75c4b775feaac3ecbc794a1b59d791b1aad0` | Original OSRC wrapper package distributed by Samsung. |
| **Kernel Source (Tree)** | `audit/eze4-source-intake/extracted/kernel/` | Directory / C Tree | 5.15.189 | *(Directory of 86,456 entries)* | Complete source tree extracted for static audit. |
| **Boot Image** | `artifacts/stock/images/boot.img` | Android Boot v4 | EZE4 | `c96c0eb033d2208e84fbe0a0926df3ce2e8c6a94066702f2592e7bc165d11013` | Official `boot.img` (67.1 MB), contains stock kernel Image and AVB footer. |
| **Boot Image (LZ4)** | `artifacts/stock/raw/boot.img.lz4` | LZ4 frame | EZE4 | `4a1cb8550faad30bda66df9d432dd6ec815ce79a795d12a9c35d01f4c7e3cc1f` | Compressed LZ4 stream extracted from the `AP_*.tar.md5` archive. |
| **Init Boot** | `artifacts/stock/images/init_boot.img` | Android Boot v4 | EZE4 | `9efb41692562f648b1227a7f7212bd87eec59d299689ac0b11c51348800e969c` | Generic initial ramdisk image (16.8 MB), LZ4-legacy ramdisk. |
| **Init Boot (LZ4)** | `artifacts/stock/raw/init_boot.img.lz4` | LZ4 frame | EZE4 | `40f6be7510ae627bde0e6d8f4ff1136ba3d2175e95ff4b6d92d6af38499629c1` | Init_boot LZ4 stream extracted from AP. |
| **Vendor Boot** | `artifacts/stock/images/vendor_boot.img` | Android Vendor Boot v4 | EZE4 | `60e85ca061cc67cfa1f8d9fd86fc3840ccb46d87887c9b3ed20deca7c02459e8` | Image with ramdisk fragments (generic + DLKM with 281 modules) and base DTB (33.6 MB). |
| **Vendor Boot (LZ4)** | `artifacts/stock/raw/vendor_boot.img.lz4` | LZ4 frame | EZE4 | `c7278a25410a8bc0c1bc0d1571df50487937ec11f7b684c9e1ed30ccf5c71046` | Vendor_boot LZ4 stream. |
| **DTBO Image** | `artifacts/stock/images/dtbo.img` | Android DTBO | EZE4 | `0dd2392e46fdd404d807b4d866b78f6a5c4833220c35fb2618f2651dce04469b` | Hardware overlays container (8.4 MB), contains 3 overlays (r00, r01, r04). |
| **DTBO (LZ4)** | `artifacts/stock/raw/dtbo.img.lz4` | LZ4 frame | EZE4 | `5f872b1537387c7639f30e6f91e9b9044ea69ab087cb201196b24360df02ffa5` | DTBO LZ4 stream extracted from AP. |
| **VBMeta Image** | `artifacts/stock/images/vbmeta.img` | AVB 2.0 Descriptor | EZE4 | `bef09047de0beb48c8e8c57c283be46a283268cbf248b68c40b125441df40a9f` | AVB 2.0 signing root partition (10,128 bytes) with Samsung public keys. |
| **VBMeta (LZ4)** | `artifacts/stock/raw/vbmeta.img.lz4` | LZ4 frame | EZE4 | `2106019b8a159b6237641faa850619a78feb9f470b2b3a0bd416598ad3245740` | VBMeta LZ4 stream extracted from AP. |
| **Stock Kernel Image** | Extracted from `boot.img` @ offset 4096 (len 39,356,928) | ARM64 Linux Image (PE/COFF) | 5.15.189-33478785 | `ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9` | Exact factory-loaded executable kernel binary in EZE4 firmware. |
| **Built Kernel Image** | `artifacts/eze4/x510xxuceze4-baseline-20260905/Image` | ARM64 Linux Image | 5.15.189-33478785 | `a6f5c4f1b0e88191c395fa91cead4756986a5466d9da199558948358f0c6758b` | Deterministically rebuilt kernel via project Lima pipeline. |
| **vmlinux (ELF DWARF)** | Lima VM: `/home/markpi.guest/osrc-eze4-work/runs/eze4-fixed2/build-source/out-eze4/vmlinux` | ELF 64-bit LSB (DWARF/BTF) | 5.15.189-33478785 | `44fd5d2b8949924c44d8809063763a099f6b6e1a00ab46c8c48262388724de8d` | Unstripped vmlinux binary (552 MB) with `.BTF` and `.debug_info` sections. |
| **System.map** | `artifacts/eze4/x510xxuceze4-baseline-20260905/System.map` | Plain text | 5.15.189-33478785 | `ec6047c299488b63d71a61facfae66a50fa1864b6c5499a8992768eb311d4515` | Complete virtual symbol table of the compiled EZE4 kernel. |
| **Module.symvers** | `artifacts/eze4/x510xxuceze4-baseline-20260905/Module.symvers` | Plain text | 5.15.189-33478785 | `f57afda2eb6a6755a7237b99e0f6908c0f39066929d9fda30b2e8011087df841` | CRCs of 15,123 exported symbols (`EXPORT_SYMBOL`) for `CONFIG_MODVERSIONS`. |
| **Kernel Config** | `artifacts/eze4/x510xxuceze4-baseline-20260905/kernel.config` | Kconfig config | 5.15.189 | `f9bb6c47759b96749258ae1081a8aa9e0e0c0a7a0774fe554708345ba08a64db` | Exact `.config` configuration generated by `s5e8835-gts9fewifixx_defconfig`. |
| **BTF** | In `vmlinux` (`.BTF` section, 6,000,722 bytes @ offset 0x1bdab1c) | BPF Type Format | 5.15.189 | *(Embedded in ELF/Image)* | Kernel data types, structs, and offsets information for BPF/tracing. |
| **Base DTB** | `artifacts/eze4/x510xxuceze4-baseline-20260905/s5e8835.dtb` | Device Tree Blob | 5.15.189 | `814f78c734c7a7d43e1fceb9fc35faa95f8c04c8313cc3973a04eadac473254f` | Base device tree blob for Exynos 1380 SoC (s5e8835). |
| **Stock DTB** | `artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dtb` | Device Tree Blob | EZE4 Stock | `f5c015b6d5102a013fa7d10e8284566c3c737c357f495ca973ce96f7c8ec3f62` | DTB extracted directly from factory `vendor_boot.img` partition. |
| **DTBO Overlay r00** | `artifacts/eze4/x510xxuceze4-baseline-20260905/gts9fewifi_eur_open_w00_r00.dtbo` | Device Tree Overlay | EZE4 r00 | `4f2fd84ef62c70d4143919d8ddbe6d1152f6532d078878dc30fcb1cf68b790be` | Hardware overlay rev 00 (byte-for-byte identical to stock `overlay-00`). |
| **DTBO Overlay r01** | `artifacts/eze4/x510xxuceze4-baseline-20260905/gts9fewifi_eur_open_w00_r01.dtbo` | Device Tree Overlay | EZE4 r01 | `c764f7c69a9fef235af7c042b1ec7331f600b7eb60dd67d465ec721f8386f325` | Hardware overlay rev 01 (byte-for-byte identical to stock `overlay-01`). |
| **DTBO Overlay r04** | `artifacts/eze4/x510xxuceze4-baseline-20260905/gts9fewifi_eur_open_w00_r04.dtbo` | Device Tree Overlay | EZE4 r04 | `cdee895e13eae5ed35c3a951eb3b8a448a46f60c89f73546bcb7c3b4fae8d403` | Production hardware overlay rev 04 (byte-for-byte identical to stock `overlay-02`). |
| **Stock Modules Audit** | `artifacts/stock/vendor-ramdisk-audit/` | CPIO Metadata | EZE4 Stock | `06adcacad3020efcc0a263c1d62c83ab1504e30f79114398a45250fe8da76deb` | Record of 281 stock DLKM modules, with dependency tables and hashes. |
| **Built Modules Tarball** | `artifacts/eze4/x510xxuceze4-baseline-20260905/modules-root.tar.gz` | Tar Gzip | 5.15.189-33478785 | `18d3768e66c934c063133c1cf9ebdf1a4448c1cf45fcb4e95ed49e5485feed0c` | 282 compiled kernel modules with 100.00% proven ABI parity. |
| **AVB Toolchain** | `sources/toolchain/avb-android16/` | Python / Binary | Android 16 | `d4683e75f9a12a0a7089871fcc0432d242ccc6d44e7c5fe18f4a0f527151ab66` | Official AOSP AVB 2.0 tools for signature and descriptor inspection. |
| **MagiskBoot Tool** | `sources/toolchain/magisk-v30.7/` | Host / guest binary | v30.7 | N/A | Utility to unpack and repack Android boot v4 headers. |
| **Compiler Toolchain** | Lima VM: Ubuntu Clang / LLD | Clang 21.1.8 | LLVM 21.1.8 | N/A | Reproducible aarch64 cross-compiler used in the pipeline. |
| **Build Scripts** | `scripts/build-eze4-in-lima.sh` | Bash Script | v1.0 | N/A | Build orchestrator in the Lima virtualized environment. |
| **ABI Verification Tool** | `scripts/verify-eze4-abi.py` | Python 3 Script | v1.0 | N/A | Automated verifier for `__versions` CRCs against `Module.symvers`. |
| **Firmware Archive Reference**| Host: `/Users/markpi/Downloads/SAMFW.COM_SM-X510_EUX_X510XXUCEZE4_fac.zip` | Zip | EZE4 EUX | `45a450875ce753e74d8183aa085837ada91cabe2832d9725a1567aa29b01d375` | Complete official factory-downloaded firmware archive. |

---

## 2. Bootloader Component Status (`sboot`)

- **Local Presence**: There are no disassembled binary files of `sboot.bin` in the local workspace, because the AP package only includes standard Android OS partitions (`boot`, `init_boot`, `vendor_boot`, `recovery`, `dtbo`, `vbmeta`, `super`). The BL firmware (`BL_X510XXUCEZE4_*.tar.md5`) was not extracted locally to conserve storage space.
- **Physical Hardware Evidence**: Execution of physical diagnostics in Odin Mode (recorded in `docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md`) confirmed that the actual unit has bootloader revision 12 (`RP SWREV B:12`), official binary status (`CURRENT BINARY: Samsung Official`), intact Knox status (`WARRANTY VOID: 0x0000`), and completed Knox Guard protection (`KG STATE: Completed (00)`).
- **Security Guards**: The bootloader is strictly locked.
