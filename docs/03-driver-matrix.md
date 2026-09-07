# 3. Driver Matrix: Android/Downstream vs Linux Mainline

> In this checkout `docs/03-comparacion-drivers.md` does not exist; the canonical document is this `docs/03-driver-matrix.md`. The comprehensive matrix and reproducible searches reside in [`reports/generated/wifi/driver-matrix.md`](../reports/generated/wifi/driver-matrix.md).

## Identity and Methodology

This comparison utilizes mainline snapshot `26260251022f` (2026-08-21), downstream X510 U3 `9a752a833474` (X510XXU3BXDG, 5.15.123), and stock EZE4 DT extracted from `vendor_boot`/`dtbo`. Downstream source is a U3 reference, not the exact source for `X510XXUCEZE4`; the declared target is `SM-X510` Wi-Fi (`configs/target-sm-x510.env:3-7`, `sources/README.md:7-10`).

"Exact" signifies that mainline contains the identical string in an `of_device_id` table or binding. "Family" indicates related code that still requires S5E8835 platform data, clocks, pinctrl, and validation. Textual matches never prove electrical or functional compatibility. The mainline checkout is sparse; content searches were restricted to present files (`rg`), and path presence/absence was checked against `git ls-tree` where applicable.

## Subsystem Summary

| Subsystem | Observed Downstream DT/Driver | Local Mainline Support | Work / Blocker | Priority |
|---|---|---|---|---:|
| CPU, PSCI, GIC, timer, DMA | `arm,psci-1.0`, `arm,gic-400`, `arm,armv8-timer`, `arm,pl330` | exact / generic | Validate IRQs, topology, and clocks | 1 |
| UART | `samsung,exynos-uart` + USI v2 | Samsung family; no S5E8835 | S5E8835 platform data, pinmux, clocks, earlycon; stock UART0 is disabled | 1 |
| HSI2C / USI | `samsung,exynos5-hsi2c` | Exact string; USI only other families | Validate USI variant, FIFO, IRQ, clocks, and pinctrl | 2 |
| SPI / PWM | `samsung,exynos-spi`, `samsung,s3c6400-pwm` | SPI Exynos850 family; PWM binding exact, driver outside sparse checkout | Add S5E8835 data, prescalers, and DMA; do not confuse PWM timer with provider | 2 |
| Clocks / CMU | `samsung,s5e8835-clock`, private CAL/ACPM | No S5E8835 support | Port CMU by domain, resets, and parent sources | 1 |
| Pinctrl / GPIO / EINT | Six `samsung,s5e8835-pinctrl` nodes | Exynos family; no S5E8835 | Bank tables, EINT/wakeup, and pull configs per hw-rev | 1 |
| PMU / ACPM / power domains | `samsung,exynos-pmu`, `samsung,exynos-pd` | PMU from other families; no S5E8835 `exynos-pd` | Minimal PMU/ACPM and power domains before UFS/USB/DPU/GPU | 1 |
| IOMMU | `samsung,sysmmu-v8` | `samsung,exynos-sysmmu` family only | Port v8 before DPU, cameras, and GPU | 2 |
| UFS | `samsung,exynos-ufs`, Samsung FMP/PHY/calibration | Exynos core for Exynos7/AutoV9/GS101; no S5E8835 | PHY, calibration, clocks, reset, PD, SysMMU; begin read-only | 2 |
| USB DWC3 | `synopsys,dwc3` + `samsung,exynos-dwusb` | Core exact; glue family only | S5E8835 glue, clocks, and role switching | 2 |
| USB PHY | `samsung,exynos-usbdrd-phy` | Exynos5 family; no S5E8835 string | USB2/USB3, calibration/OTP, Type-C, and PMU | 2 |
| Display DPU | `samsung,exynos-decon/dpp/dsim` | Legacy Exynos DRM/DSI; no S5E8835 | Major port: atomic modesetting, SysMMU, CMU, DSIM, and MIPI PHY | 3 |
| LCD Panel | Candidates HX83102J BOE / NT36523N CSOT; private `samsung,panel-drv` | Families HX83102 and NT36523, other panels | Select via overlay/ID; verify power sequences, timings, regulators, and backlight | 3 |
| GPU | Downstream `arm,mali`; variant not inferred from `compatible` | Panfrost present in Git tree, no local verified `arm,mali`/S5E8835 | PD, clocks, reset, SysMMU, and firmware | 4 |
| Touchscreen | Proprietary Novatek/Himax: `nvt_ts_spi`, `himax,hxcommon` | Other NT/HX; not these compatibles | Identify actual IC, SPI, IRQ/reset, and firmware | 4 |
| Wacom | `wacom,w90xx` | Other W900/I2C/HID | Specific protocol, GPIO, and power lines | 4 |
| Wi-Fi / BT | SCSC: `samsung,scsc_wifibt`, `exynos,wifibt_if` | Absent | Driver/firmware/protocol, memory, IRQ, PMU/QoS; complex block | 5 |
| Audio | ABOX + `cirrus,cs35l45` | CS35L45 codec exact; ABOX/machine absent | DSP/firmware, ASoC machine driver, and audio routing | 5 |
| PMIC / Charging / USB-PD | SM5714, SM5440, `sec-battery`, S2MPU15/16 | Absent for these IDs | MFD, regulator, charger, fuel gauge, Type-C; do not modify limits without measurement | 5 |
| Cameras / NPU | Proprietary Samsung stack | No equivalent S5E8835 platform support | Do not block first boot; requires IOMMU, firmware, and sensor drivers | 6 |
| Modem / CPIF | X516 5G reference | Not applicable to X510 Wi-Fi | Keep excluded and disabled; do not infer hardware from X516 | 6/N/A |

