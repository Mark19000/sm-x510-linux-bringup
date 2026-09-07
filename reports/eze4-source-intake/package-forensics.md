# EZE4 OSRC Package Forensics

## Scope and Conclusion

This audit was performed exclusively on artifacts in `audit/eze4-source-intake/` and the original wrapper preserved in `/Users/markpi/Downloads/SM-X510(1).zip`. No modifications were made to `sources/`, the pipeline, or patches, and no second extraction was performed.

**Primary conclusion (high confidence):** the two ZIPs are not two alternative complete snapshots nor two complementary halves. The first ZIP is the effective base release for `X510XXUCEZE4`: it contains the full kernel and a selection of platform sources for Android 16. The second ZIP is, according to its own instructions, an incremental package applied on top of the base for `X510XXSDEZF1`; however, its payload is a valid 114-byte `tar.gz` containing a single empty directory `Kernel/`. In practice it contributes **zero files, zero changes, and zero file duplicates**. It does not replace the base ZIP.

The external name of the second ZIP also mentions `X510XXSEEZG3`, but neither its README nor internal tar names EZG3. The most probable explanation is that Samsung bundled on the portal two releases that reuse the same publication/source delta. That is a **medium confidence inference**, not something proven by content. What is provable is solely:

- external name: `..._X510XXSDEZF1_X510XXSEEZG3.zip`;
- internal README: base `X510XXUCEZE4` and update `X510XXSDEZF1`;
- internal tar name: `X510XXSDEZF1_kernel.tar.gz`;
- payload: zero source files;
- zero mention of `EZG3` inside the package or in `notice.html`.

## Chain of Custody and Hashes

Reference command:

```sh
shasum -a 256 /Users/markpi/Downloads/SM-X510\(1\).zip \
  audit/eze4-source-intake/wrapper/* \
  audit/eze4-source-intake/packages/base/* \
  audit/eze4-source-intake/packages/update/*
```

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Original wrapper `SM-X510(1).zip` | 286,506,851 | `c0da997484b4c6cd3fe6f065202087e12861a6112622bd4e4fc44c5395d58424` |
| Base ZIP `SM-X510_EUR_16_Opensource.zip` | 286,431,317 | `72378f3be5c38344d52d231f85ee75c4b775feaac3ecbc794a1b59d791b1aad0` |
| Update ZIP `SM-X510_EUR_16_Opensource_X510XXSDEZF1_X510XXSEEZG3.zip` | 1,116 | `ddc73051ffb0f4c710d313380d654190d0a6a8811ab02e987d4ecdad6643e02b` |
| `notice.html` | 8,536,905 | `7870e1a50a24d239de1b80eba30836390344bcdd071298ddddcfe3bf3fa2daa7` |

Hashes of extracted internal payloads:

| Payload | Bytes | SHA-256 |
|---|---:|---|
| `base/Kernel.tar.gz` | 254,856,521 | `2f3e18626011311a1450138e19b2091f7c177a5f8be6400a091f216800969b0f` |
| `base/Platform.tar.gz` | 38,854,884 | `29dd271f53186ea1a78abb304c1a7b0fccfc571e5ab50d56c0f249926acd17f3` |
| `base/README_Kernel.txt` | 2,499 | `1b9fc0a5dd1362d4f27f9e7ed50c209a1643656eefc279f1738c4c2f3052e19c` |
| `base/README_Platform.txt` | 2,240 | `3735f9e3cb6f8d85ca87c1e2f7ea3cef7fe744edaef047830b71eca9e416969e` |
| `update/X510XXSDEZF1_kernel.tar.gz` | 114 | `ade4aab83be90608fcd5aaa98c6835939461be135e5efa18dcdc66fe577eee87` |
| `update/X510XXSDEZF1_kernel.txt` | 2,615 | `344276b34de54272a98b95fe6c9ab57c8de7a388a383e2fcfd9a50cd1d797a26` |

`unzip -t` validated wrapper and both internal ZIPs with zero errors. `gzip -t` validated all three compressed tarballs. Listings of all three tarballs contain no absolute paths, `..` components, or duplicate names. High confidence in structural integrity; hashes do not imply cryptographic authenticity because no published Samsung signature or checksum was provided for cross-checking.

## Hierarchical Inventory

### User Wrapper

`SM-X510(1).zip` contains exactly two entries:

```text
SM-X510(1).zip
├── SM-X510_EUR_16_Opensource.zip                         286,431,317 B
└── SM-X510_EUR_16_Opensource_X510XXSDEZF1_X510XXSEEZG3.zip  1,116 B
```

The wrapper does not contain `notice.html`; NOTICE was provided as a separate artifact and is copied in `audit/eze4-source-intake/wrapper/notice.html`.

### ZIP 1: Base Delivery

```text
SM-X510_EUR_16_Opensource.zip
├── Kernel.tar.gz          254,856,521 B (tar: 1,643,991,040 B)
├── Platform.tar.gz         38,854,884 B (tar:   190,033,920 B)
├── README_Kernel.txt            2,499 B
└── README_Platform.txt          2,240 B
```

