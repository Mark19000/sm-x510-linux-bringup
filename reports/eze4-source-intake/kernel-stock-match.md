# Kernel Version and Match Audit: OSRC EZE4 ↔ Stock

Audit date: 2026-09-05  
Model/target: `SM-X510`, physical firmware `X510XXUCEZE4` (Android 16/U12)  
Scope: static inspection of clean OSRC and preserved stock `boot.img`. Source was neither compiled nor modified.

## Verdict

- **Base version of OSRC: Linux `5.15.189`**, with **very high** confidence.
- **The historical discrepancy U11 `5.15.180` vs stock EZE4 `5.15.189` is eliminated at base version level**.
- The tree is **strongly aligned with the release that produced the stock EZE4 kernel**: same version, virtually identical defconfig, exact same compiler, and coherent dates. Confidence: **high**.
- It is not yet possible to certify that the tarball is a **byte-exact/reproducible snapshot** of the production build. SCM commit/history and external values that generated `-android13-3-33478785` are missing; nor has a baseline build been executed. Confidence in byte-exact identity: **indeterminate**.

In operational terms: this is no longer a U11 source used as an approximation. It is the published base source for EZE4, containing the same `5.15.189` base and nearly identical effective configuration observed in stock. Remaining caution pertains to the exact identity of the snapshot and build environment, not the base version.

## 1. Exact Version Declared by Source

Direct evidence in `audit/eze4-source-intake/extracted/kernel/Makefile:2-6`:

```text
VERSION = 5
PATCHLEVEL = 15
SUBLEVEL = 189
EXTRAVERSION =
```

Result without external suffixes: `5.15.189`. There is no `EXTRAVERSION`, `localversion*` file, or `.scmversion` inside the tarball, and the package contains no internal `.git` metadata.

The specific defconfig confirms the same base in `audit/eze4-source-intake/extracted/kernel/arch/arm64/configs/s5e8835-gts9fewifixx_defconfig:3`:

```text
# Linux/arm64 5.15.189 Kernel Configuration
```

SHA-256 hashes of audited identity components:

| File | SHA-256 |
|---|---|
| `kernel/Makefile` | `ed1690e295cb4f9e76a5b850dc68a79bc04982bcb44e65225eaccbd0eff0e838` |
| defconfig `s5e8835-gts9fewifixx_defconfig` | `64b52796edb48acc0a050ceb8088cf5545b97d150208744da7bb2a49ba53a287` |
| `kernel/build_kernel.sh` | `edd394e84b60c202ffd73fad09e21a602baa623cd2df3761aef916e42d9a7d5e` |

## 2. Observable Identity of Stock EZE4 Kernel

`artifacts/stock/firmware-metadata.txt` establishes binary provenance:

```text
outer_zip=SAMFW.COM_SM-X510_EUX_X510XXUCEZE4_fac.zip
ap_entry=AP_X510XXUCEZE4_X510XXUCEZE4_MQB109790656_REV00_user_low_ship_MULTI_CERT_meta_OS16.tar.md5
target_model=SM-X510
target_ap=X510XXUCEZE4
target_csc=EUX
target_csc_version=X510OXMCEZE4
```

The payload was re-extracted from `artifacts/stock/images/boot.img` using boot v4 header fields: offset `4096`, size `39356928`. Its complete string is:

```text
Linux version 5.15.189-android13-3-33478785 (dpi@VPHORC631) (Android (8490178, based on r450784d) clang version 14.0.6 (https://android.googlesource.com/toolchain/llvm-project 4c603efb0cca074e9238af8b4106c30add4418f6), LLD 14.0.6) #1 SMP PREEMPT Fri May 15 20:06:17 KST 2026
```

It also contains the vermagic:

```text
5.15.189-android13-3-33478785 SMP preempt mod_unload modversions aarch64
```

Therefore:

| Dimension | OSRC | Stock EZE4 | Result |
|---|---|---|---|
| Linux base | `5.15.189` | `5.15.189` | matches |
| release suffix | not pinned in tarball | `-android13-3-33478785` | requires external variables |
| compiler | Clang `14.0.6`, build `8490178`, `r450784d`, LLVM commit `4c603e...` | exactly same string | matches |
| linker | LLD `14.0.6` configuration | LLD `14.0.6` | matches |
| build host/user | not included | `dpi@VPHORC631` | external/missing |
| build timestamp | not pinned by script | `Fri May 15 20:06:17 KST 2026` | external/missing |
| build ordinal | not included | `#1` | external/missing |

