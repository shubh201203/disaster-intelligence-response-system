# PHASE 5F-A — Objective Function Design, Unit Audit & Priority Dominance Analysis

**System:** Disaster Incident Response System (DIRS)  
**Phase:** 5F-A (Shelter & Volunteer Optimization: Research, Audit & Formulation)  
**Component:** Mathematical Optimization Objectives & Multi-Criteria Trade-offs  
**Classification:** MATHEMATICAL SPECIFICATION & RESEARCH FORMULATION (PRE-IMPLEMENTATION)  
**Date:** 2026-09-22  

---

## 1. Design Principles: Lexicographic-Compatible Calibrated Penalties

In disaster operations, life safety strictly dominates operational convenience:
$$\text{Life Safety Coverage} \gg \text{Vulnerable / Medical Protection} \gg \text{Response Transit Time} \gg \text{Operational Overhead}$$

To ensure numerical stability and microsecond solve times in OR-Tools CP-SAT without requiring multiple sequential solve passes, this hierarchy is established through **scale-separated penalty coefficients**.

---

## 2. Shelter Assignment Objective Function Audit

### 2.1 Mathematical Formulation
$$\min Z_{\text{shelter}} = Z_{\text{unmet\_gen}} + Z_{\text{unmet\_spec}} + Z_{\text{transit\_time}} + Z_{\text{transit\_dist}} + Z_{\text{activation}}$$

$$\min Z_{\text{shelter}} = \sum_{i \in I} \omega_i P_i \cdot \gamma_1 u_{i, \text{GEN}} + \sum_{i \in I} \omega_i P_i \left( \gamma_2 u_{i, \text{ACC}} + \gamma_3 u_{i, \text{MED}} + \gamma_4 u_{i, \text{MED\_ACC}} \right) + \sum_{i \in I} \sum_{s \in S} \left( \gamma_5 t_{is} + \gamma_6 d_{is} \right) x_{is} + \gamma_7 \sum_{s \in S} y_s$$

Where $x_{is} = \sum_{g \in G} x_{isg}$.

### 2.2 Term-by-Term Unit Audit & Coefficient Rationale

| Term | Mathematical Expression | Units | Coefficient Value | Representative Scale | Operational Rationale |
|---|---|---|---|---|---|
| **$Z_{\text{unmet\_gen}}$** | $\sum_i \omega_i P_i \gamma_1 u_{i, \text{GEN}}$ | person $\cdot$ priority $\cdot$ penalty | $\gamma_1 = 1,000$ | $10^5 \text{ to } 10^7$ | Heavy baseline penalty for leaving any displaced citizen unsheltered. |
| **$Z_{\text{unmet\_spec}}$ (ACC)** | $\sum_i \omega_i P_i \gamma_2 u_{i, \text{ACC}}$ | person $\cdot$ priority $\cdot$ penalty | $\gamma_2 = 2,000$ | $10^5 \text{ to } 10^7$ | Additional penalty for leaving vulnerable citizens without accessible shelter. |
| **$Z_{\text{unmet\_spec}}$ (MED)** | $\sum_i \omega_i P_i \gamma_3 u_{i, \text{MED}}$ | person $\cdot$ priority $\cdot$ penalty | $\gamma_3 = 2,500$ | $10^5 \text{ to } 10^7$ | Heavy penalty for leaving injured citizens without medical-equipped shelter. |
| **$Z_{\text{unmet\_spec}}$ (MED\_ACC)**| $\sum_i \omega_i P_i \gamma_4 u_{i, \text{MED\_ACC}}$ | person $\cdot$ priority $\cdot$ penalty | $\gamma_4 = 4,000$ | $10^5 \text{ to } 10^7$ | Combined penalty for individuals requiring both medical and accessibility care. |
| **$Z_{\text{transit\_time}}$** | $\sum_{i, s} \gamma_5 t_{is} x_{is}$ | person $\cdot$ minutes | $\gamma_5 = 10$ | $10^3 \text{ to } 10^5$ | Minimizes transit duration through the road network to safe shelters. |
| **$Z_{\text{transit\_dist}}$** | $\sum_{i, s} \gamma_6 d_{is} x_{is}$ | person $\cdot$ km | $\gamma_6 = 1$ | $10^2 \text{ to } 10^4$ | Secondary tie-breaker discouraging circuitous transit routes. |
| **$Z_{\text{activation}}$** | $\sum_s \gamma_7 y_s$ | active shelter | $\gamma_7 = 500$ | $10^3 \text{ to } 10^4$ | Prevents unnecessary facility fragmentation; consolidates staff and relief logistics. |

---

## 3. Volunteer Assignment Objective Function Audit

