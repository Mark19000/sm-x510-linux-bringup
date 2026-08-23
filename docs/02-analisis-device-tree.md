# 2. Análisis de DTS/DTSI

## Fuentes examinadas

La unidad real usa `X510XXUCEZE4` (Android 16/U12). Ya tenemos el paquete AP
EUX exacto y sus DT binarios; todavía falta la publicación OSRC exacta. Por
tanto distinguimos **datos EZE4 observados** de **código U3 de referencia**.

- SM-X510 downstream 5.15.123, commit `9a752a8...`, importado de `X510XXU3BXDG`.
- SM-X516 downstream 5.15.153, commit `56f84616...`, importado de `X516BXXU7CYE1`.
- DT base EZE4 extraído de `vendor_boot.img` y tres entradas de `dtbo.img`.
- `arch/arm64/boot/dts/exynos/s5e8835.dts`: unas 12 400 líneas.
- overlays Wi-Fi `r00/r01/r04` y 5G `r00/r01/r02/r04`.
- Linux mainline snapshot `26260251022f...`, 21 de agosto de 2026.

Regenera los datos con:

```sh
make fetch VARIANT=wifi
make report VARIANT=wifi
# Para la X516:
make fetch VARIANT=5g
make report VARIANT=5g
```

Los resultados mecánicos quedan separados en
`reports/generated/wifi/compatibles.md` y `reports/generated/5g/compatibles.md`.

## Selección de revisión

| Archivo | `dtbo-hw_rev` | `dtbo-hw_rev_end` |
|---|---:|---:|
| r00 | 0 | 0 |
| r01 Wi-Fi | 1 | 3 |
| r01 5G | 1 | 1 |
| r02 5G | 2 | 3 |
| r04 | 4 | 32 |

La tabla EZE4 stock contiene exactamente esos tres rangos Wi-Fi: 0, 1–3 y
4–32. Eso confirma cómo se empaquetan las revisiones, pero no cuál eligió esta
unidad concreta. Para esa última pregunta aún necesitamos el hwrev que expone
el bootloader o el árbol efectivo de `/proc/device-tree`.

Entre revisiones cambian pull-ups/pull-downs de pinctrl, calibración del
magnetómetro y fragmentos de display, además de muchos phandles renumerados. No
elijas r04 porque sea el número más alto. La selección pertenece al
bootloader y debe confirmarse con el DT en ejecución o con los metadatos del
DTBO stock.

## Árbol base S5E8835

Bloques observados:

- 8 CPU y PSCI 1.0;
- GIC-400, temporizador ARM y PMU;
- reloj `samsung,s5e8835-clock` y seis controladores pinctrl;
- 16 UART, 29 HSI2C y 15 SPI definidos, casi todos deshabilitados por defecto;
- UFS embebido en `0x13500000` con calibración Samsung privada;
- DWC3 en `0x13200000` y PHY USB Samsung;
- DPU/DECON/DSIM, IOMMU v8 y Mali downstream;
- audio ABOX, cámaras, NPU, sensores, Wi-Fi/BT SCSC y memoria reservada;
- PMIC S2MPU15/S2MPU16 controlados mediante ACPM.

El nodo `/chosen` downstream fija una línea de kernel Android y rangos initrd.
UART0 está en `0x13800000`, tiene propiedades de debug, pero aparece
`status = "disabled"`. No se habilita automáticamente en este proyecto: primero
hay que localizar sus pines y comprobar si salen a un conector o sólo son
internos.

## Overlay de la Tab S9 FE

Los overlays identifican `SAMSUNG,GTS9FEWIFI_EUR_OPEN` o
`SAMSUNG,GTS9FE_EUR_OPEN` y añaden o modifican, entre otros:

- panel LCD BOE HX83102J o CSOT NT36523N, modos 90/60/30 Hz;
- táctil Novatek o Himax;
- digitalizador Wacom `wacom,w9`;
- amplificadores Cirrus CS35L45;
- carga/USB-PD Silicon Mitus SM5714 y carga directa SM5440;
- PMIC S2MPU15/S2MPU16;
- teclado/touchpad/pogo STM32;
- cámaras IMX355 y HI1337;
- teclas, sensores Hall, termistores y parámetros de batería;
- en la variante móvil, interfaces de módem/CP.

