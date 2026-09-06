# Phase J2.1-R1 Raw Evidence & Provenance Contract

Evidence directory hierarchy:
```text
runtime-evidence/<experiment_id>/<session_id>/
├── raw/
│   ├── manifest.sha256
│   ├── session_identity.txt
│   ├── boot_identity.txt
│   ├── clock_calibration.jsonl
│   ├── T0001_condition_before.json
│   ├── T0001_supervisor.stdout
│   ├── T0001_supervisor.stderr
│   ├── T0001_events.jsonl
│   └── ...
├── normalized/
│   └── T0001_observation.json
├── analysis/
└── report/
```

---

## 1. Raw Provenance Selectors

Derived claims and observables must reference exact supporting raw content using one of three typed selector modes:

```json
// Mode 1: Line range for structured text logs
{
  "path": "raw/T0001_supervisor.stdout",
  "sha256": "4a7d...b3",
  "producer": "SUPERVISOR",
  "artifact_type": "TEXT_LOG",
  "selector": {
    "selector_type": "LINE_RANGE",
    "start": 104,
    "end": 108
  }
}

// Mode 2: Byte range for binary traces
{
  "path": "raw/T0001_trace.pcap",
  "sha256": "8f12...e0",
  "producer": "TARGET_CHILD",
  "artifact_type": "BINARY_TRACE",
  "selector": {
    "selector_type": "BYTE_RANGE",
    "start": 4096,
    "end": 8192
  }
}

// Mode 3: Event sequence range for structured event streams
{
  "path": "raw/T0001_events.jsonl",
  "sha256": "1c99...aa",
  "producer": "SYSTEM_LOG",
  "artifact_type": "TEXT_LOG",
  "selector": {
    "selector_type": "EVENT_SEQUENCE_RANGE",
    "start": 12,
    "end": 15
  }
}
```

---

## 2. Deterministic Manifest Closure Algorithm

To eliminate manifest self-reference recursion and ensure cryptographic immutability:

1. **Stop Telemetry Capture**: Close all write pipes, terminate background monitors, flush log streams.
2. **Sync Filesystems**: Issue `syncfs` / `fsync` across target storage partitions.
3. **Enumerate Raw Files**: Enumerate all regular files under `raw/` relative to `raw/` root in strict lexicographical UTF-8 byte order.
4. **Exclude Manifest**: The manifest file itself (`manifest.sha256`) and temporary files (`*.tmp`) are strictly excluded from enumeration.
5. **Compute SHA-256**: Compute canonical lowercase hexadecimal SHA-256 for each enumerated file.
6. **Write Temporary Manifest**: Write canonical format:
   ```text
   <sha256_hex_lowercase>  <relative_path_posix>\n
   ```
   to `raw/.manifest.tmp`.
7. **Fsync & Atomic Move**: `fsync(raw/.manifest.tmp)` and atomically rename `raw/.manifest.tmp` $\to$ `raw/manifest.sha256`.
8. **Seal Session**: Compute `raw_session_manifest_sha256 = SHA256(raw/manifest.sha256)` and record it in `session_closed.json`.
9. **Lock Files**: Set all files in `raw/` to read-only (`chmod -R a-w raw/`). Any subsequent modification immediately fails integrity checks.

---

## 3. Separation of Run Package vs Raw Session Manifest

- **`run_package_manifest`**: An immutable bundle of binaries, scripts, schemas, and condition threshold profiles bound in **Phase J3** before any execution occurs.
- **`raw_session_manifest`**: An immutable catalog of telemetry generated at **runtime** and sealed only *after* evidence collection finishes. Its hash cannot exist prior to session completion.