`Kernel.tar.gz` contains 86,456 entries: 80,863 regular files, 5,554 directories, and 39 symlinks. It contains zero precompiled `.ko` modules or precompiled DTB/DTBOs: it contains their sources and build rules.

Primary functional hierarchy of kernel (entry count from tar by branch):

```text
kernel source (`./`)
├── drivers/          39,432
├── arch/             16,190
├── Documentation/     8,612
├── include/           6,433
├── tools/             5,692
├── sound/             2,809
├── fs/                2,257
├── net/               1,955
├── kernel/              563
├── security/            545
├── scripts/             496
├── lib/                 482
├── mm/                  175
├── crypto/              204
├── block/               112
├── LICENSES/             25
├── build.config.* and module build scripts/configs
└── Makefile, Kconfig, COPYING, version.diff, README...
```

Confirmed relevant specific contents:

- defconfig: `arch/arm64/configs/s5e8835-gts9fewifixx_defconfig`;
- product DTS: `arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r00.dts`, `r01.dts`, and `r04.dts`;
- base SoC: `arch/arm64/boot/dts/exynos/s5e8835.dts`;
- specific module lists: `vendor_module_list_s5e8835_gts9fewifi.cfg` and variants;
- Samsung/Exynos subsystems in `drivers/samsung`, `drivers/clk/samsung`, `drivers/devfreq/exynos`, `drivers/input/sec_input`, `drivers/scsi/ufs`, `drivers/gpu`, etc.;
- 456 config/defconfig paths, 3,221 DTS/DTSI sources, 2,853 Makefiles, 33,900 `.c`, and 26,263 `.h` across the full tarball.

`Platform.tar.gz` contains 15,252 entries: 13,579 regular files and 1,673 directories, with zero symlinks. Top branches are:

```text
platform source
├── external/    9,432 entries
├── libcore/     4,387
├── vendor/      1,324
│   └── samsung/
│       ├── external/ims_voice_engine
│       ├── external/ksmbd-tools
│       ├── external/ztd/bpf_progs
│       └── frameworks/{base/imsservice,camerasolution}
├── art/            88
├── system/         20
└── build_64bit.sh    1
```

Notable AOSP/external branches include `e2fsprogs`, `eigen`, `iptables`, `libnl`, `iproute2`, `aac`, `hyphenation-patterns`, `oj-libjdwp`, `libexif`, `erofs-utils`, `f2fs-tools`, `gptfdisk`, and `dnsmasq`. Counted 105 `Android.bp`, 21 Makefiles, 49 shell scripts, 1,640 `.c`, 1,051 `.cc/.cpp/.cxx`, 2,533 `.h`, and 4,122 `.java`. No DTS/DTB, `.ko` modules, or defconfigs exist in this tar; all relevant Device Tree source is in the kernel tar.

Platform README explicitly declares `Android 16.0`. Kernel README prescribes `TARGET_SOC=s5e8835`, `ARCH=arm64`, `s5e8835-gts9fewifixx_defconfig`, and Clang `clang-r450784d`. While it shows `PLATFORM_VERSION=13`, that is a kernel build instruction and does not contradict the Android 16 declaration of the platform package; its accuracy/obsolescence is addressed in the build audit.

### ZIP 2: Nominal Update EZF1/EZG3

```text
SM-X510_EUR_16_Opensource_X510XXSDEZF1_X510XXSEEZG3.zip
├── X510XXSDEZF1_kernel.tar.gz   114 B
│   └── Kernel/                    empty directory
└── X510XXSDEZF1_kernel.txt     2,615 B
```

The uncompressed tar occupies 10,240 bytes due to tar blocking/framing, not useful data. `tar -tvzf` shows a single directory entry and `tar -tzf ... | wc -l` returns `1`. There are no regular files, patches, diffs, configs, source, revision metadata, or platform components.

The README literally states, in instructions form, to download and unpack `X510XXUCEZE4` kernel first and then unpack/update with `X510XXSDEZF1` kernel. Therefore:

- **formal relationship:** base + subsequent overlay;
- **material relationship:** empty overlay, source output identical to base;
- **duplicates between packages:** zero duplicated files, because update contains no files;
- **subsequent revision?:** yes in label/instruction (`EZF1`), but no revision in content;
- **complementary?:** only in formal sense of Samsung flow; not in content;
- **kernel vs other components?:** base ZIP provides kernel and platform; update ZIP claims to be kernel only, but provides no source;
- **proven versions:** base `X510XXUCEZE4`, nominal update `X510XXSDEZF1`, additional external alias `X510XXSEEZG3`.

## Precaution: Extraction on Case-Insensitive Filesystem

Authoritative inventory must be the tar, not `extracted/platform` tree. `Platform.tar.gz` contains 38 pairs of distinct Linux paths differing solely in case, all under iptables (e.g. `libxt_DSCP.c` vs `libxt_dscp.c`, and `xt_MARK.h` vs `xt_mark.h`). On the case-insensitive APFS filesystem used by the workspace, one of each pair overwrote the other.

