# PHASE 5F-A — Implementation Sequence & Integration Roadmap

**System:** Disaster Incident Response System (DIRS)  
**Phase:** 5F-A (Shelter & Volunteer Optimization: Research, Audit & Formulation)  
**Component:** Engineering Implementation Architecture & Interface Roadmap  
**Date:** 2026-09-22  

---

## 1. Phased Implementation Roadmap (Pending Human Authorization)

Implementation will strictly proceed in a sequenced, modular fashion to maintain architectural isolation:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: CORE OPTIMIZATION ENGINES (Pure Mathematical Models)               │
│ • backend/app/ai/optimization/shelter.py                                    │
│   - ShelterAssignmentEngine (OR-Tools CP-SAT)                               │
│   - Baselines A, B, C (Nearest, Largest Capacity, Priority-First)           │
│ • backend/app/ai/optimization/volunteer.py                                  │
│   - VolunteerAssignmentEngine (OR-Tools CP-SAT)                             │
│   - Baselines A, B (Nearest Qualified, FCFS Qualified)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: BENCHMARK DATASETS & CALIBRATION                                   │
│ • backend/app/ai/optimization/shelter_benchmark_dataset.py                  │
│ • backend/app/ai/optimization/volunteer_benchmark_dataset.py                │
│   - Deterministic PRNG seeding (seed=42)                                    │
│   - Scalability tiers: DIRS-SHELTER-(10..100), DIRS-VOL-(10..100)           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: SERVICE LAYER & GOVERNMENT HITL RBAC                               │
│ • backend/app/ai/optimization/shelter_service.py                            │
│ • backend/app/ai/optimization/volunteer_service.py                          │
│   - Enforces UserRole.GOVT check for approval                               │
│   - Generates OptimizationOverrideLog and AuditLog upon override            │
│   - Generates structured explainability JSON                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: AUTOMATED TESTING & FORENSIC BENCHMARKING                          │
│ • tests/backend/test_phase5f_shelter.py (Scenarios S1-S8, Invariants)       │
│ • tests/backend/test_phase5f_volunteer.py (Scenarios V1-V8, Invariants)     │
│ • scripts/benchmark_phase5f.py & scripts/forensic_phase5f_audit.py          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 5C Graph Engine Integration Interface

Phase 5F directly consumes the road network engine implemented in Phase 5C (`backend/app/ai/optimization/graph.py`):

```python
# 1. Querying Distance & Travel Time Matrices for Shelter Assignment
shelter_matrix: DistanceTimeMatrix = graph_engine.compute_distance_time_matrix(
    origin_ids=[inc.id for inc in incidents],
    destination_ids=[sh.id for sh in shelters]
)

# 2. Querying Distance & Travel Time Matrices for Volunteer Assignment
volunteer_matrix: DistanceTimeMatrix = graph_engine.compute_distance_time_matrix(
    origin_ids=[vol.id for vol in volunteers],
    destination_ids=[inc.id for inc in incidents]
)
```

### Dynamic Blockage & Graph Version Handling:
1. **Network Version Binding:** The solver records `graph_version = graph_engine.get_graph_version()` in `solver_metadata_json`.
2. **Dynamic Blockage Response:** If road segments become `BLOCKED`, Phase 5C Dijkstra shortest paths yield $t_{is} \ge \text{IMPASSABLE\_THRESHOLD}$. The CP-SAT solver sets $R_{is} = 0$, structurally preventing assignments across blocked edges.
3. **Stale Plan Detection:** When a government officer reviews a proposed plan, the service verifies that the current `graph_version` matches the proposal. If a new blockage has occurred, a `STALE_NETWORK_WARNING` is raised.

---

## 3. Phase 5E Vehicle Routing Integration Interface

While Phase 5F shelter optimization decides *which* shelter evacuees are assigned to, physical transportation requires coordination with Phase 5E:

```text
[Phase 5F Shelter Plan: x_is evacuees from Incident i to Shelter s]
                             │
                             ▼
     [Evacuation Transport Request Generation]
     - Origin: Incident i coordinates
     - Destination: Shelter s coordinates
     - Passenger Load: x_is persons
                             │
                             ▼
[Future Phase 5E Passenger Routing Extension]
Dispatches municipal buses / vans to execute evacuation routes.
```

### Bi-directional Supply Chain Coupling:
When shelter $s$ is activated ($y_s = 1$), its occupancy increases by $\sum_i x_{is}$. This generates immediate secondary relief supply demands:
- Potable water ($15\text{ Litres/person/day}$)
- Dry food rations ($2\text{ packs/person/day}$)
- Medical triage kits

These secondary demands can be directly fed into **Phase 5D (Multi-Commodity Resource Allocation)** and **Phase 5E (Vehicle Routing)** to keep active evacuation shelters provisioned.
