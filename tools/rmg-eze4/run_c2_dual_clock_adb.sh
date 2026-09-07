#!/bin/sh
# Minimal three-command deployment for the local C2 observer:
#   1. adb push, 2. one detached adb shell launch, 3. one adb pull.
# There is deliberately no host-side polling loop and no wakelock command.
set -eu

ADB_BIN=${ADB_BIN:-adb}
ADB_SERIAL=${ADB_SERIAL:-}
OBSERVER_BIN=${OBSERVER_BIN:-}
TRIAL_ID=${TRIAL_ID:-}
TRIAL_PID=${TRIAL_PID:-}
DURATION_MS=${DURATION_MS:-60000}
INTERVAL_MS=${INTERVAL_MS:-200}
GRACE_MS=${GRACE_MS:-5000}
REMOTE_DIR=${REMOTE_DIR:-/data/local/tmp}
OUTPUT=${OUTPUT:-}

if [ -z "$OBSERVER_BIN" ] || [ -z "$TRIAL_ID" ] || [ -z "$TRIAL_PID" ] || [ -z "$OUTPUT" ]; then
	printf '%s\n' 'usage: OBSERVER_BIN=... TRIAL_ID=... TRIAL_PID=... OUTPUT=... [DURATION_MS=60000] [INTERVAL_MS=200] [ADB_SERIAL=...] run_c2_dual_clock_adb.sh' >&2
	exit 2
fi
case "$TRIAL_ID" in
	''|*[!A-Za-z0-9._-]*)
		printf '%s\n' 'TRIAL_ID contains unsafe characters' >&2
		exit 2
		;;
esac
case "$REMOTE_DIR" in
	/*|/data/local/tmp) ;;
	*)
		printf '%s\n' 'REMOTE_DIR must be an absolute path' >&2
		exit 2
		;;
esac
case "$TRIAL_PID" in
	''|*[!0-9]*)
		printf '%s\n' 'TRIAL_PID must be a positive decimal PID' >&2
		exit 2
		;;
esac

REMOTE_BIN="$REMOTE_DIR/c2_dual_clock_observer.$TRIAL_ID"
REMOTE_JSON="$REMOTE_DIR/c2_dual_clock_observer.$TRIAL_ID.jsonl"
WAIT_SECONDS=$(( (DURATION_MS + GRACE_MS + 999) / 1000 ))
if command -v sha256sum >/dev/null 2>&1; then
	OBSERVER_SHA256=$(sha256sum "$OBSERVER_BIN" | awk '{print $1}')
else
	OBSERVER_SHA256=$(shasum -a 256 "$OBSERVER_BIN" | awk '{print $1}')
fi

adb_run()
{
	if [ -n "$ADB_SERIAL" ]; then
		"$ADB_BIN" -s "$ADB_SERIAL" "$@"
	else
		"$ADB_BIN" "$@"
	fi
}

now_ms()
{
	python3 -c 'import time; print(int(time.time() * 1000))'
}

# The observer opens the result with O_EXCL.  The launch transaction also
# rejects an existing result before launching, so a failed new run cannot
# be followed by pulling stale JSON for the same trial ID.
adb_run push "$OBSERVER_BIN" "$REMOTE_BIN"

# chmod and self-detached launch are one adb shell transaction.
# Stdin, stdout, stderr and all inherited descriptors are detached/closed,
# and the parent exits 0 after emitting observer_pid=<pid>.
REMOTE_COMMAND="if [ -e '$REMOTE_JSON' ]; then exit 73; fi; chmod 700 '$REMOTE_BIN' && '$REMOTE_BIN' --detach --trial-id '$TRIAL_ID' --trial-pid '$TRIAL_PID' --duration-ms '$DURATION_MS' --interval-ms '$INTERVAL_MS' --output '$REMOTE_JSON'"

LAUNCH_START_MS=$(now_ms)
LAUNCH_OUTPUT=$(adb_run shell "$REMOTE_COMMAND")
LAUNCH_END_MS=$(now_ms)
LAUNCH_DURATION_MS=$(( LAUNCH_END_MS - LAUNCH_START_MS ))

OBSERVER_PID=$(printf '%s\n' "$LAUNCH_OUTPUT" | grep -E '^observer_pid=[0-9]+' | head -n1 | cut -d= -f2 || true)
if [ -z "$OBSERVER_PID" ]; then
	printf '%s\n' "Launch failed: observer_pid not reported by observer. Output was: $LAUNCH_OUTPUT" >&2
	exit 3
fi

# Validation: ensure the process is alive after ADB returns
LIVENESS_CHECK=$(adb_run shell "kill -0 $OBSERVER_PID && echo ALIVE || echo DEAD")
case "$LIVENESS_CHECK" in
	*ALIVE*) ;;
	*)
		printf '%s\n' "Validation failed: observer process $OBSERVER_PID is not alive after adb shell return" >&2
		exit 4
		;;
esac

# Pure local wait on host: strictly NO ADB commands during the observation window.
sleep "$WAIT_SECONDS"

# Retrieve result at the end
adb_run pull "$REMOTE_JSON" "$OUTPUT"

printf 'observer_output=%s\n' "$OUTPUT"
printf 'observer_sha256=%s\n' "$OBSERVER_SHA256"
printf 'remote_output=%s\n' "$REMOTE_JSON"
printf 'observer_pid=%s\n' "$OBSERVER_PID"
printf 'launch_duration_ms=%s\n' "$LAUNCH_DURATION_MS"
printf 'post_return_liveness=ALIVE\n'
printf 'adb_commands=4\n'
printf 'host_wait_seconds=%s\n' "$WAIT_SECONDS"

