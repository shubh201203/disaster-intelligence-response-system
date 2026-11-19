# DIRS — Capstone Viva Defense, Presentation Master & Evidence Checklist
## Disaster Intelligence and Response System (DIRS)

**Document Identifier:** `DIRS-CAPSTONE-VIVA-010`  
**Classification:** OFFICIAL / ACADEMIC & TECHNICAL DEFENSE  
**Target Release:** DIRS v5.2 (Capstone Release)  
**Parent Programme:** Phase 6G / Accelerated Work Package 4 (Capstone Packaging & Verification)  
**Publication Date:** November 18, 2026  
**Status:** Certified / Complete  

---

## 1. Master Capstone Presentation Script (10 / 15 / 20-Minute Tiers)

### 1.1 Presentation Timing Overview
* **Tier 1 (10 Minutes) — Executive & Operational Overview:** Problem statement $\to$ Multi-role response $\to$ Offline intake $\to$ CP-SAT portfolio optimization $\to$ Conclusion.
* **Tier 2 (15 Minutes) — Engineering Architecture Demonstration:** Tier 1 $+$ Precedence DAG Kahn/CPM-PL analysis $+$ Community recovery decay & What-If simulation.
* **Tier 3 (20 Minutes) — Comprehensive Technical Deep-Dive:** Tier 2 $+$ Dual-ledger solvency mathematics $+$ Infeasibility diagnostic cores $+$ Multi-user account isolation & idempotency safeguards.

---

### 1.2 Step-by-Step Presentation Script

#### Section 1: Opening & Problem Statement (Minutes 0:00 – 2:00)
> *"Good morning, esteemed committee members. In catastrophic disaster events—such as the recent severe inundation across the South Chennai corridor—emergency response systems face a critical dilemma: telecommunications blackouts disable frontline reporting, volunteer deployments lack centralized situational intelligence, and municipal post-disaster reconstruction is hindered by uncoordinated project dependencies and conflicting budget constraints.*
>
> *Today, we present **DIRS (Disaster Intelligence and Response System)**: a unified, role-aware operational platform uniting offline-resilient field intake, GIS situational command, infrastructure precedence analysis, community recovery simulation, and mathematical portfolio optimization."*

#### Section 2: Core Architecture & Role Topology (Minutes 2:00 – 4:00)
> *"DIRS is engineered with a React 18 / TypeScript frontend and a FastAPI / SQLAlchemy backend backed by 40 relational tables and Google OR-Tools CP-SAT. Rather than a one-size-fits-all portal, DIRS enforces strict least-privilege role boundaries across five personas: Citizens, Volunteers, NGOs, Government Command, and Optimization Administrators.*
>
> *Notice our route architecture: while citizens and volunteers focus on field reporting and rescue tasks, only Government officers have access to the Precedence DAG visualizer and engineering verification gates, and only authorized administrators access the mathematical solver."*

#### Section 3: Citizen Offline Intake & Synchronization Resilience (Minutes 4:00 – 7:00)
> *(Navigate to `/citizen/report` as `citizen@dirs.org`)*
> *"Let us simulate a live field scenario. During a cyclone, cell towers fail. A citizen encounters severe flash flooding at the Adyar Riverfront. In standard web applications, submitting a form without connectivity results in an immediate crash and lost field data.*
>
> *In DIRS, our local-first IndexedDB engine detects offline status. When the user clicks 'Save Local Draft', the payload is immediately serialized into our browser database under a compound index partitioning drafts by user ID and type.*
>
> *(Open `DraftSyncManager` drawer)*
> *Notice the Offline Resilience Banner. The draft is safe, persistent across device restarts, and completely isolated from any other user who might log in on this device. When connectivity restores, clicking 'Sync Now' triggers our synchronization state machine. A verified HTTP 201 response commits the report and records the server UUID. Our client idempotency guard prevents double-clicks from ever dispatching duplicate requests."*

