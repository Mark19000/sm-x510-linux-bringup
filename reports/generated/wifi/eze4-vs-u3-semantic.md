# SM-X510 EZE4 frente a fuente U3: comparación DTS semántica

Informe generado por `tools/dts_semantic_diff.py`. La comparación es
conservadora: ignora sólo la ortografía de etiquetas, normaliza listas de
cadenas NUL y mapea un phandle a una ruta únicamente cuando su definición
local o una referencia explícita del par demuestra el destino. Un resultado
`INCONCLUSIVE`/`INCOMPLETE` no es una equivalencia.

## Evidencia de mapeo U3/EZE4

- Entrada U3: `sources/wifi-kernel/arch/arm64/boot/dts/exynos/s5e8835.dts` y
  `.../samsung/gts9fewifi/gts9fewifi_eur_open_w00_r04.dts`, del árbol
  `X510XXU3BXDG` (commit `9a752a83347461b3785711760ba925fcabea3071`),
  identificado como U3/Android 14 en
  [`docs/00-seguridad-y-modelos.md`](../../../docs/00-seguridad-y-modelos.md).
- Entrada EZE4 base: `artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts`,
  extraída de `vendor_boot.img`; el manifiesto conserva el mismo FDT y
  `artifacts/stock/firmware-metadata.txt` identifica el AP como
  `X510XXUCEZE4`/SM-X510/EUX.
- Entrada EZE4 overlay r04: `artifacts/stock/dt/overlays/overlay-02-...dts`
  (también `recovery/fdt-02-offset-044fe3b8.dts`), con
  `compatible = "SAMSUNG,GTS9FEWIFI_EUR_OPEN", "SAMSUNG,S5E8835"` y rango
  `dtbo-hw_rev = 4..32`, que coincide con `dtbo.img`/`recovery/manifest.json`.
  Ambas copias DTS tienen SHA-256
  `e236e27ea08d8135702f7848753ceed975273aa41393b5e622864161395e6bdd`.

El mapeo es por SoC/placa, compatible y rango de revisión observado; no prueba
que el bootloader de una unidad concreta haya elegido r04 ni que el código U3
sea arrancable en EZE4.

Comando base reproducible (el informe limita el detalle a 32 filas):

```sh
python3 tools/dts_semantic_diff.py --detail-limit 32 \
  sources/wifi-kernel/arch/arm64/boot/dts/exynos/s5e8835.dts \
  artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts
```

## Comparación del DT base

- Left: `sources/wifi-kernel/arch/arm64/boot/dts/exynos/s5e8835.dts`
- Right: `artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts`
- Status: **DIFFERENT (INCOMPLETE)**
- Nodes: 1479 left / 1493 right
- Material differences: 37
- Phandle renumberings ignored by path: 602
- Unresolved references: 10

## Phandle renumbering

