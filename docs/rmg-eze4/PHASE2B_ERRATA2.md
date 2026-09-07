# Phase 2B Technical Errata: Methodological Rigor Adjustments and Reclassifications

- **Corrected Document**: `docs/rmg-eze4/PHASE2B.md`, `zg3_target_inventory_v2.csv`, `zg3_eze4_struct_diff.md`
- **Errata Date**: 2026-09-06
- **Scope**: Elimination of global ABI compatibility overclaims, formal distinction between `sizeof(struct mm_struct)` and SLUB allocator geometry, technical resolution of P0 oracle macros, and adjustment of architectural derivation sources.

---

## 1. ABI Compatibility Claim Adjustment

- **Previous Wording**: *"ABI interna 100% compatible"*.
- **Methodological Correction**: The static audit performed exhaustively covers the fields and structures used by the reference exploit, but does not evaluate the thousands of unrelated structure members across the kernel tree.
- **Rigorous Formulation**:
  > **"53/53 target-relevant structural parameters audited are identical between ZG3 target and EZE4."**

---

## 2. Precision of `MM_STRUCT_SZ`: `sizeof` vs SLUB Allocation Bucket

- **Ground Truth Extracted from BTF / DWARF**:
  $$\text{sizeof}(\text{struct mm\_struct}) = 992 \text{ bytes } (\mathbf{0x3e0})$$
- **SLUB Allocator Geometry (`kmalloc-1k`)**:
  - In Linux with the SLUB allocator, memory requests in the range $(512, 1024]$ bytes are satisfied by the general slab cache `kmalloc-1k` ($1024 \text{ bytes} = \mathbf{0x400}$).
  - `MM_STRUCT_SZ = 0x400` models the **allocation bucket size** in the slab, not the byte size of the struct itself.
- **Action**:
  - Do not represent any artificial member called `alloc_bucket` in `struct mm_struct`.
  - Formally record `sizeof(struct mm_struct) = 0x3e0` and document `0x400` as the SLUB bucket size derived from `BTF + SLUB geometry`.

---

## 3. Functional Resolution of P0 Oracle Macros

In the initial inventory version, these were imprecisely classified as include guards. Source code inspection in `src/oracle.c` (lines 280–295) establishes their true algorithmic purpose:

```c
/* In src/oracle.c */
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

- **`P0_FINGERPRINT_MIN_BEST` (5)**: Minimum threshold of matching words (out of a total of 8 64-bit words sampled on the page) to accept a positive KASLR slide identification in the physical oracle.
  - **Category**: `EXPLOIT_ALGORITHM_CONSTANT`
  - **Derivation Source**: `EMPIRICAL`
- **`P0_FINGERPRINT_MIN_MARGIN` (3)**: Disambiguation margin required between the best candidate (`best_score`) and second best (`second_score`) to discard false positives caused by repetitive pattern pages.
  - **Category**: `EXPLOIT_ALGORITHM_CONSTANT`
  - **Derivation Source**: `EMPIRICAL`

---

## 4. Revision of `DERIVATION_SOURCE` for Critical Route Macros

- **`PRODUCTION_STACK_PI_RIGHT_ONLY`**:
  - Setting to `0` (Tab S9 FE) vs `1` (Galaxy S24 phones) strictly depends on the order relationship between the virtual address of `ASHMEM_MISC_FOPS` and the simulated parent node (`fake_fops`) in kernel virtual memory space.
  - **Category**: `EXPLOIT_ALGORITHM_CONSTANT`
  - **Corrected Derivation Source**: `KERNEL_MEMORY_LAYOUT` (relative ordering of virtual sections and symbols in `vmlinux`).
- **`SLIDE_ROUTE`**:
  - Selection (`SLIDE_ROUTE_FPSIMD`) is determined by the ARM64 CPU architecture (availability of 128-bit vector registers in `struct fpsimd_context` in signal frame `ucontext_t`) and by Android SELinux security policy (blocking multicast network sockets).
  - **Category**: `EXPLOIT_ALGORITHM_CONSTANT`
  - **Corrected Derivation Source**: `SOC_ARCHITECTURE` (standard signal delivery mechanism in `aarch64` and platform restrictions).