#### Section 4: Volunteer Field Damage Assessment & Engineering Certification (Minutes 7:00 – 10:00)
> *(Log in as `volunteer@dirs.org`, open Field Damage Inspection tab)*
> *"Next, frontline responders evaluate structural destruction. Here, Volunteer Priya Patel submits a standardized damage assessment for the Adyar Health Centre Substation, noting moderate damage and an 85% assessor confidence rating.*
>
> *(Log in as `admin@dirs.gov`, open Command Center Tab 3)*
> *Now we switch to the Government Command Center. The Government Engineer reviews the incoming field inspection. Under statutory public safety regulations, volunteers cannot certify damage levels. The Government Engineer opens our Engineering Certification Gate modal, reviews the structural notes, commits an official 'VERIFY' decision with certified damage level 'MODERATE', and logs mandatory engineering rationale. This creates an unalterable audit trail in `recovery_override_logs`."*

#### Section 5: Precedence Graph Intelligence & Cycle Validation (Minutes 10:00 – 13:00) [15m & 20m Tiers]
> *(Open Command Center Tab 2: Infrastructure Precedence)*
> *"Once damage is certified, municipal reconstruction begins. Infrastructure projects cannot proceed arbitrarily—a water treatment plant cannot operate without power, and access roads must be cleared before transformer delivery.*
>
> *DIRS integrates a pure topological dependency engine. Our interactive SVG visualizer executes Kahn’s algorithm to generate a topological layout and performs Critical Path Method with Project Lag (CPM-PL) calculations. Red nodes and glowing edges indicate the Critical Path where Total Float equals zero.*
>
> *(Click 'Validate Dependency Link')*
> *To demonstrate mathematical integrity, let us test our Dry-Run Dependency Link Validator. If a planner attempts to introduce a candidate edge that creates a circular loop, our backend detects the cycle in linear time, rejects the candidate edge, and displays the exact circular loop path without writing a single invalid byte to the database."*

#### Section 6: Community Recovery Monitoring & What-If Simulation (Minutes 13:00 – 16:00) [15m & 20m Tiers]
> *(Navigate to `/admin/simulation`)*
> *"Simultaneously, municipal leadership must monitor human recovery. DIRS tracks ward-level indicators across five essential sectors: Power, Water, Health, Schools, and Livelihoods.*
>
> *Crucially, disaster field data ages rapidly. DIRS implements an exponential temporal confidence decay engine. Observations older than 24 hours degrade from 'FRESH' to 'MODERATE', 'STALE_AMBER', and finally 'EXPIRED_RED'. Under Vulnerability Rescoring, the platform computes a normalized vulnerability index $\phi \in [0.0, 1.0]$.*
>
> *Under our What-If Forward Simulation Workbench, administrators can simulate future trajectories under perturbed budgets, resource bottlenecks, or secondary hazard shocks before committing capital resources."*

#### Section 7: Mathematical Recovery Portfolio Optimization (Minutes 16:00 – 18:30) [20m Tier]
> *(Navigate to `/admin/recovery-optimization`)*
> *"Finally, we present our capstone solver engine: Phase 6D-B Mathematical Recovery Portfolio Optimization.*
>
> *Given a candidate portfolio of reconstruction projects, finite multi-period budgets, and specialized resource constraints, selecting the optimal schedule is an NP-hard combinatorial optimization problem. DIRS formulates this as a discrete integer programming model solved via Google OR-Tools CP-SAT.*
>
> *(Click 'Evaluate Optimal Portfolio Schedule')*
> *Notice our human-in-the-loop confirmation checklist and indeterminate stopwatch overlay. Upon solution, DIRS presents:
> 1. A 1-based periodic Gantt timeline mapping scheduled projects to exact coordinates.
> 2. A dual-ledger solvency matrix strictly separating integer Community Credit Units (CCU) from exact Decimal INR liquidity balances.
> 3. If a scenario is mathematically infeasible, our 4-tier diagnostic advisor extracts the minimal assumption core explaining the exact conflicting constraints.*
>
> *Every solver input is canonically fingerprinted with SHA-256 for cryptographic reproducibility."*

