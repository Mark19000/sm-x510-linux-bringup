# First stock runtime observation plan

This is a future observation-only plan. It assumes stock firmware and bootloader, no root, exploit, flashing, image changes, module loading, or persistent changes.

## PRECHECKS

| PURPOSE | COMMAND_OR_SOURCE | EXPECTED_OUTPUT | WHICH_PARAMETER_OR_UNKNOWN_IT_INFORMS | RISK | PERSISTENT_CHANGE |
|---|---|---|---|---|---|
| Confirm ordinary ADB connection | `adb get-state` | `device` or a connection error | Session validity only | Minimal | None |
| Record firmware identity | `adb shell getprop ro.build.fingerprint` and `adb shell getprop ro.build.version.incremental` | Stock property strings | Confirms EZE4 observation context | Minimal | None |
| Record kernel identity | `adb shell uname -a` | Kernel release/build string | All environment-dependent rows | Minimal | None |

## BOOT OBSERVATIONS

| PURPOSE | COMMAND_OR_SOURCE | EXPECTED_OUTPUT | WHICH_PARAMETER_OR_UNKNOWN_IT_INFORMS | RISK | PERSISTENT_CHANGE |
|---|---|---|---|---|---|
| Confirm effective command line | `adb shell cat /proc/cmdline` | Readable command line or permission denial | `nokaslr`; loader-boundary inputs | Minimal | None |
| Inspect effective bootconfig | `adb shell cat /proc/bootconfig` | Key/value boot configuration or absence | Loader/P0 inputs | Minimal | None |
| Collect legitimate boot log buffer | `adb logcat -b all -d -v threadtime` | Existing log buffers | Possible load/KASLR messages; no assumption they exist | Low; potentially sensitive local logs | None |
| Check whether kernel log is ordinarily readable | `adb shell dmesg` | Existing log or permission denial | Possible placement evidence | Low; potentially sensitive local logs | None |

## POST-BOOT OBSERVATIONS

| PURPOSE | COMMAND_OR_SOURCE | EXPECTED_OUTPUT | WHICH_PARAMETER_OR_UNKNOWN_IT_INFORMS | RISK | PERSISTENT_CHANGE |
|---|---|---|---|---|---|
| Record CPU topology | `adb shell cat /sys/devices/system/cpu/online` | Online CPU range | Timing/race prerequisites only | Minimal | None |
| Record memory environment | `adb shell cat /proc/meminfo` | Memory counters | Allocation/resource prerequisites only | Minimal | None |
| Record scheduler-visible uptime/load | `adb shell cat /proc/uptime` and `adb shell cat /proc/loadavg` | Uptime and load figures | Timing context only | Minimal | None |
| Check deployment pathname metadata | `adb shell ls -ld /data/local/tmp/cve-2026-43499-root` | File metadata or not-found/permission result | `ROOT_UMH_PATH` existence only | Minimal | None |

## LOG COLLECTION

Capture command outputs verbatim with device time, firmware properties, and one session identifier in a host-side evidence directory. Host-side capture does not change the device. Do not interpret absent log text as proof that a slide is unreachable.

## TIMING OBSERVATIONS

If desired, record host-observed duration of benign read-only commands such as `adb shell true` and `adb shell getprop ro.build.fingerprint`. These measurements describe ADB/userspace latency only. They do not validate the five race/allocator parameters or any vulnerable kernel path.

## STOP CONDITIONS

Stop if the device is not demonstrably on stock EZE4, ADB requests authorization changes beyond the already accepted ordinary debugging relationship, any command would require root, a command would write device state, logs expose material the operator does not wish to retain, or observed state differs from the documented baseline. Do not substitute privileged commands, vulnerability triggers, flashing, bootloader actions, or module operations.
