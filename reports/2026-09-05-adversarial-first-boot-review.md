# SM-X510 U12/EZE4 — Adversarial Unlock & First-Boot Review

> **Errata 2026-09-05:** this review identified defects, but not all legacy documents were corrected at that time. The subsequent errata audit quarantines them; this report must not be interpreted as a closure certification.

> **Physical Evidence Update (2026-09-05):** Physical observation of the pre-Download Mode screen (requested in Section 11) was completed via capture `IMG_2113.HEIC`. The Chinese language text explicitly confirms the affordance `长按音量增加键：设备解锁模式` ("Long press Volume Up key: Device Unlock Mode"), omitted from the English section. Consequently, the bootloader-exposed path status transitions from `INSUFFICIENT_EVIDENCE` / `UNKNOWN` to **`CONFIRMED`**, and practical capability to **`STRONGLY_SUPPORTED`**. Unit status remains strictly **`LOCKED`** (`ro.boot.flash.locked=1`, `warranty_bit=0`), the meaning of `[Reboot Device - D2]` remains **`UNKNOWN`**, and custom flashing remains **`NOT_READY_FOR_FIRST_CUSTOM_FLASH`** as host recovery and AVB validation remain pending. See [`docs/boot-chain/unlock-evidence-matrix.md`](file:///Users/markpi/tab-s9-fe-linux/docs/boot-chain/unlock-evidence-matrix.md).

> **Historical closure annotation:** documentation defects identified here are canonically consolidated in [`docs/boot-chain/unlock-evidence-matrix.md`](file:///Users/markpi/tab-s9-fe-linux/docs/boot-chain/unlock-evidence-matrix.md) and [`docs/hardware/evidence/2026-09-05-download-warning-device-unlock-mode.md`](file:///Users/markpi/tab-s9-fe-linux/docs/hardware/evidence/2026-09-05-download-warning-device-unlock-mode.md).

Date: 2026-09-05. Scope: static, non-invasive review. No image was unlocked, flashed, signed, or generated.

## 1. Executive verdict

**Final verdict: NO.** Would not yet authorize proceeding to unlock or first custom boot.

The kernel/ABI front is exceptionally strong: EZE4 `5.15.189` source, stock kernelrelease/vermagic, 281/281 modules, and 15,123/15,123 CRCs. That reduces risk *after* handover, but does not resolve the two most dangerous frontiers:

1. **Unproven unlock:** the unit is `locked`, OEM toggle does not appear, and there was no evidence of the Samsung "Device Unlock Mode" affordance, nor physical reading of FRP/RMM/OEM LOCK in Download Mode.
2. **Non-operational recovery:** Download Mode enumerates, but a Loke/Odin session has not been tested; `heimdall` is not installed and the full firmware ZIP recorded in `artifacts/stock/FIRMWARE_SHA256SUM` no longer exists at that path. Only extracted partial images remain.

Furthermore, the plan contains a confirmed AVB error: **`flags=1` does not disable signature/hash verification; it disables hashtree. `VERIFICATION_DISABLED` is `flags=2`**. The "vbmeta-only with flags=1" probe does not test what the document asserts.

Overall classification: kernel software **CONFIRMED**; unlock **INSUFFICIENT_EVIDENCE**; Samsung AVB policy **UNKNOWN**; recovery **CONTRADICTED** relative to "guaranteed".

## 2. What is genuinely proven

| Evidence | State | Actual Scope |
|---|---|---|
| SM-X510 Wi-Fi, S5E8835, EZE4/U12 | **CONFIRMED** | Unit and firmware identity. |
| `ro.boot.flash.locked=1`, vbmeta device state locked, verified boot green | **CONFIRMED** | Current locked state; does not report whether unlock is permitted. |
| KG `Completed` | **CONFIRMED** | Samsung defines Completed as KG service terminated and client deactivated; does not by itself equal OEM unlock enabled. [Samsung Knox Guard](https://docs.samsungknox.com/dev/knox-guard/how-knox-guard-works/) |
| Download Mode and USB `04e8:685d` | **CONFIRMED** | Physical path and enumeration function today with stock. Does not prove transfer, PIT, or flashing/restoration. |
| EZE4/stock ABI | **CONFIRMED** per provided validation | Eliminates legacy U11/U12 risk; does not validate boot headers, AVB, or Samsung policy. |
| Boot v4 layout | **CONFIRMED** | `boot`: kernel / empty ramdisk; `init_boot`: ramdisk; `vendor_boot`: vendor ramdisk + DTB + table + bootconfig. See `artifacts/stock/boot-layout.json`. |
| Root AVB | **CONFIRMED** by official `avbtool` | RSA4096/SHA256, RIL 0, index 0, flags 0; graph detailed in §5. |
| Factory reset on changing LOCKED→UNLOCKED | **STRONGLY_SUPPORTED**, not observed | AOSP requires physical confirmation and data wipe; exact Samsung behavior and UI timing remain unobserved. [AOSP locking/unlocking](https://source.android.com/docs/core/architecture/bootloader/locking_unlocking) |
| Knox consequences | **STRONGLY_SUPPORTED** for non-approved software; exact timing **UNKNOWN** | Samsung confirms Warranty Bit persistence and Knox feature lockout if tripped, but does not prove this firmware burns it during the mere act of unlock, before executing/flashing non-approved code. [Samsung hardware-backed security](https://docs.samsungknox.com/admin/fundamentals/whitepaper/samsung-knox-mobile-security/system-security/hw-backed-security/) |

## 3. Weak assumptions

1. **"Hidden OEM toggle = seven-day wait / RMM." — UNKNOWN.** May be regional policy, incomplete provisioning, FRP/account, enterprise management, RMM/KG, date/time/network, firmware, or complete lack of support. No reading of `OEM LOCK`, `FRP LOCK`, `RMM STATE`, or physical affordance discriminates.
2. **"KG Completed unlocks OEM." — CONTRADICTED.** Only means KG management ended. KG, RMM, FRP, and bootloader lock are distinct states.
3. **"EUX permits unlock." — UNKNOWN.** `ro.oem.key1=EUX` identifies customization/market; it is not a capability bit.
4. **"Device Unlock Mode still exists." — UNKNOWN for EZE4.** Download Mode exists; long-press Vol-Up option and its text were not documented.
5. **"Unlock burns Knox immediately." — PLAUSIBLE, not confirmed.** Local documentation asserts it categorically in `docs/decisions/oem-unlock-knox.md`; must be downgraded until observed or specific documentation is found. Warranty Bit is persistent if tripped.
6. **"Restoring stock reverts everything." — CONTRADICTED.** Does not revert Warranty Bit, necessarily attestation, or UNLOCKED state; relock has its own risks and normally another wipe.
7. **"U11 bootloader would cause hard-brick." — CONTRADICTED as certainty.** Expected standard anti-rollback result is `SW REV CHECK FAIL` rejection; writing mismatched bootloaders/PIT can be critical, but there is no evidence that a normal downgrade attempt accepted by Loke necessarily produces a brick.
8. **"PBL/iROM guarantees Download Mode always." — CONTRADICTED.** The runbook attributes Loke to ROM and promises access even with corruption. Current enumeration only proves the current chain; Download Mode depends on more than the kernel and has not been tested after corruption or power failure.
9. **"USB detach / power draw / backlight proves handover." — CONTRADICTED as proof.** Plausible but non-exclusive indicators: bootloader reset/rejection produces similar signals.
10. **"Identical DTBO eliminates hw_rev." — CONTRADICTED.** Content is validated; the revision applied by this unit and Samsung selection remain unobserved.

## 4. Unlock path verdict

### `INSUFFICIENT_EVIDENCE`

The unit is locked and the visible prerequisite — OEM Unlocking — is missing. `KG=Completed` is favorable because KG no longer manages the device, but does not prove absence of RMM/FRP or `get_unlock_ability=1`. AOSP describes the toggle as the mechanism enabling unlock capability requiring physical confirmation + wipe, but Samsung uses Download Mode/Loke and may add custom policy. [AOSP locking/unlocking](https://source.android.com/docs/core/architecture/bootloader/locking_unlocking)

I do not classify as `BLOCKED` because full screen observation is still pending; neither as `LIKELY` because the single directly relevant indicator — the toggle — is negative.

**Next single, non-destructive observation:** enter Download Mode without confirming any prompt and photograph/transcribe the **entire** screen, including `OEM LOCK`, `FRP LOCK`, `KG/RMM STATE`, `WARRANTY VOID`, `AP SWREV`, and all key instructions. The presence/absence of "hold Volume Up: Device Unlock Mode" provides more information than waiting days blindly. Do not hold down or accept an unlock screen during this observation.

## 5. AVB trust graph

Inspection reproduced with official AOSP `avbtool` on `artifacts/stock/images/*`:

```text
Samsung root of trust
└── vbmeta (SHA256_RSA4096, rollback=0 @ location 0, flags=0)
    ├── HASH boot          ── boot v4 payload (also carries footer/vbmeta self-hash)
    ├── HASH init_boot     ── init_boot v4 (footer/vbmeta self-hash)
    ├── HASH vendor_boot   ── vendor_boot v4 (footer/vbmeta self-hash)
    ├── HASH recovery
    ├── HASH bootloader/fld/harx/keystorage/ldfw/tzsw
    ├── HASHTREE system/vendor/product/odm/system_dlkm/vendor_dlkm
    ├── CHAIN dtbo   @ rollback location 1 ── embedded vbmeta → HASH dtbo
    ├── CHAIN prism  @ rollback location 2 ── no local image audited
    └── CHAIN optics @ rollback location 3 ── no local image audited
```

| Partition | Descriptor / Parent | Rollback | If Changed | Expected Effect of Root Flags |
|---|---|---:|---|---|
| `boot` | Direct HASH in root vbmeta; additional self-hash footer | root loc. 0; footer shows 0 | Recalculate content/footer and root descriptor; OEM signature unavailable | `flags=2` requests skipping downstream AVB verification; Samsung acceptance UNKNOWN. `flags=1` does not suffice. |
| `init_boot` | Direct root HASH + footer self-hash | observed loc. 0 | Same as boot | Same. |
| `vendor_boot` | Direct root HASH + footer self-hash | observed loc. 0 | Same; also preserve table/DTB/bootconfig | Same. |
| `dtbo` | CHAIN from root to OEM key, RIL 1; embedded vbmeta contains HASH dtbo | loc. 1, embedded index 0 | Requires valid metadata in partition and consistency with chain, unless implementation skips verification | In standard libavb `VERIFICATION_DISABLED` stops verification; Samsung behavior UNKNOWN. |
| `prism`, `optics` | Root CHAIN | loc. 2/3 | Do not touch; local content unaudited | Do not assert coverage without images. |

**Mandatory correction:** `AVB_VBMETA_IMAGE_FLAGS_HASHTREE_DISABLED=1`; `AVB_VBMETA_IMAGE_FLAGS_VERIFICATION_DISABLED=2`, confirmed in official `avbtool`. A historical version of `docs/boot-chain/avb-experiment-plan.md` used `flags=1` as "verification disabled"; it was corrected and quarantined. `--disable_verity` and `--disable_verification` produce different bits; using both yields 3. [AOSP AVB](https://android.googlesource.com/platform/external/avb/)

That AOSP indicates an UNLOCKED device may continue with errors does not prove Samsung EZE4 implements exactly that tolerance. [AOSP device state](https://source.android.com/docs/security/features/verifiedboot/device-state)

## 6. Minimum modification set verdict

### **E — cannot yet be proven**

- To **replace only the kernel**, `boot` is the functionally correct partition: boot v4 contains kernel and empty ramdisk. A `boot + vbmeta` could structurally suffice for a handover probe.
- For **minimal Linux userspace**, the ramdisk resides in `init_boot`; therefore the logical candidate is `boot + init_boot + vbmeta`.
- `vendor_boot` can remain stock in principle because it provides correct DTB/DTBO and all 281 modules now have exact ABI match with EZE4. But tests of init sequence, runtime module signing, ramdisk dependencies, and ensuring a modified kernel preserves all expected contracts remain missing.
- `dtbo` must remain stock as long as no concrete need exists.

I do not select A/B because Samsung policy on alternate vbmeta and embedded footers is unproven. I do not select C/D because there is no evidence `vendor_boot` must change. The error in the plan is confounding **structural minimum**, **minimum to detect handover**, and **minimum to reach `/init`**.

A vbmeta-only probe is also not "harmless": it replaces the root covering boot, init_boot, vendor_boot, recovery, firmware, and hashtrees, and flags 2/3 can alter policy for the entire chain.

## 7. Observability ranking

| Rank | Channel | Earliest Stage | Dependencies | Confidence / Failures |
|---:|---|---|---|---|
| 1 | Download/Odin | Pre-kernel | Current boot chain, keys, USB-C, Loke | **CONFIRMED** for stock. Only tests visible bootloader/transport, never kernel execution. |
| 2 | USB electrical | Power-on / pre-kernel | Meter and repeatable baseline | **PLAUSIBLE**. Distinguishes phases, not actors; rejection and crash can overlap. |
| 3 | DSS `log_kernel` | From printk if DSS is active early | Reserved memory, driver/firmware, persistence and later reader | **PLAUSIBLE/STRONGLY_SUPPORTED** by DT/source; survival across wipe/reset and extraction method unproven. |
| 4 | Display | After clocks/pinctrl/DRM or bootloader splash | Driver/panel/firmware; distinguish splash from kernel | **PLAUSIBLE**, low specificity. |
| 5 | USB gadget | Late kernel or `/init` | DWC3/PHY/clocks/gadget config/userspace | **STRONGLY_SUPPORTED** as positive test; absence diagnoses nothing. |
| 6 | pstore/ramoops | After console/panic | Configured backend + persistent reserved region | **UNKNOWN / not available today**: config exists, but no active node/param. |
| 7 | Recovery / Android post-mortem | After failure | Bootable stock recovery, block/log access, no overwrite | **PLAUSIBLE**. Post-read method, not early channel; recovery covered by root vbmeta. |

`sec_debug` is not a safety net for the first pre-handover failure: if AVB rejects it does not run; if its components are modules, it only helps after `/init` loads them. Built-in DSS can be earlier, but it must be proven that buffers survive and are readable afterwards.

## 8. Recovery review

Current status: **not recovery-ready**.

- Download Mode reached and enumerates: **CONFIRMED**.
- Loke handshake, PIT read, and safe short transfer: **UNTESTED**.
- `heimdall`: **not installed** on this `arm64` Mac.
- Official Odin: requires a Windows host; no validated Windows/VM/passthrough exists.
- Heimdall claims macOS support, but recent reports/forks exist specifically for USB stalls on large transfers on Apple Silicon; that invalidates assuming enumeration suffices to restore `super`. [Heimdall upstream](https://github.com/benjamin-dobell/heimdall), [Apple Silicon fork](https://github.com/aljosasavic/heimdall-apple-silicon)
- Complete EZE4 firmware recorded as `/Users/markpi/Downloads/SAMFW.COM_SM-X510_EUX_X510XXUCEZE4_fac.zip` **is not present**. Only `boot/init_boot/vendor_boot/dtbo/vbmeta/recovery` exist; complete verifiable BL/AP/CSC are missing locally.
- The runbook instructs restoring only `boot` and `vendor_boot`; that is incorrect if `vbmeta` or `init_boot` was also altered. **Every modified partition** must be restored, and in an uncertain state the complete BL/AP/CSC package, without PIT/repartition unless necessity is demonstrated.
- `HOME_CSC` must not promise data preservation after unlock: unlock may already have wiped `userdata`, and FRP may require previous account credentials.

Adversarial scenario: a rejected vbmeta likely leaves Download Mode available, but it is not guaranteed. Power failure during bootloader/partition-table flashing, an incorrect binary revision accepted by a flawed tool, or USB disconnect during a critical partition write can exceed documented recovery procedures. Do not touch BL, PIT, `tzsw`, `ldfw`, `prism`, `optics`, or `super` in a first phase.

## 9. Brick-risk matrix

| Action | Risk | Plausible "Brick" |
|---|---|---|
| vbmeta-only | **MEDIUM** | Rejection / reboot loop; normally soft brick if Download Mode and stock vbmeta remain restorable. Affects entire trust graph, not just boot. |
| custom `boot.img` | **MEDIUM** | Rejection or kernel crash/hang; expected soft brick. Risk grows with incorrect header/size and lack of proven recovery. |
| custom `init_boot` | **MEDIUM** | Panic / no `/init`, loss of expected userspace recovery; soft brick if Download Mode works. |
| custom `vendor_boot` | **HIGH** | Incorrect DTB / vendor ramdisk / table / bootconfig can cause extremely early failure; harder recovery but normally via Download Mode. |
| custom `dtbo` | **HIGH** | Erroneous overlay / reserved-memory / regulators can hang, reset, or cause functional damage; unnecessary with identical stock DTBO. |
| rollback mistakes | **HIGH** | Standard downgrade should be rejected; accepted higher indices can raise a persistent floor / RPMB preventing prior stock from booting. Potential persistent soft brick; boot-chain writes raise material risk. |
| partition size mistakes | **HIGH** | Safe tool must reject oversize; raw/truncated write can corrupt neighboring partition / metadata. From soft brick to potentially unrecoverable. |
| wrong image header | **MEDIUM** | Rejection before kernel; normally soft brick. May appear as AVB failure. |
| wrong bootloader revision | **HIGH** | Expected outcome is SWREV rejection, not "automatic hard-brick." If an incompatible BL/PIT is successfully written or interrupted, Download Mode can be lost: potentially unrecoverable without disassembly/JTAG, prohibited here. |

"LOW" is not appropriate for any write while end-to-end recovery does not exist. None of these actions typically entails physical damage; hardware risks arise primarily from DT/regulators, thermals, battery charging, or writing critical firmware.

## 10. Exact blockers remaining

1. Full Download Mode screen: OEM/FRP/RMM/KG/Warranty/SWREV and Device Unlock Mode affordance.
2. Verifiable explanation of why OEM Unlocking does not appear; do not assume a timer.
3. Owner consent to wipe and possible irreversible Warranty Bit.
4. Correct all references to `flags=1` as verification-disabled; distinguish flags 1, 2, and 3.
5. Define handling of root vbmeta and embedded footers without assuming Samsung tolerance.
6. Retrieve and verify complete EZE4 BL/AP/CSC firmware; currently missing.
7. Real recovery host: Odin/Windows or compatible Heimdall, installed and tested through handshake/PIT without writing.
8. Explicit inventory of all partitions each experiment would alter and exact rollback procedure.
9. Unequivocal positive execution signal; power draw / detach alone do not suffice.
10. Demonstrate DSS/sec_debug reader and persistence before treating them as recovery telemetry.

## 11. One recommended next action

**Perform a single photographic capture / full transcription of Download Mode, without pressing the unlock option or accepting prompts.**

That data determines whether an advertised Samsung unlock path exists, exposes real FRP/RMM/OEM/KG, and validates or refutes several runbook pages without altering device state. If "Device Unlock Mode" does not appear or active FRP/RMM exists, halt the unlock line and diagnose that condition; do not compensate by attempting vbmeta.

## Final answer

**NO**

Would not authorize the owner to proceed yet: OEM toggle is absent, unlock path is unproven, AVB plan uses the wrong flag, and macOS recovery is not prepared nor possesses the recorded complete firmware. ABI parity eliminates a major risk, but does not compensate for these pre-kernel and recovery shortcomings.
