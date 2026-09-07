/*
 * C2-OBS-02: local dual-clock observer for the EZE4 runtime.
 *
 * This is deliberately a small, unprivileged program.  It only calls
 * clock_gettime(2), clock_getres(2), nanosleep(2), and read-only stdio for
 * /proc/<pid>/cgroup and cgroup.events.  It never requests a wakelock, changes
 * scheduling or affinity, accesses a device node, or changes a power or
 * security setting.
 *
 * The result is JSON Lines.  By default stdout is used; --output selects an
 * explicit output file.  The output stream is fully buffered so that the
 * observer does not turn every 100--200 ms sample into a storage wakeup.  A
 * caller that needs a durable stream may redirect stdout explicitly, but the
 * normal deployment passes --output and retrieves the closed file once.
 *
 * The EZE4 source intake establishes the clock model used here:
 *   include/linux/timekeeping.h:28-35: the default ktime reference is
 *     CLOCK_MONOTONIC and excludes suspend;
 *   include/linux/timekeeping.h:87-99: ktime_get_boottime includes suspend;
 *   kernel/time/posix-stubs.c:69-91: clock_gettime dispatches the two IDs to
 *     those accessors;
 *   kernel/time/hrtimer.c:76-106: timer bases bind MONOTONIC and BOOTTIME to
 *     their respective accessors.
 *
 * The observer sleeps on a relative nanosleep (the normal POSIX sleep clock
 * is CLOCK_MONOTONIC), never on a BOOTTIME alarm.  Therefore it does not ask
 * the kernel to wake the device from suspend.  BOOTTIME is used only for the
 * trial end condition and for the measurement itself; after resume the next
 * sample records the accumulated divergence.
 */

#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

#define SCHEMA_VERSION "c2-dual-clock-obs.v1"
#define DEFAULT_INTERVAL_MS 200U
#define MIN_INTERVAL_MS 100U
#define MAX_INTERVAL_MS 200U
#define MIN_DURATION_MS 100U
#define MAX_DURATION_MS (24U * 60U * 60U * 1000U)
#define JSON_BUFFER_BYTES (64U * 1024U)
#define CGROUP_BUFFER_BYTES 4096U
#define BOOT_ID_BYTES 128U

enum cgroup_status {
	CGROUP_NOT_REQUESTED = 0,
	CGROUP_AVAILABLE,
	CGROUP_PERMISSION_DENIED,
	CGROUP_UNAVAILABLE,
	CGROUP_AMBIGUOUS,
	CGROUP_MALFORMED,
	CGROUP_READ_ERROR,
	CGROUP_PID_EXITED,
	CGROUP_PID_REUSED,
	CGROUP_DRIFT,
};

struct cgroup_binding {
	int requested;
	pid_t pid;
	char path[PATH_MAX];
	FILE *stream;
	enum cgroup_status bind_status;
	uint64_t pid_starttime_ticks;
};

struct clock_sample {
	uint64_t monotonic_ns;
	uint64_t boottime_ns;
	uint64_t process_cpu_ns;
	int process_cpu_valid;
	uint64_t pair_span_ns;
};

struct options {
	unsigned int duration_ms;
	unsigned int interval_ms;
	const char *output_path;
	const char *trial_id;
	int trial_pid_set;
	pid_t trial_pid;
	int detach;
};

static void usage(const char *argv0)
{
	fprintf(stderr,
		"usage: %s --duration-ms N [--interval-ms 100..200] "
		"[--trial-id ID] [--trial-pid PID] [--output PATH|-] [--detach]\n",
		argv0);
}

static int parse_unsigned(const char *text, unsigned int *value)
{
	char *end = NULL;
	unsigned long parsed;

	if (text == NULL || *text == '\0' || *text == '-')
		return -1;
	errno = 0;
	parsed = strtoul(text, &end, 10);
	if (errno != 0 || end == text || *end != '\0' ||
		parsed > UINT_MAX)
		return -1;
	*value = (unsigned int)parsed;
	return 0;
}

static int parse_pid(const char *text, pid_t *value)
{
	unsigned int parsed;

	if (parse_unsigned(text, &parsed) != 0 || parsed == 0 ||
		parsed > (unsigned int)INT_MAX)
		return -1;
	*value = (pid_t)parsed;
	return 0;
}

static int valid_token(const char *text)
{
	size_t length;
	size_t i;

	if (text == NULL)
		return 0;
	length = strlen(text);
	if (length == 0 || length > 63)
		return 0;
	for (i = 0; i < length; ++i) {
		unsigned char c = (unsigned char)text[i];
		if (!(c == '.' || c == '_' || c == '-' ||
			(c >= '0' && c <= '9') ||
			(c >= 'A' && c <= 'Z') ||
			(c >= 'a' && c <= 'z')))
			return 0;
	}
	return 1;
}

