# Auditoría exhaustiva de infraestructura de crash logging — Samsung Exynos S5E8835 U11 / SM-X510

Fecha: 2026-08-24
Artefacto auditado: `artifacts/u11/x510xxsbdzb4-u11-clang21-20260823/`
Fase: análisis offline, **no flasheo**

## 1. Resumen ejecutivo

El kernel U11 ya incorpora **dos pilares completos** de captura de fallos:

1. **`sec_debug` Samsung** (módulos + DT + región reservada), que registra
   panic/reset reason/watchdog y prepara el "upload cause" para el bootloader.
2. **`pstore`/`ramoops` upstream** compilado (`=y`) pero **sin nodo DT ni
   cmdline activos**, por lo que hoy no persiste nada por sí solo.

Además existe **Debug Snapshot (DSS)** Samsung con regiones dedicadas en DRAM
para log_kernel, wdtmsg, ITMON, etc., ya declaradas en DT base.

Falta para primer boot sin UART:
- Garantizar que los módulos `sec_debug_base_early.ko`, `debug-snapshot.ko`
  y `debug-snapshot-debug-kinfo.ko` se cargan **antes** de cualquier riesgo,
  idealmente desde initramfs minimal o como built-in futuro.
- Decidir si usamos `ramoops` upstream (nuevo nodo DT) o confiamos sólo en
  `sec_debug`/DSS Samsung. Recomendación inicial: usar DSS/sec_debug primero;
  añadir ramoops sólo como segundo mecanismo independiente.

## 2. Inventario detallado

### CONFIG_PSTORE / CONFIG_PSTORE_RAM

| Opción | Estado | Comentario |
|---|---|---|
| `CONFIG_PSTORE=y` | activo | Backend base disponible. |
| `CONFIG_PSTORE_RAM=y` | activo | Driver ramoops listo para usar. |
| `CONFIG_PSTORE_CONSOLE=y` | activo | Persistiría consola si hubiera backend. |
| `CONFIG_PSTORE_PMSG=y` | activo | Mensajes userspace. |
| `CONFIG_PSTORE_DEFLATE_COMPRESS=y` | activo | Compresión por defecto. |
| `CONFIG_PSTORE_BLK=n` | inactivo | No hay backend por bloque; irrelevante ahora. |

**Estado real:** pstore está compilado pero **no tiene ningún nodo DT ni
parámetros cmdline asociados**. Sin `ramoops.mem_address/mem_size`, el driver no
hace nada. Es capacidad muerta hasta que la activemos deliberadamente.

### ramoops en Device Tree

- En `/tmp/u11-base.dts` (descompilado del DTB U11) **no aparece ningún nodo**
  compatible con `"ramoops"` ni `"persistentram"` ni referencia a
  `ramoops.mem_address`.
- Tampoco existe en los tres DTBO Wi-Fi r00/r01/r04.

Conclusión: ramoops upstream está **compilado pero no cableado**.

### reserved-memory existente en DTB U11

Regiones relevantes ya presentes en `s5e8835.dtb`:

| Nodo | Dirección física | Tamaño | Propósito |
|---|---|---|---|
| `header` | 0xFD000000 | 0x10000 | Cabecera Debug Snapshot |
| `log_kernel` | 0xFD010000 | 0x200000 | Log del kernel DSS |
| `log_s2d` | 0xFD210000 | 0x600000 | Scan-to-dump |
| `wdtmsg` | 0x8ADB11000 | 0x1000 | Últimos mensajes watchdog |
| `log_itmon` | 0xFFFE0000 | 0x20000 | Historial ITMON |
| `log_itmon_history` | 0x8ADB10000 | 0x1000 | Ídem |
| `sec_debug_next` (en DTBO) | 0x91200000 | 0x200000 | Buffer principal sec_debug GEN3 |
| `seclog_mem` | 0xC3000000 | 0x80000 | Log seguro exynos-seclog |
| `debug_kinfo_reserved@fcfff000` | 0xFCFFF000 | 0x1000 | debug-kinfo |

