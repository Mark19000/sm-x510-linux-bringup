# J2 synthetic dry-run report

The fixtures in `tools/rmg-eze4/tests/fixtures/phase_j2_timeout_scenarios.json` were run through the existing Phase I `engine.analyze_observations()` interface by `test_phase_j2_design.py`. The complete Phase I and J0 test modules were run in the same invocation. No device, payload, build, or network interface was used.

| Fixture | Expected | Actual | Result |
|---|---|---|---|
| clean compatible | `COMPATIBLE` | `COMPATIBLE` | PASS |
| clean incompatible | `INCOMPATIBLE` | `INCOMPATIBLE` | PASS |
| single timeout below required E4 | `INCONCLUSIVE` | `INCONCLUSIVE` | PASS |
| late completion/no headroom | `INCONCLUSIVE` | `INCONCLUSIVE` | PASS |
| high jitter but within declared criterion | `COMPATIBLE` | `COMPATIBLE` | PASS |
| missing observable | `INCONCLUSIVE` | `INCONCLUSIVE` | PASS |
| clock mismatch | `INVALID_MEASUREMENT` | `INVALID_MEASUREMENT` | PASS |
| HIGH confounder present | `INCONCLUSIVE` | `INCONCLUSIVE` | PASS |
| cross-boot disagreement | `INCONCLUSIVE` | `INCONCLUSIVE` | PASS |
| cross-condition disagreement | `INCONCLUSIVE` | `INCONCLUSIVE` | PASS |
| ADB interruption | `INCONCLUSIVE` | `INCONCLUSIVE` | PASS |
| unexpected reboot/session break | `INVALID_MEASUREMENT` | `INVALID_MEASUREMENT` | PASS |
| malformed evidence | `INVALID_MEASUREMENT` | `INVALID_MEASUREMENT` | PASS |
| wrong firmware identity | `INVALID_MEASUREMENT` | `INVALID_MEASUREMENT` | PASS |

Test result: 16 test methods passed, including all Phase I tests, all Phase J0 candidate guards, and the 14-scenario J2 matrix. A future approved commit must reproduce this result. Any failure or ambiguous result is a hard GO-gate blocker.
