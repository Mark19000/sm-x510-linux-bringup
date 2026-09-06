# J2 supervisor and attempt state model

| State | Meaning |
|---|---|
| `GATED` | All hard GO gates evaluated; no child exists. |
| `SESSION_READY` | Identity, collector, clocks and condition are bound to a session. |
| `ATTEMPT_ACTIVE_PRE_SLIDE` | Child forked; monotonic timer running; active threshold is 1200 s while no forced offset and `slide_ready=0`. |
| `ATTEMPT_ACTIVE_OVERALL` | `slide_ready=1` or a forced offset exists; active threshold is 2200 s from the original post-fork start. |
| `CHILD_TERMINAL` | Child exited or was signalled; awaiting/undergoing interpretation. |
| `TIMEOUT_DECIDED` | Parent observed whole-second elapsed time at or above the active threshold and logged timeout. |
| `REAPED` | `waitpid` bound terminal status to the child PID. |
| `RETRY_DELAY` | Clean retry is permitted and the five-second delay is outside the trial. |
| `SESSION_TERMINAL` | Success, exhausted attempts, unsafe-retry refusal, or STOP. |

## Timeout transitions

| Transition | Initiating event | Clock start | Expected completion | Decision point | Cleanup/retry | Terminal interpretation |
|---|---|---|---|---|---|---|
| pre-slide watchdog | child remains active with `slide_ready=0` | parent post-fork monotonic sample | `slide_ready`, clean child terminal, or explicit failure | integer `now.tv_sec-start.tv_sec >= 1200` | SIGKILL then blocking reap; retry only if source safety gates allow | `EXPECTED_P0_TIMEOUT`, outside candidate compatibility; trial inconclusive for this parameter |
| overall watchdog | child active after `slide_ready` | same post-fork sample | recognized child terminal before 2195 s for affirmative headroom | integer elapsed `>=2200` | SIGKILL then blocking reap; safety gates govern retry | attributable repeated expiry may be `INCOMPATIBLE` |
| clean success | child exits 0 | same sample | success line and reap status 0 | no timeout decision | constructor returns; no retry | qualifying completion, not proof of exploit compatibility |
| explicit child failure | child exits nonzero | same sample | failure line and reap status | no timeout decision | retry only if clean and attempts remain | valid terminal observation; affirmative only if lifecycle coverage criterion is met |
| child crash/external child signal | signal termination | same sample | signal line and reap | no supervisor-timeout line | safety gates govern retry | distinguish from timeout; normally inconclusive for adequacy |
| unsafe state | dirty or writer flag after failure | same sample | refusal line | no new timeout decision | no retry; session ends | wrong-state terminal; experiment/session STOP if unexpected |

The following are mutually exclusive trial outcomes: `QUALIFYING_COMPLETION`, `EXPECTED_P0_TIMEOUT`, `SUPERVISOR_OVERALL_TIMEOUT`, `CHILD_EXPLICIT_FAILURE`, `CHILD_SIGNAL_FAILURE`, `WRONG_STATE_TERMINATION`, `EXTERNAL_INTERRUPTION`, and `MEASUREMENT_FAILURE`. A supervisor timeout requires the ordered pair of timeout line then signal-9/reap for the same PID. Signal 9 alone is not a timeout. Successful completion requires exit status 0 and the completion line. External interruption or missing terminal evidence cannot be inferred as either.
