from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import base64

from app.database import get_db
from app.models.user import User
from app.core.deps import get_current_user, require_role
from app.core.idempotency import idempotency_service, get_idempotency_key
from app.recovery.services.recovery_service import RecoveryService
from app.recovery.services.damage_assessment_service import DamageAssessmentService
from app.recovery.services.recovery_needs_service import RecoveryNeedsService
from app.recovery.services.population_reconciliation import PopulationReconciliationService
from app.recovery.services.recovery_spatial_service import RecoverySpatialService
from app.recovery.services.community_monitoring_service import CommunityMonitoringService
from app.recovery.services.recovery_simulation_service import RecoverySimulationService
from app.schemas.recovery import (
    RecoveryAssessmentCreate,
    RecoveryAssessmentVerify,
    RecoveryAssessmentSupersede,
    RecoveryAssessmentResponse,
    RecoveryNeedCreate,
    RecoveryNeedResponse,
    RecoveryNeedPublicResponse,
    RecoveryProjectCreate,
    RecoveryProjectApprove,
    RecoveryProjectStatusUpdate,
    RecoveryProjectResponse,
    ProjectDependencyCreate,
    ProjectDependencyResponse,
    PrecedenceGraphResponse,
    PrecedenceEdgeValidateRequest,
    PrecedenceEdgeValidateResponse,
    RecoveryResourceCreate,
    RecoveryResourceResponse,
    CommunityRecoveryMetricCreate,
    CommunityRecoveryMetricResponse,
    RecoveryOverrideLogResponse,
    DamageScreeningRequest,
    DamageScreeningResponse,
    DamageAssessmentFieldCreate,
    DamageAssessmentVerifyRequest,
    DamageAssessmentHistoryResponse,
    StructuredRecoveryNeedCreate,
    StructuredRecoveryNeedResponse,
    PopulationReconciliationRequest,
    PopulationReconciliationResponse,
    RecoverySpatialSummaryResponse,
    RecoveryAnalyticsSummaryResponse,
    CommunityMetricSummaryResponse,
    VulnerabilityRescoreRequest,
    VulnerabilityRescoreResponse,
    RecoveryWhatIfSimulationRequest,
    RecoveryWhatIfSimulationResponse
)

router = APIRouter(prefix="/recovery", tags=["Post-Disaster Recovery Data Foundation"])


# ==============================================================================
# 1. RECOVERY ASSESSMENTS
# ==============================================================================

