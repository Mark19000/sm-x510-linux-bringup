# Auditoría de drivers: X510 downstream frente a Linux mainline

## Alcance y método

Esta matriz compara únicamente las fuentes locales ya descargadas y el DT stock
extraído de EZE4. No es una afirmación de que todos los nodos estén poblados en
la unidad ni de que un `compatible` compartido sea eléctricamente intercambiable.

| Fuente | Identidad usada |
|---|---|
| Objetivo | `SM-X510`, variante Wi-Fi, AP `X510XXUCEZE4` (`configs/target-sm-x510.env:3-7`) |
| DT observado | base `artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts` y tres overlays EZE4 (`artifacts/stock/dt/overlays/`) |
| Samsung downstream | `sources/wifi-kernel`, commit `9a752a833474`, X510 `X510XXU3BXDG`, 5.15.123 |
| Mainline | `sources/mainline-kernel`, commit `26260251022f`, 2026-08-21 |

El código Samsung es U3 y sirve como referencia, no como fuente exacta EZE4
(`sources/README.md:7-10`). El DT stock contiene overlays para hw-rev 0, 1--3 y
4--32; sin el hw-rev efectivo no se puede elegir r00, r01 o r04
(`docs/02-analisis-device-tree.md:29-48`). Por eso los paneles y controladores
táctiles se mantienen como candidatos.

Se marcaron como **exactos** sólo los casos en que la cadena aparece en el
`of_device_id`/binding mainline. Una familia (por ejemplo Exynos850) indica
que hay código reutilizable para estudiar, no una sustitución segura. El
checkout mainline es sparse (`git -C sources/mainline-kernel sparse-checkout
list`); las búsquedas de contenido (`rg`) sólo cubren los ficheros presentes.
Cuando una ruta no está en el sparse checkout se comprobó su existencia con
`git ls-tree -r HEAD`, sin convertir la falta de un blob local en un negativo.

## Matriz por bloque

Prioridad: 1 = bring-up mínimo y consola, 2 = almacenamiento/periférico básico,
3 = display, 4 = entrada/GPU, 5 = funciones Android/energía, 6 = funciones
opcionales o de otra variante.