| path | left | right |
|---|---:|---:|
| `/BIG@10080000` | `0x102` | `0x103` |
| `/CP@10080000` | `0x11e` | `0x11f` |
| `/G3D@10080000` | `0x108` | `0x109` |
| `/ISP@10080000` | `0x114` | `0x115` |
| `/LITTLE@10080000` | `0x105` | `0x106` |
| `/NPU@10080000` | `0x10b` | `0x10c` |
| `/abox-gic@14ef0000` | `0xe0` | `0xe1` |
| `/abox@14e50000` | `0x1cf` | `0x1d1` |
| `/abox@14e50000/abox-core@14e55000` | `0x1d0` | `0x1d2` |
| `/abox@14e50000/abox-core@14e55000/abox-firmware-dram0` | `0x1d2` | `0x1d4` |
| `/abox@14e50000/abox-core@14e55000/abox-firmware-sram0` | `0x1d1` | `0x1d3` |
| `/abox@14e50000/abox-core@14e55080` | `0x1d3` | `0x1d5` |
| `/abox@14e50000/abox-core@14e55100` | `0x1d4` | `0x1d6` |
| `/abox@14e50000/abox-ddma@14e56000` | `0x1f9` | `0x1fb` |
| `/abox@14e50000/abox-ddma@14e56100` | `0x1fa` | `0x1fc` |
| `/abox@14e50000/abox-ddma@14e56200` | `0x1fb` | `0x1fd` |
| `/abox@14e50000/abox-ddma@14e56300` | `0x1fc` | `0x1fe` |
| `/abox@14e50000/abox-ddma@14e56400` | `0x1fd` | `0x1ff` |
| `/abox@14e50000/abox-ddma@14e56500` | `0x1fe` | `0x200` |
| `/abox@14e50000/abox-debug@0` | `0x20d` | `0x20f` |
| `/abox@14e50000/abox-dsif@14e50de0` | `0x206` | `0x208` |
| `/abox@14e50000/abox-dual@14e53080` | `0x1ed` | `0x1ef` |
| `/abox@14e50000/abox-dual@14e53180` | `0x1ee` | `0x1f0` |
| `/abox@14e50000/abox-dual@14e53280` | `0x1ef` | `0x1f1` |
| `/abox@14e50000/abox-dual@14e53380` | `0x1f0` | `0x1f2` |
| `/abox@14e50000/abox-dual@14e53480` | `0x1f1` | `0x1f3` |
| `/abox@14e50000/abox-dual@14e53580` | `0x1f2` | `0x1f4` |
| `/abox@14e50000/abox-dual@14e53680` | `0x1f3` | `0x1f5` |
| `/abox@14e50000/abox-dual@14e53780` | `0x1f4` | `0x1f6` |
| `/abox@14e50000/abox-dual@14e53880` | `0x1f5` | `0x1f7` |
| `/abox@14e50000/abox-dual@14e53980` | `0x1f6` | `0x1f8` |
| `/abox@14e50000/abox-dual@14e53a80` | `0x1f7` | `0x1f9` |

Only the first 32 renumberings are shown; total is 602.

## Differences by path

