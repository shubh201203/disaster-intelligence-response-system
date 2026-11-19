# DIRS — PHASE 6D-B MILESTONE 2B
# GOVERNANCE DECISION RECORD: RSK-M2-07
## MANDATORY LIFE-SAFETY START DEADLINE DERIVATION POLICY

- **Governance Record ID:** RSK-M2-07
- **Component:** Disaster Intelligence and Response System (DIRS) — Phase 6D-B, Milestone 2B CP-SAT Optimization Engine
- **Spec Author:** Disaster Intelligence Architecture Board
- **Current Status:** **RESOLVED — OPTION A SELECTED AND OWNER-APPROVED**
- **Original Formulation Date:** 2026-11-17
- **Owner Decision Date:** 2026-11-17 (Instruction received 2026-11-17T04:25:50+05:30)
- **Approved Policy:** **OPTION A — CALLER-MANDATORY SAFETY DEADLINE**
- **Applicable Milestones:** Milestone 2B (Engine Verification), Milestone 3 (API Orchestration & Service Integration)

---

## 1. EXECUTIVE SUMMARY & OWNER DECISION

In the approved Phase 6D-B Milestone 2A mathematical specification, the recovery optimization engine is required to enforce an inviolable start deadline ($T_{\text{safety\_max}}$) for all Tier-1 mandatory life-safety projects:
$$w_j = 1 \quad \text{and} \quad S_j \le T_{\text{safety\_max}} \quad \forall j \in \mathcal{J}_{\text{mandatory}}$$

### The Governance Gap (Milestone 2A)
Milestone 2A specified the mathematical relation $S_j \le T_{\text{safety\_max}}$, but **did not define a numerical default value, nor did it specify an external service from which $T_{\text{safety\_max}}$ must be derived** when an incoming portfolio contains mandatory projects but omits an explicit deadline.

### Owner Determination (2026-11-17)
The Project Owner has explicitly reviewed the policy options and formally approved:

> **SELECTED POLICY: OPTION A — CALLER-MANDATORY SAFETY DEADLINE**  
> For every recovery optimization request containing mandatory life-safety projects:
> 1. `max_safety_start_period` ($T_{\text{safety\_max}}$) must be **explicitly supplied by the caller**.
> 2. Missing or null values **must fail closed** (`MODEL_INVALID` / validation rejection).
> 3. Values outside the valid discrete planning horizon $[1, T]$ **must be rejected**.
> 4. **No default, inferred deadline, severity-derived deadline, or horizon-fraction fallback is permitted** within the optimization engine.
> 5. The upstream caller (API layer, decision-support interface, or workflow orchestrator) is strictly responsible for supplying the approved deadline.
> 6. The supplied value must remain fully traceable in the canonical SHA-256 optimization input fingerprint and execution audit metadata.

### Owner Rationale
Explicit caller responsibility avoids embedding arbitrary, hardcoded safety-policy heuristics (such as an ungrounded 25% horizon fraction or assumed period-1 constraint) within the mathematical optimization engine. Requiring explicit specification by the caller forces emergency response planners and upstream decision-makers to make an intentional, auditable determination of the life-safety response window for each disaster scenario.

---

## 2. SPECIFICATION TRACEABILITY IN APPROVED MILESTONE 2A

The requirement for $T_{\text{safety\_max}}$ originates across three approved Milestone 2A design artifacts (which remain frozen and unmodified):

1. **`PHASE6D_B_MILESTONE_2A_CONSTRAINT_TRACEABILITY.md` (§11):**
   > *"Mandatory Life-Safety Projects: $w_j = 1$ and $S_j \le T_{\text{safety\_max}}$ for all $j \in \mathcal{J}_{\text{mandatory}}$."*  
   > Traceability Category: Operational Policy Constraint (Inviolable).

2. **`PHASE6D_B_MILESTONE_2A_MATHEMATICAL_FORMULATION.md` (§3.2):**
   > *"Mandatory Selection & Safety Start Bound: $w_j = 1, \sum_{t=1}^{T_{\text{safety\_max}}} x_{j, t} = 1 \quad \forall j \in \mathcal{J}_{\text{mandatory}}$."*  
   > Defines the discrete time-indexed formulation where project start must occur in or before discrete period $T_{\text{safety\_max}}$.

3. **`PHASE6D_INFEASIBILITY_HARD_CONSTRAINT_AUDIT.md` (§4.1):**
   > *"Lists $S_j \le T_{\text{safety\_max}}$ as an inviolable operational requirement that must never be relaxed during diagnostic relaxation passes or solver assumption cores."*

---

## 3. ENGINE IMPLEMENTATION TRACEABILITY & VERIFICATION