### 3.1 Mathematical Formulation
$$\min Z_{\text{volunteer}} = Z_{\text{unfilled\_gen}} + Z_{\text{unfilled\_med}} + Z_{\text{transit\_time}} + Z_{\text{transit\_dist}} + Z_{\text{activation}}$$

$$\min Z_{\text{volunteer}} = \sum_{i \in I} \sum_{k \in K} \sum_{t \in T} \omega_i P_i \cdot \lambda_1 u_{ikt} + \sum_{i \in I} \sum_{t \in T} \omega_i P_i \cdot \lambda_2 u_{i, \text{MED}, t} + \sum_{v \in V} \sum_{i \in I} \sum_{k \in K} \sum_{t \in T} (\lambda_3 \tau_{vi} + \lambda_4 \delta_{vi}) y_{vikt} + \lambda_5 \sum_{v \in V} \sum_{t \in T} z_{vt}$$

### 3.2 Term-by-Term Unit Audit & Coefficient Rationale

| Term | Mathematical Expression | Units | Coefficient Value | Representative Scale | Operational Rationale |
|---|---|---|---|---|---|
| **$Z_{\text{unfilled\_gen}}$** | $\sum_{i, k, t} \omega_i P_i \lambda_1 u_{ikt}$ | task $\cdot$ priority $\cdot$ penalty | $\lambda_1 = 1,000$ | $10^5 \text{ to } 10^7$ | Baseline penalty for failing to staff an emergency response task. |
| **$Z_{\text{unfilled\_med}}$** | $\sum_{i, t} \omega_i P_i \lambda_2 u_{i, \text{MED}, t}$| task $\cdot$ priority $\cdot$ penalty | $\lambda_2 = 1,500$ | $10^5 \text{ to } 10^7$ | **Medical-task unmet penalty**: Additional penalty for unfulfilled trauma/medical responder roles. |
| **$Z_{\text{transit\_time}}$** | $\sum_{v, i, k, t} \lambda_3 \tau_{vi} y_{vikt}$ | minutes | $\lambda_3 = 10$ | $10^2 \text{ to } 10^4$ | Minimizes arrival latency of field personnel to incident scenes. |
| **$Z_{\text{transit\_dist}}$** | $\sum_{v, i, k, t} \lambda_4 \delta_{vi} y_{vikt}$ | km | $\lambda_4 = 1$ | $10^1 \text{ to } 10^3$ | Prefers geographically proximate local volunteers. |
| **$Z_{\text{activation}}$** | $\sum_{v, t} \lambda_5 z_{vt}$ | deployed volunteer | $\lambda_5 = 50$ | $10^2 \text{ to } 10^3$ | Minimal mobilization barrier preventing excessive deployment for trivial demands. |

### 3.3 Explicit Pre-Implementation Consistency Decision on Medical Unmet Penalty

**Question:** In $Z_{\text{volunteer}}$, is an unfilled medical task ($k = \text{MEDICAL}$) intentionally included in BOTH the baseline task penalty $Z_{\text{unfilled\_gen}}$ ($\lambda_1$) and the specific medical penalty $Z_{\text{unfilled\_med}}$ ($\lambda_2$)?

**Resolution: YES, INTENTIONALLY INCLUDED IN BOTH TERMS (Hierarchical Penalty Surcharge).**

- **Mathematical Formulation:**
  For any non-medical task ($k \in \{\text{GENERAL}, \text{LOGISTICS}, \text{RESCUE}\}$), the marginal penalty for leaving it unfilled is:
  $$\lambda_{\text{effective}}(k) = \lambda_1 = 1,000$$
  For any medical task ($k = \text{MEDICAL}$), it appears in the baseline summation with weight $\lambda_1 = 1,000$ and in the medical surcharge summation with weight $\lambda_2 = 1,500$. Therefore, the combined marginal penalty for an unfilled medical task is:
  $$\lambda_{\text{effective}}(\text{MEDICAL}) = \lambda_1 + \lambda_2 = 1,000 + 1,500 = 2,500$$
- **Operational & Mathematical Rationale:**
  1. *Life-Safety Dominance:* This structure mirrors the Phase 5D commodity priority tiering where scarce life-saving commodities incur additive penalty multipliers.
  2. *Strict Priority Invariant:* The $2.5\times$ penalty ratio ($\frac{2,500}{1,000}$) mathematically guarantees that in any resource-constrained scenario where a medical responder could theoretically perform either a general task or a medical task, the solver is heavily penalized ($+1,500 \cdot \omega_i P_i$) if the medical task is neglected in favor of a general task.
  3. *Implementation Compactness:* Formulating it as $\lambda_1 \sum_{k} u_{ikt} + \lambda_2 u_{i, \text{MED}, t}$ avoids maintaining piecewise lookup tables and directly matches CP-SAT linear expression construction.
