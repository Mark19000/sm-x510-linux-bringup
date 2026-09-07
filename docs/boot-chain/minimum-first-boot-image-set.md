# Minimum first-boot image set — offline closure

Date: 2026-09-05. Verdict: **CANNOT_YET_BE_DETERMINED**.

## Independent reconstruction

| Image | What bootloader verifies | What runtime consumes | Why it can remain stock | Why it may need change |
|---|---|---|---|---|
| boot | Root HASH; stock also has self-footer | Linux kernel; boot v4 ramdisk is empty | Never, if the goal is a custom kernel | Required for a different `Image`; header/layout must remain valid |
| init_boot | Root HASH + self-footer | Generic ramdisk and `/init` path | A kernel-handoff marker need not require userspace | Required for a controlled Linux initramfs unless another proven source supplies it |
| vendor_boot | Root HASH + self-footer | Vendor ramdisk fragments, modules, DTB, bootconfig | DTB is EZE4 stock; 281 modules and CRC ABI match the canonical EZE4 kernel | May need change only if stock ramdisk/init sequence interferes or a DTB/bootconfig change becomes justified |
| dtbo | Root CHAIN → embedded vbmeta HASH | Bootloader-selected overlay | All three overlays are byte-identical to the validated source output | No current technical need; changing adds risk |
| vbmeta | OEM-signed root of graph | Bootloader AVB policy and Android verified-boot state | Only if every protected image remains stock | A changed boot no longer matches its root HASH; exact acceptable alternative is UNKNOWN |

## Candidate models after a future owner unlock

| Candidate | Bytes/partitions changed | AVB consequence | Diagnostic/recovery assessment |
|---|---|---|---|
| **A. boot only** | Kernel/header/footer in `boot` | Root HASH `boot` and embedded self-HASH cease to match. AOSP UNLOCKED normally permits verification errors, but Samsung EZE4 behavior is UNKNOWN. | Fewest writes and easiest partition rollback. Best first candidate *if* unlocked Samsung accepts it and the kernel contains an intrinsic readable marker. |
| **B. boot + vbmeta** | A plus root of trust | Root can be made internally descriptive only without the OEM signing key; flags 2/3 acceptance is UNKNOWN and affects the whole graph. | More dangerous and less isolated than A. Do not use merely because old plans assumed it. |
| **C. boot + vendor_boot** | Kernel plus vendor ramdisk/DTB/bootconfig | Breaks two root HASH descriptors and both self-footers while stock root still disagrees. | No present need: EZE4 DT and all 281 module ABIs match. Adds a high-risk variable without supplying the generic `/init`. |
| **D. boot + vendor_boot + vbmeta** | Three partitions including root | Same Samsung-policy unknown plus vendor_boot structural risk. | Inferior to A/B absent a measured vendor_boot incompatibility. |
| **E. another set** | Most plausible later set is boot + init_boot, with or without vbmeta depending on unlocked policy | Breaks boot/init_boot root HASH and self-footers | Needed only when the milestone becomes controlled Linux `/init`; not required merely to prove custom kernel execution if stock Android can boot. |

Under LOCKED, none is viable with available OEM keys. After UNLOCKED, A is mechanically minimal and B is not automatically required: AOSP device-state behavior permits verification errors, while Samsung behavior remains unmeasured. Therefore neither `boot-only` nor `boot+vbmeta` is proven.

The “minimum” also depends on the milestone. Kernel execution can potentially use stock init_boot/vendor_boot/dtbo; controlled Linux userspace likely needs init_boot. These must not be collapsed into one experiment.

No AVB flag is assumed sufficient. `flags=1` is not disable-verification, and Samsung handling of `flags=2/3` is unknown.
