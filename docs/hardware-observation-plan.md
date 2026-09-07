# Hardware Observation Plan and First Boot Preparation

Date: 2026-08-24
Audited artifact: `artifacts/u11/x510xxsbdzb4-u11-clang21-20260823/kernel.config`
Phase: preparatory, **no flashing**

## 1. Kernel `.config` Audit

### Critical Options

| Config | U11 Value | Classification | Impact on M2 (first printk) / M3 (`/init`) |
|---|---|---|---|
| `CONFIG_PSTORE` | `y` | already active | Required to persist logs after panic/reboot; no effect on reaching `/init`. |
| `CONFIG_PSTORE_RAM` | `y` | already active | Enables ramoops if reserved region + correct cmdline present; key to capturing late failures even without console. |
| `CONFIG_USB_GADGET` | `y` | already active | Prerequisite for USB console; does not affect M2/M3 directly. |
| `CONFIG_USB_CONFIGFS` | `y` | already active | Interface needed to create serial gadget from initramfs. |
| `CONFIG_USB_CONFIGFS_SERIAL` | `y` | already active | Generic serial function available; ACM is also active. |
| `CONFIG_SERIAL_SAMSUNG` | `y` (+ console) | already active | Samsung UART driver; essential for physical console if it exists. |
| `CONFIG_SERIAL_EARLYCON` | `y` | already active | Messages before standard console; top M2 priority. |
| `CONFIG_EARLY_PRINTK` | absent (typical on modern arm64; earlycon is used) | not needed | Blocks nothing; `earlycon=` is the proper mechanism. |
| DRM core | `CONFIG_DRM=y`, DeCON/DSI/DPU/Samsung = `y/m` | already active | Not relevant to M2/M3; useful once shell/logs are available. |
| DRM specific panel | `DRM_PANEL_MCD_COMMON=m`; rest generic off | partially active | Post-M3 risk: if physical panel does not match, black screen but live system. Not initial priority. |
| `CONFIG_USB_DWC3_EXYNOS` | `=y` and also `=m` (apparent Kconfig contradiction) | review | Module must be present in usb-console initramfs; built-in preferred. Verify with `modules.builtin`. |
| Ramoops reserved region | not visible in config | required to activate (DT/cmdline) | Without reserved address/size, pstore RAM stores nothing. Offline action before flashing. |

### Summary

- **Already active:** full pstore, base ramoops, gadget/configfs/serial/ACM, Samsung serial + earlycon, Samsung DRM core.
- **Required to activate/prepare:** ramoops memory reservation in DT + cmdline parameters; explicit verification of DWC3-Exynos module/built-in status.
- **Not needed:** classic `CONFIG_EARLY_PRINTK` (obsolete on arm64).

## 2. Three Initramfs Profiles

All share static BusyBox 1.36.1 ARM64, current `/init`, and reproducible gzip/lz4 packaging. Documented as designs; not yet built.

### A) minimal

Objective: Maximum probability of executing `/init`.

Content:
- Static BusyBox + `/init` + `/etc/passwd`, `/etc/group`.
- Zero modules (`MODULES_MODE=none`).
- No USB gadget, no driver loading.
- Recommended cmdline:
  - `earlycon=exynos4210,mmio32,0x13800000`
  - `console=ttySAC0,115200n8`
  - `printk.devkmsg=on`
  - `panic_print=0x1f`
  - `panic_timeout=30`

Interpretation: If this profile fails to reach `/init`, the problem lies earlier (AVB/bootloader) or in the observability channel, not in drivers.

### B) debug

Objective: Maximize evidence upon any failure.

Adds relative to A:
- Maximum printk via cmdline: `loglevel=8 ignore_loglevel`.
- `pstore`/`ramoops` with reserved region defined in DT or `ramoops.mem_address=... ramoops.mem_size=... ramoops.record_size=... ramoops.console_size=...`.
- `crashkernel` NOT enabled (unnecessary for initial contact and adds risk).
- `softlockup_panic=1 hardlockup_panic=1 nmi_watchdog=1` optional if converting hangs to pstore records is desired.
- `panic_timeout=0` (no automatic reboot during attended operator trials).

Intended use: Second pass, once kernel boot is confirmed and capturing crash point is needed.

### C) usb-console

Objective: Shell over USB serial if kernel reaches point where DWC3 + configfs function.

Adds relative to A:
- U11 modules loaded via modprobe: `dwc3-exynos-usb` + `phy-exynos-usbdrd-super` (existing list in `configs/initramfs-modules-usb.conf`).
- ACM gadget activation (already implemented in `/init` under `gts9fe.usb_debug=1`).
- Cmdline: `gts9fe.usb_debug=1` + same parameters as minimal.

Success criterion: Host detects new `/dev/ttyUSB*` or `/dev/ttyACM*` port. If present without shell, issue is post-DWC3 but pre-userspace-visible.

## 3. Target Evidence and Interpretation