static int parse_options(int argc, char **argv, struct options *options)
{
	int i;

	memset(options, 0, sizeof(*options));
	options->interval_ms = DEFAULT_INTERVAL_MS;
	options->trial_id = "UNSPECIFIED";
	for (i = 1; i < argc; ++i) {
		if (strcmp(argv[i], "--duration-ms") == 0 && i + 1 < argc) {
			if (parse_unsigned(argv[++i], &options->duration_ms) != 0)
				return -1;
		} else if (strcmp(argv[i], "--interval-ms") == 0 && i + 1 < argc) {
			if (parse_unsigned(argv[++i], &options->interval_ms) != 0)
				return -1;
		} else if (strcmp(argv[i], "--output") == 0 && i + 1 < argc) {
			options->output_path = argv[++i];
		} else if (strcmp(argv[i], "--trial-id") == 0 && i + 1 < argc) {
			options->trial_id = argv[++i];
		} else if (strcmp(argv[i], "--trial-pid") == 0 && i + 1 < argc) {
			if (parse_pid(argv[++i], &options->trial_pid) != 0)
				return -1;
			options->trial_pid_set = 1;
		} else if (strcmp(argv[i], "--detach") == 0) {
			options->detach = 1;
		} else if (strcmp(argv[i], "--help") == 0 ||
			   strcmp(argv[i], "-h") == 0) {
			return 1;
		} else {
			return -1;
		}
	}
	if (options->duration_ms < MIN_DURATION_MS ||
		options->duration_ms > MAX_DURATION_MS ||
		options->interval_ms < MIN_INTERVAL_MS ||
		options->interval_ms > MAX_INTERVAL_MS ||
		!valid_token(options->trial_id))
		return -1;
	if (options->output_path != NULL &&
		strcmp(options->output_path, "-") != 0 &&
		options->output_path[0] == '\0')
		return -1;
	if (options->detach && (options->output_path == NULL ||
		strcmp(options->output_path, "-") == 0))
		return -1;
	return 0;
}

static int timespec_to_ns(const struct timespec *value, uint64_t *result)
{
	uint64_t seconds;

	if (value == NULL || value->tv_sec < 0 || value->tv_nsec < 0 ||
		value->tv_nsec >= 1000000000L)
		return -1;
	seconds = (uint64_t)value->tv_sec;
	if (seconds > (UINT64_MAX - (uint64_t)value->tv_nsec) / 1000000000ULL)
		return -1;
	*result = seconds * 1000000000ULL + (uint64_t)value->tv_nsec;
	return 0;
}

static int difference_u64(uint64_t newer, uint64_t older, uint64_t *result)
{
	if (newer < older)
		return -1;
	*result = newer - older;
	return 0;
}

static int signed_difference(uint64_t left, uint64_t right, int64_t *result)
{
	if (left >= right) {
		uint64_t difference = left - right;
		if (difference > (uint64_t)INT64_MAX)
			return -1;
		*result = (int64_t)difference;
		return 0;
	}
	if (right - left > (uint64_t)INT64_MAX)
		return -1;
	*result = -(int64_t)(right - left);
	return 0;
}

static int clock_resolution_ns(clockid_t clock_id, uint64_t *result)
{
	struct timespec resolution;

	if (clock_getres(clock_id, &resolution) != 0)
		return -1;
	return timespec_to_ns(&resolution, result);
}

static int read_clock_sample(struct clock_sample *sample)
{
	struct timespec mono_before;
	struct timespec boot;
	struct timespec mono_after;
	uint64_t mono_before_ns;
	uint64_t boot_ns;
	uint64_t mono_after_ns;
	uint64_t process_cpu_ns;

	if (clock_gettime(CLOCK_MONOTONIC, &mono_before) != 0 ||
		clock_gettime(CLOCK_BOOTTIME, &boot) != 0 ||
		clock_gettime(CLOCK_MONOTONIC, &mono_after) != 0 ||
		timespec_to_ns(&mono_before, &mono_before_ns) != 0 ||
		timespec_to_ns(&boot, &boot_ns) != 0 ||
		timespec_to_ns(&mono_after, &mono_after_ns) != 0 ||
		mono_after_ns < mono_before_ns)
		return -1;

	sample->monotonic_ns = mono_before_ns +
		(mono_after_ns - mono_before_ns) / 2ULL;
	sample->boottime_ns = boot_ns;
	sample->pair_span_ns = mono_after_ns - mono_before_ns;
	sample->process_cpu_valid =
		clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &mono_before) == 0 &&
		timespec_to_ns(&mono_before, &process_cpu_ns) == 0;
	sample->process_cpu_ns = sample->process_cpu_valid ? process_cpu_ns : 0;
	return 0;
}

static const char *cgroup_status_name(enum cgroup_status status)
{
	switch (status) {
	case CGROUP_AVAILABLE:
		return "AVAILABLE";
	case CGROUP_PERMISSION_DENIED:
		return "PERMISSION_DENIED";
	case CGROUP_UNAVAILABLE:
		return "UNAVAILABLE";
	case CGROUP_AMBIGUOUS:
		return "AMBIGUOUS";
	case CGROUP_MALFORMED:
		return "MALFORMED";
	case CGROUP_READ_ERROR:
		return "READ_ERROR";
	case CGROUP_PID_EXITED:
		return "PID_EXITED";
	case CGROUP_PID_REUSED:
		return "PID_REUSED";
	case CGROUP_DRIFT:
		return "CGROUP_DRIFT";
	case CGROUP_NOT_REQUESTED:
	default:
		return "NOT_REQUESTED";
	}
}

