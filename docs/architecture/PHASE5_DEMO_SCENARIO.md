# DIRS Phase 5A — Category 4 Cyclone Vardah Dynamic Re-Optimization Demo Scenario Specification

## Executive Summary

To visually and quantitatively evaluate the capabilities of the Phase 5 Optimization Layer during Phase 5L end-to-end verification, a realistic disaster simulation scenario has been designed: **Category 4 Cyclone Vardah Landfall in Coastal Chennai / Tamil Nadu**.

> [!IMPORTANT]
> **Performance Metric Classification Disclaimer:**  
> All comparison metrics, response delays, SLA compliance figures, and execution latencies in this document are **`ILLUSTRATIVE / SCENARIO TARGETS`** designed for experimental planning. **Actual values will be measured and reported after Phase 5 implementation.**

---

## 1. Scenario Context & Fixed Input Parameters

To guarantee an unbiased comparative evaluation, the Cyclone Vardah simulation supplies **identical scenario inputs** to Baseline A (Nearest Feasible Resource), Baseline B (First-Come-First-Served), and the Phase 5 Multi-Objective Optimizer:

- **Hazard Event**: Category 4 Severe Cyclonic Storm *Vardah*.
- **Impact Location**: Coastal Chennai (Velachery, Tambaram, Kovalam, Marina Beach).
- **Incident Demands**: 35 active disaster incidents (flooded residential areas, damaged hospitals, trapped coastal communities).
- **Relief Depots**: 4 major storage hubs (Puratchi Thalaivar Dr. M.G.R. Central Depot, Tambaram Relief Stockpile, Guindy Warehouse, Chengalpattu Depot).
- **Response Fleet**: 15 heavy trucks, 8 ambulances, 4 rescue boats.

---

## 2. Dynamic Event Timeline & Rerouting Workflow

### Timeline
1. **$T = 00:00$ (Initial Optimization Plan A)**:
   DIRS generates Initial Plan A allocating 12 supply trucks from Central Depot to Kovalam/Kelambakkam incidents via East Coast Road (ECR Highway).
2. **$T + 00:25$ (Dynamic Disruption Event)**:
   Storm surge causes a major road collapse and severe tree fall on ECR Highway near Kovalam Bridge. Local emergency team posts a verified `RoadBlockage` via the DIRS incident report interface (`severity=IMPASSABLE`).
3. **$T + 00:26$ (Event-Driven Re-Optimization Trigger)**:
   DIRS Ingestion Service receives the `RoadBlockage` update and automatically triggers Phase 5 Re-Optimization Engine.
4. **$T + 00:26.4$ (Plan B Execution `[TARGET]` Phase)**:
   The solver updates graph edge costs, sets $x_{\text{ECR},v} = 0$, reroutes the convoy via Old Mahabalipuram Road (OMR) / GST Road arterials, and reallocates supply assignments to Tambaram Depot to minimize total travel time.

---

## 3. Illustrative Target Metrics: Operational Baselines vs Dynamic Re-Optimization Target

> *Illustrative expected comparison metrics; actual values will be measured after Phase 5 implementation.*

| Metric Dimension | Baseline A: Nearest Resource `[PROJECTED]` | Baseline B: FCFS Queue `[PROJECTED]` | Phase 5 Optimization Engine `[TARGET]` | Evaluation Classification |
| :--- | :---: | :---: | :---: | :---: |
| **Mean Response Delay** | High delay (Gridlock on ECR) | High delay (Queue order ignoring geometry) | Reduced delay (Rerouted via open arterial OMR) | `ILLUSTRATIVE / SCENARIO TARGET` |
| **Critical Site SLA Compliance** | ~35.0% - 40.0% met | ~30.0% - 35.0% met | Target: $>90.0\%$ met | `ILLUSTRATIVE / SCENARIO TARGET` |
| **Unmet Medical & Water Demand** | ~30.0% unfulfilled | ~35.0% unfulfilled | Target: $<5.0\%$ unfulfilled | `ILLUSTRATIVE / SCENARIO TARGET` |
| **Total Fleet Traversal Distance** | High (Inefficient backtracking) | High (Long-distance dispatch) | Minimized (Optimized vehicle routing) | `ILLUSTRATIVE / SCENARIO TARGET` |
| **Optimization Runtime** | N/A (Static algorithm) | N/A (Static queue) | Target: $<2.0\text{ seconds}$ latency | `TARGET LATENCY BUDGET` |
| **Government HITL Approval** | Manual radio delay | Manual radio delay | 1-Click Command Center Approval | `GOVERNANCE TARGET` |

---

## 4. Empirical Evaluation Protocol for Phase 5L Verification

During sub-phase 5L implementation, the benchmark script (`scripts/demo_phase5_optimization.py`) will execute Baseline A, Baseline B, and the Phase 5 Optimizer against the fixed Cyclone Vardah dataset and compute exact empirical metrics using the formal definitions established in `PHASE5_OPTIMIZATION_OBJECTIVES.md`:

$$\text{Baseline Response Delay} = \frac{1}{|I|} \sum_{i \in I} \max(0, u_i^{\text{Baseline}} - T_i^{\text{target}})$$
$$\text{Optimized Response Delay} = \frac{1}{|I|} \sum_{i \in I} \max(0, u_i^{\text{Optimized}} - T_i^{\text{target}})$$
$$\text{Percentage Delay Improvement} = \frac{\text{Baseline Response Delay} - \text{Optimized Response Delay}}{\text{Baseline Response Delay}} \times 100\%$$
$$\text{Baseline SLA Compliance} = \frac{|\{i \in I \mid u_i^{\text{Baseline}} \le T_i^{\text{target}}\}|}{|I|} \times 100\%$$
$$\text{Optimized SLA Compliance} = \frac{|\{i \in I \mid u_i^{\text{Optimized}} \le T_i^{\text{target}}\}|}{|I|} \times 100\%$$
$$\text{Measured Optimization Runtime} = t_{\text{completion}} - t_{\text{invocation}} \quad (\text{ms})$$

All empirical results will be recorded in `docs/PHASE5_L_DEMO_RESULTS.md` upon completion of Phase 5L.