Estas regiones están **ya reservadas** (`no-map` donde aplica) y son coherentes
con el firmware stock. No hay conflicto conocido con memoria normal mientras
usemos exactamente estas direcciones.

### sec_debug Samsung

Estado en `.config`:

```text
CONFIG_SEC_DEBUG=m
CONFIG_SEC_DEBUG_BASE=m
CONFIG_SEC_DEBUG_BASE_BUILT_IN=y
CONFIG_SEC_DEBUG_RESET_REASON=m
CONFIG_SEC_DEBUG_MEMTAB=y
CONFIG_SEC_DEBUG_AUTO_COMMENT=y
CONFIG_SEC_DEBUG_LOCKUP_INFO=y
CONFIG_SEC_DEBUG_WORKQUEUE_LOCKUP_PANIC=y
...
```

Código fuente relevante:

- `drivers/samsung/debug/sec_debug_base_early.c`: driver platform
  compatible `"samsung,sec_debug"`. Busca `memory-region` cuyo nombre sea
  `"sec_debug_next"`, mapea la memoria no-cacheable, limpia SDN y expone APIs
  a otros módulos (`secdbg_base_get_buf_base`, etc.).
- `sec_debug_base.c`: registra panic handler que escribe
  `UPLOAD_CAUSE_KERNEL_PANIC` (0xC8) u otras causas en el PMU vía
  `exynos_pmu_write(SEC_DEBUG_PANIC_INFORM, ...)`.
- `sec_debug_reset_reason.c`: lee registros PMIC/RST_STAT para clasificar el
  reset (WDTRESET, SWRESET, PORESET, etc.) y expone `/proc` correspondiente.

DTBO aplican nodos:

```dts
fragment@sec_debug {
    target-path = "/";
    __overlay__ {
        sec_debug {
            compatible = "samsung,sec_debug";
            status = "okay";
            memory-region = <&sec_debug_next>;
            bdev_path = "/dev/block/by-name/debug";
        };
    };
};
fragment@sec_debug_built { ... memory-region = <&sec_debug_next>; };
fragment@sec_debug_reset_reason { ... strings power_on_src/rst_stat ... };
```

y reservan la región:

```dts
fragment@1 {
    target = <0xffffffff>; /* /reserved-memory */
    __overlay__ {
        sec_debug_next {
            reg = <0x00 0x91200000 0x200000>;
            no-map;
            phandle = <0x55>;
        };
    };
};
```

Módulos construidos (presentes en `modules.order`):

```text
drivers/samsung/debug/sec_debug.ko
drivers/samsung/debug/sec_debug_base_early.ko
drivers/samsung/debug/sec_debug_reset_reason.ko
drivers/samsung/debug/sec_debug_extra_info.ko
... (17 módulos sec_debug)
```

**Estado real:** infraestructura completa y lista, pero depende de que esos
módulos se carguen en tiempo de arranque. Hoy **no aparecen en
`configs/initramfs-modules.conf`** ni en el USB, así que en un boot mínimo con
initramfs actual **no se cargarían** y sec_debug estaría inactivo.

### last_kmsg / watchdog reset reason

- `last_kmsg = <0x01>` ya está declarado en el nodo `dss` (Debug Snapshot) del
  DTB base.
- `wdtmsg` región reservada en 0x8ADB11000 (4 KiB).
- `hardlockup-watchdog` compatible `"samsung,hardlockup-watchdog"` presente.
- `CONFIG_SEC_DEBUG_SOFTDOG=m`, `CONFIG_SEC_DEBUG_WATCHDOGD_FOOTPRINT=m`.
- `sec_debug_reset_reason.ko` construido y listo; necesita ser cargado.

Todo el soporte de "por qué se reinició" existe; sólo falta carga de módulo.

## 3. Qué falta realmente añadir

Para que el primer boot sin UART capture evidencia automáticamente:

