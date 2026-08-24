# Identidad de hardware SM-X510 U12/EZE4

Fecha de auditoría: 2026-08-24. Modo: sólo lectura sobre artefactos locales y documentación existente. No se ejecutó ADB ni se tocó la unidad.

## Resumen ejecutivo

- **Confirmado:** la unidad objetivo es `SM-X510` Wi-Fi con firmware `X510XXUCEZE4`, CSC `EUX` / `X510OXMCEZE4`, Android 16, One UI 8.5, parche `2026-05-05` y binario/revisión de bootloader registrada como U12.
- **No confirmado:** el valor numérico exacto de `hw_rev` de la placa física y, por tanto, qué entrada del `dtbo.img` eligió o elegiría el bootloader.
- La tabla DTBO define tres rangos Wi-Fi: overlay índice `0` para revisión `0`, índice `1` para revisiones `1–3`, e índice `2`, denominado `r04`, para revisiones `4–32`.
- No hay evidencia local que permita inferir el `hw_rev` físico desde el nombre de firmware `EZE4`, desde `REV00` en el AP ni desde los metadatos AVB/DTBO. Asumir `r04` sería una decisión no demostrada.
- El método correcto sigue siendo leer el árbol efectivo o las propiedades expuestas por el firmware en un arranque stock; si eso no es posible, el proyecto debe continuar tratando la revisión como incógnita bloqueante para cualquier prueba que dependa de BOM/pinctrl/display/sensores.

## Evidencia encontrada

### Identidad confirmada por configuración y firmware

| Dato | Valor | Evidencia |
|---|---|---|
| Modelo | `SM-X510` | `configs/target-sm-x510.env`; `scripts/collect-device.sh` valida `ro.product.model` |
| Variante | Wi-Fi | Configuración objetivo y tabla DTBO `GTS9FEWIFI_EUR_OPEN` |
| Plataforma/build Android | `BP4A.251205.006` | `configs/target-sm-x510.env`; documentación de la unidad |
| Versión AP/PDA | `X510XXUCEZE4` | `configs/target-sm-x510.env`; `artifacts/stock/firmware-metadata.txt` |
| CSC / multi-CSC | `EUX` / `OXM` (`X510OXMCEZE4`) | `configs/target-sm-x510.env`; cadena SAOMC documentada |
| Revisión binaria bootloader | `U12` | Campo `TARGET_BOOTLOADER_REVISION=12` y documentación del proyecto |
| Firmware conservado | ZIP completo con SHA-256 `45a45087...01d375` | `configs/target-sm-x510.env`; `docs/10-unidad-x510-eze4.md` |
| Entrada AP | `AP_..._MQB109790656_REV00_user_low_ship...tar.md5` | `artifacts/stock/firmware-metadata.txt` |

### Tabla de overlays EZE4

El manifiesto de `artifacts/stock/dt/overlays/manifest.json` registra tres entradas. Los campos `id` y `rev` estándar son cero; la discriminación relevante está en `custom[]`. Los DTS descompilados confirman su significado:

| Índice DTBO | Archivo | Campos custom | Rango declarado en DTS |
|---:|---|---|---|
| `0` | `overlay-00-id-00000000-rev-00000000.dtbo` | `[0,0,0,0]` | `dtbo-hw_rev = <0x00>`, `dtbo-hw_rev_end = <0x00>` |
| `1` | `overlay-01-id-00000000-rev-00000000.dtbo` | `[1,3,0,0]` | `dtbo-hw_rev = <0x01>`, `dtbo-hw_rev_end = <0x03>` |
| `2` | `overlay-02-id-00000000-rev-00000000.dtbo` | `[4,32,0,0]` | `dtbo-hw_rev = <0x04>`, `dtbo-hw_rev_end = <0x20>` |

El DTB base de `vendor_boot` declara:

```text
dtb-hw_rev = <0x00>
dtb-hw_rev_end = <0xff>
```

