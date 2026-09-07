# P02 Track B — EZE4 dependency slice and harness gate

Status: `P02_HARNESS_NOT_ACCEPTED_FAIL_CLOSED` (offline review, 2026-09-06).
No device, payload, exploit, or hardware trial was run for this track.

This is a narrow Track B artifact. It records the canonical P02 path, the
minimum dependency slice, the EZE4 binding evidence, and the pre-registered
decision rule. It does not claim that a trigger-only probe demonstrates P02.

## Identity and provenance gate

An accepted trial must bind all results to this exact runtime and stock image:

```text
model:       SM-X510
fingerprint: samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys
kernel:      5.15.189-android13-3-33478785
Image.stock: ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9
source tree: audit/eze4-source-intake/extracted/kernel
workspace revision at audit: 43d11c438e9c18db4b464bf5ef3c201738b4f473
Kernel.tar.gz: 2f3e18626011311a1450138e19b2091f7c177a5f8be6400a091f216800969b0f
```

The runtime values are in
`docs/rmg-eze4/runtime-evidence/20260906T094426Z/raw/01_product_model.txt`,
`03_build_fingerprint.txt`, and `06_uname.txt`. The stock image digest is
computed from `artifacts/stock/images/Image.stock`; source-derived types do not
replace this image binding. The extracted source directory is part of the
workspace rather than a separate Git checkout; the package digest above is the
source provenance anchor.

The retained reference is the ZG3 repository at commit
`b7a854e9f8cf36808ccccc0975ad7d3880ed923a` (same P02 sources at the checked
out `bcfe2b9cd84a776ce3b3bc5b8aa0c9b6f6d8b4f7` tree). The relevant reference
blob IDs are:

```text
slide_app.c: d70cc5cbb337bdec9459f4df4761fbe917e996da
fpsimd.c:    d410ca9cfc525c4ccab75ba16b572cf9312c0aad
mcast.c:     07973b867c5d39145c5c86f57449211755164e5c
pselect.c:   9358e259738bf7ae41368bb8921071931ba48ac2
fops.c:      30ae6ea2b739fca8d92d22ee68a2dd13ff9e7177
common.h:    7623ef3d4f2cf32058a50d494975fc2a8eb04c19
target.h:    8fb45592b9973b6908527131a857dc2b9e962c94
```

There is no EZE4 `target.h` or EZE4 `p0_fingerprint.h` in the reference tree.
The only X510 target header is `gts9fewifi-X510XXSEEZG3/target.h`, whose
fingerprint and symbols are ZG3-bound. It is not an EZE4 harness input.

## Canonical P02 reconstruction

The first unproven effect is not “a futex returned an error.” It is the
following lifetime transition:

1. `futex_wait_requeue_pi()` allocates `struct rt_mutex_waiter rt_waiter` on
   the waiting task's kernel stack and publishes `q.rt_waiter = &rt_waiter`
   (`audit/eze4-source-intake/extracted/kernel/kernel/futex/core.c:3428-3464`).
2. The waiting task sleeps on the non-PI futex. A different userspace thread
   calls `FUTEX_CMP_REQUEUE_PI`; the kernel calls
   `rt_mutex_start_proxy_lock(..., this->rt_waiter, this->task)`
   (`core.c:2385-2408`). The explicit arguments establish the proxy relation:
   `waiter->task` is the sleeping task, while `current` is the requeue caller.
3. On proxy deadlock/error, `rt_mutex_start_proxy_lock()` calls
   `remove_waiter(lock, waiter)` (`kernel/locking/rtmutex_api.c:322-334`).
4. The EZE4 source's `remove_waiter()` locks and clears `current->pi_blocked_on`
   (`kernel/locking/rtmutex.c:1459-1471`) instead of the `waiter->task`
   association. The target task can therefore retain a pointer to the
   stack-resident `rt_waiter` after its lifetime ends. This is the controlled
   stale waiter/task relationship that P02 must demonstrate.
5. The waiting side later reaches proxy-lock wait/cleanup and frees the local
   waiter (`core.c:3514-3524`). `EDEADLK`, `ETIMEDOUT`, or return from this
   routine describes control flow; none is evidence that the stale relation
   existed or was controlled.

