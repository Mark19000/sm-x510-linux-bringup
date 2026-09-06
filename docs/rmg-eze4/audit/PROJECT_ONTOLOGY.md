# Project Ontology — RMG-EZE4

## Entity Relationships

```mermaid
graph TD
    FW["Firmware (X510XXUCEZE4)"] --> BIN["Binary Artifact (Image.stock)"]
    FW --> SRC["Source Code (OSRC EZE4)"]

    BIN --> SYM["Symbol Offsets (eze4_symbol_map.csv)"]
    BIN --> VULN["Vulnerability Presence (stock_rtmutex_binary_verification.md)"]
    BIN --> P0T["P0 Fingerprint Table (generated.h)"]

    SRC --> STRUCT["Structure Layouts (eze4_struct_layout.csv)"]
    SRC --> ALG["Algorithm Constants"]

    STRUCT --> PARAM["Target Parameters (180)"]
    SYM --> PARAM
    ALG --> PARAM

    PARAM --> |"143 identical"| STATIC_OK["Static Compatibility"]
    PARAM --> |"10 changed"| REDERIVED["Rederived Values"]
    PARAM --> |"20 runtime"| RUNTIME["Runtime Validation Required"]
    PARAM --> |"3+3+1"| OTHER["Legacy/NA/Unresolved"]

    RUNTIME --> EXP["Experiment Design (J2 Contract)"]
    EXP --> TRIAL["Trial (child lifecycle)"]
    TRIAL --> BOOT["Boot (device cycle)"]
    BOOT --> COND["Condition Class"]
    TRIAL --> CONF["Confounder Observation"]
    TRIAL --> VOTE["Evidence Vote"]

    VOTE --> AGG["E4 Aggregation"]
    AGG --> VERDICT["Campaign Verdict"]

    P0T --> COLL["Collision Analysis"]
    COLL --> REACH["Reachability (UNKNOWN)"]
    REACH -.-> |"requires"| LOADER["Samsung Bootloader (unavailable)"]

    FW --> OBS["Physical Observation (Phase G)"]
    OBS --> IDENT["Runtime Identity (6 dimensions)"]
    IDENT --> SCHEMA["Schema v2.2.1 (const binding)"]
```

## Category Error Prevention Rules

1. **Firmware artifact** cannot prove **runtime behavior**
2. **Source semantics** cannot prove **stock binary behavior** (must verify via disassembly)
3. **Rebuild address** cannot substitute for **stock address**
4. **struct sizeof** cannot substitute for **allocation bucket size**
5. **P0 label** cannot substitute for **physical KASLR offset** or **virtual displacement**
6. **Environment observation** cannot substitute for **consumer validation**
7. **Parameter absence** cannot substitute for **parameter incompatibility**
8. **Single occurrence** cannot satisfy **statistical evidence threshold**
9. **Schema compliance** cannot prove **runtime availability** of required telemetry
10. **Test PASS** cannot prove **correct validation** when test and validator share constants
