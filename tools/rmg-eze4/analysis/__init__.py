"""Canonical Phase J2 offline validation and campaign aggregation API.

The historical Phase-I classifier remains available explicitly as
``analysis.engine``; it is deliberately not re-exported here.
"""

from .aggregator import (
    COMPATIBLE, INCOMPATIBLE, INCONCLUSIVE, INVALID_EXPERIMENT,
    aggregate_campaign,
)
from .validator import validate_observation_record

__all__ = [
    "INCONCLUSIVE",
    "INCOMPATIBLE",
    "COMPATIBLE",
    "INVALID_EXPERIMENT",
    "aggregate_campaign",
    "validate_observation_record",
]
