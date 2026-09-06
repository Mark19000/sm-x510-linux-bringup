# Phase I must-validate synthetic tests

The harness applies the same six synthetic scenarios to `SKB_SEND_SIZE`, `SLIDE_WAIT_NSEC`, `SLIDE_REQUEUE_ARM_USEC`, `FOPS_ROUTE_COARSE_DELAY_USEC`, and `FOPS_ROUTE_FINE_DELAY_TICKS`.

| Scenario | Synthetic input property | Required classifier behavior |
|---|---|---|
| Compatible-looking | Direct criterion is met at the Phase H minimum level; E4 cases span distinct condition IDs. | `COMPATIBLE` only when attribution and prerequisite checks pass. |
| Incompatible-looking | The Phase H incompatibility criterion is explicitly met at its minimum level. | `INCOMPATIBLE`. |
| Insufficient | Environment resembles the baseline but evidence is E1 only. | `INCONCLUSIVE`. |
| Confounded | More than one parameter is declared changed. | `INCONCLUSIVE` with partial attribution. |
| Condition drift | One `CONDITION_ID` contains conflicting environment tuples. | `INVALID_MEASUREMENT`. |
| Missing prerequisite | A hard/required prerequisite is unresolved. | `INCONCLUSIVE` and not attributable. |

Thirty logical cases (five parameters × six scenarios) are executed by `test_five_must_validate_six_scenarios`. The E1 scenario proves that environmental similarity alone cannot validate any of the five. No operational value or procedure is encoded.
