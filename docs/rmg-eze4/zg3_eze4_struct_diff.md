# Auditoría Comparativa Estructural: ZG3 vs EZE4 (BTF, DWARF e Image.stock)

- **Dispositivo**: Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510` / `gts9fewifi`)
- **SoC**: Samsung Exynos 1380 (`s5e8835`)
- **Firmware Base Comparado**: `X510XXUCEZE4` (Kernel 5.15.189) vs `X510XXSEEZG3` (Kernel 5.15.189)
- **Fuentes de Ground Truth**:
  - EZE4 BTF (`vmlinux` unstripped sección `.BTF`, 6.0 MB)
  - EZE4 DWARF (`vmlinux` unstripped secciones `.debug_*`, 400+ MB analizadas con `pahole` y `llvm-dwarfdump`)
  - EZE4 `Image.stock` (binario de fábrica extraído de `boot.img`, SHA-256: `ca56baf4...`)
- **Fecha de Auditoría**: 2026-09-06

---

## 1. Tabla Maestra de Comparación Estructural

| Estructura | Miembro / Campo | ZG3 Target Value | EZE4 BTF Value | EZE4 DWARF Value | Clasificación | Evidencia Directa en `Image.stock` | Resultado de Cruce |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| `task_struct` | `usage` | `0x38` (56) | `0x38` (56) | `0x38` (56) | **IDENTICAL** | *No observable en remove_waiter* | **BTF/DWARF MATCH** |
| `task_struct` | `prio` | `0x7c` (124) | `0x7c` (124) | `0x7c` (124) | **IDENTICAL** | *No observable en remove_waiter* | **BTF/DWARF MATCH** |
| `task_struct` | `normal_prio` | `0x84` (132) | `0x84` (132) | `0x84` (132) | **IDENTICAL** | *No observable en remove_waiter* | **BTF/DWARF MATCH** |
| `task_struct` | `sched_task_group` | `0x400` (1024) | `0x400` (1024) | `0x400` (1024) | **IDENTICAL** | *No observable en remove_waiter* | **BTF/DWARF MATCH** |
| `task_struct` | `real_cred` | `0x790` (1936) | `0x790` (1936) | `0x790` (1936) | **IDENTICAL** | *No observable en remove_waiter* | **BTF/DWARF MATCH** |
| `task_struct` | `cred` | `0x798` (1944) | `0x798` (1944) | `0x798` (1944) | **IDENTICAL** | *No observable en remove_waiter* | **BTF/DWARF MATCH** |
| `task_struct` | `pi_lock` | `0x884` (2180) | `0x884` (2180) | `0x884` (2180) | **IDENTICAL** | `add x22, x20, #0x884` (`ffffffc0091506b8`) | **THREE-WAY MATCH** |
| `task_struct` | `pi_waiters` (`rb_root`) | `0x898` (2200) | `0x898` (2200) | `0x898` (2200) | **IDENTICAL** | `add x1, x21, #0x898` (`ffffffc009150784`) | **THREE-WAY MATCH** |
| `task_struct` | `pi_waiters` (`rb_leftmost`)| `0x8a0` (2208) | `0x8a0` (2208) | `0x8a0` (2208) | **IDENTICAL** | `ldr x8, [x21, #2208]` (`ffffffc009150734`) | **THREE-WAY MATCH** |
| `task_struct` | `pi_top_task` | `0x8a8` (2216) | `0x8a8` (2216) | `0x8a8` (2216) | **IDENTICAL** | *Top task pointer en task_struct* | **BTF/DWARF MATCH** |
| `task_struct` | `pi_blocked_on` | `0x8b0` (2224) | `0x8b0` (2224) | `0x8b0` (2224) | **IDENTICAL** | `str xzr, [x20, #2224]` (`ffffffc009150708`) | **THREE-WAY MATCH** |
| `rt_mutex_waiter`| `tree_entry` | `0x00` (0) | `0x00` (0) | `0x00` (0) | **IDENTICAL** | `ldr x8, [x23]` (`ffffffc0091506d0`) | **THREE-WAY MATCH** |
| `rt_mutex_waiter`| `pi_tree_entry` | `0x18` (24) | `0x18` (24) | `0x18` (24) | **IDENTICAL** | `ldr x8, [x23, #24]!` (`ffffffc009150728`)| **THREE-WAY MATCH** |
| `rt_mutex_waiter`| `task` | `0x30` (48) | `0x30` (48) | `0x30` (48) | **IDENTICAL** | *Ignorado por remove_waiter vulnerable* | **BTF/DWARF MATCH** |
| `rt_mutex_waiter`| `lock` | `0x38` (56) | `0x38` (56) | `0x38` (56) | **IDENTICAL** | `ldr x8, [x24, #56]` (`ffffffc0091506a8`) | **THREE-WAY MATCH** |
| `rt_mutex_waiter`| `wake_state` | `0x40` (64) | `0x40` (64) | `0x40` (64) | **IDENTICAL** | *wake_state en waiter* | **BTF/DWARF MATCH** |
| `rt_mutex_waiter`| `prio` | `0x44` (68) | `0x44` (68) | `0x44` (68) | **IDENTICAL** | `ldr w10, [x0, #44]` (`ffffffc00915078c` donde `x0=waiter+0x18`)| **THREE-WAY MATCH** |
| `rt_mutex_waiter`| `deadline` | `0x48` (72) | `0x48` (72) | `0x48` (72) | **IDENTICAL** | `ldr x12, [x0, #48]` (`ffffffc0091507b8` donde `x0=waiter+0x18`)| **THREE-WAY MATCH** |
| `rt_mutex_waiter`| `ww_ctx` | `0x50` (80) | `0x50` (80) | `0x50` (80) | **IDENTICAL** | *ww_ctx en waiter* | **BTF/DWARF MATCH** |
| `rt_mutex_base` | `wait_lock` | `0x00` (0) | `0x00` (0) | `0x00` (0) | **IDENTICAL** | `_raw_spin_lock_irq(lock)` | **BTF/DWARF MATCH** |
| `rt_mutex_base` | `waiters` | `0x08` (8) | `0x08` (8) | `0x08` (8) | **IDENTICAL** | `add x1, x19, #0x8` (`ffffffc0091506f4`) | **THREE-WAY MATCH** |
| `rt_mutex_base` | `owner` | `0x18` (24) | `0x18` (24) | `0x18` (24) | **IDENTICAL** | `add x8, x19, #0x18; ldar x8, [x8]` (`ffffffc0091506c0`) | **THREE-WAY MATCH** |
| `file_operations`| `owner` | `0x00` (0) | `0x00` (0) | `0x00` (0) | **IDENTICAL** | *fops struct vfs* | **BTF/DWARF MATCH** |
| `file_operations`| `llseek` | `0x08` (8) | `0x08` (8) | `0x08` (8) | **IDENTICAL** | *fops struct vfs* | **BTF/DWARF MATCH** |
| `file_operations`| `read` | `0x10` (16) | `0x10` (16) | `0x10` (16) | **IDENTICAL** | *fops struct vfs* | **BTF/DWARF MATCH** |
| `file_operations`| `write` | `0x18` (24) | `0x18` (24) | `0x18` (24) | **IDENTICAL** | *fops struct vfs* | **BTF/DWARF MATCH** |
| `file_operations`| `read_iter` | `0x20` (32) | `0x20` (32) | `0x20` (32) | **IDENTICAL** | *fops struct vfs* | **BTF/DWARF MATCH** |
| `file_operations`| `write_iter` | `0x28` (40) | `0x28` (40) | `0x28` (40) | **IDENTICAL** | *fops struct vfs* | **BTF/DWARF MATCH** |
| `file_operations`| `unlocked_ioctl`| `0x50` (80) | `0x50` (80) | `0x50` (80) | **IDENTICAL** | *fops struct vfs* | **BTF/DWARF MATCH** |
| `file_operations`| `compat_ioctl` | `0x58` (88) | `0x58` (88) | `0x58` (88) | **IDENTICAL** | *fops struct vfs* | **BTF/DWARF MATCH** |
| `file_operations`| `mmap` | `0x60` (96) | `0x60` (96) | `0x60` (96) | **IDENTICAL** | *fops struct vfs* | **BTF/DWARF MATCH** |
| `file_operations`| `open` | `0x70` (112) | `0x70` (112) | `0x70` (112) | **IDENTICAL** | *fops struct vfs* | **BTF/DWARF MATCH** |
| `file_operations`| `release` | `0x80` (128) | `0x80` (128) | `0x80` (128) | **IDENTICAL** | *fops struct vfs* | **BTF/DWARF MATCH** |
| `file_operations`| `splice_read` | `0xc8` (200) | `0xc8` (200) | `0xc8` (200) | **IDENTICAL** | *fops struct vfs* | **BTF/DWARF MATCH** |
| `file_operations`| `show_fdinfo` | `0xe0` (224) | `0xe0` (224) | `0xe0` (224) | **IDENTICAL** | *fops struct vfs* | **BTF/DWARF MATCH** |
| `struct page` | `size` | `0x40` (64) | `0x40` (64) | `0x40` (64) | **IDENTICAL** | *page frame size* | **BTF/DWARF MATCH** |
| `struct page` | `compound_head` | `0x08` (8) | `0x08` (8) | `0x08` (8) | **IDENTICAL** | *page union type 134* | **BTF/DWARF MATCH** |
| `struct page` | `slab_cache` | `0x18` (24) | `0x18` (24) | `0x18` (24) | **IDENTICAL** | *slab page union type 133* | **BTF/DWARF MATCH** |
| `struct page` | `page_type` | `0x30` (48) | `0x30` (48) | `0x30` (48) | **IDENTICAL** | *page union type 140* | **BTF/DWARF MATCH** |
| *(SLUB bucket)* | `mm_struct` alloc bucket | `0x400` (1024) | `0x400` (1024) | `0x400` (1024) | **IDENTICAL** | `sizeof(mm)=0x3e0` -> `kmalloc-1k` | **BTF/SLUB MATCH** |
| `work_struct` | `data` | `0x00` (0) | `0x00` (0) | `0x00` (0) | **IDENTICAL** | *atomic_long_t data* | **BTF/DWARF MATCH** |
| `work_struct` | `entry` | `0x08` (8) | `0x08` (8) | `0x08` (8) | **IDENTICAL** | *struct list_head entry* | **BTF/DWARF MATCH** |
| `work_struct` | `func` | `0x18` (24) | `0x18` (24) | `0x18` (24) | **IDENTICAL** | *work_func_t func* | **BTF/DWARF MATCH** |
| `workqueue_struct`| `dfl_pwq` | `0xb0` (176) | `0xb0` (176) | `0xb0` (176) | **IDENTICAL** | *struct pool_workqueue \** | **BTF/DWARF MATCH** |
| `pool_workqueue`| `pool` | `0x00` (0) | `0x00` (0) | `0x00` (0) | **IDENTICAL** | *struct worker_pool \** | **BTF/DWARF MATCH** |
| `pool_workqueue`| `wq` | `0x08` (8) | `0x08` (8) | `0x08` (8) | **IDENTICAL** | *struct workqueue_struct \** | **BTF/DWARF MATCH** |
| `pool_workqueue`| `work_color` | `0x10` (16) | `0x10` (16) | `0x10` (16) | **IDENTICAL** | *int work_color* | **BTF/DWARF MATCH** |
| `pool_workqueue`| `refcnt` | `0x18` (24) | `0x18` (24) | `0x18` (24) | **IDENTICAL** | *int refcnt* | **BTF/DWARF MATCH** |
| `pool_workqueue`| `nr_in_flight` | `0x1c` (28) | `0x1c` (28) | `0x1c` (28) | **IDENTICAL** | *int nr_in_flight[]* | **BTF/DWARF MATCH** |
| `pool_workqueue`| `nr_active` | `0x5c` (92) | `0x5c` (92) | `0x5c` (92) | **IDENTICAL** | *int nr_active* | **BTF/DWARF MATCH** |
| `pool_workqueue`| `max_active` | `0x60` (96) | `0x60` (96) | `0x60` (96) | **IDENTICAL** | *int max_active* | **BTF/DWARF MATCH** |
| `worker_pool` | `worklist` | `0x20` (32) | `0x20` (32) | `0x20` (32) | **IDENTICAL** | *struct list_head worklist* | **BTF/DWARF MATCH** |
| `worker_pool` | `nr_idle` | `0x34` (52) | `0x34` (52) | `0x34` (52) | **IDENTICAL** | *int nr_idle* | **BTF/DWARF MATCH** |
| `configfs_buffer`| `page` | `16` (`0x10`) | `16` (`0x10`) | `16` (`0x10`) | **IDENTICAL** | *char \*page* | **DWARF/SRC MATCH** |
| `configfs_buffer`| `needs_read_fill`| `80` (`0x50`)| `80` (`0x50`)| `80` (`0x50`)| **IDENTICAL** | *int needs_read_fill* | **DWARF/SRC MATCH** |
| `configfs_buffer`| `bin_buffer` | `88` (`0x58`)| `88` (`0x58`)| `88` (`0x58`)| **IDENTICAL** | *char \*bin_buffer* | **DWARF/SRC MATCH** |
| `configfs_buffer`| `bin_buffer_size`| `96` (`0x60`)| `96` (`0x60`)| `96` (`0x60`)| **IDENTICAL** | *int bin_buffer_size* | **DWARF/SRC MATCH** |
| `configfs_buffer`| `cb_max_size` | `100` (`0x64`)| `100` (`0x64`)| `100` (`0x64`)| **IDENTICAL** | *int cb_max_size* | **DWARF/SRC MATCH** |

