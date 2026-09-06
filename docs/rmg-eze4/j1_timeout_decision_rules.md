# Abstract Decision Rules: `DEFAULT_ATTEMPT_TIMEOUT_SEC`

This document formalizes the abstract decision logic and classification criteria for evaluating the compatibility of `DEFAULT_ATTEMPT_TIMEOUT_SEC`. It defines the four canonical states—`COMPATIBLE`, `INCOMPATIBLE`, `INCONCLUSIVE`, and `INVALID_MEASUREMENT`—in terms of predicate calculus and deterministic pseudocode, operating strictly on normalized evidence records without prescribing a specific numeric timeout value or runtime execution steps.

---

## 1. Formal Classification Definitions

### 1.1 `COMPATIBLE`
The parameter configuration is certified `COMPATIBLE` if and only if:
1. All records satisfy structural validity and complete provenance.
2. Attribution is strictly preserved (`CHANGED_PARAMETERS` contains only `DEFAULT_ATTEMPT_TIMEOUT_SEC`).
3. Evidence satisfies canonical level **E4** (`CROSS_BOOT_CROSS_CONDITION`).
4. Cross-condition partition coverage is satisfied ($\ge 2$ distinct verified conditions).
5. Across all tested valid partitions, every legitimate attempt duration tail $T_{\text{attempt}}$ completes with positive policy headroom below the active timeout threshold:
   $$\forall r \in R, \quad T_{\text{attempt}}(r) + T_{\text{headroom}} \le T_{\text{timeout}}$$
6. No premature timeout expiries occurred during legitimate attempt execution.
7. Zero unresolved contradictions, outliers, or condition drifts exist.

### 1.2 `INCOMPATIBLE`
The parameter configuration is certified `INCOMPATIBLE` if:
1. Records satisfy structural validity, complete provenance, and attributable status.
2. Evidence satisfies at least canonical level **E3** (repeated controlled observation).
3. Under one or more valid operating conditions, repeated legitimate exploit attempts are prematurely terminated by the supervisor watchdog timer before reaching terminal completion:
   $$\exists r \in R, \quad T_{\text{attempt}}(r) \ge T_{\text{timeout}} \implies \text{TERMINATED\_BY\_TIMEOUT}$$
4. The termination is uniquely attributable to the inadequacy of `DEFAULT_ATTEMPT_TIMEOUT_SEC` (and not to pre-P0 delays, child deadlocks, or external cancellation).

### 1.3 `INCONCLUSIVE`
An evaluation yields `INCONCLUSIVE` if any of the following hold:
1. **Insufficient Evidence Level:** Supplied evidence level is below the required threshold (e.g. E1 or E2 when evaluating compatibility).
2. **Missing Partition Coverage:** Cross-condition or cross-boot requirements are unmet (e.g. all trials performed under a single condition).
3. **Contradictory Observables:** Records within the evaluation set vote in opposing directions (e.g. compatible on one trial, incompatible on another without condition explanation).
4. **Attribution Failure:** Multiple parameters were modified simultaneously, or prerequisite group dependencies (`UNRESOLVED_GROUP_DEPENDENCIES`) remain open.
5. **Unlabelled Observable:** Supervisor logs a timeout, but stage-labelled durations are unavailable, preventing separation of P0 search duration from overall duration.
6. **Unresolved Outlier:** An unexplained duration anomaly occurs without documented root cause.

### 1.4 `INVALID_MEASUREMENT`
An evaluation yields `INVALID_MEASUREMENT` if the observation data fails formal measurement hygiene:
1. **Schema Non-Conformance:** Any mandatory schema field (e.g., `TIMESTAMP_HOST`, `SESSION_ID`, `OBSERVABLE`) is missing or malformed.
2. **Missing Raw Evidence Reference:** `RAW_EVIDENCE_REF` is absent, preventing immutable cryptographic provenance tracking.
3. **Baseline Mismatch:** `BASELINE_MATCH == False` (device state did not match canonical EZE4 baseline).
4. **Session Mismatch:** `SESSION_MATCH == False` (evidence originates from an unauthorized or mixed session).
5. **Condition Drift:** The same `CONDITION_ID` is associated with conflicting `ENVIRONMENT` dictionaries across trials.
6. **Explicit Invalidation:** Collector flagged `MEASUREMENT_INVALID == True` (e.g. device freeze, timebase jump, clock step).

---

## 2. Mathematical and Predicate Formulation

Let $R = \{r_1, r_2, \dots, r_n\}$ be a set of normalized observation records.

