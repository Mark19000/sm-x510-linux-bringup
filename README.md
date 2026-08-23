# Samsung Galaxy Tab S9 FE Linux Bring-Up

Port of Linux to the Exynos S5E8835 SoC in the Samsung Galaxy Tab S9 FE Wi-Fi (SM-X510), documented as a kernel bring-up learning project.

## Objective

Reach the first observable boot of the downstream U11 kernel (Android 16) on U12/EZE4 hardware, prioritising reproducibility, traceability, and safety before touching the device.

## Hardware

- Samsung Galaxy Tab S9 FE Wi-Fi (SM-X510)
- SoC: Exynos S5E8835
- Stock firmware: X510XXUCEZE4 (Android 16, bootloader U12)
- Kernel source available: OSRC X510XXSBDZB4 (U11, best available reference)

## Boot chain

```
Samsung bootloader (U-Boot derivative)
  |
  +-- AVB verification (vbmeta -> boot, init_boot, vendor_boot, dtbo)
  |
  +-- Kernel image (Image) + Device Tree (DTB + DTBO overlay)
  |
  +-- init_boot ramdisk (initramfs: /init as PID 1)
  |
  +-- vendor_boot ramdisk (vendor modules + DTB copy)
       |
       v
   Linux userspace (/init -> shell or real init)
```

The goal is to replace the kernel and initramfs while keeping the rest of the
chain intact. AVB must be resolved through a legitimate unlock before the
device will accept modified partitions.

## Methodology

- Offline auditable pipeline in a Lima ARM64 VM
- Two clean builds verified byte-for-byte identical
- Compiled DTB semantic audit U11↔EZE4
- Module audit: 282 U11 modules vs 281 stock EZE4 vendor_boot modules
- Physical write gate: NO-GO until all safety conditions are met

## Results

| Metric | Status |
|---|---|
| Binary reproducibility | PASS |
| Preflight offline payload M3 | READY |
| Initramfs minimal fits init_boot | Yes (~1.8 MB margin) |
| Host test suite | 90/90 OK |
| Hardware observation | Pending |
| Physical write | NO-GO |

## Failures encountered and lessons learned

| Problem | Root cause | Lesson |
|---|---|---|
| Physical paths leaked into module .rodata via ThinLTO | O= placed as sibling of source tree instead of direct child | Kbuild must set srctree=.. so Clang receives relative paths |
| Different build IDs in Image between runs | VDSO and kernel build IDs not pinned | Explicit build ID patch required for full reproducibility |
| Disk space exhaustion in VM | LTO/BTF builds consume ~8 GB per run | Check df -h before every run |
| Patch apply failure on retry | Patches already applied from previous attempt | Reverse patches with git apply -R before re-running |
| Tar extraction structure mismatch | Samsung Kernel.tar.gz has no root subdirectory | Always verify post-extraction layout |

## Project structure

```
├── configs/       Build recipes, Kconfig fragments, hash manifests
├── docs/          Numbered pedagogical documentation
├── patches/       10 kernel patches (Clang 21 compatibility, early userspace)
├── reports/       Audit reports and generated evidence
├── scripts/       Complete offline pipeline with safety guards
├── tools/         DTB semantic diff, module audit, reproducibility compare
├── tests/         90 host-only tests
├── initramfs/     Rescue initramfs source scripts
└── lima/          VM configuration
```

## Why these patches exist

Samsung's downstream kernel targets Android's Clang toolchain and build system.
When compiled with modern standalone Clang 21 and standard Kbuild, ten issues
surface: C declarations valid under older standards are rejected, return types
on vendor drivers don't match their prototypes, devfreq and GPU QoS helpers
have broken fallback logic, USB Type-C compares against the wrong enum, the
Novatek touchscreen driver returns an invalid IRQ status, and the build system
embeds non-reproducible VDSO/kernel build IDs into the binary.

Each patch fixes one of these problems minimally. Together they make the kernel
compile cleanly with Clang 21 and produce bit-identical output across builds.
The early-userspace patch enables CONFIG_DEVTMPFS, virtual terminals, and
initrd support that Android deliberately disables in its defconfig but that are
required for a standalone Linux initramfs to reach /init.

## Usage

```sh
make check        # verify host dependencies
make test         # run 90-test suite + shell syntax validation
make u11-offline  # run full offline audit: initramfs + DTB + modules + preflight
```

All commands are read-only. No script generates flashable images or writes to hardware.

## Safety model

This project explicitly does **not** produce flashable images. Every build script carries a physical write gate (`NO-GO`) that prevents any interaction with the target device. The goal is laboratory analysis only.

## Next steps

1. Validate UART or USB console access on hardware
2. Resolve AVB through legitimate bootloader unlock
3. Execute M2/M3 milestone with minimal initramfs
4. Obtain exact EZE4 OSRC when Samsung publishes it

## License

MIT — see [LICENSE](LICENSE).

Samsung OSRC kernel sources are proprietary and are **not** included in this repository. The patches, tools, documentation, and pipeline scripts are original work.
