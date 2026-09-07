# U3 → U11 Changes Summary by Subsystem

The numbers count paths whose content/presence changes. They do not prove
hardware compatibility on their own; they must be read alongside the DTS semantic diff.

| subsystem | changed | U3 only | U11 only | examples |
|---|---:|---:|---:|---|
| `device_tree_s5e8835_x510` | 3 | 0 | 0 | `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r00.dts`<br>`arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r01.dts`<br>`arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r04.dts` |
| `psci_gic_timers` | 28 | 0 | 0 | `drivers/clocksource/Kconfig`<br>`drivers/clocksource/arm_global_timer.c`<br>`drivers/clocksource/exynos_mct.c` |
| `cmu_clocks` | 1 | 0 | 0 | `drivers/clk/samsung/clk.c` |
| `pinctrl_gpio_eint` | 31 | 0 | 0 | `drivers/gpio/Kconfig`<br>`drivers/gpio/gpio-74x164.c`<br>`drivers/gpio/gpio-aggregator.c` |
| `pmu_acpm_power_domains` | 0 | 0 | 0 | — |
| `sysmmu_iommu` | 0 | 0 | 0 | — |
| `ufs_phy_fmp` | 12 | 0 | 0 | `drivers/scsi/ufs/Kconfig`<br>`drivers/scsi/ufs/cdns-pltfrm.c`<br>`drivers/scsi/ufs/ufs-exynos.c` |
| `usb_dwc3_typec` | 164 | 1 | 0 | `drivers/usb/atm/cxacru.c`<br>`drivers/usb/cdns3/cdns3-gadget.c`<br>`drivers/usb/cdns3/cdns3-gadget.h` |
| `display_dsim_panel` | 43 | 0 | 1 | `drivers/gpu/drm/samsung/dpu/cal_common/decon_cal.h`<br>`drivers/gpu/drm/samsung/dpu/cal_common/dsim_cal.h`<br>`drivers/gpu/drm/samsung/dpu/cal_common/rcd_cal.h` |
| `touchscreen_wacom_pogo` | 14 | 0 | 0 | `drivers/input/sec_input/sec_input.h`<br>`drivers/input/sec_input/stm32/stm32_pogo_cmd_v3.c`<br>`drivers/input/sec_input/stm32/stm32_pogo_fn_v3.c` |
| `gpu_mali` | 11 | 0 | 0 | `drivers/gpu/arm/exynos/frontend/gpex_clock.c`<br>`drivers/gpu/arm/exynos/frontend/gpex_dvfs.c`<br>`drivers/gpu/arm/exynos/mali_exynos_kbase_entrypoint.c` |
| `wifi_bt_scsc` | 45 | 0 | 0 | `drivers/misc/samsung/scsc/Kconfig`<br>`drivers/misc/samsung/scsc/mx140_file.c`<br>`drivers/misc/samsung/scsc/mxman_split.c` |
| `battery_pmic_charging` | 29 | 0 | 0 | `drivers/battery/charger/sm5440_charger/sm5440_charger.c`<br>`drivers/battery/charger/sm5440_charger/sm5440_charger.dtsi`<br>`drivers/battery/charger/sm5714_charger/sm5714_charger.c` |
| `thermal` | 0 | 0 | 0 | — |
| `build_toolchain` | 7 | 0 | 0 | `Makefile`<br>`arch/arm64/Makefile`<br>`build.config.db845c` |
