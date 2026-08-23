# Comparación OSRC U3 ↔ U11

Informe host-only generado por `tools/osrc_tree_compare.py`. Las entradas
se leen sin modificarlas; los ficheros `.part` se ignoran y no se espera
ninguna descarga incompleta.

## Entradas

| árbol | raíz | commit Git | ficheros | `.part` ignorados | enlaces ignorados |
|---|---|---|---:|---:|---:|
| `U3` | `<guest-home>/osrc-u11-work/u3-clean-x510xxu3bxdg` | `9a752a83347461b3785711760ba925fcabea3071` | 80673 | 0 | 26 |
| `U11` | `<guest-home>/osrc-u11-work/x510xxsbdzb4-u11-inspect4-20260823/u11-composite/Kernel` | `-` | 80777 | 0 | 26 |

## Inventario por componente

| componente | U3 | U11 | sólo U3 | sólo U11 | cambiados | sin cambios |
|---|---:|---:|---:|---:|---:|---:|
| `dts` | 3200 | 3217 | 0 | 17 | 228 | 2972 |
| `drivers` | 37094 | 37155 | 18 | 79 | 3721 | 33355 |
| `configs` | 2450 | 2454 | 0 | 4 | 107 | 2343 |
| `build_scripts` | 3385 | 3389 | 3 | 7 | 85 | 3297 |

### Detalle `dts`