The vulnerable source path is statically present in EZE4. Static presence and
the 53/53 matching target-relevant layout fields do not prove that a userspace
sequence reaches the stale state on the retail device.

## ZG3 dependency slice

### Strict P02 trigger core

The trigger core requires only ordinary userspace futex operations and thread
ordering:

```text
two distinct private u32 futex words
waiter: FUTEX_LOCK_PI(chain), FUTEX_WAIT_REQUEUE_PI(wait -> target)
owner:  FUTEX_LOCK_PI(target), then FUTEX_LOCK_PI(chain)
proxy:  FUTEX_CMP_REQUEUE_PI(wait -> target, nr_wake=1, nr_requeue=1,
                             cmpval=0 as passed by the retained wrapper)
waiter: FUTEX_UNLOCK_PI(chain) after the declared wake/abort state
```

The syscall operation values must come from the platform headers (`<linux/futex.h>`
and `SYS_futex`); no ZG3 numeric syscall literals are accepted. `SLIDE_WAIT_NSEC`
and `SLIDE_REQUEUE_ARM_USEC` are ZG3 empirical timing values, not EZE4 proofs.

### Code that is not in an isolated P02 harness

The retained `slide_child_trigger_write()` (`slide_app.c:403-459`) is not a
P02-only harness. It creates the downstream consumer, waits for its readiness,
and returns success only from `waiter_ok` plus `slide_stack_write_window` (or
`sched_ok`). Its consumer route is part of later memory manipulation:

* `slide_pselect_stack_copy()` requires `page_base`, `fake_lock`, and `fake_w0`
  and performs the pselect/`sched_setattr` route (`pselect.c:284-394`).
* `slide_fpsimd_stack_copy()` writes a fake waiter into the user signal frame
  and uses `tgkill`/`sched_setattr` (`fpsimd.c:23-134`). Its success boolean is
  only signal-frame parsing, user-memory write, and scheduler return status.
* The required `prepare_good_kernel_page()`/controlled-mm setup, fake
  `rt_mutex_waiter`/`task_struct`, pipe/SKB reclaim, P0 oracle, KASLR, FOPS and
  ASHMEM route are P03 or later. They must not be pulled into P02.

The ZG3 owner/waiter loops also leave threads alive forever
(`slide_app.c:232-235,266-269`). A timeout, hang, or supervisor kill is
`INCONCLUSIVE`, never a positive result.

## EZE4 binding and offset ledger

| Dependency | Classification | EZE4 evidence / gate |
|---|---|---|
| `futex_wait_requeue_pi()` stack waiter and proxy call | `UNCHANGED_EZE4` (static) | EZE4 source above; stock image/source identity bound. Runtime reachability remains untested. |
| `rt_mutex_start_proxy_lock()` and `remove_waiter()` | `UNCHANGED_EZE4` (vulnerability present) | EZE4 source lines cited above and stock-image audit. This is code presence, not stale-state evidence. |
| `struct rt_mutex_waiter` / `rt_mutex_base` | `REDERIVED_EZE4` | BTF/DWARF: `eze4_struct_layout.csv:320-330`; waiter size `0x58`, `lock->owner 0x18`. |
| `struct task_struct` PI fields and `struct rb_node` | `REDERIVED_EZE4` | `eze4_struct_layout.csv:4-6,212,215-217`; `pi_lock 0x884`, `pi_waiters 0x898`, `pi_top_task 0x8a8`, `pi_blocked_on 0x8b0`. |
| ARM64 FPSIMD signal ABI | `UNCHANGED_EZE4` (architectural/static) | EZE4 arm64 signal sources; not a P02 stale-state observable. |
| `SLIDE_WAIT_NSEC`, requeue arm/poll counts, route delays | `ZG3_ONLY` / `RUNTIME_DEPENDENT` | No EZE4 timing campaign; fail closed. |
| fake waiter/task, reclaimed page, pipe/SKB, FOPS, ASHMEM, P0/KASLR | `ZG3_ONLY` / `P03+` | Excluded from P02. |
| `KMALLOC_CACHES_OFF` | `ZG3_ONLY` / changed | ZG3 `0x01b04c70`; EZE4 stock `0x01b04bb0`. |
| `ANON_PIPE_BUF_OPS_OFF` | `ZG3_ONLY` / changed | ZG3 `0x01912de0`; EZE4 stock `0x01912d20`. |
| `ASHMEM_FOPS_OFF` | `ZG3_ONLY` / changed | ZG3 `0x01ab3c08`; EZE4 stock `0x01ab3b48`. |
| `SLIDE_NFULNL_LOGGER_NAME_OFF` | `ZG3_ONLY` / changed | ZG3 `0x017fdc14`; EZE4 stock `0x017fdb3c`. |

