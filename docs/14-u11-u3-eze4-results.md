# 14. U3 → U11 → EZE4 Results and Decision for M2/M3

This chapter provides the auditable cutoff as of August 23, 2026. Downloaded
packages were analyzed, the U11 source was composed on ext4, compared with U3
and with device trees extracted from EZE4, and a full U11 kernel was built.
Nothing was written to the tablet, and U3 remains the canonical source for the
existing pipeline.

## Exact Delivery Inventory

Files matching `.part`, empty files, and placeholders were ignored. The three
complete ZIPs related to SM-X510 found in `Downloads` were:

| file | bytes | SHA-256 | identity |
|---|---:|---|---|
| `SM-X510.zip` | 285055969 | `3320da592f76b703531eee8c04ef9d872f7254cd906127dd2feda79c310e9928` | Android 16 OSRC wrapper |
| `SM-X510_EUR_16_Opensource.zip` | 284751324 | `18596f241925b729f48638a1750d3d71e3370d9056b2c9c4373a7cc04c1d9791` | OSRC base; identical copy to the one included in wrapper |
| `SAMFW.COM_SM-X510_EUX_X510XXUCEZE4_fac.zip` | 10717872605 | `45a450875ce753e74d8183aa085837ada91cabe2832d9725a1567aa29b01d375` | EZE4 stock firmware, Android 16, U12/EUX |

The wrapper also contains these two independent deliveries:

| member | bytes | SHA-256 | function |
|---|---:|---|---|
| `SM-X510_EUR_16_Opensource.zip` | 284751324 | `18596f241925b729f48638a1750d3d71e3370d9056b2c9c4373a7cc04c1d9791` | `X510XXU8DYJ4` base |
| `SM-X510_EUR_16_Opensource_X510XXSBDZB4.zip` | 237796 | `c0e3fb5bdbd6447669dd57e43d9817838c24ce0f08e6f0293f3cc98e1cefc5ad` | `X510XXSBDZB4` exact supplement |

The base contains `Kernel.tar.gz` (254699729 bytes, SHA-256
`064746422c2c1ba83f3c245e137f6c0a105a19280d10ece48987cac5e9d26983`)
and `Platform.tar.gz` (37445621 bytes, SHA-256
`68929260cd0f996dc59121186ea4c87fe6ca762e849c661dce2eacfd3184d567`).
The kernel tar has 80,777 regular files and 39 safe internal symlinks;
the Platform tar has 13,275 regular files. Platform does not participate in
the kernel build.

## Why This Is Indeed the Corresponding U11 Source

Identification does not depend on the external filename:

1. The supplement README explicitly instructs downloading `X510XXU8DYJ4`
   first and then updating it with `X510XXSBDZB4`.
2. The internal root is named `SM-X510_EUR_16_XX_X510XXSBDZB4/Kernel`.
3. The Platform README declares Android 16.0.
4. The composite Makefile declares Linux 5.15.180.
5. The recipe selects `s5e8835-gts9fewifixx_defconfig`, `TARGET_SOC=s5e8835`,
   `PLATFORM_VERSION=13`, `LLVM=1`, and Clang `r450784d`.
6. `B` in `X510XXSBDZB4` is binary revision U11.

The supplement contains 13 kernel files; three battery DTSIs are identical
to the base and ten actually change. Changes are concentrated in defconfig,
HID/accessories, USB restrictions, F2FS, `/proc` integrity, and DDAR cleanup.
It does not include board or SoC DTS/DTSI: those come from the U8 base,
an important detail when attributing DT proximity to "U11".

Therefore, **we do have the source corresponding to X510XXSBDZB4/U11/Android 16**,
composed as U8 base plus U11 supplement. Samsung did not include `.git`,
a commit hash, or an upstream tag; that information is genuinely unavailable
and must not be invented.

On APFS, the full kernel is not extracted because the tar contains names that
collide on a case-insensitive filesystem. The full copy lives on ext4 in
the VM. On the host, only packages, manifests, and reports under
`sources/osrc-releases/x510xxsbdzb4-u11-android16` and `artifacts/u11` are
kept; U3, `sources/wifi-kernel`, and `artifacts/stock` remain untouched.

## Kernel and Configuration Distance

| stage | kernel | demonstrable base/commit | Android / binary |
|---|---|---|---|
| U3 `X510XXU3BXDG` | 5.15.123 | commit `9a752a83347461b3785711760ba925fcabea3071` | Android 14 / U3 |
| U11 `X510XXSBDZB4` | 5.15.180 | OSRC archive without Git; delivery base `X510XXU8DYJ4` | Android 16 / U11 |
| stock `X510XXUCEZE4` | 5.15.189-android13-3-33478785 | stock Kbuild string; exact source requested and pending | Android 16 / U12 |

