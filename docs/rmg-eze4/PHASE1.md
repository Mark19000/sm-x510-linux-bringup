# Reporte de Fase 1 — Reconocimiento y Auditoría Estática (EZE4 vs ZG3)

- **Dispositivo**: Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510` / `gts9fewifi`)
- **SoC**: Samsung Exynos 1380 (`s5e8835`)
- **Firmware Base Objetivo**: `X510XXUCEZE4` (Android 16 / One UI 8.5 / U12 Bootloader)
- **Firmware de Referencia**: `X510XXSEEZG3` (Root-My-Galaxy target `gts9fewifi-X510XXSEEZG3`)
- **Kernel Base**: Linux `5.15.189-android13-3-33478785`
- **Estado de Ejecución**: **FASE 1 COMPLETADA**
- **Fecha**: 2026-09-06

---

## 1. Resumen de Artefactos EZE4

La inspección integral del repositorio `tab-s9-fe-linux` confirmó una base de artefactos sumamente madura, validada y con trazabilidad determinista:

### Artefactos Presentes y Validados
1. **Código Fuente Oficial Samsung OSRC**:
   - Paquete base `Kernel.tar.gz` (SHA-256: `2f3e186260...`, 254.8 MB) y envoltorio ZIP `SM-X510_EUR_16_Opensource.zip` (SHA-256: `72378f3b...`, 286.4 MB).
   - Árbol de código fuente completamente extraído en `audit/eze4-source-intake/extracted/kernel/` (86,456 entradas).
2. **Particiones Stock Extraídas de Firmware Oficial**:
   - `boot.img` (67.1 MB, SHA-256: `c96c0eb0...`) con cabecera Android Boot v4 y kernel uncompressed aarch64 Image de fábrica (39.3 MB, SHA-256: `ca56baf4...`).
   - `init_boot.img` (16.8 MB, SHA-256: `9efb4169...`).
   - `vendor_boot.img` (33.6 MB, SHA-256: `60e85ca0...`) con tablas de módulos y DTB base stock.
   - `dtbo.img` (8.4 MB, SHA-256: `0dd2392e...`) con overlays r00, r01 y r04.
   - `vbmeta.img` (10.1 KB, SHA-256: `bef09047...`) con estructura AVB 2.0.
   - Flujos comprimidos originales `*.img.lz4` preservados en `artifacts/stock/raw/`.
3. **Compilación Determinista EZE4 (Línea Base Validada)**:
   - Kernel binario reconstruido `artifacts/eze4/x510xxuceze4-baseline-20260905/Image` (38.9 MB, SHA-256: `a6f5c4f1...`).
   - `vmlinux` unstripped completo generado en Lima VM (`/home/markpi.guest/osrc-eze4-work/runs/eze4-fixed2/build-source/out-eze4/vmlinux`, 552 MB, SHA-256: `44fd5d2b...`).
   - Sección de depuración de tipos `.BTF` (tamaño 6,000,722 bytes) y tablas DWARF completas en `vmlinux`.
   - `System.map` completo con símbolos del kernel (5.7 MB, SHA-256: `ec6047c2...`).
   - `Module.symvers` con 15,123 símbolos exportados (705.1 KB, SHA-256: `f57afda2...`).
   - `.config` de producción generado por `s5e8835-gts9fewifixx_defconfig` (SHA-256: `f9bb6c47...`).
   - Binarios DTB (`s5e8835.dtb`) y DTBOs (`r00.dtbo`, `r01.dtbo`, `r04.dtbo`) byte-idénticos a los de fábrica.
   - 282 módulos de kernel (`modules-root.tar.gz`, 11.9 MB), demostrando 100.00% de paridad ABI (0 discrepancias de CRC en 15,123 símbolos) contra los 281 módulos DLKM stock.
4. **Cadenas de Herramientas y Scripts**:
   - VM Lima ARM64 (`Ubuntu 24.04`, Clang 21.1.8 / LLD 21.1.8) activa y funcional.
   - `avbtool` de Android 16 (`sources/toolchain/avb-android16/`) y `magiskboot` v30.7.
   - Herramientas de verificación automatizada: `scripts/verify-eze4-abi.py`, `tools/dts_semantic_diff.py`, `tools/bootimg_info.py`.

### Artefactos Faltantes / No Presentes Localmente
1. **Binario de Bootloader (`sboot.bin`)**: El paquete BL del firmware stock no fue extraído a disco para optimizar espacio (el archivo AP cubre todas las particiones del SO). Sin embargo, el estado físico del bootloader (revisión 12 / `SWREV B:12`, `WARRANTY VOID: 0x0000`, `KG STATE: Completed (00)`) está documentado con evidencia fotográfica en `docs/hardware/evidence/`.
2. **Archivos de Target EZE4**: No existen todavía `target.h` ni `p0_fingerprint.h` adaptados para EZE4.

---

## 2. Anatomía del Target ZG3 (`gts9fewifi-X510XXSEEZG3`)

El análisis exhaustivo de `target.h` y `p0_fingerprint.h` arrojó un total de **180 constantes y macros** inventariadas en [`docs/rmg-eze4/zg3_target_inventory.csv`](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/zg3_target_inventory.csv):

| Categoría | Cantidad | Descripción Principal |
| :--- | :---: | :--- |
| **STRUCT_LAYOUT** | **67** | Desplazamientos de miembros en `task_struct`, `rt_mutex_waiter`, `file_operations`, `work_struct`, `configfs_bin_buffer`, `struct page`. |
| **KERNEL_SYMBOL** | **52** | Desplazamientos relativos al texto (`*_OFF`) y direcciones absolutas (`KIMAGE_TEXT_BASE + offset`) para símbolos clave. |
| **RUNTIME_TUNING** | **42** | Intentos de carrera, retardos finos/gruesos, ranuras de oráculo P0, afinidad de hilos y umbrales. |
| **MEMORY_LAYOUT** | **8** | Mapa de memoria virtual (`KIMAGE_TEXT_BASE`, direct map, vmemmap) y paso KASLR (`0x4000`). |
| **FIRMWARE_BUILD** | **4** | Identificador de variante (`BUILD_VARIANT_LABEL`), fingerprint de Android 16 y tabla de 32 huellas P0. |
| **UNKNOWN** | **4** | Guardas de inclusión de preprocesador (`OFFSET_H`, `P0_FINGERPRINT_H`). |
| **SOC** | **2** | Dirección base física de carga de DRAM para Exynos 1380 (`0x80000000`). |
| **KERNEL_VERSION** | **1** | Banderas de buffer de tubería (`PIPE_BUF_FLAG_CAN_MERGE`). |
| **TOTAL** | **180** | **100% catalogado en CSV con valores, líneas, propósitos y dependencias.** |

---

## 3. Estado de la Corrección CVE-2026-43499 (`rtmutex`)

- **Veredicto Estricto**: **`PATCH ABSENT`** (Árbol local vulnerable a nivel de código fuente).
- **Evidencia Técnica**:
  - En `audit/eze4-source-intake/extracted/kernel/kernel/locking/rtmutex.c` (líneas 1468–1471), `remove_waiter()` ejecuta:
    ```c
    raw_spin_lock(&current->pi_lock);
    rt_mutex_dequeue(lock, waiter);
    current->pi_blocked_on = NULL;
    raw_spin_unlock(&current->pi_lock);
    ```
  - Asume erróneamente que `waiter->task == current`.
  - En llamadas proxy (`rt_mutex_start_proxy_lock()`), `waiter->task != current`, por lo que el cerrojo adquirido es el incorrecto y `waiter->task->pi_blocked_on` nunca es anulado, reteniendo un puntero colgante.
  - La corrección upstream (asociada al commit `3bfdc63936dd` y notas *"When invoked from rt_mutex_start_proxy_lock() waiter::task != current !"*) **no está presente** en el árbol EZE4 de Samsung.
  - Documentación completa en [`docs/rmg-eze4/rtmutex_patch_status.md`](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/rtmutex_patch_status.md).

---

## 4. Diferencias Preliminares ZG3 vs EZE4 (Matriz Semáforo)

| Dimensión / Vector | Clasificación | Hallazgos y Justificación Técnica |
| :--- | :---: | :--- |
| **Versión de Kernel** | **GREEN** | Idéntica: Linux `5.15.189-android13-3-33478785` en ambos firmwares. |
| **Configuración de Kernel** | **GREEN** | Idéntica: Misma base `s5e8835-gts9fewifixx_defconfig`. |
| **SoC / Hardware Memory Map** | **GREEN** | Idéntico: Exynos 1380 (`s5e8835`), `P0_PHYS_OFFSET = 0x80000000`, KASLR step `0x4000` (16 KB). |
| **Estado CVE-2026-43499** | **GREEN** | Idéntico: Ambos firmwares carecen del parche (`PATCH ABSENT`). |
| **Mecanismo de Ruta (FPSIMD)** | **GREEN** | Compatible: Basado en ABI pública de señales ARM64 (`sigcontext`). |
| **Tamaños de Estructuras (ABI)**| **YELLOW** | **Debe verificarse con BTF**: Aunque los módulos DLKM mantuvieron 100% de paridad CRC, structs internas no exportadas deben corroborarse contra `vmlinux`. |
| **Símbolos del Kernel (Offsets)** | **RED** | **Completamente dependiente del firmware**: Se demostró desplazamiento de texto. `init_task` se movió de `0x239fd80` a `0x233f0c0`, `prepare_kernel_cred` de `0x113a88` a `0xfb360`, `commit_creds` de `0x113330` a `0xfac1c`. |
| **Tabla de Huellas P0** | **RED** | **Completamente dependiente del firmware**: Muestrea bytes exactos de la imagen `Image`; los hashes de `Image` difieren (`ca56baf4...` en ZG3 vs `a6f5c4f1...` en EZE4). |
| **Build Fingerprint** | **RED** | Cambia de `X510XXSEEZG3` a `X510XXUCEZE4`. |

---

## 5. Hallazgos sobre Rutas FPSIMD y Tuning

- **`SLIDE_ROUTE_FPSIMD`**:
  - Utiliza el marco de señal `ucontext_t` y la estructura `struct fpsimd_context` (`FPSIMD_MAGIC` = `0x46508001`) guardada en el espacio de usuario al entregar `SIGUSR2`.
  - Proporciona un búfer continuo de 512 bytes en `vregs[32]` para alojar el `fake_waiter`.
  - Resuelve las restricciones de SELinux en Android que impiden el uso de sockets multicast (`SLIDE_ROUTE_MCAST`).
  - Es independiente del build y completamente compatible con EZE4.
- **`PRODUCTION_STACK_PI_RIGHT_ONLY`**:
  - Fijada en `0` para `gts9fewifi` (a diferencia de teléfonos Galaxy como el S24 que usan `1`).
  - Controla la orientación de inserción en el árbol rojo-negro del cerrojo (`tree_left = slide_oracle_target` vs `tree_right`).
  - Depende del orden relativo de direcciones virtuales entre el nodo padre y los gadgets de fops en el espacio de memoria.
  - Documentación completa en [`docs/rmg-eze4/fpsimd_static_analysis.md`](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/fpsimd_static_analysis.md).

---

## 6. Incógnitas y Factores a Resolver (Unknowns)

1. **Resolución de Símbolos Estáticos Ocultos**: Símbolos como `ashmem_misc_fops`, `configfs_read_iter`, `configfs_bin_write_iter` y `copy_splice_read` no aparecen listados en `System.map` de EZE4 bajo esos nombres directos (posiblemente estáticos o inlined en compilación ThinLTO). Deben localizarse mediante desensamblado o inspección DWARF en `vmlinux`.
2. **Validación de Offsets Internos de `task_struct`**: Corroborar si `TASK_STRUCT_CRED_OFF` (`0x798`), `TASK_STRUCT_REAL_CRED_OFF` (`0x790`) y los desplazamientos de `pi_lock` (`0x884`) y `pi_blocked_on` (`0x8b0`) son idénticos entre ZG3 y EZE4 utilizando el volcado `.BTF` de `vmlinux`.
3. **Página de Huellas P0 EZE4**: La tabla `p0_fingerprint.h` de ZG3 no puede ser utilizada para resolver KASLR en EZE4; debe sintetizarse una tabla específica para la `Image` stock de EZE4.

---

## 7. Próxima Fase Recomendada

**Fase 2: Extracción Estática de Tipos (BTF/DWARF) y Mapeo de Símbolos EZE4**
1. **Auditoría de Tipos mediante BTF**: Ejecutar `bpftool btf dump` o inspección pahole sobre `/home/markpi.guest/.../out-eze4/vmlinux` para extraer los desplazamientos exactos de:
   - `struct task_struct` (`cred`, `real_cred`, `pi_lock`, `pi_waiters`, `pi_blocked_on`).
   - `struct rt_mutex_waiter` (`pi_tree_entry`, `task`, `lock`, `prio`).
   - `struct mm_struct` (tamaño de slab y offsets).
   - `struct file_operations` y `struct work_struct`.
2. **Localización de Gadgets y Símbolos No Exportados**: Identificar mediante análisis de desensamblado en `vmlinux` las direcciones exactas de `ashmem_misc_fops`, `configfs_bin_write_iter` y funciones de splicing.
3. **Generación de la Tabla de Huellas P0 EZE4**: Crear un script estático que procese la `Image` stock de EZE4 y genere la cabecera `p0_fingerprint.h` correspondiente para el paso de 16 KB.
4. **Comprobación de Orientación rbtree**: Evaluar las direcciones relativas de EZE4 para verificar si `PRODUCTION_STACK_PI_RIGHT_ONLY` debe ser `0` o `1`.
