# Phase 3B Closure Report: P0 Fingerprint Quality, Collision Analysis, and Offline Validation

- **Device**: Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510` / `gts9fewifi`)
- **SoC**: Samsung Exynos 1380 (`s5e8835`)
- **Target Base Firmware**: `X510XXUCEZE4` (Kernel Linux 5.15.189-android13-3-33478785)
- **Reference Firmware**: `X510XXSEEZG3` (Kernel Linux 5.15.189-android13-3-33478785)
- **Date**: 2026-09-06
- **Phase 3B Status**: **COMPLETED**
- **Scope**: Exclusively static audit, combinatorial analysis, and offline data validation.

---

## 1. Executive Summary of Phase 3B

In this phase, the KASLR fingerprint table of the P0 oracle was subjected to a rigorous battery of combinatorial tests, positional entropy analysis, corruption degradation simulation, and binary comparison against the previous ZG3 build.

Essential results:
1. **Binary Rederivation Audit**: Each of the 1,000 QWORDs (125 candidates $\times$ 8 positions) was rederived directly from `artifacts/stock/images/Image.stock` (SHA-256: `ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9`). The result is **`EXACT_MATCH`** (100% consistency).
2. **125 $\times$ 125 Similarity Matrix**: 96.80% of candidates (121/125 slides) achieve the maximum category **`PASS_STRONG`** with a separation margin $\ge 5$ words relative to the nearest competitor.
3. **Collision Zone Identification**: The only 4 entries that did not achieve `PASS_STRONG` correspond to the upper tail slides:
   - `FAIL_SLIDES`: `0x1e4000`, `0x1e8000`, `0x1ec000` ($\text{margin} = 0$, `best_other_score = 8`).
   - `BORDERLINE_SLIDES`: `0x1f0000` ($\text{margin} = 1$, `best_other_score = 7`).
   These 4 entries physically map to header offsets `0x00c000`, `0x008000`, `0x004000`, and `0x000000` of the `Image` binary, which contain ARM64 kernel `nop` instruction padding sequences (`0xd503201fd503201f`). This property is identical in the ZG3 reference table.
4. **Fault Simulation (11,500 Evaluated Cases)**:
   - **0 misidentifications** (0.00%): Not a single corrupted pattern produced an erroneous slide selection.
   - Across the 121 code slides (`0x000000` to `0x1e0000`), the correct identification rate is **100.00%** with 1, 2, and even 3 corrupted QWORDs.
   - Across the 4 NOP padding positions, the algorithm triggers a **safe rejection** (`SAFE_REJECTION`) due to tied candidates or insufficient margin, preventing catastrophic failures.
5. **Generator Equivalence**: Numerical and structural equivalence of the original Perl script (`tools/generate_p0_fingerprint.pl`) against the EZE4 table was verified: **`ALGORITHM_EQUIVALENT`**.
6. **ZG3 vs EZE4 Comparison**: 106 of 125 rows (84.80%) and 978 of 1,000 QWORDs (97.80%) are exactly identical, confirming high binary stability across builds.

---

## 2. Audit and Rederivation of the EZE4 Table

The geometric and binary properties of `docs/rmg-eze4/eze4_p0_fingerprint_table.csv` were verified against the stock binary:
- **Number of rows**: Exactly 125.
- **Slide range**: `0x000000` to `0x1f0000` (probe offsets: `0x1f0000` to `0x000000`).
- **KASLR step**: `0x4000` (16 KB) constant.
- **Intra-page offsets**: `0x000, 0x200, 0x400, 0x600, 0x800, 0xa00, 0xc00, 0xe00`.
- **Endianness**: Little-endian (`<Q`, 64-bit unsigned).
- **Access limits**: Maximum offset read in image: $\text{0x1f0000} + \text{0xe00} + 8 = \text{0x1f0e08}$ (2,035,208 bytes), well below the size of `Image.stock` (39,356,928 bytes).

**Audit Verdict**: **`EXACT_MATCH`** (125/125 rows, 1000/1000 QWORDs validated).

---

## 3. Complete Similarity and Discrimination Matrix

Generated [**`docs/rmg-eze4/p0_similarity_matrix.csv`**](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/p0_similarity_matrix.csv) ($125 \times 125$) and [**`docs/rmg-eze4/p0_discrimination_report.csv`**](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/p0_discrimination_report.csv).

### 3.1 Distribution of Discrimination Verdicts
| Verdict | Criterion | Rows | Percentage |
| :--- | :--- | :---: | :---: |
| **PASS_STRONG** | $\text{margin} \ge 5$ | 121 | 96.80% |
| **PASS** | $3 \le \text{margin} < 5$ | 0 | 0.00% |
| **BORDERLINE** | $0 < \text{margin} < 3$ | 1 | 0.80% |
| **FAIL** | $\text{margin} \le 0$ (tie or beaten) | 3 | 2.40% |
| **Total** | | **125** | **100.00%** |

### 3.2 Analysis of Discrimination Exceptions
- **`0x1e4000` (FAIL)**: $\text{Image\_offset} = \text{0x00c000}$. 8 words `0xd503201fd503201f` (`nop; nop`). Ties with `0x1e8000` and `0x1ec000` with score 8 ($\text{margin} = 0$).
- **`0x1e8000` (FAIL)**: $\text{Image\_offset} = \text{0x008000}$. 8 words `0xd503201fd503201f`. Ties with `0x1e4000` and `0x1ec000` with score 8 ($\text{margin} = 0$).
- **`0x1ec000` (FAIL)**: $\text{Image\_offset} = \text{0x004000}$. 8 words `0xd503201fd503201f`. Ties with `0x1e4000` and `0x1e8000` with score 8 ($\text{margin} = 0$).
- **`0x1f0000` (BORDERLINE)**: $\text{Image\_offset} = \text{0x000000}$. Contains 1 ARM64 branch instruction (`0x1487bffffa405a4d`) and 7 `nop`s. Its score against padding slides is 7 ($\text{margin} = 8 - 7 = 1 < 3$).

---

## 4. Positional Collision and Entropy Analysis

Generated [**`docs/rmg-eze4/p0_word_entropy.csv`**](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/p0_word_entropy.csv).

| Index | Intra-page Offset | Unique Values (out of 125) | Max Collision Group | Zero Count | Repeated Values | Shannon Entropy (bits) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | `0x000` | 121 | 3 (`0x1e4000-1ec000`) | 0 (0.0%) | 7 (5.6%) | 6.896 |
| 1 | `0x200` | 121 | 4 (`0x1e4000-1f0000`) | 0 (0.0%) | 6 (4.8%) | 6.886 |
| 2 | `0x400` | 120 | 4 (`0x1e4000-1f0000`) | 1 (0.8%) | 8 (6.4%) | 6.870 |
| 3 | `0x600` | 118 | 4 (`0x1e4000-1f0000`) | 2 (1.6%) | 12 (9.6%) | 6.838 |
| 4 | `0x800` | 119 | 4 (`0x1e4000-1f0000`) | 0 (0.0%) | 10 (8.0%) | 6.854 |
| 5 | `0xa00` | 121 | 4 (`0x1e4000-1f0000`) | 0 (0.0%) | 6 (4.8%) | 6.886 |
| 6 | `0xc00` | 122 | 4 (`0x1e4000-1f0000`) | 0 (0.0%) | 4 (3.2%) | 6.902 |
| 7 | `0xe00` | 120 | 4 (`0x1e4000-1f0000`) | 0 (0.0%) | 8 (6.4%) | 6.870 |

*Methodological note*: Observed Shannon entropy ranges between **6.838 and 6.902 bits** per position (the theoretical maximum for 125 elements is $\log_2(125) \approx 6.966$ bits). This demonstrates nearly optimal positional dispersion throughout kernel `.text`.

---

## 5. Robustness to Corrupted Samples (Combinatorial Simulation)

Generated [**`docs/rmg-eze4/p0_error_tolerance.csv`**](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/p0_error_tolerance.csv) evaluating $125 \times (8 + 28 + 56) = 11,500$ corruption combinations:

| Error Level | Total Patterns | Accepted (Correct) | Safely Rejected | Misidentifications | Acceptance Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1 Erroneous QWORD** | 1,000 | 968 | 32 | **0** (0.00%) | **96.80%** |
| **2 Erroneous QWORDs** | 3,500 | 3,388 | 112 | **0** (0.00%) | **96.80%** |
| **3 Erroneous QWORDs** | 7,000 | 6,776 | 224 | **0** (0.00%) | **96.80%** |
| **Overall Total** | **11,500** | **11,132** | **368** | **0** (0.00%) | **96.80%** |

### Critical Safety Conclusions:
1. **Zero False Positives**: The oracle **never confuses one slide with another**, even with 37.5% destroyed data (3 out of 8 words).
2. **Safe Rejections**: The 368 rejected cases correspond exclusively to the 4 NOP padding positions (`0x1e4000`, `0x1e8000`, `0x1ec000`, `0x1f0000`), where the runtime cleanly aborts returning `-1` to retry the read without causing a kernel panic.

---

## 6. Cross Comparison: EZE4 vs ZG3 Reference Table

Generated [**`docs/rmg-eze4/zg3_eze4_p0_diff.csv`**](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/zg3_eze4_p0_diff.csv) comparing the 1,000 QWORDs:
- **8/8 identical rows**: **106 / 125 (84.80%)**
- **Rows with differences**: **19 / 125 (15.20%)**
- **Total identical QWORDs**: **978 / 1,000 (97.80%)**
- **Different QWORDs**: **22 / 1,000 (2.20%)**
- **Distribution of differences**: Pos 0: 2, Pos 1: 6, Pos 2: 4, Pos 3: 3, Pos 4: 1, Pos 5: 2, Pos 6: 3, Pos 7: 1.
- **Interpretation**: High binary stability between Samsung build versions (Kernel 5.15.189).

---

## 7. Validation of the Original Perl Generator

Audited and executed `tools/generate_p0_fingerprint.pl`:
1. Reading `SLIDE_KASLR_STEP`: Extracted from `target.h` (`0x4000`).
2. Row calculation: $\text{int}(\text{0x1f0000} / \text{0x4000}) + 1 = 125$.
3. Image offset: $\text{Image\_offset} = \text{0x1f0000} - \text{slide}$.
4. Slide order: Increasing from `0x000000` to `0x1f0000`.
5. Intra-page offsets: Exactly `0x000, 0x200, 0x400, 0x600, 0x800, 0xa00, 0xc00, 0xe00`.
6. Integer format: Little-endian 64-bit (`Q<`).
7. Numerical comparison with rederived EZE4 table: **100% identical (0 discrepancies)**.

**Generator Verdict**: **`ALGORITHM_EQUIVALENT`**.

---

## 8. Generated Artifact

The header file was generated as an offline analysis artifact:
- [**`docs/rmg-eze4/p0_fingerprint_EZE4.generated.h`**](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/p0_fingerprint_EZE4.generated.h) (529 lines, 125 entries).
- Contains the mandatory warning:
  ```c
  /*
   * OFFLINE-GENERATED ANALYSIS ARTIFACT.
   * NOT YET VALIDATED ON HARDWARE.
   */
  ```
- **NOT copied to `src/targets/`**.
- **Executable `target.h` NOT generated**.
- **NO code was compiled**.

---

## 9. Phase 3B Mandatory Metrics and Parameters

```
P0_TABLE_ROWS: 125
P0_TABLE_REDERIVATION: EXACT_MATCH
PERL_GENERATOR_EQUIVALENCE: ALGORITHM_EQUIVALENT
MIN_SELF_MARGIN: 0
MAX_OTHER_SCORE: 8
BORDERLINE_SLIDES: 0x1f0000
FAIL_SLIDES: 0x1e4000, 0x1e8000, 0x1ec000

