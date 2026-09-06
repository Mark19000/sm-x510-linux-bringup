# Phase G — first non-invasive stock runtime observation

```text
SESSION_ID: 20260906T094426Z
DEVICE_CONNECTED: YES (one transient disconnect after logcat; reconnected)
BASELINE_MATCH: YES
FIRMWARE: X510XXUCEZE4; samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys; security patch 2026-05-05
KERNEL: Linux 5.15.189-android13-3-33478785 #1 SMP PREEMPT; aarch64

CMDLINE_READABLE: NO — PERMISSION_DENIED
BOOTCONFIG_READABLE: NO — PERMISSION_DENIED
DMESG_READABLE: INCONCLUSIVE — ADB disconnected at the sole permitted attempt
LOGCAT_CAPTURED: YES

NOKASLR_RUNTIME_STATUS: UNKNOWN — effective cmdline unavailable and no legitimate log evidence

ROOT_UMH_PATH_STATUS: NOT_FOUND on current stock deployment

RUNTIME_PARAMETERS_TOTAL: 20
VALIDATED: 0
PARTIALLY_INFORMED: 15
UNCHANGED: 5
CONTRADICTED: 0

P0_NEW_EVIDENCE: NO_NEW_EVIDENCE
P0_LOADER_MAPPING_STATUS: OPEN
COLLISION_REACHABILITY_STATUS: UNKNOWN / INSUFFICIENT_EVIDENCE

STATIC_MODEL_CONTRADICTIONS: 0

DEVICE_WRITES_PERFORMED: NO
ROOT_USED: NO
PAYLOAD_EXECUTED: NO
KERNEL_PATH_TRIGGERED: NO
FLASHING_PERFORMED: NO
```

The baseline is confirmed. Runtime observation refines the exact build fingerprint, kernel build identity, CPU topology, one memory/load snapshot, and the absence of the helper at its exact current pathname. These facts partially inform 15 rows but validate none of the 19 L3 parameters and do not validate the helper path value for a future deployment. Five rows receive no parameter-specific evidence and remain unchanged.

`/proc/cmdline` and `/proc/bootconfig` were normally read once and denied. The first logcat download was interrupted by the transient ADB loss and is preserved; a retry completed with status 0. It contains no KASLR/relocation evidence, and its bootloader matches are CP/modem text and an adbd request string. The one permitted dmesg attempt coincided with the disconnect, so dmesg accessibility remains inconclusive and was not retried. No permission workaround was used.

All raw command records and stderr are preserved under `docs/rmg-eze4/runtime-evidence/20260906T094426Z/raw/` and hashed in `evidence_sha256.txt`. Analysis artifacts are separate. No P0 label/address mapping was exposed, and all four collision labels remain unknown.

## Final verdict

`NON_INVASIVE_OBSERVATION_COMPLETE`
