# Minimal Modification Set — SM-X510 U12/EZE4

> **SUPERSEDED — DO NOT USE AS AN OPERATIONAL PLAN.** Preserved as a historical U11 audit. Contains invalidated conclusions regarding the minimum, `dtbo`, and AVB flags. Current authority is `docs/boot-chain/minimum-first-boot-image-set.md`; the prevailing verdict is `CANNOT_YET_BE_DETERMINED`.

Date: 2026-08-24
Scope: first experiment with custom kernel, without flashing or generating executable images.
Status: static audit of stock images and U11 artifacts already present in the repository.

## Executive Summary

- **ERRATA:** root protects `boot`, `init_boot`, and `vendor_boot` via direct HASH; `dtbo` via CHAIN to its child vbmeta, whose HASH covers `dtbo`. Each inspected image also contains embedded vbmeta.
- **FACT:** `boot.img` provides the kernel; `init_boot.img` provides only GKI ramdisk; `vendor_boot.img` provides vendor ramdisk, compressed Samsung base DTB, and bootconfig; `dtbo.img` provides three overlays.
- **FACT:** The built U11 kernel is `5.15.180` and stock EZE4 inventories correspond to `5.15.189-android13-3`. With `MODVERSIONS=y` and different vermagic, the 281 modules of the stock vendor ramdisk must be treated as incompatible until proven otherwise.
- **FACT:** The three available U11 overlays are byte-identical to the overlays extracted from EZE4 `dtbo.img`. Therefore, stock `dtbo.img` is a valid candidate to remain unchanged in the minimal experiment, subject to unlocked bootloader policy.
- **ERRATA:** that operational conclusion is withdrawn. After unlock, `boot-only` is the mechanically minimal candidate for an EZE4 marker, but Samsung acceptance of the broken hash is **UNKNOWN**; there is no proven set.

## Discovered Evidence

### Direct inspection

| Image | Format | Relevant content | Embedded AVB |
|---|---|---|---|
| `artifacts/stock/images/boot.img` | Android boot v4 | kernel 39,356,928 B; ramdisk absent | footer + vbmeta SHA256_RSA4096 |
| `artifacts/stock/images/init_boot.img` | Android boot v4 | no kernel; GKI LZ4-legacy ramdisk of 2,486,802 B | footer + vbmeta SHA256_RSA4096 |
| `artifacts/stock/images/vendor_boot.img` | vendor boot v4 | vendor ramdisk LZ4-legacy of 18,077,432 B; compressed Samsung DTB of 239,652 B; bootconfig `buildtime_bootconfig=enable` | footer + vbmeta SHA256_RSA4096 |
| `artifacts/stock/images/dtbo.img` | DTBO v0 | 3 overlays; custom `[0,0]`, `[1,3]`, `[4,32]` | footer + vbmeta SHA256_RSA4096 |
| `artifacts/stock/images/vbmeta.img` | vbmeta | public key SHA-1 `b6924fd490355eca36e5a5cd9c4d2b4bd6434029`; global rollback index 0; flags 0 | root of trust |

### Root vbmeta descriptors

- Hash descriptor `boot`: original size `39,363,360`; digest `3f28d10f...31a420c`.
- Hash descriptor `init_boot`: original size `2,495,248`; digest `4f514634...f32efc`.
- Hash descriptor `vendor_boot`: original size `18,334,480`; digest `7c5898f8...050da7`.
- Hash descriptor `dtbo`: original size `542,896`; digest `47c853eb...e2dde`.
- Chain partitions: `dtbo` RIL 1, `prism` RIL 2, `optics` RIL 3.

The four hash descriptors have `flags=0`. There is no static indication of tolerance for modifications in the locked state.

### Stock vendor ramdisk ABI

**FACTS:**

- EZE4 inventory: 281 modules in `modules.load` and `modules.dep`.
- U11 kernel: 282 modules with vermagic `5.15.180 SMP preempt mod_unload modversions aarch64`.
- Documented stock reference: `5.15.189-android13-3-33478785`.
- Both sides use `CONFIG_MODVERSIONS=y`. The U11 tree has `Module.symvers`, but no comparable CRC table of the stock kernel exists in this repository.
- The first stock modules include `exynos-chipid_v2.ko`, `exynos-reboot.ko`, `sec_debug_base_early.ko`, `clk_exynos.ko`, `exynos_mct_v3.ko`, `s3c2410_wdt.ko`, and `pinctrl-samsung-core.ko`.
- In the audited U11 build, chipid, S5E8835 clocks, MCT v3, watchdog, and pinctrl core are modular; base GIC is built-in (`CONFIG_EXYNOS_GIC=y`).
- `CONFIG_MODULE_SIG_FORCE` and `CONFIG_SECURITY_LOCKDOWN_LSM` are not active in the audited U11 kernel. Automatic rejection by signature should not be overestimated; the primary blocker is vermagic/CRC/binary ABI/CFI.