U11 reduces the known jump from 66 kernel revisions to just 9. Among the
defconfig changes U3→U11, notable items are SCMI virtio, lazy RCU, an
additional ARM64 mitigation, CUBIC instead of BIC, NTFS3, the ashmem/memfd
shim, HDM as a module, and the change of SCSC firmware path from
`/vendor/etc/wifi` to `/vendor/firmware/wifi`. `PABLO_OBTE_SUPPORT` changes
from module to disabled.

Samsung's U11 defconfig still lacks `CONFIG_FHANDLE`, devtmpfs, VT, and the
tmpfs ACL/xattrs required by our early userspace. Patch 0001 remains necessary
for M3. The final config contains 312 `=m` symbols; 282 `.ko` modules were built
and installed, identical to the U3 trial, although composition is not identical
(`PABLO_OBTE_SUPPORT` disappears, among other changes).

## DTS/DTSI and Drivers

The raw inventory counts 3,200 DTS/DTSI files in U3 and 3,217 in U11; 228 paths
change. In drivers, there are 37,094 paths in U3 and 37,155 in U11: 3,721 change,
18 exist only in U3, and 79 exist only in U11. These are path metrics, not 3,721
tablet incompatibilities. The reproducible breakdown by subsystem is in
`reports/generated/u11-osrc/subsystems.md`.

| subsystem | changed paths | only U3 | only U11 |
|---|---:|---:|---:|
| DT S5E8835/X510 | 3 | 0 | 0 |
| PSCI/GIC/timers | 28 | 0 | 0 |
| CMU/clocks | 1 | 0 | 0 |
| pinctrl/GPIO/EINT | 31 | 0 | 0 |
| PMU/ACPM/power domains | 0 | 0 | 0 |
| SysMMU/IOMMU | 0 | 0 | 0 |
| UFS/PHY/FMP | 12 | 0 | 0 |
| USB/DWC3/Type-C | 164 | 1 | 0 |
| display/DSIM/panel | 43 | 0 | 1 |
| touchscreen/Wacom/pogo | 14 | 0 | 0 |
| GPU/Mali | 11 | 0 | 0 |
| Wi-Fi/BT SCSC | 45 | 0 | 0 |
| battery/PMIC/charging | 29 | 0 | 0 |
| thermal | 0 | 0 | 0 |
| build/toolchain | 7 | 0 | 0 |

These figures classify paths by name and presence. For example, "164 USB"
includes generic backports under `drivers/usb`; it does not mean there are
164 changes specific to the tablet's USB controller.

The material base DT changes U3→U11 most relevant to boot are:

- a `wdtmsg` reservation at `0x08adb11000`, size `0x1000`;
- GPIO/EINT bank `gph1` and its interrupts 0x4f–0x52;
- `snps,usb2-lpm-disable` in DWC3;
- `dsim,disable-shdw-vss-updt = <1>` in DSIM;
- clock and `clock-names = "gpu_clock"` in Mali.

In the r04 overlay, there are 17 material semantic differences: new keyboards and
touchpad, IMX355 pinning/preload, thermal zone names, `pktproc` policy, and battery
capacity 10090→8000. These are peripherals and product policy; they do not appear
on their own to block the first kernel message.

For PSCI/GIC/timers, CMU, pinctrl, UFS/PHY/FMP, USB/Type-C, display/panel,
input/Wacom, GPU, SCSC, battery/PMIC/charging, and thermal, the report separates
modified paths and enables auditing them without mistaking a generic Linux
backport for an X510-specific change. No path changes appeared under the specific
patterns for PMU/ACPM/power domains, SysMMU/IOMMU, or thermal; this does not prove
internal identity across all their includes.

## What Portion of U3→EZE4 Was Already Present in U11

Stock mapping is r00→overlay-00, r01→overlay-01, and r04→overlay-02.
Semantic comparison of r04 U11→EZE4 finds **zero material differences** across
1,215 nodes, but leaves 207 external references unresolved: its correct status
is `INCONCLUSIVE`, not "identical". In the base DT U11→EZE4, both have 1,493 nodes.
Comparing only source DTS showed one difference (`/mfc debug_mode`, from 1 to 0),
but that was insufficient: comparing the **already compiled DTBs** reveals four
differences and leaves 14 unresolved references:

- two `cpus` string-lists in `/ems/pe-list` are encoded differently;
- `/mfc debug_mode` changes from 1 to 0;
- SCSC `cpu_table_rps` changes from two strings to four.