- **Sólo U11** (17):
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/aax_v35x/s5e8835-a35x-camera_kor.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/aay_v26x/module_4ha.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/aay_v26x/module_gc02m1.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/aay_v26x/module_imx258.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/aay_v26x/module_jn1.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/aay_v26x/s5e8835-a26x-camera_00.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/mmy_v36x/module_2ld.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/mmy_v36x/module_4ha.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/mmy_v36x/module_gc02m1.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/mmy_v36x/module_imx258.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/mmy_v36x/module_jn1.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/mmy_v36x/s5e8835-m36x-camera_00.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/mmy_v36x/s5e8835-m36x-camera_kor.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/mmy_v36x/s5e8835-m36x-camera_kor_01.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/sty_v40/module_gc5035.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/sty_v40/module_imx355.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/sty_v40/s5e8835-gts10lite-camera_00.dtsi`
- **Cambian** (228):
  - `arch/arc/boot/dts/hsdk.dts`
  - `arch/arm/boot/dts/am33xx.dtsi`
  - `arch/arm/boot/dts/am3517.dtsi`
  - `arch/arm/boot/dts/am4372.dtsi`
  - `arch/arm/boot/dts/arm-realview-pb1176.dts`
  - `arch/arm/boot/dts/artpec6-devboard.dts`
  - `arch/arm/boot/dts/aspeed-bmc-asrock-e3c246d4i.dts`
  - `arch/arm/boot/dts/bcm2711.dtsi`
  - `arch/arm/boot/dts/bcm2837-rpi-cm3-io3.dts`
  - `arch/arm/boot/dts/bcm4708-linksys-ea6500-v2.dts`
  - `arch/arm/boot/dts/bcm47189-luxul-xap-1440.dts`
  - `arch/arm/boot/dts/bcm47189-luxul-xap-810.dts`
  - `arch/arm/boot/dts/bcm53573.dtsi`
  - `arch/arm/boot/dts/bcm947189acdbmr.dts`
  - `arch/arm/boot/dts/dm814x.dtsi`
  - `arch/arm/boot/dts/dm816x.dtsi`
  - `arch/arm/boot/dts/dra62x.dtsi`
  - `arch/arm/boot/dts/dra7-dspeve-thermal.dtsi`
  - `arch/arm/boot/dts/dra7-iva-thermal.dtsi`
  - `arch/arm/boot/dts/dra7-l4.dtsi`
  - `arch/arm/boot/dts/dra7.dtsi`
  - `arch/arm/boot/dts/exynos4210-i9100.dts`
  - `arch/arm/boot/dts/exynos4210-smdkv310.dts`
  - `arch/arm/boot/dts/exynos4412-origen.dts`
  - `arch/arm/boot/dts/exynos4412-smdk4412.dts`
  - `arch/arm/boot/dts/imx1-ads.dts`
  - `arch/arm/boot/dts/imx1-apf9328.dts`
  - `arch/arm/boot/dts/imx1.dtsi`
  - `arch/arm/boot/dts/imx23-sansa.dts`
  - `arch/arm/boot/dts/imx23.dtsi`
  - `arch/arm/boot/dts/imx25-eukrea-cpuimx25.dtsi`
  - `arch/arm/boot/dts/imx25-eukrea-mbimxsd25-baseboard-cmo-qvga.dts`
  - `arch/arm/boot/dts/imx25-eukrea-mbimxsd25-baseboard-dvi-svga.dts`
  - `arch/arm/boot/dts/imx25-eukrea-mbimxsd25-baseboard-dvi-vga.dts`
  - `arch/arm/boot/dts/imx25-pdk.dts`
  - `arch/arm/boot/dts/imx25.dtsi`
  - `arch/arm/boot/dts/imx27-apf27dev.dts`
  - `arch/arm/boot/dts/imx27-eukrea-cpuimx27.dtsi`
  - `arch/arm/boot/dts/imx27-eukrea-mbimxsd27-baseboard.dts`
  - `arch/arm/boot/dts/imx27-phytec-phycard-s-rdk.dts`
  - `arch/arm/boot/dts/imx27-phytec-phycore-rdk.dts`
  - `arch/arm/boot/dts/imx27-phytec-phycore-som.dtsi`
  - `arch/arm/boot/dts/imx27.dtsi`
  - `arch/arm/boot/dts/imx28-xea.dts`
  - `arch/arm/boot/dts/imx28.dtsi`
  - `arch/arm/boot/dts/imx31.dtsi`
  - `arch/arm/boot/dts/imx35.dtsi`
  - `arch/arm/boot/dts/imx50.dtsi`
  - `arch/arm/boot/dts/imx51.dtsi`
  - `arch/arm/boot/dts/imx53.dtsi`
  - … y 178 más (ver JSON).

### Detalle `drivers`

- **Sólo U3** (18):
  - `drivers/gpu/drm/amd/display/dc/calcs/Makefile`
  - `drivers/gpu/drm/amd/display/dc/calcs/bw_fixed.c`
  - `drivers/gpu/drm/amd/display/dc/calcs/calcs_logger.h`
  - `drivers/gpu/drm/amd/display/dc/calcs/custom_float.c`
  - `drivers/gpu/drm/amd/display/dc/calcs/dce_calcs.c`
  - `drivers/gpu/drm/amd/display/dc/calcs/dcn_calc_auto.c`
  - `drivers/gpu/drm/amd/display/dc/calcs/dcn_calc_auto.h`
  - `drivers/gpu/drm/amd/display/dc/calcs/dcn_calc_math.c`
  - `drivers/gpu/drm/amd/display/dc/calcs/dcn_calcs.c`
  - `drivers/gpu/drm/amd/display/dc/dml/dcn2x/dcn2x.c`
  - `drivers/gpu/drm/amd/display/dc/dml/dcn2x/dcn2x.h`
  - `drivers/iio/adc/stx104.c`
  - `drivers/input/serio/i8042-x86ia64io.h`
  - `drivers/net/ethernet/hisilicon/hns3/hns3pf/Makefile`
  - `drivers/net/ethernet/hisilicon/hns3/hns3vf/Makefile`
  - `drivers/net/ethernet/mellanox/mlxbf_gige/mlxbf_gige_gpio.c`
  - `drivers/net/vxlan.c`
  - `drivers/usb/typec/tcpm/tcpci.h`
- **Sólo U11** (79):
  - `drivers/dma-buf/dma-fence-unwrap.c`
  - `drivers/dma-buf/st-dma-fence-unwrap.c`
  - `drivers/gpu/drm/amd/display/dc/dml/calcs/bw_fixed.c`
  - `drivers/gpu/drm/amd/display/dc/dml/calcs/calcs_logger.h`
  - `drivers/gpu/drm/amd/display/dc/dml/calcs/custom_float.c`
  - `drivers/gpu/drm/amd/display/dc/dml/calcs/dce_calcs.c`
  - `drivers/gpu/drm/amd/display/dc/dml/calcs/dcn_calc_auto.c`
  - `drivers/gpu/drm/amd/display/dc/dml/calcs/dcn_calc_auto.h`
  - `drivers/gpu/drm/amd/display/dc/dml/calcs/dcn_calc_math.c`
  - `drivers/gpu/drm/amd/display/dc/dml/calcs/dcn_calcs.c`
  - `drivers/gpu/drm/amd/display/dc/dml/dcn20/dcn20_fpu.c`
  - `drivers/gpu/drm/amd/display/dc/dml/dcn20/dcn20_fpu.h`
  - `drivers/gpu/drm/samsung/panel/panel_wrapper.h`
  - `drivers/iio/addac/Kconfig`
  - `drivers/iio/addac/Makefile`
  - `drivers/iio/addac/stx104.c`
  - `drivers/input/serio/i8042-acpipnpio.h`
  - `drivers/knox/Kconfig`
  - `drivers/knox/Makefile`
  - `drivers/knox/hdm/Kconfig`
  - `drivers/knox/hdm/Makefile`
  - `drivers/knox/hdm/hdm_log.h`
  - `drivers/knox/hdm/main.c`
  - `drivers/knox/hdm/uh.h`
  - `drivers/knox/hdm/uh_entry.S`
  - `drivers/knox/ngksm/Kconfig`
  - `drivers/knox/ngksm/Makefile`
  - `drivers/knox/ngksm/ngk_hypervisor_detector.c`
  - `drivers/knox/ngksm/ngk_hypervisor_detector.h`
  - `drivers/knox/ngksm/ngksm_common.h`
  - `drivers/knox/ngksm/ngksm_kernel_api.c`
  - `drivers/knox/ngksm/ngksm_main.c`
  - `drivers/knox/ngksm/ngksm_netlink.c`
  - `drivers/knox/ngksm/ngksm_netlink.h`
  - `drivers/knox/ngksm/ngksm_rate_limit.c`
  - `drivers/knox/ngksm/ngksm_rate_limit.h`
  - `drivers/media/platform/exynos/camera/sensor/module_framework/actuator/is-actuator-dw9818.c`
  - `drivers/media/platform/exynos/camera/sensor/module_framework/actuator/is-actuator-dw9818.h`
  - `drivers/media/platform/exynos/camera/sensor/module_framework/cis/is-cis-4ha-setB.h`
  - `drivers/media/platform/exynos/camera/sensor/module_framework/cis/is-cis-gc5035-setB.h`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/aax_v35x/s5e8835-a35x-camera_kor.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/aay_v26x/is-vendor-config_aay_v26x.h`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/aay_v26x/module_4ha.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/aay_v26x/module_gc02m1.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/aay_v26x/module_imx258.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/aay_v26x/module_jn1.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/aay_v26x/s5e8835-a26x-camera_00.dtsi`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/mmy_v36x/is-vendor-config_mmy_v36x.h`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/mmy_v36x/is-vendor-config_mmy_v36x_kor.h`
  - `drivers/media/platform/exynos/camera/vendor/mcd_v2/mmy_v36x/module_2ld.dtsi`
  - … y 29 más (ver JSON).
- **Cambian** (3721):
  - `arch/um/drivers/Kconfig`
  - `arch/um/drivers/Makefile`
  - `arch/um/drivers/line.c`
  - `arch/um/drivers/net_kern.c`
  - `arch/um/drivers/ubd_kern.c`
  - `arch/um/drivers/vector_kern.c`
  - `drivers/Kconfig`
  - `drivers/Makefile`
  - `drivers/accessibility/speakup/main.c`
  - `drivers/accessibility/speakup/synth.c`
  - `drivers/acpi/acpi_extlog.c`
  - `drivers/acpi/acpi_fpdt.c`
  - `drivers/acpi/acpi_lpit.c`
  - `drivers/acpi/acpi_lpss.c`
  - `drivers/acpi/acpi_pad.c`
  - `drivers/acpi/acpi_processor.c`
  - `drivers/acpi/acpi_video.c`
  - `drivers/acpi/acpica/Makefile`
  - `drivers/acpi/acpica/dbconvert.c`
  - `drivers/acpi/acpica/dbnames.c`
  - `drivers/acpi/acpica/evxfregn.c`
  - `drivers/acpi/acpica/exprep.c`
  - `drivers/acpi/acpica/exregion.c`
  - `drivers/acpi/acpica/psargs.c`
  - `drivers/acpi/acpica/psopcode.c`
  - `drivers/acpi/apei/ghes.c`
  - `drivers/acpi/arm64/gtdt.c`
  - `drivers/acpi/arm64/iort.c`
  - `drivers/acpi/battery.c`
  - `drivers/acpi/bus.c`
  - `drivers/acpi/button.c`
  - `drivers/acpi/cppc_acpi.c`
  - `drivers/acpi/device_sysfs.c`
  - `drivers/acpi/ec.c`
  - `drivers/acpi/fan.c`
  - `drivers/acpi/irq.c`
  - `drivers/acpi/nfit/core.c`
  - `drivers/acpi/pmic/tps68470_pmic.c`
  - `drivers/acpi/prmt.c`
  - `drivers/acpi/processor_idle.c`
  - `drivers/acpi/processor_perflib.c`
  - `drivers/acpi/property.c`
  - `drivers/acpi/resource.c`
  - `drivers/acpi/sbs.c`
  - `drivers/acpi/scan.c`
  - `drivers/acpi/sleep.c`
  - `drivers/acpi/thermal.c`
  - `drivers/acpi/video_detect.c`
  - `drivers/acpi/x86/s2idle.c`
  - `drivers/acpi/x86/utils.c`
  - … y 3671 más (ver JSON).

### Detalle `configs`

- **Sólo U11** (4):
  - `drivers/iio/addac/Kconfig`
  - `drivers/knox/Kconfig`
  - `drivers/knox/hdm/Kconfig`
  - `drivers/knox/ngksm/Kconfig`
- **Cambian** (107):
  - `Documentation/kbuild/kconfig.rst`
  - `arch/Kconfig`
  - `arch/arm/Kconfig`
  - `arch/arm/mach-davinci/Kconfig`
  - `arch/arm64/Kconfig`
  - `arch/arm64/configs/s5e8835-gts9fewifixx_defconfig`
  - `arch/ia64/Kconfig`
  - `arch/m68k/Kconfig`
  - `arch/mips/Kconfig`
  - `arch/parisc/Kconfig`
  - `arch/powerpc/configs/85xx-hw.config`
  - `arch/powerpc/platforms/44x/Kconfig`
  - `arch/riscv/Kconfig`
  - `arch/sh/Kconfig`
  - `arch/sh/Kconfig.debug`
  - `arch/sparc/Kconfig`
  - `arch/um/Kconfig`
  - `arch/um/configs/i386_defconfig`
  - `arch/um/configs/x86_64_defconfig`
  - `arch/um/drivers/Kconfig`
  - `arch/x86/Kconfig`
  - `arch/x86/Kconfig.cpu`
  - `arch/x86/Kconfig.debug`
  - `arch/x86/configs/gki_defconfig`
  - `block/Kconfig`
  - `drivers/Kconfig`
  - `drivers/bus/Kconfig`
  - `drivers/clk/Kconfig`
  - `drivers/clk/imx/Kconfig`
  - `drivers/clk/qcom/Kconfig`
  - `drivers/clocksource/Kconfig`
  - `drivers/dma/Kconfig`
  - `drivers/extcon/Kconfig`
  - `drivers/firmware/Kconfig`
  - `drivers/gpio/Kconfig`
  - `drivers/gpu/drm/Kconfig`
  - `drivers/gpu/drm/fsl-dcu/Kconfig`
  - `drivers/gpu/drm/samsung/panel/Kconfig`
  - `drivers/gpu/drm/samsung/panel/tft_common/Kconfig`
  - `drivers/gpu/drm/tegra/Kconfig`
  - `drivers/gpu/drm/vmwgfx/Kconfig`
  - `drivers/hwmon/Kconfig`
  - `drivers/iio/Kconfig`
  - `drivers/iio/accel/Kconfig`
  - `drivers/iio/adc/Kconfig`
  - `drivers/iio/dac/Kconfig`
  - `drivers/iio/proximity/Kconfig`
  - `drivers/leds/Kconfig`
  - `drivers/md/Kconfig`
  - `drivers/media/platform/exynos/camera/sensor/module_framework/actuator/Kconfig`
  - … y 57 más (ver JSON).

### Detalle `build_scripts`

- **Sólo U3** (3):
  - `drivers/gpu/drm/amd/display/dc/calcs/Makefile`
  - `drivers/net/ethernet/hisilicon/hns3/hns3pf/Makefile`
  - `drivers/net/ethernet/hisilicon/hns3/hns3vf/Makefile`
- **Sólo U11** (7):
  - `drivers/iio/addac/Makefile`
  - `drivers/knox/Makefile`
  - `drivers/knox/hdm/Makefile`
  - `drivers/knox/ngksm/Makefile`
  - `drivers/net/vxlan/Makefile`
  - `samples/fanotify/Makefile`
  - `security/kzt/Makefile`
- **Cambian** (85):
  - `BUILD.bazel`
  - `Makefile`
  - `arch/arc/Makefile`
  - `arch/arm64/Makefile`
  - `arch/arm64/boot/dts/Makefile`
  - `arch/ia64/Makefile`
  - `arch/microblaze/kernel/Makefile`
  - `arch/mips/Makefile`
  - `arch/mips/vdso/Makefile`
  - `arch/powerpc/Makefile`
  - `arch/powerpc/lib/Makefile`
  - `arch/powerpc/mm/kasan/Makefile`
  - `arch/riscv/kernel/vdso/Makefile`
  - `arch/s390/kernel/syscalls/Makefile`
  - `arch/s390/kernel/vdso32/Makefile`
  - `arch/s390/kernel/vdso64/Makefile`
  - `arch/um/drivers/Makefile`
  - `arch/x86/boot/compressed/Makefile`
  - `arch/x86/events/Makefile`
  - `arch/x86/platform/efi/Makefile`
  - `arch/x86/purgatory/Makefile`
  - `arch/xtensa/boot/Makefile`
  - `build.config.db845c`
  - `build.config.erd8535_t`
  - `build.config.erd8835_t`
  - `build.config.erd9935_t`
  - `build.config.gki.aarch64`
  - `drivers/Makefile`
  - `drivers/acpi/acpica/Makefile`
  - `drivers/dma-buf/Makefile`
  - `drivers/dma/idxd/Makefile`
  - `drivers/edac/Makefile`
  - `drivers/firmware/efi/libstub/Makefile`
  - `drivers/gpu/drm/amd/display/dc/Makefile`
  - `drivers/gpu/drm/amd/display/dc/dml/Makefile`
  - `drivers/hid/Makefile`
  - `drivers/iio/Makefile`
  - `drivers/iio/adc/Makefile`
  - `drivers/input/input_boost/Makefile`
  - `drivers/media/cec/platform/Makefile`
  - `drivers/media/platform/exynos/camera/sensor/module_framework/actuator/Makefile`
  - `drivers/media/platform/exynos/camera/sensor/module_framework/modules/Makefile`
  - `drivers/mfd/Makefile`
  - `drivers/mtd/tests/Makefile`
  - `drivers/net/Makefile`
  - `drivers/net/dsa/mv88e6xxx/Makefile`
  - `drivers/net/ethernet/hisilicon/hns3/Makefile`
  - `drivers/net/ethernet/mellanox/mlxbf_gige/Makefile`
  - `drivers/pci/endpoint/functions/Makefile`
  - `drivers/samsung/debug/Makefile`
  - … y 35 más (ver JSON).

## Matriz DTS U3 ↔ U11 ↔ EZE4

| EZE4 | U3 | U11 | U3↔U11 | U3↔EZE4 | U11↔EZE4 |
|---|---|---|---|---|---|
| `overlays/overlay-00-id-00000000-rev-00000000.dts` | `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r00.dts` (high) | `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r00.dts` (path) | DIFFERENT (INCOMPLETE) | DIFFERENT (INCOMPLETE) | INCONCLUSIVE |
| `overlays/overlay-01-id-00000000-rev-00000000.dts` | `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r01.dts` (high) | `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r01.dts` (path) | DIFFERENT (INCOMPLETE) | DIFFERENT (INCOMPLETE) | INCONCLUSIVE |
| `overlays/overlay-02-id-00000000-rev-00000000.dts` | `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r04.dts` (high) | `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r04.dts` (path) | DIFFERENT (INCOMPLETE) | DIFFERENT (INCOMPLETE) | INCONCLUSIVE |
| `recovery/fdt-00-offset-044a6080.dts` | `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r00.dts` (high) | `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r00.dts` (path) | DIFFERENT (INCOMPLETE) | DIFFERENT (INCOMPLETE) | INCONCLUSIVE |
| `recovery/fdt-01-offset-044d221c.dts` | `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r01.dts` (high) | `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r01.dts` (path) | DIFFERENT (INCOMPLETE) | DIFFERENT (INCOMPLETE) | INCONCLUSIVE |
| `recovery/fdt-02-offset-044fe3b8.dts` | `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r04.dts` (high) | `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r04.dts` (path) | DIFFERENT (INCOMPLETE) | DIFFERENT (INCOMPLETE) | INCONCLUSIVE |
| `recovery/fdt-03-offset-0452b040.dts` | `arch/arm64/boot/dts/exynos/s5e8835.dts` (high) | `arch/arm64/boot/dts/exynos/s5e8835.dts` (path) | DIFFERENT (INCOMPLETE) | DIFFERENT (INCOMPLETE) | DIFFERENT (INCOMPLETE) |
| `vendor_boot/fdt-00-offset-0113f040.dts` | `arch/arm64/boot/dts/exynos/s5e8835.dts` (high) | `arch/arm64/boot/dts/exynos/s5e8835.dts` (path) | DIFFERENT (INCOMPLETE) | DIFFERENT (INCOMPLETE) | DIFFERENT (INCOMPLETE) |

DTB binarios detectados pero no comparados semánticamente:

- `<project-root>/artifacts/stock/dt/recovery/fdt-00-offset-044a6080.dtb`: DTB binario; proporciona el DTS decompilado para comparación semántica
- `<project-root>/artifacts/stock/dt/recovery/fdt-01-offset-044d221c.dtb`: DTB binario; proporciona el DTS decompilado para comparación semántica
- `<project-root>/artifacts/stock/dt/recovery/fdt-02-offset-044fe3b8.dtb`: DTB binario; proporciona el DTS decompilado para comparación semántica
- `<project-root>/artifacts/stock/dt/recovery/fdt-03-offset-0452b040.dtb`: DTB binario; proporciona el DTS decompilado para comparación semántica
- `<project-root>/artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dtb`: DTB binario; proporciona el DTS decompilado para comparación semántica

Los estados `INCONCLUSIVE`/`DIFFERENT (INCOMPLETE)` no prueban equivalencia.
La heurística de mapeo DTS sólo prioriza candidatos por `compatible` y ruta;
revisa o fija los pares ambiguos con `--dts-map` antes de portar cambios.