| Bloque y compatibles observados | Driver downstream Samsung | Soporte en mainline de este snapshot | Dependencias, bloqueo y prioridad | Evidencia local (rutas/grep) |
|---|---|---|---|---|
| **CPU, PSCI, GIC, timer y DMA**: `arm,psci-1.0`, `arm,gic-400`, `arm,armv8-timer`, `arm,pl330` | Descriptores genéricos en `s5e8835.dts`; no hay que importar política Android para arrancar | Exacto/genérico: PSCI binding, GIC, timer ARM y PL330 | Validar `interrupt-parent`, topología y clocks antes de habilitar más IP. **P1** | DT stock `:5540,9936,9972,10186`; mainline `drivers/clocksource/arm_arch_timer.c:1217`, `drivers/irqchip/irq-gic.c:1515`, `drivers/of/platform.c:481`, bindings PSCI/DMA |
| **UART**: `samsung,exynos-uart` | `drivers/tty/serial/exynos_tty.c`, tabla S5E8835 y USI v2 | No hay `samsung,exynos-uart` en los ficheros mainline presentes; `samsung_tty.c` sólo tiene datos para S3C/S5PV210/Exynos4210/5433/850 y otros | Añadir datos/compatible S5E8835, clocks, pinctrl y earlycon. El UART0 stock está deshabilitado; no asumir que sus pines son externos. **P1** | DT stock `:4352`; downstream `sources/wifi-kernel/drivers/tty/serial/exynos_tty.c:3446`; mainline `drivers/tty/serial/samsung_tty.c:2632-2644`; `rg -n -F 'samsung,exynos-uart' sources/mainline-kernel` = 0 |
| **HSI2C / USI**: `samsung,exynos5-hsi2c` | `drivers/i2c/busses/i2c-exynos5.c`; integración downstream de USI v2 | Compatible exacto para el bus genérico (`drivers/i2c/busses/i2c-exynos5.c:251`), pero el binding sólo documenta familias previas; USI mainline enumera Exynos850/8895 y no S5E8835 | Confirmar variante USI, clocks, IRQ, pinctrl y modo FIFO; no extrapolar datos Exynos850. **P2** | DT stock `:3432`; downstream `.../i2c-exynos5.c:292`; mainline `.../i2c-exynos5.c:251`, `drivers/soc/samsung/exynos-usi.c:122-125`; `Documentation/devicetree/bindings/i2c/i2c-exynos5.yaml:47` |
| **SPI**: `samsung,exynos-spi` | `drivers/spi/spi-s3c64xx.c`, entrada genérica downstream | Mainline tiene la familia `samsung,exynos850-spi`, no la cadena stock `samsung,exynos-spi` | Añadir/validar datos S5E8835 y clocks/DMAs antes de usar touch, Wacom o sensores. **P2/P4 según consumidor** | DT stock `:4068`; downstream `.../spi-s3c64xx.c:2414`; mainline `.../spi-s3c64xx.c:1635-1638` |
| **PWM**: `samsung,s3c6400-pwm` | Proveedor `drivers/pwm/pwm-samsung.c:641` | Binding exacto (`Documentation/devicetree/bindings/pwm/pwm-samsung.yaml:26`), pero el checkout no contiene el proveedor; el árbol Git sí contiene `drivers/pwm/pwm-samsung.c`; también hay timer PWM en `drivers/clocksource/samsung_pwm_timer.c:489` | Separar “timer reconocido” de “PWM consumidor”; comprobar clocks/prescalers y no usarlo como prueba de soporte de panel. **P2** | DT stock `:10135`; downstream `.../pwm-samsung.c:641`; `git -C sources/mainline-kernel ls-tree -r --name-only HEAD -- drivers/pwm/pwm-samsung.c` |
| **Clocks / CMU**: `samsung,s5e8835-clock`, `samsung,s5e8835-oscclk` | `drivers/clk/samsung/clk-s5e8835.c` más CAL/ACPM y DVFS privados | No hay `samsung,s5e8835*` en los ficheros mainline presentes; sólo patrones de Exynos850/990/2200/AutoV9 | Bloque raíz: portar bindings y CMU por dominios, reset y fuentes de reloj; no copiar un driver monolítico con valores de otro SoC. **P1** | DT stock `:9965`; downstream `sources/wifi-kernel/drivers/clk/samsung/clk-s5e8835.c:568,666`; `rg -n -F 'samsung,s5e8835' sources/mainline-kernel` = 0; downstream `drivers/soc/samsung/cal-if/`, `drivers/soc/samsung/acpm/` |
| **Pinctrl / GPIO / EINT**: seis nodos `samsung,s5e8835-pinctrl` | `drivers/pinctrl/samsung/pinctrl-samsung.c`, tablas S5E8835 y EINT/wakeup | No hay S5E8835 en los ficheros mainline presentes; la familia mainline enumera Exynos850, S5E9925/S5E9935 y otros | Portar bancos, offsets, EINT y wakeup; revisar pull changes por hw-rev antes de activar buses. **P1** | DT stock `:1723,1900` y cuatro nodos más; downstream `.../pinctrl-samsung.c:1547`; mainline `.../pinctrl-samsung.c:1501`; binding `samsung,pinctrl.yaml`; `rg -n -F 'samsung,s5e8835' sources/mainline-kernel` = 0 |
| **PMU / ACPM / reset / power domains**: `samsung,exynos-pmu`, `samsung,exynos-pd` | `drivers/soc/samsung/exynos-pmu.c`, `exynos-pd/`, ACPM IPC/CAL | PMU sólo tiene datos para SoC anteriores, Exynos850 y GS101 (`drivers/soc/samsung/exynos-pmu.c:124-151`); no hay `exynos-pd` S5E8835 en los ficheros mainline presentes | Dependencia de clocks, UFS, USB, display, GPU y suspend; implementar mínimo verificable y dominios esenciales. **P1** | DT stock `:9978`; downstream `.../exynos-pd.c:34,539`; mainline `.../exynos-pmu.c:151`; `rg -n -F 'samsung,exynos-pd' sources/mainline-kernel` = 0 |
| **IOMMU / SysMMU**: `samsung,sysmmu-v8` | `drivers/iommu/samsung/samsung-iommu.c:1568` | Sólo familia antigua `samsung,exynos-sysmmu` (`drivers/iommu/exynos-iommu.c:870`); no `sysmmu-v8` en los ficheros mainline presentes | Bloquea DPU, cámara y GPU; portar datos v8, fault handling y bindings antes de esos consumidores. **P2** | DT stock `:4688`; downstream `.../samsung-iommu.c:1568`; mainline `.../exynos-iommu.c:870`; `rg -n -F 'samsung,sysmmu-v8' sources/mainline-kernel` = 0 |
| **UFS**: `samsung,exynos-ufs` | `drivers/scsi/ufs/ufs-exynos.c` con FMP, PM QoS y calibración; PHY Samsung | `drivers/ufs/host/ufs-exynos.c` sólo declara GS101, Exynos7, AutoV9/AutoV920 y Tesla; binding `samsung,exynos-ufs.yaml` no enumera S5E8835 | Necesita PHY/calibrado, clocks, reset, power-domain y SysMMU. Arrancar read-only después de la infraestructura. **P2** | DT stock `:7061`; downstream `.../ufs-exynos.c:2689`, `.../phy-samsung-ufs.c:75`; mainline `.../ufs-exynos.c:2312-2327`, binding `ufs/samsung,exynos-ufs.yaml:18-25`; `rg -n 'compatible = "samsung,exynos-ufs"' sources/mainline-kernel` = 0 |
| **USB DWC3 core**: `synopsys,dwc3` | Core DWC3 más glue `drivers/usb/dwc3/dwc3-exynos.c` | Core genérico exacto en mainline; el glue S5E8835 no (`dwc3-exynos.c` mainline sólo lista hasta Exynos850/GS101/AutoV920) | Puede probarse el core sólo con DT/clocks correctos; no confundirlo con USB funcional. **P2** | DT stock `:6805`/glue `:6778`; downstream `.../dwc3-exynos.c:98`; mainline `drivers/usb/dwc3/core.c:2828-2831`, glue `.../dwc3-exynos.c:198-219`; `rg -n -F 'samsung,exynos-dwusb' sources/mainline-kernel` = 0 |
| **USB PHY / role switch**: `samsung,exynos-usbdrd-phy` | `drivers/phy/samsung/phy-exynos-usbdrd.c`, calibración/OTP y Type-C downstream | Familia `phy-exynos5-usbdrd.c` (Exynos7/850/990/2200/GS101), sin `exynos-usbdrd-phy` S5E8835 | Portar PHY USB2/USB3, calibración, glue y role switch; depende de PMU/clock/pinctrl. **P2** | DT stock `:6827`; downstream `.../phy-exynos-usbdrd.c:2204` y `:41-54`; mainline `.../phy-exynos5-usbdrd.c:2878-2918`; `rg -n -F 'samsung,exynos-usbdrd-phy' sources/mainline-kernel` = 0 |
| **Display DPU / DECON / DPP / DSIM**: `samsung,exynos-decon`, `...-dpp`, `...-dsim` | `drivers/gpu/drm/samsung/dpu/` (DECON, DPP, DSIM y CAL Samsung) | Mainline sólo tiene DRM Exynos antiguo (Exynos5433/7) y DSI genérico; no hay los compatibles S5E8835 en los ficheros presentes | Gran port: clocks, pinctrl, PMU, SysMMU, DRM atomic y PHY MIPI. No bloquear consola por display. **P3** | DT stock `:5013,5188,5208`; downstream `.../drivers/gpu/drm/samsung/dpu/`; mainline `drivers/gpu/drm/exynos/exynos7_drm_decon.c:82-87`; `rg -n -e 'samsung,exynos-dpp' -e 'samsung,exynos-decon' -e 'samsung,exynos-dsim' sources/mainline-kernel` = 0 |
| **Panel LCD**: overlay ofrece `nt36523n_gts9fe_csot` y `hx83102j_gts9fe_boe`; nodo privado `samsung,panel-drv` | `drivers/gpu/drm/samsung/panel/tft_common/{nt36523n_gts9fe_csot,hx83102j_gts9fe_boe}.c` y secuencias Samsung | Mainline sí tiene familias Himax HX83102 y Novatek NT36523, pero sólo descriptores de otros paneles; no `gts9fe` | Seleccionar por ID/overlay efectivo y verificar comandos, timings, reguladores, reset y backlight. No afirmar BOE/CSOT montado. **P3** | Overlay 01 `:877-879,955-957` y panel privado `:1042`; downstream panel files; mainline `panel-himax-hx83102.c:1341-1368`, `panel-novatek-nt36523.c:1244-1257`, bindings `display/panel/{himax,hx83102,novatek,nt36523}.yaml` |
| **GPU**: `arm,mali` en DT; variante no inferida del `compatible` | Driver Mali downstream bajo `drivers/gpu/arm/v_r38p1` | El árbol Git mainline contiene la familia Panfrost, pero `drivers/gpu/drm/panfrost` no está en el sparse checkout; el compatible exacto no se puede auditar sin materializar esos blobs | Depende de clocks, power-domain, reset, SysMMU y firmware; prioridad posterior al framebuffer básico. **P4** | DT downstream `sources/wifi-kernel/arch/arm64/boot/dts/exynos/s5e8835.dts:6673-6674`; `git -C sources/mainline-kernel ls-tree -r --name-only HEAD -- drivers/gpu/drm/panfrost`; `rg -n -F 'arm,mali' sources/mainline-kernel` = 0 sólo en ficheros presentes |
| **Táctil SPI**: `nvt_ts_spi`, `novatek-mp-criteria-725C`, `himax,hxcommon` | Novatek `drivers/input/touchscreen/novatek/nt36523_tablet_spi/`; Himax `.../himax/hx83xxx_spi/` | Novatek mainline declara NT11205/NT36672A; Himax declara HX852ES/HX83112B; no estos compatibles SPI/`hxcommon` | Debe detectarse el IC real del overlay efectivo; requiere SPI, pinctrl, IRQ/reset, reguladores y firmware. No elegir Novatek/Himax por nombre de archivo. **P4** | Overlay 01 `:2396,2429,2758`; downstream `.../nt36xxx.c`, `.../himax_platform_SPI.c:1546`; mainline `drivers/input/touchscreen/novatek-nvt-ts.c:321-326`, `himax_hx852x.c:482-486`, `himax_hx83112b.c:417-418` |
| **Digitalizador Wacom**: `wacom,w90xx` | `drivers/input/wacom/wacom_i2c.c:3290` | Mainline tiene Wacom I2C/HID y `wacom_w9000.c`, pero compatibles W9002/W9007, no `w90xx` | Confirmar protocolo, GPIO, energía y bus; mantener independiente del táctil LCD. **P4** | Overlay 01 `:4391`; downstream `.../wacom_i2c.c:3290`; mainline `drivers/input/touchscreen/wacom_w9000.c:415-418` |
| **Wi-Fi / BT SCSC**: `samsung,scsc_wifibt`, `exynos,wifibt_if`, QoS | `drivers/misc/samsung/scsc/`, `platform_mif_s5e8835.c` y `drivers/net/wireless/scsc` | No hay SCSC en los ficheros mainline presentes y el árbol Git tampoco tiene `drivers/net/wireless/scsc` | Driver, firmware, memoria reservada, IRQ, PMU/QoS y protocolo son privados; no es un bloque razonable para el primer arranque. `a96t396_wifi` es otro nodo I2C del overlay, no prueba WLAN. **P5** | DT stock `:234,8442-8458`, overlay 01 `:2868-2869`; downstream `.../platform_mif_s5e8835.c:53-54`; `rg -n -F 'samsung,scsc_wifibt' sources/mainline-kernel` = 0; `git ls-tree ... drivers/net/wireless/scsc` vacío |
| **Audio**: `samsung,abox`, `samsung,abox-core`, `cirrus,cs35l45` | ABOX/machine `sound/soc/samsung/exynos/{abox,exynos8835_sound.c}` y codec downstream | Codec CS35L45 exacto (I2C/SPI y binding); no ABOX ni máquina Exynos8835 en los ficheros presentes | El codec aislado no produce audio: faltan DSP/firmware, ABOX, machine, clocks y rutas. **P5** | DT stock `:5846`; overlay 01 `:5287,5388`; downstream `.../abox_core.c:564`, `.../exynos8835_sound.c:1697`; mainline `sound/soc/codecs/cs35l45-i2c.c:50`, `cs35l45-spi.c:52`; `rg -n -F 'samsung,abox' sources/mainline-kernel` = 0 |
| **PMIC, carga y USB-PD**: `samsung,sm5714-charger`, `siliconmitus,sm5714mfd`, `siliconmitus,sm5440`, `samsung,sec-battery` | MFD/charger/fuel-gauge/Type-C SM5714, SM5440 y `sec-battery`; PMIC S2MPU15/16 | No hay drivers/compatibles de SM5714, SM5440, S2MPU15/16 ni `sec-battery` en los ficheros mainline presentes; sólo otros Silicon Mitus genéricos | Alto riesgo: no habilitar carga ni cambiar límites/reguladores sin esquema y mediciones; depende I2C, GPIO, IRQ y ACPM. **P5** | Overlay 01 `:264-277,2608-2609`; downstream `drivers/mfd/sm/sm5714/sm5714_core.c:448`, `drivers/usb/typec/sm/sm5714/sm5714_typec.c:4490`, `drivers/battery/common/sec_direct_charger.c:1171`; consultas `rg -n -F sm5714`, `sm5440` y `sec-battery` sobre mainline: 0 |
| **Cámaras / NPU / multimedia Samsung**: `samsung,exynos-is`, `samsung,exynos-npu` y sensores privados | `drivers/media/platform/exynos/camera`, `drivers/vision`/stack Samsung | El snapshot no tiene `drivers/media/platform/exynos` (`git ls-tree` vacío) ni un stack S5E8835/NPU equivalente; hay bindings de cámaras Exynos antiguas | No bloquear consola/UFS/USB por estos bloques; requieren IOMMU, clocks, firmware, memoria reservada y sensores identificados. **P6** | DT base `docs/02-analisis-device-tree.md:60-62`; compatibles en `reports/generated/wifi/compatibles.md`; `git -C sources/mainline-kernel ls-tree -r --name-only HEAD -- drivers/media/platform/exynos`; `git -C sources/mainline-kernel ls-tree -r --name-only HEAD -- drivers/vision` |
| **Módem/CPIF** (sólo referencia X516, no objetivo Wi-Fi) | Código CPIF/GNSS en la referencia 5G `sources/device-kernel` | No aplicable a `TARGET_VARIANT=wifi`; no habilitar nodos CP por similitud de SoC | Mantener deshabilitado y fuera del bring-up X510 Wi-Fi; no inferir hardware de la matriz X516. **P6/N/A** | `configs/target-sm-x510.env:3-4`; `sources/README.md:9`; `docs/02-analisis-device-tree.md:82-84` |