static enum cgroup_status errno_cgroup_status(void)
{
	if (errno == EACCES || errno == EPERM)
		return CGROUP_PERMISSION_DENIED;
	if (errno == ENOENT || errno == ESRCH || errno == ENOTDIR)
		return CGROUP_UNAVAILABLE;
	return CGROUP_READ_ERROR;
}

static int safe_relative_cgroup(const char *relative)
{
	const char *cursor = relative;

	if (relative == NULL || *relative == '\0')
		return 1;
	if (*relative != '/')
		return 0;
	while (*cursor != '\0') {
		if (*cursor == '\n' || *cursor == '\r' ||
			*cursor == '\\' || *cursor == '\0')
			return 0;
		if (cursor[0] == '.' && cursor[1] == '.' &&
			(cursor[2] == '/' || cursor[2] == '\0'))
			return 0;
		++cursor;
	}
	return 1;
}

static enum cgroup_status read_unified_cgroup_path(pid_t pid, char *path,
						 size_t path_size)
{
	char proc_path[64];
	char line[PATH_MAX];
	char relative[PATH_MAX];
	FILE *proc_file;
	unsigned int matches = 0;

	if (snprintf(proc_path, sizeof(proc_path), "/proc/%ld/cgroup",
		     (long)pid) >= (int)sizeof(proc_path))
		return CGROUP_MALFORMED;
	proc_file = fopen(proc_path, "r");
	if (proc_file == NULL)
		return errno_cgroup_status();
	while (fgets(line, sizeof(line), proc_file) != NULL) {
		char *marker;
		char *newline;

		if (strncmp(line, "0::", 3) != 0)
			continue;
		marker = line + 3;
		newline = strpbrk(marker, "\r\n");
		if (newline != NULL)
			*newline = '\0';
		if (!safe_relative_cgroup(marker) || strlen(marker) >= sizeof(relative)) {
			fclose(proc_file);
			return CGROUP_MALFORMED;
		}
		if (matches++ == 0)
			(void)snprintf(relative, sizeof(relative), "%s", marker);
	}
	fclose(proc_file);
	if (matches != 1)
		return matches == 0 ? CGROUP_UNAVAILABLE : CGROUP_AMBIGUOUS;
	if (strcmp(relative, "/") == 0 || relative[0] == '\0') {
		if (snprintf(path, path_size, "/sys/fs/cgroup/cgroup.events") >=
			(int)path_size)
			return CGROUP_MALFORMED;
	} else if (snprintf(path, path_size,
			   "/sys/fs/cgroup%s/cgroup.events", relative) >=
		   (int)path_size)
		return CGROUP_MALFORMED;
	return CGROUP_AVAILABLE;
}

static enum cgroup_status read_pid_starttime(pid_t pid, uint64_t *starttime)
{
	char proc_path[64];
	char line[PATH_MAX];
	char *right_paren;
	char *token;
	char *saveptr = NULL;
	FILE *proc_file;
	unsigned int field;
	char *end = NULL;
	unsigned long long parsed;

	if (snprintf(proc_path, sizeof(proc_path), "/proc/%ld/stat", (long)pid) >=
		(int)sizeof(proc_path))
		return CGROUP_MALFORMED;
	proc_file = fopen(proc_path, "r");
	if (proc_file == NULL)
		return errno_cgroup_status();
	if (fgets(line, sizeof(line), proc_file) == NULL) {
		enum cgroup_status status = ferror(proc_file) ?
			CGROUP_READ_ERROR : CGROUP_PID_EXITED;
		fclose(proc_file);
		return status;
	}
	fclose(proc_file);
	right_paren = strrchr(line, ')');
	if (right_paren == NULL || right_paren[1] != ' ')
		return CGROUP_MALFORMED;
	token = strtok_r(right_paren + 2, " \n", &saveptr); /* field 3 */
	if (token == NULL)
		return CGROUP_MALFORMED;
	for (field = 4; field <= 22; ++field) {
		token = strtok_r(NULL, " \n", &saveptr);
		if (token == NULL)
			return CGROUP_MALFORMED;
		if (field == 22) {
			errno = 0;
			parsed = strtoull(token, &end, 10);
			if (errno != 0 || end == token || *end != '\0' ||
				parsed > UINT64_MAX)
				return CGROUP_MALFORMED;
			*starttime = (uint64_t)parsed;
		}
	}
	return CGROUP_AVAILABLE;
}

static enum cgroup_status validate_binding(const struct cgroup_binding *binding)
{
	char current_path[PATH_MAX];
	uint64_t current_starttime;
	enum cgroup_status status;

