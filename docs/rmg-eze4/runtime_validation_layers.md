# Runtime-validation layers

The minimum layer is the lowest layer that could validate the parameter itself. Lower-layer observations may inform prerequisites without validating the value.

## Layer definitions

- **L0 — OFFLINE ONLY:** source, binary, configuration, image, and documentation evidence. No device access.
- **L1 — PASSIVE DEVICE OBSERVATION:** read-only stock-device properties, proc/sys exposure, and existing logs. No state-changing command.
- **L2 — BENIGN ACTIVE MEASUREMENT:** timing ordinary userspace operations or requesting ordinary diagnostic output without triggering the vulnerable path.
- **L3 — CONTROLLED KERNEL-PATH VALIDATION:** evidence from the parameter's actual consumer. It is outside Phase F and must not be inferred from L1/L2 prerequisites.

| Parameter(s) | Minimum layer | Evidence that would validate | Evidence that is insufficient |
|---|---|---|---|
| `ROOT_UMH_PATH` | L1 | Read-only metadata establishes whether the exact deployed path exists in the relevant future deployment state. | Existence of `/data/local/tmp` alone; the same path in ZG3 source. |
| `P0_FINGERPRINT_MIN_BEST`, `P0_FINGERPRINT_MIN_MARGIN` | L3 | Actual-path score and runner-up-margin evidence across relevant EZE4 states demonstrates the acceptance policy. | Clean Image simulations, fingerprint membership, or unrelated logs. |
| `SKB_SEND_SIZE` | L3 | Actual consumer/allocation evidence establishes the intended allocation/fragment geometry and path outcome. | `/proc/slabinfo` availability, total memory, or matching ZG3 source alone. |
| `SLIDE_WAIT_NSEC`, `SLIDE_REQUEUE_ARM_USEC`, `FOPS_ROUTE_COARSE_DELAY_USEC`, `FOPS_ROUTE_FINE_DELAY_TICKS` | L3 | Actual-path ordering and timing evidence establishes that required states occur with the configured values. | CPU topology, clock source, scheduler policy, or benign userspace latency alone. |
| `SLIDE_KERNEL_PAGE_SETUP_ATTEMPTS`, `FOPS_KERNEL_PAGE_SETUP_ATTEMPTS` | L3 | Actual-path attempt outcomes establish whether the caps admit setup completion. | General memory pressure or allocator metadata. |
| `DEFAULT_EXPLOIT_ATTEMPTS`, `DEFAULT_ATTEMPT_TIMEOUT_SEC`, `DEFAULT_P0_ATTEMPT_TIMEOUT_SEC` | L3 | Actual supervisor/path duration and terminal-state evidence establishes attempt-policy adequacy. | Uptime, ordinary command latency, or source bounds. |
| `SLIDE_KSNITCH_APPENDED_FUTEXES`, `SLIDE_KSNITCH_REPEAT_MEASUREMENT`, `SLIDE_KSNITCH_AVERAGE`, `SLIDE_KSNITCH_SCREEN_REPEAT`, `SLIDE_KSNITCH_SCREEN_AVERAGE` | L3 | Actual discovery signal, candidate separation, and resource outcome establishes the profile. | CPU count, memory totals, or benign futex timing. |
| `SKB_RECLAIM_SENDS`, `SLIDE_RECLAIM_SENDS` | L3 | Actual-path reclaim/coverage outcome establishes whether counts are adequate. | Socket limits, slab listings, or free-memory snapshots alone. |

L0 has already established source semantics and constraints for all 20. L1/L2 can characterize the environment, but only the pathname can be closed by passive observation. This plan supplies no L3 procedure.