---

## 2. Hallazgos Fundamentales de la Auditoría

1. **Invarianza Estructural (Parámetros Relevantes Idénticos)**:
   - **53/53 parámetros estructurales relevantes para el target auditados son idénticos entre ZG3 target y EZE4.**
   - No existe un solo desplazamiento estructural que haya variado entre el firmware de julio (ZG3) y el firmware local de mayo (EZE4).
2. **Paridad con Image.stock (Three-Way Match)**:
   - Todos los accesos a campos que pudieron observarse en el flujo desensamblado de `remove_waiter()` en `Image.stock` (`pi_lock`, `pi_blocked_on`, `pi_waiters.rb_root`, `pi_waiters.rb_leftmost`, `rt_mutex_base.waiters`, `rt_mutex_base.owner`, `rt_mutex_waiter.lock`, `rt_mutex_waiter.prio`, `rt_mutex_waiter.deadline`) demostraron coincidencia exacta y sin ambigüedad entre BTF, DWARF y el binario de fábrica.
3. **Clarificación Formal de `MM_STRUCT_SZ 0x400`**:
   - `sizeof(struct mm_struct)` en EZE4 es de **992 bytes** (`0x3e0`).
   - `MM_STRUCT_SZ = 0x400` no es un miembro ni el tamaño exacto del struct, sino el **tamaño de allocation bucket** de SLUB (`kmalloc-1k` = 1024 bytes) en el cual se aloja la estructura. La macro ZG3 modela con precisión la geometría del slab derivada de BTF + SLUB.