	status = read_pid_starttime(binding->pid, &current_starttime);
	if (status != CGROUP_AVAILABLE)
		return status == CGROUP_UNAVAILABLE ? CGROUP_PID_EXITED : status;
	if (current_starttime != binding->pid_starttime_ticks)
		return CGROUP_PID_REUSED;
	status = read_unified_cgroup_path(binding->pid, current_path,
						 sizeof(current_path));
	if (status != CGROUP_AVAILABLE)
		return status;
	if (strcmp(current_path, binding->path) != 0)
		return CGROUP_DRIFT;
	return CGROUP_AVAILABLE;
}

static enum cgroup_status bind_cgroup(struct cgroup_binding *binding,
					      pid_t pid)
{
	enum cgroup_status status;

	memset(binding, 0, sizeof(*binding));
	binding->requested = 1;
	binding->pid = pid;
	status = read_unified_cgroup_path(pid, binding->path,
						 sizeof(binding->path));
	if (status != CGROUP_AVAILABLE)
		return binding->bind_status = status;
	binding->stream = fopen(binding->path, "r");
	if (binding->stream == NULL)
		return binding->bind_status = errno_cgroup_status();
	status = read_pid_starttime(pid, &binding->pid_starttime_ticks);
	if (status != CGROUP_AVAILABLE) {
		fclose(binding->stream);
		binding->stream = NULL;
		return binding->bind_status = status;
	}
	binding->bind_status = CGROUP_AVAILABLE;
	return binding->bind_status;
}

static enum cgroup_status read_cgroup(struct cgroup_binding *binding,
					      int *frozen, int *populated)
{
	char line[CGROUP_BUFFER_BYTES];
	int saw_frozen = 0;
	int saw_populated = 0;

	*frozen = -1;
	*populated = -1;
	if (!binding->requested)
		return CGROUP_NOT_REQUESTED;
	if (binding->bind_status != CGROUP_AVAILABLE || binding->stream == NULL)
		return binding->bind_status;
	{
		enum cgroup_status binding_status = validate_binding(binding);
		if (binding_status != CGROUP_AVAILABLE)
			return binding_status;
	}
	if (fseek(binding->stream, 0L, SEEK_SET) != 0) {
		clearerr(binding->stream);
		/* Some pseudo-files do not support seek; reopen the bound path. */
		fclose(binding->stream);
		binding->stream = fopen(binding->path, "r");
		if (binding->stream == NULL)
			return errno_cgroup_status();
	}
	clearerr(binding->stream);
	while (fgets(line, sizeof(line), binding->stream) != NULL) {
		int value;
		if (sscanf(line, "frozen %d", &value) == 1 &&
			(value == 0 || value == 1)) {
			*frozen = value;
			saw_frozen = 1;
		} else if (sscanf(line, "populated %d", &value) == 1 &&
			(value == 0 || value == 1)) {
			*populated = value;
			saw_populated = 1;
		}
	}
	if (ferror(binding->stream)) {
		clearerr(binding->stream);
		return CGROUP_READ_ERROR;
	}
	if (!saw_frozen || !saw_populated)
		return CGROUP_MALFORMED;
	return CGROUP_AVAILABLE;
}

static void close_cgroup(struct cgroup_binding *binding)
{
	if (binding->stream != NULL) {
		fclose(binding->stream);
		binding->stream = NULL;
	}
}

static void json_string(FILE *stream, const char *value)
{
	const unsigned char *cursor = (const unsigned char *)value;

	fputc('"', stream);
	while (cursor != NULL && *cursor != '\0') {
		switch (*cursor) {
		case '"':
		case '\\':
			fputc('\\', stream);
			fputc(*cursor, stream);
			break;
		case '\n':
			fputs("\\n", stream);
			break;
		case '\r':
			fputs("\\r", stream);
			break;
		case '\t':
			fputs("\\t", stream);
			break;
		default:
			if (*cursor < 0x20)
				fprintf(stream, "\\u%04x", (unsigned int)*cursor);
			else
				fputc(*cursor, stream);
			break;
		}
		++cursor;
	}
	fputc('"', stream);
}

static void json_optional_u64(FILE *stream, uint64_t value, int valid)
{
	if (valid)
		fprintf(stream, "%" PRIu64, value);
	else
		fputs("null", stream);
}

static void json_optional_i64(FILE *stream, int64_t value, int valid)
{
	if (valid)
		fprintf(stream, "%" PRId64, value);
	else
		fputs("null", stream);
}

static int read_boot_id(char *value, size_t value_size)
{
	FILE *stream;
	char *newline;

	if (value == NULL || value_size < 2)
		return -1;
	value[0] = '\0';
	stream = fopen("/proc/sys/kernel/random/boot_id", "r");
	if (stream == NULL)
		return -1;
	if (fgets(value, (int)value_size, stream) == NULL) {
		fclose(stream);
		value[0] = '\0';
		return -1;
	}
	fclose(stream);
	newline = strpbrk(value, "\r\n");
	if (newline != NULL)
		*newline = '\0';
	if (value[0] == '\0' || strlen(value) >= value_size - 1)
		return -1;
	return 0;
}

static void emit_boot_fields(FILE *stream, const char *boot_id,
				     const char *boot_status)
{
	fputs(",\"boot_id_read_status\":", stream);
	json_string(stream, boot_status);
	fputs(",\"boot_id\":", stream);
	if (boot_id != NULL && boot_id[0] != '\0')
		json_string(stream, boot_id);
	else
		fputs("null", stream);
}

