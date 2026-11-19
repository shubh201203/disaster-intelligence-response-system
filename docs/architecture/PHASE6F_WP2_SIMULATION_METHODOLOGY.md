# DIRS Phase 6F / Accelerated Programme WP2: What-If Simulation Methodology

**Document Version:** 1.0.0  
**Service:** `RecoverySimulationService`  
**Location:** `backend/app/recovery/services/recovery_simulation_service.py`  

---

## 1. Objectives & Non-Mutating Invariants

Post-disaster infrastructure recovery is subject to deep policy uncertainties, budget delays, global supply shocks, and secondary hazard events. The What-If Recovery Simulation Engine provides executive leadership with forward-looking decision support under varying operational assumptions.

### Strict Non-Mutating Policy Safeguard
The simulation engine is **100% read-only with respect to operational database tables**:
- No database commits, rollbacks, inserts, or updates are triggered.
- Candidate project entities and resource demands are read from the database (or standardized prototypical recovery projects when database records are unpopulated) and simulated exclusively in transient memory.
- Responses explicitly certify `is_non_mutating: true`.

---

## 2. Forward State Projection Dynamics

For each planning period $t \in \{1, 2, \dots, T\}$ (with statutory period length $\Delta = 30$ calendar days):

### 2.1 Cash Flow State Transition
$$\text{Cash}_t = \text{Cash}_{t-1} + (\beta \cdot B_{\text{periodic}}) - \text{Spend}_t$$
Where:
- $\beta$: Capital budget multiplier ($\beta \in [0.5, 1.5]$).
- $B_{\text{periodic}}$: Periodic budget allocation.
- $\text{Spend}_t$: Sum of capital expended on active projects in period $t$.

### 2.2 Material Supply & Bottleneck Modeling
For each material category $m \in \{\text{CEMENT}, \text{STEEL}, \text{PIPING}, \text{TIMBER}, \text{MACHINERY}, \text{WORKFORCE}\}$:
$$\text{Available}_m = \mu \cdot \text{Demand}_m$$
Where $\mu \in [0.3, 1.0]$ is the material supply factor.
- If $\mu < 1.0$, project start concurrency is throttled:
  $$\text{ConcurrencyLimit} = \max(1, \lfloor 4 \cdot \mu \rfloor)$$
- Deficit items ($\text{Deficit}_m = \text{Demand}_m - \text{Available}_m$) are categorized into impact tiers:
  - `HIGH`: $\text{Deficit} / \text{Demand} > 0.30$
  - `MODERATE`: $\text{Deficit} / \text{Demand} \le 0.30$

### 2.3 Secondary Hazard Recurrence Shock
When `disaster_recurrence_shock = true` and $t = t_{\text{shock}}$:
- **Project Duration Setback:** In-flight projects suffer delay:
  $$\text{periods\_left} \leftarrow \text{periods\_left} + \max(1, \lceil \delta_{\text{damage}} \cdot \text{periods\_left} \rceil)$$
- **Displacement Surge:** Displaced population increases:
  $$N_{\text{displaced}} \leftarrow \lfloor N_{\text{displaced}} \cdot (1.0 + \delta_{\text{damage}}) \rfloor$$
- **Utility Setback:** Recovery score temporarily regresses:
  $$S_t \leftarrow \max(0.0, \; S_{t-1} \cdot (1.0 - 0.5 \cdot \delta_{\text{damage}}))$$

### 2.4 Sector Prioritization
Candidate projects are scheduled by a priority ranking function incorporating sector priority boosts $\gamma_s \ge 1.0$:
$$\text{Priority}(c) = \gamma_{\text{sector}(c)} \cdot \left(\frac{\text{RecoveryContribution}(c)}{\max(1.0, \text{Cost}(c))}\right)$$
Cash and start capacity are allocated greedily to the highest-priority projects first.

---

## 3. Comparative Analytics & Outcome Metrics

The simulation outputs a side-by-side comparison between the nominal baseline scenario ($\beta=1.0, \mu=1.0, \text{shock}=\text{false}$) and the perturbed scenario:

1. **Makespan Comparison:** Baseline completion period vs. simulated completion period.
2. **Target Milestone:** First period where $S(t) \ge 80.0\%$.
3. **Score Delta:** $\Delta S = S_{\text{simulated}}(T) - S_{\text{baseline}}(T)$.
4. **Trajectory Time Series:** Period-by-period snapshots capturing capital spend, active projects, cumulative completed projects, remaining displaced persons, recovery score, and unmet needs deficit.
