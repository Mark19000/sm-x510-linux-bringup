# Phase I synthetic campaign report

Campaign `SYNTHETIC_PHASE_I_CAMPAIGN` contains two synthetic sessions, three synthetic boot IDs, and three synthetic condition IDs. Every evidence reference is explicitly synthetic and preserved as a raw SHA-256-style reference; no real address or device-derived state is used.

| Parameter | Synthetic outcome | Pipeline behavior |
|---|---|---|
| `SKB_SEND_SIZE` | Direct repeated E3 geometry records with immutable references. | Compatible classification is permitted and provenance retained. |
| `SLIDE_WAIT_NSEC` | Repeated attributable wrong ordering at E3. | Incompatible classification is permitted under the Phase H negative minimum. |
| `FOPS_ROUTE_FINE_DELAY_TICKS` | Favorable evidence only at E3 and without cross-condition completion. | `INCONCLUSIVE`; E4/cross-condition requirement enforced. |
| `P0_FINGERPRINT_MIN_MARGIN` | Table membership only while loader mapping remains open. | `INCONCLUSIVE`; `P0_BLOCKED`; no reachability inference. |
| `DEFAULT_ATTEMPT_TIMEOUT_SEC` | Opposed results on separate synthetic boots. | `INCONCLUSIVE`; contradiction surfaced rather than averaged. |
| `SLIDE_RECLAIM_SENDS` | Required geometry/P0 consumer prerequisite absent. | Stop event `MISSING_PREREQUISITE`; result excluded from validation. |

The dry run demonstrates multiple identity partitions, preserved raw references, insufficient-evidence detection, cross-boot contradiction handling, E3/E4 enforcement, unsupported-conclusion refusal, and preservation of P0 uncertainty. Missing partitions contribute no votes, and one success never dominates opposed failures. The fixture is `tools/rmg-eze4/tests/fixtures/synthetic_campaign.json`.