static int sample_offset(const struct clock_sample *sample, int64_t *offset)
{
	return signed_difference(sample->boottime_ns, sample->monotonic_ns,
				 offset);
}

static void emit_prefix(FILE *stream, const char *record_type,
				const char *trial_id, uint64_t sequence,
				const struct clock_sample *sample, int64_t offset,
				int offset_valid, uint64_t sampling_gap,
				int sampling_gap_valid, uint64_t elapsed_mono,
				int elapsed_mono_valid, uint64_t elapsed_boot,
				int elapsed_boot_valid, int64_t suspend_delta,
				int suspend_delta_valid, const char *boot_id,
				const char *boot_status)
{
	fputs("{\"schema\":\"" SCHEMA_VERSION "\",\"record_type\":",
		stream);
	json_string(stream, record_type);
	fputs(",\"trial_id\":", stream);
	json_string(stream, trial_id);
	fprintf(stream, ",\"sequence\":%" PRIu64, sequence);
	fprintf(stream, ",\"clock_monotonic_ns\":%" PRIu64,
		 sample->monotonic_ns);
	fprintf(stream, ",\"clock_boottime_ns\":%" PRIu64,
		 sample->boottime_ns);
	fputs(",\"boottime_minus_monotonic_ns\":", stream);
	json_optional_i64(stream, offset, offset_valid);
	fputs(",\"sampling_gap_ns\":", stream);
	json_optional_u64(stream, sampling_gap, sampling_gap_valid);
	fputs(",\"elapsed_monotonic_ns\":", stream);
	json_optional_u64(stream, elapsed_mono, elapsed_mono_valid);
	fputs(",\"elapsed_boottime_ns\":", stream);
	json_optional_u64(stream, elapsed_boot, elapsed_boot_valid);
	fputs(",\"suspend_delta_ns\":", stream);
	json_optional_i64(stream, suspend_delta, suspend_delta_valid);
	fprintf(stream, ",\"pair_read_span_ns\":%" PRIu64,
		 sample->pair_span_ns);
	fputs(",\"process_cpu_ns\":", stream);
	json_optional_u64(stream, sample->process_cpu_ns,
				 sample->process_cpu_valid);
	emit_boot_fields(stream, boot_id, boot_status);
}

static void emit_cgroup_fields(FILE *stream,
				       enum cgroup_status read_status,
				       int frozen, int populated)
{
	fputs(",\"cgroup_read_status\":", stream);
	json_string(stream, cgroup_status_name(read_status));
	fputs(",\"cgroup_frozen\":", stream);
	if (frozen == 0 || frozen == 1)
		fprintf(stream, "%d", frozen);
	else
		fputs("null", stream);
	fputs(",\"cgroup_populated\":", stream);
	if (populated == 0 || populated == 1)
		fprintf(stream, "%d", populated);
	else
		fputs("null", stream);
}

static int emit_metadata(FILE *stream, const struct options *options,
				 const struct cgroup_binding *binding,
				 enum cgroup_status cgroup_read_status, int frozen,
				 int populated, const struct clock_sample *start,
				 uint64_t mono_resolution, uint64_t boot_resolution,
				 int process_cpu_clock_available, int64_t offset,
				 int offset_valid, const char *boot_id,
				 const char *boot_status)
{
	fputs("{\"schema\":\"" SCHEMA_VERSION
		"\",\"record_type\":\"metadata\",\"trial_id\":",
		stream);
	json_string(stream, options->trial_id);
	fputs(",\"sequence\":0,\"clock_monotonic_ns\":", stream);
	fprintf(stream, "%" PRIu64, start->monotonic_ns);
	fputs(",\"clock_boottime_ns\":", stream);
	fprintf(stream, "%" PRIu64, start->boottime_ns);
	fputs(",\"boottime_minus_monotonic_ns\":", stream);
	json_optional_i64(stream, offset, offset_valid);
	fputs(",\"sampling_gap_ns\":null,\"elapsed_monotonic_ns\":0",
		stream);
	fputs(",\"elapsed_boottime_ns\":0,\"suspend_delta_ns\":0",
		stream);
	fprintf(stream, ",\"pair_read_span_ns\":%" PRIu64,
		 start->pair_span_ns);
	fputs(",\"process_cpu_ns\":", stream);
	json_optional_u64(stream, start->process_cpu_ns,
				 start->process_cpu_valid);
	fprintf(stream, ",\"clock_monotonic_resolution_ns\":%" PRIu64,
		 mono_resolution);
	fprintf(stream, ",\"clock_boottime_resolution_ns\":%" PRIu64,
		 boot_resolution);
	fprintf(stream, ",\"interval_ms\":%u,\"duration_ms\":%u",
		 options->interval_ms, options->duration_ms);
	fprintf(stream, ",\"output_buffer_bytes\":%u,\"output_flush_mode\":\"fclose\"",
		 JSON_BUFFER_BYTES);
	fprintf(stream, ",\"pid\":%ld,\"process_cpu_clock_available\":%s",
		 (long)getpid(), process_cpu_clock_available ? "true" : "false");
	fputs(",\"sleep_clock\":\"CLOCK_MONOTONIC\",\"end_clock\":\"CLOCK_BOOTTIME\"",
		stream);
	fputs(",\"trial_pid\":", stream);
	if (options->trial_pid_set)
		fprintf(stream, "%ld", (long)options->trial_pid);
	else
		fputs("null", stream);
	fputs(",\"cgroup_binding_status\":", stream);
	json_string(stream, cgroup_status_name(binding->bind_status));
	fputs(",\"cgroup_path\":", stream);
	if (binding->bind_status == CGROUP_AVAILABLE)
		json_string(stream, binding->path);
	else
		fputs("null", stream);
	fputs(",\"pid_starttime_ticks\":", stream);
	if (binding->bind_status == CGROUP_AVAILABLE)
		fprintf(stream, "%" PRIu64, binding->pid_starttime_ticks);
	else
		fputs("null", stream);
	emit_cgroup_fields(stream, cgroup_read_status, frozen, populated);
	emit_boot_fields(stream, boot_id, boot_status);
	fputs("}\n", stream);
	return ferror(stream) ? -1 : 0;
}