Ese rango amplio describe la aceptación del DT base, no la revisión física. El nodo raíz también contiene `model = "Samsung GTS9FEWIFI EUR OPEN board based on S5E8835"` después de aplicar el overlay correspondiente.

### Nodo `chosen`

El `chosen` extraído de EZE4 contiene:

```text
bootargs = "console=ram printk.devkmsg=on arm64.nopauth arm64.nomte nokaslr kasan=off clocksource=arch_sys_counter clk_ignore_unused firmware_class.path=/vendor/firmware rcupdate.rcu_expedited=1 swiotlb=noforce loop.max_part=7 cgroup.memory=nokmem";
linux,initrd-start = <0x84000000>;
linux,initrd-end   = <0x8cffffff>;
```

En el DTS estático no aparece ninguna propiedad de identidad como `hw-rev`, `board-id` físico o `stdout-path`. Existen valores `board-id = <0x10>` y `board-rev = <0x00>` dentro de otro nodo del árbol base, pero no hay evidencia local de que representen el `hw_rev` dinámico usado para seleccionar DTBO ni que el bootloader los actualice.

El `vendor_boot.img` incluye además 28 bytes de bootconfig con `buildtime_bootconfig=enable`. Su contenido observado no aporta identidad de placa.

### Datos que no identifican la placa física

| Campo o etiqueta | Qué identifica | Por qué no resuelve `hw_rev` |
|---|---|---|
| `X510XXUCEZE4` | Release AP/CSC Samsung | Es una etiqueta de software; no hay mapeo local a revisión de PCB |
| `EZE4` | Sufijo de release AP | No equivale demostrablemente a un número de revisión DTBO |
| `U12` | Revisión/binario bootloader registrado por el propietario | Distinta taxonomía respecto al rango `hw_rev` del DTBO |
| `REV00` del AP tar | Etiqueta del paquete AP | No existe evidencia que lo vincule al `hw_rev` de esta unidad |
| Rollback indexes AVB (`dtbo=1`, `prism=2`, `optics=3`) | Política anti-retroceso AVB | Son índices lógicos por partición, no revisiones físicas |
| Modelo/región en ajustes o `getprop` | Producto y CSC | Puede no exponer directamente la selección DTBO |

## Qué significa

1. El proyecto tiene una identidad de producto y firmware suficientemente sólida para seleccionar paquetes y comparar imágenes stock.
2. La identidad física fina está incompleta: conocer SM-X510/U12/EZE4 no demuestra cuál de los tres árboles efectivos usa la tablet.
3. La elección del DTBO pertenece al bootloader. Los rangos `custom[]` son una tabla candidata muy fuerte, pero no una observación del dispositivo.
4. El overlay `r04` cubre un intervalo grande (`4–32`) precisamente porque agrupa varias posibles revisiones. Eso facilita empaquetar firmware, pero no convierte `r04` en el valor real de esta unidad.

## Riesgos

- **Riesgo alto:** construir o validar un initramfs/kernel contra `r04` cuando la unidad sea `r00` o `r01–r03`. Las diferencias documentadas afectan pinctrl, calibración de magnetómetro y fragmentos de display/touch.
- **Riesgo medio:** confundir `U12`, `EZE4`, `REV00` o rollback index con `hw_rev`, introduciendo un supuesto falso en informes posteriores.
- **Riesgo medio:** usar propiedades no verificadas como `board-rev = <0x00>` sin entender quién las produce ni si el firmware las actualiza.
- **Riesgo bajo para boot temprano, alto para periféricos:** el DT base y bloques CPU/GIC/PSCI/timers pueden ser iguales entre overlays, mientras display, carga, sensores o GPIO quedan mal descritos.

## Hipótesis

