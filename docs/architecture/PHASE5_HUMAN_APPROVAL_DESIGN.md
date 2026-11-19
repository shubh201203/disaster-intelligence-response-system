# DIRS Phase 5A — Government Human-in-the-Loop (HITL) Approval Workflow & Audit Design

## Executive Summary

Autonomous AI dispatch of emergency resources poses significant ethical, legal, and operational risks during critical disaster scenarios. In strict accordance with DIRS capstone governance principles, the Phase 5 Optimization Layer operates under a **Human-in-the-Loop (HITL)** architecture. 

The optimization engine generates mathematical recommendations for resource allocation and vehicle routing; however, **no vehicle dispatch order or resource transfer is executed until a authorized Government Command Center Official reviews, modifies (if necessary), and explicitly approves the recommendation.**

---

## 1. Recommendation Lifecycle & State Transition Diagram

```
                 ┌───────────────────────────┐
                 │ Incident Data & AI Models │
                 └─────────────┬─────────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │  Optimization Triggered   │
                 └─────────────┬─────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Recommendation State: OPTIMIZED_PROPOSED                    │
│ - Solver computes optimal route & allocation plan          │
│ - Rendered in Government Command Center UI                  │
└──────────────┬───────────────┬───────────────┬──────────────┘
               │               │               │
       Approved│       Rejected│       Modified│
               ▼               ▼               ▼
┌────────────────────┐ ┌──────────────┐ ┌─────────────────────┐
│ APPROVED_BY_GOVT   │ │REJECTED_BY_GOVT│ │ MODIFIED_BY_GOVT    │
│ - Dispatches orders│ │- Re-runs with│ │ - User adjusts route│
│ - Logged to Audit  │ │  new params  │ │ - Re-validates      │
└────────────────────┘ └──────────────┘ └──────────┬──────────┘
                                                   │
                                                   ▼
                                         ┌────────────────────┐
                                         │ APPROVED_BY_GOVT   │
                                         └────────────────────┘
```

---

## 2. Proposed Database Models for Phase 5B

To maintain immutable auditability, three database tables will be added in Phase 5B under `backend/app/models/optimization.py`:

```python
# Conceptual Schema for Phase 5B Implementation
class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), nullable=False, default="PROPOSED")  # PROPOSED, APPROVED, REJECTED, MODIFIED
    solver_execution_time_ms = Column(Float, nullable=False)
    total_unmet_demand = Column(Float, nullable=False)
    total_fleet_travel_time_mins = Column(Float, nullable=False)
    optimality_gap_percent = Column(Float, nullable=False)
    input_snapshot_json = Column(JSON, nullable=False)  # Frozen copy of incidents/inventory at run time

class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("optimization_runs.id"), nullable=False)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    depot_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    vehicle_id = Column(Integer, nullable=True)
    commodity_category = Column(String(50), nullable=False)
    allocated_quantity = Column(Float, nullable=False)
    scheduled_arrival_time = Column(DateTime(timezone=True), nullable=True)
    route_waypoints_json = Column(JSON, nullable=True)

class OptimizationOverrideLog(Base):
    __tablename__ = "optimization_override_logs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("optimization_runs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Govt User
    original_value_json = Column(JSON, nullable=False)
    overridden_value_json = Column(JSON, nullable=False)
    justification_reason = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
```

---

## 3. Mandatory Integration with Existing `AuditLog` System

When a Government User approves or modifies an optimization plan, an immutable audit entry is automatically published to `AuditLog`:

- `action`: `"OPTIMIZATION_PLAN_APPROVED"` or `"OPTIMIZATION_PLAN_OVERRIDDEN"`
- `performed_by`: `User.id` (Must have role `"GOVT"`)
- `details`: Includes `run_id`, solver runtime, percentage of demand satisfied, list of modified allocation lines, and user justification text.

---

## 4. Government Command Center UI Requirements

1. **Interactive Plan Preview**:
   Displays an interactive Leaflet/PostGIS map layer showing proposed vehicle trajectories, depot pickup points, dynamic road blockages (highlighted in red), and incident delivery points.
2. **Side-by-Side Override Editor**:
   Allows Government Officials to click any vehicle route or commodity allocation and manually adjust quantities or reassign vehicles.
3. **Mandatory Justification Capture**:
   If an official overrides an AI recommendation (e.g. diverting a water truck from Incident A to Incident B), the UI enforces a mandatory text input field requiring a clear operational justification reason before submission.
