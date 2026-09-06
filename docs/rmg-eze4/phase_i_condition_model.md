# Phase I condition matrix model

The abstract condition tuple contains only Phase H-derived dimensions: firmware/kernel baseline, boot identity, CPU-topology state, scheduler/load class, memory-availability/pressure class, allocator-state descriptor, counter/timebase identity, resource-limit class, discovery candidate mix, and consumer-observability state. Group contracts select the relevant subset.

Every dimension has one of three provenance kinds:

- `OBSERVED_CONDITION`: recorded context not asserted to be held fixed.
- `CONTROLLED_CONDITION`: declared fixed by the future study design, with supporting provenance.
- `UNKNOWN_CONDITION`: unavailable or changing context; it cannot silently inherit a prior value.

A `CONDITION_ID` is the digest-addressed identity of the normalized tuple plus provenance kinds. Material changes create a new ID. Unknown values are explicit and may force `INCONCLUSIVE` when a group requires them for attribution. This model describes representation only and prescribes no manipulation of hardware or load.
