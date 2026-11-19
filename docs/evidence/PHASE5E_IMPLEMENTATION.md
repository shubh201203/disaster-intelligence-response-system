# PHASE 5E — Implementation Architecture

**Component:** Multi-Depot Capacitated Vehicle Routing Optimization Engine  
**Module:** `backend/app/ai/optimization/routing.py`

---

## 1. Architecture Flow

```text
Phase 5D Resource Allocation Result (CommodityAllocationItems)
                         │
                         ▼
        convert_allocations_to_shipments()
     (Aggregates commodities by [origin_depot, incident])
                         │
                         ▼
             Phase 5C RoadGraphEngine
       (Generates NxN time, distance, reachability)
                         │
                         ▼
           VehicleRoutingEngine (OR-Tools)
     ┌────────────────────────────────────────┐
     │ • HARD-FORBIDDEN IMPASSABLE ARCS       │
     │ • Two-Dimensional Capacity (kg, m³)   │
     │ • Time Dimension (Travel + Service)    │
     │ • Soft Upper Bounds on Time Windows    │
     │ • Depot Compatibility Constraints      │
     │ • Return to Origin Depot Policy        │
     └────────────────────────────────────────┘
                         │
                         ▼
           RoutingResult & Unrouted Shipments
                         │
                         ▼
        VehicleRoutingService (Government HITL)
       (APPROVE / MODIFY / REJECT + AuditLog)
```

---

## 2. Key Modules
1. `backend/app/ai/optimization/routing.py`: Core OR-Tools `RoutingModel` implementation, Baselines A & B, conservation validator.
2. `backend/app/ai/optimization/routing_benchmark_dataset.py`: Reproducible calibrated benchmark generator (`DIRS-ROUTE-25`).
3. `backend/app/ai/optimization/routing_service.py`: Database orchestrator enforcing Government RBAC and override auditing.