**HYPOTHESES:**

- If an init or loader attempts to load stock modules with the U11 kernel, standard failure begins with format/vermagic and continues with unknown CRC/symbols where applicable. Exact behavior depends on the loader and error policy.
- If the vendor ramdisk is delivered but not processed, the kernel may reach `/init`; without critical early drivers integrated, it may lack functional clocks/timers/pinctrl or hang prior to userspace.

### DTBO

Byte-by-byte comparison:

| Stock overlay | U11 artifact | Result |
|---|---|---|
| `overlay-00-id-00000000-rev-00000000.dtbo` | `gts9fewifi_eur_open_w00_r00.dtbo` | BYTE-IDENTICAL |
| `overlay-01-id-00000000-rev-00000000.dtbo` | `gts9fewifi_eur_open_w00_r01.dtbo` | BYTE-IDENTICAL |
| `overlay-02-id-00000000-rev-00000000.dtbo` | `gts9fewifi_eur_open_w00_r04.dtbo` | BYTE-IDENTICAL |

This supports keeping stock `dtbo.img` in the first experiment. It does not eliminate uncertainty regarding how the Samsung bootloader selects the overlay or additional vendor-specific checks.

## What This Means

### Decision table by image

| Image | Function | Modification required | Can remain stock | Risk |
|---|---|---|---|---|
| `boot.img` | Deliver custom kernel to bootloader | Yes, to run U11 kernel | No, if the objective is running that kernel under UNLOCKED | Invalidates AVB descriptor; possible orange/red warning; under LOCKED likely prevents handoff |
| `init_boot.img` | Provide generic/GKI initial ramdisk | Depends: yes if custom `/init` or experimental initramfs replaces stock; no if intact stock GKI ramdisk is used | Only if its content remains compatible with U11 kernel and does not load cross-ABI code | Stock Android ramdisk may expect Android16 vendor/environment and hide or prevent experimental `/init` |
| `vendor_boot.img` | Provide vendor ramdisk, base DTB, and bootconfig | Not as a structural requirement if kernel has all pre-`/init` drivers built-in and processing its stock DLKMs is avoided; yes if replacing DTB/bootconfig or removing incompatible modules | Risky hypothesis: DT/bootconfig correct, but 281 `5.15.189` modules are NO-GO for `5.15.180` kernel | Cross-ABI loading may fail via vermagic/CRC; failures in clocks/MCT/pinctrl may prevent userspace; keeping stock reduces changes but not functional risk |
| `dtbo.img` | Apply overlay according to hardware revision | Not at this time | Yes as a strong candidate: U11 overlays are byte-identical to EZE4 | Bootloader selection and Samsung policies unverified; any change breaks AVB unnecessarily |
| `vbmeta.img` | Anchor hashes, keys, rollback indexes, and chain partitions | Yes in a coherent UNLOCKED flow: regenerate/sign with controlled key or use disabled-verification policy validated by bootloader | No if `boot` or `init_boot` changes; stock vbmeta would continue anchoring old hashes | Incorrect signature or misinterpreted flags can produce RED-state/no-boot; regeneration does not authorize flashing |

### Specific questions

#### What is the absolute minimum set?

From the executable content perspective:

1. `boot.img` with U11 kernel;
2. `vbmeta.img` consistent with changed images and acceptable by bootloader in UNLOCKED state;
3. a controlled initramfs path.

That third point can materialize in two ways:

- **Path A:** modify `init_boot.img` (and possibly `vendor_boot.img`) to deliver coherent U11 initramfs/modules. Practical set: 3–4 images.
- **Path B:** use intact stock ramdisk only if U11 kernel carries everything needed up to `/init` as built-in and no process loads the 281 stock modules. Nominal set: 2 images (`boot`, `vbmeta`), but this path is a hypothesis conditioned on build/configuration and stock Android ramdisk behavior.

Therefore, a universal "physical minimum" does not yet exist: it depends on the initramfs profile and chosen U11 build.

#### If you only change `boot.img` and `init_boot.img`, can `vendor_boot` remain stock?

Only under three simultaneous conditions:

1. UNLOCKED state and regenerated/coherent vbmeta accepted by bootloader.
2. Stock base DTB remains correct for hardware and U11 kernel.
3. No component loads the `5.15.189` modules contained in vendor ramdisk, or the loader tolerates and isolates those failures without affecting the path to `/init`.

The first condition belongs to the AVB experiment. The other two are feasible only with additional evidence. Keeping `vendor_boot` stock preserves DTB/bootconfig, but delivers an incompatible inventory; it is not recommended as a first test unless the kernel has critical early drivers built-in and the module loader is explicitly controlled.

#### What happens if the 281 stock modules reach the U11 kernel?

**Inferred scenario, not observed:**