| Observable Result | Meaning | Next Decision |
|---|---|---|
| Zero UART bytes + host USB sees nothing new | Pre-kernel failure (AVB, bootloader, invalid image). Kernel likely never executed an instruction. | Return to AVB/signing/boot/init_boot format. Do not touch drivers or rootfs. |
| Zero UART bytes + host USB enumerates serial gadget | Kernel progressed far; only physical UART channel missing. | Continue M3/M4 via USB. UART becomes hardware/pinout issue, not boot blocker. |
| Partial UART bytes and hang | Early timer/PSCI/GIC/memory failure. | Compare selected DTBO, review earlycon and PSCI; consider JTAG. |
| Full UART log up to panic "no init found" | Kernel OK; initramfs invalid or corrupt. | Review cpio format, compression, size, and boot v4 metadata. |
| USB shell functional | M3 achieved. | Proceed to read-only UFS/rootfs, then screen (post-M3), not before. |
| Black screen but USB/UART live | DRM/panel not yet matched. | Expected outcome; does not constitute boot failure. |
| Reboot loop without log | Early panic with automatic reboot or firmware watchdog. | Repeat with debug profile and `panic_timeout=0`. |
| Complete silence, even host USB detects nothing | Probable bootloader rejection or unexpected hardware discrepancy. | Audit AVB/vbmeta and effective r00/r01/r04 overlay. |

## 4. USB Current Draw Interpretation

Host USB-C port provides three independent signals without opening tablet:

1. **Current drawn** (measurable with inline USB meter):
   - < ~20 mA constant: Likely nothing real started; may be awaiting negotiation or in silent download/recovery mode.
   - Sudden step to >100 mA sustained: Signal of real CPU activity (kernel executing code), even without enumeration.
   - Stable fluctuating current (~100–300 mA): Typical pattern of live kernel with active scheduler.
2. **USB enumeration**:
   - Samsung device appears (VID 0x04e8) → Bootloader communicating over USB (download mode or Odin-like).
   - Linux Gadget device appears (VID 0x1d6b, product "Tab S9 FE rescue") → Kernel reached DWC3 + userspace init. Direct M3 proof.
   - Nothing appears → Either bootloader did not enter transfer mode, or kernel did not reach USB.
3. **Port type / negotiation**:
   - If host reports "unknown device" or descriptor error → USB communication attempt occurred, partial failure.
   - If zero electrical transaction → Issue prior to USB, likely pre-kernel.

Rule: USB current draw is a statistical indicator, never deterministic proof. Only enumeration with correct VID/PID or a log constitutes strong proof.

## 5. USB-C Chain: Dependency Hierarchy

Without disassembling tablet, USB-C chain consists of three layers:

| Layer | Responsible | Observable From Host |
|---|---|---|
| Physical / CC / orientation | PMIC + Type-C controller + Samsung bootloader | Current negotiation, VBUS presence, cable detection/orientation |
| Bootloader / download mode | Samsung SBOOT/LK2 | VID 0x04e8 enumeration in Odin/Heimdall, response to proprietary protocol |
| Linux Kernel (DWC3 + gadget) | U11 kernel + initramfs + modules | VID 0x1d6b enumeration with serial/ACM gadget, appearance of `/dev/tty*` on host |

Practical conclusions:

- If device enters download mode and host detects it as Samsung, **bootloader and physical USB-C layer are functional**, independent of our kernel. This can be tested today safely without flashing.
- If kernel fails to reach gadget, whether failure is physical USB-C, bootloader, or kernel remains unknown; secondary evidence (UART, pstore) is required to discriminate.
- Serial function depends entirely on kernel; its appearance proves M3, not bootloader functionality.

## 6. Decision Tree Following First Attempt

```text
First attempt (minimal profile)
├── Does host detect Samsung gadget in download mode?
│   ├── Yes → bootloader OK, physical layer OK. Flash candidate and observe.
│   └── No → resolve download mode entry first. STOP.
│
├── After flashing, does host detect Linux gadget (0x1d6b)?
│   ├── Yes → kernel reached /init. Proceed to UFS/read-only tests.
│   └── No → proceed.
│
├── Are UART bytes observed?
│   ├── Yes, full log up to initramfs panic → fix format/init_boot.
│   ├── Yes, partial hang → review PSCI/timer/earlycon.
│   └── No bytes → continue.
│
├── Does USB current draw jump to active pattern (>100 mA sustained)?
│   ├── Yes → kernel likely alive, issue solely observability.
│   │        → repeat with usb-console.
│   └── No, low flat current → likely pre-kernel. Return to AVB/signing.
│
└── None of the above → repeat with debug profile + pstore.
    Extract pstore via recovery/ADB if stock Android boots again.
```

## 7. Fixed Rules for This Phase

- Single variable changed between trials.
Trial sheet mandatory prior to touching hardware (see `docs/12-first-test-preflight.md`).
- Timeout and abort conditions written prior to trial.
- No simultaneous modification of kernel + DTBO + vbmeta + rootfs.
- The verdict remains **NO-GO for flashing**; this phase only prepares instrumentation.
