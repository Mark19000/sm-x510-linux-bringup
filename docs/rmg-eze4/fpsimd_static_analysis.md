# Static Analysis: Macros `SLIDE_ROUTE_FPSIMD` and `PRODUCTION_STACK_PI_RIGHT_ONLY`

- **Objective**: Static investigation of the purpose, architectural dependencies, controlled code, and technical justification of the configuration macros found in the ZG3 target (`src/targets/gts9fewifi-X510XXSEEZG3/target.h`).
- **Audited Repository**: `Root-My-Galaxy-Payloads-ZG3` (branch `gts9fewifi-X510XXSEEZG3-v4`)
- **Audit Date**: 2026-09-06
- **Scope**: Exclusively software design analysis and architectural compatibility.

---

## 1. Macro: `SLIDE_ROUTE_FPSIMD`

### 1.1 Declaration and Definition
- In `src/common.h`:
  ```c
  #define SLIDE_ROUTE_PSELECT 0
  #define SLIDE_ROUTE_MCAST   1
  #define SLIDE_ROUTE_FPSIMD  2
  ...
  #define SLIDE_USE_FPSIMD (SLIDE_ROUTE == SLIDE_ROUTE_FPSIMD)
  ```
- In `src/targets/gts9fewifi-X510XXSEEZG3/target.h`:
  ```c
  #define SLIDE_ROUTE SLIDE_ROUTE_FPSIMD
  ```

### 1.2 Controlled Code
1. **Branch Points**:
   - `src/slide_app.c`: During child sub-process initialization (`slide_log_child_context`) and the wait stack synchronization point (`slide_pi_worker_thread`), selects the copy function:
     ```c
     #if SLIDE_USE_MCAST
       slide_mcast_stack_copy();
     #elif SLIDE_USE_FPSIMD
       slide_fpsimd_stack_copy();
     #else
       slide_pselect_stack_copy();
     #endif
     ```
   - `src/fpsimd.c`: Conditionally compiles the signal handler, ARM64 vector register inspection, and the consumer thread with `sched_setattr`.
   - `src/util.c`: Enables route-specific affinity and `rseq` disabling auxiliary routines.

### 1.3 Kernel Structures and Features Involved
- **ARM64 Signal Delivery Mechanism (`sigaction` / `rt_sigreturn`)**:
  - Upon receiving a signal (in this case `SIGUSR2` sent via `tgkill()`), the Linux kernel constructs a `struct ucontext_t` context frame in user space (or on the alternate signal stack).
  - The ARM64 extension header (`uc_mcontext.__reserved`) contains context blocks headed by `struct _aarch64_ctx`.
  - Among these blocks, `struct fpsimd_context` is included with magic number `FPSIMD_MAGIC` (`0x46508001`).
  - This structure contains the dump of the 32 128-bit vector registers of the FPU/NEON (`vregs[32]`, totaling 512 bytes of contiguous data).
- **Write Window and Structure Aliasing**:
  - Through the signal handler, the code locates the `fpsimd_context` record and writes a `fake_waiter` inside `vregs` space.
  - Upon resuming execution or interacting with the scheduler, the data placed in `vregs` is reflected on the stack according to the `FPSIMD_WAITER_OFF` alignment.

### 1.4 Historical Evolution in the Repository
- **Commit `529d88a` (2026-08-19, by `zainarbani`)**: *"Add fpsimd route & refactor"*.
  - Introduces `src/fpsimd.c` and defines `SLIDE_ROUTE_FPSIMD 2`.
  - Retires exclusive dependency on multicast sockets (`setsockopt` / `IP_MSFILTER`) and `pselect6`.
- **Commit `0062f3d` (2026-08-28, by `zainarbani`)**: *"Switch to fpsimd route"*.
  - Migrates targets `a54x-A546BXXSLFZG3` and `a54x-A546EXXSKFZF4` (Exynos 1380 SoC / `s5e8835`) to `SLIDE_ROUTE_FPSIMD`.
- **Commit `b7a854e` (2026-09-01, by `Hameed Musharaf K`)**: *"V4: FPSIMD route fully working on gts9fewifi-X510XXSEEZG3"*.
  - Adapts and validates the FPSIMD route for Galaxy Tab S9 FE Wi-Fi (`SM-X510`), reporting execution success on attempt 1/8.

