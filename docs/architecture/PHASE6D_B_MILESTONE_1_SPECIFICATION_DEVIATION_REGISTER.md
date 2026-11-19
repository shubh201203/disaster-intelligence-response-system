# DIRS Phase 6D-B — Milestone 1 Specification Deviation Register

**Document ID:** `DIRS-PHASE6D-B-M1-DEV-01`  
**Classification:** ARCHITECTURAL DEVIATION REGISTER & CHANGE-CONTROL LOG  
**Author:** Principal Software Architect, Operations Research Specialist & QA Lead  
**Date:** November 17, 2026  
**Status:** COMPLETE — FORMAL IMPLEMENTATION EXCEPTIONS RECORDED  
**Scope:** Milestone 1 (Domain Contracts and Pure Mathematical Services)  
**Database Policy:** ZERO MIGRATIONS — Schema frozen at `phase6b_recovery_foundation`  

---

## 1. Purpose and Governance Principle

This register formally documents architectural and mathematical deviations between the frozen Phase 6D-A research specification ([`docs/PHASE6D_MCPI_MATHEMATICAL_FORMULATION.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE6D_MCPI_MATHEMATICAL_FORMULATION.md)) and the implemented Phase 6D-B Milestone 1 domain services in [`backend/app/recovery/services/`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/recovery/services).

### Strict Governance Rules
1. **Preservation of Frozen Artifacts:** The historical Phase 6D-A specification document (`PHASE6D_MCPI_MATHEMATICAL_FORMULATION.md`) remains strictly unmodified to maintain a forensic audit trail of the baseline design.
2. **Transparent Acknowledgment:** The engineering team does **not** claim that the current implementation is an exact match for Section 5.1 of the frozen specification.
3. **Traceability of Authority:** Every deviation is mapped directly to the specific project-owner instruction that authorized it, complete with mathematical rationale, test proof, and change-control tracking.

---

## 2. Frozen Specification Baseline (Verbatim)

From [`docs/PHASE6D_MCPI_MATHEMATICAL_FORMULATION.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE6D_MCPI_MATHEMATICAL_FORMULATION.md), Section 5.1 (lines 113–120):

```markdown
### 5.1 Deterministic Lexicographic Tie-Breaking
When two candidate projects achieve identical MCPI scores (|MCPI_a - MCPI_b| < 10^-4):
1. First Tie-Breaker: Highest normalized Life-Safety Urgency phi_L.
2. Second Tie-Breaker: Highest Vulnerable Population Density phi_V.
3. Third Tie-Breaker: Highest Transitive Downstream Cascade Cascade(j).
4. Fourth Tie-Breaker: Lowest Estimated Capital Cost C_j (cost-effectiveness).
5. Final Deterministic Arbiter: Cryptographic SHA-256 hash of project_code (guarantees mathematical determinism across platform restarts).
```

---

## 3. Formal Deviation Register

### DEV-M1-01: Elimination of Tolerance-Based Substantive Equivalence Threshold ($10^{-4}$)

| Field | Detail |
| :--- | :--- |
| **Deviation ID** | `DEV-M1-01` |
| **Component** | `MCPIPrioritizationService.rank_portfolio` in [`backend/app/recovery/services/mcpi_prioritization_service.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/recovery/services/mcpi_prioritization_service.py) |
| **Frozen Requirement** | Equivalence condition: $|\text{MCPI}_a - \text{MCPI}_b| < 10^{-4}$. Projects within $0.0001$ were treated as tied and subjected to secondary criteria. |
| **Implemented Behavior** | Exact raw floating-point comparison under IEEE 754 64-bit double precision. No tolerance grouping or epsilon-clustering is performed. Any substantive score difference (even $10^{-5}$) determines ranking. Subsequent criteria are invoked if and only if prior criteria are mathematically identical. |
| **Authorizing Directive** | Project Owner Request #10 (Milestone 1 Final Correction and Evidence Pass, Section A): *"Remove tolerance-based equality as a reason to invoke project ID. Use exact equality of the final compared values for stable ID ordering... A small but real difference in substantive priority must not be overridden by project ID."* |
| **Mathematical Rationale** | Tolerance-based equivalence ($|\Delta| < 10^{-4}$) creates intransitive equivalence classes (e.g., $A \approx B$ and $B \approx C$, but $A \not\approx C$). Furthermore, a project with a demonstrably higher substantive score could be bypassed by a lower-scoring project purely because of secondary tie-breakers or non-substantive ID sorting. Exact evaluation preserves strict monotonicity. |
| **Governance Rationale** | Prevents arbitrary override of real substantive priority differences by procedural identifiers in public disaster recovery allocations. |
| **Affected Files & Tests** | **Source:** `backend/app/recovery/services/mcpi_prioritization_service.py`<br>**Tests:** `test_adversarial_exact_equality_mcpi_sub_tolerance_diff`, `test_adversarial_exact_equality_life_safety_sub_tolerance_diff`, `test_adversarial_exact_equality_vulnerability_sub_tolerance_diff` in `tests/backend/test_phase6d_mathematical_services.py` |
| **Classification** | **Permanent Approved Implementation Exception.** |
| **Change-Control Action** | Amend Section 5.1 in the next official revision of `PHASE6D_MCPI_MATHEMATICAL_FORMULATION.md` when the documentation baseline is unlocked for updates. |

---

### DEV-M1-02: Replacement of Cryptographic Hash Arbiter with Ascending `project_id`

| Field | Detail |
| :--- | :--- |
| **Deviation ID** | `DEV-M1-02` |
| **Component** | Final non-substantive tie-breaker in [`backend/app/recovery/services/mcpi_prioritization_service.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/recovery/services/mcpi_prioritization_service.py) |
| **Frozen Requirement** | "5. Final Deterministic Arbiter: Cryptographic SHA-256 hash of `project_code` (guarantees mathematical determinism across platform restarts)." |
| **Implemented Behavior** | Pre-sorts ascending alphabetical by `project_id`, followed by a stable Python Timsort on substantive criteria. Operates strictly as a non-substantive final arbiter when all 5 substantive criteria are identical. |
| **Authorizing Directive** | Project Owner Request #9 & #10 (Milestone 1 Final Acceptance Audit & Final Correction): *"Use ascending project_id only as a stable, non-substantive final ordering after all approved substantive criteria are equal. Do not allow project ID or any arbitrary identifier to affect substantive priority. Do not introduce new ranking criteria."* |
| **Mathematical Rationale** | Cryptographic hashing generates a pseudo-random permutation among identical projects, obscuring auditability without providing substantive value. Stable lexicographical ordering on canonical primary keys (`project_id`) achieves identical determinism with $O(1)$ evaluation cost and zero external hashing dependencies. |
| **Governance Rationale** | High-stakes disaster response audits require transparent, explainable tie-breaking. A simple ascending identifier is human-auditable and predictable, unlike an opaque cryptographic digest. |
| **Affected Files & Tests** | **Source:** `backend/app/recovery/services/mcpi_prioritization_service.py`<br>**Tests:** `test_authorized_tie_breaking_hierarchy`, `test_project_id_zero_substantive_effect_reversed_ids`, `test_project_id_stable_final_tie_breaker_exact_equality` in `tests/backend/test_phase6d_mathematical_services.py` |
| **Classification** | **Permanent Approved Implementation Exception.** |
| **Change-Control Action** | Amend Section 5.1 Item 5 in the next official revision of `PHASE6D_MCPI_MATHEMATICAL_FORMULATION.md`. |

---

## 4. Architectural Summary of Multi-Tier Tie-Breaking

The implementation strictly separates the multi-stage ranking pipeline into three mathematically distinct tiers:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 1: NON-COMPENSATORY SAFETY FILTER              │
│       Elevate all projects with S_L ≥ 0.85 to TIER_1_MANDATORY          │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 2: SUBSTANTIVE MCPI ORDERING                   │
│       Sort descending by exact unrounded IEEE double raw score          │
│       (No tolerance epsilon grouping; any diff > 0 decides order)       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (Invoked ONLY if raw scores identical)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 3: SUBSTANTIVE TIE-BREAKERS                    │
│       1. Life-Safety Urgency (phi_L, exact float descending)            │
│       2. Vulnerability Density (phi_V, exact float descending)          │
│       3. Transitive Cascade (Cascade(j), integer descending)            │
│       4. Capital Cost (C_j, exact float ascending; lower cost wins)     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (Invoked ONLY if ALL 4 criteria identical)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                STAGE 4: STABLE NON-SUBSTANTIVE FINAL ARBITER            │
│       Project ID (project_id, string ascending alphabetical)            │
│       Guaranteed zero effect on any project with substantive difference │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Audit Conclusion

Both deviations (`DEV-M1-01` and `DEV-M1-02`) are formally recorded, mathematically justified, and validated by adversarial automated tests. They stand as **approved implementation exceptions** sanctioned by explicit project-owner directives during Milestone 1 remediation and acceptance audits.
