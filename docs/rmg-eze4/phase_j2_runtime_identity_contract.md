# Phase J2 Runtime Identity Contract

```yaml
CONTRACT: PHASE_J2_RUNTIME_IDENTITY
VERSION: 1.1.0
STATUS: BINDING_AND_FROZEN
AUTHORITY: PHASE_G_PHYSICAL_OBSERVATION
SCOPE: RUNTIME_IDENTITY_ENFORCEMENT_ONLY
REAL_L3_EXECUTION: NO
```

---

## 1. Canonical Physical Baseline (Phase G Authority)

The runtime identity parameters below are grounded strictly in the physical observation of the target hardware conducted in Phase G (`docs/rmg-eze4/PHASE_G.md`, raw logs in `docs/rmg-eze4/runtime-evidence/20260906T094426Z/`).
These exact values supersede all prior illustrative, synthetic, or preliminary strings across all active contracts, schemas, validators, test fixtures, and GO gates.

```text
CANONICAL_MODEL:
SM-X510

CANONICAL_DEVICE:
gts9fewifi

CANONICAL_INCREMENTAL:
X510XXUCEZE4

CANONICAL_BUILD_FINGERPRINT:
samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys

CANONICAL_KERNEL_IDENTITY:
5.15.189-android13-3-33478785

CANONICAL_STOCK_IMAGE_SHA256:
ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9
```

---

## 2. Security Patch Policy Decision

```text
POLICY_DECISION: OPTION_B (AUXILIARY_BASELINE_METADATA)
VALUE: 2026-05-05
```

### Rationale
1. The exact full build fingerprint `samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys` uniquely and immutably identifies the platform build `BP4A.251205.006` and incremental `X510XXUCEZE4`, which inherently and cryptographically fixes the security patch level at `2026-05-05`.
2. The canonical observation schema v2.2.0 did not define `security_patch` as a top-level or artifact identity property.
3. Adding `security_patch` as a mandatory field in Schema v2.2.1 would invent a new structural requirement without adding discriminative security.
4. Therefore, `security_patch: "2026-05-05"` is retained as authoritative auxiliary baseline metadata (documented in Phase G and this contract), without introducing a breaking structural schema change.

---

## 3. Strict Equality Invariants

All runtime checks, offline validators, JSON schemas, and preflight GO gates must enforce **exact equality**:

$$\text{Observed Identity} \equiv \text{Canonical Physical Identity}$$

### Prohibited Operations:
1. **No Substring Matching**: Matching `gts9fewifi` inside `gts9fewifixx` or partial strings is strictly forbidden.
2. **No Generic Regex**: Kernel pattern matching like `/^5\.15\.189.*/` is strictly forbidden. The exact release string `5.15.189-android13-3-33478785` is required.
3. **No Incremental Substitution**: `X510XXUCEZE4` is an incremental build tag, NOT the full build fingerprint.
4. **No Cross-Variant Contamination**: Fingerprints with altered CSC segments (e.g. `gts9fewifixx` instead of `gts9fewifieea`) must fail closed.
5. **No Digest Reassociation**: The digest `ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9` belongs exclusively to `Image.stock` (raw uncompressed ARM64 kernel extracted from `boot.img`), never to `boot.img` itself.

---

## 4. Cross-Layer Identity Matrix

| Component | Target Identity Expression | Failure Consequence |
| :--- | :--- | :--- |
| **Observation Schema v2.2.1** | `const: "SM-X510"`, `const: "gts9fewifi"`, `const: "X510XXUCEZE4"`, `const: "samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys"`, `const: "5.15.189-android13-3-33478785"`, `const: "ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9"` | Schema validation failure |
| **GO Gate G02** | `ro.product.model == SM-X510 && ro.product.device == gts9fewifi && ro.board.platform == s5e8835` | Hard STOP (wrong device) |
| **GO Gate G03** | `ro.build.version.incremental == X510XXUCEZE4 && ro.build.fingerprint == samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys` | Hard STOP (wrong firmware) |
| **GO Gate G04** | `uname -r == 5.15.189-android13-3-33478785` | Hard STOP (wrong kernel) |
| **GO Gate G05** | `sha256sum(Image.stock) == ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9` | Hard STOP (wrong stock image) |
| **Validator Constants** | Exact equality against `CANONICAL_*` constants in `tools/rmg-eze4/analysis/validator.py` | `VALIDATION_ERROR` |