#### Section 8: Summary, Limitations & Future Roadmap (Minutes 18:30 – 20:00)
> *"In summary, DIRS v5.2 achieves complete horizontal and vertical integration across 85 API endpoints, 40 relational tables, and all five operational personas with 100% passing automated regressions.*
>
> *We explicitly disclose system boundaries: statutory capital infrastructure restoration is strictly separated from NGO commodity relief; live external cloud infrastructure and decentralized CRDT mesh synchronization are designated for Phase 7 Enterprise Hardening.*
>
> *Thank you. We now invite technical questions from the committee."*

---

## 2. Presentation Evidence Checklist

| # | Feature / Workflow | Persona / Role | Target Route / UI Element | Expected Evidentiary Artifact | Verification Status |
| :-: | :--- | :---: | :--- | :--- | :---: |
| 1 | **JWT Login & RBAC Redirection** | All Roles | `/login` $\to$ Role Dashboards | Token issued in `localStorage`; correct dashboard rendered | **VERIFIED** |
| 2 | **Offline Incident Draft Persistence** | `CITIZEN` | `/citizen/report` $\to$ Offline Banner | Persistent draft in IndexedDB `dirs_offline_drafts` with UUID | **VERIFIED** |
| 3 | **Queue Manager & Server Ack** | `CITIZEN` | `DraftSyncManager` Drawer | State transition `DRAFT` $\to$ `SYNCING` $\to$ `SYNCED` with server UUID | **VERIFIED** |
| 4 | **Municipal Recovery Card** | `CITIZEN` | `/citizen` Dashboard | Recovery score percentage and sector indicators | **VERIFIED** |
| 5 | **Field Damage Inspection Form** | `VOLUNTEER` | `/volunteer` (Field Inspection tab) | Damage assessment submission; `PENDING_VERIFICATION` status | **VERIFIED** |
| 6 | **Engineering Certification Gate** | `GOVT` | `/admin` (Field Inspections tab) | Certification modal commit; damage level certified in audit log | **VERIFIED** |
| 7 | **Precedence DAG Network View** | `GOVT` | `/admin` (Precedence Network tab) | Interactive SVG network with topological layout and node drawer | **VERIFIED** |
| 8 | **CPM-PL Critical Path Highlighting**| `GOVT` | Precedence Visualizer | Red glowing nodes/edges with Total Float $TF=0$ | **VERIFIED** |
| 9 | **Dry-Run Cycle Validation Alert** | `GOVT` | Dry-Run Validator Modal | Red rejection alert displaying exact circular cycle path | **VERIFIED** |
| 10 | **Vulnerability Rescoring & Decay** | `GOVT` | `/admin/simulation` | Normalized score $\phi \in [0.0, 1.0]$, confidence decay factor | **VERIFIED** |
| 11 | **What-If Trajectory Simulation** | `GOVT` | Simulation Workbench | Trajectory curves under budget multiplier & bottleneck analysis | **VERIFIED** |
| 12 | **CP-SAT Portfolio Schedule** | `ADMIN` / `GOVT` | `/admin/recovery-optimization` | 1-based periodic Gantt timeline and status banner `OPTIMAL` | **VERIFIED** |
| 13 | **Dual-Ledger Solvency Matrix** | `ADMIN` / `GOVT` | Optimization View | Parallel integer CCU ledger and exact Decimal INR cash ledger | **VERIFIED** |
| 14 | **NGO Inventory Scoping Toggle** | `NGO` | `/ngo` Dashboard | "All Hubs" vs "My Org Only" filtering by `owner_id = user.id` | **VERIFIED** |
| 15 | **Institutional Governance Notice** | `NGO` | `/ngo` Dashboard | Warning demarcating statutory capital reconstruction boundaries | **VERIFIED** |

---

## 3. Technical Viva Defense Questions & Answers