### 1.5 Nature Diagnostic: Hardware, Kernel, or Build?
- **Dependency Level**: **CPU Architecture / Kernel Signal Subsystem**.
- **Justification**:
  - Does not depend on an arbitrary firmware offset; relies on the public ARM64 signal ABI (`asm/sigcontext.h`).
  - Adopted on Exynos 1380 devices because strict SELinux policies on Android restrict certain network socket calls (`mcast`), whereas signal delivery and FP/SIMD register handling are completely standard operations for any user-space thread.
  - **Relevance for EZE4**: Since EZE4 shares the same ARM64 v8.2-A architecture and the same 5.15 kernel with the same signal calling conventions, the `SLIDE_ROUTE_FPSIMD` route is conceptually identical between ZG3 and EZE4.

---

## 2. Macro: `PRODUCTION_STACK_PI_RIGHT_ONLY`

### 2.1 Declaration and Definition
- In `src/targets/gts9fewifi-X510XXSEEZG3/target.h`:
  ```c
  #define PRODUCTION_STACK_PI_RIGHT_ONLY 0
  ```
- In other targets (`a54x-A546BXXSLFZG3`, `e1s-S921BXXSFDZE1`, `e2s-S926BXXUEDZDR`):
  ```c
  #define PRODUCTION_STACK_PI_RIGHT_ONLY 1
  ```

### 2.2 Controlled Code
This macro modulates assembling the simulated waiter's red-black tree (rbtree) in copy routines (`fpsimd.c`, `mcast.c`, `pselect.c`):

```c
/* In src/fpsimd.c, src/mcast.c, src/pselect.c */
#if defined(PRODUCTION_STACK_PI_RIGHT_ONLY) && PRODUCTION_STACK_PI_RIGHT_ONLY
  if (slide_oracle_parent == fake_fops &&
      slide_oracle_target == data_addr(ASHMEM_MISC_FOPS)) {
    tree_right = slide_oracle_target;
    tree_left = 0;
    pi_parent = fake_w0 + FAKE_WAITER_PI_TREE_ENTRY_OFF;
    pi_right = 0;
    pi_left = 0;
  }
#endif
```

When `PRODUCTION_STACK_PI_RIGHT_ONLY` is defined as `0` (as in target `gts9fewifi-X510XXSEEZG3`):
- Default assignment is maintained:
  - `tree_left = slide_oracle_target;`
  - `tree_right = 0;`
  - `pi_parent = slide_oracle_parent;`
  - `pi_left = 0;` *(fix incorporated in commit b7a854e: "pi_left=NULL fix in fpsimd.c")*
  - `pi_right = 0;`

### 2.3 Kernel Structures and Features Involved
- **Priority Tree Structure (`struct rb_node` in `struct rt_mutex_waiter`)**:
  - In the priority inheritance locking subsystem, waiters are ordered in a red-black tree according to their priority and memory address.
  - When inserting a simulated node into the lock structure, the algorithm compares the key/address of the parent node (`rb_parent`) with the node to insert (`slide_oracle_target`).
  - Depending on whether the relative virtual address of the target symbol (such as `ASHMEM_MISC_FOPS`) is greater than or less than the parent node in kernel virtual address space, the child must be situated strictly on the left branch (`rb_left`) or right branch (`rb_right`).

### 2.4 Justification of `0` on Galaxy Tab S9 FE (ZG3)
- On mobile devices such as Galaxy S24 (`e1s`) or Galaxy S24+ (`e2s`), the location of fops variables and dynamic tables in virtual address space required linking the right branch (`PRODUCTION_STACK_PI_RIGHT_ONLY 1`).
- On Galaxy Tab S9 FE (`SM-X510`), the target author discovered empirically that for this specific kernel binary (`ZG3`), insertion is only valid oriented toward the left branch (`tree_left = slide_oracle_target`), requiring setting `PRODUCTION_STACK_PI_RIGHT_ONLY 0`.

### 2.5 Nature Diagnostic: Hardware, Kernel, or Build?
- **Dependency Level**: **Kernel Virtual Layout / Firmware Build**.
- **Justification**:
  - Directly depends on the relative virtual address of symbols in the kernel image (`System.map`) and linker (LLD) decisions on `.data` and `.rodata` section ordering.
  - **Relevance for EZE4**: In Section 4 of the preliminary audit, virtual addresses and symbol offsets in EZE4 were shown to differ substantially from ZG3 (for example, `init_task` shifted from `0x239fd80` to `0x233f0c0`, and `kmalloc_caches` from `0x1b04c70` to `0x1ab9250`).
  - Therefore, if the ordering relationship between parent and child node virtual addresses differs in EZE4, this macro cannot be inherited blindly and requires rigorous static validation of relative addresses from the EZE4 `System.map`.