The Milestone 2B implementation already adheres strictly to the Owner-Approved Option A policy across all components without requiring code alterations:

### 3.1 Input Contract Specification (`backend/app/recovery/optimization/schemas.py`)
- `RecoveryOptimizationRequest.max_safety_start_period`: Defined as `Optional[int] = None` with property alias `safety_max_period`. No numerical default is provided.
- `compute_canonical_input_fingerprint()`: Includes `"max_safety_start_period": request.max_safety_start_period` directly in the canonical UTF-8 JSON payload hashed via SHA-256, ensuring complete provenance and auditability.

### 3.2 Pre-Solve Request Validation (`backend/app/recovery/optimization/recovery_optimization_orchestrator.py`)
In `RecoveryOptimizationOrchestrator.validate_request()`:
```python
# Mandatory Life-Safety Deadline Authorization Check (RSK-M2-01, RSK-M2-07)
has_mandatory = any(c.is_tier1_mandatory for c in request.candidates)
if has_mandatory:
    if request.max_safety_start_period is None:
        errors.append(
            "Request contains mandatory life-safety projects but max_safety_start_period "
            "(T_safety_max) is None. An explicit authorized safety deadline is required."
        )
    elif request.max_safety_start_period < 1 or request.max_safety_start_period > request.planning_horizon_periods:
        errors.append(
            f"max_safety_start_period ({request.max_safety_start_period}) must be between "
            f"1 and planning_horizon_periods ({request.planning_horizon_periods})."
        )
```

### 3.3 Inviolable CP-SAT Hard Constraint (`backend/app/recovery/optimization/recovery_cpsat_solver.py`)
In `RecoveryCPSATSolver.solve()`:
```python
# Hard model constraint: strictly inviolable by solver assumptions
if c.is_tier1_mandatory:
    model.Add(w[pid] == 1)
    if self.request.max_safety_start_period is not None:
        t_safety = self.request.max_safety_start_period
        model.Add(start_var[pid] <= t_safety).OnlyEnforceIf(w[pid])
```
Because the constraint is added directly to the model rather than conditioned on an assumption literal, it cannot be relaxed or dropped during diagnostic relaxation passes.

### 3.4 Post-Solve Schedule Reconciliation (`backend/app/recovery/optimization/recovery_optimization_orchestrator.py`)
In Stage 11 of `reconcile_solution()`:
Independently verifies that every selected project with `is_tier1_mandatory == True` satisfies $S_j \le T_{\text{safety\_max}}$. Any returned schedule violating this condition is rejected.

---

## 4. EVALUATION OF POLICY OPTIONS & DECISION HISTORY

| Option ID | Policy Description | Evaluation & Operational Trade-offs | Owner Determination |
|---|---|---|:---:|
| **Option A** | **Caller-Mandatory Safety Deadline**<br>Caller must explicitly provide $T_{\text{safety\_max}}$; missing or out-of-horizon values fail closed. | **Strengths:** Maximum operational transparency; prevents hidden heuristic assumptions; preserves pure mathematical integrity.<br>**Trade-offs:** Requires upstream API callers to provide explicit deadline. | **SELECTED AND OWNER-APPROVED**<br>*(Approved on 2026-11-17)* |
| **Option B** | **Canonical Horizon Fraction Default**<br>Engine defaults to $\max(1, \lfloor \alpha \cdot T \rfloor)$ (e.g., $0.25 \cdot T$) when omitted. | **Weaknesses:** Embeds arbitrary safety heuristic in mathematical core; risks masking omissions by human disaster managers. | **REJECTED / NOT SELECTED**<br>*(Rejected on 2026-11-17)* |
| **Option C** | **Declarative Disaster Severity Mapping**<br>Engine or API layer infers $T_{\text{safety\_max}}$ dynamically from incident damage classifications. | **Weaknesses:** Violates phase separation and introduces cross-module coupling between Incident Management and CP-SAT Solver. | **REJECTED / NOT SELECTED**<br>*(Rejected on 2026-11-17)* |

---

## 5. GOVERNANCE STATUS & ACCEPTANCE SIGN-OFF

- **Policy Status:** **FORMALLY RESOLVED & OWNER-APPROVED (OPTION A)**
- **Decision Date:** **2026-11-17**
- **Milestone 2B Engine Status:** **100% CONFORMANT** (Pre-solve validation, CP-SAT formulation, reconciliation, and SHA-256 fingerprinting already strictly implement Option A).
- **Milestone 3 Integration Requirement:** Upstream API routers and workflow services implemented in Milestone 3 must validate that incoming requests with mandatory life-safety projects supply `max_safety_start_period`.
- **Milestone 3 Authorization Gate:** Milestone 3 remains **NOT STARTED** awaiting formal Milestone 2B closeout.