The four changed symbols are not needed by the strict futex trigger. Their
presence in a proposed “P02” build is a dependency-slice failure. No numeric
offset is compiled or accepted for this Track B artifact. If a future
kernel-state reader is proposed, every offset must be rederived from the exact
stock Image/BTF binding above and independently reviewed before use.

## Observable gate

No currently available ordinary userspace observable proves P02. The following
are explicitly insufficient:

```text
FUTEX_CMP_REQUEUE_PI -> -1/EDEADLK
FUTEX_WAIT_REQUEUE_PI -> -1/ETIMEDOUT
successful tgkill/SIGUSR2 delivery or FPSIMD record parsing
sched_setattr() success
absence of a crash, warning, reboot, or panic
/proc wchan/syscall state
```

These establish control-flow, signal, scheduler, or liveness facts only. The
generic scheduler tracepoint does not expose the identity/lifetime of
`waiter->task->pi_blocked_on`. A tracefs kprobe/BPF experiment would require
additional privilege/policy and kernel instrumentation; it would also need a
reviewed pointer/lifetime witness and could perturb the timing. No such
read-only, unprivileged, kernel-visible witness is available in this tree.

Therefore:

```text
trigger_isolated:      NO (current ZG3 trigger is coupled to downstream route)
EZE4_bound:            STATIC_ONLY (identity/source/image bound; no target build)
offsets_required:      none for a strict trigger-only probe
offsets_ready:         NO for any kernel-state reader or fake-payload route
success_observable:    NOT_AVAILABLE
P02_OBSERVABLE_READY:  false
```

Building the full ZG3 route would import P03+ and create a false-positive
`slide_stack_write_window`; stripping the route would leave no P02-specific
observable. The fail-closed decision is therefore to build neither as an
accepted P02 harness.

## Pre-registered decision rule

The classification is fixed before any future trial:

### `P02_PASS`

All of the following are required: exact identity/image binding; valid C2/C3
confounder coverage; complete labelled futex/proxy path; no policy denial,
crash, hang, timeout ambiguity, or offset ambiguity; and an independent,
kernel-visible witness that the proxy cleanup left the intended target task's
stale waiter relation and that the observed consequence is attributable to
that relation. No current userspace-only record can satisfy this criterion.

### `P02_FAIL`

Only after the same valid trigger and witness gates are satisfied, an
independent observation shows that the required stale relation is absent. A
normal `EDEADLK`, `ETIMEDOUT`, denied `sched_setattr`, missing signal frame,
or ordinary safe return is not `FAIL`.

### `P02_INCONCLUSIVE`

Any missing/partial C2 or C3 gate, identity mismatch, policy denial, missing
kernel witness, dependency-slice contamination, unexpected crash/reboot,
hang/supervisor timeout, missing stage, or ambiguous offset/path is
`INCONCLUSIVE` and must stop. It must never be upgraded to PASS because the
process exited cleanly.

## Track B verdict

```text
P02 trigger:       STATIC_PATH_IDENTIFIED
P02 harness:       NOT_ACCEPTED_FAIL_CLOSED
EZE4 offsets:      STRUCTURAL_ONLY
P02 observable:     NOT_READY
trial executed:    NO
pre-registered:    PASS / FAIL / INCONCLUSIVE (rules above)
current result:    INCONCLUSIVE (no valid runtime trial was authorized)
first blocker:     no independent kernel-visible P02 stale-relation witness
next action:       obtain an independently reviewed, non-invasive witness or
                   keep P02 untested; do not adapt/execute the ZG3 harness
```
