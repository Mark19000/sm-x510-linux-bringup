# 3. Matriz Android/downstream frente a Linux mainline

> En este checkout no existe `docs/03-comparacion-drivers.md`; el documento
> canónico es este `docs/03-matriz-de-drivers.md`. La matriz exhaustiva y las
> búsquedas reproducibles están en [`reports/generated/wifi/driver-matrix.md`](../reports/generated/wifi/driver-matrix.md).

## Identidad y criterio

La comparación usa el snapshot mainline `26260251022f` (21-08-2026), el
downstream X510 U3 `9a752a833474` (X510XXU3BXDG, 5.15.123) y el DT stock EZE4
extraído de `vendor_boot`/`dtbo`. El código downstream es una referencia U3, no
el código exacto de `X510XXUCEZE4`; el objetivo declarado es `SM-X510` Wi-Fi
(`configs/target-sm-x510.env:3-7`, `sources/README.md:7-10`).

“Exacto” significa que mainline contiene la misma cadena en un `of_device_id` o
binding. “Familia” significa código relacionado que todavía necesita datos,
clocks, pinctrl y validación S5E8835. Ninguna coincidencia de texto demuestra
compatibilidad eléctrica o funcional. El checkout mainline es sparse; las
búsquedas de contenido se limitaron a sus ficheros presentes (`rg`), y la
existencia/ausencia de rutas se contrastó con `git ls-tree` cuando corresponde.

## Resumen por bloque

| Subsistema | DT/driver downstream observado | Mainline local | Trabajo/bloqueo | Prioridad |
|---|---|---|---|---:|
| CPU, PSCI, GIC, timer, DMA | `arm,psci-1.0`, `arm,gic-400`, `arm,armv8-timer`, `arm,pl330` | exacto/genérico | validar IRQ, topología y clocks | 1 |
| UART | `samsung,exynos-uart` + USI v2 | familia Samsung; no S5E8835 | entrada de datos S5E8835, pinmux, clocks, earlycon; UART0 stock está disabled | 1 |
| HSI2C / USI | `samsung,exynos5-hsi2c` | cadena exacta; USI sólo otras familias | validar variante USI, FIFO, IRQ, clocks y pinctrl | 2 |
| SPI / PWM | `samsung,exynos-spi`, `samsung,s3c6400-pwm` | SPI familia Exynos850; PWM binding exacto, proveedor fuera del sparse checkout | añadir datos S5E8835, prescalers y DMA; no confundir timer PWM con proveedor | 2 |
| Clocks / CMU | `samsung,s5e8835-clock`, CAL/ACPM privado | sin S5E8835 | portar CMU por dominios, resets y fuentes | 1 |
| Pinctrl / GPIO / EINT | seis nodos `samsung,s5e8835-pinctrl` | familia Exynos; sin S5E8835 | tablas de bancos, EINT/wakeup y pulls por hw-rev | 1 |
| PMU / ACPM / power domains | `samsung,exynos-pmu`, `samsung,exynos-pd` | PMU de otras familias; sin `exynos-pd` S5E8835 | mínimo de PMU/ACPM y dominios antes de UFS/USB/DPU/GPU | 1 |
| IOMMU | `samsung,sysmmu-v8` | sólo familia `samsung,exynos-sysmmu` | portar v8 antes de DPU, cámara y GPU | 2 |
| UFS | `samsung,exynos-ufs`, FMP/PHY/calibración Samsung | core Exynos para Exynos7/AutoV9/GS101; sin S5E8835 | PHY, calibración, clocks, reset, PD, SysMMU; empezar read-only | 2 |
| USB DWC3 | `synopsys,dwc3` + `samsung,exynos-dwusb` | core exacto; glue sólo familia | glue S5E8835, clocks y role switch | 2 |
| USB PHY | `samsung,exynos-usbdrd-phy` | familia Exynos5; sin cadena S5E8835 | USB2/USB3, calibración/OTP, Type-C y PMU | 2 |
| Display DPU | `samsung,exynos-decon/dpp/dsim` | DRM Exynos antiguo/DSI; sin S5E8835 | port grande: atomic, SysMMU, CMU, DSIM y MIPI PHY | 3 |
| Panel LCD | candidatos HX83102J BOE / NT36523N CSOT; `samsung,panel-drv` privado | familias HX83102 y NT36523, otros paneles | seleccionar por overlay/ID; verificar secuencias, timings, reguladores y backlight | 3 |
| GPU | `arm,mali` downstream; variante no inferida del `compatible` | Panfrost existe en el árbol Git, sin `arm,mali`/S5E8835 verificado localmente | PD, clocks, reset, SysMMU y firmware | 4 |
| Táctil | Novatek/Himax privados: `nvt_ts_spi`, `himax,hxcommon` | otros NT/HX; no esos compatibles | identificar IC real, SPI, IRQ/reset y firmware | 4 |
| Wacom | `wacom,w90xx` | otros W900/I2C/HID | protocolo, GPIO y energía específicos | 4 |
| Wi-Fi / BT | SCSC: `samsung,scsc_wifibt`, `exynos,wifibt_if` | ausente | driver/firmware/protocolo, memoria, IRQ, PMU/QoS; bloque difícil | 5 |
| Audio | ABOX + `cirrus,cs35l45` | codec CS35L45 exacto; ABOX/machine ausentes | DSP/firmware, ASoC machine y rutas | 5 |
| PMIC / carga / USB-PD | SM5714, SM5440, `sec-battery`, S2MPU15/16 | ausente para esos IDs | MFD, regulator, charger, fuel gauge, Type-C; no tocar límites sin medición | 5 |
| Cámaras / NPU | stack Samsung privado | sin plataforma S5E8835 equivalente | no bloquear primer arranque; requiere IOMMU, firmware y sensores | 6 |
| Módem/CPIF | referencia X516 5G | no aplica a X510 Wi-Fi | mantener fuera y deshabilitado; no inferir hardware de X516 | 6/N/A |

