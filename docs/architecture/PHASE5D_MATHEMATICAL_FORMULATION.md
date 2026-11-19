# DIRS Phase 5D — Multi-Commodity Resource Allocation Mathematical Formulation

## 1. Sets and Indices
- $I$: Set of active disaster incidents, indexed by $i \in I$.
- $D$: Set of available resource depots, indexed by $d \in D$.
- $R$: Set of resource commodities $r \in \{\text{WATER, FOOD, MEDICAL\_KITS, RESCUE\_EQUIPMENT, SANITATION\_KITS, TEMPORARY\_SHELTER\_SUPPLIES}\}$.

## 2. Input Parameters
- $Demand_{i,r} \ge 0$: Demanded quantity of commodity $r$ at incident $i$.
- $Supply_{d,r} \ge 0$: Inventory supply of commodity $r$ available at depot $d$.
- $Priority_i \in [0.0, 100.0]$: Priority score for incident $i$ (from Phase 4 Severity/Risk AI models).
- $SeverityMultiplier_i \in \{1.0, 2.0, 3.0\}$: Boost multiplier based on severity classification ($\text{CRITICAL}=3.0, \text{HIGH}=2.0, \text{MEDIUM/LOW}=1.0$).
- $t_{d,i} \ge 0$: Shortest path travel time in minutes from depot $d$ to incident $i$ (from Phase 5C `RoadGraphEngine`).
- $dist_{d,i} \ge 0$: Geodesic travel distance in kilometers from depot $d$ to incident $i$.
- $M_{d,i} \in \{0, 1\}$: Binary reachability mask ($1$ if path exists and unblocked, $0$ if impassable/unreachable).

## 3. Decision Variables
- $x_{d,i,r} \in \mathbb{Z}_{\ge 0}$: Integer quantity of commodity $r$ shipped from depot $d$ to incident $i$.
- $y_{d,i} \in \{0, 1\}$: Binary variable indicating if depot $d$ sends any shipment to incident $i$.
- $u_{i,r} \in \mathbb{Z}_{\ge 0}$: Integer unmet demand quantity of commodity $r$ at incident $i$.

## 4. Hard Operational Constraints
1. **Supply Inventory Bounds:**
   $$\sum_{i \in I} x_{d,i,r} \le Supply_{d,r}, \quad \forall d \in D, r \in R$$

2. **Demand Balance Formulation:**
   $$u_{i,r} = \max\left(0, Demand_{i,r} - \sum_{d \in D} x_{d,i,r}\right), \quad \forall i \in I, r \in R$$

3. **Shipment Linkage & Reachability Masking:**
   $$x_{d,i,r} \le \min(Supply_{d,r}, Demand_{i,r}) \cdot y_{d,i} \cdot M_{d,i}, \quad \forall d \in D, i \in I, r \in R$$

4. **Non-Negativity:**
   $$x_{d,i,r} \ge 0, \quad u_{i,r} \ge 0, \quad \forall d \in D, i \in I, r \in R$$

## 5. Multi-Objective Minimize Function
$$\min Z = \alpha_1 \sum_{i \in I} \sum_{r \in R} (Priority_i \cdot SeverityMultiplier_i \cdot u_{i,r}) + \alpha_2 \sum_{i \in I} \sum_{r \in R} \left(\frac{Priority_i^2}{10} \cdot SeverityMultiplier_i \cdot u_{i,r}\right) + \alpha_3 \sum_{d \in D} \sum_{i \in I} (t_{d,i} \cdot y_{d,i}) + \alpha_4 \sum_{d \in D} \sum_{i \in I} (dist_{d,i} \cdot y_{d,i})$$

**Multi-Objective Weight Calibration:**
- $\alpha_1 = 10.0$ (Primary priority-weighted shortage penalty)
- $\alpha_2 = 5.0$ (Quadratic penalty for high-severity shortages)
- $\alpha_3 = 1.0$ (Shipment travel time minimization)
- $\alpha_4 = 0.2$ (Travel distance minimization)
