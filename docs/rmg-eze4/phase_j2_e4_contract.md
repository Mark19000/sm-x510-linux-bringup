# Phase J2.1-R1 E4 Coverage & Decision Contract

Compatibility requires meeting the smallest deterministic campaign structure below. Satisfying this contract authorizes a mathematical conclusion, never real execution.

---

## 1. Minimal E4 Partition Structure ($3 \times 2 \times 2 = 12$)

Twelve arbitrarily distributed trials are strictly prohibited. The campaign must satisfy:

1. **$\ge 3$ Distinct Verified Boots**: Each boot verified by a cryptographic `boot_id` derived from `boot_instance_token` and `kernel_identity`.
2. **2 Condition Classes on EVERY Boot**: Both `SETTLED_NOMINAL` and `ELEVATED_VALID` must be evaluated on every qualifying boot.
3. **$\ge 2$ Valid Qualifying Trials per Partition Cell**:
   $$\text{Boot 1: } [\text{SETTLED } \ge 2, \text{ELEVATED } \ge 2]$$
   $$\text{Boot 2: } [\text{SETTLED } \ge 2, \text{ELEVATED } \ge 2]$$
   $$\text{Boot 3: } [\text{SETTLED } \ge 2, \text{ELEVATED } \ge 2]$$
   $$\text{Total Minimum Valid Qualifying Trials} = 3 \times 2 \times 2 = 12$$

---

## 2. Attempt Ordinal & Safe-Retry Contract

- Every partition cell must start with a cold attempt (`attempt_ordinal = 1`).
- Later clean retries (`attempt_ordinal > 1`) are permitted if and only if the audited source state verifies that no dirty kernel state, unreaped resources, or memory leaks occurred.
- Fabricating retries or proceeding after dirty/writer/unsafe states is prohibited. If clean retry coverage cannot be obtained safely, report it explicitly as unavailable and halt for independent review.

---

## 3. Invalid Trial Caps

- **Maximum per boot**: $\le 1$ invalid trial.
- **Maximum total across campaign**: $\le 2$ invalid trials.
- An invalid trial is retained in evidence and may be replaced to satisfy cell quotas, provided the caps are not breached.
- Exceeding either limit ($\ge 2$ in any single boot, or $\ge 3$ total) triggers immediate:
  $$\text{campaign\_verdict} = \text{INVALID\_EXPERIMENT}$$

---

## 4. Decision Rules

### Compatibility (`COMPATIBLE`)
- Complete $3 \times 2 \times 2 = 12$ partition coverage satisfied.
- $100\%$ `COMPATIBLE_VOTE` among qualifying trials ($T \le 2195.000\text{ s}$ from post-fork).
- $0$ `INCOMPATIBLE_VOTE`.
- $0$ unresolved outliers.
- Invalid caps preserved ($\le 1$/boot, $\le 2$ total).

### Incompatibility (`INCOMPATIBLE`)
- Requires:
  $$\ge 3\text{ valid attributable overall timeouts in the SAME condition across } \ge 2\text{ distinct verified boots}$$
- A single isolated timeout yields `INCONCLUSIVE`.
- Two timeouts on the same boot yield `INCONCLUSIVE`.
- One timeout in `SETTLED_NOMINAL` and one timeout in `ELEVATED_VALID` yield `INCONCLUSIVE`.
- Disagreements are surfaced, never averaged away.

### Inconclusive (`INCONCLUSIVE`)
- Any campaign that does not violate invalid caps and does not meet the $3 \times 2$ incompatibility threshold, but fails full E4 cell coverage or contains non-attributable outcomes.

### Invalid Experiment (`INVALID_EXPERIMENT`)
- Any breach of invalid trial caps ($\ge 2$/boot or $\ge 3$ total).
- Systemic clock corruption, raw manifest divergence, or state machine violations.