Current payload extraction yields SHA-256 `ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9`. Historical report `reports/2026-08-23-u11-eze4-binary-abi-audit.md` records `0ab39c...` for payload even though `boot.img` retains the same hash `c96c0e...`. This must be corrected or explained during cross-review; it does not affect directly read version strings, but prevents reusing that payload hash without review.

## 3. OSRC Defconfig vs Stock Embedded Configuration

IKCONFIG configuration was extracted directly from stock payload using `kernel/scripts/extract-ikconfig` and `LC_ALL=C`. Result contains 8,582 lines; official defconfig contains 8,581. Complete `diff -u` contains **a single hunk**:

```diff
-CONFIG_UNUSED_KSYMS_WHITELIST="gki/abi_symbollist.raw"
+CONFIG_UNUSED_KSYMS_WHITELIST="/home/dpi/qb5_8814/workspace/P4_1716/android/kernel/s5e8835/gki/abi_symbollist.raw"
+CONFIG_KMI_SYMBOL_LISTS="android/abi_gki_aarch64_virtual_device ... abi_greylist"
```

Interpretation:

- The stock absolute path is a materialization of the production workspace; OSRC sanitizes it to a valid relative path.
- `CONFIG_KMI_SYMBOL_LISTS` records in stock a variable generated by the build framework. Its absence from the distributed defconfig does not indicate a functional source code difference by itself.
- Outside that block, the stock embedded configuration matches line-by-line with OSRC defconfig, including all driver and platform selections.

Identical critical options in both:

```text
CONFIG_LOCALVERSION=""
CONFIG_LOCALVERSION_AUTO=y
CONFIG_BUILD_SALT=""
CONFIG_MODULES=y
CONFIG_MODVERSIONS=y
CONFIG_MODULE_SIG=y
CONFIG_MODULE_SIG_PROTECT=y
CONFIG_MODULE_SIG_ALL=y
CONFIG_MODULE_SIG_SHA1=y
CONFIG_TRIM_UNUSED_KSYMS=y
CONFIG_LTO_CLANG=y
CONFIG_LTO_CLANG_THIN=y
CONFIG_CFI_CLANG=y
CONFIG_CFI_CLANG_SHADOW=y
CONFIG_ARM64_MODULE_PLTS=y
CONFIG_RELOCATABLE=y
```

This near-total match is far stronger evidence than merely sharing `VERSION/PATCHLEVEL/SUBLEVEL`.

## 4. Defconfig and Official Recipe

The specific recipe distributed is `audit/eze4-source-intake/extracted/kernel/build_kernel.sh` and executes:

```text
PLATFORM_VERSION=13
ANDROID_MAJOR_VERSION=t
LLVM=1
ARCH=arm64
TARGET_SOC=s5e8835
make s5e8835-gts9fewifixx_defconfig
make
```

It also pins toolchain `clang-r450784d`, which corresponds exactly with `CONFIG_CC_VERSION_TEXT` and with the stock kernel string. `README_Kernel.txt` repeats the same defconfig and toolchain.

The tree also carries generic GKI configurations. They should not be confused with the device-specific simple recipe:

- `build.config.constants`: `BRANCH=android13-5.15`.
- `build.config.common`: `KMI_GENERATION=8`.
- `build.config.mcd`: `KMI_GENERATION=3`.
- `build.config.erd8835_t`: uses `erd8835_t_gki_defconfig`, not final defconfig `gts9fewifixx` invoked by OSRC README/script.

Those files do not suffice to automatically derive the stock suffix. Specifically, using `build.config.common` literally would suggest KMI generation `8`, whereas stock exposes `android13-3`.

## 5. Localversion, Samsung Release IDs, and Traceability

`scripts/setlocalversion` can construct `-android13-<KMI_GENERATION>` when the framework passes `BRANCH` and `KMI_GENERATION`. It can append `-ab<BUILD_NUMBER>`, but stock ends in `-33478785`, not `-ab33478785`.

Conclusions:

