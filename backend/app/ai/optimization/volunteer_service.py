"""
DIRS Phase 5F-D — Volunteer Assignment Service Orchestrator
Connects database entities, invokes Phase 5C graph engine, executes CP-SAT volunteer optimization,
persists OptimizationRun & OptimizationRecommendation DB records, and enforces Government HITL RBAC.
Classification: DECISION-SUPPORT WORKFLOW (HUMAN-IN-THE-LOOP REQUIRED)
"""
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.user import User, UserRole, VolunteerProfile
from app.models.incident import Incident
from app.models.rescue import RoadBlockage
from app.models.audit import AuditLog
from app.models.optimization import OptimizationRun, OptimizationRecommendation, OptimizationOverrideLog

from app.ai.optimization.graph import RoadGraphEngine
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph
from app.ai.optimization.volunteer import (
    VolunteerAssignmentEngine,
    VolunteerInput,
    IncidentTaskInput,
    VolunteerAssignmentResult
)


class VolunteerAssignmentService:
    """
    Phase 5F-D Volunteer Assignment Service Orchestrator.
    Handles data ingestion, network matrix computation, solver execution,
    recommendation persistence, and Government HITL authorization.
    """

    def __init__(self, solver_engine: Optional[VolunteerAssignmentEngine] = None):
        self.solver_engine = solver_engine or VolunteerAssignmentEngine()

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

    def run_volunteer_optimization(
        self,
        db: Session,
        requesting_user_id: str,
        objective_weights: Optional[Dict[str, float]] = None,
        solver_time_limit_sec: float = 5.0
    ) -> OptimizationRun:
        """
        Executes full Phase 5F-D volunteer assignment optimization and persists DB recommendations.
        Strictly produces PROPOSED recommendations; no automatic operational dispatch.
        """
        # 1. Fetch DB Incidents & Volunteers
        inc_records = db.query(Incident).filter(Incident.status != "CLOSED").all()
        vol_profiles = db.query(VolunteerProfile).join(User).filter(User.is_active == True).all()

        incidents_input: List[IncidentTaskInput] = []
        for inc in inc_records:
            # required_skills e.g. {"MEDICAL": 2, "RESCUE": 1}
            req_skills = inc.required_skills or {}
            if req_skills:
                incidents_input.append(IncidentTaskInput(
                    incident_id=inc.id,
                    title=inc.title,
                    latitude=inc.latitude,
                    longitude=inc.longitude,
                    priority_score=inc.priority_score or 50.0,
                    severity_level=inc.severity_level or "MEDIUM",
                    required_skills=req_skills,
                    shifts=["SHIFT_1"],
                    task_durations={"SHIFT_1": 4.0}
                ))

        volunteers_input: List[VolunteerInput] = []
        for vp in vol_profiles:
            user = vp.user
            volunteers_input.append(VolunteerInput(
                volunteer_id=user.id,
                name=user.full_name or f"Volunteer {user.id[:8]}",
                latitude=vp.current_lat or 13.0827,
                longitude=vp.current_lng or 80.2707,
                skill_category=vp.skill_category or "GENERAL",
                skills=vp.skills or [],
                medical_certified=bool(vp.medical_certified),
                verification_status=vp.verification_status or "PENDING",
                is_available=bool(vp.is_available),
                assignment_status=vp.assignment_status or "UNASSIGNED",
                max_shift_hours=vp.max_shift_hours if vp.max_shift_hours is not None else 8.0,
                max_travel_time_mins=vp.max_travel_time_mins if vp.max_travel_time_mins is not None else 45.0,
                shift_availability=vp.shift_availability or []
            ))

        # 2. Build Graph Engine & Compute Travel Matrix
        graph = self.load_graph_with_blockages(db)

        # 3. Execute Solver
        engine = self.solver_engine
        if objective_weights:
            engine = VolunteerAssignmentEngine(weights=objective_weights)

        t_start = time.perf_counter()
        result: VolunteerAssignmentResult = engine.solve(
            volunteers=volunteers_input,
            incidents=incidents_input,
            graph_engine=graph,
            solver_time_limit_sec=solver_time_limit_sec
        )
        runtime_ms = (time.perf_counter() - t_start) * 1000.0

        # 4. Persist OptimizationRun
        run = OptimizationRun(
            status="PROPOSED",
            requesting_user_id=requesting_user_id,
            objective_config_json=objective_weights or engine.weights,
            input_snapshot_json={
                "incidents_count": len(incidents_input),
                "volunteers_count": len(volunteers_input),
                "total_tasks_demanded": result.total_tasks_demanded
            },
            solver_metadata_json={
                "solver_status": result.solver_status,
                "operational_feasibility": result.operational_feasibility,
                "total_tasks_assigned": result.total_tasks_assigned,
                "total_tasks_unmet": result.total_tasks_unmet,
                "unmet_percentage": result.unmet_percentage,
                "skill_unmet_counts": result.skill_unmet_counts,
                "deployed_volunteers_count": result.deployed_volunteers_count,
                "mean_transit_time_mins": result.mean_transit_time_mins,
                "total_transit_minutes": result.total_transit_minutes,
                "total_transit_km": result.total_transit_km,
                "objective_value": result.objective_value,
                "objective_breakdown": result.objective_breakdown,
                "explanation_summary": result.explanation_summary
            },
            runtime_ms=round(runtime_ms, 2),
            optimality_gap=result.optimality_gap,
            feasibility_status="FEASIBLE" if result.solver_status in ["OPTIMAL", "FEASIBLE"] else "INFEASIBLE",
            graph_version=result.graph_version
        )
        db.add(run)
        db.flush()

        # 5. Persist Proposed Recommendations
        for item in result.assignments:
            rec = OptimizationRecommendation(
                run_id=run.id,
                recommendation_type="VOLUNTEER_ASSIGNMENT",
                incident_id=item.incident_id,
                volunteer_id=item.volunteer_id,
                skill_category=item.skill_category,
                shift_id=item.shift_id,
                transit_time_minutes=item.transit_time_minutes,
                transit_distance_km=item.transit_distance_km,
                allocated_quantity=1.0,
                objective_contribution=item.objective_contribution,
                explanation=f"Assign {item.volunteer_name} ({item.skill_category}) to Incident {item.incident_id} [{item.shift_id}]. Transit: {item.transit_time_minutes} min.",
                status="PROPOSED"
            )
            db.add(rec)

        db.commit()
        db.refresh(run)
        return run

    def approve_plan(self, db: Session, run_id: str, approving_user: User) -> OptimizationRun:
        """
        Government Human-in-the-Loop Approval Gate.
        Strictly enforces UserRole.GOVT RBAC.
        Transitions run and recommendations to APPROVED, updates volunteer assignment status.
        """
        if approving_user.role != UserRole.GOVT:
            raise PermissionError(f"User {approving_user.id} with role {approving_user.role} is not authorized to approve optimization plans. GOVT role required.")

        run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
        if not run:
            raise ValueError(f"OptimizationRun {run_id} not found.")

        run.status = "APPROVED"

        # Update recommendation statuses and volunteer assignment statuses
        for rec in run.recommendations:
            rec.status = "APPROVED"
            if rec.volunteer_id:
                vp = db.query(VolunteerProfile).filter(VolunteerProfile.user_id == rec.volunteer_id).first()
                if vp:
                    vp.assignment_status = "ASSIGNED"

        # Audit Log
        audit = AuditLog(
            user_id=approving_user.id,
            action="APPROVE_VOLUNTEER_PLAN",
            target_entity="OptimizationRun",
            details={"approved_recommendations_count": len(run.recommendations)}
        )
        db.add(audit)
        db.commit()
        db.refresh(run)
        return run

    def override_plan(
        self,
        db: Session,
        run_id: str,
        overriding_user: User,
        action: str,  # MODIFY, REJECT
        justification: str,
        overridden_items: Optional[List[Dict[str, Any]]] = None
    ) -> OptimizationOverrideLog:
        """
        Government Human-in-the-Loop Override / Rejection.
        Strictly enforces UserRole.GOVT RBAC. Logs immutable audit trail.
        """
        if overriding_user.role != UserRole.GOVT:
            raise PermissionError(f"User {overriding_user.id} with role {overriding_user.role} is not authorized to override optimization plans. GOVT role required.")

        run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
        if not run:
            raise ValueError(f"OptimizationRun {run_id} not found.")

        run.status = "MODIFIED" if action == "MODIFY" else "REJECTED"

        if action == "REJECT":
            for rec in run.recommendations:
                rec.status = "REJECTED"

        override_log = OptimizationOverrideLog(
            run_id=run.id,
            user_id=overriding_user.id,
            action=action,
            original_value_json=run.solver_metadata_json,
            overridden_value_json={"overridden_items": overridden_items or []},
            justification_reason=justification
        )
        db.add(override_log)

        audit = AuditLog(
            user_id=overriding_user.id,
            action=f"OVERRIDE_VOLUNTEER_PLAN_{action}",
            target_entity="OptimizationRun",
            details={"action": action, "justification": justification}
        )
        db.add(audit)

        db.commit()
        db.refresh(override_log)
        return override_log
