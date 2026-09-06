# Reporte de Fase 2B — BTF/DWARF Struct Ground Truth y Reclasificación

- **Dispositivo**: Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510` / `gts9fewifi`)
- **SoC**: Samsung Exynos 1380 (`s5e8835`)
- **Firmware Base Objetivo**: `X510XXUCEZE4` (Kernel Linux 5.15.189)
- **Firmware de Referencia**: `X510XXSEEZG3` (Kernel Linux 5.15.189)
- **Estado de Ejecución**: **FASE 2B COMPLETADA**
- **Fecha**: 2026-09-06

---

## 1. Corrección de Errata de Fase 2A

Se identificó y corrigió formalmente la atribución del operando `#2208` en el desensamblado de `remove_waiter()` en `Image.stock`:
- **Discrepancia detectada**: $2208_{10} = \mathbf{0x8a0}_{16}$, no `0x8a8`.
- **Ground Truth**:
  - `0x898` (2200): `task_struct.pi_waiters.rb_root` (`struct rb_node *`)
  - `0x8a0` (2208): `task_struct.pi_waiters.rb_leftmost` (`struct rb_node *`)
  - `0x8a8` (2216): `task_struct.pi_top_task` (`struct task_struct *`)
  - `0x8b0` (2224): `task_struct.pi_blocked_on` (`struct rt_mutex_waiter *`)
- **Veredicto**: La macro `FAKE_TASK_PI_TOP_TASK_OFF 0x8a8` de ZG3 es **100% correcta** para `pi_top_task`. La instrucción stock `ldr x8, [x21, #2208]` accedía a `owner->pi_waiters.rb_leftmost`.
- Documentación completa en [`docs/rmg-eze4/PHASE2A_ERRATA.md`](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/PHASE2A_ERRATA.md).

---

## 2. Extracción de Ground Truth (BTF y DWARF en `vmlinux` EZE4)

Se extrajeron los tamaños y desplazamientos exactos de las 12 estructuras fundamentales del kernel mediante `bpftool btf dump` y `pahole -F btf` sobre `/home/markpi.guest/osrc-eze4-work/runs/eze4-fixed2/build-source/out-eze4/vmlinux`:

1. `struct task_struct`: tamaño 4608 bytes (`0x1200`), 216 miembros.
   - `usage` = `0x38`
   - `prio` = `0x7c`
   - `normal_prio` = `0x84`
   - `sched_task_group` = `0x400`
   - `real_cred` = `0x790`
   - `cred` = `0x798`
   - `pi_lock` = `0x884`
   - `pi_waiters` = `0x898`
   - `pi_top_task` = `0x8a8`
   - `pi_blocked_on` = `0x8b0`
2. `struct rt_mutex_waiter`: tamaño 88 bytes (`0x58`), 8 miembros.
   - `tree_entry` = `0x00`
   - `pi_tree_entry` = `0x18`
   - `task` = `0x30`
   - `lock` = `0x38`
   - `wake_state` = `0x40`
   - `prio` = `0x44`
   - `deadline` = `0x48`
   - `ww_ctx` = `0x50`
3. `struct rt_mutex_base`: tamaño 32 bytes (`0x20`), `waiters` @ `0x08`, `owner` @ `0x18`.
4. `struct rt_mutex`: tamaño 32 bytes (`0x20`).
5. `struct rb_node`: tamaño 24 bytes (`0x18`).
6. `struct rb_root_cached`: tamaño 16 bytes (`0x10`).
7. `struct file_operations`: tamaño 288 bytes (`0x120`), 36 miembros.
8. `struct file`: tamaño 264 bytes (`0x108`), 23 miembros.
9. `struct page`: tamaño 64 bytes (`0x40`), `compound_head` @ `0x08`, `slab_cache` @ `0x18`, `page_type` @ `0x30`.
10. `struct mm_struct`: tamaño 992 bytes (`0x3e0`), correspondiente al slab bucket `kmalloc-1k` (`0x400`).
11. `struct work_struct`: tamaño 48 bytes (`0x30`), `data` @ `0x00`, `entry` @ `0x08`, `func` @ `0x18`.
12. `struct cred`: tamaño 176 bytes (`0xb0`), 26 miembros.
13. Subestructuras adicionales (`workqueue_struct`, `pool_workqueue`, `worker_pool`, `configfs_buffer`).

Todos los 350 campos auditados han sido volcados en [`docs/rmg-eze4/eze4_struct_layout.csv`](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/eze4_struct_layout.csv).

---

## 3. Reclasificación Integral del Target ZG3 (v2)

Se separaron rigurosamente los miembros reales del kernel de los layouts sintéticos del payload en [`docs/rmg-eze4/zg3_target_inventory_v2.csv`](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/zg3_target_inventory_v2.csv):

