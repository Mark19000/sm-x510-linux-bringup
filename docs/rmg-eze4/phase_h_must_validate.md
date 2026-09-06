# Phase H must-validate analysis

These five values remain mandatory validation gates. This analysis defines falsifiable assumptions and does not recommend replacements.

## `SKB_SEND_SIZE = 0x8e80`

The encoded assumption is that this exact requested length produces the allocation/fragment geometry required by the direct `page.c`, `pipe.c`, and `fops.c` consumers while satisfying exact send-length checks. Reuse remains compatible only if repeated direct observations on EZE4 show that geometry and the expected consumer state. One unambiguous incompatible allocation class, fragment layout, or attributable safe path failure falsifies reuse. Memory pressure, slab state, socket behavior, reclaim counts, and CPU concurrency matter. Geometry can be isolated at the direct consumer if those conditions are recorded. A wrong value is expected to cause **allocator mismatch** or **safe abort/path failure**; broader behavior is unknown without consumer evidence.

## `SLIDE_WAIT_NSEC = 2000000000L`

The assumption is that the wait remains active long enough for the required PI waiter state, without expiry changing the intended ordering. Compatibility requires the state transition to precede expiry across the defined CPU/load scope. Repeated expiry-before-state observations falsify reuse. Scheduler policy, CPU topology/affinity, frequency, contention, load, and setup completion matter. It can be isolated only with waiter-state and expiry events separately observable. A wrong value is expected to cause **incorrect path ordering** and may produce a **safe abort**.

## `SLIDE_REQUEUE_ARM_USEC = 20000`

The assumption is that requeue arming occurs after the prerequisite waiter state and inside the required ordering window. Compatibility requires repeated correctly ordered state transitions across the defined conditions. A systematic attributable early/late arm falsifies reuse. CPU/load/scheduler conditions and `SLIDE_WAIT_NSEC` are dependencies. It is isolatable only after waiter establishment is validated and events are separately labelled. A wrong value is expected to cause **incorrect path ordering** or **reduced reliability**.

## `FOPS_ROUTE_COARSE_DELAY_USEC = 50000`

The assumption is that coarse placement puts execution near the fops route state window so the fine sweep can cover it. Compatibility requires state-labelled traces to place the configured coarse baseline within reach of the fine offsets across the defined conditions. Repeated systematic window misses attributable to coarse placement falsify reuse. CPU topology, scheduling, load, frequency, counter behavior, and setup state matter. It cannot be fully isolated from the fine sweep using aggregate outcomes; direct coarse/state timing can isolate it. A wrong value is expected to cause **incorrect path ordering** or **reduced reliability**.

## `FOPS_ROUTE_FINE_DELAY_TICKS`

Current sequence: `0ULL; 0x10ULL; 0x20ULL; 0x30ULL; 0x40ULL; 0x60ULL; 0x80ULL; 0x18ULL`.

The assumption is that the finite, attempt-indexed counter-offset sweep intersects the live state window around the coarse delay. Compatibility requires at least one listed offset to repeatedly reach that state across the defined condition scope, with every relevant offset receiving sufficient coverage. Repeated evidence that the window lies outside the sweep falsifies reuse. Counter source/rate, migration, CPU/load/scheduler behavior, coarse delay, and supervisor attempt coverage matter. It is isolatable only with per-offset state timing and a stable coarse baseline. A wrong value is expected to cause **reduced reliability** or **incorrect path ordering**.
