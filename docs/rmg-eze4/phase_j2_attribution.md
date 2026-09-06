# J2 attribution and parameter isolation

## Held constant

Device/firmware/kernel identity, artifact hashes, target configuration, `DEFAULT_ATTEMPT_TIMEOUT_SEC=2200`, P0 timeout, attempt count, all race/resource/fingerprint values, app foreground policy, collector version, lifecycle labels and decision rules remain fixed. No environment override may alter the candidate or another target parameter.

## Intentionally varied

Only boot identity and the two predeclared E4 condition strata vary. Attempt ordinal is covered where a source-authorized clean retry naturally occurs; it is never forced by unsafe continuation.

## Merely observed

Uptime, thermal status/frequency caps, load, memory availability/pressure, scheduler context, ADB health, stage progress, child PID/status and dirty/writer disposition are covariates. They are not treated as tuned parameters.

## Attribution contaminants

Any parameter/configuration/artifact drift; unseparated pre-P0 time; freezer/suspension; external signal; child deadlock; thermal condition drift; collector loss; reboot; clock corruption; unrelated concurrent experiment; unsafe retry; or incomplete lifecycle coverage destroys causal attribution. Evidence of any such event is handled by the confounder, STOP and result contracts rather than averaged away.

The Phase I projection must set `CHANGED_PARAMETERS` to exactly `["DEFAULT_ATTEMPT_TIMEOUT_SEC"]`, `P0_DEPENDENCY` to `P0_INDEPENDENT`, and have no unresolved group dependency. This denotes the parameter under evaluation, not an authorization to change its value during the campaign.

No trial or campaign result validates `SLIDE_KSNITCH_APPENDED_FUTEXES`, `SKB_SEND_SIZE`, `SLIDE_WAIT_NSEC`, `SLIDE_REQUEUE_ARM_USEC`, `FOPS_ROUTE_COARSE_DELAY_USEC`, or `FOPS_ROUTE_FINE_DELAY_TICKS`. Any relevant side observation is tagged `INCIDENTAL_OBSERVATION_ONLY`, excluded from compatibility flags, and routed to a separate future review.
