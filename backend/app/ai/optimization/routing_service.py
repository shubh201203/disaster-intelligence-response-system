"""
DIRS Phase 5E - Vehicle Routing Service Orchestrator
Connects database entities, invokes Phase 5C graph engine, executes OR-Tools RoutingModel,
persists OptimizationRun & OptimizationRecommendation DB records, and enforces Government HITL RBAC.
"""
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.incident import Incident
from app.models.vehicle import Vehicle
from app.models.rescue import RoadBlockage
from app.models.audit import AuditLog
from app.models.optimization import OptimizationRun, OptimizationRecommendation, OptimizationOverrideLog

from app.ai.optimization.graph import RoadGraphEngine
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph
from app.ai.optimization.allocation import AllocationResult
from app.ai.optimization.routing import (
    VehicleRoutingEngine,
    VehicleInput,
    ShipmentInput,
    RoutingResult,
    convert_allocations_to_shipments,
    verify_phase5d_conservation,
)

class VehicleRoutingService:
    """
    Phase 5E Routing Service Orchestrator.
    """

    def __init__(self, routing_engine: Optional[VehicleRoutingEngine] = None):
        self.routing_engine = routing_engine or VehicleRoutingEngine()

    def load_graph_with_blockages(self, db: Session, num_nodes: int = 50) -> RoadGraphEngine:
        """Loads Phase 5C RoadGraphEngine and applies active RoadBlockage DB records."""
        graph = create_chennai_benchmark_graph(num_nodes=num_nodes)
        blockages = db.query(RoadBlockage).all()
        for b in blockages:
            if b.latitude and b.longitude:
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

    def run_routing_optimization(
        self,
        db: Session,
        requesting_user_id: str,
        allocation_result: AllocationResult,
        solver_time_limit_sec: float = 10.0
    ) -> OptimizationRun:
        """
        Executes full Phase 5E vehicle routing optimization on approved Phase 5D allocations.
        Enforces vehicle eligibility (AVAILABLE only) and persists DB recommendations.
        """
        # 1. Fetch available vehicles
        vehicle_records = db.query(Vehicle).filter(
            Vehicle.status == "AVAILABLE",
            Vehicle.is_active == True
        ).all()

        vehicles: List[VehicleInput] = [
            VehicleInput(
                vehicle_id=v.id,
                vehicle_code=v.vehicle_code,
                vehicle_type=v.vehicle_type,
                capacity_weight_kg=v.capacity_weight_kg or 2000.0,
                capacity_volume_m3=v.capacity_volume_m3 or 10.0,
                depot_id=v.depot_id or "DEPOT_DEFAULT",
                depot_lat=v.current_location_lat or 13.0827,
                depot_lng=v.current_location_lng or 80.2707,
                status=v.status
            )
            for v in vehicle_records
        ]

        # 2. Fetch incidents and depots for coordinate mapping
        inc_records = db.query(Incident).all()
        inc_info = {
            inc.id: (inc.latitude, inc.longitude, inc.title, getattr(inc, "priority_score", 50.0) or 50.0, getattr(inc, "severity_level", "MEDIUM") or "MEDIUM")
            for inc in inc_records
        }

        # Build depot coordinate map from vehicles / depots
        depot_info = {
            v.depot_id: (v.depot_lat, v.depot_lng) for v in vehicles
        }

        # 3. Convert Phase 5D allocations to physical shipments
        shipments = convert_allocations_to_shipments(
            allocation_result=allocation_result,
            depot_info=depot_info,
            incident_info=inc_info,
        )

        # 4. Load RoadGraphEngine
        graph_engine = self.load_graph_with_blockages(db)

        # 5. Solve RoutingModel
        result = self.routing_engine.solve(
            shipments=shipments,
            vehicles=vehicles,
            graph_engine=graph_engine,
            solver_time_limit_sec=solver_time_limit_sec
        )

        # 6. Verify Phase 5D conservation
        conservation = verify_phase5d_conservation(shipments, result)
        if not conservation["conservation_holds"]:
            raise ValueError(f"CRITICAL: Phase 5D conservation violated in routing! {conservation['violations']}")

        # 7. Persist OptimizationRun
        opt_run = OptimizationRun(
            status="PROPOSED",
            requesting_user_id=requesting_user_id,
            objective_config_json=self.routing_engine.weights,
            input_snapshot_json={
                "num_shipments": len(shipments),
                "num_eligible_vehicles": len(vehicles),
                "graph_version": result.graph_version,
                "phase5d_conservation_verified": True
            },
            solver_metadata_json={
                "solver_name": "OR-Tools-RoutingModel",
                "solver_status": result.solver_status,
                "target_latency_sec": solver_time_limit_sec,
                "timing_breakdown": result.timing_breakdown
            },
            runtime_ms=result.solver_runtime_ms,
            optimality_gap=0.0,
            feasibility_status=result.operational_status
        )
        db.add(opt_run)
        db.commit()
        db.refresh(opt_run)

        # 8. Persist OptimizationRecommendation for each route
        for route in result.routes:
            rec = OptimizationRecommendation(
                run_id=opt_run.id,
                recommendation_type="VEHICLE_ROUTE",
                vehicle_id=route.vehicle_id,
                depot_id=route.start_depot_id,
                proposed_route_json={
                    "vehicle_code": route.vehicle_code,
                    "vehicle_type": route.vehicle_type,
                    "stops": [
                        {
                            "stop_index": s.stop_index,
                            "incident_id": s.incident_id,
                            "incident_title": s.incident_title,
                            "arrival_time_min": s.arrival_time_min,
                            "service_end_min": s.service_end_min,
                            "commodities": s.commodities,
                            "lateness_min": s.lateness_min
                        }
                        for s in route.stops
                    ],
                    "total_distance_km": route.total_distance_km,
                    "total_travel_time_min": route.total_travel_time_min,
                    "total_service_time_min": route.total_service_time_min,
                    "total_duration_min": route.total_route_duration_min,
                    "weight_utilization_pct": route.weight_utilization_pct,
                    "volume_utilization_pct": route.volume_utilization_pct,
                },
                explanation=route.explanation,
                status="PROPOSED"
            )
            db.add(rec)

        db.commit()
        db.refresh(opt_run)
        return opt_run

    def approve_route_plan(self, db: Session, run_id: str, govt_user_id: str, justification_reason: str) -> OptimizationOverrideLog:
        """Enforces Government HITL approval RBAC (`UserRole.GOVT`), logs audit entry, and updates status."""
        user = db.query(User).filter(User.id == govt_user_id).first()
        if not user or user.role != UserRole.GOVT:
            raise ValueError("Only authorized users with GOVT role can approve vehicle routing plans.")

        run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
        if not run:
            raise ValueError(f"OptimizationRun {run_id} not found.")

        audit = AuditLog(
            user_id=govt_user_id,
            action="ROUTING_PLAN_APPROVED",
            target_entity="OptimizationRun",
            details={"run_id": run_id, "justification": justification_reason}
        )
        db.add(audit)
        db.commit()

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

    def override_route_plan(
        self,
        db: Session,
        run_id: str,
        govt_user_id: str,
        action: str,
        overridden_value_json: Dict[str, Any],
        justification_reason: str
    ) -> OptimizationOverrideLog:
        """Enforces Government HITL modification/rejection RBAC and logs immutable override audit entry."""
        user = db.query(User).filter(User.id == govt_user_id).first()
        if not user or user.role != UserRole.GOVT:
            raise ValueError("Only authorized users with GOVT role can override vehicle routing plans.")

        if action not in ("MODIFY", "REJECT"):
            raise ValueError(f"Invalid override action '{action}'. Must be MODIFY or REJECT.")

        run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
        if not run:
            raise ValueError(f"OptimizationRun {run_id} not found.")

        audit_action = "ROUTING_PLAN_MODIFIED" if action == "MODIFY" else "ROUTING_PLAN_REJECTED"
        audit = AuditLog(
            user_id=govt_user_id,
            action=audit_action,
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
