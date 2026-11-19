# PHASE 5E — Scenario Results (ROUTE-01 to ROUTE-10)

Comprehensive evaluation of Phase 5E routing behavior across 10 controlled operational scenarios.

---

| Scenario Code | Scenario Description | Expected Operational Behavior | Measured Result | Status |
|---|---|---|---|---|
| **ROUTE-01** | Normal Multi-Depot Multi-Stop | Feasible tours serving multiple incidents from compatible depots | 8 vehicles deployed, 21 stops served, 0 late minutes | **PASSED** |
| **ROUTE-02** | Vehicle Scarcity (Few Available Vehicles) | Solver assigns high-priority shipments first; drops low-priority | Unrouted shipments marked with capacity diagnostic; CRITICAL served | **PASSED** |
| **ROUTE-03** | Capacity Bottleneck (Large Demands) | Vehicle weight/volume caps strictly enforced; multiple trips needed | Cumulative weight <= capacity at all stops; overweight rejected | **PASSED** |
| **ROUTE-04** | Critical Priority Competition | Critical incidents prioritized in schedule; 3x late penalty applied | 100% SLA compliance for CRITICAL incidents; mean critical arrival 65.49 min | **PASSED** |
| **ROUTE-05** | IMPASSABLE Road Blockage | Direct arc hard-forbidden; solver reroutes along alternate open edges | `IMPASSABLE ARC SELECTED = FALSE`; tour rerouted via alternate nodes | **PASSED** |
| **ROUTE-06** | DELAYED Road Segment | Delay penalty incorporated in transit cost; route adjusted if cost warrants | Travel duration increased by exact delay; optimal bypass chosen | **PASSED** |
| **ROUTE-07** | Time-Window Conflict | Tight delivery deadline causing potential lateness penalty | Soft upper-bound penalties correctly tracked; lateness quantified | **PASSED** |
| **ROUTE-08** | Completely Unreachable Incident | Graph partition or cut leaves incident disconnected | Incident marked explicitly as `UNROUTED` with unreachable reason | **PASSED** |
| **ROUTE-09** | Multi-Stop Consolidation | Vehicle visits multiple incidents along contiguous corridor | Multi-stop routes generated with sequential arrival/service/departure | **PASSED** |
| **ROUTE-10** | Zero Shipments / Inactive Demand | Clean termination without solver failure or exception | Empty route list returned with operational status `UNROUTABLE` | **PASSED** |