Evidence:

```sh
tar -tzf Platform.tar.gz | perl ...   # groups=38 excess=38
comm -23 <(file list from tar) <(file list from extracted tree)
```

`comm` confirms exactly 38 tar entries absent from the extracted tree. The five `.DS_Store` files observed in the tree do not belong to the tar and explain the apparent count difference (`find` is not a faithful archive inventory). This does not affect kernel analysis, whose tar experienced no such loss, but future **Platform** baselines must be extracted onto a case-sensitive volume/filesystem. High confidence.

## Analysis of `notice.html`

`notice.html` is an ASCII HTML document of 8,536,905 bytes functioning as a compliance inventory for firmware/binaries, not as a manifest for the two source ZIPs:

- 1,262 entries in "Libraries" table of contents (958 distinct names);
- 8,994 associations in "Files";
- 498 license/attribution text groups (`id0` to `id497`);
- license texts such as Apache-2.0, BSD, GPL/LGPL, MIT, ISC, zlib, and component-specific licenses;
- a final written offer pointing to `opensource.samsung.com` to obtain source under publication obligations for three years.

It does provide useful clues of product affiliation: contains paths/names `gts9fewifi`, `s5e8835`, display/touch firmware, product overlays, `fstab.s5e8835`, `init.s5e8835.rc`, `init.insmod.s5e8835.cfg`, images `boot.img`, `vendor_boot.img`, `dtbo.img`, `vendor_dlkm.img`, and a `/kernel` entry. It thus corroborates that the NOTICE describes a build in the SM-X510 / GTS9 FE Wi-Fi ecosystem and its open source composition.

It does not contain `X510XXUCEZE4`, `X510XXSDEZF1`, `X510XXSEEZG3`, or their abbreviated suffixes. Nor does it identify a kernel commit/tag. Consequently:

- it cannot date or distinguish EZE4/EZF1/EZG3;
- it does not prove source is bit-exact with a concrete firmware;
- it does not explain why EZG3 appears only in the external name;
- it is not a third source package nor does it provide an additional overlay.

Confidence in these limitations is high, based on direct case-insensitive search across the entire document.

## Matrix of Assertions and Confidence

| Finding | Direct Evidence | Confidence |
|---|---|---|
| ZIP 1 is sole substantive source payload | Four entries; complete kernel/platform tars; READMEs | High |
| ZIP 2 must be applied after EZE4 | `X510XXSDEZF1_kernel.txt`, steps 1–2 | High |
| ZIP 2 modifies zero files | Valid tar with only `Kernel/`, zero regular files | High |
| Resulting source from base + update is materially base EZE4 | Overlay without files | High |
| EZG3 reuses publication/delta of EZF1 | External name bundles both; zero internal EZG3 payload/mention | Medium (inference) |
| Base ZIP is Android 16 | `README_Platform.txt`: "version info - Android 16.0" | High |
| Kernel is for S5E8835 / GTS9 FE Wi-Fi | README, defconfig, DTS, and specific module lists | High |
| NOTICE belongs to inspected product family | Multiple `gts9fewifi`/`s5e8835` names and firmware paths | High |
| NOTICE identifies exact EZE4 release | Contains no release identifiers | Unproven |
| Extracted Platform tree is complete | 38 case-only collision losses | False; high confidence |

## Essential Reproduction Commands

```sh
unzip -t /Users/markpi/Downloads/SM-X510\(1\).zip
unzip -t audit/eze4-source-intake/wrapper/SM-X510_EUR_16_Opensource.zip
unzip -t audit/eze4-source-intake/wrapper/SM-X510_EUR_16_Opensource_X510XXSDEZF1_X510XXSEEZG3.zip
gzip -t audit/eze4-source-intake/packages/{base/Kernel.tar.gz,base/Platform.tar.gz,update/X510XXSDEZF1_kernel.tar.gz}
tar -tvzf audit/eze4-source-intake/packages/update/X510XXSDEZF1_kernel.tar.gz
tar -tzf audit/eze4-source-intake/packages/base/Kernel.tar.gz | wc -l
tar -tzf audit/eze4-source-intake/packages/base/Platform.tar.gz | wc -l
rg -n -i 'X510XX|EZE4|EZF1|EZG3|gts9fe|s5e8835' audit/eze4-source-intake/wrapper/notice.html
```

## Implication for SOL Consolidation

For kernel, ABI, patches, and Device Tree audits, the substantive official baseline is exclusively `Kernel.tar.gz` from the base EZE4 ZIP; the second ZIP introduces zero differences to merge. For platform, audits must use the tar inventory or postpone exhaustive comparisons until a case-sensitive extraction is available. Exact equivalence with stock kernel and Linux version are not concluded here: they belong to kernel/ABI audits and require evidence beyond packaging.
