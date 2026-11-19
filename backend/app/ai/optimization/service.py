import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.incident import Incident
from app.models.resource import Resource
from app.models.rescue import RoadBlockage
from app.models.audit import AuditLog
from app.models.optimization import OptimizationRun, OptimizationRecommendation, OptimizationOverrideLog

from app.ai.optimization.graph import RoadGraphEngine
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph
from app.ai.optimization.allocation import (
    ResourceAllocationEngine,
    IncidentDemandInput,
    DepotSupplyInput,
    AllocationResult
)

class ResourceAllocationService:
    """
    Phase 5D Optimization Service Orchestrator.
    Connects database entities, invokes Phase 5C graph engine, calls CP-SAT solver,
    persists OptimizationRun & OptimizationRecommendation DB records, and enforces Government HITL RBAC.
    """

    def __init__(self, solver_engine: Optional[ResourceAllocationEngine] = None):
        self.solver_engine = solver_engine or ResourceAllocationEngine()

    def load_graph_with_blockages(self, db: Session, num_nodes: int = 50) -> RoadGraphEngine:
        """Loads Phase 5C RoadGraphEngine and applies active RoadBlockage DB records."""
        graph = create_chennai_benchmark_graph(num_nodes=num_nodes)
        blockages = db.query(RoadBlockage).all()
        for b in blockages:
            if b.latitude and b.longitude:
                # Find nearest graph node pair or mock segment
                nodes = list(graph.graph.nodes.keys())
                if len(nodes) >= 2:
                    graph.apply_blockage(
                        blockage_id=b.id,
                        source_id=nodes[0],
                        target_id=nodes[1],
                        blockage_status=b.blockage_status or "IMPASSABLE",
                        delay_penalty_mins=b.delay_penalty_mins or 0.0
                    )
        return graph

    def run_optimization(
        self,
        db: Session,
        requesting_user_id: str,
        objective_weights: Optional[Dict[str, float]] = None,
        solver_time_limit_sec: float = 2.0
    ) -> OptimizationRun:
        """Executes full Phase 5D resource allocation optimization and persists DB recommendations."""
        # 1. Fetch DB Incidents & Resources
        inc_records = db.query(Incident).filter(Incident.status != "CLOSED").all()
        res_records = db.query(Resource).all()

        incidents_input: List[IncidentDemandInput] = []
        for inc in inc_records:
            # Parse demands from ai_breakdown or default sphere demand
            demands = inc.ai_breakdown.get("predicted_demand", {}) if inc.ai_breakdown else {}
            if not demands:
                demands = {
                    "WATER": float(inc.people_affected * 15.0),
                    "FOOD": float(inc.people_affected * 2.5),
                    "MEDICAL_KITS": float(math.ceil(inc.people_affected / 20.0))
                }
            incidents_input.append(IncidentDemandInput(
                incident_id=inc.id,
                title=inc.title,
                latitude=inc.latitude,
                longitude=inc.longitude,
                priority_score=inc.priority_score or 50.0,
                severity_level=inc.severity_level or "MEDIUM",
                demands=demands,
                created_at_str=inc.created_at.isoformat() if inc.created_at else ""
            ))

        depots_input: List[DepotSupplyInput] = []
        for res in res_records:
            depots_input.append(DepotSupplyInput(
                depot_id=res.id,
                name=res.resource_name,
                latitude=res.location_lat or 13.0827,
                longitude=res.location_lng or 80.2707,
                supplies={res.category: float(res.available_quantity)}
            ))

        # 2. Ingest Phase 5C Graph Engine
        graph = self.load_graph_with_blockages(db)

        # 3. Solve Allocation Problem
        if objective_weights:
            self.solver_engine.weights = objective_weights

        result: AllocationResult = self.solver_engine.solve(
            incidents=incidents_input,
            depots=depots_input,
            graph_engine=graph,
            solver_time_limit_sec=solver_time_limit_sec
        )

        # 4. Persist OptimizationRun Record
        opt_run = OptimizationRun(
            requesting_user_id=requesting_user_id,
            status="PROPOSED",
            objective_config_json=self.solver_engine.weights,
            input_snapshot_json={
                "incident_count": len(incidents_input),
                "depot_count": len(depots_input),
                "graph_version": result.graph_version
            },
            solver_metadata_json={
                "solver_name": "OR-Tools-CP-SAT",
                "solver_status": result.solver_status,
                "target_latency_sec": solver_time_limit_sec
            },
            runtime_ms=result.solver_runtime_ms,
            optimality_gap=result.optimality_gap,
            feasibility_status=result.operational_feasibility
        )
        db.add(opt_run)
        db.commit()
        db.refresh(opt_run)

        # 5. Persist OptimizationRecommendation Records
        for item in result.allocations:
            rec = OptimizationRecommendation(
                run_id=opt_run.id,
                recommendation_type="RESOURCE_DISPATCH",
                incident_id=item.incident_id,
                depot_id=item.depot_id,
                commodity_category=item.commodity,
                allocated_quantity=item.quantity,
                proposed_route_json={
                    "travel_time_minutes": item.travel_time_minutes,
                    "distance_km": item.distance_km
                },
                explanation=item.explanation,
                status="PROPOSED"
            )
            db.add(rec)

        db.commit()
        db.refresh(opt_run)
        return opt_run

    def approve_plan(self, db: Session, run_id: str, govt_user_id: str, justification_reason: str) -> OptimizationOverrideLog:
        """Enforces Government HITL approval RBAC (`UserRole.GOVT`), logs audit entry, and updates status."""
        user = db.query(User).filter(User.id == govt_user_id).first()
        if not user or user.role != UserRole.GOVT:
            raise ValueError("Only authorized users with GOVT role can approve optimization plans.")

        run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
        if not run:
            raise ValueError(f"OptimizationRun {run_id} not found.")

        # Create system AuditLog entry
        audit = AuditLog(
            user_id=govt_user_id,
            action="OPTIMIZATION_PLAN_APPROVED",
            target_entity="OptimizationRun",
            details={"run_id": run_id, "justification": justification_reason}
        )
        db.add(audit)
        db.commit()

        # Create OptimizationOverrideLog record
        override = OptimizationOverrideLog(
            run_id=run.id,
            user_id=govt_user_id,
            action="APPROVE",
            original_value_json={"status": run.status},
            overridden_value_json={"status": "APPROVED"},
            justification_reason=justification_reason,
            audit_log_id=audit.id
        )
        db.add(override)
        run.status = "APPROVED"
        db.commit()
        db.refresh(override)
        return override

    def override_plan(
        self,
        db: Session,
        run_id: str,
        govt_user_id: str,
        action: str,  # MODIFY or REJECT
        overridden_value_json: Dict[str, Any],
        justification_reason: str
    ) -> OptimizationOverrideLog:
        """Enforces Government HITL modification/rejection RBAC and logs immutable override audit entry."""
        user = db.query(User).filter(User.id == govt_user_id).first()
        if not user or user.role != UserRole.GOVT:
            raise ValueError("Only authorized users with GOVT role can override optimization plans.")

        if action not in ("MODIFY", "REJECT"):
            raise ValueError(f"Invalid override action '{action}'. Must be MODIFY or REJECT.")

        run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
        if not run:
            raise ValueError(f"OptimizationRun {run_id} not found.")

        # Create system AuditLog entry
        audit = AuditLog(
            user_id=govt_user_id,
            action=f"OPTIMIZATION_PLAN_{action}ED",
            target_entity="OptimizationRun",
            details={"run_id": run_id, "action": action, "justification": justification_reason}
        )
        db.add(audit)
        db.commit()

        override = OptimizationOverrideLog(
            run_id=run.id,
            user_id=govt_user_id,
            action=action,
            original_value_json={"status": run.status},
            overridden_value_json=overridden_value_json,
            justification_reason=justification_reason,
            audit_log_id=audit.id
        )
        db.add(override)
        run.status = "MODIFIED" if action == "MODIFY" else "REJECTED"
        db.commit()
        db.refresh(override)
        return override
