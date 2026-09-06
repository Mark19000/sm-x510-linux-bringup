# Phase I canonical observation record

The canonical record is a JSON object validated by `tools/rmg-eze4/schemas/observation.schema.json`. It is a normalized index over immutable evidence, never a replacement for raw evidence.

Required identity fields are `SESSION_ID`, `BOOT_ID`, `CONDITION_ID`, `TRIAL_ID`, `MEASUREMENT_ID`, `GROUP_ID`, and `PARAMETER`. Measurement fields are `OBSERVABLE`, `TIMESTAMP_HOST`, optional `TIMESTAMP_DEVICE_IF_AVAILABLE`, `SOURCE`, `RAW_EVIDENCE_REF`, `ENVIRONMENT`, `EXPECTED_CRITERION`, `OBSERVED_VALUE`, `RESULT`, `CONFIDENCE`, `CONFOUNDERS`, and `NOTES`. Analysis-control fields include `EVIDENCE_LEVEL`, `OBSERVABLE_AVAILABLE`, `CHANGED_PARAMETERS`, prerequisite state, P0 dependency, baseline match, and explicit synthetic provenance.

`RESULT` supports `COMPATIBLE`, `INCOMPATIBLE`, `INCONCLUSIVE`, `SAFE_ABORT`, `MEASUREMENT_INVALID`, and `NOT_OBSERVED`. A safe abort is an observed terminal event, not automatically evidence of compatibility or incompatibility. The offline classifier uses explicit criterion flags and attribution metadata; it does not infer semantic success from arbitrary numeric values.

`RAW_EVIDENCE_REF` is mandatory and resolves through the campaign manifest to an immutable raw object and SHA-256 digest. Normalized records may summarize or parse a measurement but must preserve this reference. A missing reference makes attribution invalid.

All Phase I fixtures set `SYNTHETIC: true`. Future approved passive records require an explicit provenance policy outside this synthetic harness; the library itself accepts only caller-supplied records and performs no collection.
