# Phase I evidence layout and immutability

```text
campaign/
  raw/
  normalized/
  analysis/
  reports/
  raw_sha256.txt
  campaign_manifest.json
```

`raw/` contains captured or synthetic source objects and is read-only to the analysis system. `normalized/` contains schema-valid observation records referencing raw objects. `analysis/` contains deterministic classifier outputs, exclusions, and rule versions. `reports/` contains human-readable summaries derived from analysis.

`raw_sha256.txt` is a host-side manifest with one SHA-256 digest and relative path per raw object. `campaign_manifest.json` links campaign/session/boot identities, the manifest digest, normalization version, analysis version, and every `RAW_EVIDENCE_REF`. Normalization never overwrites raw files. A digest mismatch, missing raw reference, duplicate path, or manifest ambiguity invalidates the affected measurement and triggers a stop rule.
