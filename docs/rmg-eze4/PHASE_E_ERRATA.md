# Phase E accounting errata

## 180-row category total

`eze4_target_readiness_v2.csv` contains 180 data rows. Phase E printed six status categories totaling 177 and omitted the three rows already classified `NOT_APPLICABLE`: `OFFSET_H`, `BUILD_FINGERPRINT`, and `P0_FINGERPRINT_H`. Their classification remains unchanged. The corrected total is:

| Status | Rows |
|---|---:|
| `CONFIRMED_IDENTICAL` | 143 |
| `CONFIRMED_CHANGED` | 10 |
| `LEGACY_INACTIVE` | 3 |
| `NOT_APPLICABLE` | 3 |
| `RUNTIME_VALIDATION_REQUIRED` | 20 |
| `STATICALLY_UNRESOLVED` | 1 |
| **Total** | **180** |

## 20-row runtime-validation total

The Phase E criticality subtotal of 17 described only the rows inherited from `runtime_parameter_criticality.csv`. Three additional readiness rows were assigned `RUNTIME_VALIDATION_REQUIRED` during Phase E:

| Name | Reason | Phase F primary criticality |
|---|---|---|
| `P0_FINGERPRINT_MIN_BEST` | Runtime read errors can reduce the best score below the clean-Image score. | `ENVIRONMENT_DISCOVERY` |
| `P0_FINGERPRINT_MIN_MARGIN` | Runtime read errors can alter the winner/runner-up margin. | `ENVIRONMENT_DISCOVERY` |
| `ROOT_UMH_PATH` | The string is firmware-independent, but existence of the deployed file is external runtime state and is not present in stock-image evidence. | `ENVIRONMENT_DISCOVERY` |

Thus the corrected 20-row criticality accounting is: correctness-critical 1, race-sensitive 4, performance-only 0, other 15. `ROOT_UMH_PATH` had been described as probably reusable; Phase F retains that compatibility inference but classifies the target row as `RUNTIME_VALIDATION_REQUIRED` because the required deployed pathname cannot be confirmed statically. This is a substantive evidence classification, not an arithmetic adjustment.
