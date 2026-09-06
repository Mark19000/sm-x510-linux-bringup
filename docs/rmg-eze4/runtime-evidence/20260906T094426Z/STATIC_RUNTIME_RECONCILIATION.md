# Static/runtime reconciliation

Session: `20260906T094426Z`

| Area | Category | Finding |
|---|---|---|
| Firmware identity | STATIC_CONFIRMED | `SM-X510`, `gts9fewifi`, and incremental `X510XXUCEZE4` match the canonical baseline. |
| Exact fingerprint | STATIC_REFINED | Runtime supplies `samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys`, previously unavailable. |
| Kernel identity | STATIC_CONFIRMED | Runtime reports `5.15.189-android13-3-33478785`, aarch64, PREEMPT. |
| Effective nokaslr | NO_USEFUL_RUNTIME_EVIDENCE | `/proc/cmdline` was permission denied; logcat had no KASLR match. Static DT evidence is unchanged but not runtime-confirmed. |
| Effective cmdline | NO_USEFUL_RUNTIME_EVIDENCE | Permission denied; no bypass attempted. |
| Effective bootconfig | NO_USEFUL_RUNTIME_EVIDENCE | Permission denied; no bypass attempted. |
| CPU topology | RUNTIME_ONLY_INFORMATION | CPUs `0-7` were online at capture. This informs context, not timing values. |
| Memory environment | RUNTIME_ONLY_INFORMATION | `MemTotal=7899684 kB`, `MemAvailable=4335012 kB`, and `SwapTotal=8388604 kB` at capture. This is one snapshot, not allocator geometry. |
| ROOT_UMH_PATH | STATIC_REFINED | Exact pathname is `NOT_FOUND` on the current untouched stock `/data`, confirming that existence is deployment state. |
| Useful boot logs | NO_USEFUL_RUNTIME_EVIDENCE | A successful logcat retry provided no AP kernel placement evidence; dmesg was inconclusive after transient ADB loss. |
| P0/loader mapping | NO_USEFUL_RUNTIME_EVIDENCE | No address-domain correlation or placement selector was exposed. |

No observation contradicts `CANONICAL_STATUS.md`. The EEA fingerprint refines the former metadata unknown; it does not change active target semantics or establish loader behavior.
