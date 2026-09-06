# PHASE J2.1-R1.1 — EXACT EZE4 IDENTITY BINDING PATCH
## Root-My-Galaxy EZE4 Compatibility Research Project (`tab-s9-fe-linux`)

```yaml
PHASE: J2.1-R1.1
PURPOSE: EXACT_EZE4_IDENTITY_BINDING_PATCH
REAL_L3_EXECUTION_PERFORMED: NO
AUTHORITY: PHASE_G_PHYSICAL_OBSERVATION
SCHEMA_VERSION: 2.2.1
EVENT_GRAMMAR_VERSION: 2.1.1
```

---

## 1. PURPOSE & BOUNDARIES

Phase J2.1-R1.1 serves as a minimal corrective patch to Phase J2.1-R1.
In accordance with the governing instructions:
- No experiment semantics, watchdog epochs, C1/C2/C3 semantics, E4 thresholds, invalid-trial caps, result taxonomies, timing equations, headroom policies, safe-retry policies, or campaign aggregation rules have been modified.
- No real L3 action (payload execution, root attempt, vulnerable-path execution, kernel write, module load, flash, reboot-for-experiment, or device state modification) is performed or authorized.
- The sole purpose of R1.1 is to bind the exact physically observed EZE4 runtime identity from Phase G into the active schema (v2.2.1) and GO gates, add negative identity tests, rerun the complete offline suite, and confirm zero regression.

---

## 2. CANONICAL PHYSICAL EZE4 BASELINE

| Identity Dimension | Exact Canonical Value | Provenance |
| :--- | :--- | :--- |
| **Model** | `SM-X510` | Physically confirmed via Phase G baseline (`ro.product.model`) |
| **Device Codename** | `gts9fewifi` | Physically confirmed via Phase G baseline (`ro.product.device`) |
| **Incremental Version** | `X510XXUCEZE4` | Physically confirmed via Phase G baseline (`ro.build.version.incremental`) |
| **Build Fingerprint** | `samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys` | Physically confirmed via Phase G baseline (`ro.build.fingerprint`) |
| **Security Patch** | `2026-05-05` | Physically confirmed via Phase G baseline (`ro.build.version.security_patch`) |
| **Kernel Identity** | `5.15.189-android13-3-33478785` | Physically confirmed via Phase G baseline (`uname -r`) |
| **Stock Kernel Image SHA-256** | `ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9` | Bit-exact digest of extracted uncompressed `Image.stock` |

---

## 3. SECURITY PATCH POLICY DECISION

**Decision: OPTION B (Auxiliary Baseline Metadata)**

### Rationale:
1. The exact full build fingerprint `samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys` binds the build ID `BP4A.251205.006` and incremental `X510XXUCEZE4`, inherently locking security patch level `2026-05-05`.
2. The observation schema did not contain a `security_patch` field. Adding a new hard structural schema requirement would gratuitously alter telemetry structures.
3. Therefore, `security_patch: "2026-05-05"` remains authoritative auxiliary baseline metadata in Phase G documentation and the runtime identity contract without mutating observation record structure.

---

## 4. SCHEMA V2.2.1 HARDENING & GO GATES ENFORCEMENT

1. **Schema v2.2.1**:
   - `build_fingerprint` tightened from `{ "type": "string", "minLength": 10 }` to `const: "samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys"`.
   - `kernel_identity` tightened from `{ "type": "string", "pattern": "^5\\.15\\.189.*" }` to `const: "5.15.189-android13-3-33478785"`.
   - Generic patterns, substring matches, and family-only prefixes fail schema validation closed.
2. **GO Gates (`docs/rmg-eze4/phase_j2_go_gates.csv`)**:
   - G02 requires exact: `ro.product.model==SM-X510 && ro.product.device==gts9fewifi && ro.board.platform==s5e8835`.
   - G03 requires exact: `ro.build.version.incremental==X510XXUCEZE4 && ro.build.fingerprint==samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys`.
   - G04 requires exact: `uname -r==5.15.189-android13-3-33478785`.
   - G05 requires exact: `sha256sum(Image.stock)==ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9`.
   - Substring matching where exact match is available is strictly eliminated.

---

## 5. AUDIT QUESTIONS

1. **What is the exact accepted full Android fingerprint?**
   `samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys`
2. **What is the exact accepted kernel identity?**
   `5.15.189-android13-3-33478785`
3. **Is `/^5\.15\.189.*/` sufficient?**
   **NO**. Exact equality `5.15.189-android13-3-33478785` is strictly required.
4. **Is `X510XXUCEZE4` itself the full build fingerprint?**
   **NO**. It is the incremental build property (`ro.build.version.incremental`).
5. **Is the Image.stock digest still `ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9`?**
   **YES**.
6. **Can the active schema accept a wrong fingerprint with the correct incremental?**
   **NO**. Rejected closed by `const` in Schema v2.2.1 and `validator.py`.
7. **Can the active schema accept another 5.15.189 kernel build?**
   **NO**. Rejected closed by `const` in Schema v2.2.1 and `validator.py`.

---

## 6. J2 SEMANTIC REGRESSION GUARD CONFIRMATION

- `slide_ready` resets candidate timer? **NO**
- Watchdog epoch? **POST-FORK DEVICE CLOCK_MONOTONIC**
- Single attributable timeout == INCOMPATIBLE? **NO**
- Incompatibility threshold? **$\ge 3$ same-condition attributable timeouts across $\ge 2$ boots**
- Invalid caps? **$\le 1$ per boot, $\le 2$ total**
- E4 partitioning? **$\ge 3$ boots, both conditions per boot, $\ge 2$ valid qualifying trials per boot $\times$ condition**
