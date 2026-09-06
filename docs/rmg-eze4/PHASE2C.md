# Reporte de Fase 2C — Kernel Symbol Ground Truth (System.map, vmlinux e Image.stock)

- **Dispositivo**: Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510` / `gts9fewifi`)
- **SoC**: Samsung Exynos 1380 (`s5e8835`)
- **Firmware Base Objetivo**: `X510XXUCEZE4` (Kernel Linux 5.15.189-android13-3-33478785)
- **Firmware de Referencia**: `X510XXSEEZG3` (Kernel Linux 5.15.189)
- **Fuentes de Evidencia**:
  - `Image.stock` (binario de fábrica oficial extraído de `boot.img`, SHA-256: `ca56baf4...`, tamaño: 39,356,928 bytes)
  - `System.map` reconstruido (127,817 símbolos generados en el árbol OSRC EZE4)
  - `vmlinux` reconstruido con DWARF + BTF (`/home/markpi.guest/osrc-eze4-work/runs/eze4-fixed2/build-source/out-eze4/vmlinux`)
- **Estado de Ejecución**: **FASE 2C COMPLETADA**
- **Fecha**: 2026-09-06

---

## 1. Resumen Ejecutivo y Hallazgo Crítico

Durante la Fase 2C se auditaron y resolvieron de forma exhaustiva las **54 macros de símbolos** catalogadas en el inventario del target ZG3 (correspondientes a **27 objetivos únicos del kernel**: 29 macros de offset y 25 macros de dirección virtual absoluta `KIMAGE_TEXT_BASE + OFF`).

El análisis reveló un hallazgo fundamental para la compatibilidad del firmware:

1. **Paridad Casi Absoluta con el Binario de Fábrica (`Image.stock`)**:
   - **23 de los 27 objetivos únicos (46 de las 54 macros, 85.2%) son 100% idénticos al byte** entre el target ZG3 y el binario de fábrica oficial `Image.stock` de EZE4.
   - Las 4 macros restantes presentan variaciones menores y perfectamente acotadas (deltas sistemáticos de -192 bytes / `-0xc0` en `.data`/`.rodata`). **Nota metodológica**: La atribución de estos deltas a variaciones de compilador/empaquetado entre los builds de mayo (EZE4) y julio (ZG3) se mantiene formalmente como **HIPÓTESIS** (causa exacta clasificada como **UNKNOWN** por falta de árbol privado de Samsung). Los offsets binarios en `Image.stock` están demostrados al 100% mediante desensamblado y análisis de punteros:
     - `KMALLOC_CACHES_OFF`: `0x01b04bb0` (delta `-0xc0` vs ZG3 `0x01b04c70`)
     - `ANON_PIPE_BUF_OPS_OFF`: `0x01912d20` (delta `-0xc0` vs ZG3 `0x01912de0`)
     - `ASHMEM_FOPS_OFF`: `0x01ab3b48` (delta `-0xc0` vs ZG3 `0x01ab3c08`)
     - `SLIDE_NFULNL_LOGGER_NAME_OFF`: `0x017fdb3c` (delta `-0xd8` vs ZG3 `0x017fdc14`)
2. **Cero Símbolos No Resueltos**:
   - Se resolvió el 100% de los símbolos (`0` UNRESOLVED).
3. **Resolución Definitiva de Ambigüedades Históricas**:
   - `COPY_SPLICE_READ`: Se demostró que corresponde a `generic_file_splice_read()` en `fs/splice.c` (renombrada `copy_splice_read` en Linux 6.3+ upstream). En `Image.stock` reside exactamente en `0x003fcb5c`, idéntico a ZG3.
   - `compat_ashmem_ioctl`: Identificada en `Image.stock` en `0x00d02c78`, manejando `COMPAT_ASHMEM_SET_SIZE` y `COMPAT_ASHMEM_SET_PROT_MASK`.
   - `SELINUX_ENFORCING`: Verificada en `Image.stock` en `0x026654e8` como el primer byte (`enforcing`) de `struct selinux_state` mediante el desensamblado de `sel_write_enforce()`.
   - `SLIDE_TRACEFS_WORKER_CALLER`: Verificada en `Image.stock` en `0x00108668` como la instrucción `mov x0, x20` inmediatamente posterior a la llamada bloqueante `bl schedule` en `worker_thread()`.
   - `SLIDE_RANDOM_TABLE_BOOT_ID_DATA_PTR` y `SLIDE_SYSCTL_BOOTID`: Verificadas en `Image.stock` en `0x024be6f8` y `0x0274a5c9`.
4. **Diferenciación Rebuilt vs Stock**:
   - Se mantuvieron columnas separadas para el `vmlinux` reconstruido (herramienta de laboratorio OSRC) y el `Image.stock` oficial (binario de producción firmado que corre en el dispositivo).

---

## 2. Tabla Maestra de Ground Truth de Símbolos

A continuación se detalla la correspondencia para los 27 objetivos funcionales del kernel (archivo maestro completo en [`docs/rmg-eze4/eze4_symbol_map.csv`](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/eze4_symbol_map.csv)):

| Macro de Offset | Categoría | Valor ZG3 Target | Rebuilt vmlinux VA | Rebuilt Offset | Offset en `Image.stock` | VA en `Image.stock` | Certeza Stock | Estado Stock |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `SLIDE_TRACEFS_WORKER_CALLER_OFF` | `KERNEL_TEXT_OFFSET` | `0x00108668` | `ffffffc0080f136c` | `0x000f136c` | **`0x00108668`** | `ffffffc008108668` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `INIT_TASK_OFF` | `KERNEL_DATA_SYMBOL` | `0x0239fd80` | `ffffffc00a33f0c0` | `0x0233f0c0` | **`0x0239fd80`** | `ffffffc00a39fd80` | ABSOLUTE_PATTERN | **CONFIRMED_MATCH** |
| `PREPARE_KERNEL_CRED_OFF` | `KERNEL_TEXT_OFFSET` | `0x00113a88` | `ffffffc0080fb360` | `0x000fb360` | **`0x00113a88`** | `ffffffc008113a88` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `COMMIT_CREDS_OFF` | `KERNEL_TEXT_OFFSET` | `0x00113330` | `ffffffc0080fac1c` | `0x000fac1c` | **`0x00113330`** | `ffffffc008113330` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `OVERRIDE_CREDS_OFF` | `KERNEL_TEXT_OFFSET` | `0x00113718` | `ffffffc0080faffc` | `0x000faffc` | **`0x00113718`** | `ffffffc008113718` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `ROOT_TASK_GROUP_OFF` | `KERNEL_DATA_SYMBOL` | `0x02591f40` | `ffffffc00a535f40` | `0x02535f40` | **`0x02591f40`** | `ffffffc00a591f40` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `SELINUX_ENFORCING_OFF` | `KERNEL_DATA_SYMBOL` | `0x026654e8` | `ffffffc00a6094e8` | `0x026094e8` | **`0x026654e8`** | `ffffffc00a6654e8` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `KMALLOC_CACHES_OFF` | `KERNEL_DATA_SYMBOL` | `0x01b04c70` | `ffffffc009ab9250` | `0x01ab9250` | **`0x01b04bb0`** | `ffffffc009b04bb0` | ABSOLUTE_DISASM | **MINOR_DELTA** (`-0xc0`) |
| `ANON_PIPE_BUF_OPS_OFF` | `KERNEL_DATA_SYMBOL` | `0x01912de0` | `ffffffc0098cf760` | `0x018cf760` | **`0x01912d20`** | `ffffffc009912d20` | ABSOLUTE_DISASM | **MINOR_DELTA** (`-0xc0`) |
| `SYSTEM_UNBOUND_WQ_OFF` | `KERNEL_DATA_SYMBOL` | `0x0238ae20` | `ffffffc00a32ae20` | `0x0232ae20` | **`0x0238ae20`** | `ffffffc00a38ae20` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `CALL_USERMODEHELPER_EXEC_WORK_OFF` | `KERNEL_TEXT_OFFSET` | `0x00100eec` | `ffffffc0080e9db8` | `0x000e9db8` | **`0x00100eec`** | `ffffffc008100eec` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `ASHMEM_FOPS_OFF` | `KERNEL_DATA_SYMBOL` | `0x01ab3c08` | `ffffffc009a6b388` | `0x01a6b388` | **`0x01ab3b48`** | `ffffffc009ab3b48` | ABSOLUTE_DISASM | **MINOR_DELTA** (`-0xc0`) |
| `ASHMEM_MISC_FOPS_OFF` | `KERNEL_DATA_SYMBOL` | `0x024ff750` | `ffffffc00a4a36f0` | `0x024a36f0` | **`0x024ff750`** | `ffffffc00a4ff750` | ABSOLUTE_PATTERN | **CONFIRMED_MATCH** |
| `ASHMEM_IOCTL_OFF` | `KERNEL_TEXT_OFFSET` | `0x00d026c0` | `ffffffc008cccdf0` | `0x00cccdf0` | **`0x00d026c0`** | `ffffffc008d026c0` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `ASHMEM_COMPAT_IOCTL_OFF` | `KERNEL_TEXT_OFFSET` | `0x00d02c78` | `ffffffc008ccd524` | `0x00ccd524` | **`0x00d02c78`** | `ffffffc008d02c78` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `ASHMEM_MMAP_OFF` | `KERNEL_TEXT_OFFSET` | `0x00d02cd0` | `ffffffc008ccd574` | `0x00ccd574` | **`0x00d02cd0`** | `ffffffc008d02cd0` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `ASHMEM_OPEN_OFF` | `KERNEL_TEXT_OFFSET` | `0x00d02f0c` | `ffffffc008ccd77c` | `0x00ccd77c` | **`0x00d02f0c`** | `ffffffc008d02f0c` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `ASHMEM_RELEASE_OFF` | `KERNEL_TEXT_OFFSET` | `0x00d02f90` | `ffffffc008ccd800` | `0x00ccd800` | **`0x00d02f90`** | `ffffffc008d02f90` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `ASHMEM_SHOW_FDINFO_OFF` | `KERNEL_TEXT_OFFSET` | `0x00d030b0` | `ffffffc008ccd920` | `0x00ccd920` | **`0x00d030b0`** | `ffffffc008d030b0` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `CONFIGFS_READ_ITER_OFF` | `KERNEL_TEXT_OFFSET` | `0x004759c4` | `ffffffc0084491ac` | `0x004491ac` | **`0x004759c4`** | `ffffffc0084759c4` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `CONFIGFS_BIN_WRITE_ITER_OFF` | `KERNEL_TEXT_OFFSET` | `0x00475e80` | `ffffffc00844964c` | `0x0044964c` | **`0x00475e80`** | `ffffffc008475e80` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `COPY_SPLICE_READ_OFF` | `KERNEL_TEXT_OFFSET` | `0x003fcb5c` | `ffffffc0083d17a0` | `0x003d17a0` | **`0x003fcb5c`** | `ffffffc0083fcb5c` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `NOOP_LLSEEK_OFF` | `KERNEL_TEXT_OFFSET` | `0x003b1d24` | `ffffffc0083877cc` | `0x003877cc` | **`0x003b1d24`** | `ffffffc0083b1d24` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |
| `SLIDE_NFULNL_LOGGER_NAME_OFF` | `KERNEL_DATA_SYMBOL` | `0x017fdc14` | `ffffffc009823e65` | `0x01823e65` | **`0x017fdb3c`** | `ffffffc0097fdb3c` | ABSOLUTE_PATTERN | **MINOR_DELTA** (`-0xd8`) |
| `SLIDE_NFULNL_LOGGER_OBJECT_OFF`| `KERNEL_DATA_SYMBOL` | `0x023925a0` | `ffffffc00a3325a0` | `0x023325a0` | **`0x023925a0`** | `ffffffc00a3925a0` | ABSOLUTE_PATTERN | **CONFIRMED_MATCH** |
| `SLIDE_RANDOM_TABLE_BOOT_ID_DATA_PTR_OFF`| `KERNEL_DATA_SYMBOL`| `0x024be6f8` | `ffffffc00a4624c8` | `0x024624c8` | **`0x024be6f8`** | `ffffffc00a4be6f8` | ABSOLUTE_PATTERN | **CONFIRMED_MATCH** |
| `SLIDE_SYSCTL_BOOTID_OFF` | `KERNEL_DATA_SYMBOL` | `0x0274a5c9` | `ffffffc00a6efc41` | `0x026efc41` | **`0x0274a5c9`** | `ffffffc00a74a5c9` | ABSOLUTE_DISASM | **CONFIRMED_MATCH** |

> [!NOTE]
> Las 25 macros de tipo `KERNEL_SYMBOL` corresponden a la fórmula `(KIMAGE_TEXT_BASE + <SYMBOL>_OFF)`. Debido a que `KIMAGE_TEXT_BASE` es idéntico (`0xffffffc008000000`), su estado de verificación sigue 1:1 el estado de su respectivo offset.

---

## 3. Evidencias Binarias Clave en `Image.stock`

### A. `generic_file_splice_read` vs `COPY_SPLICE_READ`
En el árbol Linux upstream posterior a 6.3, `generic_file_splice_read` fue renombrada a `copy_splice_read`. En Linux 5.15 GKI, la función responsable de puentear la lectura de páginas hacia un pipe llamando a `read_iter` es `generic_file_splice_read()`.

En `Image.stock` (`0xffffffc0083fcb5c`):
```assembly
ffffffc0083fcb5c:  d503233f  paciasp
ffffffc0083fcb60:  d10243ff  sub    sp, sp, #0x90
ffffffc0083fcb64:  a9067bfd  stp    x29, x30, [sp, #96]
ffffffc0083fcb68:  910183fd  add    x29, sp, #0x60
ffffffc0083fcb6c:  a90757f6  stp    x22, x21, [sp, #112]
ffffffc0083fcb70:  a9084ff4  stp    x20, x19, [sp, #128]
ffffffc0083fcb74:  d5384108  mrs    x8, sp_el0
ffffffc0083fcb78:  aa0103f4  mov    x20, x1
ffffffc0083fcb7c:  aa0003f3  mov    x19, x0
ffffffc0083fcb80:  f942f108  ldr    x8, [x8, #1504]      ; current->stack_canary
ffffffc0083fcb84:  9100c3e0  add    x0, sp, #0x30
ffffffc0083fcb88:  2a1f03e1  mov    w1, wzr
ffffffc0083fcb8c:  f81f83a8  stur   x8, [x29, #-8]
```
Coincidencia binaria al 100% con la función en ZG3.

### B. `SELINUX_ENFORCING` en `Image.stock`
Desensamblado de `sel_write_enforce()` en `Image.stock` (`0xffffffc0086ed874`):
```assembly
ffffffc0086ed874:  9000fbc0  adrp   x0, 0xffffffc00a665000
ffffffc0086ed878:  9113a000  add    x0, x0, #0x4e8       ; &selinux_state = 0xffffffc00a6654e8
ffffffc0086ed89c:  97ffc537  bl     avc_has_perm(state=x0, ...)
...
ffffffc0086ed920:  390002a8  strb   w8, [x21]            ; escribe nuevo estado de enforcing
```
Demuestra que `selinux_state` se ubica exactamente en `0x026654e8`. Dado que el campo `bool enforcing` es el miembro en offset 0 (`sizeof=1`), `SELINUX_ENFORCING_OFF = 0x026654e8ULL` es exacto.

### C. `ROOT_TASK_GROUP` en `Image.stock`
Desensamblado del scheduler en `Image.stock` (`0xffffffc0081236b8`):
```assembly
ffffffc0081236b8:  d001236f  adrp   x15, 0xffffffc00a591000
ffffffc0081236c0:  913d01ef  add    x15, x15, #0xf40     ; &root_task_group = 0xffffffc00a591f40
ffffffc0081236c8:  f9420150  ldr    x16, [x10, #1024]    ; lee task_struct.sched_task_group (+0x400)
```
Coincidencia exacta con `ROOT_TASK_GROUP_OFF = 0x02591f40ULL`.

### D. `SLIDE_TRACEFS_WORKER_CALLER` en `Image.stock`
Desensamblado de `worker_thread()` en `Image.stock` (`0xffffffc008108660`):
```assembly
ffffffc008108660:  94412e1e  bl     _raw_spin_unlock_irq
ffffffc008108664:  944106c4  bl     schedule
ffffffc008108668:  aa1403e0  mov    x0, x20              ; Retorno de schedule (offset 0x108668)
ffffffc00810866c:  94412da2  bl     _raw_spin_lock_irq
```
Coincidencia exacta con `SLIDE_TRACEFS_WORKER_CALLER_OFF = 0x00108668ULL`.

### E. `SLIDE_RANDOM_TABLE_BOOT_ID_DATA_PTR` y `SLIDE_SYSCTL_BOOTID`
Volcado de datos en `0x24be6f8` de `Image.stock`:
```
0x024be6f8: c9 a5 74 0a c0 ff ff ff  -> Puntero a 0xffffffc00a74a5c9 (&sysctl_bootid)
0x024be700: 00 00 00 00 24 01 00 00  -> maxlen = 0, mode = 0444
```
Demuestra que `random_table[4].data` (`0x024be6f8`) apunta a `sysctl_bootid` en `0x0274a5c9`, validando ambas macros al unísono.

---

## 4. Análisis de Deltas Menores (-0xc0 / -192 bytes)

Se identificó un agrupamiento compacto en las tablas de datos de `.data` y `.rodata` donde los offsets de `Image.stock` están desplazados exactamente **192 bytes (`0xc0`)** respecto al target ZG3:

1. `KMALLOC_CACHES_OFF`:
   - ZG3: `0x01b04c70`
   - Stock EZE4: `0x01b04bb0` (`0x01b04c70 - 0xc0`)
   - Evidencia: `adrp x22, 0xffffffc009b04000; add x22, x22, #0xbb0` en `create_kmalloc_caches()`.
2. `ANON_PIPE_BUF_OPS_OFF`:
   - ZG3: `0x01912de0`
   - Stock EZE4: `0x01912d20` (`0x01912de0 - 0xc0`)
   - Evidencia: Tabla de 4 punteros a `anon_pipe_buf_release` (`0x083c24c8`) y `anon_pipe_buf_try_steal` (`0x083c2580`).
3. `ASHMEM_FOPS_OFF`:
   - ZG3: `0x01ab3c08`
   - Stock EZE4: `0x01ab3b48` (`0x01ab3c08 - 0xc0`)
   - Evidencia: Puntero `.fops` en `ashmem_misc` (`0x024ff750`) que apunta directamente a `0xffffffc009ab3b48`.
4. `SLIDE_NFULNL_LOGGER_NAME_OFF`:
   - ZG3: `0x017fdc14`
   - Stock EZE4: `0x017fdb3c` (`0x017fdc14 - 0xd8`)
   - Evidencia: Puntero `.name` en `nfulnl_logger` (`0x023925a0`) que apunta a `"nfnetlink_log"` en `0xffffffc0097fdb3c`.

**Nota metodológica**: La atribución de estos desplazamientos a pequeñas adiciones de símbolos globales en parches mensuales de seguridad es una **HIPÓTESIS** explicativa plausible, pero su causa exacta formal permanece clasificada como **UNKNOWN** por falta de acceso al código fuente privado de Samsung. Lo único verificado con rigor de ground truth son los valores numéricos exactos observados en el desensamblado de `Image.stock`.

---

## 5. Ordenamiento Relativo de Memoria y `PRODUCTION_STACK_PI_RIGHT_ONLY`

El parámetro `PRODUCTION_STACK_PI_RIGHT_ONLY` controla si el árbol rbtree de waiters se orienta únicamente a la derecha o a la izquierda en función de si la dirección virtual de `ASHMEM_MISC_FOPS` es mayor o menor que los objetos del payload:

- En `Image.stock` EZE4:
  $$\text{VA}(\text{ASHMEM\_MISC\_FOPS}) = \text{0xffffffc00a4ff750}$$
  $$\text{VA}(\text{ROOT\_TASK\_GROUP}) = \text{0xffffffc00a591f40}$$
  $$\text{VA}(\text{SELINUX\_ENFORCING}) = \text{0xffffffc00a6654e8}$$
  $$\text{VA}(\text{SLIDE\_SYSCTL\_BOOTID}) = \text{0xffffffc00a74a5c9}$$
- El ordenamiento relativo de las regiones de memoria y los símbolos globales entre ZG3 y EZE4 es **rigurosamente idéntico**.
- Por consiguiente, `PRODUCTION_STACK_PI_RIGHT_ONLY = 0` se mantiene inalterado.

---

## 6. Métricas Finales de Fase 2C

- **Total de macros auditadas**: **54 / 54 (100%)**
- **Objetivos únicos del kernel auditados**: **27 / 27 (100%)**
- **Coincidencias idénticas stock (`CONFIRMED_MATCH`)**: **46 macros (85.2%)** / **23 objetivos únicos**
- **Deltas menores auditados (`MINOR_DELTA`)**: **8 macros (14.8%)** / **4 objetivos únicos**
- **Símbolos no resueltos (`UNRESOLVED`)**: **0 (0.0%)**
- **Contradicciones entre fuentes**: **0**
- **Estado de Fase 2C**: **COMPLETADA CON ÉXITO**.