ONE_QWORD_ERROR: 96.80% ACCEPTED (968/1000), 3.20% REJECTED (32/1000), 0.00% MISIDENTIFIED (0/1000)
TWO_QWORD_ERROR: 96.80% ACCEPTED (3388/3500), 3.20% REJECTED (112/3500), 0.00% MISIDENTIFIED (0/3500)
THREE_QWORD_ERROR: 96.80% ACCEPTED (6776/7000), 3.20% REJECTED (224/7000), 0.00% MISIDENTIFIED (0/7000)

SAFE_REJECTIONS: 368
MISIDENTIFICATIONS: 0

ZG3_IDENTICAL_ROWS: 106 / 125 (84.80%)
ZG3_IDENTICAL_QWORDS: 978 / 1000 (97.80%)

HEADER_GENERATED: YES (docs/rmg-eze4/p0_fingerprint_EZE4.generated.h - OFFLINE ANALYSIS ARTIFACT ONLY)
BLOCKERS: None (the 3 collisions correspond to NOP padding inherent to the Samsung ARM64 kernel image architecture, identical to ZG3, and neutralized by the margin filter P0_FINGERPRINT_MIN_MARGIN = 3).
```

---

## 10. Phase 3B Final Verdict

$$\mathbf{P0\_OFFLINE\_VALIDATED\_WITH\_WARNINGS}$$

### Verdict Justification:
- **Validated**: 121 of 125 candidates (96.8%) exhibit a margin $\ge 5$ with 100% tolerance against up to 3 simultaneous errors. In 11,500 simulations, 0 cases of erroneous identification were recorded.
- **With Warnings (`WITH_WARNINGS`)**: The 3 slides `0x1e4000`, `0x1e8000`, `0x1ec000` exhibit identical collision (8 NOPs) and `0x1f0000` exhibits score 7 (7 NOPs + 1 branch). If the bootloader were to randomly load the kernel at one of these 4 slides, the oracle will safely reject the read due to insufficient margin, forcing a clean retry.

---

## 11. Preventive Halt

In accordance with user instructions, the work session is concluded at this point:
- **No continuation to any subsequent phase**.
- **No executable `target.h` generated**.
- **Nothing is compiled**.
- **No interaction with the device**.
