# Post-unlock stock baseline — design only

Purpose: measure the transition from locked stock to unlocked stock before any custom binary is introduced. This checklist does not authorize or describe the unlock action itself.

## Preconditions

- Owner separately accepted factory reset and uncertain Knox consequences.
- Unlock path was physically identified, not guessed.
- Recovery met the project readiness gate.
- The device has completed any unlock-triggered reset and boots unmodified EZE4 stock.

## Capture set

Record a timestamped bundle and compare it to the locked-stock baseline:

```text
adb shell getprop
adb shell cat /proc/cmdline
adb shell cat /proc/version
adb shell uname -a
adb shell cat /proc/bootconfig
adb shell cat /sys/firmware/devicetree/base/chosen/bootargs
adb shell cat /proc/modules
adb shell dmesg
```

Failure/permission denial is recorded, not bypassed. Also record labelled values for:

```text
ro.boot.flash.locked
ro.boot.vbmeta.device_state
ro.boot.verifiedbootstate
ro.boot.warranty_bit
knox.kg.state
ro.boot.kg
ro.boot.kg.bit
ro.boot.other.locked
ro.boot.frp_status
ro.oem_unlock_supported
sys.oem_unlock_allowed
```

Photograph the full normal boot warning, Developer Options OEM row if present, and all Download Mode status fields. Record factory-reset timing and whether Internet/account setup was required. Do not infer missing properties from blank, unlabelled output.

## Integrity comparison

- Verify the device still reports EZE4/U12 and exact stock kernelrelease.
- Compare the captured properties and Download Mode fields against locked stock.
- Where Android permissions allow read-only access, hash named block partitions; otherwise retain the already verified firmware images and record “not readable”, not an assumed match.
- Do not proceed if stock Android, Download Mode, charging or USB behavior is abnormal.

## Exit condition

The baseline is complete only when the device is demonstrably UNLOCKED while still running stock EZE4 and the delta from locked stock is archived. This milestone is distinct from first custom flash.