1. **Cargar módulos sec_debug desde initramfs minimal**, antes de cualquier
   experimento:
   - `sec_debug_base_early`
   - `sec_debug_reset_reason`
   - `sec_debug`
   - opcionalmente `debug-snapshot-debug-kinfo`
   Esto requiere añadirlos al cierre calculado por modprobe en
   `configs/initramfs-modules.conf` (futuro, no ahora).
2. **Verificar que el cmdline no desactiva DSS/sec_debug** (no hay indicios de
   que lo haga; confirmar en `proc/cmdline` cuando haya acceso físico).
3. **Decidir sobre ramoops upstream**: recomendación inicial **no añadirlo
   todavía**. Motivos:
   - Ya tenemos dos sistemas Samsung nativos (sec_debug + DSS) con memoria
     reservada por el firmware stock.
   - Añadir ramoops implicaría reservar otra región DRAM nueva, con riesgo de
     colisión con firmware/TZ/otros periféricos que no conocemos al 100%.
   - Para M2/M3, sec_debug/DSS cubre exactamente el caso de fallo que queremos
     observar (panic/hang/reset).
   Si más adelante queremos ramoops igualmente, el nodo sería:

   ```dts
   / {
       reserved-memory {
           #address-cells = <2>;
           #size-cells = <1>;
           ranges;

           ramoops_region: ramoops_region@91400000 {
               compatible = "ramoops";
               reg = <0x00 0x91400000 0x00100000>;
               no-map;
           };
       };

       ramoops {
           compatible = "ramoops";
           memory-region = <&ramoops_region>;
           record-size = <0x20000>;
           console-size = <0x80000>;
           pmsg-size = <0x20000>;
           ecc-size = <16>;
       };
   };
   ```

   con dirección elegida fuera de todas las regiones listadas arriba. La
   dirección 0x91400000 es adyacente a `sec_debug_next` (que acaba en
   0x91400000). Debe validarse contra mapa físico completo antes de usarse.

## 4. Riesgos de reservar memoria incorrectamente

Reservar DRAM mal puede causar:

1. **Colisión con TrustZone / firmware EL3.** Las regiones altas
   (0xFC000000–0xFFFFFFFF) están llenas de zonas seguras. Un error aquí puede
   provocar abort síncrono en EL3, reinicio instantáneo sin log.
2. **Corrupción de buffers de firmware de coprocesadores** (CP/GNSS/NPU/Audio)
   que ya tienen regiones reservadas propias. Si solapamos, el firmware puede
   escribir en nuestro buffer o viceversa, generando panics falsos.
3. **Conflicto con CMA / memblock del propio kernel.** Si marcamos `no-map`
   sobre una zona que Linux ya asignó dinámicamente, obtenemos corrupción
   silenciosa o BUG_ON.
4. **Inconsistencia entre bootloader y kernel.** Si el bootloader espera que
   cierta dirección esté libre (por ejemplo para pasar datos de reset reason),
   y nosotros la reservamos con otro propósito, perdemos la evidencia original.

Regla práctica para esta fase:

- **No crear ninguna reserva nueva.** Usar únicamente las direcciones ya
  presentes en el DTB/DTBO stock.
- Si en el futuro añadimos ramoops, elegir dirección tras obtener el mapa
  físico real (`/proc/iomem`, `memblock_dump_all`) en un boot vivo, nunca
  adivinada offline.

## 5. Conclusión operativa

La infraestructura de crash logging Samsung en U11 es **mucho más completa de
lo esperado**: sec_debug, Debug Snapshot, reset reason y watchdog footprint
están compilados y con memoria ya reservada por el firmware.

El único hueco real para el primer boot sin UART es **asegurar la carga de esos
módulos en el initramfs minimal**. Ese cambio pertenece a la fase siguiente,
junto con la verificación física de que `/dev/block/by-name/debug` es accesible
y que el PMU acepta la escritura de upload cause.