- Vermagic `5.15.189-android13-3` does not match `5.15.180`; normal loading fails before resolving symbols.
- With `MODVERSIONS=y`, even ignoring vermagic, stock CRC tables are missing to demonstrate ABI equality.
- `CONFIG_CFI_CLANG=y` adds risk of binary callback discrepancy beyond names/CRC.
- Failures in early modules can leave the system without clocks, MCT, pinctrl, or SoC identity. Depending on the driver and probe, the outcome may be error, hang, or panic.
- If the loader ignores individual failures, boot may reach `/init`, but with essential subsystems absent; that is not a success and complicates diagnostics.

#### Can `dtbo.img` remain stock if U11 overlays are byte-identical?

Yes, as a technical content decision. The three compared artifacts are byte-by-byte identical. Two separate uncertainties remain:

- bootloader policy when selecting overlay and validating `dtbo` under UNLOCKED / alternative vbmeta state;
- correct hardware revision selection, not yet observed physically.

Not modifying `dtbo` reduces variables and preserves stock selection behavior.

#### Must `vbmeta.img` always be regenerated? Is a flag enough?

If any image anchored by root vbmeta changes, its descriptor ceases to match. The OEM key is not available. On an UNLOCKED device, one hypothesis is using `VERIFICATION_DISABLED` (`flags=2`), provided the Samsung bootloader respects that policy. `flags=1` is `HASHTREE_DISABLED`, which does not disable hashes/signatures; `flags=3` combines both bits.

No value is automatically sufficient:

- **FACT:** stock vbmeta has flags 0 and OEM signature.
- **HYPOTHESIS:** unlocked bootloader accepts an alternative vbmeta with `flags=2` or `flags=3`.
- **HYPOTHESIS:** Samsung does not add additional checks that cause that configuration to fail.

The AVB experiment must first define a validated recovery route. Under LOCKED it must not be assumed that any flag permits boot.

## Risks

| Risk | Class | Proposed mitigation |
|---|---|---|
| Mixing U11 kernel with 281 stock U12 modules | High | Treat as NO-GO; use coherent U11 initramfs or built-in early drivers |
| Believing changing only boot/vbmeta is sufficient | Critical if stock Android ramdisk is used | Explicitly define who provides `/init` and which modules are loaded |
| Modifying DTBO unnecessarily | Medium | Keep stock because overlays are identical |
| Assuming `flags=2/3` is universally valid | High | Maintain as Samsung hypothesis until validating recovery and obtaining future authorization |
| Concealing module failures via tolerant loader | Medium-High | Record every load result; do not interpret reaching a shell as full compatibility |
| Confusing AVB rejection with early kernel crash | High | Use signal matrix: persistent warning, Download Mode, USB enumeration, and power consumption |

## Hypotheses

1. A U11 kernel with chipid, S5E8835 clock, MCT v3, pinctrl, and basic PMU built-in can reach `/init` without processing stock U12 modules.
2. Stock GKI ramdisk can coexist with that kernel only if it does not impose incompatible dependencies prior to experimental `/init`.
3. Corrected historical hypothesis: UNLOCKED bootloader accepts modified images with `VERIFICATION_DISABLED` (`flags=2`) while `vendor_boot` and `dtbo` remain stock. Samsung acceptance remains **UNKNOWN** and the set is no longer the canonical minimal candidate.
4. Stock DTBO selection works without image change because overlay content is byte-by-byte equivalent.
5. Samsung does not require an additional Knox/RPMB chain incompatible with this scheme.

No prior hypothesis authorizes a physical attempt on its own.

## Recommended Experiments

All are local audits or plan preparation; none generates a flashable image.

1. **Close built-in path:** audit config/build necessary to integrate critical pre-userspace drivers as `=y` and verify that `/init` does not depend on stock vendor ramdisk.
2. **Define minimal U11 initramfs:** non-flashable local packaging to measure size and dependencies; separate MINIMAL profile from SEC_DEBUG.
3. **Simulate image composition:** calculate offsets, sizes, and hashes of candidate boot/init_boot/vbmeta without writing partitions.
4. **Test AVB policy locally:** verify candidate chains with avbtool and document which descriptor should fail in each combination.
5. **Calibrate stock baseline:** USB/power/display observation plan with current firmware before any physical change.
6. **Decide physical order:** after closing earlycon/sec_debug and unlock, start with the smallest number of changed images that guarantees coherent initramfs; do not optimize for "fewer bytes" but for less uncertainty.

## Proposed Documentation

- This document as canonical source of minimal modification set.
- `docs/boot-chain/avb-experiment-plan.md` must define states, signals, and recovery.
- `docs/debugging/earlycon-analysis.md` must decide cmdline/bootconfig before fixing `boot`/`vendor_boot`.
- `docs/debugging/sec-debug-firstboot-profile.md` must fix modules and load order of initramfs.
- Update `docs/first-boot-experiment-plan-v2.md` with the conclusion: real minimum depends on initramfs/built-in path, and stock U12 vendor ramdisk must not be loaded against U11 kernel.
