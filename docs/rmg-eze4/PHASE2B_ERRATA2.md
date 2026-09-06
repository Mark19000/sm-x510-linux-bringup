# Errata Técnico de Fase 2B: Ajustes de Rigor Metodológico y Reclasificaciones

- **Documento Corregido**: `docs/rmg-eze4/PHASE2B.md`, `zg3_target_inventory_v2.csv`, `zg3_eze4_struct_diff.md`
- **Fecha de Errata**: 2026-09-06
- **Alcance**: Eliminación de sobreafirmaciones de compatibilidad global de ABI, distinción formal entre `sizeof(struct mm_struct)` y la geometría del asignador SLUB, resolución técnica de las macros de oráculo P0 y ajuste de fuentes de derivación arquitectónicas.

---

## 1. Ajuste de Afirmación de Compatibilidad de ABI

- **Redacción Previa**: *"ABI interna 100% compatible"*.
- **Corrección Metodológica**: La auditoría estática realizada cubre de manera exhaustiva los campos y estructuras utilizados por el exploit de referencia, pero no evalúa los miles de miembros de estructuras no relacionadas en el árbol del kernel.
- **Formulación Rigurosa**:
  > **"53/53 parámetros estructurales relevantes para el target auditados son idénticos entre ZG3 target y EZE4."**

---

## 2. Precisión de `MM_STRUCT_SZ`: `sizeof` vs Allocation Bucket SLUB

- **Ground Truth Extraído de BTF / DWARF**:
  $$\text{sizeof}(\text{struct mm\_struct}) = 992 \text{ bytes } (\mathbf{0x3e0})$$
- **Geometría del Asignador SLUB (`kmalloc-1k`)**:
  - En Linux con el asignador SLUB, las solicitudes de memoria en el rango $(512, 1024]$ bytes son satisfechas por la caché general de slab `kmalloc-1k` ($1024 \text{ bytes} = \mathbf{0x400}$).
  - `MM_STRUCT_SZ = 0x400` modela el tamaño del **slot de asignación (allocation bucket)** en el slab, no el tamaño en bytes del struct en sí.
- **Acción**:
  - No representar ningún miembro artificial denominado `alloc_bucket` en `struct mm_struct`.
  - Registrar formalmente `sizeof(struct mm_struct) = 0x3e0` y documentar `0x400` como el tamaño de bucket SLUB derivado de `BTF + geometría SLUB`.

---

## 3. Resolución Funcional de Macros de P0 Oracle

En la primera versión del inventario se clasificaron de forma imprecisa como include guards. La inspección del código fuente en `src/oracle.c` (líneas 280–295) establece su verdadero propósito algorítmico:

```c
/* En src/oracle.c */
#ifdef P0_FINGERPRINT_MIN_BEST
  if (best_score < P0_FINGERPRINT_MIN_BEST ||
      best_score - second_score < P0_FINGERPRINT_MIN_MARGIN) {
    pr_warning("p0 fingerprint rejected low-confidence best=%d second=%d "
               "min_best=%d margin=%d\n",
               best_score, second_score,
               P0_FINGERPRINT_MIN_BEST, P0_FINGERPRINT_MIN_MARGIN);
    return (uintptr_t)-1;
  }
#endif
```

- **`P0_FINGERPRINT_MIN_BEST` (5)**: Umbral mínimo de palabras coincidentes (sobre un total de 8 palabras de 64 bits muestreadas en la página) para aceptar una identificación positiva del slide de KASLR en el oráculo físico.
  - **Categoría**: `EXPLOIT_ALGORITHM_CONSTANT`
  - **Fuente de Derivación**: `EMPIRICAL`
- **`P0_FINGERPRINT_MIN_MARGIN` (3)**: Margen de desambiguación exigido entre el mejor candidato (`best_score`) y el segundo mejor (`second_score`) para descartar falsos positivos producidos por páginas con patrones repetitivos.
  - **Categoría**: `EXPLOIT_ALGORITHM_CONSTANT`
  - **Fuente de Derivación**: `EMPIRICAL`

---

## 4. Revisión de `DERIVATION_SOURCE` para Macros Críticas de Ruta

- **`PRODUCTION_STACK_PI_RIGHT_ONLY`**:
  - Su fijación en `0` (Tab S9 FE) vs `1` (teléfonos Galaxy S24) depende estrictamente de la relación de orden entre la dirección virtual de `ASHMEM_MISC_FOPS` y el nodo padre simulado (`fake_fops`) en el espacio de memoria virtual del kernel.
  - **Categoría**: `EXPLOIT_ALGORITHM_CONSTANT`
  - **Fuente de Derivación Corregida**: `KERNEL_MEMORY_LAYOUT` (ordenamiento relativo de secciones y símbolos virtuales en `vmlinux`).
- **`SLIDE_ROUTE`**:
  - Su selección (`SLIDE_ROUTE_FPSIMD`) está determinada por la arquitectura de CPU ARM64 (disponibilidad de registros vectoriales de 128 bits en `struct fpsimd_context` en el marco de señal `ucontext_t`) y por el entorno de seguridad SELinux de Android (que bloquea sockets de red multicast).
  - **Categoría**: `EXPLOIT_ALGORITHM_CONSTANT`
  - **Fuente de Derivación Corregida**: `SOC_ARCHITECTURE` (mecanismo estándar de entrega de señales en `aarch64` y restricciones de plataforma).
