# J2 experimental unit

One trial is exactly one supervisor attempt/child PID, not one supervisor session and not one boot.

## Boundaries and identity

- Start boundary: the parent successfully forks the child and immediately samples `CLOCK_MONOTONIC` into `started`. The child attempt-start line binds attempt ordinal, child PID, session, boot and trial identities.
- End boundary: the same child is reaped and its terminal class is recorded: exit 0, explicit nonzero exit, signal, or supervisor timeout followed by SIGKILL and reap. Missing reap evidence makes the trial inconclusive; missing identity/provenance makes it invalid.
- Pre-state: firmware/kernel/artifact and effective parameter gates pass; boot ID is fixed; the declared condition snapshot is stable; the app is foreground/not frozen; no other validation or parameter override is active; collector and clocks are ready.
- Post-state: child is reaped, terminal supervisor state is captured, raw files are closed and hashed, and dirty/writer/retry disposition is recorded. No assumption of safe retry follows from child termination.
- `experiment_id`: immutable campaign identifier `J2-TIMEOUT-<UTC-date>-<nonce>`.
- `session_id`: one authorized supervisor invocation and collection envelope; never reused after collector restart or identity loss.
- `boot_id`: SHA-256-derived identifier from a read-only boot-instance token plus kernel identity. Evidence from distinct boot IDs is never merged as one boot.
- `trial_id`: `<experiment_id>/<boot_id>/<session_id>/A<two-digit-attempt-ordinal>-P<child-pid>`. The tuple must be unique.
- `attempt_id`: session-local attempt ordinal plus child PID; ordinal reuse across sessions is allowed only because the full trial ID remains unique.

Attempts following dirty/writer state are not silently started. A retry, if the source permits one, is a new trial with a new child PID and ordinal and retains its attempt-history condition value.
