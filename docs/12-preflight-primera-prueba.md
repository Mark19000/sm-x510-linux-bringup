# 12. Preflight for First Physical Hardware Boot Test

## Current Verdict: NO-GO

Reference artifacts serve offline lab validation, but **must not be flashed**. The gate does not open simply because payloads fit within partition size budgets or compile cleanly; it opens only when all evidence regarding identity, recovery, observability, and authenticity is complete.

| Gate | Current Evidence | Status |
|---|---|---|
| Model / Firmware | SM-X510, EUX/OXM, X510XXUCEZE4, U12 | Complete |
| Official Stock Package | Complete firmware ZIP and extracted partitions with hashes | Complete |
| Image Formats | Android v4 boot, init_boot, and vendor_boot measured | Complete |
| Offline Build Pipeline | Image, DTB, DTBOs, 282 modules, initramfs profiles | Complete |
| Packaging Integrity | Byte-identical unpack/repack round trip verified | Complete |
| Stock AVB | RSA4096 signature and partition digests verify | Complete |
| Candidate AVB | Digest mismatch detected, as expected | **BLOCKS** |
| EZE4 Kernel Source | Only known U3 reference exists | **BLOCKS** |
| Effective Hardware Revision | r00/r01/r04 table known, physical choice unobserved | **BLOCKS** |
| Observable Console | UART/USB/pstore unvalidated on physical unit | **BLOCKS** |
| Bootloader Unlock / Knox | State and consequences not accepted / recorded by owner | **BLOCKS** |
| Restored Recovery Procedure | Firmware available, flashing restore unvalidated | **BLOCKS** |

A single `BLOCKS` maintains the overall `NO-GO` verdict.

## Safe Read-Only Diagnostic Collection

With stock Android running and USB debugging authorized:

```sh
./scripts/collect-device.sh
```

Review results thoroughly:

```sh
sed -n '1,120p' reports/device-*/identity.txt
sed -n '1,220p' reports/device-*/proc-cmdline.txt
sed -n '1,220p' reports/device-*/partitions-by-name.txt
file reports/device-*/running.dtb
```

Re-confirm `SM-X510`, `X510XXUCEZE4`, U12 bootloader, and EUX CSC. If `running.dtb` is empty due to Android security permissions, record it as missing data; do not guess the active overlay.

Do not use `adb root`, `dd`, direct writes to `/dev/block`, slot changes, Odin/Heimdall, or reboot commands into download/recovery mode during this phase.

## Offline Evidence Required for Every Build

```sh
make test

DIST=artifacts/kernel/wifi/reference-dist
(cd "$DIST" && sha256sum -c SHA256SUMS)
(cd artifacts/busybox && sha256sum -c SHA256SUMS)
(cd artifacts/initramfs/wifi && sha256sum -c SHA256SUMS)
./scripts/verify-avb-candidates.sh
```

The final command **must** report two things simultaneously: stock passes verification, and candidate is rejected by digest. Rejecting an AVB-invalid candidate proves the validator works; it does not authorize disabling AVB verification.

Also record:

```sh
cat "$DIST/BUILD-METADATA"
cat artifacts/stock/boot-layout.json
cat artifacts/candidates/reference/SHA256SUMS
```

## Mandatory Conditions Prior to Designing a Boot Attempt

1. Obtain and compare the exact OSRC source corresponding to EZE4, or formally justify every divergence affecting DT, Kconfig, and ABI. The U3 reference does not satisfy this gate.
2. Identify the active hardware revision and overlay of the physical unit via bootloader diagnostic evidence or runtime Device Tree.
3. Document the actual OEM Unlock state, data wipe implications, and potential permanent Knox alteration. The decision belongs exclusively to the device owner.
4. Establish an official restoration path compatible with U12, stable external power, reliable cabling, and a secondary host system prepared for emergency recovery.
5. Secure an observable output channel prior to UFS initialization: verified serial console, pre-tested USB ACM gadget, or proven persistent crash logging.
6. Resolve AVB through the legitimate workflow supported by an unlocked bootloader. Do not fabricate Samsung signing keys, flash third-party "vbmeta disable" hacks, or attempt bootloader downgrade.
7. Explicitly define the single variable being modified and the temporal abort criteria.

## First Attempt Design Once All Gates Pass

The initial test target is strictly milestone M2/M3: early kernel banner and execution of `/init`. It must use initramfs `MODULES_MODE=none`, no persistent root, and no experimental charging drivers. UFS storage, graphical display, and Wi-Fi are outside the scope of the initial test.

Before any future hardware write, create an immutable attempt record:

```text
Attempt ID:
UTC Date/Time:
Model / AP / CSC / Bootloader / Hw-Rev:
Official Stock Firmware Hash:
Exact Source Commit and patchset_sha256:
SHA-256 for Image, DTB, DTBO, CPIO, and Container Image:
AVB Result and Bootloader Policy:
Console Channel and Preflight Test:
Restoration Runbook and Available Host Machine:
Single Variable Changed:
Timeout and Abort Condition:
```

Following the attempt, attach the raw console log even if empty. A silent reboot without output does not prove "the kernel fails to execute"; it simply isolates the failure to before the first observable output channel.

## Immediate Stop Triggers

- Model, AP, CSC, binary counter, or partition sizing mismatches;
- Any proposal to downgrade bootloader from U12 to U3;
- File hashes diverging from values recorded in the attempt sheet;
- AVB verification failing for an unexpected reason;
- Missing local stock recovery firmware or reliance on future internet downloads during recovery;
- Tablet running hot, unstable battery voltage, or lacking stable external power;
- Proposal to test new kernel, DTBO, vbmeta, and rootfs simultaneously.

Encountering any of these conditions requires an immediate return to offline analysis. Stopping during preflight is a successful safety outcome: it prevents turning a technical unknown into data loss or a non-recoverable device brick.