### Predicates over an individual record $r$:
- $\text{ValidSchema}(r) \iff \text{validate\_observation}(r) == \emptyset$
- $\text{ProvenanceOk}(r) \iff r.\text{RAW\_EVIDENCE\_REF} \ne \text{null}$
- $\text{Attributable}(r) \iff \text{assess\_attribution}(r) == \text{ATTRIBUTABLE}$
- $\text{ConditionDrift}(R) \iff \exists r_i, r_j \in R : r_i.\text{CONDITION\_ID} == r_j.\text{CONDITION\_ID} \land r_i.\text{ENVIRONMENT} \ne r_j.\text{ENVIRONMENT}$
- $\text{MaxLevel}(R) = \max_{r \in R} \text{LEVELS}[r.\text{EVIDENCE\_LEVEL}]$

### Vote function $V(r)$:
$$V(r) = \begin{cases}
\text{INVALID\_MEASUREMENT} & \text{if } r.\text{MEASUREMENT\_INVALID} == \text{True} \\
\text{INCONCLUSIVE} & \text{if } \neg r.\text{OBSERVABLE\_AVAILABLE} \lor r.\text{OUTLIER\_UNRESOLVED} \\
\text{INCONCLUSIVE} & \text{if } r.\text{COMPATIBLE} \land r.\text{INCOMPATIBLE} \\
\text{INCOMPATIBLE} & \text{if } r.\text{INCOMPATIBLE} \land \neg r.\text{COMPATIBLE} \\
\text{COMPATIBLE} & \text{if } r.\text{COMPATIBLE} \land \neg r.\text{INCOMPATIBLE} \\
\text{INCONCLUSIVE} & \text{otherwise}
\end{cases}$$

---

## 3. Decision Logic Pseudocode

```python
def decide_timeout_compatibility(records: list[dict], required_level: str = "E4") -> dict:
    if not records:
        return {"classification": "INCONCLUSIVE", "reasons": ["NO_OBSERVATIONS"]}

    # 1. Structural Schema and Hygiene Validation
    structural_errors = []
    for r in records:
        structural_errors.extend(validate_observation(r))
    if structural_errors:
        return {
            "classification": "INVALID_MEASUREMENT",
            "reasons": sorted(set(structural_errors))
        }

    # 2. Attribution Assessment
    attribution_failures = []
    for r in records:
        state, reasons = assess_attribution(r, prerequisites_valid=True, p0_resolved=True)
        if state != "ATTRIBUTABLE":
            attribution_failures.extend(reasons)
    if attribution_failures:
        return {
            "classification": "INCONCLUSIVE",
            "reasons": sorted(set(attribution_failures))
        }

    # 3. Condition Consistency Check (No Condition Drift)
    condition_envs = {}
    for r in records:
        cid = r["CONDITION_ID"]
        env_repr = canonical_json(r["ENVIRONMENT"])
        condition_envs.setdefault(cid, set()).add(env_repr)
    if any(len(envs) > 1 for envs in condition_envs.values()):
        return {
            "classification": "INVALID_MEASUREMENT",
            "reasons": ["CONDITION_DRIFT"]
        }

    # 4. Evidence Level Enforcement
    max_level = max(r["EVIDENCE_LEVEL"] for r in records)
    if not enforce_evidence_level(max_level, required_level):
        return {
            "classification": "INCONCLUSIVE",
            "reasons": ["INSUFFICIENT_EVIDENCE_LEVEL"]
        }

    # 5. Cross-Condition Coverage Enforcement
    distinct_conditions = {r["CONDITION_ID"] for r in records}
    if len(distinct_conditions) < 2:
        return {
            "classification": "INCONCLUSIVE",
            "reasons": ["CROSS_CONDITION_REQUIRED"]
        }

    # 6. Vote Aggregation
    votes = Counter(record_vote(r) for r in records)

    if votes["INVALID_MEASUREMENT"] > 0:
        return {
            "classification": "INVALID_MEASUREMENT",
            "reasons": ["INVALID_MEMBER_MEASUREMENT"]
        }

    # Surfacing Contradictions (Never averaging them away)
    if votes["COMPATIBLE"] > 0 and votes["INCOMPATIBLE"] > 0:
        return {
            "classification": "INCONCLUSIVE",
            "reasons": ["CONTRADICTORY_OBSERVABLE"]
        }

    if votes["INCOMPATIBLE"] > 0:
        return {"classification": "INCOMPATIBLE", "reasons": []}

    if votes["INCONCLUSIVE"] > 0:
        return {
            "classification": "INCONCLUSIVE",
            "reasons": ["INCONCLUSIVE_MEMBER"]
        }

    if votes["COMPATIBLE"] > 0:
        return {"classification": "COMPATIBLE", "reasons": []}

    return {"classification": "INCONCLUSIVE", "reasons": ["NO_DECISIVE_VOTE"]}
```