@router.post("/assessments", response_model=RecoveryAssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_assessment(
    data: RecoveryAssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a formal engineering damage & loss assessment for a damaged facility.
    Allowed roles: GOVT, VOLUNTEER, ADMIN.
    """
    if current_user.role not in ("GOVT", "VOLUNTEER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Government officers, Volunteers, or Admins may submit recovery assessments."
        )
    return RecoveryService.create_assessment(db, data, inspector_id=current_user.id)


@router.get("/assessments", response_model=List[RecoveryAssessmentResponse])
def list_assessments(
    incident_id: Optional[str] = None,
    sector: Optional[str] = None,
    current_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List recovery assessments. By default returns only the current active version.
    """
    return RecoveryService.list_assessments(db, incident_id=incident_id, sector=sector, current_only=current_only)


@router.get("/assessments/{id}", response_model=RecoveryAssessmentResponse)
def get_assessment(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    asms = RecoveryService.list_assessments(db, current_only=False)
    target = next((a for a in asms if a.id == id), None)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return target


@router.post("/assessments/{id}/verify", response_model=RecoveryAssessmentResponse)
def verify_assessment(
    id: str,
    data: RecoveryAssessmentVerify,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Human-in-the-loop verification gate: Only GOVT or ADMIN can verify/reject an assessment.
    """
    return RecoveryService.verify_assessment(db, assessment_id=id, data=data, officer_id=current_user.id)


@router.post("/assessments/{id}/supersede", response_model=RecoveryAssessmentResponse, status_code=status.HTTP_201_CREATED)
def supersede_assessment(
    id: str,
    data: RecoveryAssessmentSupersede,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Creates a new monotonic version (V+1) of an existing assessment, preserving the historical record.
    Requires Government authority and justification logging.
    """
    return RecoveryService.supersede_assessment(db, old_id=id, data=data, inspector_id=current_user.id)


# ==============================================================================
# 2. RECOVERY NEEDS & DOUBLE-COUNT PREVENTION
# ==============================================================================

@router.post("/needs", response_model=RecoveryNeedResponse, status_code=status.HTTP_201_CREATED)
def create_need(
    data: RecoveryNeedCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Quantifies multi-sectoral recovery requirements for a ward.
    Automatically reconciles against census baseline caps to prevent double-counting.
    Hashes beneficiary ID with protected salt.
    """
    if current_user.role not in ("GOVT", "VOLUNTEER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Government officers, Volunteers, or Admins may record recovery needs."
        )
    return RecoveryService.create_need(db, data)


@router.get("/needs")
def list_needs(
    ward_code: Optional[str] = None,
    sector: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves recovery needs.
    Government/Admin receives full schema with pseudonymized hashes.
    Citizens/Volunteers/NGOs receive public schema strictly stripping household identifiers.
    """
    needs = RecoveryService.list_needs(db, ward_code=ward_code, sector=sector)
    is_privileged = current_user.role in ("GOVT", "ADMIN")
    if is_privileged:
        return [RecoveryNeedResponse.model_validate(n) for n in needs]
    else:
        return [RecoveryNeedPublicResponse.model_validate(n) for n in needs]


# ==============================================================================
# 3. RECOVERY PROJECTS & APPROVAL GATES
# ==============================================================================

@router.post("/projects", response_model=RecoveryProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    data: RecoveryProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Formally records a capital reconstruction/restoration project.
    Strictly restricted to GOVT or ADMIN.
    """
    return RecoveryService.create_project(db, data, user_id=current_user.id)


@router.get("/projects", response_model=List[RecoveryProjectResponse])
def list_projects(
    sector: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists recovery projects and current status. Available to all authenticated roles.
    """
    return RecoveryService.list_projects(db, sector=sector, status_filter=status_filter)


@router.get("/projects/{id}", response_model=RecoveryProjectResponse)
def get_project(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prjs = RecoveryService.list_projects(db)
    target = next((p for p in prjs if p.id == id), None)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery project not found")
    return target


@router.post("/projects/{id}/approve", response_model=RecoveryProjectResponse)
def approve_project(
    id: str,
    data: RecoveryProjectApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Government Sanction Approval Gate: Commits funding and changes project state to APPROVED.
    Requires sanction order voucher number. Strictly restricted to GOVT or ADMIN.
    """
    return RecoveryService.approve_project(db, project_id=id, data=data, officer_id=current_user.id)


@router.patch("/projects/{id}/status", response_model=RecoveryProjectResponse)
def update_project_status(
    id: str,
    data: RecoveryProjectStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Updates operational progress status and records actual expenditure. Restricted to GOVT/ADMIN.
    """
    return RecoveryService.update_project_status(db, project_id=id, data=data, officer_id=current_user.id)


@router.delete("/projects/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """Deletes a recovery project and its attached dependency relations."""
    RecoveryService.delete_project(db, project_id=id)
    return None


@router.post("/projects/seed-standard-scenario", status_code=status.HTTP_200_OK)
def seed_standard_projects_scenario(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Seeds the authoritative 5-project precedence benchmark scenario:
    A (Road clearance, 5d) -> B (Electricity, 4d) & C (Water, 3d)
    B & C -> D (Hospital, 2d), B -> E (Transport, 3d).
    Makespan = 12 days, Critical Path = A -> B -> E.
    """
    return RecoveryService.seed_standard_scenario(db, officer_id=current_user.id)


# ==============================================================================
# 4. PROJECT DEPENDENCY GRAPH
# ==============================================================================

@router.post("/dependencies", response_model=ProjectDependencyResponse, status_code=status.HTTP_201_CREATED)
def add_dependency(
    data: ProjectDependencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Records a directed precedence relation between two projects.
    Executes Kahn's algorithm cycle detection: rejects cycles with HTTP 400.
    """
    return RecoveryService.add_dependency(db, data)


@router.delete("/dependencies/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dependency(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """Deletes a dependency precedence edge."""
    RecoveryService.delete_dependency(db, dependency_id=id)
    return None


@router.get("/dependencies", response_model=List[ProjectDependencyResponse])
def list_dependencies(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return RecoveryService.list_dependencies(db, project_id=project_id)


@router.get("/dependencies/graph", response_model=PrecedenceGraphResponse, status_code=status.HTTP_200_OK)
def get_precedence_graph(
    period_days: float = Query(30.0, ge=1.0, description="Duration in calendar days per planning period"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Extracts the complete recovery project precedence graph with CPM-PL metrics and critical-path identification.
    """
    return RecoveryService.get_precedence_graph(db, period_days=period_days)


@router.post("/dependencies/validate-edge", response_model=PrecedenceEdgeValidateResponse, status_code=status.HTTP_200_OK)
def validate_dependency_edge(
    data: PrecedenceEdgeValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dry-run candidate dependency validation: checks existence, duplicates, self-loops,
    and cycles using Kahn's algorithm without database writes.
    """
    return RecoveryService.validate_dependency_edge(db, data)


# ==============================================================================
# 5. RECOVERY RESOURCES
# ==============================================================================

@router.post("/resources", response_model=RecoveryResourceResponse, status_code=status.HTTP_201_CREATED)
def create_resource(
    data: RecoveryResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Allocates durable materials (cement, steel) or heavy machinery to a recovery project.
    """
    if current_user.role not in ("GOVT", "NGO", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Government officers, NGOs, or Admins may allocate recovery materials."
        )
    return RecoveryService.create_resource(db, data)


@router.get("/resources", response_model=List[RecoveryResourceResponse])
def list_resources(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return RecoveryService.list_resources(db, project_id=project_id)


# ==============================================================================
# 6. COMMUNITY RECOVERY METRICS
# ==============================================================================

@router.post("/community-metrics", response_model=CommunityRecoveryMetricResponse, status_code=status.HTTP_201_CREATED)
def ingest_community_metric(
    data: CommunityRecoveryMetricCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Ingests longitudinal recovery metrics for a ward with automated freshness tagging.
    """
    return RecoveryService.ingest_community_metric(db, data, user_id=current_user.id)


@router.get("/community-metrics", response_model=List[CommunityRecoveryMetricResponse])
def list_community_metrics(
    ward_code: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Public dashboard endpoint: Ward recovery progress and utility restoration.
    """
    return RecoveryService.list_community_metrics(db, ward_code=ward_code)


# ==============================================================================
# 7. OVERRIDE LOGS & AUDITABILITY
# ==============================================================================

@router.get("/overrides", response_model=List[RecoveryOverrideLogResponse])
def list_override_logs(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Compliance audit trail of all human approvals, budget alterations, and supersessions.
    Restricted to GOVT and ADMIN.
    """
    return RecoveryService.list_override_logs(db, project_id=project_id)


# ==============================================================================
# 8. PHASE 6C: DAMAGE ASSESSMENT INTELLIGENCE & TIER-1 CV SCREENING
# ==============================================================================

@router.post("/damage-assessments/screen-image", response_model=DamageScreeningResponse, status_code=status.HTTP_200_OK)
def screen_damage_image(
    data: DamageScreeningRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Executes Tier-1 damage screening on an evidence image using the frozen Phase 3B CV pipeline.
    Output is strictly non-certified structural screening and requires government verification.
    """
    if current_user.role not in ("GOVT", "NGO", "VOLUNTEER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role not authorized for damage screening"
        )

    raw_bytes = None
    if data.image_base64:
        try:
            raw_bytes = base64.b64decode(data.image_base64)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 encoded image string"
            )

    return DamageAssessmentService.screen_damage_image(
        db=db,
        image_path=data.image_path,
        image_bytes=raw_bytes,
        incident_id=data.incident_id,
        user_id=current_user.id
    )


@router.post("/damage-assessments/field-inspection", response_model=RecoveryAssessmentResponse, status_code=status.HTTP_201_CREATED)
def submit_field_inspection(
    data: DamageAssessmentFieldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: Optional[str] = Depends(get_idempotency_key)
):
    """
    Submits a field damage assessment with coordinates, structural notes, and optional CV screening linkage.
    Initial state is PENDING_VERIFICATION. Supports idempotent re-submission via Idempotency-Key.
    """
    if current_user.role not in ("GOVT", "NGO", "VOLUNTEER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role not authorized to submit field damage assessments"
        )

    if idempotency_key:
        fingerprint = idempotency_service.compute_fingerprint(data)
        is_cached, cached_res = idempotency_service.check_or_lock(
            key=idempotency_key,
            user_id=str(current_user.id),
            endpoint="/api/v1/recovery/damage-assessments/field-inspection",
            fingerprint=fingerprint
        )
        if is_cached:
            return cached_res

    try:
        assessment = DamageAssessmentService.submit_field_inspection(db, data, inspector=current_user)

        if idempotency_key:
            res_dict = RecoveryAssessmentResponse.model_validate(assessment).model_dump(mode="json")
            idempotency_service.store_result(
                key=idempotency_key,
                user_id=str(current_user.id),
                endpoint="/api/v1/recovery/damage-assessments/field-inspection",
                response_data=res_dict,
                status_code=status.HTTP_201_CREATED
            )

        return assessment
    except Exception:
        if idempotency_key:
            idempotency_service.release_lock(
                key=idempotency_key,
                user_id=str(current_user.id),
                endpoint="/api/v1/recovery/damage-assessments/field-inspection"
            )
        raise


@router.post("/damage-assessments/{assessment_id}/verify", response_model=RecoveryAssessmentResponse)
def verify_damage_assessment_p6c(
    assessment_id: str,
    data: DamageAssessmentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Government engineering verification gate. Authorizes, rejects, or disputes a field assessment.
    """
    return DamageAssessmentService.verify_damage_assessment(
        db=db,
        assessment_id=assessment_id,
        data=data,
        verifier=current_user
    )


@router.post("/damage-assessments/{assessment_id}/supersede", response_model=RecoveryAssessmentResponse)
def supersede_damage_assessment_p6c(
    assessment_id: str,
    data: RecoveryAssessmentSupersede,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits a superseding inspection (V_k -> V_{k+1}), incrementing monotonic version
    and marking the previous version as non-current.
    """
    if current_user.role not in ("GOVT", "NGO", "VOLUNTEER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role not authorized to supersede damage assessments"
        )
    return DamageAssessmentService.supersede_assessment(
        db=db,
        old_id=assessment_id,
        data=data,
        inspector=current_user
    )


@router.get("/damage-assessments/{assessment_id}/history", response_model=DamageAssessmentHistoryResponse)
def get_assessment_history(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns complete chronological version history and supersession lineage for an assessment.
    """
    if current_user.role not in ("GOVT", "NGO", "VOLUNTEER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return DamageAssessmentService.get_assessment_history(db, assessment_id)


# ==============================================================================
# 9. PHASE 6C: STRUCTURED RECOVERY NEEDS & DEMOGRAPHICS
# ==============================================================================

@router.post("/needs/structured", response_model=StructuredRecoveryNeedResponse, status_code=status.HTTP_201_CREATED)
def create_structured_need(
    data: StructuredRecoveryNeedCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits structured recovery need with Phase 6A demographic conservation (GEN, ACC, MED, MED_ACC),
    salted beneficiary hashing, and census baseline capping.
    """
    if current_user.role not in ("GOVT", "NGO", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Citizens and Volunteers cannot ingest household-level recovery needs"
        )
    return RecoveryNeedsService.create_structured_need(db, data, user_id=current_user.id)


@router.get("/needs/structured", response_model=List[StructuredRecoveryNeedResponse])
def list_structured_needs(
    sector: Optional[str] = None,
    ward_code: Optional[str] = None,
    district: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists structured recovery needs with demographic breakdowns. Restricted to authorized roles.
    """
    if current_user.role not in ("GOVT", "NGO", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to Government and NGO officials."
        )
    return RecoveryNeedsService.list_structured_needs(
        db=db,
        sector=sector,
        ward_code=ward_code,
        district=district
    )


# ==============================================================================
# 10. PHASE 6C: POPULATION RECONCILIATION
# ==============================================================================

@router.post("/reconciliation/reconcile-population", response_model=PopulationReconciliationResponse)
def reconcile_population(
    data: PopulationReconciliationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reconciles multi-source population and household estimates, detects duplicate
    beneficiary records, flags conflicting assessments, and verifies against census caps.
    """
    if current_user.role not in ("GOVT", "NGO", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Government and NGO officials may trigger population reconciliation"
        )
    return PopulationReconciliationService.reconcile_population(db, data)


# ==============================================================================
# 11. PHASE 6C: SPATIAL RECOVERY & ANALYTICS
# ==============================================================================

@router.get("/spatial/damage-summary", response_model=RecoverySpatialSummaryResponse)
def get_ward_spatial_summary(
    ward_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aggregates damage and needs indicators for an administrative ward with synthetic spatial boundary GeoJSON.
    """
    if current_user.role not in ("GOVT", "NGO", "VOLUNTEER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return RecoverySpatialService.get_ward_spatial_summary(db, ward_code=ward_code)


@router.get("/spatial/radius", response_model=List[RecoveryAssessmentResponse])
def query_damage_by_radius(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    sector: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    PostGIS spatial distance query for damage assessments within radius_km.
    """
    if current_user.role not in ("GOVT", "NGO", "VOLUNTEER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return RecoverySpatialService.query_damage_by_radius(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        sector=sector
    )


@router.get("/spatial/bbox", response_model=List[RecoveryAssessmentResponse])
def query_damage_by_bbox(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    sector: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    PostGIS spatial bounding-box query for damage assessments.
    """
    if current_user.role not in ("GOVT", "NGO", "VOLUNTEER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return RecoverySpatialService.query_damage_by_bbox(
        db=db,
        min_lat=min_lat,
        min_lon=min_lon,
        max_lat=max_lat,
        max_lon=max_lon,
        sector=sector
    )


@router.get("/analytics/summary", response_model=RecoveryAnalyticsSummaryResponse)
def get_public_analytics_summary(
    db: Session = Depends(get_db)
):
    """
    Public situation awareness endpoint. Aggregates only approved recovery indicators,
    scrubbing all raw household PII and unverified screening claims.
    """
    return RecoverySpatialService.get_public_analytics_summary(db)


# ==============================================================================
# PHASE 6F / WP2: COMMUNITY RECOVERY MONITORING, RESCORING & SIMULATION
# ==============================================================================

@router.get("/monitoring/community-metrics/summary", response_model=CommunityMetricSummaryResponse)
def get_community_metrics_summary(
    ward_code: Optional[str] = None,
    district: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ward-level and community-level longitudinal recovery indicators aggregated across wards
    with automated exponential confidence decay and data freshness categorization.
    """
    return CommunityMonitoringService.get_community_metric_summary(db, ward_code=ward_code, district=district)


@router.post("/monitoring/vulnerability-rescore", response_model=VulnerabilityRescoreResponse)
def rescore_vulnerability(
    data: VulnerabilityRescoreRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Evaluates transparent vulnerability rescoring fusing demographic baselines with
    real-time infrastructure restoration deficits, displacement pressure, and observation confidence decay.
    """
    return CommunityMonitoringService.rescore_vulnerability(data)


@router.post("/simulation/what-if", response_model=RecoveryWhatIfSimulationResponse)
def simulate_recovery_what_if(
    data: RecoveryWhatIfSimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Executes in-memory what-if recovery simulation evaluating policy decisions, budget shifts,
    resource supply shocks, and disaster recurrence risks without mutating database records.
    Restricted to GOVT/ADMIN.
    """
    return RecoverySimulationService.simulate_what_if(db, data)