| Nueva Categoría | Cantidad | Descripción y Ejemplos |
| :--- | :---: | :--- |
| **KERNEL_STRUCT_MEMBER** | **51** | Miembros reales de estructuras (`task_struct.cred`, `rt_mutex_waiter.lock`, `fops.read`). |
| **RUNTIME_TUNING** | **27** | Intentos de carrera, retardos, timeouts y umbrales de oráculo. |
| **KERNEL_SYMBOL** | **25** | Símbolos virtuales absolutos derivados de `KIMAGE_TEXT_BASE + offset`. |
| **EXPLOIT_ALGORITHM_CONSTANT** | **16** | Constantes de control de ruta y algoritmo (`SLIDE_ROUTE_FPSIMD`, `PRODUCTION_STACK_PI_RIGHT_ONLY`, `MM_STRUCT_SZ`, `P0_FINGERPRINT_MIN_*`). |
| **PAYLOAD_SYNTHETIC_LAYOUT** | **15** | Offsets internos de la página artificial (`W0_OFF`, `LOCK_OFF`, `SCRATCH_OFF`, `FOPS_OFF`, `BANK_*`). |
| **KERNEL_TEXT_OFFSET** | **15** | Desplazamientos relativos al texto para funciones ejecutables (`commit_creds`, `ashmem_mmap`). |
| **KERNEL_DATA_SYMBOL** | **14** | Desplazamientos relativos al texto para variables y tablas globales (`init_task`, `kmalloc_caches`). |
| **KERNEL_MEMORY_LAYOUT** | **8** | Regiones MMU (`KIMAGE_TEXT_BASE`, direct map, vmemmap, KASLR step `0x4000`). |
| **UNKNOWN** | **2** | Guardas de inclusión de preprocesador (`OFFSET_H`, `P0_FINGERPRINT_H`). |
| **BUILD_METADATA** | **2** | Etiqueta de variante (`BUILD_VARIANT_LABEL`) y ruta de cabecera. |
| **FIRMWARE_FINGERPRINT** | **2** | `ro.build.fingerprint` de Android y tabla de 32 huellas KASLR. |
| **SOC_CONSTANT** | **2** | Dirección física de carga DRAM Exynos 1380 (`0x80000000`). |
| **KERNEL_STRUCT_SIZE** | **1** | `STRUCT_PAGE_SIZE` (`0x40`). |
| **TOTAL** | **180** | **100% reclasificado con fuente de derivación.** |

---

## 4. Comparación Estructural ZG3 vs EZE4 y Cruce con `Image.stock`

- **Resultado de Comparación**: **53/53 parámetros estructurales relevantes para el target auditados son idénticos entre ZG3 target y EZE4.**
- **Cruce con `Image.stock`**: Todos los accesos observables directamente en el desensamblado de `remove_waiter()` en `Image.stock` coinciden al 100% con BTF y DWARF:
  - `task_struct.pi_lock` (`0x884`): **THREE-WAY MATCH**
  - `task_struct.pi_blocked_on` (`0x8b0`): **THREE-WAY MATCH**
  - `task_struct.pi_waiters.rb_root` (`0x898`): **THREE-WAY MATCH**
  - `task_struct.pi_waiters.rb_leftmost` (`0x8a0`): **THREE-WAY MATCH**
  - `rt_mutex_base.waiters` (`0x08`): **THREE-WAY MATCH**
  - `rt_mutex_base.owner` (`0x18`): **THREE-WAY MATCH**
  - `rt_mutex_waiter.lock` (`0x38`): **THREE-WAY MATCH**
  - `rt_mutex_waiter.prio` (`0x44`): **THREE-WAY MATCH**
  - `rt_mutex_waiter.deadline` (`0x48`): **THREE-WAY MATCH**
- Documentación completa en [`docs/rmg-eze4/zg3_eze4_struct_diff.md`](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/zg3_eze4_struct_diff.md).

---

## 5. Cierre y Métricas de Fase 2B

- **Número de macros reclasificadas**: **180 / 180 (100%)**
- **Número de parámetros estructurales auditados idénticos ZG3 / EZE4**: **53 / 53 (100.00%)**
- **Número de offsets estructurales que cambiaron**: **0**
- **Número de UNKNOWN restantes**: **2** (exclusivamente guardas de inclusión de preprocesador: `OFFSET_H`, `P0_FINGERPRINT_H`)
- **Contradicciones BTF vs DWARF**: **0**
- **Contradicciones BTF/DWARF vs Image.stock**: **0**
- **Veredicto Estructural**: **53/53 parámetros estructurales relevantes para el target auditados son idénticos entre ZG3 target y EZE4.**
- **Factores Pendientes para Fase 2C**: Mapeo y verificación de direcciones y offsets de símbolos en `System.map`, `vmlinux` y `Image.stock`.
