# Phase E — static closure

## Required summary

```text
TOTAL_PARAMETERS: 180
CONFIRMED_IDENTICAL: 143
CONFIRMED_CHANGED: 10
LEGACY_INACTIVE: 3
NOT_APPLICABLE: 3
RUNTIME_VALIDATION_REQUIRED: 20
STATICALLY_UNRESOLVED: 1

RUNTIME_CORRECTNESS_CRITICAL: 1
RUNTIME_RACE_SENSITIVE: 4
RUNTIME_PERFORMANCE_ONLY: 0
RUNTIME_OTHER: 15

PROBABLY_REUSABLE_BEFORE: 3
PROBABLY_REUSABLE_CLOSED: 3
PROBABLY_REUSABLE_REMAINING: 0

COLLISION_SLIDE_1E4000: INSUFFICIENT_EVIDENCE
COLLISION_SLIDE_1E8000: INSUFFICIENT_EVIDENCE
COLLISION_SLIDE_1EC000: INSUFFICIENT_EVIDENCE
COLLISION_SLIDE_1F0000: INSUFFICIENT_EVIDENCE

KASLR_KERNEL_GRANULARITY: 0x200000 generic virtual KASLR and protocol physical base; 0x4000 is proved only for the P0 oracle label domain
KASLR_KERNEL_RANGE: virtual offset zero with retained nokaslr; enabled generic formula is BIT(VA_BITS_MIN-3)..BIT(VA_BITS_MIN-3)+mask in 0x200000 steps; P0/bootloader range unknown
BOOTLOADER_BEHAVIOR_KNOWN: NO

P0_COLLISION_RISK: REACHABILITY_UNKNOWN; boot-specific P0 failure if any collision label occurs
P0_STATIC_BLOCKER: missing authoritative mapping/distribution between loader placement and P0 labels

TARGET_PARAMETERS_BLOCKING_OFFLINE_DRAFT: 0
TARGET_PARAMETERS_BLOCKING_RUNTIME: 21
```

## KASLR closure

The stock DT's `nokaslr` disables generic arm64 virtual KASLR despite the compiled configuration. Generic code and the stock Image binary use 2 MiB alignment. The Image header also requires a 2 MiB-aligned physical base because `text_offset=0`. The target's 16 KiB `SLIDE_KASLR_STEP` is directly established only as the P0 table and commit-check granularity. The loader algorithm and the relation between its placement and the P0 label are absent, so all four collision labels remain `INSUFFICIENT_EVIDENCE`, and every row in `p0_slide_reachability.csv` remains `UNKNOWN`.

The only gts9fewifi historical value found is ZG3 `0x140000`, recorded by commit `b7a854e` and repeated by PHASE3A. It is one result, lacks raw address-domain evidence, and supports no distribution claim.

## Runtime parameter necessity

**MUST_BE_VALIDATED_BEFORE_ANY_RUNTIME_TEST:** `SKB_SEND_SIZE`, `SLIDE_WAIT_NSEC`, `SLIDE_REQUEUE_ARM_USEC`, `FOPS_ROUTE_COARSE_DELAY_USEC`, and `FOPS_ROUTE_FINE_DELAY_TICKS`. Their semantics affect allocator geometry or required race ordering, so static reuse is not a correctness finding.

**CAN_START_WITH_ZG3_VALUE_BUT_UNCONFIRMED:** the two page-setup attempt limits, three supervisor attempt/timeout controls, five KernelSnitch population/measurement controls, and two reclaim-send counts. This grouping means only that source semantics do not prohibit reuse; it is not a safety or correctness confirmation.

**PERFORMANCE_ONLY:** none. Every listed value can at least change success rate, safe-abort timing, or path completion.

**INACTIVE_OR_CONDITIONAL:** none among the 17; all are present on the selected production path, though individual late-stage consumers are reached conditionally.

**UNKNOWN:** none at the source-semantics level. Runtime adequacy remains unvalidated for all 17.

The P0 acceptance thresholds and `ROOT_UMH_PATH` are readiness-classified `RUNTIME_VALIDATION_REQUIRED`. The path remains statically compatible/probably reusable as a string, but its deployment-state prerequisite is unconfirmed. See `PHASE_E_ERRATA.md`.

## Readiness decision

An offline, non-executable target draft can be prepared from the static parameter set, but Phase E did not create one. Runtime use remains blocked by the 20 validation-required rows and the firmware-specific fingerprint table's unresolved collision reachability. The sole statically unresolved target row is the diagnostic build label and does not block a draft.

## Final verdict

`STATIC_ANALYSIS_EXHAUSTED_RUNTIME_VALIDATION_REQUIRED`