## Orden de bring-up que se desprende de la comparación

```text
PSCI + GIC + timer + UART (si sus pines son verificables)
        |
        +--> CMU/clock + pinctrl/GPIO + PMU/ACPM mínimo
                    |
                    +--> I2C/SPI/PWM --> sensores/entrada
                    +--> SysMMU --> UFS (read-only), USB
                    +--> DPU/DSIM/PHY --> panel (más tarde)
                    +--> GPU/audio/Wi-Fi/PD/cámara/NPU (después)
```

El primer objetivo seguro es una imagen de diagnóstico con PSCI/GIC/timer,
UART sólo tras verificar pinmux, y la infraestructura de clocks/pinctrl/PMU
aislada. UFS, USB y display no deben activarse sólo porque el core mainline
exista: cada uno requiere sus datos S5E8835. Wi-Fi/BT, audio ABOX, carga y
cámara/NPU quedan deliberadamente fuera del primer arranque.

## Bloqueadores explícitos de M2/M3

Los hitos del proyecto definen M2 como “primer mensaje del kernel” y M3 como
`/init` ejecutándose como PID 1 (`README.md:83-94`). Para esos dos hitos, los
bloqueadores de driver/DT son únicamente:

- **M2:** DT base correcto para EZE4, PSCI/GIC/timer, clocks/PMU mínimos, y un
  canal observable. El canal puede ser UART sólo si se valida pinmux/nivel y
  clock; el UART0 stock aparece disabled. Si se usa USB/pstore como alternativa,
  su ruta debe estar previamente demostrada, no asumida.