static int emit_sample(FILE *stream, const struct options *options,
			       const struct cgroup_binding *binding,
			       enum cgroup_status cgroup_read_status, int frozen,
			       int populated, uint64_t sequence,
			       const struct clock_sample *sample,
			       const struct clock_sample *start,
			       const struct clock_sample *previous,
			       int64_t start_offset, int start_offset_valid,
			       const char *boot_id, const char *boot_status)
{
	uint64_t sampling_gap = 0;
	uint64_t elapsed_mono = 0;
	uint64_t elapsed_boot = 0;
	int64_t offset = 0;
	int64_t suspend_delta = 0;
	int sampling_gap_valid =
		difference_u64(sample->monotonic_ns, previous->monotonic_ns,
			       &sampling_gap) == 0;
	int elapsed_mono_valid =
		difference_u64(sample->monotonic_ns, start->monotonic_ns,
			       &elapsed_mono) == 0;
	int elapsed_boot_valid =
		difference_u64(sample->boottime_ns, start->boottime_ns,
			       &elapsed_boot) == 0;
	int offset_valid = sample_offset(sample, &offset) == 0;
	int suspend_delta_valid = 0;

	/* A negative offset is retained, but the relative delta is invalid. */
	if (offset_valid && start_offset_valid && offset >= 0 &&
		start_offset >= 0) {
		uint64_t current = (uint64_t)offset;
		uint64_t initial = (uint64_t)start_offset;
		suspend_delta_valid = signed_difference(current, initial,
							&suspend_delta) == 0;
	}
	emit_prefix(stream, "sample", options->trial_id, sequence, sample,
		    offset, offset_valid, sampling_gap, sampling_gap_valid,
		    elapsed_mono, elapsed_mono_valid, elapsed_boot, elapsed_boot_valid,
		    suspend_delta, suspend_delta_valid, boot_id, boot_status);
	emit_cgroup_fields(stream, cgroup_read_status, frozen, populated);
	fputs("}\n", stream);
	(void)binding;
	return ferror(stream) ? -1 : 0;
}

static int emit_end(FILE *stream, const struct options *options,
			    const struct cgroup_binding *binding,
			    enum cgroup_status cgroup_read_status, int frozen,
			    int populated, uint64_t sequence,
			    const struct clock_sample *sample,
			    const struct clock_sample *start,
			    const struct clock_sample *previous,
			    int64_t start_offset, int start_offset_valid,
			    uint64_t sample_count, const char *boot_id,
			    const char *boot_status)
{
	uint64_t sampling_gap = 0;
	uint64_t elapsed_mono = 0;
	uint64_t elapsed_boot = 0;
	int64_t offset = 0;
	int64_t suspend_delta = 0;
	int sampling_gap_valid =
		difference_u64(sample->monotonic_ns, previous->monotonic_ns,
			       &sampling_gap) == 0;
	int elapsed_mono_valid =
		difference_u64(sample->monotonic_ns, start->monotonic_ns,
			       &elapsed_mono) == 0;
	int elapsed_boot_valid =
		difference_u64(sample->boottime_ns, start->boottime_ns,
			       &elapsed_boot) == 0;
	int offset_valid = sample_offset(sample, &offset) == 0;
	int suspend_delta_valid = 0;
	if (offset_valid && start_offset_valid && offset >= 0 &&
		start_offset >= 0)
		suspend_delta_valid = signed_difference((uint64_t)offset,
							(uint64_t)start_offset,
							&suspend_delta) == 0;
	emit_prefix(stream, "end", options->trial_id, sequence, sample,
		    offset, offset_valid, sampling_gap, sampling_gap_valid,
		    elapsed_mono, elapsed_mono_valid, elapsed_boot, elapsed_boot_valid,
		    suspend_delta, suspend_delta_valid, boot_id, boot_status);
	emit_cgroup_fields(stream, cgroup_read_status, frozen, populated);
	{
		long output_position = ftell(stream);
		fputs(",\"sample_count\":", stream);
		fprintf(stream, "%" PRIu64, sample_count);
		fputs(",\"output_buffer_bytes\":", stream);
		fprintf(stream, "%u", JSON_BUFFER_BYTES);
		fputs(",\"output_flush_mode\":\"fclose\",\"output_file_position_before_end_bytes\":",
		       stream);
		if (output_position >= 0)
			fprintf(stream, "%ld", output_position);
		else
			fputs("null", stream);
		fputs(",\"termination\":\"completed\"}\n", stream);
	}
	(void)binding;
	return ferror(stream) ? -1 : 0;
}

