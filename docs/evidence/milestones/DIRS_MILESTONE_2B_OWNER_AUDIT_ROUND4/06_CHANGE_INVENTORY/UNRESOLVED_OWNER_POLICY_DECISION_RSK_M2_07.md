# UNRESOLVED OWNER POLICY DECISION RSK-M2-07

**Title:** Mandatory Life-Safety Start Deadline ($T_{\text{safety\_max}}$) Derivation Policy
**Status:** RECORDED AS UNRESOLVED OWNER POLICY DECISION
**Reference:** Milestone 2A Constraint Traceability §11; Mathematical Formulation §3.2

## 1. Traceability Gap
Milestone 2A specifies that all Tier-1 mandatory recovery projects must satisfy $w_j = 1$ and $S_j \le T_{\text{safety\_max}}$. However, Milestone 2A does not specify a numerical default value for $T_{\text{safety\_max}}$ when omitted by callers, nor does it define an external service from which it must be computed.

## 2. Engineering Remediation in Milestone 2B
To prevent inventing unapproved operational policy while ensuring mathematical and life-safety integrity, the Milestone 2B CP-SAT optimization engine strictly implements a **fail-closed** architecture:
- If any project in the portfolio is designated as `is_tier1_mandatory == True`, the caller must explicitly supply `max_safety_start_period` satisfying $1 \le T_{\text{safety\_max}} \le T$.
- If omitted or out of bounds, validation immediately rejects the request with `MODEL_INVALID` (`MISSING_SAFETY_DEADLINE` or `INVALID_SAFETY_DEADLINE`).

## 3. Owner Decision Required Prior to Milestone 3
The project owner must decide in Milestone 3 whether to:
1. Retain caller-mandated explicit deadlines (Option A); or
2. Adopt a system-wide default derivation formula (Option B), e.g., $T_{\text{safety\_max}} = \lceil 0.25 \times T \rceil$ or declaration-based threshold.