## Dependencias de bring-up

```text
PSCI + GIC + timer + UART verificable
          |
          +--> CMU/clock + pinctrl/GPIO + PMU/ACPM
                       |
                       +--> I2C/SPI/PWM --> sensores/entrada
                       +--> SysMMU --> UFS (read-only), USB
                       +--> DPU/DSIM/PHY --> panel
                       +--> GPU/audio/Wi-Fi/PD/cámara/NPU
```

La primera imagen debe priorizar consola y diagnóstico. No se habilita UART0
sólo porque tenga un nodo stock: el DT observado lo deja disabled y aún hay que
verificar pinmux y destino. UFS, USB y display requieren datos S5E8835 aunque el
core mainline exista. Wi-Fi/BT, ABOX, carga y cámara/NPU se dejan para después.

## Bloqueadores explícitos de M2/M3

M2 es el primer mensaje del kernel y M3 es `/init` como PID 1 (`README.md:83-94`).
Los bloqueadores de infraestructura son el DT base EZE4 correcto, PSCI/GIC/timer,
CMU/clock, pinctrl/GPIO, PMU/ACPM mínimo y un canal observable (UART validado,
USB previamente probado o pstore). M3 añade IRQ/SMP estables y un initramfs
válido con `/init`; no necesita UFS, pantalla, táctil, GPU, Wi-Fi, audio ni
carga. La prueba inicial recomendada usa initramfs sin módulos y no activa esos
periféricos (`docs/12-preflight-primera-prueba.md:94-111`).

UFS (M5), USB completo, DPU/panel, táctil/Wacom, GPU, Wi-Fi/BT SCSC, ABOX,
SM5714/SM5440, cámaras/NPU, sensores y CPIF pueden esperar a M5/M6/M7. La
matriz detallada lista las dependencias que habrá que resolver en cada fase.

## Evidencia y límites

- El DT base stock identifica `samsung,s5e8835` y contiene los bloques de
  infraestructura; los overlays EZE4 incluyen rangos hw-rev 0, 1--3 y 4--32.
  No se conoce cuál selecciona el bootloader de la unidad.
- El overlay observado contiene dos candidatos de panel y dos familias de
  táctil; no se debe convertir esa lista en una afirmación de BOM.
- `reports/generated/wifi/compatibles.md` registra 259 cadenas, 12 coincidencias
  exactas y 247 sin coincidencia. Es una comparación textual, no una prueba de
  funcionamiento.
- No se compiló ni se probó ningún driver en la tablet y no se flasheó nada.

La matriz completa conserva las rutas y líneas de `rg` y `git ls-tree` para
repetir cada conclusión sin acceder a Internet.
