# Phase G2 independent review

## Scope and method

This review was derived from the repository's static source documents and the raw records under `runtime-evidence/20260906T094426Z/raw/`. Phase G and its generated analysis files were consulted only after the independent findings below had been established. No device or hardware access, compilation, payload execution, privileged operation, or state-changing action was performed.

## Evidence integrity

Independent SHA-256 calculation covered all 46 regular files in `raw/`. The manifest also contains exactly 46 entries. Every calculated digest matches the corresponding entry in `evidence_sha256.txt`; there are no missing, extra, or mismatched raw files.

## Independently derived runtime baseline

The successful property and identity records all return status 0 and establish:

- model `SM-X510`;
- device `gts9fewifi`;
- fingerprint `samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys`;
- incremental build `X510XXUCEZE4`;
- security patch `2026-05-05`;
- kernel `Linux localhost 5.15.189-android13-3-33478785 #1 SMP PREEMPT Fri May 15 20:06:17 KST 2026 aarch64 Toybox`.

This confirms the intended EZE4 SM-X510/gts9fewifi baseline and refines the static record with the exact EEA fingerprint and stock kernel build identity. The connection evidence shows an initial host-side ADB daemon/startup failure followed by a successful `device` result; it does not weaken the later identity records.

## Protected inputs and logs

| Capture | Return status | stderr | Independent result |
|---|---:|---|---|
| `/proc/cmdline` | 1 | `cat: /proc/cmdline: Permission denied` | Effective cmdline unavailable. Runtime presence of `nokaslr` is unknown. |
| `/proc/bootconfig` | 1 | `cat: /proc/bootconfig: Permission denied` | Effective bootconfig unavailable. |
| sole `dmesg` attempt | 1 | `adb: no devices/emulators found` | The attempt did not reach a readable/denied kernel-log result; dmesg accessibility and contents remain inconclusive. |
| first all-buffer logcat | 255 | empty | Partial capture terminated during the transient disconnect. It is not a successful complete capture. |
| retry all-buffer logcat | 0 | empty | Successful capture, but no useful AP-kernel placement evidence. |

Neither logcat record contains `kaslr` or `relocat` matches. Broader words such as `physical`, `slide`, address-like values, and `P0` occur extensively in ordinary framework, UI, application, hardware-service, key-management, or modem contexts; none correlates a payload P0 label with an AP-kernel physical load address or virtual displacement. The only literal `bootloader` records are `cbd: boot: Start CP bootloader`, which concerns the communications processor/modem, and an adbd service request for `getprop ro.bootloader`; neither describes the application-processor loader's kernel-placement decision. Therefore the captures contain no genuine KASLR state, relocation, P0, physical-placement, or relevant Samsung AP-bootloader evidence. Absence from logcat is not proof that such state does not exist.

## ROOT_UMH_PATH

The first pathname observation failed because ADB was disconnected (status 1, `adb: no devices/emulators found`). The retry reached the device and returned status 1 with `ls: /data/local/tmp/cve-2026-43499-root: No such file or directory`. Thus `/data/local/tmp/cve-2026-43499-root` is `NOT_FOUND` on this untouched stock deployment. This validates only current-file absence and confirms that existence is deployment state; it does not validate pathname compatibility in a future deployment.

## Independent post-L1 classification of all 20 parameters

The governing rule is that prerequisite observations do not validate an L3 value. No actual consumer/kernel path was executed. Consequently none of the 19 L3 parameters is validated. CPU topology (`0-7`), memory totals/availability, and a single load snapshot can partially inform environmental prerequisites where relevant, but cannot promote any configured value. The sole L1 pathname parameter is only partially informed because current absence is known while future deployment compatibility is not.

