# J2 closure audit

Date: 2026-09-06

## Initial state

The prior remediation had already corrected the original single-timeout masking
bug, isolated the historical Phase-I `engine.py`, selected Schema v2.2.1, and
added independent literal verdict assertions plus a 3-timeout/2-boot boundary.
The baseline J2-area discovery ran 71 tests successfully, including 56 active
J2 tests and 15 retained Phase-I/J0 historical tests.

Two active defects remained. `aggregate_campaign()` trusted callers to validate
records and accepted duplicate trial records. Separately, the
`invalid_timeout_not_counted` fixture carried an invalid trial with an illegal
`INCOMPATIBLE_VOTE`; the design test skipped validation for invalid-classified
records, hiding the inconsistency. The replay suite also imported production
verdict constants for expected values.

## Changes and confirmed semantics

- The aggregator now validates every record and returns `INVALID_EXPERIMENT` on
  malformed, missing-field, unsupported-schema, semantically invalid, duplicate
  trial, reordered-event, or duplicate-event evidence.
- The invalid fixture now uses `NO_VOTE`, and every fixture record is validated.
- Replay verdict oracles use literal strings rather than production constants.
- The analysis package exports the canonical aggregator/validator API; the
  Phase-I engine is explicit legacy only. Both unit and standalone AST guards
  reject a new engine dependency.
- `make verify-j2` is the single closure barrier.
- Current and historical status documents now have distinct scopes; superseded
  Phase-I/J1/J2 dry-run documents have visible banners.

## Oracle independence

Critical verdict and boundary assertions are `INDEPENDENT`: literals and
adversarial mutations are defined in tests, not imported from production.
Fixture generators remain `FIXTURE_MIRRORED` test-data construction aids, but
they are not verdict oracles. Cross-artifact identity checking remains a
`SAFE_MIRROR` because it compares separately retained authoritative evidence and
fails on divergence. No active critical J2 oracle is `SELF_CONFIRMING` or
`ERROR_CANCELLING`.

## Duplicated truth, engine split, and schema

Schema v2.2.1 and the E4 contract/decision table govern structure and semantics.
The validator mirrors exact identity constants under consistency control; test
oracles deliberately mirror semantic boundaries independently so mutations are
killed. `engine.py` and the Phase-I schema are historical and cannot enter the
J2 pipeline. Details are recorded in `DUPLICATED_TRUTH.csv`,
`TEST_ORACLE_MAP.csv`, and `ACTIVE_SUPERSEDED_REFERENCES.csv`.

## Test coverage

The gate covers timeout counts 1, 2, 3 and 4; concentrated/distributed timeout
placement; cross-condition contamination; invalid trials and invalid caps;
malformed/missing/unsupported input; duplicate trials/events; reordered events;
identity and schema rejection; event grammar; clock/confounder invariants;
partition minima; AST isolation; and canonical-document consistency.

## Final verdict

`J2 COMPLETE`. This is not a recovery, unlock, flashing, custom-kernel, Linux,
or hardware-readiness verdict.
