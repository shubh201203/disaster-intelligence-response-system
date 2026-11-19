import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db, SessionLocal
from app.models.user import User
from app.models.recovery import CommunityRecoveryMetric, RecoveryProject, RecoveryResource
from app.recovery.services.community_monitoring_service import CommunityMonitoringService
from app.recovery.services.recovery_simulation_service import RecoverySimulationService
from app.schemas.recovery import (
    VulnerabilityRescoreRequest,
    RecoveryWhatIfSimulationRequest,
    SimulationPerturbationParams
)


@pytest.fixture
def db_session():
    """Provides a transactional database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client(db_session: Session):
    """Provides FastAPI test client overriding db dependency"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def govt_token(db_session: Session) -> str:
    from app.core.security import create_access_token
    user = db_session.query(User).filter(User.email == "govt_officer_wp2@example.com").first()
    if not user:
        user = User(
            email="govt_officer_wp2@example.com",
            hashed_password="hashed_pwd",
            full_name="Govt Recovery Coordinator",
            role="GOVT",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return create_access_token(subject=user.id)


@pytest.fixture
def citizen_token(db_session: Session) -> str:
    from app.core.security import create_access_token
    user = db_session.query(User).filter(User.email == "citizen_wp2@example.com").first()
    if not user:
        user = User(
            email="citizen_wp2@example.com",
            hashed_password="hashed_pwd",
            full_name="Citizen Observer",
            role="CITIZEN",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return create_access_token(subject=user.id)


# ==============================================================================
# 1. PURE MATHEMATICAL UNIT TESTS: CONFIDENCE DECAY & RECOVERY SCORING
# ==============================================================================

def test_confidence_decay_math_fresh():
    """Delta t = 0 -> Confidence = 100%, Status = FRESH"""
    now = datetime.now(timezone.utc)
    conf, days, status = CommunityMonitoringService.calculate_confidence_decay(
        initial_confidence=100.0,
        last_verified_at=now,
        evaluation_time=now
    )
    assert conf == 100.0
    assert days == 0.0
    assert status == "FRESH"


def test_confidence_decay_math_moderate():
    """Delta t = 6 days -> C(t) = 100 * exp(-0.05 * 6) = 74.08% -> MODERATE"""
    eval_time = datetime.now(timezone.utc)
    verified_time = eval_time - timedelta(days=6)
    conf, days, status = CommunityMonitoringService.calculate_confidence_decay(
        initial_confidence=100.0,
        last_verified_at=verified_time,
        evaluation_time=eval_time
    )
    assert 73.0 <= conf <= 75.0
    assert days == 6.0
    assert status == "MODERATE"


def test_confidence_decay_math_stale():
    """Delta t = 16 days -> C(t) = 100 * exp(-0.05 * 16) = 44.93% -> STALE_AMBER"""
    eval_time = datetime.now(timezone.utc)
    verified_time = eval_time - timedelta(days=16)
    conf, days, status = CommunityMonitoringService.calculate_confidence_decay(
        initial_confidence=100.0,
        last_verified_at=verified_time,
        evaluation_time=eval_time
    )
    assert 44.0 <= conf <= 46.0
    assert days == 16.0
    assert status == "STALE_AMBER"


def test_confidence_decay_math_expired():
    """Delta t = 30 days -> C(t) = 100 * exp(-0.05 * 30) = 22.31% -> EXPIRED_RED"""
    eval_time = datetime.now(timezone.utc)
    verified_time = eval_time - timedelta(days=30)
    conf, days, status = CommunityMonitoringService.calculate_confidence_decay(
        initial_confidence=100.0,
        last_verified_at=verified_time,
        evaluation_time=eval_time
    )
    assert 21.0 <= conf <= 23.5
    assert days == 30.0
    assert status == "EXPIRED_RED"


def test_overall_recovery_score_sector_weights():
    """Verifies authoritative weights: power 0.25, water 0.25, health 0.20, schools 0.15, livelihoods 0.15"""
    score = CommunityMonitoringService.calculate_overall_recovery_score(
        power_pct=100.0,
        water_pct=80.0,
        health_pct=60.0,
        schools_pct=50.0,
        livelihoods_pct=40.0
    )
    # 0.25*100 + 0.25*80 + 0.20*60 + 0.15*50 + 0.15*40 = 25 + 20 + 12 + 7.5 + 6 = 70.5
    assert score == 70.5


# ==============================================================================
# 2. VULNERABILITY RESCORING TESTS
# ==============================================================================

def test_vulnerability_rescore_known_census():
    """Known census baseline properly bounds and rescores demographic vulnerability"""
    req = VulnerabilityRescoreRequest(
        ward_code="WARD-NORTH-04",
        district="DIST-NORTH",
        total_affected_population=1200,
        n_accessible_needs=40,
        n_chronic_medical=30,
        n_intersectional=10,
        census_baseline_population=10000,
        power_grid_restoration_pct=60.0,
        potable_water_access_pct=70.0,
        healthcare_facility_operational_pct=80.0,
        schools_open_pct=50.0,
        livelihoods_resumed_pct=40.0,
        remaining_displaced_persons=150
    )
    resp = CommunityMonitoringService.rescore_vulnerability(req)
    assert resp.ward_code == "WARD-NORTH-04"
    assert resp.baseline_status == "BASELINE_KNOWN"
    assert resp.effective_denominator == 2000.0  # max(100, 0.20 * 10000)
    assert 0.0 <= resp.base_demographic_vulnerability <= 1.0
    assert 0.0 <= resp.rescored_vulnerability <= 1.0
    assert resp.freshness_status == "FRESH"
    assert "formula" in resp.audit_trail


def test_vulnerability_rescore_unknown_census():
    """Missing census baseline uses guarded statutory reference scale (500.0) and sets uncertainty_flag"""
    req = VulnerabilityRescoreRequest(
        ward_code="WARD-UNKNOWN-CENSUS",
        district="DIST-REMOTE",
        total_affected_population=300,
        n_accessible_needs=20,
        n_chronic_medical=15,
        n_intersectional=5,
        census_baseline_population=None,
        power_grid_restoration_pct=20.0,
        potable_water_access_pct=30.0,
        healthcare_facility_operational_pct=10.0,
        schools_open_pct=0.0,
        livelihoods_resumed_pct=10.0,
        remaining_displaced_persons=80
    )
    resp = CommunityMonitoringService.rescore_vulnerability(req)
    assert resp.baseline_status == "BASELINE_UNKNOWN"
    assert resp.effective_denominator == 500.0
    assert resp.uncertainty_flag is True
    assert resp.infrastructure_deficit_score > 0.70


def test_vulnerability_rescore_with_decay():
    """Old verification timestamp triggers confidence decay and STALE/EXPIRED uncertainty flag"""
    eval_time = datetime.now(timezone.utc)
    old_time = eval_time - timedelta(days=25)
    req = VulnerabilityRescoreRequest(
        ward_code="WARD-STALE-01",
        district="DIST-EAST",
        total_affected_population=500,
        census_baseline_population=5000,
        power_grid_restoration_pct=50.0,
        potable_water_access_pct=50.0,
        remaining_displaced_persons=50,
        last_verified_at=old_time
    )
    resp = CommunityMonitoringService.rescore_vulnerability(req)
    assert resp.freshness_status in ("STALE_AMBER", "EXPIRED_RED")
    assert resp.data_confidence < 35.0
    assert resp.uncertainty_flag is True


# ==============================================================================
# 3. WHAT-IF SIMULATION ENGINE TESTS
# ==============================================================================

def test_what_if_simulation_nominal(db_session: Session):
    """Executes nominal what-if scenario projecting period snapshots across horizon"""
    req = RecoveryWhatIfSimulationRequest(
        scenario_name="Nominal Capital Restoration Baseline",
        planning_horizon_periods=12,
        period_length_days=30.0,
        initial_budget=15000000.0,
        periodic_budget_inflow=2000000.0,
        perturbation=SimulationPerturbationParams(
            budget_multiplier=1.0,
            material_supply_factor=1.0,
            disaster_recurrence_shock=False
        )
    )
    resp = RecoverySimulationService.simulate_what_if(db_session, req)
    assert resp.is_non_mutating is True
    assert len(resp.trajectory) == 12
    assert resp.baseline_final_recovery_score > 0.0
    assert resp.simulated_final_recovery_score == resp.baseline_final_recovery_score
    assert resp.recovery_score_delta == 0.0
    assert resp.trajectory[0].period == 1
    assert resp.trajectory[-1].period == 12


def test_what_if_simulation_budget_surge(db_session: Session):
    """20% budget multiplier completes projects earlier or with higher cumulative utilization"""
    req = RecoveryWhatIfSimulationRequest(
        scenario_name="Surge Recovery Funding Scenario",
        planning_horizon_periods=12,
        period_length_days=30.0,
        initial_budget=20000000.0,
        periodic_budget_inflow=3000000.0,
        perturbation=SimulationPerturbationParams(
            budget_multiplier=1.2,
            material_supply_factor=1.0,
            disaster_recurrence_shock=False
        )
    )
    resp = RecoverySimulationService.simulate_what_if(db_session, req)
    assert resp.total_budget_allocated > 20000000.0
    assert resp.simulated_final_recovery_score >= resp.baseline_final_recovery_score


def test_what_if_simulation_supply_shock_bottleneck(db_session: Session):
    """Severe material supply disruption (0.5) flags bottleneck resources"""
    req = RecoveryWhatIfSimulationRequest(
        scenario_name="Supply Chain Disruption Scenario",
        planning_horizon_periods=8,
        period_length_days=30.0,
        initial_budget=10000000.0,
        periodic_budget_inflow=1000000.0,
        perturbation=SimulationPerturbationParams(
            budget_multiplier=1.0,
            material_supply_factor=0.5,
            disaster_recurrence_shock=False
        )
    )
    resp = RecoverySimulationService.simulate_what_if(db_session, req)
    assert len(resp.bottleneck_resources) > 0
    for b in resp.bottleneck_resources:
        assert b.deficit_quantity > 0.0
        assert b.available_supply < b.demand_quantity


def test_what_if_simulation_recurrence_shock(db_session: Session):
    """Secondary hazard recurrence shock triggers shock flag and temporary regression"""
    req = RecoveryWhatIfSimulationRequest(
        scenario_name="Secondary Inundation Shock Scenario",
        planning_horizon_periods=10,
        period_length_days=30.0,
        initial_budget=12000000.0,
        periodic_budget_inflow=1500000.0,
        perturbation=SimulationPerturbationParams(
            budget_multiplier=1.0,
            material_supply_factor=1.0,
            disaster_recurrence_shock=True,
            shock_period=4,
            shock_damage_factor=0.3
        )
    )
    resp = RecoverySimulationService.simulate_what_if(db_session, req)
    shock_snapshots = [s for s in resp.trajectory if s.shock_occurred]
    assert len(shock_snapshots) == 1
    assert shock_snapshots[0].period == 4


def test_what_if_simulation_immutability_non_mutating(db_session: Session):
    """Guarantees zero database modifications before and after running simulation"""
    initial_project_count = db_session.query(RecoveryProject).count()
    initial_resource_count = db_session.query(RecoveryResource).count()

    req = RecoveryWhatIfSimulationRequest(
        scenario_name="Immutability Verification",
        planning_horizon_periods=6,
        initial_budget=5000000.0,
        periodic_budget_inflow=500000.0,
        perturbation=SimulationPerturbationParams(budget_multiplier=1.5, disaster_recurrence_shock=True)
    )
    resp = RecoverySimulationService.simulate_what_if(db_session, req)
    assert resp.is_non_mutating is True

    final_project_count = db_session.query(RecoveryProject).count()
    final_resource_count = db_session.query(RecoveryResource).count()
    assert final_project_count == initial_project_count
    assert final_resource_count == initial_resource_count


# ==============================================================================
# 4. API CONTRACT & INTEGRATION TESTS
# ==============================================================================

def test_api_community_metric_summary(test_client: TestClient, govt_token: str, db_session: Session):
    """GET /api/v1/recovery/monitoring/community-metrics/summary returns aggregated wards"""
    # Insert a test metric
    metric = CommunityRecoveryMetric(
        ward_code="WARD-TEST-01",
        district="DIST-CENTRAL",
        metric_date=datetime.now(timezone.utc),
        active_shelter_count=3,
        remaining_displaced_persons=220,
        power_grid_restoration_pct=85.0,
        potable_water_access_pct=90.0,
        healthcare_facility_operational_pct=75.0,
        schools_open_pct=70.0,
        livelihoods_resumed_pct=60.0,
        data_confidence=95.0,
        freshness_status="FRESH",
        last_verified_at=datetime.now(timezone.utc)
    )
    db_session.add(metric)
    db_session.commit()

    headers = {"Authorization": f"Bearer {govt_token}"}
    res = test_client.get("/api/v1/recovery/monitoring/community-metrics/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_wards_monitored"] >= 1
    assert "sector_restoration_averages" in data
    assert "wards" in data


def test_api_vulnerability_rescore(test_client: TestClient, govt_token: str):
    """POST /api/v1/recovery/monitoring/vulnerability-rescore executes rescore"""
    payload = {
        "ward_code": "WARD-INTEG-01",
        "district": "DIST-SOUTH",
        "total_affected_population": 800,
        "n_accessible_needs": 30,
        "n_chronic_medical": 20,
        "n_intersectional": 10,
        "census_baseline_population": 6000,
        "power_grid_restoration_pct": 70.0,
        "potable_water_access_pct": 75.0,
        "healthcare_facility_operational_pct": 60.0,
        "schools_open_pct": 50.0,
        "livelihoods_resumed_pct": 45.0,
        "remaining_displaced_persons": 100
    }
    headers = {"Authorization": f"Bearer {govt_token}"}
    res = test_client.post("/api/v1/recovery/monitoring/vulnerability-rescore", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["ward_code"] == "WARD-INTEG-01"
    assert "rescored_vulnerability" in data
    assert "audit_trail" in data


def test_api_what_if_simulation_rbac(test_client: TestClient, govt_token: str, citizen_token: str):
    """POST /api/v1/recovery/simulation/what-if enforces GOVT/ADMIN role"""
    payload = {
        "scenario_name": "API Role Boundary Test",
        "planning_horizon_periods": 6,
        "initial_budget": 5000000.0,
        "periodic_budget_inflow": 500000.0,
        "perturbation": {
            "budget_multiplier": 1.0,
            "material_supply_factor": 1.0,
            "disaster_recurrence_shock": False
        }
    }
    # Citizen access should be rejected with 403 Forbidden
    res_citizen = test_client.post(
        "/api/v1/recovery/simulation/what-if",
        json=payload,
        headers={"Authorization": f"Bearer {citizen_token}"}
    )
    assert res_citizen.status_code == 403

    # Govt access should succeed with 200 OK
    res_govt = test_client.post(
        "/api/v1/recovery/simulation/what-if",
        json=payload,
        headers={"Authorization": f"Bearer {govt_token}"}
    )
    assert res_govt.status_code == 200
    data = res_govt.json()
    assert data["scenario_name"] == "API Role Boundary Test"
    assert data["is_non_mutating"] is True


# ==============================================================================
# 5. CENSUS RECONCILIATION & CONFLICT DETECTION TESTS
# ==============================================================================

def test_census_reconciliation_empty(db_session: Session):
    """Empty reconciliation returns EMPTY status and 100% confidence"""
    from app.recovery.services.population_reconciliation import PopulationReconciliationService
    from app.schemas.recovery import PopulationReconciliationRequest

    req = PopulationReconciliationRequest(ward_code="NONEXISTENT-WARD-999")
    resp = PopulationReconciliationService.reconcile_population(db_session, req)
    assert resp.reconciliation_status == "EMPTY"
    assert resp.source_record_count == 0
    assert resp.confidence_score == 100.0


def test_census_reconciliation_duplicates_and_conflicts(db_session: Session):
    """Tests deduplication and conflict tracking across multi-need records"""
    from app.recovery.services.population_reconciliation import PopulationReconciliationService
    from app.schemas.recovery import PopulationReconciliationRequest
    from app.models.recovery import RecoveryNeed

    # Insert two records with same hash but conflicting displaced counts
    h = "test_beneficiary_hash_12345"
    n1 = RecoveryNeed(
        ward_code="WARD-RECON-01",
        district="DIST-RECON",
        sector="HOUSING",
        affected_households=4,
        displaced_persons=12,
        vulnerable_persons=2,
        beneficiary_id_hash=h,
        household_head_name_masked="J*** D***",
        census_baseline_population=5000
    )
    n2 = RecoveryNeed(
        ward_code="WARD-RECON-01",
        district="DIST-RECON",
        sector="WASH",
        affected_households=4,
        displaced_persons=20,  # conflicting observation
        vulnerable_persons=2,
        beneficiary_id_hash=h,
        household_head_name_masked="J*** D***",
        census_baseline_population=5000
    )
    db_session.add_all([n1, n2])
    db_session.commit()

    req = PopulationReconciliationRequest(ward_code="WARD-RECON-01")
    resp = PopulationReconciliationService.reconcile_population(db_session, req)

    assert resp.source_record_count == 2
    assert resp.unique_beneficiary_count == 1
    assert len(resp.duplicate_candidates) == 1
    assert len(resp.unresolved_conflicts) == 1
    assert resp.reconciliation_status == "FLAGGED_FOR_HUMAN_REVIEW"
    assert resp.confidence_score < 90.0
