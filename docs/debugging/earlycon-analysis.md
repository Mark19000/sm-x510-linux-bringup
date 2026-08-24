# Earlycon Analysis — SM-X510 U12/EZE4 (read-only audit)

## Executive summary

- Stock images provide **no earlycon activation**: `boot.img` and `init_boot.img` have empty cmdline fields; the effective stock kernel parameters come from the DT `chosen.bootargs`, which uses `console=ram` only.
- The Samsung Exynos earlycon driver is built into the U11 kernel (`CONFIG_SERIAL_SAMSUNG=y`) but the newer `exynos_tty.c` driver used on this platform registers **no `OF_EARLYCON_DECLARE`** — only the legacy Samsung driver does.
- Any injection point for `earlycon=` lives inside an AVB-signed partition (`vendor_boot.img` DT/bootconfig or `boot.img` cmdline), so enabling it requires unlocking the bootloader and regenerating/re-signing vbmeta with test keys or disabling verification flags.
- Without UART physical access, earlycon output would still require a serial receiver on some exposed pad — which this unit does not have confirmed. Therefore **earlycon alone does not solve observability without UART hardware**.

## Evidence found

| Location | Content | Verified |
|----------|---------|----------|
| `boot.img` header v4 cmdline | empty (`b''`) | ✅ parsed directly |
| `init_boot.img` header v4 cmdline | empty (`b''`); no kernel present | ✅ |
| `vendor_boot.img` header v4 cmdline | `"bootconfig loop.max_part=7"` | ✅ |
| `vendor_boot.img` bootconfig section size | 0 bytes (the 28-byte string observed previously was the vendor_ramdisk table padding area, not bootconfig) | ✅ corrected |
| DT `chosen.bootargs` | `console=ram printk.devkmsg=on arm64.nopauth arm64.nomte nokaslr kasan=off clocksource=arch_sys_counter clk_ignore_unused firmware_class.path=/vendor/firmware rcupdate.rcu_expedited=1 swiotlb=noforce loop.max_part=7 cgroup.memory=nokmem` | ✅ |
| DT `chosen.stdout-path` | **absent** | ✅ |
| `CONFIG_SERIAL_EARLYCON` | `y` in U11 build | ✅ |
| Legacy Samsung earlycon registrations | `s3c2410`, `s3c2412`, `s3c2440`, `s3c6400`, `s5pv210`, `exynos4210` compatibles in `drivers/tty/serial/samsung_tty.c` | ✅ |
| Platform driver `exynos_tty.c` compatible | `samsung,exynos-uart` — **no OF_EARLYCON_DECLARE** found | ✅ |

## What this means

### Where earlycon can be introduced

| Injection point | Feasible? | AVB impact |
|----------------|-----------|------------|
| `boot.img` cmdline field | Yes (field exists, currently empty) | Hash descriptor breaks → vbmeta must be re-signed or verification disabled |
| `vendor_boot.img` header cmdline | Yes (`"bootconfig loop.max_part=7"` present) | Same as above |
| `vendor_boot.img` DT `chosen.bootargs` | Yes (append `earlycon=…`) | Same as above |
| `vendor_boot.img` bootconfig section | Currently 0 bytes; adding content changes image → AVB impact | Same as above |
| `init_boot.img` | No relevant cmdline field; ramdisk-only | N/A |

### Format required

Per `Documentation/admin-guide/kernel-parameters.txt`:

```
exynos4210,<mmio-address>
```

The UART must already be configured by the bootloader; no baud options are supported by the legacy Samsung earlycon driver. For this SoC the debug UART base address is typically `0x13800000`, but that has not been confirmed from the EZE4 DT (no `stdout-path` exists).

The newer `exynos_tty.c` driver matching `samsung,exynos-uart` does **not** register an earlycon handler. Therefore `earlycon=samsung,…` will not match anything unless the legacy `samsung_tty.c` path is also compiled in (it is, via `CONFIG_SERIAL_SAMSUNG=y`), and even then the compatible strings registered are older ones (`exynos4210-uart`, etc.), not `samsung,exynos-uart`.

## Risks

1. **No physical UART**: even with earlycon active, there may be no accessible serial pin to capture output. This analysis cannot solve observation alone.
2. **AVB breakage is guaranteed** under LOCKED state for any of the touched partitions.
3. **Bootloader may append its own parameters** after those in the images — unknown whether it overrides or merges. Not verifiable locally.
4. **Clock gating**: Samsung bootloaders often leave UART gates enabled only when debug mode is active. If disabled before handoff, earlycon writes to a gated clock silently fail or hang.

## Hypotheses (unverified)

- H1: Samsung Download Mode or the normal bootloader appends extra kernel parameters at runtime beyond what is visible in the static images.
- H2: UART0 clock gate remains enabled during normal boot (some Samsung devices keep debug UART alive regardless).
- H3: A non-invasive mechanism exists (e.g., bootloader-reserved property or fuse) to enable UART debug without modifying images — unconfirmed.

## Recommended experiments (design only, no execution)

| # | Experiment | Purpose | Risk |
|---|-----------|---------|------|
| E1 | On a *separate unlocked test device* (or emulator), add `earlycon=exynos4210,0x13800000` to `chosen.bootargs`, rebuild vendor_boot with test-signed vbmeta, verify kernel reaches earlycon print | Confirm driver compatibility and base address | Requires unlock; medium |
| E2 | Capture `/proc/cmdline` on stock booted device (via ADB) | Determine whether bootloader appends parameters | None — passive read |
| E3 | Probe UART pads with logic analyzer during stock boot | Confirm whether bootloader emits anything on UART0 pre-kernel | Hardware access risk low but unit integrity risk nonzero |

## Documentation proposed

- This file: `docs/debugging/earlycon-analysis.md`.
- Cross-reference: `docs/boot-chain/minimal-modification-set.md` (Agent 3) for which partitions must change.
- Follow-up needed: confirm actual UART base address from EZE4 board documentation or live `/proc/iomem`.