### Domain 1: System Architecture & Data Engineering
**Q1: Why did DIRS choose a monolithic FastAPI backend with client-side IndexedDB rather than a distributed microservices architecture?**  
*Answer:* In emergency response, operational simplicity, deterministic transaction boundaries, and low deployment friction take precedence over microservice decomposition. FastAPI provides high-throughput async I/O with native OpenAPI contracts. Client-side IndexedDB provides zero-latency offline persistence directly within the browser origin sandbox without requiring local daemon installations on field responder tablets.

**Q2: How does DIRS guarantee that switching user accounts on a shared field tablet does not leak previous user data?**  
*Answer:* DIRS implements three-tier account isolation: (1) IndexedDB read queries filter strictly on compound index `['user_id', 'draft_type']`; (2) store-level mutating functions verify that `expectedUserId` matches the stored `user_id` and throw security violation exceptions on mismatch; (3) TanStack React Query memory caches parameterize query keys with `user?.id` (`['resources-ngo', user?.id]`), instantly partitioning the cache upon principal change.

---

### Domain 2: Optimization Mathematics & CP-SAT Solver
**Q3: How does the Phase 6D-B solver prevent floating-point inaccuracies in multi-million rupee budgets?**  
*Answer:* The optimization engine enforces strict decimal separation: integer Community Credit Units (CCU) are modeled directly as discrete integer domain variables in CP-SAT, while currency amounts (INR) are handled using Python's exact `Decimal` arithmetic converted to exact integer paisa/cents for solver bounds. Dual-ledger balances are reconciled post-solve without binary floating-point representation.

**Q4: What happens if an optimization scenario is mathematically infeasible?**  
*Answer:* The solver does not crash or fabricate approximate schedules. It sets `is_feasible = false`, suppresses the Gantt timeline, and invokes our 4-Tier Infeasibility Diagnostic Advisor. The advisor extracts the minimal assumption core identifying whether the conflict arises from mandatory project deadlines, resource capacity deficits, budget limits, or circular dependencies.

---

### Domain 3: Infrastructure Precedence & Topological Graph Theory
**Q5: What algorithm does DIRS use for cycle detection in project dependency graphs, and what is its computational complexity?**  
*Answer:* DIRS uses Kahn’s algorithm for topological sorting and cycle detection. It maintains in-degree counts for all vertices and iteratively dequeues zero-in-degree nodes. Its time complexity is $O(|V| + |E|)$, which executes in milliseconds even on dense infrastructure networks. If the processed node count is less than $|V|$, a cycle exists, and the service traverses back-edges via Depth-First Search (DFS) to extract the exact ordered circular path.

**Q6: What is the difference between Total Float and Free Float in CPM-PL?**  
*Answer:* Total Float ($TF_i = LS_i - ES_i$) is the total amount of time project $i$ can be delayed from its early start without delaying the overall project makespan. Free Float ($FF_i = \min_{j \in \text{succ}(i)} (ES_j - EF_i - L_{ij})$) is the time project $i$ can be delayed without delaying the early start of any immediate successor. Projects with $TF_i = 0$ constitute the Critical Path.

---

### Domain 4: Community Recovery & Vulnerability Modeling
**Q7: How does DIRS model confidence decay in disaster observation data?**  
*Answer:* Observation confidence decays exponentially with time: $\text{Confidence}(t) = \text{BaseConfidence} \times e^{-\lambda \Delta t}$, where $\Delta t$ is the elapsed hours since observation and $\lambda = 0.015$ (half-life of approximately 46 hours). This ensures that stale reports submitted days earlier have diminished influence on current vulnerability rescoring compared to recent field inspections.

---

### Domain 5: Security, RBAC & Institutional Boundaries
**Q8: Why does DIRS prohibit NGOs from directly pledging capital infrastructure reconstruction projects in the database?**  
*Answer:* Forensic schema inspection confirms that the operational database lacks an `ngo_pledges` table or an organization foreign key on `recovery_projects`. Storing NGO pledge claims in arbitrary text fields (such as `supplier_info`) violates data integrity. Statutory public works require formal municipal procurement and financial sanctions. DIRS guides NGOs to focus on humanitarian commodity logistics while displaying formal governance notices regarding bilateral capital partnerships.
