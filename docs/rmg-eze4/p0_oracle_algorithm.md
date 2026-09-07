# Technical Audit of the P0 Oracle Algorithm (KASLR Physical Slide Oracle)

- **Device**: Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510` / `gts9fewifi`)
- **SoC**: Samsung Exynos 1380 (`s5e8835`)
- **Target Base Firmware**: `X510XXUCEZE4` (Kernel Linux 5.15.189)
- **Reference Firmware**: `X510XXSEEZG3` (Kernel Linux 5.15.189)
- **Audited Code Files**:
  - `src/oracle.c`
  - `src/targets/gts9fewifi-X510XXSEEZG3/p0_fingerprint.h`
  - `src/targets/gts9fewifi-X510XXSEEZG3/target.h`
  - `tools/generate_p0_fingerprint.pl`
  - `src/slide_app.c`, `src/fops.c`, `src/pselect.c`, `src/fpsimd.c`
- **Date**: 2026-09-06

---

## 1. Fundamentals and Purpose of P0

### What is P0?
In the Samsung Exynos 1380 physical memory architecture, **P0** refers to the kernel DRAM physical load base (`P0_KERNEL_PHYS_LOAD = 0x80000000ULL`).

In the context of the *Root-My-Galaxy* suite, the **P0 Oracle** (*Physical Page 0 Oracle*) is a KASLR (*Kernel Address Space Layout Randomization*) leak mechanism operating in the physical memory domain. Unlike traditional leak techniques based on network sockets (multicast), user-page timing, or `/proc` and `sysfs` interfaces (heavily restricted by SELinux on Android 13/14), the P0 oracle uses the geometry of Linux pipe buffers (40-byte / `0x28` `struct user_pipe_buffer`) and physical probe primitives to read a kernel memory page without prior root privileges.

### What does it attempt to identify?
Its exclusive goal is to determine with absolute mathematical certainty the KASLR randomization offset **`slide`** in the current boot session:
$$\text{VA}(\text{symbol}) = \text{KIMAGE\_TEXT\_BASE} + \text{offset} + \text{slide}$$

In Samsung's ARM64 architecture:
- `KIMAGE_TEXT_BASE = 0xffffffc008000000ULL`
- `slide \in [0x000000, 0x1f0000]`

By obtaining the `slide`, the exploit runtime derandomizes all control functions (`commit_creds`, `prepare_kernel_cred`, return gadgets).

---

## 2. Parameters and Mechanism of the Physical Oracle

### Macro `PHYS_P0_ORACLE`
Defined in `target.h` (`#define PHYS_P0_ORACLE 1`), instructs the compiler and runtime to compile and use functions in `src/oracle.c` (`prepare_p0_pipe_oracle`, `verify_p0_pipe_oracle_gate`, `scan_p0_pipe_oracle`, `restore_p0_oracle_pages`). If set to 0, the exploit would depend on network oracles like multicast (`SLIDE_USE_MCAST`) or tracefs (`SLIDE_USE_TRACEFS`), both inoperative or unstable in Samsung One UI 6 SELinux environment.

### Use of `P0_ORACLE_PROBE_OFFSET`
Defined for Tab S9 FE as:
$$\text{P0\_ORACLE\_PROBE\_OFFSET} = \text{0x1f0000ULL} \quad (2\text{ MB})$$

The exploit configures a fixed physical probe page located at exactly $2\text{ MB}$ from the DRAM physical base:
$$P_{\text{probe}} = P_{\text{base}} + \text{P0\_ORACLE\_PROBE\_OFFSET} = \text{0x80000000} + \text{0x1f0000} = \text{0x801f0000}$$

When the bootloader loads the kernel with a random KASLR slide $\text{slide}$, the kernel start is positioned at:
$$P_{\text{load}} = P_{\text{base}} + \text{slide}$$

Therefore, the relative position within the `Image` binary exposed under the physical probe address $P_{\text{probe}}$ is:
$$P_{\text{load}} + \text{Image\_offset} = P_{\text{probe}}$$
$$(P_{\text{base}} + \text{slide}) + \text{Image\_offset} = P_{\text{base}} + \text{P0\_ORACLE\_PROBE\_OFFSET}$$
$$\mathbf{\text{Image\_offset} = \text{P0\_ORACLE\_PROBE\_OFFSET} - \text{slide}}$$

This formula is the cornerstone of the oracle: **as kernel slide grows, the window observed at the physical page shifts backwards in the Image file**.

---

## 3. Discrepancy: 32 vs 125 Candidates and `SLIDE_KASLR_STEP`

### How does `SLIDE_KASLR_STEP` come into play?
The KASLR step (`SLIDE_KASLR_STEP`) defines the minimum alignment granularity allowed by the kernel when randomizing its load address.
- On most flagship phones (Galaxy S24/S23, Qualcomm or Exynos 2400 SoC), the step is **64 KB** (`0x10000`).
- On the Samsung Galaxy Tab S9 FE family and mid-range phones with Exynos 1380 (`s5e8835`), the kernel uses a **16 KB** step (`0x4000`):
  $$\text{SLIDE\_KASLR\_STEP} = \text{0x4000ULL} \quad (16\text{ KB})$$