- **M3:** todo lo anterior, más IRQ/SMP estables y un initramfs con `devtmpfs`,
  formato y `/init` válidos. No hace falta UFS, pantalla, táctil, GPU, Wi-Fi,
  audio ni carga: el preflight recomienda `MODULES_MODE=none` y rootfs en
  initramfs para esta prueba (`docs/12-preflight-primera-prueba.md:94-111`).
- **Bloqueadores de infraestructura compartida:** CMU S5E8835, pinctrl/GPIO,
  PMU/ACPM y, sólo si el canal elegido lo necesita, UART/USB básico. El SysMMU,
  UFS, DPU, DSIM, PHY de pantalla, GPU y periféricos Android no deben entrar en
  M2/M3 por presión de “hacer más funcionar”.

Pueden esperar hasta los hitos posteriores (M5/M6/M7): UFS y particiones en
`ro`, USB host/role switch, DPU/DSIM/panel, táctil Novatek/Himax, Wacom,
Panfrost/Mali, Wi-Fi/BT SCSC, audio ABOX/CS35L45, SM5714/SM5440 y batería,
cámaras/NPU, sensores y CPIF. Esta separación evita que un fallo en un
periférico opcional o en una BOM aún no identificada oculte el motivo de un
fallo temprano.

Esta lista ordena el trabajo técnico; no abre la puerta a una prueba física.
Las puertas de fuente EZE4 exacta, hw-rev, AVB, restauración y observabilidad
siguen siendo las del preflight (`docs/12-preflight-primera-prueba.md`) y pueden
mantener el veredicto NO-GO aunque M2/M3 estén resueltos en laboratorio.

## Limitaciones y comprobaciones reproducibles

- `reports/generated/wifi/compatibles.md` es un informe mecánico (259 cadenas,
  12 coincidencias exactas); una coincidencia no demuestra funcionamiento.
- Las búsquedas de compatibles se hicieron con `rg -n PATTERN
  sources/mainline-kernel` sobre los ficheros locales, y la presencia de rutas
  no materializadas con `git ls-tree -r HEAD`; el checkout de trabajo es
  parcial y no se debe forzar una descarga de blobs para cerrar un negativo.
- No se recompiló ni se probó ningún driver en la tablet y no se flasheó nada.
- No se conoce el hw-rev efectivo ni la BOM (panel/touch/PMIC) de la unidad; las
  filas de candidatos se deben resolver con DT en ejecución, IDs del componente
  y mediciones de alimentación antes de portar comandos o límites.
