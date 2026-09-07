# P02 first-trial preregistration — EZE4

Status: `BLOCKED_BEFORE_HARDWARE_TRIGGER` (2026-09-07).

This record is limited to P02. It authorizes neither P03+ nor reuse of the ZG3
downstream consumers.

## Reactive-path audit

| path | entrypoint | reads `pi_blocked_on` | dereferences waiter | state-changing | may sleep | may crash if stale | userspace reachable | privilege | classification |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| `kernel/locking/rtmutex_api.c:436-456` | `rt_mutex_adjust_pi()` | yes | yes | yes | no explicit sleep | yes | scheduler syscall, indirectly | own permitted downgrade: none | `REACTIVE_DESTRUCTIVE` |
| `kernel/sched/core.c:7450-7728` | `sched_setattr`, `sched_setscheduler`, `sched_setparam` | indirect | indirect | yes | no in fair downgrade | yes | yes | same UID; some changes need `CAP_SYS_NICE` | `REACTIVE_DESTRUCTIVE` |
| `kernel/locking/rtmutex.c:660-1000` | `rt_mutex_adjust_prio_chain()` | yes | yes | yes | preemptible | yes | indirect only | caller-dependent | `REACTIVE_DESTRUCTIVE` |
| `kernel/locking/rtmutex.c:1122-1200` | contended PI lock | owner state | yes | yes | yes | yes | futex PI | none normally | `REACTIVE_DESTRUCTIVE` |
| `kernel/locking/rtmutex.c:1453-1504` | waiter cleanup | owner state | yes | yes | operation may block | yes | futex timeout/signal | none | `REACTIVE_DESTRUCTIVE` |
| `kernel/sched/core.c:7037` | debug warning | yes | no | warning only | no | no | not independently | kernel | `UNREACHABLE` |
| `kernel/locking/rtmutex_api.c:467-472` | task-free debug check | yes | no | warning only | no | no | debug config disabled | kernel/debug | `UNREACHABLE` |

Invalid, denied, and scheduler no-op requests return through `unlock` before
`rt_mutex_adjust_pi()`. A permitted fair-priority change is the least invasive
userspace route that reaches the stale state, but after the null/equality tests
the first useful operation is `waiter->lock`. The function returns `void` and
does not expose the chain-walk result to userspace. Consequently its available
signals are ambiguous latency/hang or a crash; the latter is not P02 evidence.

No candidate met `DIFFERENTIAL_PROOF` or `STRONG_DIFFERENTIAL_EVIDENCE`.

## Fixed decision rule

`P02 PASS` requires exact EZE4 identity, trigger-path evidence, valid trial
integrity and C2 timeline, and a differential result absent from CONTROL that
is specifically attributable to the stale PI relationship rather than normal
futex behavior.

`P02 FAIL` requires the same valid trigger, observability and control gates,
with the experimental operation failing to show the preregistered difference.

`P02 INCONCLUSIVE` applies to any observation gap, uncertain trigger/timing,
control-reproducible result, crash without independent causal evidence,
ADB/device instability, or invalid thermal/runtime condition.

These rules are fixed before `TRL-P02-CONTROL-001` or `TRL-P02-EZE4-001`.

## Execution gate

```text
EZE4 identity valid:             YES
P02 trigger isolated:            DESIGN_ONLY
differential witness accepted:   NO
control completed:               NO
C2 timeline usable:              YES, with suspend as an explicit confounder
TRL-P02-EZE4-001 executed:        NO
```

The ZG3 harness is rejected as a build input because it always imports a
downstream consumer, P03+ dependencies, false-positive success booleans, and
non-terminating worker loops. A future accepted harness must be a standalone
single-source P02 binary, exact-identity-bound, finite, parameter-explicit, and
free of fake objects, reclaim, spray, pselect/FPSIMD/mcast consumers, KASLR,
credentials, SELinux changes, persistence, or P03+ code.