| kind | path | property | left | right |
|---|---|---|---|---|
| `property-changed` | `/__local_fixups__/dss` | `memory-region` | `[["cells",[["null-ref",0],["ref","/reserved-memory/debug_snapshot/log_s2d"],["ref","/reserved-memory/debug_snapshot/log_kevents"],["ref","/reserved-memory/log_itmon"],["ref","/reserved-memory/vframe"],["ref","/reserved-memory/tui"],["ref","/set@0001"],["ref","/set@0102"],["ref","/set@0300"]]]]` | `[["cells",[["null-ref",0],["ref","/reserved-memory/debug_snapshot/log_s2d"],["ref","/reserved-memory/debug_snapshot/log_kevents"],["ref","/reserved-memory/debug_kinfo_reserved@fcfff000"],["ref","/reserved-memory/vstream"],["ref","/reserved-memory/secure_camera"],["ref","/set@0000"],["ref","/set@0101"],["ref","/set@0202"],["ref","/set@0400"]]]]` |
| `property-changed` | `/__local_fixups__/dwmmc2@100E0000` | `pinctrl-0` | `[["cells",[["null-ref",0],["ref","/reserved-memory/debug_snapshot/log_s2d"],["ref","/reserved-memory/debug_snapshot/log_kevents"],["ref","/reserved-memory/log_itmon"]]]]` | `[["cells",[["null-ref",0],["ref","/reserved-memory/debug_snapshot/log_s2d"],["ref","/reserved-memory/debug_snapshot/log_kevents"],["ref","/reserved-memory/debug_kinfo_reserved@fcfff000"]]]]` |
| `property-added` | `/__local_fixups__/mali@10300000` | `clocks` | `-` | `<0x0>` |
| `node-added` | `/__local_fixups__/pinctrl@11430000/gph1` | `-` | `-` | `-` |
| `property-added` | `/__symbols__` | `gph1` | `-` | `"/pinctrl@11430000/gph1"` |
| `property-added` | `/__symbols__` | `wdtmsg` | `-` | `"/reserved-memory/wdtmsg"` |
| `property-added` | `/drmdsim@0x148C0000` | `disable-shdw-vss-updt` | `-` | `<0x1>` |
| `property-changed` | `/dss` | `memory-region` | `[["cells",[["ref","/reserved-memory/debug_snapshot/header"],["ref","/reserved-memory/debug_snapshot/log_kernel"],["ref","/reserved-memory/debug_snapshot/log_s2d"],["ref","/reserved-memory/debug_snapshot/log_first"],["ref","/reserved-memory/debug_snapshot/log_arrdumpreset"],["ref","/reserved-memory/debug_snapshot/log_platform"],["ref","/reserved-memory/debug_snapshot/log_kevents"],["ref","/reserved-memory/log_backtrace"],["ref","/reserved-memory/debug_snapshot/log_kevents_small"]]]]` | `[["cells",[["ref","/reserved-memory/debug_snapshot/header"],["ref","/reserved-memory/debug_snapshot/log_kernel"],["ref","/reserved-memory/debug_snapshot/log_s2d"],["ref","/reserved-memory/debug_snapshot/log_first"],["ref","/reserved-memory/debug_snapshot/log_arrdumpreset"],["ref","/reserved-memory/debug_snapshot/log_platform"],["ref","/reserved-memory/debug_snapshot/log_kevents"],["ref","/reserved-memory/log_backtrace"],["ref","/reserved-memory/debug_snapshot/log_kevents_small"],["ref","/reserved-memory/wdtmsg"]]]]` |
| `node-added` | `/exynos_devfreq/devfreq_disp@17000040/skew` | `-` | `-` | `-` |
| `node-added` | `/exynos_devfreq/devfreq_disp@17000040/skew/skew_1` | `-` | `-` | `-` |
| `property-removed` | `/icpu@15910000/firmware/binary` | `#permanent` | `(boolean)` | `-` |
| `property-added` | `/icpu@15910000/firmware/binary` | `permanent` | `-` | `(boolean)` |
| `property-added` | `/mali@10300000` | `clock-names` | `-` | `"gpu_clock"` |
| `property-added` | `/mali@10300000` | `clocks` | `-` | `<&clock> <0x898>` |
| `property-changed` | `/mfc` | `debug_mode` | `[["cells",[["number",1]]]]` | `[["cells",[["number",0]]]]` |
| `node-added` | `/pinctrl@11430000/gph1` | `-` | `-` | `-` |
| `phandle-added` | `/pinctrl@11430000/gph1` | `phandle` | `-` | `372` |
| `node-added` | `/reserved-memory/wdtmsg` | `-` | `-` | `-` |
| `phandle-added` | `/reserved-memory/wdtmsg` | `phandle` | `-` | `11` |
| `property-added` | `/set@0001/tex` | `foreground` | `-` | `<0x1>` |
| `node-added` | `/set@0501/cpuidle_gov` | `-` | `-` | `-` |
| `property-removed` | `/set@0501/ecs_dynamic` | `dynamic-busy-ratio` | `<0x32 0x32>` | `-` |
| `node-added` | `/set@0501/fclamp` | `-` | `-` | `-` |
| `node-added` | `/set@0501/fclamp/monitor-group` | `-` | `-` | `-` |
| `node-added` | `/set@0501/gsc` | `-` | `-` | `-` |
| `node-added` | `/set@0501/gsc/monitor-group` | `-` | `-` | `-` |
| `node-added` | `/set@0501/ontime` | `-` | `-` | `-` |
| `node-added` | `/set@0501/ontime/domain0` | `-` | `-` | `-` |
| `node-added` | `/set@0501/ontime/domain1` | `-` | `-` | `-` |
| `node-added` | `/set@0501/should_spread` | `-` | `-` | `-` |
| `property-added` | `/set@0501/tex` | `camera-daemon` | `-` | `<0x1>` |
| `property-changed` | `/set@0501/tex` | `prio` | `[["cells",[["number",119]]]]` | `[["cells",[["number",110]]]]` |

Only the first 32 differences are shown; total is 37.

