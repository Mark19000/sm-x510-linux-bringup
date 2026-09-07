# Driver Audit: X510 Downstream vs Linux Mainline

## Scope and Method

This matrix compares only the local sources already downloaded and the stock DT
extracted from EZE4. It is not an assertion that all nodes are populated on
the unit nor that a shared `compatible` is electrically interchangeable.

| Source | Identity Used |
|---|---|
| Target | `SM-X510`, Wi-Fi variant, AP `X510XXUCEZE4` (`configs/target-sm-x510.env:3-7`) |
| Observed DT | base `artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts` and three EZE4 overlays (`artifacts/stock/dt/overlays/`) |
| Samsung downstream | `sources/wifi-kernel`, commit `9a752a833474`, X510 `X510XXU3BXDG`, 5.15.123 |
| Mainline | `sources/mainline-kernel`, commit `26260251022f`, 2026-08-21 |

The Samsung code is U3 and serves as a reference, not as exact EZE4 source
(`sources/README.md:7-10`). The stock DT contains overlays for hw-rev 0, 1--3, and
4--32; without the effective hw-rev, r00, r01, or r04 cannot be chosen
(`docs/02-analisis-device-tree.md:29-48`). Therefore, panels and touch
controllers remain as candidates.

Only cases where the string appears in the mainline `of_device_id`/binding were
marked as **exact**. A family (for example Exynos850) indicates that there is
reusable code to study, not a safe substitution. The mainline checkout is sparse
(`git -C sources/mainline-kernel sparse-checkout list`); content searches (`rg`)
only cover present files. When a path is not in the sparse checkout, its existence
was verified with `git ls-tree -r HEAD`, without converting the absence of a local
blob into a negative.

## Matrix by Block

Priority: 1 = minimal bring-up and console, 2 = storage/basic peripheral,
3 = display, 4 = input/GPU, 5 = Android functions/power, 6 = optional or other
variant functions.

