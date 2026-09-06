"""Canonical E4 Campaign Aggregator for Phase J2.1-R1.

Implements the exact canonical J2 E4 decision contract:
- >= 3 distinct boots
- Both SETTLED_NOMINAL and ELEVATED_VALID present on every boot
- >= 2 valid qualifying trials per boot x condition partition (min 12 total)
- Max 1 invalid trial per boot, max 2 invalid total (exceeding -> INVALID_EXPERIMENT)
- Incompatibility: >= 3 valid attributable timeouts in SAME condition across >= 2 boots
- Single timeout -> INCONCLUSIVE
"""

from collections import Counter, defaultdict
from typing import Dict, List, Mapping, Tuple


COMPATIBLE = "COMPATIBLE"
INCOMPATIBLE = "INCOMPATIBLE"
INCONCLUSIVE = "INCONCLUSIVE"
INVALID_EXPERIMENT = "INVALID_EXPERIMENT"


def aggregate_campaign(records: List[Mapping]) -> Dict:
    """Aggregate normalized observations into a final campaign verdict."""
    if not records:
        return {"verdict": INCONCLUSIVE, "reasons": ["NO_RECORDS"]}

    # Track boots, conditions, and invalid counts
    boot_invalid_counts = Counter()
    total_invalid = 0

    valid_trials = []
    incompatible_timeout_trials = []

    # Map partitions: (boot_id, condition_class) -> list of records
    partitions = defaultdict(list)
    boots_seen = set()
    boot_conditions = defaultdict(set)

    for r in records:
        boot_id = r.get("boot_id", "UNKNOWN_BOOT")
        boots_seen.add(boot_id)
        cond_class = r.get("condition_vector", {}).get("condition_class", "UNKNOWN_COND")
        boot_conditions[boot_id].add(cond_class)

        cls = r.get("classification", {})
        validity = cls.get("trial_validity")
        vote = cls.get("trial_evidence_vote")
        term = cls.get("trial_terminal_class")

        if validity == "INVALID":
            boot_invalid_counts[boot_id] += 1
            total_invalid += 1
        elif validity == "VALID":
            valid_trials.append(r)
            partitions[(boot_id, cond_class)].append(r)
            if vote == "INCOMPATIBLE_VOTE" and term == "SUPERVISOR_OVERALL_TIMEOUT":
                incompatible_timeout_trials.append(r)

    # 1. Check Invalid Caps (Strict Fail-Closed)
    for boot_id, count in boot_invalid_counts.items():
        if count > 1:
            return {
                "verdict": INVALID_EXPERIMENT,
                "reasons": [f"BOOT_{boot_id}_EXCEEDED_INVALID_CAP_{count}_GT_1"]
            }

    if total_invalid > 2:
        return {
            "verdict": INVALID_EXPERIMENT,
            "reasons": [f"CAMPAIGN_TOTAL_INVALID_EXCEEDED_CAP_{total_invalid}_GT_2"]
        }

    # 2. Check Incompatibility Threshold (>= 3 same condition across >= 2 boots)
    if incompatible_timeout_trials:
        # Group by condition
        condition_timeouts = defaultdict(list)
        for t in incompatible_timeout_trials:
            c = t.get("condition_vector", {}).get("condition_class")
            condition_timeouts[c].append(t)

        for cond, timeouts in condition_timeouts.items():
            distinct_boots = {t.get("boot_id") for t in timeouts}
            if len(timeouts) >= 3 and len(distinct_boots) >= 2:
                return {
                    "verdict": INCOMPATIBLE,
                    "reasons": [
                        f"REPEATED_ATTRIBUTABLE_TIMEOUTS_IN_{cond}_COUNT_{len(timeouts)}_ACROSS_{len(distinct_boots)}_BOOTS"
                    ]
                }

    # 3. Check Compatibility Criteria
    # Require at least 3 boots
    if len(boots_seen) < 3:
        return {
            "verdict": INCONCLUSIVE,
            "reasons": [f"INSUFFICIENT_BOOTS_{len(boots_seen)}_LT_3"]
        }

    # Every boot must have both SETTLED_NOMINAL and ELEVATED_VALID
    for boot_id in boots_seen:
        conds = boot_conditions[boot_id]
        if "SETTLED_NOMINAL" not in conds or "ELEVATED_VALID" not in conds:
            return {
                "verdict": INCONCLUSIVE,
                "reasons": [f"BOOT_{boot_id}_MISSING_REQUIRED_CONDITIONS_{conds}"]
            }

    # Every boot x condition cell must have >= 2 valid qualifying trials
    partition_deficits = []
    for boot_id in boots_seen:
        for c in ["SETTLED_NOMINAL", "ELEVATED_VALID"]:
            cell_count = len(partitions[(boot_id, c)])
            if cell_count < 2:
                partition_deficits.append(f"CELL_({boot_id},{c})_HAS_{cell_count}_VALID_TRIALS_LT_2")

    if partition_deficits:
        return {
            "verdict": INCONCLUSIVE,
            "reasons": partition_deficits
        }

    # Minimum total valid trials >= 12
    if len(valid_trials) < 12:
        return {
            "verdict": INCONCLUSIVE,
            "reasons": [f"TOTAL_VALID_TRIALS_{len(valid_trials)}_LT_12"]
        }

    # If any incompatible vote occurred without meeting the 3x2 threshold, verdict is INCONCLUSIVE
    if len(incompatible_timeout_trials) > 0:
        return {
            "verdict": INCONCLUSIVE,
            "reasons": ["ATTRIBUTABLE_TIMEOUT_WITHOUT_MEETING_FALSIFICATION_THRESHOLD"]
        }

    # Check that every qualifying trial voted COMPATIBLE_VOTE
    non_compat_votes = [
        t for t in valid_trials
        if t.get("classification", {}).get("trial_evidence_vote") != "COMPATIBLE_VOTE"
    ]
    if non_compat_votes:
        return {
            "verdict": INCONCLUSIVE,
            "reasons": [f"CONTAINS_{len(non_compat_votes)}_VALID_TRIALS_WITHOUT_COMPATIBLE_VOTE"]
        }

    # All criteria satisfied
    return {
        "verdict": COMPATIBLE,
        "valid_count": len(valid_trials),
        "boots_count": len(boots_seen),
        "reasons": ["E4_CONTRACT_FULLY_SATISFIED"]
    }
