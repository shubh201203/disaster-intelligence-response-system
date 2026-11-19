import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint

from app.models.incident import Incident
from app.models.user import User
from app.models.recovery import (
    RecoveryAssessment,
    RecoveryNeed,
    RecoveryProject,
    ProjectDependency,
    RecoveryResource,
    CommunityRecoveryMetric,
    RecoveryOverrideLog
)
from app.schemas.recovery import (
    RecoveryAssessmentCreate,
    RecoveryAssessmentUpdate,
    RecoveryAssessmentVerify,
    RecoveryAssessmentSupersede,
    RecoveryNeedCreate,
    RecoveryProjectCreate,
    RecoveryProjectUpdate,
    RecoveryProjectApprove,
    RecoveryProjectStatusUpdate,
    ProjectDependencyCreate,
    RecoveryResourceCreate,
    RecoveryResourceUpdate,
    CommunityRecoveryMetricCreate,
    PrecedenceGraphResponse,
    PrecedenceGraphNode,
    PrecedenceGraphEdge,
    PrecedenceCPMInfo,
    PrecedenceEdgeValidateRequest,
    PrecedenceEdgeValidateResponse
)
from app.recovery.services.project_dependency_service import (
    ProjectDependencyService,
    ProjectActivity,
    DependencyEdge,
    CyclicDependencyError
)
from app.core.security import hash_beneficiary_id, mask_person_name
from app.services.audit_service import AuditService


