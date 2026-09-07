# 1. Boot Architecture

## The Components

A PC discovers most hardware via enumerable buses. An embedded SoC does not: Linux requires a Device Tree describing addresses, interrupts, clocks, GPIOs, and inter-device relationships.

In this tablet, in simplified terms:

```text
Boot ROM -> Samsung bootloaders -> AVB verification
                                   |
                                   +-> boot: kernel/ramdisk per header specification
                                   +-> vendor_boot: vendor ramdisk and/or DTB
                                   +-> dtbo: model and hardware revision overlays
                                   |
                                   `-> kernel + effective DT + initramfs
                                                      |
                                                      `-> /init (PID 1)
```

The published configuration specifies Android boot image header v4, builds `Image`, `s5e8835.dtb`, and `dtbo.img`, and supports LZ4 ramdisks. These parameters must not be copied blindly: `extract-stock.sh` allows inspecting the exact target firmware.

## DTB vs DTBO

- **DTS/DTSI**: Human-readable text source.
- **DTB**: Binary compiled representation handed to the kernel.
- **DTBO**: One or more binary overlays that modify the base tree.
- **Effective DT**: Final resulting tree actually seen by the kernel after bootloader overlay application.

The Samsung repository contains a large `s5e8835.dts`. The X510 Wi-Fi adds three overlays (r00, r01, and r04) and the X516 5G reference adds four (adding r02). These are decompiled sources: they utilize numeric phandles, non-normalized node names, and private vendor properties. They serve as hardware documentation, not as mainline-ready Device Trees.

## Downstream Kernel vs Mainline

**Downstream** is the 5.15 kernel modified by Android/Samsung. It contains the proprietary drivers necessary for early bring-up and is the realistic path to the first shell. **Mainline** is the upstream Linux tree. It offers cleaner maintainability, but in the analyzed snapshot contains no S5E8835 / Exynos 1380 platform support.

The strategy is deliberately incremental:

1. Boot downstream with a diagnostic Linux initramfs;
2. Identify every dependency and firmware blob;
3. Write upstream bindings and drivers subsystem by subsystem;
4. Create a clean mainline DTS only once basic clocks, pinctrl, and interrupts have upstream driver support;
5. Maintain recoverable Android capability while replacing hardware drivers block by block.

## What Happens When `/init` Executes

The kernel unpacks a `cpio` archive into `rootfs`. If `/init` is present, it executes as PID 1. That program mounts `/proc`, `/sys`, and `/dev`, discovers devices, and optionally mounts a persistent root filesystem and invokes `switch_root`. For milestone M3, a full Linux distribution is not required: static BusyBox and the `initramfs/rootfs/init` script are sufficient to prove that kernel execution, memory management, Device Tree bindings, and early userspace progressed far enough.