static int sleep_interval_ms(unsigned int interval_ms)
{
	struct timespec request;
	struct timespec remaining;

	request.tv_sec = (time_t)(interval_ms / 1000U);
	request.tv_nsec = (long)(interval_ms % 1000U) * 1000000L;
	while (nanosleep(&request, &remaining) != 0) {
		if (errno != EINTR)
			return -1;
		request = remaining;
	}
	return 0;
}

static FILE *open_output(const char *path)
{
	int fd;
	FILE *stream;

	if (path == NULL || strcmp(path, "-") == 0)
		return stdout;
	fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
	if (fd < 0)
		return NULL;
	stream = fdopen(fd, "w");
	if (stream == NULL) {
		close(fd);
		return NULL;
	}
	return stream;
}

static int detach_process(void)
{
	int pipefd[2];
	pid_t pid;
	pid_t grandchild_pid;
	ssize_t bytes_read;
	int dev_null_fd;
	int max_fd;
	int fd;

	if (pipe(pipefd) != 0)
		return -1;

	pid = fork();
	if (pid < 0) {
		close(pipefd[0]);
		close(pipefd[1]);
		return -1;
	}
	if (pid > 0) {
		/*
		 * Parent process: wait for grandchild to report its PID,
		 * emit the PID to stdout for caller synchronization,
		 * and exit 0 immediately so the launching shell returns.
		 */
		close(pipefd[1]);
		grandchild_pid = 0;
		bytes_read = read(pipefd[0], &grandchild_pid, sizeof(grandchild_pid));
		close(pipefd[0]);
		if (bytes_read == (ssize_t)sizeof(grandchild_pid) && grandchild_pid > 0) {
			printf("observer_pid=%ld\n", (long)grandchild_pid);
			fflush(stdout);
		}
		_exit(0);
	}

	/* First child: create new session / process group */
	close(pipefd[0]);
	if (setsid() < 0) {
		close(pipefd[1]);
		_exit(2);
	}

	/* Second fork: prevent process from acquiring a controlling terminal */
	pid = fork();
	if (pid < 0) {
		close(pipefd[1]);
		_exit(2);
	}
	if (pid > 0) {
		/* First child exits immediately */
		close(pipefd[1]);
		_exit(0);
	}

	/*
	 * Grandchild process: running as an orphaned daemon adopted by init.
	 * Notify parent of grandchild PID before closing descriptors.
	 */
	grandchild_pid = getpid();
	if (write(pipefd[1], &grandchild_pid, sizeof(grandchild_pid)) !=
	    (ssize_t)sizeof(grandchild_pid)) {
		close(pipefd[1]);
		_exit(2);
	}
	close(pipefd[1]);

	/* Redirect stdin, stdout, stderr to /dev/null */
	dev_null_fd = open("/dev/null", O_RDWR);
	if (dev_null_fd < 0)
		_exit(2);

	if (dup2(dev_null_fd, STDIN_FILENO) < 0 ||
	    dup2(dev_null_fd, STDOUT_FILENO) < 0 ||
	    dup2(dev_null_fd, STDERR_FILENO) < 0) {
		close(dev_null_fd);
		_exit(2);
	}
	if (dev_null_fd > STDERR_FILENO)
		close(dev_null_fd);

	/* Close all other inherited file descriptors */
	max_fd = (int)sysconf(_SC_OPEN_MAX);
	if (max_fd < 0 || max_fd > 4096)
		max_fd = 4096;
	for (fd = 3; fd < max_fd; ++fd) {
		close(fd);
	}

	return 0;
}