| # | Parameter | Minimum layer | Post-L1 classification | Independent basis |
|---:|---|---|---|---|
| 1 | `SLIDE_KERNEL_PAGE_SETUP_ATTEMPTS` | L3 | `PARTIALLY_INFORMED` | Memory/CPU environment observed; no actual setup-attempt outcomes. |
| 2 | `FOPS_KERNEL_PAGE_SETUP_ATTEMPTS` | L3 | `PARTIALLY_INFORMED` | Memory/CPU environment observed; no actual setup-attempt outcomes. |
| 3 | `FOPS_ROUTE_COARSE_DELAY_USEC` | L3 | `PARTIALLY_INFORMED` | CPU/load context observed; no actual-path ordering or timing. |
| 4 | `FOPS_ROUTE_FINE_DELAY_TICKS` | L3 | `PARTIALLY_INFORMED` | CPU/load context observed; no actual-path ordering or timing. |
| 5 | `DEFAULT_EXPLOIT_ATTEMPTS` | L3 | `UNCHANGED` | No consumer, success-distribution, or terminal-state evidence. |
| 6 | `DEFAULT_ATTEMPT_TIMEOUT_SEC` | L3 | `UNCHANGED` | No actual supervisor/path duration evidence. |
| 7 | `DEFAULT_P0_ATTEMPT_TIMEOUT_SEC` | L3 | `UNCHANGED` | No actual P0-path duration evidence. |
| 8 | `SLIDE_WAIT_NSEC` | L3 | `PARTIALLY_INFORMED` | CPU/load context observed; no waiter-state/timing evidence. |
| 9 | `SLIDE_REQUEUE_ARM_USEC` | L3 | `PARTIALLY_INFORMED` | CPU/load context observed; no requeue-ordering evidence. |
| 10 | `SLIDE_KSNITCH_APPENDED_FUTEXES` | L3 | `PARTIALLY_INFORMED` | Memory/CPU prerequisites observed; no discovery/resource outcome. |
| 11 | `SLIDE_KSNITCH_REPEAT_MEASUREMENT` | L3 | `PARTIALLY_INFORMED` | Environment observed; no discovery signal/noise evidence. |
| 12 | `SLIDE_KSNITCH_AVERAGE` | L3 | `PARTIALLY_INFORMED` | Environment observed; no discovery signal/noise evidence. |
| 13 | `SLIDE_KSNITCH_SCREEN_REPEAT` | L3 | `PARTIALLY_INFORMED` | Environment observed; no candidate-separation evidence. |
| 14 | `SLIDE_KSNITCH_SCREEN_AVERAGE` | L3 | `PARTIALLY_INFORMED` | Environment observed; no candidate-separation evidence. |
| 15 | `SKB_SEND_SIZE` | L3 | `PARTIALLY_INFORMED` | General memory/CPU context observed; no allocation/fragment geometry. |
| 16 | `SKB_RECLAIM_SENDS` | L3 | `PARTIALLY_INFORMED` | General memory context observed; no reclaim/coverage outcome. |
| 17 | `SLIDE_RECLAIM_SENDS` | L3 | `PARTIALLY_INFORMED` | General memory context observed; no reclaim/coverage outcome. |
| 18 | `P0_FINGERPRINT_MIN_BEST` | L3 | `UNCHANGED` | No actual-path score evidence. |
| 19 | `P0_FINGERPRINT_MIN_MARGIN` | L3 | `UNCHANGED` | No actual-path winner/runner-up margin evidence. |
| 20 | `ROOT_UMH_PATH` | L1 | `PARTIALLY_INFORMED` | Exact path currently absent; future deployment compatibility untested. |

Totals are therefore: `VALIDATED=0`, `PARTIALLY_INFORMED=15`, `UNCHANGED=5`, and `CONTRADICTED=0`.

## P0, loader, and collision conclusions

Static evidence establishes that the 125 P0 labels enumerate `0x000000..0x1f0000` at `0x4000` oracle/search granularity. It does not establish that these labels are literal generic arm64 virtual KASLR offsets or physical Image addresses. Static DT evidence retains `nokaslr`, while the generic virtual path and documented Image placement use 2 MiB alignment; the missing transformation is a Samsung loader/P0-domain question. Runtime evidence could not confirm effective `nokaslr` and exposed no label/address correlation, selector, range, entropy, exclusion, or distribution. The loader mapping therefore remains open.

For `0x1e4000`, `0x1e8000`, `0x1ec000`, and `0x1f0000`, table membership and in-Image offsets do not prove hardware reachability. All four remain `UNKNOWN` / `INSUFFICIENT_EVIDENCE`. If any is reached, static control-flow evidence says the current P0 policy rejects it, restores the sampled pages, marks/retains dirty state, and offers no compiled same-boot fallback; repeated attempts in that boot do not resolve the deterministic fingerprint collision. The single historical ZG3 `0x140000` observation neither proves nor excludes the four collision placements.

## Static/runtime reconciliation and comparison with Phase G

No runtime result contradicts the static model. Runtime confirms the target identity and kernel lineage, refines previously unavailable build metadata, and confirms that the helper's existence is deployment-dependent. Permission denial prevents runtime confirmation of the static retained-DT `nokaslr` fact, but lack of confirmation is not a contradiction. The log and dmesg outcomes add no P0/loader evidence.

After independent derivation, comparison with `PHASE_G.md`, `runtime_validation_after_L1.csv`, `STATIC_RUNTIME_RECONCILIATION.md`, and `analysis/P0_LOADER_REVIEW.md` found their material claims, per-parameter classifications, totals, and boundaries consistent with the raw evidence and validation-layer rules. No erratum requiring correction was identified.

PHASE_G_CONFIRMED_BY_INDEPENDENT_REVIEW
