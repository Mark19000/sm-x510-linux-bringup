"""LEGACY Phase-I offline observation classifier.

HISTORICAL / BACKWARD-COMPATIBILITY ONLY:
This module implements the Phase-I / early Phase-J0 single-record observation
classification model. It is retained strictly for backward compatibility with
historical Phase-I and Phase-J0 test suites (test_phase_i_analysis.py,
test_phase_j0_selection.py).

DO NOT USE FOR PHASE J2 / J2.1-R1 EVALUATIONS:
Phase J2.1-R1 canonical campaign evaluations are governed exclusively by
`aggregator.py` (aggregate_campaign) operating on Schema v2.2.1 multi-boot/
multi-condition campaigns. Phase J2 active test suites and evaluation pipelines
must not import or route decisions through this legacy module.
"""

from collections import Counter
import json
from typing import Iterable, Mapping, Sequence

COMPATIBLE = "COMPATIBLE"
INCOMPATIBLE = "INCOMPATIBLE"
INCONCLUSIVE = "INCONCLUSIVE"
INVALID_MEASUREMENT = "INVALID_MEASUREMENT"

ATTRIBUTABLE = "ATTRIBUTABLE"
PARTIALLY_ATTRIBUTABLE = "PARTIALLY_ATTRIBUTABLE"
NOT_ATTRIBUTABLE = "NOT_ATTRIBUTABLE"

LEVELS = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4}
REQUIRED_FIELDS = {
    "SESSION_ID", "BOOT_ID", "CONDITION_ID", "TRIAL_ID", "MEASUREMENT_ID",
    "GROUP_ID", "PARAMETER", "OBSERVABLE", "TIMESTAMP_HOST", "SOURCE",
    "RAW_EVIDENCE_REF", "ENVIRONMENT", "EXPECTED_CRITERION",
    "OBSERVED_VALUE", "CONFIDENCE", "CONFOUNDERS", "SYNTHETIC",
}


def validate_observation(record: Mapping) -> list[str]:
    """Return structural errors; an empty list means structurally usable."""
    errors = [f"MISSING_{name}" for name in sorted(REQUIRED_FIELDS - record.keys())]
    if record.get("SYNTHETIC") is not True:
        errors.append("NOT_EXPLICITLY_SYNTHETIC_OR_APPROVED_INPUT")
    if record.get("EVIDENCE_LEVEL") not in LEVELS:
        errors.append("BAD_EVIDENCE_LEVEL")
    if not isinstance(record.get("ENVIRONMENT"), Mapping):
        errors.append("BAD_ENVIRONMENT")
    if not isinstance(record.get("CONFOUNDERS"), list):
        errors.append("BAD_CONFOUNDERS")
    if record.get("OBSERVABLE_AVAILABLE") not in (True, False):
        errors.append("BAD_OBSERVABLE_AVAILABILITY")
    if record.get("BASELINE_MATCH") is False:
        errors.append("BASELINE_MISMATCH")
    if record.get("SESSION_MATCH") is False:
        errors.append("WRONG_SESSION")
    return errors


def enforce_evidence_level(actual: str, required: str) -> bool:
    """True iff the supplied canonical evidence level meets the minimum."""
    return actual in LEVELS and required in LEVELS and LEVELS[actual] >= LEVELS[required]


def assess_attribution(record: Mapping, prerequisites_valid: bool = True,
                       p0_resolved: bool = True) -> tuple[str, list[str]]:
    """Classify attribution without interpreting the observed value."""
    reasons: list[str] = []
    if not record.get("RAW_EVIDENCE_REF"):
        reasons.append("MISSING_RAW_EVIDENCE_REF")
    if not record.get("ENVIRONMENT"):
        reasons.append("MISSING_ENVIRONMENT")
    changed = record.get("CHANGED_PARAMETERS", [])
    if len(changed) > 1:
        reasons.append("MULTIPLE_PARAMETERS_CHANGED")
    if not prerequisites_valid:
        reasons.append("MISSING_PREREQUISITE")
    if record.get("P0_DEPENDENCY") in {"P0_DEPENDENT", "P0_ONLY"} and not p0_resolved:
        reasons.append("P0_BLOCKED")
    if record.get("MULTI_BOOT") and not record.get("BOOT_ID"):
        reasons.append("MISSING_BOOT_ID")
    unresolved = record.get("UNRESOLVED_GROUP_DEPENDENCIES", [])
    if unresolved:
        reasons.append("UNRESOLVED_GROUP_DEPENDENCY")
    if not reasons:
        return ATTRIBUTABLE, []
    hard = {"MISSING_RAW_EVIDENCE_REF", "MISSING_PREREQUISITE", "P0_BLOCKED",
            "MISSING_BOOT_ID", "UNRESOLVED_GROUP_DEPENDENCY"}
    state = NOT_ATTRIBUTABLE if hard.intersection(reasons) else PARTIALLY_ATTRIBUTABLE
    return state, reasons


