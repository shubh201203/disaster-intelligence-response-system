# PHASE 5F-A — Algorithm Selection & Architectural Trade-off Analysis

**System:** Disaster Incident Response System (DIRS)  
**Phase:** 5F-A (Shelter & Volunteer Optimization: Research, Audit & Formulation)  
**Component:** Solver Engine Selection & Problem Decomposition Strategy  
**Classification:** ARCHITECTURAL SPECIFICATION & RESEARCH EVALUATION (PRE-IMPLEMENTATION)  
**Date:** 2026-09-22  

---

## 1. Solver Selection Evaluation

We systematically evaluate candidate mathematical programming frameworks for Shelter Assignment and Volunteer Assignment against four engineering criteria:
1. **Expressiveness:** Ability to natively enforce side constraints (demographic accessibility, medical certifications, binary facility activation).
2. **Computational Latency Target:** Capability to achieve real-time operational response targets ($\le 2.0\text{ seconds}$).
3. **Determinism:** Bit-exact reproducibility across consecutive runs.
4. **Maintenance Simplicity:** Minimal external dependencies and architectural consistency with Phase 5D.

### 1.1 Comparative Solver Candidate Matrix

| Algorithm / Solver Framework | Shelter Suitability | Volunteer Suitability | Expressiveness for Side Constraints | Proposed Latency Target ($N \le 50$) | Verdict & Rationale |
|---|---|---|---|---|---|
| **OR-Tools RoutingModel (`pywrapcp`)** | Inappropriate | Inappropriate | Poor (forced dummy TSP tours) | $> 2,000\text{ ms}$ | **REJECTED.** RoutingModel is designed for sequence-dependent vehicle tours (Phase 5E). Neither shelter evacuation nor volunteer staffing involves vehicle stop sequencing. Forcing them into CVRPTW would create unnecessary overhead. |
| **Pure Min-Cost Network Flow (MCF)** | High for pure flow; Inadequate for side constraints | Inadequate | Inadequate (cannot enforce binary activation or multi-skill matrices) | $\le 50\text{ ms}$ (target) | **REJECTED FOR CORE ENGINE.** While pure transportation flow solves in polynomial time, it cannot natively handle fixed shelter opening costs ($y_s$), accessibility matching ($A_s$), or multi-skill volunteer eligibility. |
| **Hungarian / Kuhn-Munkres Matching** | Inadequate | Partial (1-to-1 only) | Low (rigid square matrix assumption) | $\le 50\text{ ms}$ (target) | **REJECTED.** Volunteer assignment is a many-to-many generalized assignment problem ($d_{ikt} > 1$), violating 1-to-1 matching assumptions. |
| **OR-Tools CP-SAT (`ortools.sat.python.cp_model`)** | **Optimal** | **Optimal** | **Excellent** (Arbitrary linear integer, Boolean reification, soft constraints) | **$\le 200\text{ ms}$ (target)** | **SELECTED FOR BOTH MODULES.** Modern conflict-driven clause learning (CDCL) and integer presolve provide microsecond feasibility verification, exact integer arithmetic, and strict determinism. Proposed performance target: $< 100\text{ ms}$ at standard operational scales, to be experimentally validated after implementation. |

### 1.2 Selection Conclusion
- **Shelter Assignment Engine:** Formulated as a Capacitated Transportation Flow Problem with Facility Activation and Demographic Side Constraints, to be solved via **OR-Tools CP-SAT**.
- **Volunteer Assignment Engine:** Formulated as a Generalized Assignment Problem (GAP) with Multi-Skill Matrices and Workload Constraints, to be solved via **OR-Tools CP-SAT**.

---

## 2. Joint vs. Sequential vs. Independent Optimization Analysis

We rigorously evaluate whether DIRS should solve shelter and volunteer assignments jointly, sequentially, or independently:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ OPTION A: Fully Independent Parallel Solvers                                │
│   [Incidents] ──┬──> [Shelter Assignment Engine]   ──> [Shelter Plan]       │
│                 └──> [Volunteer Assignment Engine] ──> [Volunteer Plan]     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ OPTION B: Pipeline-Sequential Solvers (Coordinated)                         │
│   [Incidents] ──> [Shelter Assignment Engine] ──> [Shelters Activated]      │
│                                                          │                  │
│                                                          ▼ (Staffing Tasks) │
│                   [Volunteer Assignment Engine] <────────┘                  │
│                            │                                                │
│                            ▼                                                │
│                    [Volunteer Plan]                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ OPTION C: Joint Monolithic Program                                          │
│   min Z_joint = Z_shelter + Z_volunteer + Z_cross_coupling                  │
│   Subject to: All shelter and volunteer constraints in one single solve.     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 In-Depth Trade-Off Evaluation

| Evaluation Dimension | Option A: Independent | Option B: Sequential Pipeline | Option C: Joint Monolithic |
|---|---|---|---|
| **Computational Complexity** | Decoupled flow + decoupled assignment. Linear sum of decision spaces. | Sequential decoupled solves. Retains fast independent sub-models. | Joint optimization introduces a cross-product of shelter, incident, volunteer, skill, and temporal decision variables, increasing model size and potentially reducing scalability, interpretability, and ease of human override. It is therefore treated as a future research extension rather than part of the initial implementation. |
| **Organizational Alignment (NDMA/SDMA)** | Aligned. Different response desks manage shelters and personnel. | **Optimal.** Shelter openings create staffing tasks for volunteer coordination. | Unrealistic. Incident commanders do not solve shelter beds and volunteer callouts simultaneously on a single console. |
| **Fault Tolerance & Partial Data** | High. Missing volunteer records do not block shelter evacuations. | High. Gracefully defaults to Option A if shelter solve is bypassed. | Fragile. Incomplete data in one domain blocks all recommendations. |
| **Explainability & HITL Overrides** | Direct, modular explanations per domain. | Causal, transparent explanations: *"Volunteer V assigned to Shelter S staffing task."* | Monolithic black box. Overriding one volunteer can unexpectedly alter shelter evacuee flows across districts. |

### 2.2 Formal Architectural Recommendation

**RECOMMENDATION: Option B with Option A Fallback.**
1. **Default Mode (Option B - Sequential Coordination):**
   - Incident evacuation demands are solved first by the Shelter Assignment Engine.
   - When shelters are activated ($y_s = 1$), staffing demand tasks (e.g., 2 General Support Volunteers per 50 evacuees, 1 Medical Volunteer per shelter with medical needs) are automatically generated as secondary task demands.
   - The Volunteer Assignment Engine solves both incident-site response tasks and shelter-site staffing tasks.
2. **Standalone Mode (Option A - Independent Execution):**
   - Either solver can be invoked independently via dedicated endpoints (`/api/v1/optimization/shelters` and `/api/v1/optimization/volunteers`), ensuring operational resilience during fragmented communications.
3. **Monolithic Program (Option C) is REJECTED** from initial implementation due to combinatorial variable expansion, reduced human interpretability, and operational mis-alignment with multi-agency disaster command structures.