- **Implementation Binding:**
  All Phase 5F solver code, verification suites, and baseline comparison engines will implement this exact additive penalty: $\lambda_{\text{effective}}(\text{MEDICAL}) = \lambda_1 + \lambda_2 = 2,500$.

---

## 4. Priority Dominance & Worst-Case Trade-Off Analysis

A defensible optimization formulation must mathematically guarantee intended operational behaviors across worst-case trade-offs.

### 4.1 Trade-Off Case 1: Critical Unmet Evacuee vs. Long Travel Time
- **Scenario:** Can the solver choose to leave a citizen unassigned at a `CRITICAL` incident ($\omega_i = 5, P_i = 80$) to save an extreme travel time ($t_{is} = 60\text{ min}, d_{is} = 30\text{ km}$) to a distant open shelter?
- **Unassigned Cost Incurred:**
  $$\Delta Z_{\text{unmet}} = \omega_i P_i \gamma_1 = 5 \times 80 \times 1,000 = 400,000$$
- **Transit Cost Saved if Left Unassigned:**
  $$\Delta Z_{\text{transit}} = (\gamma_5 \times 60) + (\gamma_6 \times 30) = (10 \times 60) + (1 \times 30) = 630$$
- **Condition Check:**
  $$\Delta Z_{\text{unmet}} = 400,000 \gg 630 = \Delta Z_{\text{transit}}$$
  **Dominance Ratio:** $\frac{400,000}{630} \approx 635 : 1$.  
  *Proof:* The solver will ALWAYS assign the evacuee to any reachable shelter rather than leaving them unsheltered.

### 4.2 Trade-Off Case 2: Critical Incident vs. Low-Priority Incident Capacity Contention
- **Scenario:** A single shelter slot remains. Incident $A$ (`CRITICAL`, $\omega_A = 5, P_A = 90$) is $45\text{ min}$ away. Incident $B$ (`LOW`, $\omega_B = 1, P_B = 20$) is $5\text{ min}$ away. Will the solver assign the slot to $A$ despite the longer travel time?
- **Cost if Assigned to Critical Incident $A$ (leaving $B$ unassigned):**
  $$Z_A = (\text{transit } A) + (\text{unmet } B) = (10 \times 45 + 1 \times 20) + (1 \times 20 \times 1,000) = 470 + 20,000 = 20,470$$
- **Cost if Assigned to Low Incident $B$ (leaving $A$ unassigned):**
  $$Z_B = (\text{transit } B) + (\text{unmet } A) = (10 \times 5 + 1 \times 2) + (5 \times 90 \times 1,000) = 52 + 450,000 = 450,052$$
- **Difference:**
  $$Z_B - Z_A = 450,052 - 20,470 = +429,582 > 0$$
  *Proof:* Minimizing $Z$ strictly selects $A$ over $B$. The critical incident receives the shelter slot with a safety margin exceeding $400,000$ objective points.

### 4.3 Trade-Off Case 3: Medical Volunteer vs. General Task
- **Scenario:** A medical volunteer can be dispatched to a `HIGH` priority incident for a medical task ($\omega=3, P=75$) at $30\text{ min}$ transit, or used for a general relief task at an adjacent incident ($5\text{ min}$ transit).
- **Cost if Medical Task Assigned:**
  $$Z_{\text{med}} = (\text{transit } 30) + (\text{unmet general}) = (10 \times 30) + (3 \times 75 \times 1,000) = 300 + 225,000 = 225,300$$
- **Cost if General Task Assigned (leaving Medical Task unfilled):**
  $$Z_{\text{gen}} = (\text{transit } 5) + (\text{unmet medical}) = (10 \times 5) + (3 \times 75 \times (1,000 + 1,500)) = 50 + 562,500 = 562,550$$
- **Difference:**
  $$Z_{\text{gen}} - Z_{\text{med}} = +337,250 > 0$$
  *Proof:* The medical volunteer is strictly directed to the life-safety medical task.

---

## 5. Integer Scaling & Numerical Precision

To preserve exact integer arithmetic inside OR-Tools CP-SAT:
- All continuous parameters ($t_{is}, d_{is}, \tau_{vi}, \delta_{vi}, P_i$) are scaled by integer multiplier:
  $$\text{SCALE\_FACTOR} = 100$$
- An evacuee transit time of $12.34\text{ minutes}$ is converted to $1,234$ in the internal solver model.
- Upon solution extraction, all metrics are scaled back via division by $100.0$.