| Block and observed compatibles | Samsung downstream driver | Mainline support in this snapshot | Dependencies, blocker, and priority | Local evidence (paths/grep) |
|---|---|---|---|---|
| **CPU, PSCI, GIC, timer, and DMA**: `arm,psci-1.0`, `arm,gic-400`, `arm,armv8-timer`, `arm,pl330` | Generic descriptors in `s5e8835.dts`; no need to import Android policy to boot | Exact/generic: PSCI binding, GIC, ARM timer, and PL330 | Validate `interrupt-parent`, topology, and clocks before enabling more IP. **P1** | Stock DT `:5540,9936,9972,10186`; mainline `drivers/clocksource/arm_arch_timer.c:1217`, `drivers/irqchip/irq-gic.c:1515`, `drivers/of/platform.c:481`, PSCI/DMA bindings |
| **UART**: `samsung,exynos-uart` | `drivers/tty/serial/exynos_tty.c`, S5E8835 table and USI v2 | No `samsung,exynos-uart` in present mainline files; `samsung_tty.c` only has data for S3C/S5PV210/Exynos4210/5433/850 and others | Add S5E8835 data/compatible, clocks, pinctrl, and earlycon. Stock UART0 is disabled; do not assume its pins are external. **P1** | Stock DT `:4352`; downstream `sources/wifi-kernel/drivers/tty/serial/exynos_tty.c:3446`; mainline `drivers/tty/serial/samsung_tty.c:2632-2644`; `rg -n -F 'samsung,exynos-uart' sources/mainline-kernel` = 0 |
| **HSI2C / USI**: `samsung,exynos5-hsi2c` | `drivers/i2c/busses/i2c-exynos5.c`; downstream USI v2 integration | Exact compatible for generic bus (`drivers/i2c/busses/i2c-exynos5.c:251`), but binding only documents prior families; mainline USI enumerates Exynos850/8895 and not S5E8835 | Confirm USI variant, clocks, IRQ, pinctrl, and FIFO mode; do not extrapolate Exynos850 data. **P2** | Stock DT `:3432`; downstream `.../i2c-exynos5.c:292`; mainline `.../i2c-exynos5.c:251`, `drivers/soc/samsung/exynos-usi.c:122-125`; `Documentation/devicetree/bindings/i2c/i2c-exynos5.yaml:47` |
| **SPI**: `samsung,exynos-spi` | `drivers/spi/spi-s3c64xx.c`, generic downstream entry | Mainline has `samsung,exynos850-spi` family, not stock string `samsung,exynos-spi` | Add/validate S5E8835 data and clocks/DMAs before using touch, Wacom, or sensors. **P2/P4 depending on consumer** | Stock DT `:4068`; downstream `.../spi-s3c64xx.c:2414`; mainline `.../spi-s3c64xx.c:1635-1638` |
| **PWM**: `samsung,s3c6400-pwm` | Provider `drivers/pwm/pwm-samsung.c:641` | Exact binding (`Documentation/devicetree/bindings/pwm/pwm-samsung.yaml:26`), but checkout does not contain provider; Git tree does contain `drivers/pwm/pwm-samsung.c`; PWM timer also present in `drivers/clocksource/samsung_pwm_timer.c:489` | Separate "recognized timer" from "consumer PWM"; verify clocks/prescalers and do not use as proof of panel support. **P2** | Stock DT `:10135`; downstream `.../pwm-samsung.c:641`; `git -C sources/mainline-kernel ls-tree -r --name-only HEAD -- drivers/pwm/pwm-samsung.c` |
| **Clocks / CMU**: `samsung,s5e8835-clock`, `samsung,s5e8835-oscclk` | `drivers/clk/samsung/clk-s5e8835.c` plus private CAL/ACPM and DVFS | No `samsung,s5e8835*` in present mainline files; only Exynos850/990/2200/AutoV9 patterns | Root block: port bindings and per-domain CMU, reset, and clock sources; do not copy a monolithic driver with values from another SoC. **P1** | Stock DT `:9965`; downstream `sources/wifi-kernel/drivers/clk/samsung/clk-s5e8835.c:568,666`; `rg -n -F 'samsung,s5e8835' sources/mainline-kernel` = 0; downstream `drivers/soc/samsung/cal-if/`, `drivers/soc/samsung/acpm/` |
| **Pinctrl / GPIO / EINT**: six nodes `samsung,s5e8835-pinctrl` | `drivers/pinctrl/samsung/pinctrl-samsung.c`, S5E8835 tables and EINT/wakeup | No S5E8835 in present mainline files; mainline family enumerates Exynos850, S5E9925/S5E9935, and others | Port banks, offsets, EINT, and wakeup; check pull changes per hw-rev before activating buses. **P1** | Stock DT `:1723,1900` and four more nodes; downstream `.../pinctrl-samsung.c:1547`; mainline `.../pinctrl-samsung.c:1501`; binding `samsung,pinctrl.yaml`; `rg -n -F 'samsung,s5e8835' sources/mainline-kernel` = 0 |
| **PMU / ACPM / reset / power domains**: `samsung,exynos-pmu`, `samsung,exynos-pd` | `drivers/soc/samsung/exynos-pmu.c`, `exynos-pd/`, ACPM IPC/CAL | PMU only has data for earlier SoCs, Exynos850, and GS101 (`drivers/soc/samsung/exynos-pmu.c:124-151`); no S5E8835 `exynos-pd` in present mainline files | Dependency for clocks, UFS, USB, display, GPU, and suspend; implement verifiable minimum and essential domains. **P1** | Stock DT `:9978`; downstream `.../exynos-pd.c:34,539`; mainline `.../exynos-pmu.c:151`; `rg -n -F 'samsung,exynos-pd' sources/mainline-kernel` = 0 |
| **IOMMU / SysMMU**: `samsung,sysmmu-v8` | `drivers/iommu/samsung/samsung-iommu.c:1568` | Only older `samsung,exynos-sysmmu` family (`drivers/iommu/exynos-iommu.c:870`); no `sysmmu-v8` in present mainline files | Blocks DPU, camera, and GPU; port v8 data, fault handling, and bindings before those consumers. **P2** | Stock DT `:4688`; downstream `.../samsung-iommu.c:1568`; mainline `.../exynos-iommu.c:870`; `rg -n -F 'samsung,sysmmu-v8' sources/mainline-kernel` = 0 |
| **UFS**: `samsung,exynos-ufs` | `drivers/scsi/ufs/ufs-exynos.c` with FMP, PM QoS, and calibration; Samsung PHY | `drivers/ufs/host/ufs-exynos.c` only declares GS101, Exynos7, AutoV9/AutoV920, and Tesla; binding `samsung,exynos-ufs.yaml` does not enumerate S5E8835 | Needs PHY/calibration, clocks, reset, power-domain, and SysMMU. Mount read-only after infrastructure. **P2** | Stock DT `:7061`; downstream `.../ufs-exynos.c:2689`, `.../phy-samsung-ufs.c:75`; mainline `.../ufs-exynos.c:2312-2327`, binding `ufs/samsung,exynos-ufs.yaml:18-25`; `rg -n 'compatible = "samsung,exynos-ufs"' sources/mainline-kernel` = 0 |
| **USB DWC3 core**: `synopsys,dwc3` | DWC3 core plus glue `drivers/usb/dwc3/dwc3-exynos.c` | Exact generic core in mainline; S5E8835 glue is not (mainline `dwc3-exynos.c` only lists up to Exynos850/GS101/AutoV920) | Core can be tested only with correct DT/clocks; do not confuse with functional USB. **P2** | Stock DT `:6805`/glue `:6778`; downstream `.../dwc3-exynos.c:98`; mainline `drivers/usb/dwc3/core.c:2828-2831`, glue `.../dwc3-exynos.c:198-219`; `rg -n -F 'samsung,exynos-dwusb' sources/mainline-kernel` = 0 |
| **USB PHY / role switch**: `samsung,exynos-usbdrd-phy` | `drivers/phy/samsung/phy-exynos-usbdrd.c`, calibration/OTP, and downstream Type-C | `phy-exynos5-usbdrd.c` family (Exynos7/850/990/2200/GS101), without S5E8835 `exynos-usbdrd-phy` | Port USB2/USB3 PHY, calibration, glue, and role switch; depends on PMU/clock/pinctrl. **P2** | Stock DT `:6827`; downstream `.../phy-exynos-usbdrd.c:2204` and `:41-54`; mainline `.../phy-exynos5-usbdrd.c:2878-2918`; `rg -n -F 'samsung,exynos-usbdrd-phy' sources/mainline-kernel` = 0 |
| **Display DPU / DECON / DPP / DSIM**: `samsung,exynos-decon`, `...-dpp`, `...-dsim` | `drivers/gpu/drm/samsung/dpu/` (DECON, DPP, DSIM, and Samsung CAL) | Mainline only has older Exynos DRM (Exynos5433/7) and generic DSI; S5E8835 compatibles are not in present files | Large port: clocks, pinctrl, PMU, SysMMU, DRM atomic, and MIPI PHY. Do not block console on display. **P3** | Stock DT `:5013,5188,5208`; downstream `.../drivers/gpu/drm/samsung/dpu/`; mainline `drivers/gpu/drm/exynos/exynos7_drm_decon.c:82-87`; `rg -n -e 'samsung,exynos-dpp' -e 'samsung,exynos-decon' -e 'samsung,exynos-dsim' sources/mainline-kernel` = 0 |
| **LCD Panel**: overlay offers `nt36523n_gts9fe_csot` and `hx83102j_gts9fe_boe`; private node `samsung,panel-drv` | `drivers/gpu/drm/samsung/panel/tft_common/{nt36523n_gts9fe_csot,hx83102j_gts9fe_boe}.c` and Samsung sequences | Mainline does have Himax HX83102 and Novatek NT36523 families, but only descriptors for other panels; not `gts9fe` | Select by effective ID/overlay and verify commands, timings, regulators, reset, and backlight. Do not assert BOE/CSOT mounted. **P3** | Overlay 01 `:877-879,955-957` and private panel `:1042`; downstream panel files; mainline `panel-himax-hx83102.c:1341-1368`, `panel-novatek-nt36523.c:1244-1257`, bindings `display/panel/{himax,hx83102,novatek,nt36523}.yaml` |
| **GPU**: `arm,mali` in DT; variant not inferred from `compatible` | Downstream Mali driver under `drivers/gpu/arm/v_r38p1` | Mainline Git tree contains Panfrost family, but `drivers/gpu/drm/panfrost` is not in sparse checkout; exact compatible cannot be audited without materializing those blobs | Depends on clocks, power-domain, reset, SysMMU, and firmware; priority after basic framebuffer. **P4** | Downstream DT `sources/wifi-kernel/arch/arm64/boot/dts/exynos/s5e8835.dts:6673-6674`; `git -C sources/mainline-kernel ls-tree -r --name-only HEAD -- drivers/gpu/drm/panfrost`; `rg -n -F 'arm,mali' sources/mainline-kernel` = 0 only in present files |
| **Touch SPI**: `nvt_ts_spi`, `novatek-mp-criteria-725C`, `himax,hxcommon` | Novatek `drivers/input/touchscreen/novatek/nt36523_tablet_spi/`; Himax `.../himax/hx83xxx_spi/` | Mainline Novatek declares NT11205/NT36672A; Himax declares HX852ES/HX83112B; not these SPI/`hxcommon` compatibles | Real IC must be detected from effective overlay; requires SPI, pinctrl, IRQ/reset, regulators, and firmware. Do not choose Novatek/Himax by filename. **P4** | Overlay 01 `:2396,2429,2758`; downstream `.../nt36xxx.c`, `.../himax_platform_SPI.c:1546`; mainline `drivers/input/touchscreen/novatek-nvt-ts.c:321-326`, `himax_hx852x.c:482-486`, `himax_hx83112b.c:417-418` |
| **Wacom Digitizer**: `wacom,w90xx` | `drivers/input/wacom/wacom_i2c.c:3290` | Mainline has Wacom I2C/HID and `wacom_w9000.c`, but W9002/W9007 compatibles, not `w90xx` | Confirm protocol, GPIO, power, and bus; keep independent from LCD touch. **P4** | Overlay 01 `:4391`; downstream `.../wacom_i2c.c:3290`; mainline `drivers/input/touchscreen/wacom_w9000.c:415-418` |
| **Wi-Fi / BT SCSC**: `samsung,scsc_wifibt`, `exynos,wifibt_if`, QoS | `drivers/misc/samsung/scsc/`, `platform_mif_s5e8835.c`, and `drivers/net/wireless/scsc` | No SCSC in present mainline files and Git tree also lacks `drivers/net/wireless/scsc` | Driver, firmware, reserved memory, IRQ, PMU/QoS, and protocol are proprietary; not a reasonable block for first boot. `a96t396_wifi` is another I2C node from overlay, not proof of WLAN. **P5** | Stock DT `:234,8442-8458`, overlay 01 `:2868-2869`; downstream `.../platform_mif_s5e8835.c:53-54`; `rg -n -F 'samsung,scsc_wifibt' sources/mainline-kernel` = 0; `git ls-tree ... drivers/net/wireless/scsc` empty |
| **Audio**: `samsung,abox`, `samsung,abox-core`, `cirrus,cs35l45` | ABOX/machine `sound/soc/samsung/exynos/{abox,exynos8835_sound.c}` and downstream codec | Exact CS35L45 codec (I2C/SPI and binding); no ABOX or Exynos8835 machine in present files | Isolated codec does not produce audio: missing DSP/firmware, ABOX, machine, clocks, and routes. **P5** | Stock DT `:5846`; overlay 01 `:5287,5388`; downstream `.../abox_core.c:564`, `.../exynos8835_sound.c:1697`; mainline `sound/soc/codecs/cs35l45-i2c.c:50`, `cs35l45-spi.c:52`; `rg -n -F 'samsung,abox' sources/mainline-kernel` = 0 |
| **PMIC, Charging, and USB-PD**: `samsung,sm5714-charger`, `siliconmitus,sm5714mfd`, `siliconmitus,sm5440`, `samsung,sec-battery` | MFD/charger/fuel-gauge/Type-C SM5714, SM5440, and `sec-battery`; S2MPU15/16 PMIC | No drivers/compatibles for SM5714, SM5440, S2MPU15/16, or `sec-battery` in present mainline files; only other generic Silicon Mitus | High risk: do not enable charging or alter limits/regulators without schematics and measurements; depends on I2C, GPIO, IRQ, and ACPM. **P5** | Overlay 01 `:264-277,2608-2609`; downstream `drivers/mfd/sm/sm5714/sm5714_core.c:448`, `drivers/usb/typec/sm/sm5714/sm5714_typec.c:4490`, `drivers/battery/common/sec_direct_charger.c:1171`; queries `rg -n -F sm5714`, `sm5440`, and `sec-battery` on mainline: 0 |
| **Cameras / NPU / Samsung Multimedia**: `samsung,exynos-is`, `samsung,exynos-npu` and private sensors | `drivers/media/platform/exynos/camera`, `drivers/vision`/Samsung stack | Snapshot lacks `drivers/media/platform/exynos` (empty `git ls-tree`) and equivalent S5E8835/NPU stack; older Exynos camera bindings exist | Do not block console/UFS/USB on these blocks; require IOMMU, clocks, firmware, reserved memory, and identified sensors. **P6** | Base DT `docs/02-analisis-device-tree.md:60-62`; compatibles in `reports/generated/wifi/compatibles.md`; `git -C sources/mainline-kernel ls-tree -r --name-only HEAD -- drivers/media/platform/exynos`; `git -C sources/mainline-kernel ls-tree -r --name-only HEAD -- drivers/vision` |
| **Modem/CPIF** (X516 reference only, not Wi-Fi target) | CPIF/GNSS code in 5G reference `sources/device-kernel` | Not applicable to `TARGET_VARIANT=wifi`; do not enable CP nodes by SoC similarity | Keep disabled and out of X510 Wi-Fi bring-up; do not infer hardware from X516 matrix. **P6/N/A** | `configs/target-sm-x510.env:3-4`; `sources/README.md:9`; `docs/02-analisis-device-tree.md:82-84` |