int main(int argc, char **argv)
{
	struct options options;
	struct cgroup_binding binding;
	struct clock_sample start;
	struct clock_sample previous;
	struct clock_sample current;
	uint64_t mono_resolution;
	uint64_t boot_resolution;
	uint64_t sequence = 1;
	uint64_t sample_count = 0;
	uint64_t duration_ns;
	uint64_t elapsed_boot;
	int64_t start_offset;
	int start_offset_valid;
	int process_cpu_clock_available;
	int frozen = -1;
	int populated = -1;
	int parse_result;
	char boot_id[BOOT_ID_BYTES];
	char current_boot_id[BOOT_ID_BYTES];
	const char *boot_status;
	const char *current_boot_status;
	int boot_id_valid;
	int current_boot_id_valid;
	FILE *output;
	enum cgroup_status cgroup_read_status;

	parse_result = parse_options(argc, argv, &options);
	if (parse_result != 0) {
		if (parse_result < 0)
			usage(argv[0]);
		return parse_result < 0 ? 2 : 0;
	}
	if (options.detach) {
		if (detach_process() != 0) {
			fprintf(stderr, "C2 dual-clock observer: detach failed\n");
			return 2;
		}
	}
	if (read_clock_sample(&start) != 0) {
		fprintf(stderr, "C2 dual-clock observer: clock_gettime failed\n");
		return 2;
	}
	if (clock_resolution_ns(CLOCK_MONOTONIC, &mono_resolution) != 0 ||
		clock_resolution_ns(CLOCK_BOOTTIME, &boot_resolution) != 0) {
		fprintf(stderr, "C2 dual-clock observer: clock_getres failed\n");
		return 2;
	}
	boot_id_valid = read_boot_id(boot_id, sizeof(boot_id)) == 0;
	if (!boot_id_valid)
		boot_id[0] = '\0';
	boot_status = boot_id_valid ? "AVAILABLE" : "UNAVAILABLE";
	process_cpu_clock_available = start.process_cpu_valid;
	start_offset_valid = sample_offset(&start, &start_offset) == 0;
	memset(&binding, 0, sizeof(binding));
	if (options.trial_pid_set)
		(void)bind_cgroup(&binding, options.trial_pid);
	else
		binding.bind_status = CGROUP_NOT_REQUESTED;
	if (binding.bind_status == CGROUP_AVAILABLE)
		cgroup_read_status = read_cgroup(&binding, &frozen, &populated);
	else
		cgroup_read_status = binding.bind_status;

	output = open_output(options.output_path);
	if (output == NULL) {
		fprintf(stderr, "C2 dual-clock observer: cannot open explicit output: %s\n",
			strerror(errno));
		close_cgroup(&binding);
		return 2;
	}
	/* Full buffering limits observer-induced storage activity. */
	{
		static char output_buffer[JSON_BUFFER_BYTES];
		if (setvbuf(output, output_buffer, _IOFBF, sizeof(output_buffer)) != 0)
			goto output_error;
	}
	if (emit_metadata(output, &options, &binding, cgroup_read_status,
			  frozen, populated, &start, mono_resolution, boot_resolution,
			  process_cpu_clock_available, start_offset, start_offset_valid,
			  boot_id, boot_status) != 0)
		goto output_error;
	previous = start;
	duration_ns = (uint64_t)options.duration_ms * 1000000ULL;
	for (;;) {
		if (sleep_interval_ms(options.interval_ms) != 0)
			goto output_error;
		if (read_clock_sample(&current) != 0)
			goto output_error;
		cgroup_read_status = read_cgroup(&binding, &frozen, &populated);
		current_boot_id_valid = read_boot_id(current_boot_id,
							 sizeof(current_boot_id)) == 0;
		if (!current_boot_id_valid) {
			current_boot_id[0] = '\0';
			current_boot_status = "UNAVAILABLE";
		}
		else if (!boot_id_valid || strcmp(current_boot_id, boot_id) != 0)
			current_boot_status = "MISMATCH";
		else
			current_boot_status = "AVAILABLE";
		if (emit_sample(output, &options, &binding, cgroup_read_status,
				frozen, populated, sequence++, &current, &start,
				&previous, start_offset, start_offset_valid, current_boot_id,
				current_boot_status) != 0)
			goto output_error;
		++sample_count;
		previous = current;
		if (difference_u64(current.boottime_ns, start.boottime_ns,
				  &elapsed_boot) != 0 || elapsed_boot >= duration_ns)
			break;
	}
	/* The end record is another local pair and is part of the audited span. */
	if (read_clock_sample(&current) != 0)
		goto output_error;
	cgroup_read_status = read_cgroup(&binding, &frozen, &populated);
	current_boot_id_valid = read_boot_id(current_boot_id,
						     sizeof(current_boot_id)) == 0;
	if (!current_boot_id_valid) {
		current_boot_id[0] = '\0';
		current_boot_status = "UNAVAILABLE";
	}
	else if (!boot_id_valid || strcmp(current_boot_id, boot_id) != 0)
		current_boot_status = "MISMATCH";
	else
		current_boot_status = "AVAILABLE";
	if (emit_end(output, &options, &binding, cgroup_read_status, frozen,
			 populated, sequence, &current, &start, &previous, start_offset,
			 start_offset_valid, sample_count, current_boot_id,
			 current_boot_status) != 0)
		goto output_error;
	{
		int close_status = fclose(output);
		output = NULL;
		if (close_status != 0) {
			close_cgroup(&binding);
			fprintf(stderr, "C2 dual-clock observer: output close failed\n");
			return 2;
		}
	}
	close_cgroup(&binding);
	return 0;

output_error:
	if (output != NULL && output != stdout)
		fclose(output);
	else if (output == stdout)
		fflush(output);
	close_cgroup(&binding);
	fprintf(stderr, "C2 dual-clock observer: output or sampling failed\n");
	return 2;
}