| Hipótesis | Estado | Prueba necesaria |
|---|---|---|
| `hw_rev ∈ {0..32}` y la selección es por rango `[start,end]` de `custom[0],custom[1]` | Fuerte, consistente con DTS/manifest, pero no demostrada contra bootloader real | Comparar `/proc/device-tree` o `/sys/firmware/fdt` con cada overlay |
| Esta unidad concreta aplica el índice `2` / `r04` | No confirmada | Leer el árbol efectivo en stock |
| `TARGET_BOOTLOADER_REVISION=12` implica `hw_rev >= 4` | No confirmada | Correlacionar `hw_rev` observado con bootloader en unidades reales |
| `getprop` expone alguna propiedad derivada de `hw_rev` | Posible, dependiente de Samsung/Android build | Ejecutar inventario read-only en stock y buscar todas las propiedades |
| El bootloader añade parámetros `androidboot.*` con revisión | Posible | Capturar `/proc/cmdline` y `dmesg` en stock |

## Experimentos recomendados (sólo lectura)

### Experimento H1 — Inventario ADB en Android stock

Precondición: Android arranca normalmente y ADB autorizado.

1. Ejecutar el script existente `./scripts/collect-device.sh`; no modificarlo.
2. Conservar además, en un directorio nuevo de reporte:
   - `adb shell getprop`
   - `adb shell cat /proc/cmdline`
   - `adb exec-out cat /sys/firmware/fdt`
   - `adb shell cat /proc/device-tree/model`
   - listados de `/proc/device-tree` y `/sys/firmware/devicetree/base`
3. Descompilar el FDT recibido con `dtc -I dtb -O dts`.

Criterio de éxito: identificar exactamente qué propiedades del árbol final coinciden con overlay `0`, `1` o `2`.

Interpretación:

- Si aparecen `dtbo-hw_rev`/`dtbo-hw_rev_end` finales, registrar el rango aplicado.
- Si el bootloader añadió propiedades o cmdline con revisión, citarlas literalmente.
- Si no puede leerse el FDT por permisos, pasar a H2/H3 sin asumir resultado.

### Experimento H2 — Correlación por propiedades visibles sin root

Objetivo: encontrar señales indirectas reproducibles antes de depender del FDT.

1. Buscar en el `getprop` completo claves que contengan `rev`, `revision`, `hw`, `boot.hw`, `board`, `platform` y `product`.
2. Guardar `dmesg` si el build lo permite y buscar líneas de drivers Samsung que impriman `hw_rev`, BOM, panel, táctil o batería.
3. Registrar modelo exacto de panel/controlador táctil desde sysfs solo si es accesible sin root.

Interpretación: estas señales pueden discriminar familia de overlay, pero deben marcarse como evidencia indirecta hasta correlacionarse con el FDT.

### Experimento H3 — Observación en Download Mode sin escribir

Objetivo: determinar si el entorno de bootloader expone identidad legible.

1. Entrar en Download Mode siguiendo el procedimiento normal del dispositivo.
2. Enumerar USB desde el host y capturar descriptores/VID/PID/cadena serie.
3. Documentar pantalla y cualquier identificador visible.
4. Salir sin flashear.

Interpretación: si no aparece `hw_rev`, este experimento cierra un camino y documenta ese callejón sin salida.

## Decisión provisional

- No asumir `r04`.
- Para análisis offline, comparar los tres overlays y clasificar conclusiones según sean comunes a todos o exclusivas de uno.
- Para cualquier experimento físico sensible a revisión, exigir H1 como puerta previa.
- Si H1 falla por permisos, usar H2 como evidencia parcial y tratar la revisión como desconocida en el plan v2.

## Documentación propuesta

- Actualizar `docs/first-boot-experiment-plan-v2.md` con “hw_rev desconocido” como riesgo explícito y H1 como preflight obligatorio cuando haya acceso ADB seguro.
- Añadir a la plantilla de intento físico campos separados: `firmware=EZE4`, `bootloader_revision=U12`, `hw_rev=<unknown|number>`, `dtbo_index=<unknown|0|1|2>`.
- En futuras auditorías DT, etiquetar cada hallazgo como común a los tres overlays o específico de `r00`, `r01–r03` o `r04–r32`.
