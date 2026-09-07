# 6. Bring-up Runbook

## Attempt Record Sheet

Create an entry for every hardware boot attempt:

```text
UTC Date/Time:
Model, CSC, Revision:
Stock Firmware and SHA-256:
Kernel Commit:
Project Commit:
Config SHA-256:
Image/DTB/DTBO/Initramfs SHA-256:
Single Variable Changed in this Attempt:
Result / Milestone Reached:
Full Console/Kernel Log:
Next Hypothesis:
```

Without this discipline, two separate images named `boot.img` become indistinguishable and boot defects appear erratic.

## Phase A: Non-Destructive Offline Analysis

1. Run `./scripts/collect-device.sh` on running stock Android.
2. Extract the exact matching stock AP package.
3. Compare source DT, stock DT, and live runtime DT.
4. Record partition sizes and cryptographic digests of all images.
5. Compile kernel and initramfs, verifying architecture and entry points.

## Phase B: Console Output Before Peripherals

An observable console is the essential force multiplier. Prioritize in this order:

1. Framebuffer / display console pre-initialized by the bootloader, if preserved across handoff;
2. UART only after identifying pinmux and signaling voltage levels (typically 1.8 V; never assume 3.3 V or 5 V tolerance);
3. USB ACM console via USB gadget mode;
4. `pstore`/ramoops or vendor panic-logging buffer (`sec_debug`/last_kmsg) for non-interactive post-mortem debugging.

Do not configure `earlycon` with a guessed memory address. Downstream UART0 resides at `0x13800000`, but is disabled in the base tree and depends on specific parent clocks and pinmux routing. First verify the effective runtime Device Tree.

## Phase C: First Boot Execution

Classify where execution halts:

| Symptom | Probable Cause |
|---|---|
| Bootloader rejects image immediately | Boot image header, signing / AVB descriptor, rollback counter, partition overflow |
| Immediate reboot before any output | Incompatible Device Tree, early CPU exception, hardware watchdog reset |
| Kernel prints initial banner then hangs at SMP bringup | Clocks, PMU, PSCI firmware calls, GIC interrupt routing |
| `No working init found` | Initramfs format, wrong architecture, file permissions, bad interpreter |
| `/init` executes but `/dev` is unpopulated | `CONFIG_DEVTMPFS` missing or failed devtmpfs mount |
| Rescue shell runs but UFS storage is absent | Missing modular driver, PHY initialization, calibration tables, clocks, or IOMMU |

## Phase D: Storage Discovery

Once UFS enumerates:

```sh
dmesg | grep -i -E 'ufs|scsi|sd '
cat /proc/partitions
blkid
mkdir -p /mnt/test
mount -o ro /dev/device-node /mnt/test
```

Never execute `fsck`, `mkfs`, or `mount -o rw` on Android partitions during bring-up.

## Phase E: Peripheral Integration

Integrate subsystems one at a time: USB, display, touchscreen, Wi-Fi, audio, sensors, and finally power management / battery charging. For each subsystem, record:

- Device Tree node and board revision;
- Clocks, reset lines, regulators, and GPIO pins used;
- Driver probe logs and deferred probe notices;
- Kernel configuration deltas;
- Positive functional test and suspend/resume validation.

A driver that successfully probes but leaves power rails permanently asserted is not production-ready.