## Bring-up Order Derived from Comparison

```text
PSCI + GIC + timer + UART (if its pins are verifiable)
        |
        +--> CMU/clock + pinctrl/GPIO + minimal PMU/ACPM
                    |
                    +--> I2C/SPI/PWM --> sensors/input
                    +--> SysMMU --> UFS (read-only), USB
                    +--> DPU/DSIM/PHY --> panel (later)
                    +--> GPU/audio/Wi-Fi/PD/camera/NPU (subsequently)
```

The first safe milestone is a diagnostic image with PSCI/GIC/timer,
UART only after verifying pinmux, and isolated clock/pinctrl/PMU infrastructure.
UFS, USB, and display must not be enabled simply because the mainline core
exists: each requires its S5E8835 data. Wi-Fi/BT, ABOX audio, charging, and
camera/NPU are deliberately excluded from first boot.

## Explicit M2/M3 Blockers

Project milestones define M2 as "first kernel message" and M3 as
`/init` running as PID 1 (`README.md:83-94`). For those two milestones, the
driver/DT blockers are solely:

- **M2:** Correct base DT for EZE4, PSCI/GIC/timer, minimal clocks/PMU, and an
  observable channel. The channel can be UART only if pinmux/levels and clock
  are validated; stock UART0 appears disabled. If USB/pstore is used as an
  alternative, its path must be demonstrated beforehand, not assumed.