La existencia de dos paneles y dos controladores táctiles explica por qué no se
debe codificar una sola BOM. El kernel/DT debe detectar o seleccionar el
componente que realmente monta la unidad.

## Método para analizar tu firmware

```sh
brew install dtc lz4                 # macOS, sólo análisis
./scripts/extract-stock.sh AP_....tar.md5
```

Si tienes el ZIP completo, no extraigas primero el AP: en EZE4 ocuparía más de
11 GB y duplicaría innecesariamente el espacio. Usa el extractor en streaming:

```sh
make stock FIRMWARE=/ruta/SAMFW.COM_SM-X510_EUX_X510XXUCEZE4_....zip
```

El extractor se detiene si `artifacts/stock` ya contiene datos, para no mezclar
dos paquetes. Para repetir conscientemente la extracción exacta usa
`REPLACE_STOCK_OUTPUT=1 make stock FIRMWARE=...`; sólo sustituye `raw/`,
`images/`, `dt/` y sus metadatos generados.

El flujo `ZIP -> tar` extrae sólo `boot`, `init_boot`, `vendor_boot`, `dtbo`,
`recovery` y `vbmeta`. Omite deliberadamente `super.img`, calcula SHA-256 y no
escribe en la tablet.

La herramienta:

1. extrae el tar a una carpeta nueva;
2. descomprime imágenes LZ4;
3. interpreta la cabecera Android DTBO y separa todas las entradas;
4. busca FDT incrustados en `boot`, `vendor_boot` y `dtb`;
5. usa `dtc` para producir texto cuando está disponible;
6. calcula hashes.

Para recomponer un árbol efectivo hace falta saber qué entrada eligió el
bootloader. Con base y overlay correctos:

```sh
fdtoverlay -i base.dtb -o efectivo.dtb overlay.dtbo
dtc -I dtb -O dts -o efectivo.dts efectivo.dtb
```

Si `fdtoverlay` falla por símbolos/fixups, compara primero el DT en ejecución
obtenido por `collect-device.sh`; una base y un overlay de versiones distintas
son una causa frecuente.

## Diferencias medidas entre U3 y EZE4

Los tres overlays EZE4 se decompilaron y compararon con sus equivalentes U3.
Cada diff tiene unas 85 líneas y repite los mismos cambios sustantivos:

- `battery_full_capacity` pasa de `0x276a` a `0x1f40`;
- la tabla del teclado añade los modelos DX725, DX720 y Neos;
- los máximos del touchpad pasan a `0x578 × 0x324`;
- las zonas térmicas reciben nombres explícitos `zone_big`, `zone_lit`,
  `zone_g3d` y `zone_isp` con propiedad `zone-name`;
- `pktproc_ul_hiprio_ack_only` cambia de 1 a 0;
- la cámara IMX355 añade parámetros `pinning_setfile` y `preload_setfile`.

No son cambios cosméticos: batería, térmica, periféricos y cámara demuestran
por qué no debemos reutilizar el overlay U3 aunque compile.

El diff textual del DT base muestra unas 5 458 líneas, pero gran parte es
renumeración de phandles producida al decompilar. El comparador conservador
`tools/dts_semantic_diff.py` asocia por ruta 602 renumeraciones y separa 37
diferencias materiales; todavía deja 10 referencias externas sin resolver, por
lo que su veredicto correcto es `DIFFERENT (INCOMPLETE)`. En el overlay r04
encuentra 17 diferencias materiales y 207 referencias externas.

El informe completo y reproducible está en
[`reports/generated/wifi/eze4-vs-u3-semantic.md`](../reports/generated/wifi/eze4-vs-u3-semantic.md).
Entre los cambios base están una región reservada `wdtmsg`, GPIO `gph1`,
ajustes del scheduler EMS/on-time/gsc/fclamp y propiedades de reloj Mali. Antes
de portar un cambio hay que seguir sus referencias y comparar nodos por ruta,
no por número de phandle. La herramienta no expande DTSI ni aplica overlays y
nunca convierte evidencia incompleta en equivalencia.

## Limitaciones del informe automático

Una coincidencia textual de `compatible` sólo prueba que la cadena existe en el
checkout. Un driver puede necesitar datos específicos no implementados; y un
IP compatible puede usar una cadena distinta. La tabla automática sirve para
priorizar lectura de código. La decisión técnica está en la matriz manual del
capítulo siguiente.
