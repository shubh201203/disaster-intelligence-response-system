# DIRS Phase 6F / Accelerated Programme WP2: Scoring & Confidence Methodology

**Document Version:** 1.0.0  
**Domain:** Quantitative Recovery Indicators, Confidence Decay & Vulnerability Rescoring  

---

## 1. Longitudinal Recovery Indicator Scoring

Community recovery progress is evaluated across five statutory sectors using authoritative weights summing to 1.00:

| Sector | Indicator Symbol | Sector Weight ($w_s$) | Source Observable |
| :--- | :--- | :--- | :--- |
| Power Grid | $P_{\text{pow}}$ | $0.25$ | Percentage of grid sub-stations operational |
| Potable Water (WASH) | $P_{\text{wat}}$ | $0.25$ | Percentage of population with safe piped water |
| Healthcare Facilities | $P_{\text{hlt}}$ | $0.20$ | Percentage of primary clinics / hospitals functional |
| Primary/Sec Schools | $P_{\text{sch}}$ | $0.15$ | Percentage of operational schools |
| Livelihoods Resumption | $P_{\text{liv}}$ | $0.15$ | Percentage of registered businesses / markets open |

### Overall Recovery Score Equation
$$S_{\text{recovery}} = \sum_{s \in \text{sectors}} w_s \cdot P_s = 0.25 P_{\text{pow}} + 0.25 P_{\text{wat}} + 0.20 P_{\text{hlt}} + 0.15 P_{\text{sch}} + 0.15 P_{\text{liv}}$$

$S_{\text{recovery}}$ is strictly bounded within $[0.0, 100.0]\%$.

---

## 2. Exponential Data Confidence Decay Modeling

Field damage assessments, needs assessments, and utility telemetry inevitably degrade in reliability over elapsed time unless refreshed by physical verification.

### Mathematical Formulation
$$C(t) = C_0 \cdot \exp(-\lambda \cdot \Delta t)$$

Where:
- $C_0$: Initial data confidence assigned at verification time ($0.0 \le C_0 \le 100.0\%$).
- $\Delta t$: Elapsed time in calendar days since `last_verified_at`:
  $$\Delta t = \frac{\max(0.0, \; (t_{\text{evaluation}} - t_{\text{last\_verified}})_{\text{seconds}})}{86400.0}$$
- $\lambda$: Statutory exponential decay constant, calibrated to a 14-day observation half-life ($t_{1/2} = 14\text{ days}$):
  $$\lambda = \frac{\ln(2)}{14.0} \approx 0.04951 \approx 0.05 \text{ days}^{-1}$$

### Freshness Status Categorization
The system assigns automated operational tags based on decayed confidence $C(t)$:

| Freshness Category | Confidence Threshold | Typical Age ($\Delta t$) | Operational Action Required |
| :--- | :--- | :--- | :--- |
| `FRESH` | $C(t) \ge 85.0\%$ | $\le 3.2$ days | Fully certified for autonomous optimization dispatch |
| `MODERATE` | $60.0\% \le C(t) < 85.0\%$ | $3.2 < \Delta t \le 10.2$ days | Usable; scheduled for routine re-inspection |
| `STALE_AMBER` | $35.0\% \le C(t) < 60.0\%$ | $10.2 < \Delta t \le 21.0$ days | Flagged with `uncertainty_flag=True`; priority dispatch |
| `EXPIRED_RED` | $C(t) < 35.0\%$ | $> 21.0$ days | Excluded from critical capital allocation until re-surveyed |

---

## 3. Dynamic Vulnerability Rescoring Synthesis

Vulnerability rescoring connects infrastructure restoration directly to human demographic vulnerability.

### Step 1: Base Demographic Vulnerability ($\phi_V$)
Evaluated by `VulnerabilityScoringService` using Phase 6D-A formulas:
$$\psi = 1.0 N_{\text{GEN}} + 2.5 N_{\text{ACC}} + 3.0 N_{\text{MED}} + 4.5 N_{\text{MED\_ACC}}$$
$$\phi_V = \begin{cases} 
\min\left(1.0, \; \frac{\psi}{\max(100.0, \; 0.20 \cdot P_{\text{census}})}\right), & \text{if } P_{\text{census}} > 0 \text{ (Known Baseline)} \\
\min\left(1.0, \; \frac{\psi}{500.0}\right), & \text{if } P_{\text{census}} \text{ missing/unknown}
\end{cases}$$

### Step 2: Infrastructure Restoration Deficit ($I_{\text{def}}$)
Deficit in each sector is the complement of operational restoration:
$$d_s = \frac{\max(0.0, 100.0 - P_s)}{100.0}$$
$$I_{\text{def}} = 0.25 d_{\text{pow}} + 0.25 d_{\text{wat}} + 0.20 d_{\text{hlt}} + 0.15 d_{\text{sch}} + 0.15 d_{\text{liv}} \in [0.0, 1.0]$$

### Step 3: Displacement Pressure ($D_{\text{press}}$)
$$D_{\text{press}} = \begin{cases}
\min\left(1.0, \; \frac{N_{\text{displaced}}}{\max(100.0, \; 0.15 \cdot P_{\text{census}})}\right), & \text{if } P_{\text{census}} > 0 \\
\min\left(1.0, \; \frac{N_{\text{displaced}}}{300.0}\right), & \text{if } P_{\text{census}} \le 0
\end{cases}$$

### Step 4: Rescored Vulnerability Synthesis
$$\text{eff\_base} = \max(0.05 \cdot I_{\text{def}}, \; \phi_V)$$
$$\phi_{\text{rescored}} = \min\left(1.0, \max\left(0.0, \; 0.50 \cdot \text{eff\_base} + 0.35 \cdot (I_{\text{def}} \cdot \text{eff\_base}) + 0.15 \cdot D_{\text{press}}\right)\right)$$

### Mathematical Guarantees
1. **Range Boundedness:** $\phi_{\text{rescored}} \in [0.0, 1.0]$.
2. **Deficit Sensitivity:** As utility systems are reconstructed ($I_{\text{def}} \to 0$) and shelters de-escalate ($D_{\text{press}} \to 0$), $\phi_{\text{rescored}}$ decreases monotonically.
3. **Auditability:** Complete mathematical provenance is attached to every evaluation in `audit_trail`.