Octal escapes in Samsung's DTS explain why the source diff missed the three
string changes. The reproducible recipe is `make u11-dtb-audit` and the evidence
resides in `reports/generated/u11-dtb-binary/`.

Limited but useful conclusion: all material changes observed in the overlay
U3→EZE4 are already present in U11, and the U11 base DT remains very close to
the EZE4 binary. The four compiled differences affect EMS, MFC, and SCSC and do
not lie on the minimal path to `/init`, but they may matter after boot. Massive
phandle renumbering U3→U11 is not in itself a hardware change. We cannot conclude
complete equivalence until references are resolved or the exact EZE4 source is received.

## Compilation and Provoked Errors

The nine current patches were applied individually to the U11 composite. All nine
apply textually. A clean build with Clang 21 first uncovered two declaration
errors in the EMS scheduler and KVM, covered by 0002. Each relevant patch was
then removed and the affected unit recompiled:

| without patch | reproduced failure on U11 + Clang 21 |
|---|---|
| 0002 | implicit-int in EMS and uninitialized `clidr` pointer in KVM |
| 0003 | implicit-int in `exynos-devfreq.h` |
| 0004 | uninitialized name in exynos-cpupm |
| 0005 | implicit-int in Mali QoS |
| 0006 | uninitialized buffer in exynos-devfreq |
| 0008 | uninitialized value in charger and forbidden FPSIMD in `sec_debug_test` |
| 0009 | invalid enum conversion to `irqreturn_t` |
| 0010 | comparison between distinct enums in Type-C |

0001 was justified by defconfig, not by a compiler error. With all nine patches,
`Image`, DTB, r00/r01/r04, LTO/BTF, modules, and `modules_install` finished with
exit code 0 in 58:08, using a maximum of 6,661,420 KiB. The build used
Clang 21.1.8 ARM64 because the official r450784d binary is x86-64 and does not
run natively in this ARM64 VM. This is a strong proof of compilability, not a
binary reproduction of Samsung.

Non-fatal diagnostics remain that should not be obscured: five LLD warnings
for large stack frames in nanohub/sec_debug, and messages from kperfmon because
the isolated OSRC tree does not include `aprotoc` from the Android platform;
its rule generates the dummy replacement and the build proceeds. There were no
`error:` lines in the full patched build.

Binaries and logs are in `artifacts/u11/x510xxsbdzb4-u11-clang21-20260823`.
Two successive LTO link runs produced `Image` with differing SHA-256 hashes,
although DTB and DTBO remained stable; the cause of non-reproducibility must be
pinned down before demanding identical binary hashes.

## U3→U11 Migration Plan

U11 is clearly a superior engineering baseline, but it does not yet become
canonical. Migration should proceed as a new variant:

1. Maintain U3, the U11 composite, stock U12, and future EZE4 source across
   four distinct paths and artifact namespaces.
2. Reapply all nine patches. None disappear in the Clang 21 pipeline;
   0001 is functional and 0008 also reduces crash surface. Rewrite the
   "Android 14" description in 0002 and review compatibility patches with
   r450784d before declaring them universal.
3. Reuse safe extraction, Lima, inventories, DT analysis, DTBO builder, and
   initramfs without changes. Adapt `build-downstream.sh` to accept archive
   provenance without a Git commit and to publish only under `u11/`; today
   it is deliberately anchored to U3/EZE4 and must continue blocking.
4. Compare `vendor_boot` module order, SCSC firmware, and initramfs dependencies
   before packaging; do not mix U3 modules with a U11 kernel.
5. When EZE4 OSRC arrives, repeat composition, semantic diff, config, build,
   and negative tests; do not apply the U11 overlay on top of EZE4.

## Effect on M2 and M3

For **M2, first kernel message**, technical confidence rises from low to
moderate-high: we have a buildable Android 16 base, only nine revisions below
stock, and a DT almost matching in what is observable. It does not rise to
"ready to flash": exact EZE4 source, observable console path, selected physical
revision, unlock/AVB, and anti-rollback verification are still missing.

For **M3, `/init` as PID 1**, confidence rises to moderate. The patched U11
kernel provides initrd/devtmpfs/VT/FHANDLE/tmpfs, and our initramfs is already
reproducible. These remain dependent on M2, final boot layout and size, correct
DTBO, AVB, and the module and firmware set/ordering. The conclusion is that U11
eliminates much of the source/DT uncertainty; it does not eliminate device boot
contract uncertainty.

Therefore, the next step remains offline: integrate U11 as a non-canonical
variant and await the EZE4 OSRC response. Do not disassemble, do not flash,
and do not downgrade U12→U11.
