# EZE4 KASLR selection analysis

## Scope and terminology

This report separates four facts that earlier project prose sometimes combined: a value may be theoretically allowed by a model, accepted by kernel code, selected by the bootloader, or observed on a boot. None implies the next. In particular, the P0 table's `slide` field is a payload/oracle label until its relation to the bootloader's physical load address is independently proved.

## Kernel configuration and boot inputs

The EZE4 configuration builds a relocatable arm64 kernel with virtual-base randomization support: `CONFIG_RELOCATABLE=y`, `CONFIG_RANDOMIZE_BASE=y`, `CONFIG_ARM64_4K_PAGES=y`, and EFI/stub support are present in `artifacts/eze4/x510xxuceze4-baseline-20260905/kernel.config:405,513-514,527-528`. This establishes compiled capability, not activation on this boot.

The retained stock vendor-boot DT has `nokaslr` in `/chosen/bootargs` (`artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts:9929`); the recovery DT repeats it (`artifacts/stock/dt/recovery/fdt-03-offset-0452b040.dts:9929`). No retained stock DT/DTBO supplies a literal `kaslr-seed`; the only source hits are the generic consumer and EFI/kexec producers. The overlays add no alternate KASLR selector. Therefore the retained boot inputs explicitly disable generic arm64 virtual KASLR.

## Generic arm64 virtual randomization

`sources/wifi-kernel/arch/arm64/kernel/head.S:461-465` calls `kaslr_early_init()` only when randomization is compiled and records its returned offset in `x23`. `sources/wifi-kernel/arch/arm64/kernel/kaslr.c:35-51` reads and wipes `/chosen/kaslr-seed`; lines 86-111 reject `nokaslr`, optionally mix architectural early RNG, and reject a zero seed. Lines 121-129 derive the virtual offset from the middle half of the minimum vmalloc range and clear the low 21 bits. The resulting generic virtual displacement is always 2 MiB aligned. With the retained `nokaslr` input, this path returns zero before applying seed entropy.

The exact enabled-path minimum and maximum depend on compiled `VA_BITS_MIN`: the source formula is `BIT(VA_BITS_MIN-3) + (seed & (((1 << (VA_BITS_MIN-2))-1) & ~(SZ_2M-1)))`. The enabled-path set is contiguous in 2 MiB steps over that formula's range. The stock boot path instead has virtual offset zero because of `nokaslr`. These are virtual mapping facts; they do not define the P0 table's 16 KiB labels.

## Physical placement and Image header

The arm64 boot protocol delegates physical placement to the loader before kernel entry. `sources/wifi-kernel/Documentation/arm64/booting.rst:90-132` requires the Image to start `text_offset` bytes from a 2 MiB-aligned base and defines Image-header flag bit 3 as allowing that aligned base anywhere in usable RAM. `sources/wifi-kernel/arch/arm64/include/asm/boot.h:18` sets `MIN_KIMG_ALIGN` to 2 MiB.

Direct decoding of `artifacts/stock/images/Image.stock` gives `text_offset=0`, `image_size=0x28c0000`, flags `0xa`, and magic `0x644d5241`. Flags `0xa` describe a little-endian 4 KiB-page kernel whose 2 MiB-aligned physical base may be anywhere in RAM. Under the documented protocol, `text_offset=0` makes the Image entry address itself 2 MiB aligned.

At entry, `sources/wifi-kernel/arch/arm64/kernel/head.S:98-100` computes `adrp(__PHYS_OFFSET) & (MIN_KIMG_ALIGN-1)` into `x23`, described by the source as the physical misalignment/KASLR offset. Static disassembly of the stock Image at file offsets `0x21f0008-0x21f000c` contains `adrp x23` followed by `and x23,x23,#0x1fffff`; the path at `0x21f0350-0x21f0360` tests that value, calls the stock `kaslr_early_init`, and ORs its return into `x23`. Thus source and stock binary agree on a 2 MiB mask.

No retained kernel, DT, DTBO, boot-image metadata, vendor-boot metadata, or init-boot metadata contains the algorithm that chooses the pre-entry physical address. The kernel receives the result implicitly by executing at that address; it does not choose it.

## Meaning of `SLIDE_KASLR_STEP`

The value `0x4000` is directly proved as an oracle/control-flow granularity: ZG3 `target.h:82` defines it, the 125 fingerprint rows cover `0..0x1f0000` at that step, and `slide_app.c:851-869` rejects committed labels outside that range or off that alignment. `oracle.c:210-299` selects a fingerprint row and `slide_app.c:737,781` adds the resulting label to `KIMAGE_TEXT_BASE`.

The same value is not supported as generic arm64 virtual KASLR granularity: that code clears 21 low bits. It is also not supported by the documented physical Image placement rule when `text_offset=0`: that rule requires a 2 MiB-aligned Image address. The historical ZG3 report of a successful `0x140000` label (commit `b7a854e`) reinforces that the P0 label cannot simply be identified with the generic virtual offset. It does not reveal the missing loader mapping. The defensible classification is **oracle-specific search/commit granularity with an unproved relationship to physical placement**.

Consequently, the minimum and maximum P0 labels (`0` and `0x1f0000`) and their contiguous 16 KiB enumeration describe the table, not a proved bootloader distribution. Kernel code neither creates nor explicitly excludes those labels as labels. No Samsung-specific kernel-side override of the generic arm64 selection formula was found.

## Four collision slides

| P0 label | 16 KiB aligned | In P0 table range | Generic 2 MiB virtual alignment | Protocol physical alignment with `text_offset=0` | Image source offset | Static reachability conclusion |
|---|---:|---:|---:|---:|---:|---|
| `0x1e4000` | Yes | Yes | No | No | `0x0c000` | `INSUFFICIENT_EVIDENCE` |
| `0x1e8000` | Yes | Yes | No | No | `0x08000` | `INSUFFICIENT_EVIDENCE` |
| `0x1ec000` | Yes | Yes | No | No | `0x04000` | `INSUFFICIENT_EVIDENCE` |
| `0x1f0000` | Yes | Yes | No | No | `0x00000` | `INSUFFICIENT_EVIDENCE` |

All four corresponding offsets are within the `0x28c0000` stock Image. Kernel-side generic KASLR does not expressly permit or exclude the payload labels because it has no such label domain. Proving them unreachable would require proving that the payload label is exactly a generic displacement, which the `0x140000` historical result contradicts. No retained gts9fewifi log records any of the four values. Table membership is generation coverage, not observation.

## BOOTLOADER_KNOWLEDGE_BOUNDARY

Static kernel evidence ends at the boot protocol and the entry-time observation of the already chosen load address. It proves the required 2 MiB base alignment, the stock Image header, the generic virtual KASLR formula, and `nokaslr`; it does not prove Samsung's loader address-selection algorithm or the transformation, if any, between that address and the P0 label.

Closing the boundary requires at least one authoritative unavailable source: sboot/loader source, a relevant loader disassembly, an authoritative Samsung placement specification, boot logs that expose both placement and address domains, or runtime measurements that correlate the P0 label with physical and virtual addresses. The repository contains boot images and metadata but not sboot or bootloader code. No claim about the bootloader's range, exclusions, entropy source, or distribution follows from the current artifacts.