1. `-android13-3` is consistent with the present Samsung/Android mechanism and an external KMI generation equal to `3`.
2. `-33478785` had to arrive via `LOCALVERSION` or another production environment variable; that value does not appear literally in distributed source.
3. Number `33478785`, host `VPHORC631`, user `dpi`, date, and revision `#1` are stock build identifiers, not recoverable identifiers from OSRC snapshot.
4. `version.diff` is not a kernel tag: only alters `cpif_driver_version` from `CPIF-20230713R1` to `CPIF-20240119R1`.
5. Without `.git`, `.scmversion`, repo manifest, or commit hashes, commit identity cannot be proven nor can omitted historical changes be enumerated.

Reproducibility warning: because `CONFIG_LOCALVERSION_AUTO=y`, compiling the extracted tree **inside another parent Git repository** can cause `scripts/setlocalversion` to discover that repository and append a spurious suffix. Future baseline builds must execute in an independent extraction or set release variables in a controlled manner; the stock suffix must not be inferred from the container checkout.

## 6. Relationship with Second Package

The incremental package contains `X510XXSDEZF1_kernel.txt`, which explicitly instructs:

1. download/unpack source `X510XXUCEZE4`;
2. update it with `X510XXSDEZF1`;
3. build with same defconfig and `clang-r450784d`.

However, `X510XXSDEZF1_kernel.tar.gz` contains only the empty directory `Kernel/` (one entry, 114 bytes compressed). Therefore, it modifies no files in the audited kernel. The identity studied here remains baseline `X510XXUCEZE4`; the second package expresses an incremental relationship toward EZF1, but contributes no effective code delta.

## 7. Correspondence Evaluation

### What is Proven

- Exact base is `5.15.189` in both OSRC and stock.
- OSRC incorporates final specific defconfig `s5e8835-gts9fewifixx_defconfig`.
- That defconfig matches stock `.config` except for a single block explainable by KMI workspace sanitization / materialization.
- Expected compiler and linker match exactly with those recorded in stock.
- Archived source timestamps are May 15, 2026, the same day as the stock build; this is auxiliary evidence, not cryptographic identity.
- Incremental package EZF1 recognizes `X510XXUCEZE4` as its base source.

### What is Not Yet Proven

- Exact SCM commit or tag.
- That all files used internally by Samsung are present in the tarball.
- Exact values of `BRANCH`, `KMI_GENERATION`, `LOCALVERSION`, user/host, and timestamp used in production.
- Equality of `Image`, `Module.symvers` symbols/CRCs, BTF, or modules after recompiling.
- Reproduction of build ID `33478785` and complete vermagic without first reconstructing release environment.

### Confidence Levels

| Assertion | Confidence | Reason |
|---|---|---|
| OSRC is Linux `5.15.189` | **very high** | Direct `Makefile` and defconfig header |
| Numerical mismatch `.180`/`.189` eliminated | **very high** | source and stock both declare `.189` |
| tree corresponds to EZE4 release/build family | **high** | version + near-exact defconfig + exact toolchain + date + official provenance |
| logical snapshot is same one that produced stock | **medium-high** | convergent evidence, but no commit/manifest or compared baseline |
| byte-identical `Image` can be rebuilt today | **indeterminate** | variables/build metadata missing and not yet compiled |
| exact ABI with stock modules will hold | **indeterminate** | aligned version/config eliminates major risk, but CRCs/KMI and artifact comparison still needed |

## 8. Direct Answers

1. **Does version match?** Yes. OSRC and stock share Linux `5.15.189`. Complete stock suffix is `5.15.189-android13-3-33478785` and depends on non-preserved external parameters.
2. **Does source appear to be from same release?** Yes, with high confidence. Near-total match of embedded defconfig, exact toolchain, and source date support this.
3. **Are there indications of a different snapshot?** No positive code divergence was demonstrated in this audit. Lack of SCM traceability and private build variables means exact identity cannot be proven either.
4. **What changes relative to U11 risk?** The obvious version blocker of `5.15.180` vs `5.15.189` disappears. This is not yet equivalent to proving stock ABI: `CONFIG_MODVERSIONS`, CFI, KMI trimming, and suffix/vermagic make a clean baseline and CRC/symbol/module comparison essential before claiming compatibility.

## 9. Minimal Pending Validation

The next phase should perform a single clean extraction outside any parent Git repo, capture resulting `kernelrelease` with explicit release variables, build with `clang-r450784d`, and compare against stock: UTS string, `.config`, `Module.symvers`, exported CRCs, BTF, vermagic/modules, and finally `Image`. Until then, the correct phrasing is **"EZE4 source strongly aligned with stock"**, not **"proven exact rebuild"**.
