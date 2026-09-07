# Phase 2A Technical Errata: task_struct Offsets in remove_waiter()

- **Corrected Document**: `docs/rmg-eze4/stock_rtmutex_binary_verification.md` (Section 5, item 4)
- **Errata Date**: 2026-09-06
- **Scope**: Correction of operand attribution `#2208` in stock EZE4 binary disassembly (`Image.stock`) and formal resolution of members located at `0x8a0` and `0x8a8`.

---

## 1. Identification of Error in Phase 2A

In the Phase 2A report, Section 5 stated:
> *"4. `TASK_STRUCT_PI_TOP_TASK_OFF`: `0x8a8` (decimal 2208 + 8). Evidencia: `ldr x8, [x21, #2208]` en `0xffffffc009150734` y `0xffffffc009150748`."*

### Mathematical and Semantic Error:
- **Base Conversion**: $2208_{10} = \mathbf{0x8a0}_{16}$ (exact), **not** `0x8a8`.
- **Erroneous Interpretation**: The `ldr x8, [x21, #2208]` instruction was not accessing the `pi_top_task` pointer, but another specific member of the structure.
- **Corrective Action**: Do not propagate this attribution, and determine via Ground Truth (BTF / DWARF) the precise assignment of offsets `0x8a0` and `0x8a8`.

---

## 2. Resolution via BTF and DWARF (EZE4 `vmlinux`)

Inspection of `struct task_struct` (Type ID 462) in BTF and DWARF of the EZE4 kernel reveals the following contiguous physical layout:

```
/* Decimal Offset */  /* Hex Offset */  /* Type and Member */
2176                  0x880              spinlock_t alloc_lock; (size: 4)
2180                  0x884              raw_spinlock_t pi_lock; (size: 4)
2184                  0x888              struct wake_q_node wake_q; (size: 8)
2192                  0x890              int wake_q_count; (size: 4)
                      [4-byte alignment hole]
2200                  0x898              struct rb_root_cached pi_waiters; (size: 16)
2216                  0x8a8              struct task_struct *pi_top_task; (size: 8)
2224                  0x8b0              struct rt_mutex_waiter *pi_blocked_on; (size: 8)
```

### Internal Breakdown of `struct rb_root_cached` (Type ID 496):
The `pi_waiters` field is not a simple pointer, but a 16-byte structure optimizing the red-black tree by retaining a direct pointer to the highest priority node (`rb_leftmost`):

```c
struct rb_root_cached {
    struct rb_root rb_root;     /* Offset +0 (in task_struct: 2200 / 0x898), size: 8 */
    struct rb_node *rb_leftmost;/* Offset +8 (in task_struct: 2208 / 0x8a0), size: 8 */
};
```

---

## 3. Definitive Offset Assignment

| Decimal Offset | Hex Offset | Member in `struct task_struct` | Data Type | Size |
| :---: | :---: | :--- | :--- | :---: |
| **2200** | **`0x898`** | `pi_waiters.rb_root` | `struct rb_root` (`struct rb_node *`) | 8 bytes |
| **2208** | **`0x8a0`** | `pi_waiters.rb_leftmost` | `struct rb_node *` | 8 bytes |
| **2216** | **`0x8a8`** | `pi_top_task` | `struct task_struct *` | 8 bytes |
| **2224** | **`0x8b0`** | `pi_blocked_on` | `struct rt_mutex_waiter *` | 8 bytes |

---

## 4. Reinterpretation of `Image.stock` Disassembly

In factory binary function `remove_waiter()`:
- `x21` stores the `owner` pointer (`struct task_struct *`).
- At line `ffffffc009150734`:
  ```asm
  ffffffc009150734:  f94452a8  ldr  x8, [x21, #2208]
  ```
  The instruction dereferences `owner->pi_waiters.rb_leftmost` (offset `0x8a0` / 2208), extracting the red-black tree node representing the highest priority waiter in the owner's queue.
- At line `ffffffc009150748`:
  ```asm
  ffffffc009150748:  f90452a0  str  x0, [x21, #2208]
  ```
  The instruction updates `owner->pi_waiters.rb_leftmost = x0` following tree reorganization.

### Status of `TASK_STRUCT_PI_TOP_TASK_OFF`:
- The macro in target ZG3 defines:
  ```c
  #define FAKE_TASK_PI_TOP_TASK_OFF 0x8a8
  ```
- **Conclusion**: The value `0x8a8` for `pi_top_task` is **completely correct** on EZE4 (offset 2216). The error in Phase 2A was solely citing `#2208` (`0x8a0`) as evidence for `0x8a8`, when `#2208` corresponds to `pi_waiters.rb_leftmost`.