## Bring-up Dependencies

```text
PSCI + GIC + timer + verifiable UART
          |
          +--> CMU/clock + pinctrl/GPIO + PMU/ACPM
                       |
                       +--> I2C/SPI/PWM --> sensors/input
                       +--> SysMMU --> UFS (read-only), USB
                       +--> DPU/DSIM/PHY --> panel
                       +--> GPU/audio/Wi-Fi/PD/camera/NPU
```

The initial boot image must prioritize console output and diagnostics. UART0 is not enabled simply because a stock node exists: observed DT leaves it disabled, and pinmux and physical destination still require verification. UFS, USB, and display require S5E8835 platform data even though mainline core drivers exist. Wi-Fi/BT, ABOX, charging, and camera/NPU are deferred to later milestones.

## Explicit M2/M3 Blockers

M2 represents the first kernel message, and M3 is `/init` as PID 1 (`README.md:83-94`). Infrastructure blockers are the correct base EZE4 DT, PSCI/GIC/timer, CMU/clocks, pinctrl/GPIO, minimal PMU/ACPM, and an observable channel (validated UART, pre-tested USB, or pstore). M3 adds stable IRQ/SMP and a valid initramfs with `/init`; it does not require UFS, display, touch, GPU, Wi-Fi, audio, or battery charging. The recommended initial test uses a module-free initramfs and leaves these peripherals uninitialized (`docs/12-first-test-preflight.md:94-111`).

UFS (M5), full USB, DPU/panel, touchscreen/Wacom, GPU, SCSC Wi-Fi/BT, ABOX, SM5714/SM5440, cameras/NPU, sensors, and CPIF can wait for M5/M6/M7. The detailed matrix lists the dependencies to resolve at each phase.

## Evidence and Boundaries

- Stock base DT identifies `samsung,s5e8835` and contains infrastructure blocks; EZE4 overlays include hw-rev ranges 0, 1–3, and 4–32. Which one the unit's bootloader selects is unknown.
- Observed overlay contains two panel candidates and two touchscreen families; this list must not be converted into a confirmed BOM claim.
- `reports/generated/wifi/compatibles.md` records 259 strings, 12 exact matches, and 247 unmatched. This is a textual comparison, not proof of functionality.
- No driver was compiled for or tested on the tablet, and no images were flashed.

The complete matrix preserves paths and lines from `rg` and `git ls-tree` to allow re-evaluating each conclusion without internet access.
