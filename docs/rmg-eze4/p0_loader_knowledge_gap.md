# P0 and loader knowledge-gap map

| QUESTION | CURRENT_EVIDENCE | WHAT_IS_KNOWN | WHAT_IS_UNKNOWN | MINIMUM_ADDITIONAL_EVIDENCE | CAN_BE_OBTAINED_WITHOUT_BOOTLOADER_REVERSE_ENGINEERING | STATUS |
|---|---|---|---|---|---|---|
| What are the 125 labels? | EZE4 generated header; `oracle.c`; `slide_app.c` | They enumerate `0..0x1f0000` at `0x4000` and map a probed Image page to a committed address displacement. | Their authoritative loader/physical-address meaning. | One correlated observation exposing label plus physical and virtual addresses, or authoritative loader documentation. | Possibly, if legitimate boot logs expose the correlation. | PARTIAL |
| What does the `0x4000` step mean? | Target macro and commit checks; generic kernel source | It is the oracle table/search/commit granularity. | Whether it derives from undocumented loader placement or another address transform. | Loader algorithm/specification or correlated address evidence. | Possibly. | PARTIAL |
| How is the Image physically placed? | Image header; arm64 boot protocol; entry code | Loader acts before kernel entry; protocol base is 2 MiB aligned and `text_offset=0`. | Samsung selection range, entropy, exclusions, distribution, and compliance details. | sboot/loader source or disassembly, authoritative documentation, or explicit boot log. | Only if existing logs/documentation disclose it. | OPEN |
| Are four collision labels reachable? | Four rows exist and structurally reject; no observation | If reached, current P0 safely rejects and has no same-boot recovery. | Whether loader/P0 mapping can produce them. | Direct observations across boots or authoritative selector proof. | Possibly, but current benign sources may expose no label. | OPEN |
| What is ZG3 `0x140000`? | Commit `b7a854e`; PHASE3A secondary restatement | It is one recorded successful runtime label in payload terminology. | Whether it is physical placement, oracle label, derived displacement, or another logged value. | Raw log plus logging call/version and correlated addresses. | Yes if the original raw log is recovered. | PARTIAL |

## Safe evidence-source inventory

| Source | Classification | Contribution and limit |
|---|---|---|
| Stock Image header | AVAILABLE_NOW | Proves `text_offset`, size, flags, and protocol alignment; no selector distribution. |
| Kernel command line in stock DT | AVAILABLE_NOW | Proves retained `nokaslr`; not physical placement. |
| DT `/chosen` and DTBOs | AVAILABLE_NOW | Shows bootargs and absence of retained seed/selector property. |
| boot/vendor_boot/init_boot metadata and bootconfig size | AVAILABLE_NOW | Establishes packaging; contains no identified placement algorithm. |
| Historical ZG3 commit/report | AVAILABLE_NOW | One `0x140000` label without raw address correlation. |
| `/proc/cmdline`, `/proc/bootconfig`, readable `/sys` after stock boot | AVAILABLE_ON_DEVICE_WITHOUT_ROOT | Can confirm effective inputs/exposure; may not reveal placement. |
| Existing stock boot logs / logcat buffers | AVAILABLE_ON_DEVICE_WITHOUT_ROOT | Useful only if they legitimately expose load or KASLR addresses. |
| Restricted dmesg | AVAILABLE_ON_DEVICE_WITHOUT_ROOT | A read attempt may be denied; denial supplies no placement evidence. |
| Original raw ZG3 success log | REQUIRES_NEW_ARTIFACT | Could define what `0x140000` represented if logging context is intact. |
| Official Samsung loader documentation/source | REQUIRES_NEW_ARTIFACT | Could close selector semantics without binary analysis. |
| sboot/bootloader binary and relevant disassembly | REQUIRES_BOOTLOADER_BINARY | Could close algorithm details; no bypass or modification is contemplated. |
| Statistical placement distribution | NOT_AVAILABLE | Cannot be inferred from table rows or one historical label. |
