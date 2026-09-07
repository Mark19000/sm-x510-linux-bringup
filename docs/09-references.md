# 9. References and Provenance

## Primary Sources

- [Samsung Open Source Release Center](https://opensource.samsung.com/): Official source repository, searched by exact model and firmware build.
- [Official SM-X510 Software History](https://doc.samsungmobile.com/SM-X510/029471240301/spa-us.html): Official release log used to verify the device's build history.
- [SM-X510 EUX X510XXUCEZE4 Firmware](https://samfw.com/firmware/SM-X510/EUX/X510XXUCEZE4): Secondary index useful for cross-referencing AP/CSC and binary version; packages must be verified against actual device CSC and checksums before analysis.
- [Stock SM-X510 Source (X510XXU3BXDG)](https://github.com/underdog54/android_kernel_samsung_gts9fewifi/tree/stock): Community mirror used for downstream Wi-Fi analysis.
- [SM-X516 Source (X516BXXU7CYE1)](https://github.com/Fede2782/android_kernel_samsung_gts9fe): Community mirror used to cross-reference the 5G variant.
- [Linux Mainline](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/): Upstream tree snapshot pinned by hash in `fetch-sources.sh`.
- [AOSP Kernel Build Documentation](https://source.android.com/docs/setup/build/building-kernels).
- [Official Android Verified Boot / `avbtool`](https://android.googlesource.com/platform/external/avb/): Pinned locally from `android16-release` branch.
- [Official Magisk v30.7](https://github.com/topjohnwu/Magisk/releases/tag/v30.7): Source of `magiskboot-arm64` used solely for offline repackaging tests.

Downloaded archives and the extracted `avbtool.py` have their SHA-256 hashes pinned in `configs/toolchain-reference.sha256`; they are verified from the repository root before modifying or updating any host tool.

- [Android Common 13 / 5.15 Kernel Manifest](https://android.googlesource.com/kernel/manifest/+/refs/heads/common-android13-5.15/default.xml).
- [Linux Kernel Initramfs Documentation](https://docs.kernel.org/filesystems/ramfs-rootfs-initramfs.html).
- [Device Tree Overlay Notes](https://docs.kernel.org/devicetree/overlay-notes.html).
- [Devicetree Specifications](https://www.devicetree.org/specifications/).

## How to Cite Findings

Record repository, commit hash, and path. Example:

```text
Source: android_kernel_samsung_gts9fewifi
Commit: 9a752a83347461b3785711760ba925fcabea3071
Path: arch/arm64/boot/dts/exynos/s5e8835.dts
Node: /ufs@0x13500000
Observation: compatible samsung,exynos-ufs; address 0x13500000
```

Do not cite an isolated line from a decompiled DTS as an electrical specification. A rigorous finding combines source code, effective runtime DT, driver logs, and physical hardware verification.
