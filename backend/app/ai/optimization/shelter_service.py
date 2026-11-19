"""
DIRS Phase 5F-C — Shelter Evacuation Service Orchestrator
Connects database entities, invokes Phase 5C graph engine, executes CP-SAT shelter optimization,
persists OptimizationRun & OptimizationRecommendation DB records, and enforces Government HITL RBAC.
Classification: DECISION-SUPPORT WORKFLOW (HUMAN-IN-THE-LOOP REQUIRED)
"""
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.incident import Incident
from app.models.shelter import Shelter
from app.models.rescue import RoadBlockage
from app.models.audit import AuditLog
from app.models.optimization import OptimizationRun, OptimizationRecommendation, OptimizationOverrideLog

from app.ai.optimization.graph import RoadGraphEngine
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph
from app.ai.optimization.shelter import (
    ShelterEvacuationEngine,
    IncidentEvacuationInput,
    ShelterInput,
    ShelterEvacuationResult
)


class ShelterEvacuationService:
    """
    Phase 5F-C Shelter Evacuation Service Orchestrator.
    Handles data ingestion, network matrix computation, solver execution,
    recommendation persistence, and Government HITL authorization.
    """

    def __init__(self, solver_engine: Optional[ShelterEvacuationEngine] = None):
        self.solver_engine = solver_engine or ShelterEvacuationEngine()

    def load_graph_with_blockages(self, db: Session, num_nodes: int = 50) -> RoadGraphEngine:
        """Loads Phase 5C RoadGraphEngine and applies active RoadBlockage DB records."""
        graph = create_chennai_benchmark_graph(num_nodes=num_nodes)
        blockages = db.query(RoadBlockage).all()
        edges = list(graph.graph.edges())
        for b in blockages:
            if b.latitude and b.longitude and edges:
                u, v = edges[0]
                graph.apply_blockage(
                    blockage_id=b.id,
                    source_id=u,
                    target_id=v,
                    blockage_status=b.blockage_status or "IMPASSABLE",
                    delay_penalty_mins=b.delay_penalty_mins or 0.0
                )
        return graph

    def run_evacuation_optimization(
        self,
        db: Session,
        requesting_user_id: str,
        objective_weights: Optional[Dict[str, float]] = None,
        solver_time_limit_sec: float = 5.0
    ) -> OptimizationRun:
        """
        Executes full Phase 5F-C shelter evacuation optimization and persists DB recommendations.
        Strictly produces PROPOSED recommendations; no automatic operational dispatch.
        """
        # 1. Fetch DB Incidents & Shelters
        inc_records = db.query(Incident).filter(Incident.status != "CLOSED").all()
        shelter_records = db.query(Shelter).all()

        incidents_input: List[IncidentEvacuationInput] = []
        for inc in inc_records:
            incidents_input.append(IncidentEvacuationInput(
                incident_id=inc.id,
                title=inc.title,
                latitude=inc.latitude,
                longitude=inc.longitude,
                priority_score=inc.priority_score or 50.0,
                severity_level=inc.severity_level or "MEDIUM",
                disaster_type=inc.disaster_type or "FLOOD",
                people_affected=inc.people_affected or 1,
                evacuation_demographics=inc.evacuation_demographics or {}
            ))

        shelters_input: List[ShelterInput] = []
        for s in shelter_records:
            shelters_input.append(ShelterInput(
                shelter_id=s.id,
                name=s.name,
                latitude=s.latitude,
                longitude=s.longitude,
                total_capacity=s.total_capacity or 100,
                current_occupancy=s.current_occupancy or 0,
                status=s.status or "OPEN",
                accessibility_features=bool(s.accessibility_features),
                has_medical=bool(s.has_medical),
                has_food=bool(s.has_food),
                has_water=bool(s.has_water),
                power_available=bool(s.power_available),
                sanitation_available=bool(s.sanitation_available),
                disaster_compatibility=s.disaster_compatibility or []
            ))

        # 2. Ingest Phase 5C Graph Engine
        graph = self.load_graph_with_blockages(db)

        # 3. Solve Shelter Evacuation Problem
        if objective_weights:
            self.solver_engine.weights = objective_weights

        result: ShelterEvacuationResult = self.solver_engine.solve(
            incidents=incidents_input,
            shelters=shelters_input,
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
                "shelter_count": len(shelters_input),
                "total_displaced": result.total_evacuees_displaced,
                "total_sheltered": result.total_evacuees_sheltered,
                "total_unmet": result.total_evacuees_unmet
            },
            solver_metadata_json={
                "solver_name": "OR-Tools-CP-SAT",
                "solver_status": result.solver_status,
                "target_latency_sec": solver_time_limit_sec,
                "timing_breakdown": result.timing_breakdown
            },
            runtime_ms=result.solver_runtime_ms,
            optimality_gap=result.optimality_gap,
            feasibility_status=result.operational_feasibility,
            graph_version=result.graph_version
        )
        db.add(opt_run)
        db.commit()
        db.refresh(opt_run)

        # 5. Persist OptimizationRecommendation Records
        for item in result.assignments:
            rec = OptimizationRecommendation(
                run_id=opt_run.id,
                recommendation_type="SHELTER_EVACUATION",
                incident_id=item.incident_id,
                shelter_id=item.shelter_id,
                demographic_group=item.demographic_group,
                allocated_quantity=float(item.assigned_quantity),
                transit_time_minutes=item.travel_time_minutes,
                transit_distance_km=item.distance_km,
                objective_contribution=item.objective_contribution,
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

        # Update recommendation statuses to APPROVED
        for rec in run.recommendations:
            rec.status = "APPROVED"

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
        new_status = "MODIFIED" if action == "MODIFY" else "REJECTED"
        run.status = new_status
        for rec in run.recommendations:
            rec.status = new_status

        db.commit()
        db.refresh(override)
        return override