- **M3:** All of the above, plus stable IRQ/SMP and an initramfs with valid
  `devtmpfs`, format, and `/init`. UFS, display, touch, GPU, Wi-Fi, audio, and
  charging are not required: preflight recommends `MODULES_MODE=none` and rootfs
  in initramfs for this test (`docs/12-preflight-primera-prueba.md:94-111`).
- **Shared infrastructure blockers:** S5E8835 CMU, pinctrl/GPIO, PMU/ACPM, and,
  only if the chosen channel requires it, basic UART/USB. SysMMU, UFS, DPU,
  DSIM, display PHY, GPU, and Android peripherals must not enter M2/M3 under
  pressure to "get more working".

The following can wait until subsequent milestones (M5/M6/M7): UFS and partitions
in `ro`, USB host/role switch, DPU/DSIM/panel, Novatek/Himax touch, Wacom,
Panfrost/Mali, SCSC Wi-Fi/BT, ABOX/CS35L45 audio, SM5714/SM5440 and battery,
cameras/NPU, sensors, and CPIF. This separation prevents a failure in an
optional peripheral or an as-yet unidentified BOM from obscuring the cause of an
early crash.

This list orders technical work; it does not authorize a physical test.
The gates for exact EZE4 source, hw-rev, AVB, restoration, and observability
remain those of preflight (`docs/12-preflight-primera-prueba.md`) and can
maintain the NO-GO verdict even if M2/M3 are solved in the laboratory.

## Limitations and Reproducible Checks

- `reports/generated/wifi/compatibles.md` is a mechanical report (259 strings,
  12 exact matches); a match does not prove functionality.
- Compatible searches were performed with `rg -n PATTERN sources/mainline-kernel`
  on local files, and presence of unmaterialized paths with `git ls-tree -r HEAD`;
  the working checkout is sparse and downloading blobs must not be forced to close
  a negative.
- No driver was recompiled or tested on the tablet, and nothing was flashed.
- The effective hw-rev and BOM (panel/touch/PMIC) of the unit are not known;
  candidate rows must be resolved with running DT, component IDs, and power
  measurements before porting commands or limits.
