# Phase J2 Observation Schema Migration: v1 -> v2.1.0 -> v2.2.0 -> v2.2.1

## 1. Schema v1 Defects (Legacy J2)
- **Conflated Taxonomy**: `trial_outcome` mixed votes (`COMPATIBLE_VOTE`) with terminal lifecycle states (`QUALIFYING_COMPLETION`, `SUPERVISOR_OVERALL_TIMEOUT`).
- **Permissive Identity**: `artifact_identity` allowed arbitrary `{}` empty objects.
- **Untyped Records**: `state_transition_summary` and `observable_results` accepted arbitrary untyped objects.
- **Missing Fine-Grained Provenance**: Raw references supported only path and hash without line/byte/event selectors.

## 2. Schema v2.1.0 Semantic Regressions (Audited & Corrected in R1)
- **Timer Epoch Drift**: Erroneously modeled candidate duration starting at `P0_EXIT` instead of post-fork $t_0$.
- **Missing Candidate Identity**: Omitted explicit constants for `DEFAULT_ATTEMPT_TIMEOUT_SEC` and `2200`.
- **Conflated Firmware Fingerprint**: Treated `X510XXUCEZE4` as the full build fingerprint.
- **Non-Cryptographic Boot ID**: Permitted arbitrary UUID format instead of canonical 64-hex SHA-256 derivation.
- **Missing Typed Event Payloads**: Event schema lacked typed payload definitions matching the event grammar.
- **Premature Raw Binding**: Conflated pre-run run-package manifest with post-session raw evidence manifest.

## 3. Schema v2.2.0 Canonical Alignment
- **Watchdog Epoch Restored**: `post_fork_monotonic_ns` explicitly required as the sole duration start epoch $t_0$.
- **Explicit Candidate Identity**: `candidate_identity` mandates `candidate_parameter: "DEFAULT_ATTEMPT_TIMEOUT_SEC"` and `candidate_value: 2200`.
- **Decoupled Firmware Model**: Distinguishes `device_model` (`SM-X510`), `device_name` (`gts9fewifi`), `incremental_version` (`X510XXUCEZE4`), and full `build_fingerprint`.
- **Cryptographic Boot ID**: Mandates 64-character lowercase hex SHA-256 (`^[a-f0-9]{64}$`).
- **Typed Event Payloads**: Event transitions require typed `payload` conforming to Event Grammar v2.1.1.
- **Per-Event Boot Binding**: Every event in `state_transitions` binds `boot_id`, `session_id`, `trial_id`, `attempt_ordinal`, `pid` for foolproof boot mutation detection.
- **Package Manifest Separation**: Explicitly separates `run_package_identity` (bound in J3) from `raw_evidence_identity` (bound at session close).

## 4. Schema v2.2.1 Canonical Physical Identity Hardening (Phase J2.1-R1.1)
- **Previous Schema Version**: `2.2.0`
- **New Schema Version**: `2.2.1`
- **Identity Constraint Hardening**:
  - `build_fingerprint`: Enforces exact physical observed constant `"samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys"` (replacing permissive minimum-length check).
  - `kernel_identity`: Enforces exact physical observed constant `"5.15.189-android13-3-33478785"` (replacing permissive regex `/^5\.15\.189.*/`).
  - `device_model`: Preserves exact constant `"SM-X510"`.
  - `device_name`: Preserves exact constant `"gts9fewifi"`.
  - `incremental_version`: Preserves exact constant `"X510XXUCEZE4"`.
  - `stock_image_sha256`: Preserves exact constant `"ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9"`.
  - `security_patch`: Explicit Option B policy decision — retained as auxiliary baseline metadata (`2026-05-05`) grounded in Phase G observation, without adding an unnecessary required schema field.
- **Event Grammar Compatibility**: Event grammar version remains `2.1.1` as event grammar semantics are completely unchanged.

## 5. Migration & Compatibility Policy
- Version `2.2.1` is strictly backward-incompatible with v2.2.0, v2.1.0, and v1 due to strict identity pinning.
- All historical raw logs remain unchanged; offline validator and normalizers must target `2.2.1` schemas exclusively.
- Any record bearing synthetic or illustrative fingerprints (`UP1A.231005.007`, `gts9fewifixx`, generic `5.15.189.*`) will be rejected by Schema v2.2.1 and validator.
