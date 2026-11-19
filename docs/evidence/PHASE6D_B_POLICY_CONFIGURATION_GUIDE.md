# DIRS Phase 6D-B: Policy Configuration & Operational Administration Guide

**Subsystem:** Disaster Intelligence and Response System (DIRS)  
**Phase:** 6D-B — Recovery Prioritization, Equity-Constrained Allocation & Optimization Engine  
**Milestone:** Milestone 6 — Final Architecture Treatise & Permanent Freeze  
**Status:** Certified & Frozen  
**Date:** November 2026  

---

## 1. Introduction & Executive Principles

The Phase 6D-B Recovery Optimization Engine operates under strict statutory equity, fiduciary, and life-safety policy mandates. This guide provides disaster response administrators, government officials, and planning engineers with operational guidance for configuring optimization scenarios.

All scenario parameters must balance three fundamental objectives:
1. **Life-Safety First:** Protecting vulnerable human lives via mandatory Tier-1 projects.
2. **Geographic Equity:** Ensuring marginalized or hard-hit districts receive their fair share of recovery funds without political distortion.
3. **Fiscal Discipline:** Enforcing strict cash-flow solvency without deficit financing or currency depreciation.

---

## 2. Policy Parameters & Configuration Specifications

### 2.1 District Equity Targets ($\theta_d$)
- **Definition:** The minimum fraction of total recovery budget that must be allocated to projects in district $d$.
- **Format:** Key-value map `district_equity_targets: { "DIST_ID": float }` where $\theta_d \in [0.0, 1.0]$.
- **Sum Constraint:** $\sum_{d} \theta_d \le 1.0$.
- **Clamping Rule:** If the total demand of candidate projects in district $d$ is less than $\lceil \theta_d \cdot B_{\text{total}} \rceil$, the engine automatically clamps the floor to total district demand ($\min(\text{target}, \text{demand})$) to avoid artificial infeasibility.

### 2.2 Uncontacted Blackout District Ring-Fencing
- **Operational Context:** When communications, roads, or power infrastructure are severed in severe disaster zones, local damage assessments may be delayed or unavailable.
- **Mechanism:** Designating a district in `blackout_districts: ["DIST_ID"]` instructs the engine to ring-fence its equity quota ($\theta_d \cdot B_{\text{total}}$) into an untouched reserve escrow ($R_{\text{blackout}}$).
- **Inviolability:** The engine guarantees that the sum of expenditures across all other districts will not exceed $B_{\text{total}} - R_{\text{blackout}}$, preserving funds for when contact is re-established.

### 2.3 Fiscal Retention Rate ($\gamma$)
- **Definition:** The proportion of unspent cash in period $t$ that remains available in period $t+1$.
- **Field:** `fiscal_retention_rate: float` in range $[0.0, 1.0]$ (default: `1.0`).
- **Policy Scenarios:**
  - $\gamma = 1.0$: Standard multi-year disaster relief funds with 100% carryover.
  - $\gamma = 0.95$: Fiduciary escrow accounting with 5% maintenance/inflation contingency.
  - $\gamma = 0.0$: "Use-it-or-lose-it" annual fiscal appropriation lapses.

### 2.4 Early-Start Incentive Bonus
- **Definition:** Encourages the CP-SAT solver to schedule recovery projects as soon as their release period permits, rather than delaying until near the deadline.
- **Field:** `enable_early_start_bonus: bool` (default: `true`).
- **Mathematical Penalty:** Imposes a linear penalty $\beta_{i, t} = 1000 \cdot (t - r_i)$ on later start periods $t$, breaking ties in favor of immediate ground-breaking.

### 2.5 Caller-Mandatory Safety Deadlines (RSK-M2-07)
- **Mandate:** Tier-1 life-safety projects (e.g., flood barrier reinforcement, emergency drinking water purification, bridge shoring) cannot be subject to default solver relaxation.
- **Configuration Rule:** When any candidate has `is_tier1_mandatory = true`, the caller MUST provide an explicit `max_safety_start_period: int`.
- **Validation:** If omitted, the engine rejects the request immediately with HTTP 422 before starting solver execution.

---

## 3. Human-in-the-Loop Safeguards & UI Governance

To prevent accidental dispatch of resource-intensive optimization runs, the user interface enforces a 3-step administrative approval workflow:
1. **Scenario Inspection:** The user reviews the Candidate Projects Grid, Solvency parameters, and Equity quotas.
2. **Pre-Flight Validation Check:** The "Evaluate Scenario" button remains disabled if any validation errors exist (e.g., invalid horizon $T$, unassigned currencies, or duplicate project IDs).
3. **Modal Confirmation Dialog:** Upon clicking evaluate, an interactive checklist modal is displayed, requiring the administrator to confirm:
   - Planning horizon and period duration.
   - Total available budget and currency unit.
   - Number of candidate projects and mandatory life-safety items.
4. **Indeterminate Execution Guard:** During computation, the background UI is locked behind a modal backdrop with a live stopwatch to prevent concurrent conflicting runs.
