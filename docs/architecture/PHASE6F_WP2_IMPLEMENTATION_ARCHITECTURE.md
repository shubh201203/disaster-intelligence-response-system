# DIRS Phase 6F / Accelerated Programme WP2: Implementation Architecture

**Document Version:** 1.0.0  
**Phase Mapping:** Phase 6F (Community Recovery Monitoring, Vulnerability Rescoring & Simulation Engine)  
**Execution Work Package:** WP2 (Accelerated Programme)  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Executive Summary

Phase 6F / WP2 operationalizes community recovery intelligence within the Disaster Intelligence and Response System (DIRS). While Phase 6D-B resolved the core multi-period capital allocation optimization problem and Phase 6E WP1 provided structural precedence graph analytics, WP2 connects infrastructure restoration back to human outcomes:
1. **Longitudinal Ward Monitoring:** Multi-sector utility tracking with exponential confidence decay modeling.
2. **Dynamic Vulnerability Rescoring:** Real-time synthesis of pure demographic vulnerability ($\phi_V$) with operational infrastructure restoration deficits and displacement pressure.
3. **Census Reconciliation Integrity:** Multi-record beneficiary deduplication and census cap conflict escalation.
4. **What-If Forward Simulation:** Deterministic, non-mutating in-memory scenario projection over policy adjustments, budget shifts ($\pm 50\%$), resource supply bottlenecks ($\mu \in [0.3, 1.0]$), and disaster recurrence shocks.

---

## 2. System Architecture & Component Mapping

```
                                      +---------------------------------------------+
                                      |   Frontend: DisasterSimulationView (React)  |
                                      |   - RecoverySimulationWorkbench             |
                                      |   - Parameter Perturbation Sliders (β, μ)   |
                                      |   - Dynamic Recharts Trajectory & Deficits  |
                                      +----------------------+----------------------+
                                                             | HTTP REST / JSON
                                                             v
+--------------------------------------------------------------------------------------------------------------------+
|                                           FastAPI Recovery Routing Layer                                           |
|  - GET  /api/v1/recovery/monitoring/community-metrics/summary                                                      |
|  - POST /api/v1/recovery/monitoring/vulnerability-rescore                                                          |
|  - POST /api/v1/recovery/simulation/what-if                                                                        |
+--------------------------+---------------------------------+---------------------------------+---------------------+
                           |                                 |                                 |
                           v                                 v                                 v
+--------------------------------------+   +------------------------------------+   +--------------------------------+
|      CommunityMonitoringService      |   |    VulnerabilityScoringService     |   |    RecoverySimulationService   |
| - Ward indicator aggregation         |   | - Pure mathematical phi_V & psi    |   | - 100% Non-mutating in-memory  |
| - Exponential decay: C(t)=C0*e^-λt   |   | - Two-branch census equation       |   | - Period-by-period trajectory  |
| - Freshness categorization           |   | - Mutual exclusivity enforcement   |   | - Bottleneck resource alerts   |
+--------------------------+-----------+   +-----------------+------------------+   +----------------+---------------+
                           |                                 |                                   |
                           +---------------------------------+-----------------------------------+
                                                             |
                                                             v
                                          +-------------------------------------+
                                          |          SQLAlchemy / DB Layer      |
                                          | - CommunityRecoveryMetric (read)    |
                                          | - RecoveryProject (read-only)       |
                                          | - RecoveryResource (read-only)      |
                                          | - RecoveryNeed (read-only)          |
                                          | - ZERO DB MIGRATIONS (phase6b head) |
                                          +-------------------------------------+
```

---

## 3. Core Service Components

### 3.1 `CommunityMonitoringService`
Located at `backend/app/recovery/services/community_monitoring_service.py`:
- **Confidence Decay:** $C(t) = C_0 \cdot \exp(-\lambda \cdot \Delta t)$, where $\lambda = 0.05/\text{day}$ (half-life $\approx 13.86$ days).
- **Freshness Classification:**
  - `FRESH`: $C(t) \ge 85.0\%$
  - `MODERATE`: $60.0\% \le C(t) < 85.0\%$
  - `STALE_AMBER`: $35.0\% \le C(t) < 60.0\%$
  - `EXPIRED_RED`: $C(t) < 35.0\%$
- **Multi-Sector Recovery Score:**
  $$S = 0.25 \cdot P_{\text{power}} + 0.25 \cdot P_{\text{water}} + 0.20 \cdot P_{\text{health}} + 0.15 \cdot P_{\text{schools}} + 0.15 \cdot P_{\text{livelihoods}}$$
- **Vulnerability Rescoring:**
  Fuses $\phi_V$ from `VulnerabilityScoringService` with infrastructure deficit score $I_{\text{def}}$ and displacement pressure $D_{\text{press}}$:
  $$\phi_{\text{rescored}} = \min\left(1.0, \max\left(0.0, \; 0.50 \cdot \text{eff\_base} + 0.35 \cdot (I_{\text{def}} \cdot \text{eff\_base}) + 0.15 \cdot D_{\text{press}}\right)\right)$$

### 3.2 `RecoverySimulationService`
Located at `backend/app/recovery/services/recovery_simulation_service.py`:
- **Read-Only / Non-Mutating Guarantee:** Guaranteed zero database mutations (`is_non_mutating=True`).
- **Dynamic Scenario Perturbations:**
  - Budget Multiplier ($\beta \in [0.5, 1.5]$).
  - Material Supply Factor ($\mu \in [0.3, 1.0]$).
  - Secondary Hazard Shock ($t_{\text{shock}}$, damage factor $\delta_{\text{damage}} \in [0.1, 0.5]$).
- **Outputs:** Period snapshot time series, bottleneck resource items, baseline vs. simulated makespan and score comparison.

### 3.3 `PopulationReconciliationService`
Located at `backend/app/recovery/services/population_reconciliation.py`:
- Salted HMAC-SHA256 beneficiary grouping.
- Duplicate candidate identification.
- Observation count conflict clustering (`CONF-{hash}`).
- Census baseline cap enforcement and `CONF-CENSUS-OVERCAP` review escalation.

---

## 4. Frontend Workbench Component

Located at `frontend/src/components/recovery/RecoverySimulationWorkbench.tsx`:
- Integrated into `frontend/src/pages/admin/DisasterSimulationView.tsx` under the dedicated tab "Community Recovery & What-If".
- Provides interactive sliders for budget scaling, supply disruption, and hazard shock triggers.
- Recharts multi-line chart rendering projected recovery score and unmet needs deficit across planning periods.
- Supply bottleneck alerts with exact deficit quantities.
- Real-time vulnerability rescoring calculator displaying demographic baseline, deficit math, and confidence freshness badge.

---

## 5. Architectural Invariants Preserved

1. **Frozen CP-SAT Solver Preserved:** The Phase 6D-B solver in `backend/app/recovery/optimization/` was untouched.
2. **Gate 2 Baseline Preserved:** All 23 certified Gate 2 baseline files and `task.md` remain 100% unmodified.
3. **Zero Database Migrations:** Migration head remains at `phase6b_recovery_foundation` across 40 operational tables.
4. **Strict RBAC:** Simulation execution is strictly guarded by `require_role("GOVT")` / `ADMIN`.