### Why are there 32 candidates in some and 125 in others?
The oracle search space spans a total window of $2\text{ MB}$ (`0x1f0000`).
1. **64 KB devices (`0x10000`)**:
   $$\text{Candidates} = \frac{\text{0x1f0000}}{\text{0x10000}} + 1 = 31 + 1 = \mathbf{32\text{ entries}}$$
   (Slides: `0x000000`, `0x010000`, `0x020000`, ..., `0x1f0000`).
2. **Tab S9 FE / Exynos 1380 (`0x4000`)**:
   $$\text{Candidates} = \frac{\text{0x1f0000}}{\text{0x4000}} + 1 = 124 + 1 = \mathbf{125\text{ entries}}$$
   (Slides: `0x000000`, `0x004000`, `0x008000`, ..., `0x1f0000`).

The historical mention of "32 candidates" derives from the original design for 64 KB devices, but the actual implementation for `gts9fewifi` mandatorily requires **125 candidates** to cover the 16 KB grid.

---

## 4. Fingerprint Structure

### The 8 Intra-page Offsets
Within a standard 4 KB physical page (4096 bytes / `0x1000`), samples are taken at 8 offsets uniformly spaced by 512 bytes (`0x200`):
$$\{ \text{0x000}, \text{0x200}, \text{0x400}, \text{0x600}, \text{0x800}, \text{0xa00}, \text{0xc00}, \text{0xe00} \}$$

This intra-page dispersion ensures that the fingerprint samples:
- Block start (`0x000`)
- Intermediate points every half kilobyte
- Block end (`0xe00` to `0xe07`)

Preventing pages with identical headers or zero-padding areas from causing false matches.

### Representation of Each Word (`word`)
Each word stored in `words[8]` is an unsigned 64-bit integer (`uint64_t`, 8 bytes) in ARM64 little-endian format:
```c
struct p0_fingerprint {
  uintptr_t slide;
  uint64_t words[8];
};
```
Each word directly extracts the 8 binary bytes from the static image:
$$\text{words}[i] = \text{Image}[(\text{P0\_ORACLE\_PROBE\_OFFSET} - \text{slide}) + \text{offset}_i]$$

Since kernel `.text` code and `.rodata` tables are immutable during execution, these 64 total bytes form a cryptographically robust signature of the projected physical page.

---

## 5. Scoring Algorithm, Confidence, and Collisions

### Score Calculation (`p0_fingerprint_score`)
In `src/oracle.c:197-208`, the comparison is evaluated word by word:
```c
static int p0_fingerprint_score(
    const unsigned char *page, const struct p0_fingerprint *fingerprint) {
  int score = 0;
  for (size_t index = 0; index < P0_FINGERPRINT_WORDS; index++) {
    uint64_t value = 0;
    memcpy(&value, page + p0_fingerprint_offsets[index], sizeof(value));
    if (value == fingerprint->words[index]) {
      score++;
    }
  }
  return score;
}
```
The final score of a comparison is a discrete integer in the range $[0, 8]$.

### Criterion `P0_FINGERPRINT_MIN_BEST = 5`
- Establishes that the best candidate must have at least **5 out of 8 identical words** ($62.5\%$ minimum match).
- If the page read from the pipe were empty, contained user-memory garbage, or were corrupted, the typical score is $\le 1$. Enforcing $\text{score} \ge 5$ automatically discards any failed read before committing an erroneous address.

### Criterion `P0_FINGERPRINT_MIN_MARGIN = 3`
- Establishes the required separation between the winning candidate and its nearest competitor:
  $$\text{best\_score} - \text{second\_score} \ge 3$$
- If the best candidate scores 6 points and the second scores 4 points ($\text{margin} = 2 < 3$), the sample is considered ambiguous and is **rejected**.
- This protects against accidental collisions produced by repetitive code patterns in the kernel (for example, consecutive NOP sequences or stub functions).

### Collision Handling
In `src/oracle.c:278-292`:
1. If not exactly 1 page is modified (`changed_pages != 1`), returns `-1`.
2. If there is a tie ($\text{best\_score} \le \text{second\_score}$), returns `-1`.
3. If threshold or margin is not exceeded, the oracle emits:
   `p0 fingerprint rejected low-confidence best=%d second=%d min_best=%d margin=%d`
   and returns `(uintptr_t)-1`.
4. The caller process (`slide_app.c`) detects the `-1` value and retries the oracle with a fresh, clean attempt, **avoiding triggering a kernel panic**.

---

## 6. Conclusion of the P0 Algorithm Audit

The P0 algorithm is a highly optimized, deterministic, and mathematically formalized probabilistic discriminator:
- Total candidates in EZE4: **125 entries** (step `0x4000` across window `0x1f0000`).
- Sampling: **8 64-bit words** (64 bytes/page at offsets `0x200`).
- Validation: **Score $\ge 5$** with **Margin $\ge 3$**.