class RecoveryService:

    # ==========================================================================
    # 1. RECOVERY ASSESSMENTS
    # ==========================================================================

    @staticmethod
    def create_assessment(db: Session, data: RecoveryAssessmentCreate, inspector_id: str) -> RecoveryAssessment:
        # Validate incident
        inc = db.query(Incident).filter(Incident.id == data.incident_id).first()
        if not inc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {data.incident_id} not found")

        code = f"ASM-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"
        geom_point = None
        if db.bind and db.bind.dialect.name == "postgresql":
            geom_point = ST_SetSRID(ST_MakePoint(data.longitude, data.latitude), 4326)

        assessment = RecoveryAssessment(
            assessment_code=code,
            incident_id=data.incident_id,
            inspector_id=inspector_id,
            sector=data.sector.upper(),
            facility_name=data.facility_name,
            damage_level=data.damage_level.upper(),
            is_operational=data.is_operational,
            estimated_reconstruction_cost=data.estimated_reconstruction_cost,
            structural_notes=data.structural_notes,
            evidence_media_urls=data.evidence_media_urls or [],
            cv_assessment_id=data.cv_assessment_id,
            latitude=data.latitude,
            longitude=data.longitude,
            geom=geom_point,
            assessment_version=1,
            is_current_version=True,
            deduplication_cluster_id=data.deduplication_cluster_id or f"CLUSTER-{uuid.uuid4().hex[:6].upper()}",
            reconciliation_status="UNRECONCILED",
            provenance_tier="TIER_2_GOVT_OFFICIAL",
            data_confidence=100.0,
            freshness_status="FRESH",
            verification_status="PENDING_VERIFICATION"
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        AuditService.log_action(
            db=db,
            user_id=inspector_id,
            action="CREATE_RECOVERY_ASSESSMENT",
            target_entity="RecoveryAssessment",
            details={"assessment_code": code, "facility": data.facility_name, "sector": data.sector}
        )
        return assessment

    @staticmethod
    def verify_assessment(db: Session, assessment_id: str, data: RecoveryAssessmentVerify, officer_id: str) -> RecoveryAssessment:
        asm = db.query(RecoveryAssessment).filter(RecoveryAssessment.id == assessment_id).first()
        if not asm:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

        act = data.action.upper()
        if act not in ("VERIFY", "REJECT"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be VERIFY or REJECT")

        asm.verification_status = "VERIFIED" if act == "VERIFY" else "REJECTED"
        asm.verified_by_id = officer_id
        asm.verified_at = datetime.now(timezone.utc)
        if data.verified_cost is not None and act == "VERIFY":
            asm.estimated_reconstruction_cost = data.verified_cost
        if data.notes:
            asm.structural_notes = f"{asm.structural_notes or ''} [Verification Notes: {data.notes}]"

        db.commit()
        db.refresh(asm)

        AuditService.log_action(
            db=db,
            user_id=officer_id,
            action=f"{act}_RECOVERY_ASSESSMENT",
            target_entity="RecoveryAssessment",
            details={"assessment_id": assessment_id, "action": act, "notes": data.notes}
        )
        return asm

    @staticmethod
    def supersede_assessment(db: Session, old_id: str, data: RecoveryAssessmentSupersede, inspector_id: str) -> RecoveryAssessment:
        old_asm = db.query(RecoveryAssessment).filter(RecoveryAssessment.id == old_id).first()
        if not old_asm:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Historical assessment not found")
        if not old_asm.is_current_version:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only supersede an active current-version assessment")

        new_version_num = old_asm.assessment_version + 1
        new_code = f"{old_asm.assessment_code}-V{new_version_num}"
        geom_point = None
        if db.bind and db.bind.dialect.name == "postgresql":
            geom_point = ST_SetSRID(ST_MakePoint(old_asm.longitude, old_asm.latitude), 4326)

        new_asm = RecoveryAssessment(
            assessment_code=new_code,
            incident_id=old_asm.incident_id,
            inspector_id=inspector_id,
            sector=old_asm.sector,
            facility_name=old_asm.facility_name,
            damage_level=data.new_damage_level.upper(),
            is_operational=data.is_operational,
            estimated_reconstruction_cost=data.new_estimated_cost,
            structural_notes=data.structural_notes or old_asm.structural_notes,
            evidence_media_urls=old_asm.evidence_media_urls,
            latitude=old_asm.latitude,
            longitude=old_asm.longitude,
            geom=geom_point,
            assessment_version=new_version_num,
            is_current_version=True,
            deduplication_cluster_id=old_asm.deduplication_cluster_id,
            reconciliation_status="SUPERSEDED",
            provenance_tier="TIER_2_GOVT_OFFICIAL",
            data_confidence=100.0,
            freshness_status="FRESH",
            verification_status="PENDING_VERIFICATION"
        )
        db.add(new_asm)
        db.flush()

        # Update old version pointer
        old_asm.is_current_version = False
        old_asm.superseded_by_id = new_asm.id
        old_asm.reconciliation_status = "SUPERSEDED"

        # Log override
        log = RecoveryOverrideLog(
            project_id=None,
            user_id=inspector_id,
            action="ASSESSMENT_SUPERSEDE",
            original_value={"assessment_id": old_id, "version": old_asm.assessment_version, "damage": old_asm.damage_level},
            new_value={"new_assessment_id": new_asm.id, "version": new_version_num, "damage": data.new_damage_level},
            justification_reason=data.justification_reason
        )
        db.add(log)
        db.commit()
        db.refresh(new_asm)

        return new_asm

    @staticmethod
    def list_assessments(
        db: Session,
        incident_id: Optional[str] = None,
        sector: Optional[str] = None,
        current_only: bool = True
    ) -> List[RecoveryAssessment]:
        q = db.query(RecoveryAssessment)
        if current_only:
            q = q.filter(RecoveryAssessment.is_current_version == True)
        if incident_id:
            q = q.filter(RecoveryAssessment.incident_id == incident_id)
        if sector:
            q = q.filter(RecoveryAssessment.sector == sector.upper())
        return q.order_by(RecoveryAssessment.created_at.desc()).all()

    # ==========================================================================
    # 2. RECOVERY NEEDS & CENSUS RECONCILIATION
    # ==========================================================================

    @staticmethod
    def create_need(db: Session, data: RecoveryNeedCreate) -> RecoveryNeed:
        # Beneficiary identity pseudonymization
        hashed_id = hash_beneficiary_id(data.raw_beneficiary_id) if data.raw_beneficiary_id else None
        masked_name = mask_person_name(data.household_head_name) if data.household_head_name else None

        # Double-counting reconciliation against census baseline cap
        census_cap = data.census_baseline_population
        displaced = data.displaced_persons
        is_reconciled = False
        notes = None

        if displaced > census_cap:
            displaced = census_cap
            is_reconciled = True
            notes = f"Displaced headcount capped from {data.displaced_persons} to census baseline {census_cap}."

        need = RecoveryNeed(
            assessment_id=data.assessment_id,
            ward_code=data.ward_code,
            district=data.district,
            sector=data.sector.upper(),
            affected_households=data.affected_households,
            displaced_persons=displaced,
            vulnerable_persons=min(data.vulnerable_persons, displaced),
            beneficiary_id_hash=hashed_id,
            household_head_name_masked=masked_name,
            potable_water_demand_liters_day=data.potable_water_demand_liters_day,
            temporary_shelter_units_needed=data.temporary_shelter_units_needed,
            livelihood_support_households=data.livelihood_support_households,
            unmet_need_score=data.unmet_need_score,
            census_baseline_population=census_cap,
            is_reconciled=is_reconciled,
            reconciliation_notes=notes
        )
        db.add(need)
        db.commit()
        db.refresh(need)
        return need

    @staticmethod
    def list_needs(db: Session, ward_code: Optional[str] = None, sector: Optional[str] = None) -> List[RecoveryNeed]:
        q = db.query(RecoveryNeed)
        if ward_code:
            q = q.filter(RecoveryNeed.ward_code == ward_code)
        if sector:
            q = q.filter(RecoveryNeed.sector == sector.upper())
        return q.order_by(RecoveryNeed.data_timestamp.desc()).all()

    # ==========================================================================
    # 3. RECOVERY PROJECTS & APPROVAL GATES
    # ==========================================================================

    @staticmethod
    def create_project(db: Session, data: RecoveryProjectCreate, user_id: str) -> RecoveryProject:
        code = f"PRJ-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"
        geom = None
        if db.bind and db.bind.dialect.name == "postgresql" and data.latitude is not None and data.longitude is not None:
            geom = ST_SetSRID(ST_MakePoint(data.longitude, data.latitude), 4326)

        prj = RecoveryProject(
            project_code=code,
            need_id=data.need_id,
            title=data.title,
            description=data.description,
            sector=data.sector.upper(),
            priority_tier=data.priority_tier.upper(),
            priority_score=data.priority_score,
            status="PROPOSED",
            estimated_cost=data.estimated_cost,
            actual_expenditure=0.0,
            funding_source=data.funding_source,
            time_indexed_cost_profile=data.time_indexed_cost_profile or [data.estimated_cost],
            estimated_duration_days=data.estimated_duration_days,
            lead_agency=data.lead_agency,
            contractor_name=data.contractor_name,
            assigned_manager_id=data.assigned_manager_id or user_id,
            latitude=data.latitude,
            longitude=data.longitude,
            geom=geom,
            approval_status="PENDING_APPROVAL"
        )
        db.add(prj)
        db.commit()
        db.refresh(prj)

        AuditService.log_action(
            db=db,
            user_id=user_id,
            action="CREATE_RECOVERY_PROJECT",
            target_entity="RecoveryProject",
            details={"project_code": code, "title": data.title, "estimated_cost": data.estimated_cost}
        )
        return prj

    @staticmethod
    def approve_project(db: Session, project_id: str, data: RecoveryProjectApprove, officer_id: str) -> RecoveryProject:
        prj = db.query(RecoveryProject).filter(RecoveryProject.id == project_id).first()
        if not prj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        orig_status = prj.status
        prj.status = "APPROVED"
        prj.approval_status = "APPROVED"
        prj.approved_by_id = officer_id
        prj.sanction_order_number = data.sanction_order_number
        prj.funding_source = data.funding_source
        prj.estimated_cost = data.approved_budget
        prj.approval_timestamp = datetime.now(timezone.utc)

        log = RecoveryOverrideLog(
            project_id=project_id,
            user_id=officer_id,
            action="PROJECT_APPROVE",
            original_value={"status": orig_status, "estimated_cost": prj.estimated_cost},
            new_value={"status": "APPROVED", "approved_budget": data.approved_budget, "sanction": data.sanction_order_number},
            justification_reason=data.notes or f"Sanction Order: {data.sanction_order_number}"
        )
        db.add(log)
        db.commit()
        db.refresh(prj)

        AuditService.log_action(
            db=db,
            user_id=officer_id,
            action="APPROVE_RECOVERY_PROJECT",
            target_entity="RecoveryProject",
            details={"project_id": project_id, "sanction": data.sanction_order_number, "budget": data.approved_budget}
        )
        return prj

    @staticmethod
    def update_project_status(db: Session, project_id: str, data: RecoveryProjectStatusUpdate, officer_id: str) -> RecoveryProject:
        prj = db.query(RecoveryProject).filter(RecoveryProject.id == project_id).first()
        if not prj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        valid_statuses = ("PROPOSED", "APPROVED", "IN_TENDER", "IN_PROGRESS", "INSPECTION", "COMPLETED", "SUSPENDED")
        if data.status.upper() not in valid_statuses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {data.status}")

        orig_status = prj.status
        prj.status = data.status.upper()
        if data.actual_expenditure_increment:
            prj.actual_expenditure += data.actual_expenditure_increment

        if prj.status == "COMPLETED" and not prj.actual_completion_date:
            prj.actual_completion_date = datetime.now(timezone.utc)

        db.commit()
        db.refresh(prj)

        AuditService.log_action(
            db=db,
            user_id=officer_id,
            action="UPDATE_PROJECT_STATUS",
            target_entity="RecoveryProject",
            details={"project_id": project_id, "from": orig_status, "to": prj.status, "notes": data.notes}
        )
        return prj

    @staticmethod
    def list_projects(db: Session, sector: Optional[str] = None, status_filter: Optional[str] = None) -> List[RecoveryProject]:
        q = db.query(RecoveryProject)
        if sector:
            q = q.filter(RecoveryProject.sector == sector.upper())
        if status_filter:
            q = q.filter(RecoveryProject.status == status_filter.upper())
        return q.order_by(RecoveryProject.priority_score.desc(), RecoveryProject.created_at.desc()).all()

    @staticmethod
    def delete_project(db: Session, project_id: str) -> None:
        prj = db.query(RecoveryProject).filter(RecoveryProject.id == project_id).first()
        if not prj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery project not found")
        db.query(ProjectDependency).filter(
            (ProjectDependency.predecessor_project_id == project_id) |
            (ProjectDependency.successor_project_id == project_id)
        ).delete(synchronize_session=False)
        db.delete(prj)
        db.commit()

    @staticmethod
    def delete_dependency(db: Session, dependency_id: str) -> None:
        dep = db.query(ProjectDependency).filter(ProjectDependency.id == dependency_id).first()
        if not dep:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dependency not found")
        db.delete(dep)
        db.commit()

    @staticmethod
    def seed_standard_scenario(db: Session, officer_id: Optional[str] = None) -> Dict[str, Any]:
        import uuid
        # Reset existing recovery projects and dependencies
        db.query(ProjectDependency).delete()
        db.query(RecoveryProject).delete()
        db.commit()

        pA = RecoveryProject(
            id=str(uuid.uuid4()),
            project_code="PRJ-A-ROAD",
            title="Road Clearance & Debris Removal",
            description="Debris clearance and access restoration across main arterial corridors",
            sector="TRANSPORT",
            priority_tier="TIER_1",
            priority_score=90.0,
            status="APPROVED",
            estimated_duration_days=5,
            estimated_cost=15000000.0,
            lead_agency="Greater Chennai Corporation - Roads",
            assigned_manager_id=officer_id
        )
        pB = RecoveryProject(
            id=str(uuid.uuid4()),
            project_code="PRJ-B-ELEC",
            title="Substation & Electricity Restoration",
            description="High voltage transformer and feeder line reconnection",
            sector="POWER",
            priority_tier="TIER_1",
            priority_score=85.0,
            status="APPROVED",
            estimated_duration_days=4,
            estimated_cost=20000000.0,
            lead_agency="TANGEDCO Grid Operations",
            assigned_manager_id=officer_id
        )
        pC = RecoveryProject(
            id=str(uuid.uuid4()),
            project_code="PRJ-C-WATER",
            title="Water Treatment Pipeline Repair",
            description="Main potable distribution trunk repair and chlorination startup",
            sector="WATER",
            priority_tier="TIER_2",
            priority_score=80.0,
            status="APPROVED",
            estimated_duration_days=3,
            estimated_cost=15000000.0,
            lead_agency="Chennai MetroWater Supply Board",
            assigned_manager_id=officer_id
        )
        pD = RecoveryProject(
            id=str(uuid.uuid4()),
            project_code="PRJ-D-HOSP",
            title="Primary Health Center Reopening",
            description="Structural safety certification and emergency clinic reopening",
            sector="HEALTH",
            priority_tier="TIER_1",
            priority_score=95.0,
            status="APPROVED",
            estimated_duration_days=2,
            estimated_cost=10000000.0,
            lead_agency="Directorate of Public Health",
            assigned_manager_id=officer_id
        )
        pE = RecoveryProject(
            id=str(uuid.uuid4()),
            project_code="PRJ-E-TRANS",
            title="Zonal Bus Transit Restoration",
            description="Depot operationalization and feeder route bus service resumption",
            sector="TRANSPORT",
            priority_tier="TIER_3",
            priority_score=75.0,
            status="APPROVED",
            estimated_duration_days=3,
            estimated_cost=10000000.0,
            lead_agency="Metropolitan Transport Corporation",
            assigned_manager_id=officer_id
        )

        projects = [pA, pB, pC, pD, pE]
        db.add_all(projects)
        db.commit()
        for p in projects:
            db.refresh(p)

        deps = [
            ProjectDependency(
                id=str(uuid.uuid4()),
                predecessor_project_id=pA.id,
                successor_project_id=pB.id,
                dependency_type="FINISH_TO_START",
                lag_days=0,
                rationale="Power restoration requires accessible roads"
            ),
            ProjectDependency(
                id=str(uuid.uuid4()),
                predecessor_project_id=pA.id,
                successor_project_id=pC.id,
                dependency_type="FINISH_TO_START",
                lag_days=0,
                rationale="Pipeline repair vehicles require cleared roads"
            ),
            ProjectDependency(
                id=str(uuid.uuid4()),
                predecessor_project_id=pB.id,
                successor_project_id=pD.id,
                dependency_type="FINISH_TO_START",
                lag_days=0,
                rationale="Clinic diagnostic equipment requires power"
            ),
            ProjectDependency(
                id=str(uuid.uuid4()),
                predecessor_project_id=pC.id,
                successor_project_id=pD.id,
                dependency_type="FINISH_TO_START",
                lag_days=0,
                rationale="Hospital sterilization requires running water"
            ),
            ProjectDependency(
                id=str(uuid.uuid4()),
                predecessor_project_id=pB.id,
                successor_project_id=pE.id,
                dependency_type="FINISH_TO_START",
                lag_days=0,
                rationale="Bus terminal signals and depot power require electrical grid"
            ),
        ]
        db.add_all(deps)
        db.commit()

        return {
            "status": "SUCCESS",
            "message": "Seeded standard 5-project recovery precedence scenario",
            "projects_count": 5,
            "dependencies_count": 5,
            "makespan_days": 12,
            "critical_path": ["PRJ-A-ROAD", "PRJ-B-ELEC", "PRJ-E-TRANS"]
        }

    # ==========================================================================
    # 4. PROJECT DEPENDENCY GRAPH & CYCLE DETECTION
    # ==========================================================================

    @staticmethod
    def add_dependency(db: Session, data: ProjectDependencyCreate) -> ProjectDependency:
        if data.predecessor_project_id == data.successor_project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "ERR_SELF_LOOP", "message": "A project cannot depend on itself."}
            )

        p1 = db.query(RecoveryProject).filter(RecoveryProject.id == data.predecessor_project_id).first()
        p2 = db.query(RecoveryProject).filter(RecoveryProject.id == data.successor_project_id).first()
        if not p1 or not p2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "ERR_NODE_NOT_FOUND", "message": "Predecessor or successor project does not exist."}
            )

        # Check existing edge
        existing = db.query(ProjectDependency).filter(
            ProjectDependency.predecessor_project_id == data.predecessor_project_id,
            ProjectDependency.successor_project_id == data.successor_project_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "ERR_DUPLICATE_DEPENDENCY", "message": "Dependency edge already exists."}
            )

        # In-memory Cycle Detection using Kahn's Algorithm on hypothetical new edge
        all_deps = db.query(ProjectDependency).all()
        adj: Dict[str, List[str]] = {}
        in_degree: Dict[str, int] = {}

        # Add all projects
        all_prjs = db.query(RecoveryProject.id).all()
        for (pid,) in all_prjs:
            adj[pid] = []
            in_degree[pid] = 0

        for d in all_deps:
            if d.predecessor_project_id in adj and d.successor_project_id in adj:
                adj[d.predecessor_project_id].append(d.successor_project_id)
                in_degree[d.successor_project_id] += 1

        # Add candidate edge
        adj[data.predecessor_project_id].append(data.successor_project_id)
        in_degree[data.successor_project_id] += 1

        # Kahn's test
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited_count = 0
        while queue:
            curr = queue.pop(0)
            visited_count += 1
            for nxt in adj.get(curr, []):
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if visited_count < len(adj):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "ERR_CYCLIC_DEPENDENCY",
                    "message": "Adding dependency creates a cycle in the restoration project graph.",
                    "cycle_involving": [data.predecessor_project_id, data.successor_project_id]
                }
            )

        dep = ProjectDependency(
            predecessor_project_id=data.predecessor_project_id,
            successor_project_id=data.successor_project_id,
            dependency_type=data.dependency_type.upper(),
            lag_days=data.lag_days,
            rationale=data.rationale
        )
        db.add(dep)
        db.commit()
        db.refresh(dep)
        return dep

    @staticmethod
    def list_dependencies(db: Session, project_id: Optional[str] = None) -> List[ProjectDependency]:
        q = db.query(ProjectDependency)
        if project_id:
            q = q.filter(
                (ProjectDependency.predecessor_project_id == project_id) |
                (ProjectDependency.successor_project_id == project_id)
            )
        return q.all()

    @staticmethod
    def get_precedence_graph(db: Session, period_days: float = 30.0) -> PrecedenceGraphResponse:
        projects = db.query(RecoveryProject).all()
        deps = db.query(ProjectDependency).all()

        if not projects:
            return PrecedenceGraphResponse(
                is_acyclic=True,
                topological_order=[],
                critical_path_project_ids=[],
                project_makespan_periods=0,
                total_projects=0,
                total_dependencies=0,
                nodes=[],
                edges=[],
                cycle_path=None
            )

        activities = [
            ProjectActivity(
                project_id=p.id,
                duration_days=float(p.estimated_duration_days or 0)
            )
            for p in projects
        ]
        edges = [
            DependencyEdge(
                predecessor_id=d.predecessor_project_id,
                successor_id=d.successor_project_id,
                lag_days=float(d.lag_days or 0)
            )
            for d in deps
        ]

        try:
            dag_result = ProjectDependencyService.analyze_network(activities, edges, period_days=period_days)
            is_acyclic = True
            topological_order = dag_result.topological_order
            critical_path_ids = dag_result.critical_path
            makespan = dag_result.project_makespan_periods
            cpm_dict = dag_result.cpm_results
            cycle_path = None
        except CyclicDependencyError as e:
            is_acyclic = False
            topological_order = []
            critical_path_ids = []
            makespan = 0
            cpm_dict = {}
            cycle_path = e.cycle_path

        nodes_dto: List[PrecedenceGraphNode] = []
        for p in projects:
            cpm_info = None
            if is_acyclic and p.id in cpm_dict:
                res = cpm_dict[p.id]
                cpm_info = PrecedenceCPMInfo(
                    duration_periods=res.duration_periods,
                    early_start=res.early_start,
                    early_finish=res.early_finish,
                    late_start=res.late_start,
                    late_finish=res.late_finish,
                    total_float=res.total_float,
                    free_float=res.free_float,
                    is_critical=res.is_critical
                )

            nodes_dto.append(PrecedenceGraphNode(
                id=p.id,
                project_code=p.project_code,
                title=p.title,
                sector=p.sector,
                priority_tier=p.priority_tier,
                status=p.status,
                estimated_cost=p.estimated_cost,
                estimated_duration_days=p.estimated_duration_days,
                cpm=cpm_info
            ))

        edges_dto: List[PrecedenceGraphEdge] = []
        critical_set = set(critical_path_ids)
        for d in deps:
            lag_periods = ProjectDependencyService.convert_days_to_periods(
                float(d.lag_days or 0), period_days=period_days, is_duration=False
            )
            is_edge_crit = False
            if is_acyclic and d.predecessor_project_id in critical_set and d.successor_project_id in critical_set:
                pred_cpm = cpm_dict.get(d.predecessor_project_id)
                succ_cpm = cpm_dict.get(d.successor_project_id)
                if pred_cpm and succ_cpm and (pred_cpm.early_finish + lag_periods == succ_cpm.early_start):
                    is_edge_crit = True

            edges_dto.append(PrecedenceGraphEdge(
                id=d.id,
                predecessor_project_id=d.predecessor_project_id,
                successor_project_id=d.successor_project_id,
                dependency_type=d.dependency_type,
                lag_days=d.lag_days,
                lag_periods=lag_periods,
                is_critical_path=is_edge_crit,
                rationale=d.rationale
            ))

        return PrecedenceGraphResponse(
            is_acyclic=is_acyclic,
            topological_order=topological_order,
            critical_path_project_ids=critical_path_ids,
            project_makespan_periods=makespan,
            total_projects=len(projects),
            total_dependencies=len(deps),
            nodes=nodes_dto,
            edges=edges_dto,
            cycle_path=cycle_path
        )

    @staticmethod
    def validate_dependency_edge(db: Session, data: PrecedenceEdgeValidateRequest) -> PrecedenceEdgeValidateResponse:
        # Self loop check
        if data.predecessor_project_id == data.successor_project_id:
            return PrecedenceEdgeValidateResponse(
                is_valid=False,
                reason="SELF_LOOP",
                message="A project cannot depend on itself.",
                cycle_path=[data.predecessor_project_id, data.successor_project_id]
            )

        # Node existence check
        p1 = db.query(RecoveryProject).filter(RecoveryProject.id == data.predecessor_project_id).first()
        p2 = db.query(RecoveryProject).filter(RecoveryProject.id == data.successor_project_id).first()
        if not p1 or not p2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "ERR_NODE_NOT_FOUND", "message": "Predecessor or successor project does not exist."}
            )

        # Duplicate edge check
        existing = db.query(ProjectDependency).filter(
            ProjectDependency.predecessor_project_id == data.predecessor_project_id,
            ProjectDependency.successor_project_id == data.successor_project_id
        ).first()
        if existing:
            return PrecedenceEdgeValidateResponse(
                is_valid=False,
                reason="DUPLICATE_EDGE",
                message="Dependency edge already exists.",
                cycle_path=None
            )

        # In-memory cycle check: NO database write
        all_deps = db.query(ProjectDependency).all()
        all_projects = db.query(RecoveryProject.id).all()
        node_ids = [pid for (pid,) in all_projects]

        edges = [
            DependencyEdge(
                predecessor_id=d.predecessor_project_id,
                successor_id=d.successor_project_id,
                lag_days=float(d.lag_days or 0)
            )
            for d in all_deps
        ]
        edges.append(DependencyEdge(
            predecessor_id=data.predecessor_project_id,
            successor_id=data.successor_project_id,
            lag_days=float(data.lag_days or 0)
        ))

        try:
            ProjectDependencyService.detect_cycle_and_toposort(node_ids, edges)
            return PrecedenceEdgeValidateResponse(
                is_valid=True,
                reason=None,
                message="Candidate dependency edge is valid and acyclic.",
                cycle_path=None
            )
        except CyclicDependencyError as err:
            return PrecedenceEdgeValidateResponse(
                is_valid=False,
                reason="CYCLIC_DEPENDENCY",
                message="Candidate edge introduces a circular dependency cycle.",
                cycle_path=err.cycle_path
            )

    # ==========================================================================
    # 5. RECOVERY RESOURCES
    # ==========================================================================

    @staticmethod
    def create_resource(db: Session, data: RecoveryResourceCreate) -> RecoveryResource:
        prj = db.query(RecoveryProject).filter(RecoveryProject.id == data.project_id).first()
        if not prj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target recovery project not found")

        res = RecoveryResource(
            project_id=data.project_id,
            material_category=data.material_category.upper(),
            item_description=data.item_description,
            quantity_required=data.quantity_required,
            quantity_delivered=0.0,
            unit_of_measure=data.unit_of_measure.upper(),
            unit_cost_estimate=data.unit_cost_estimate,
            actual_unit_cost=0.0,
            supplier_info=data.supplier_info,
            delivery_status="ORDERED"
        )
        db.add(res)
        db.commit()
        db.refresh(res)
        return res

    @staticmethod
    def list_resources(db: Session, project_id: Optional[str] = None) -> List[RecoveryResource]:
        q = db.query(RecoveryResource)
        if project_id:
            q = q.filter(RecoveryResource.project_id == project_id)
        return q.all()

    # ==========================================================================
    # 6. COMMUNITY METRICS & FRESHNESS
    # ==========================================================================

    @staticmethod
    def ingest_community_metric(db: Session, data: CommunityRecoveryMetricCreate, user_id: str) -> CommunityRecoveryMetric:
        # Check freshness category
        days_elapsed = (datetime.now(timezone.utc) - data.metric_date.replace(tzinfo=timezone.utc if data.metric_date.tzinfo is None else data.metric_date.tzinfo)).days
        if days_elapsed > 30:
            freshness = "EXPIRED_RED"
        elif days_elapsed > 14:
            freshness = "STALE_AMBER"
        elif days_elapsed > 7:
            freshness = "MODERATE"
        else:
            freshness = "FRESH"

        existing = db.query(CommunityRecoveryMetric).filter(
            CommunityRecoveryMetric.ward_code == data.ward_code,
            CommunityRecoveryMetric.metric_date == data.metric_date
        ).first()

        if existing:
            existing.district = data.district
            existing.active_shelter_count = data.active_shelter_count
            existing.remaining_displaced_persons = data.remaining_displaced_persons
            existing.power_grid_restoration_pct = data.power_grid_restoration_pct
            existing.potable_water_access_pct = data.potable_water_access_pct
            existing.healthcare_facility_operational_pct = data.healthcare_facility_operational_pct
            existing.schools_open_pct = data.schools_open_pct
            existing.livelihoods_resumed_pct = data.livelihoods_resumed_pct
            existing.overall_recovery_score = data.overall_recovery_score
            # Confidence decay calculation deferred to Phase 6F; persist observed/input confidence
            existing.data_confidence = data.data_confidence
            existing.freshness_status = freshness
            existing.last_verified_at = datetime.now(timezone.utc)
            existing.verified_by_id = user_id
            db.commit()
            db.refresh(existing)
            return existing
        else:
            m = CommunityRecoveryMetric(
                id=str(uuid.uuid4()),
                ward_code=data.ward_code,
                district=data.district,
                metric_date=data.metric_date,
                active_shelter_count=data.active_shelter_count,
                remaining_displaced_persons=data.remaining_displaced_persons,
                power_grid_restoration_pct=data.power_grid_restoration_pct,
                potable_water_access_pct=data.potable_water_access_pct,
                healthcare_facility_operational_pct=data.healthcare_facility_operational_pct,
                schools_open_pct=data.schools_open_pct,
                livelihoods_resumed_pct=data.livelihoods_resumed_pct,
                overall_recovery_score=data.overall_recovery_score,
                # Confidence decay calculation deferred to Phase 6F; persist observed/input confidence
                data_confidence=data.data_confidence,
                freshness_status=freshness,
                last_verified_at=datetime.now(timezone.utc),
                verified_by_id=user_id
            )
            db.add(m)
            db.commit()
            db.refresh(m)
            return m

    @staticmethod
    def list_community_metrics(db: Session, ward_code: Optional[str] = None) -> List[CommunityRecoveryMetric]:
        q = db.query(CommunityRecoveryMetric)
        if ward_code:
            q = q.filter(CommunityRecoveryMetric.ward_code == ward_code)
        return q.order_by(CommunityRecoveryMetric.metric_date.desc()).all()

    # ==========================================================================
    # 7. OVERRIDE LOGS AUDIT
    # ==========================================================================

    @staticmethod
    def list_override_logs(db: Session, project_id: Optional[str] = None) -> List[RecoveryOverrideLog]:
        q = db.query(RecoveryOverrideLog)
        if project_id:
            q = q.filter(RecoveryOverrideLog.project_id == project_id)
        return q.order_by(RecoveryOverrideLog.timestamp.desc()).all()
