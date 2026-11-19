# PHASE 5E – Routing Formulation

**System:** DIRS (Disaster Incident Response System)
**Component:** OR-Tools Capacitated Vehicle Routing with Time Windows (CVRPTW)
**Library:** `ortools 9.15.6755` (`pywrapcp.RoutingModel`)
**Benchmark:** DIRS-ROUTE-25 (SYNTHETIC CALIBRATED ROUTING BENCHMARK)

---

## 1. Problem Overview

Phase 5E solves a multi-depot, multi-commodity CVRPTW using Google OR-Tools. Inputs are
Phase 5D allocation results (CommodityAllocationItem) and Phase 5B vehicle models. The solver
assigns delivery tasks to vehicles while respecting capacity, time windows, and road constraints.

---

## 2. Sets and Parameters

| Symbol | Definition |
|--------|-----------|
| `V` | Set of vehicles `{v₁, …, vₙ}` |
| `N` | Set of delivery nodes (one per shipment task) |
| `D` | Set of depot nodes |
| `N⁺ = N ∪ D` | All nodes including depots |
| `A` | Set of arcs (road segments) |
| `A_IMP ⊆ A` | IMPASSABLE arc set (hard-forbidden) |
| `Cw(v)` | Weight capacity of vehicle `v` (kg) |
| `Cv(v)` | Volume capacity of vehicle `v` (m³) |
| `dij` | Travel distance arc `(i,j)` (m) |
| `tij` | Travel time arc `(i,j)` (s) |
| `si` | Service time at node `i` (s) |
| `[eᵢ, lᵢ]` | Hard time window for node `i` |
| `lᵢˢ` | Soft deadline for node `i` |
| `ROUTE_SCALE` | Integer scaling factor = 100 |

---

## 3. Decision Variables

| Variable | Domain | Meaning |
|----------|--------|---------|
| `xᵢⱼᵥ ∈ {0,1}` | Binary | 1 if vehicle `v` traverses arc `(i,j)` |
| `τᵢᵥ ∈ ℤ⁺` | Integer (scaled) | Arrival time of vehicle `v` at node `i` |
| `wᵢᵥ ∈ ℤ⁺` | Integer (scaled) | Weight load of vehicle `v` after node `i` |
| `uᵢᵥ ∈ ℤ⁺` | Integer (scaled) | Volume load of vehicle `v` after node `i` |
| `slackᵢᵥ ∈ ℤ⁺` | Integer (scaled) | Late minutes beyond soft deadline at node `i` |

In OR-Tools, `xᵢⱼᵥ` is implicitly encoded via `NextVar(i)` per vehicle route.

---

## 4. Dimensions

### 4.1 Weight Dimension (`'Weight'`)

```
wᵢᵥ ≤ Cw(v) * ROUTE_SCALE     ∀ v ∈ V, i ∈ N⁺
w₀ᵥ = 0                         (start at depot)
```

Registered via `AddDimensionWithVehicleCapacity`, coefficient = `demand_kg * ROUTE_SCALE`.

### 4.2 Volume Dimension (`'Volume'`)

```
uᵢᵥ ≤ Cv(v) * ROUTE_SCALE     ∀ v ∈ V, i ∈ N⁺
u₀ᵥ = 0
```

Registered via `AddDimensionWithVehicleCapacity`, coefficient = `demand_m3 * ROUTE_SCALE`.

### 4.3 Time Dimension (`'Time'`)

Transit callback: `tᵢⱼ + sᵢ` (travel time + service time at origin node).

```
τᵢᵥ ∈ [eᵢ, lᵢ]               (hard time window, set via CumulVar bounds)
```

Soft upper bounds set via `SetCumulVarSoftUpperBound(node, lᵢˢ, penalty)`.

---

## 5. Constraints

### 5.1 Hard Constraints Table

| # | Constraint | Mechanism |
|---|-----------|-----------|
| H-1 | Each delivery node served exactly once | `AddDisjunction` with penalty=0 (mandatory) |
| H-2 | Vehicle weight capacity | `'Weight'` dimension upper bound |
| H-3 | Vehicle volume capacity | `'Volume'` dimension upper bound |
| H-4 | IMPASSABLE arc hard-forbidden | `solver().Add(NextVar(i) != j)` |
| H-5 | Depot compatibility | `SetAllowedVehiclesForIndex` per task node |
| H-6 | Vehicle returns to starting depot | `SetArcCostEvaluatorOfAllVehicles` + fixed end depot |

### 5.2 IMPASSABLE Arc Hard-Forbidden Mechanism

For every arc `(i, j) ∈ A_IMP`:

```python
routing.solver().Add(
    routing.NextVar(i) != j
)
```

This injects a hard Constraint Satisfaction constraint directly into the CP solver. The arc is
unconditionally excluded from all vehicle routes. It is not penalised — it is **structurally
impossible**. If the only feasible path between two nodes traverses an IMPASSABLE arc, the
delivery is classified as unroutable.

### 5.3 Soft Constraints Table

| # | Constraint | Mechanism | Penalty |
|---|-----------|-----------|---------|
| S-1 | Soft time window (deadline) | `SetCumulVarSoftUpperBound` | `β₁ * CRITICAL_MULTIPLIER` |
| S-2 | Unrouted deliveries | `AddDisjunction` with finite penalty | `β₄ * 100` |

### 5.4 Depot Compatibility

```python
routing.SetAllowedVehiclesForIndex(allowed_vehicles, manager.NodeToIndex(node))
```

Only vehicles whose home depot matches the task's source depot are permitted to serve a node.

---

## 6. Objective Function

```
min Z = β₁·Σ(slackᵢ) + β₂·Σ(τ_end,v) + β₃·Σ(dᵢⱼ·xᵢⱼᵥ) + β₄·|V_used|

β₁ = 1000   (late arrival penalty)
β₂ = 10     (total route time)
β₃ = 1      (total distance)
β₄ = 100    (vehicle activation)
```

CRITICAL priority nodes use `CRITICAL_MULTIPLIER = 3`, tripling `β₁` for those nodes.

---

## 7. Integer Scaling

All continuous quantities are multiplied by `ROUTE_SCALE = 100` before being passed to OR-Tools,
which operates on integers internally. Results are divided by `ROUTE_SCALE` on extraction.

---

## 8. Phase 5D Conservation Equation

For every `(incident_id, commodity_type)` pair:

```
Σ_routed(qty) + Σ_unrouted(qty) == allocated(qty)
```

This invariant is enforced at the extraction layer and validated in the test suite (TEST-5E-11).
