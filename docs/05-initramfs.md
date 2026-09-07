# 5. Building and Understanding the Initramfs

## Purpose

The initramfs is a small root filesystem that the kernel unpacks into RAM before accessing Android partitions or a regular Linux distribution. Linux executes `/init` as PID 1. This allows attempting `kernel -> /init -> shell` without writing to UFS, without systemd, and without depending on a persistent root filesystem.

Our `/init` script mounts `/proc`, `/sys`, `/dev`, and `/run`, prints diagnostic information, loads only explicitly declared modules, and drops to a rescue shell. Any root device specified via `gts9fe.root=` is strictly mounted read-only.

## Static ARM64 BusyBox

Inside Linux / Lima:

```sh
./scripts/build-busybox.sh
file artifacts/busybox/busybox
cat artifacts/busybox/SOURCE_COMMIT
(cd artifacts/busybox && sha256sum -c SHA256SUMS)
```

The recipe pins BusyBox 1.36.1 to commit `1a64f6a20aaf6ea4dbba68bbfa8cc1ab7e5c57c4`, enables only 27 essential applets, and validates each option. This avoids two previously encountered defects: `tc` fails compilation against modern headers due to removed UAPI CBQ definitions, and `allnoconfig` in this version silently ignored boolean flags in miniconfig fragments.

The tested binary is AArch64, static, and measures 1,253,440 bytes. A dynamically linked BusyBox would fail due to missing dynamic linkers/libraries; an x86_64 binary would trigger `Exec format error`.

## Reference U3 Module Profiles

The safe default profile copies no kernel modules:

```sh
DEVICE_VARIANT=wifi MODULES_MODE=none \
  INITRAMFS_OUT="$PWD/artifacts/initramfs/wifi" \
  ./scripts/build-initramfs.sh
```

Paths matching `artifacts/initramfs/wifi*` in this chapter belong to the U3 kernel. U11 profiles, sizing margins, and safety guards are documented separately in [chapter 15](15-pipeline-u11-offline.md).

Available profiles:

| Profile | Contents | Purpose |
|---|---|---|
| `none` | BusyBox and `/init` only | First boot attempt with maximum headroom to fit |
| `deps` | Dependency closure of requested module list | Reach a specific modular driver |
| `all` | All installed kernel modules | Offline diagnostics; typically exceeds partition size |

To stage downstream UFS drivers:

```sh
DEVICE_VARIANT=wifi MODULES_MODE=deps \
  MODULES_ROOT="$PWD/artifacts/kernel/wifi/reference-dist/modules-root/lib/modules" \
  MODULES_LIST="$PWD/configs/initramfs-modules.conf" \
  INITRAMFS_OUT="$PWD/artifacts/initramfs/wifi-ufs" \
  ./scripts/build-initramfs.sh
```

The configuration file requests `ufs-exynos-core`; `modprobe --show-depends` computes the genuine dependency closure, copies 28 modules matching the same `kernelrelease`, regenerates `modules.dep`, and populates the autoload list read by `/init` at `/etc/gts9fe-modules`. Do not copy `.ko` files manually: manual staging risks omitting dependencies or mixing modules built against different kernel trees.

For USB ACM diagnostics, a separate profile exists:

```sh
DEVICE_VARIANT=wifi MODULES_MODE=deps \
  MODULES_ROOT="$PWD/artifacts/kernel/wifi/reference-dist/modules-root/lib/modules" \
  MODULES_LIST="$PWD/configs/initramfs-modules-usb.conf" \
  INITRAMFS_OUT="$PWD/artifacts/initramfs/wifi-usb" \
  ./scripts/build-initramfs.sh
```

The dependency closure for `phy-exynos-usbdrd-super` and `dwc3-exynos-usb` pulls in 45 modules. This serves as dependency evidence, not as a flashable candidate: its LZ4 payload exceeds the stock ramdisk budget. The subsequent hypothesis is to build essential glue/PHY drivers directly into `Image`, measure size growth, and re-evaluate `boot` partition capacity.

## Outputs and Reproducibility

Each profile generates:

- `gts9fe-initramfs.cpio`, uncompressed and easily inspected;
- `gts9fe-initramfs.cpio.gz`, timestamp-stripped gzip;
- `gts9fe-initramfs.cpio.lz4`, if `lz4` is installed, formatted using legacy frame format matching stock images;
- `SHA256SUMS`.

The build script sorts directory entries and normalizes uid, gid, and mtime. Two runs with identical inputs produced bit-for-bit identical archives. Measured payload sizes:

| Profile | CPIO | Legacy LZ4 | Margin Relative to Stock Ramdisk (2,486,802 B) |
|---|---:|---:|---:|
| Minimal (`none`) | 1,266,176 B | 690,117 B | +1,796,685 B headroom |
| UFS (`deps`) | 6,589,952 B | 2,124,194 B | +362,608 B headroom |
| USB (`deps`) | 10,065,920 B | 3,036,866 B | **exceeds by 550,064 B** |

The headroom metric compares compressed payload bytes; it does not authorize flashing. The final partition image includes headers, alignment padding, and AVB footers, and the UFS profile leaves very tight headroom for extra userspace tools.

Verify and inspect:

```sh
(cd artifacts/initramfs/wifi && sha256sum -c SHA256SUMS)
cpio -it < artifacts/initramfs/wifi/gts9fe-initramfs.cpio
cpio -it < artifacts/initramfs/wifi-ufs/gts9fe-initramfs.cpio | \
  grep 'lib/modules/.*\.ko$'
```

## Command-Line Parameters Understood by `/init`

- No parameters: drops to a shell on the console opened by the kernel;
- `gts9fe.usb_debug=1`: attempts to configure a USB ACM gadget and opens a shell on `/dev/ttyGS0`; requires Exynos glue, PHY, DWC3, and ConfigFS operational;
- `gts9fe.root=/dev/...`: mounts the root device **strictly read-only** under `/newroot` and remains in rescue mode;
- `gts9fe.switch_root=1`: permits switching root only when a root filesystem is mounted and `/newroot/sbin/init` is executable. Rejected if a USB debug shell was also requested.

Do not use `gts9fe.root` before milestone M5, nor `gts9fe.switch_root=1` during initial storage tests. `/dev/sdX` node assignments can shift across boots; first record partition UUIDs and partition tables.

## Requirements Built In-Tree (`=y`)

Everything required before loading modules must be built into `Image`: initrd support, devtmpfs, console drivers, and core block infrastructure. The compiled configuration confirms `CONFIG_BLK_DEV_INITRD=y`, `CONFIG_DEVTMPFS=y`, `CONFIG_DEVTMPFS_MOUNT=y`, Samsung serial console, DWC3, and ConfigFS/ACM USB gadget. The Exynos UFS driver is modular in this tree, which is why the `deps` profile exists.

## First Boot Diagnostics

Milestone M3 is demonstrated only if a physical console displays output resembling:

```text
[gts9fe-init] starting early userspace
[gts9fe-init] kernel: Linux ... aarch64
[gts9fe-init] cmdline: ...
[gts9fe-init] rescue shell. Use dmesg, cat /proc/iomem and ls /sys.
```

If `No working init found` appears, verify that `/init` is permissions `0755`, begins with `#!/bin/busybox sh`, and that `/bin/busybox` is a static AArch64 executable. If `modprobe` fails, record the exact module name, `uname -r`, `modules.dep`, and symbol/version error strings; do not attempt to resolve errors by loading modules compiled against a different kernel tree.