def _record_vote(record: Mapping) -> str:
    if record.get("MEASUREMENT_INVALID"):
        return INVALID_MEASUREMENT
    if not record.get("OBSERVABLE_AVAILABLE"):
        return INCONCLUSIVE
    if record.get("OUTLIER_UNRESOLVED"):
        return INCONCLUSIVE
    compatible = record.get("COMPATIBILITY_CRITERION_MET") is True
    incompatible = record.get("INCOMPATIBILITY_CRITERION_MET") is True
    if compatible and incompatible:
        return INCONCLUSIVE
    if incompatible:
        return INCOMPATIBLE
    if compatible:
        return COMPATIBLE
    return INCONCLUSIVE


def analyze_observations(records: Sequence[Mapping], *, required_level: str,
                         prerequisites_valid: bool = True,
                         p0_resolved: bool = True,
                         require_cross_boot: bool = False,
                         require_cross_condition: bool = False) -> dict:
    """Aggregate normalized observations conservatively.

    No sample count is invented. Callers must provide an already justified
    E-level. Contradictions always surface as INCONCLUSIVE.
    """
    if not records:
        return {"classification": INCONCLUSIVE, "reasons": ["NO_OBSERVATIONS"]}
    structural = [error for record in records for error in validate_observation(record)]
    if structural:
        return {"classification": INVALID_MEASUREMENT,
                "reasons": sorted(set(structural))}
    attribution = [assess_attribution(r, prerequisites_valid, p0_resolved) for r in records]
    if any(state == NOT_ATTRIBUTABLE for state, _ in attribution):
        reasons = sorted({reason for _, rs in attribution for reason in rs})
        return {"classification": INCONCLUSIVE, "reasons": reasons}
    if any(state == PARTIALLY_ATTRIBUTABLE for state, _ in attribution):
        reasons = sorted({reason for _, rs in attribution for reason in rs})
        return {"classification": INCONCLUSIVE, "reasons": reasons}
    condition_environments: dict[str, set[str]] = {}
    for record in records:
        condition_environments.setdefault(record["CONDITION_ID"], set()).add(
            json.dumps(record["ENVIRONMENT"], sort_keys=True, separators=(",", ":"))
        )
    if any(len(values) > 1 for values in condition_environments.values()):
        return {"classification": INVALID_MEASUREMENT,
                "reasons": ["CONDITION_DRIFT"]}
    levels = [r["EVIDENCE_LEVEL"] for r in records]
    supplied = max(levels, key=lambda level: LEVELS[level])
    if not enforce_evidence_level(supplied, required_level):
        return {"classification": INCONCLUSIVE,
                "reasons": ["INSUFFICIENT_EVIDENCE_LEVEL"]}
    boots = {r["BOOT_ID"] for r in records if r.get("BOOT_ID")}
    conditions = {r["CONDITION_ID"] for r in records if r.get("CONDITION_ID")}
    if require_cross_boot and len(boots) < 2:
        return {"classification": INCONCLUSIVE, "reasons": ["CROSS_BOOT_REQUIRED"]}
    if require_cross_condition and len(conditions) < 2:
        return {"classification": INCONCLUSIVE, "reasons": ["CROSS_CONDITION_REQUIRED"]}
    votes = Counter(_record_vote(record) for record in records)
    if votes[INVALID_MEASUREMENT]:
        return {"classification": INVALID_MEASUREMENT,
                "reasons": ["INVALID_MEMBER_MEASUREMENT"]}
    if votes[COMPATIBLE] and votes[INCOMPATIBLE]:
        return {"classification": INCONCLUSIVE,
                "reasons": ["CONTRADICTORY_OBSERVABLE"]}
    if votes[INCOMPATIBLE]:
        return {"classification": INCOMPATIBLE, "reasons": []}
    if votes[INCONCLUSIVE]:
        return {"classification": INCONCLUSIVE,
                "reasons": ["INCONCLUSIVE_MEMBER"]}
    if votes[COMPATIBLE]:
        return {"classification": COMPATIBLE, "reasons": []}
    return {"classification": INCONCLUSIVE, "reasons": ["NO_DECISIVE_VOTE"]}