## Unresolved/incomplete evidence

The following references were not resolved to a local node; therefore the result cannot be called equivalent:

- `artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts: unresolved &camera_rmem in memory-region`
- `artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts: unresolved &sysmmu_brp_s0 in iommus`
- `artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts: unresolved &sysmmu_csis_s0 in iommus`
- `artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts: unresolved &sysmmu_cstat_s0 in iommus`
- `artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts: unresolved &sysmmu_rgbp_s0 in iommus`
- `artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts: unresolved &sysmmu_yuvp_s0 in iommus`
- `artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts: unresolved &wlbt_hw_ver in wlbt_hcf`
- `sources/wifi-kernel/arch/arm64/boot/dts/exynos/s5e8835.dts: external phandle sentinel in iommus`
- `sources/wifi-kernel/arch/arm64/boot/dts/exynos/s5e8835.dts: external phandle sentinel in memory-region`
- `sources/wifi-kernel/arch/arm64/boot/dts/exynos/s5e8835.dts: external phandle sentinel in wlbt_hcf`

## Comparación del overlay Wi-Fi r04

La misma herramienta se ejecutó sobre la entrada U3 r04 y el overlay EZE4
r04 (`overlay-02`), con el resultado siguiente:

- 1215 nodos en ambos lados;
- 17 diferencias materiales;
- 0 renumeraciones de phandle en esta entrada;
- 207 referencias externas sin resolver: el DTS U3 usa con frecuencia
  `0xffffffff` y el decompilado EZE4 conserva etiquetas del árbol base.

| tipo | ruta | propiedad | cambio observado |
|---|---|---|---|
| cambio | `/fragment@smd/__overlay__/samsung_mobile_device/battery` | `battery_full_capacity` | `0x276a` → `0x1f40` |
| cambio | `/fragment@smd/__overlay__/samsung_mobile_device/pogo_kpd` | `input_name` | añade DX725, DX720 y Neos |
| cambio | `/fragment@smd/__overlay__/samsung_mobile_device/pogo_kpd` | `support_keyboard_model` | añade tres pares de modelo |
| añadido | `/fragment@smd/__overlay__/samsung_mobile_device/pogo_touchpad` | `max` | `<0x578 0x324>` |
| cambio | `/fragment@modemif/__overlay__/cpif` | `pktproc_ul_hiprio_ack_only` | `1` → `0` |
| añadido | `/fragment@camera/__overlay__/is_sensor_imx355@34` | `pinning_setfile`, `preload_setfile` | booleanas |
| renombrado + propiedades | `/fragment@model/__overlay__/sec-bootstat/thermal-zones` | `BIG/G3D/ISP/LITTLE` → `zone_big/zone_g3d/zone_isp/zone_lit` | rutas nuevas; revisar `zone-name` |

Esto respalda la clasificación previa de cambios sustantivos en batería,
teclado/touchpad, térmica, cámara y CP. La salida completa reproducible para
el par de overlays es:

```sh
python3 tools/dts_semantic_diff.py --detail-limit 32 \
  sources/wifi-kernel/arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r04.dts \
  artifacts/stock/dt/overlays/overlay-02-id-00000000-rev-00000000.dts
```

## Lectura y limitaciones

El DT base contiene 602 renumeraciones que el comparador puede asociar a rutas,
pero todavía 37 diferencias materiales y 10 referencias externas sin resolver;
entre ellas hay nodos auxiliares `__symbols__`/`__local_fixups__` propios de la
representación con overlays, que deben interpretarse junto al DTB final.
El overlay conserva 17 diferencias materiales. Las referencias externas se
tratan como un marcador opaco sólo para no llenar la tabla de falsos cambios;
esa normalización incompleta fuerza el estado `INCOMPLETE` y evita afirmar
equivalencia. No se comparan DTSI incluidos ni se reconstruye un árbol efectivo
con `fdtoverlay`; validar el hardware seleccionado requiere el DT en ejecución
o evidencia del bootloader.
