"""
DIRS Phase 6D-B Milestone 3 Gate 2: Recovery Optimization API Route Test Suite.

Exhaustive verification of:
1. All solver outcomes (OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN, MODEL_INVALID, POST_SOLVE_RECONCILIATION_FAILED).
2. HTTP response semantics: 200, 401, 403, 422, 500.
3. Candidate count limit (Owner Decision A: 500 cap, 501 rejected before orchestrator execution).
4. API execution timeout cap (Owner Decision B: 120s default, env override, at-cap accept, above-cap reject, invalid config 500, no silent clamping).
5. Information leakage prevention on unexpected exceptions (sanitized 500 error DTO).
6. Correlation ID generation (fresh server-side UUID in X-Correlation-ID header).
7. Large integer objective preservation (> 2^53) and Decimal precision in JSON output.
8. Database safety: zero application-data writes, zero schedule persistence.
9. Concurrency & event-loop responsiveness: synchronous threadpool execution does not block async event loop.
"""

import os
import uuid
import time
import math
import asyncio
import threading
from decimal import Decimal
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, event

from app.main import app
from app.database import SessionLocal, engine
from app.models.user import User
from app.core.security import create_access_token
from app.core.deps import get_current_user, require_any_role
from app.schemas.recovery_optimization import (
    RecoveryOptimizationScenarioRequest,
    RecoveryOptimizationScenarioResponse,
    OptimizationErrorDetailDTO,
    OptimizationErrorType,
    ScheduledProjectResultDTO,
    PeriodSolvencyResultDTO,
    InfeasibilityDiagnosticReportDTO,
    InfeasibilityFindingDTO,
)
from app.recovery.optimization.schemas import (
    RecoveryOptimizationResponse,
    ScheduledProjectResult,
    PeriodSolvencyResult,
    InfeasibilityDiagnosticReport,
    InfeasibilityFinding,
    CurrencyUnit,
)
from app.recovery.services.recovery_optimization_service import (
    RecoveryOptimizationService,
    MAX_SCENARIO_CANDIDATES,
    DEFAULT_API_TIMEOUT_CAP_SECONDS,
    get_api_timeout_cap_seconds,
)

client = TestClient(app)


# ==============================================================================
# Test Fixtures and Helpers
# ==============================================================================

@pytest.fixture(autouse=True)
def clean_dependency_overrides_and_env():
    """Ensures clean dependency overrides and environment before and after every test."""
    app.dependency_overrides.clear()
    old_env = os.environ.get("DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS")
    yield
    app.dependency_overrides.clear()
    if old_env is not None:
        os.environ["DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS"] = old_env
    else:
        os.environ.pop("DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS", None)


def override_auth_user(role: str = "GOVT", user_id: str = "test-user-uuid-1"):
    """Overrides get_current_user with an in-memory User with the given role."""
    mock_user = User(
        id=user_id,
        email=f"test_{role.lower()}@dirs.gov.in",
        full_name=f"{role} Test Officer",
        role=role,
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return mock_user


def make_valid_minimal_payload():
    """Generates a valid minimal request payload."""
    return {
        "scenario_name": "API_Route_Test_Scenario",
        "planning_horizon_periods": 12,
        "period_length_days": 30,
        "initial_cash": "5000000.00",
        "cash_currency": "INR",
        "periodic_budgets": {
            "1": "1000000.00",
            "2": "1000000.00",
            "3": "1000000.00",
        },
        "budget_currency": "INR",
        "district_equity_targets": {},
        "blackout_districts": [],
        "candidates": [],
        "dependencies": [],
        "resource_capacities": {},
        "funding_sources": [],
        "fiscal_retention_rate": 1.0,
        "enable_early_start_bonus": True,
        "max_safety_start_period": None,
        "max_solve_time_seconds": 10.0,
        "deterministic_seed": 42,
        "num_workers": 1,
        "allow_uniform_weight_fallback": False,
    }


def make_single_candidate(project_id="PROJ_001", is_mandatory=False):
    """Generates a valid single candidate dictionary matching ProjectOptimizationCandidateDTO."""
    return {
        "project_id": project_id,
        "project_code": f"CODE_{project_id}",
        "district_id": "DIST_A",
        "estimated_cost": "250000.00",
        "cost_currency": "INR",
        "duration_periods": 2,
        "release_period": 1,
        "deadline_period": 6,
        "is_tier1_mandatory": is_mandatory,
        "raw_mcpi_score": 0.75,
        "expenditure_weights": [0.5, 0.5],
        "resource_demands": {},
        "eligible_funds": [],
    }


# ==============================================================================
# 1. Core Solver Outcomes Tests (HTTP 200)
# ==============================================================================

def test_01_api_optimal_scenario_real_integration():
    """Test 01: Real integration with CP-SAT solver for a valid scenario yielding OPTIMAL."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()
    payload["candidates"] = [make_single_candidate("PROJ_WATER_1", is_mandatory=False)]

    resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["solver_status"] == "OPTIMAL"
    assert data["is_optimal"] is True
    assert data["exact_objective_value"] is not None
    assert data["exact_best_bound"] == data["exact_objective_value"]
    assert data["conservative_best_bound"] == data["exact_objective_value"]
    assert data["optimality_gap"] == 0.0
    assert data["selected_project_count"] == 1
    assert len(data["scheduled_projects"]) == 1
    assert data["scheduled_projects"][0]["project_id"] == "PROJ_WATER_1"
    assert data["scheduled_projects"][0]["is_selected"] is True
    assert "X-Correlation-ID" in resp.headers


def test_02_api_feasible_suboptimal_scenario():
    """Test 02: Verification of FEASIBLE suboptimal solver outcome via mock."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()
    payload["candidates"] = [make_single_candidate("PROJ_001")]

    mock_resp = RecoveryOptimizationResponse(
        scenario_name="Test_Feasible",
        solver_status="FEASIBLE",
        is_optimal=False,
        exact_objective_value=50000,
        exact_best_bound=60000,
        conservative_best_bound=60000,
        objective_value=500.0,
        best_bound=600.0,
        optimality_gap=0.2,
        solve_time_seconds=1.5,
        selected_project_count=1,
        total_cost_ccu=25000000,
        total_cost_inr=Decimal("250000.00"),
        scheduled_projects=[
            ScheduledProjectResult(
                project_id="PROJ_001",
                project_code="CODE_PROJ_001",
                district_id="DIST_A",
                is_selected=True,
                scheduled_start_period=1,
                scheduled_completion_period=2,
                assigned_funding_source=None,
                cost_ccu=25000000,
                cost_inr=Decimal("250000.00"),
                periodic_expenditures_ccu={1: 12500000, 2: 12500000},
                periodic_expenditures_inr={1: Decimal("125000.00"), 2: Decimal("125000.00")},
                mcpi_score=500.0,
                raw_mcpi_score=0.75,
                quantized_mcpi_coefficient=750,
                is_tier1_mandatory=False,
            )
        ],
        periodic_solvency=[
            PeriodSolvencyResult(
                period=1,
                revenue_receipt_ccu=100000000,
                expenditure_ccu=12500000,
                cash_balance_ccu=587500000,
                cash_balance_inr=Decimal("5875000.00"),
                is_solvent=True,
            )
        ],
        district_equity_allocation_ccu={"DIST_A": 25000000},
        district_equity_allocation_inr={"DIST_A": Decimal("250000.00")},
        input_fingerprint_sha256="fake_sha256",
        ortools_version="9.15.6755",
        solver_parameters={},
        infeasibility_diagnostics=None,
    )

    with patch(
        "app.recovery.services.recovery_optimization_service.RecoveryOptimizationOrchestrator.optimize_recovery_portfolio",
        return_value=mock_resp,
    ):
        resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["solver_status"] == "FEASIBLE"
        assert data["is_optimal"] is False
        assert data["exact_objective_value"] == 50000
        assert data["conservative_best_bound"] == 60000
        assert data["optimality_gap"] == 0.2
        assert data["selected_project_count"] == 1


def test_03_api_infeasible_scenario_diagnostics():
    """Test 03: Verification of INFEASIBLE solver outcome returning diagnostic report."""
    override_auth_user("GOVT")
    valid_payload = make_valid_minimal_payload()
    valid_payload["candidates"] = [make_single_candidate("MANDATORY_PROJ_1", is_mandatory=True)]
    valid_payload["max_safety_start_period"] = 3

    mock_resp = RecoveryOptimizationResponse(
        scenario_name="Test_Infeasible",
        solver_status="INFEASIBLE",
        is_optimal=False,
        exact_objective_value=None,
        exact_best_bound=None,
        conservative_best_bound=None,
        objective_value=None,
        best_bound=None,
        optimality_gap=None,
        solve_time_seconds=0.05,
        selected_project_count=0,
        total_cost_ccu=0,
        total_cost_inr=Decimal("0"),
        scheduled_projects=[],
        periodic_solvency=[],
        district_equity_allocation_ccu={},
        district_equity_allocation_inr={},
        input_fingerprint_sha256="fake_sha256",
        ortools_version="9.15.6755",
        solver_parameters={},
        infeasibility_diagnostics=InfeasibilityDiagnosticReport(
            has_proven_infeasibility=True,
            proven_causes=[
                InfeasibilityFinding(
                    category="CASH_FLOW_DEFICIT",
                    classification="PROVEN_INFEASIBILITY",
                    message="Mandatory projects require 5000000 CCU at period 1, but only 1000000 CCU available.",
                    mathematical_condition=r"\sum_{i \in \mathcal{M}} c_{i,1} > B_1 + C_0",
                    affected_projects=["MANDATORY_PROJ_1"],
                )
            ],
            necessary_condition_violations=[],
            solver_hypotheses=[],
            warnings=[],
        ),
    )

    with patch(
        "app.recovery.services.recovery_optimization_service.RecoveryOptimizationOrchestrator.optimize_recovery_portfolio",
        return_value=mock_resp,
    ):
        resp = client.post("/api/v1/recovery/optimization/evaluate", json=valid_payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["solver_status"] == "INFEASIBLE"
        assert data["is_optimal"] is False
        assert data["exact_objective_value"] is None
        assert data["infeasibility_diagnostics"]["has_proven_infeasibility"] is True
        assert len(data["infeasibility_diagnostics"]["proven_causes"]) == 1
        assert data["infeasibility_diagnostics"]["proven_causes"][0]["category"] == "CASH_FLOW_DEFICIT"


def test_04_api_unknown_solver_result():
    """Test 04: UNKNOWN solver outcome (timeout without finding feasible solution)."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()

    mock_resp = RecoveryOptimizationResponse(
        scenario_name="Test_Unknown",
        solver_status="UNKNOWN",
        is_optimal=False,
        exact_objective_value=None,
        exact_best_bound=None,
        conservative_best_bound=None,
        objective_value=None,
        best_bound=None,
        optimality_gap=None,
        solve_time_seconds=10.0,
        selected_project_count=0,
        total_cost_ccu=0,
        total_cost_inr=Decimal("0"),
        scheduled_projects=[],
        periodic_solvency=[],
        district_equity_allocation_ccu={},
        district_equity_allocation_inr={},
        input_fingerprint_sha256="fake_sha256",
        ortools_version="9.15.6755",
        solver_parameters={},
        infeasibility_diagnostics=None,
    )

    with patch(
        "app.recovery.services.recovery_optimization_service.RecoveryOptimizationOrchestrator.optimize_recovery_portfolio",
        return_value=mock_resp,
    ):
        resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["solver_status"] == "UNKNOWN"
        assert data["is_optimal"] is False
        assert data["selected_project_count"] == 0
        assert data["exact_objective_value"] is None


def test_05_api_model_invalid_precedence_cycle():
    """Test 05: Real integration catching cyclic dependencies yielding MODEL_INVALID."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()
    payload["candidates"] = [
        make_single_candidate("P1"),
        make_single_candidate("P2"),
    ]
    payload["dependencies"] = [
        {"predecessor_id": "P1", "successor_id": "P2", "lag_periods": 0},
        {"predecessor_id": "P2", "successor_id": "P1", "lag_periods": 0},
    ]

    resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["solver_status"] == "MODEL_INVALID"
    assert data["is_optimal"] is False
    assert data["infeasibility_diagnostics"]["has_proven_infeasibility"] is True
    finding = data["infeasibility_diagnostics"]["proven_causes"][0]
    assert finding["category"] == "PRECEDENCE_DEADLINE_CONFLICT"
    assert "cyclic" in finding["message"].lower()


def test_06_api_post_solve_reconciliation_failed_retention():
    """Test 06: Verification of POST_SOLVE_RECONCILIATION_FAILED status retaining solver metadata."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()
    payload["candidates"] = [make_single_candidate("PROJ_REC_1")]

    mock_resp = RecoveryOptimizationResponse(
        scenario_name="Test_Reconciliation_Failure",
        solver_status="POST_SOLVE_RECONCILIATION_FAILED",
        is_optimal=False,
        exact_objective_value=40000,
        exact_best_bound=40000,
        conservative_best_bound=40000,
        objective_value=400.0,
        best_bound=400.0,
        optimality_gap=0.0,
        solve_time_seconds=0.25,
        selected_project_count=1,
        total_cost_ccu=25000000,
        total_cost_inr=Decimal("250000.00"),
        scheduled_projects=[
            ScheduledProjectResult(
                project_id="PROJ_REC_1",
                project_code="CODE_PROJ_REC_1",
                district_id="DIST_A",
                is_selected=True,
                scheduled_start_period=1,
                scheduled_completion_period=2,
                assigned_funding_source=None,
                cost_ccu=25000000,
                cost_inr=Decimal("250000.00"),
                periodic_expenditures_ccu={1: 12500000, 2: 12500000},
                periodic_expenditures_inr={1: Decimal("125000.00"), 2: Decimal("125000.00")},
                mcpi_score=400.0,
                raw_mcpi_score=0.75,
                quantized_mcpi_coefficient=750,
                is_tier1_mandatory=False,
            )
        ],
        periodic_solvency=[],
        district_equity_allocation_ccu={},
        district_equity_allocation_inr={},
        input_fingerprint_sha256="fake_sha256",
        ortools_version="9.15.6755",
        solver_parameters={},
        infeasibility_diagnostics=InfeasibilityDiagnosticReport(
            has_proven_infeasibility=True,
            proven_causes=[
                InfeasibilityFinding(
                    category="POST_SOLVE_RECONCILIATION_FAILED",
                    classification="PROVEN_INFEASIBILITY",
                    message="Invariant check failed: period 2 negative cash balance.",
                    mathematical_condition="Post-solve invariant reconciliation check failed",
                    affected_projects=[],
                )
            ],
            necessary_condition_violations=[],
            solver_hypotheses=[],
            warnings=[],
        ),
    )

    with patch(
        "app.recovery.services.recovery_optimization_service.RecoveryOptimizationOrchestrator.optimize_recovery_portfolio",
        return_value=mock_resp,
    ):
        resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["solver_status"] == "POST_SOLVE_RECONCILIATION_FAILED"
        assert data["is_optimal"] is False
        assert data["exact_objective_value"] == 40000
        assert data["selected_project_count"] == 1
        assert len(data["scheduled_projects"]) == 1
        assert data["infeasibility_diagnostics"]["has_proven_infeasibility"] is True


# ==============================================================================
# 2. RSK-M2-07 Governance & Input Validation Tests (HTTP 422)
# ==============================================================================

def test_07_api_rsk_m2_07_missing_safety_deadline():
    """Test 07: Omission of max_safety_start_period with Tier-1 mandatory projects -> HTTP 422."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()
    payload["candidates"] = [make_single_candidate("MANDATORY_1", is_mandatory=True)]
    payload["max_safety_start_period"] = None

    resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp.status_code == 422
    assert "RSK-M2-07" in resp.text


def test_08_api_rsk_m2_07_invalid_safety_deadline():
    """Test 08: Non-positive or out-of-horizon max_safety_start_period -> HTTP 422."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()
    payload["candidates"] = [make_single_candidate("MANDATORY_1", is_mandatory=True)]

    # Case A: 0 (must be >= 1)
    payload["max_safety_start_period"] = 0
    resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp.status_code == 422

    # Case B: Out of horizon (> 12)
    payload["max_safety_start_period"] = 15
    resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp.status_code == 422
    assert "RSK-M2-07" in resp.text


def test_09_api_unknown_request_field_rejection():
    """Test 09: Rejection of unrecognized fields via extra='forbid' -> HTTP 422."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()
    payload["injected_illegal_field"] = "malicious_payload"

    resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp.status_code == 422
    assert "extra_forbidden" in resp.text


def test_10_api_non_finite_float_rejection():
    """Test 10: Rejection of non-finite float strings ('NaN', 'Infinity') -> HTTP 422."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()
    payload["candidates"] = [make_single_candidate("P1")]
    payload["candidates"][0]["raw_mcpi_score"] = "NaN"

    resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp.status_code == 422

    # Also test Decimal NaN string rejection
    payload["candidates"][0]["raw_mcpi_score"] = 0.5
    payload["candidates"][0]["estimated_cost"] = "NaN"
    resp_dec = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp_dec.status_code == 422
    assert "finite_number" in resp_dec.text


# ==============================================================================
# 3. Candidate Count Limit Policy Tests (Owner Decision A)
# ==============================================================================

def test_11_api_candidate_count_limit_500_accepted():
    """Test 11a: 500 candidate projects passes the count guard (mocked solver)."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()
    # Construct 500 candidates
    payload["candidates"] = [make_single_candidate(f"P_{i}") for i in range(500)]

    mock_resp = RecoveryOptimizationResponse(
        scenario_name="Test_500",
        solver_status="OPTIMAL",
        is_optimal=True,
        exact_objective_value=100,
        exact_best_bound=100,
        conservative_best_bound=100,
        objective_value=1.0,
        best_bound=1.0,
        optimality_gap=0.0,
        solve_time_seconds=0.5,
        selected_project_count=0,
        total_cost_ccu=0,
        total_cost_inr=Decimal("0"),
        scheduled_projects=[],
        periodic_solvency=[],
        district_equity_allocation_ccu={},
        district_equity_allocation_inr={},
        input_fingerprint_sha256="fake_sha256",
        ortools_version="9.15.6755",
        solver_parameters={},
        infeasibility_diagnostics=None,
    )

    with patch(
        "app.recovery.services.recovery_optimization_service.RecoveryOptimizationOrchestrator.optimize_recovery_portfolio",
        return_value=mock_resp,
    ) as mock_orch:
        resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
        assert resp.status_code == 200
        assert mock_orch.called is True


def test_11_api_candidate_count_limit_501_rejected_before_orchestrator():
    """Test 11b: 501 candidate projects rejected with HTTP 422 without invoking orchestrator."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()
    payload["candidates"] = [make_single_candidate(f"P_{i}") for i in range(501)]

    with patch(
        "app.recovery.services.recovery_optimization_service.RecoveryOptimizationOrchestrator.optimize_recovery_portfolio"
    ) as mock_orch:
        resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
        assert resp.status_code == 422
        assert "Candidate count (501) exceeds maximum permitted scenario size of 500" in resp.text
        # CRUCIAL INVARIANT: Orchestrator MUST NOT have been invoked
        assert mock_orch.called is False


# ==============================================================================
# 4. Precision Preservation Tests (Arbitrary Int > 2^53 & Decimal)
# ==============================================================================

def test_12_api_large_integer_objective_preservation_above_2_pow_53():
    """Test 12: Preserving arbitrary-precision 64-bit integer objectives > 2^53 in JSON."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()
    large_int = 2**54 + 9999  # 18,014,398,509,491,983 > 2^53 (9,007,199,254,740,992)

    mock_resp = RecoveryOptimizationResponse(
        scenario_name="Test_Large_Int",
        solver_status="OPTIMAL",
        is_optimal=True,
        exact_objective_value=large_int,
        exact_best_bound=large_int,
        conservative_best_bound=large_int,
        objective_value=float(large_int),
        best_bound=float(large_int),
        optimality_gap=0.0,
        solve_time_seconds=0.1,
        selected_project_count=0,
        total_cost_ccu=0,
        total_cost_inr=Decimal("0"),
        scheduled_projects=[],
        periodic_solvency=[],
        district_equity_allocation_ccu={},
        district_equity_allocation_inr={},
        input_fingerprint_sha256="fake_sha256",
        ortools_version="9.15.6755",
        solver_parameters={},
        infeasibility_diagnostics=None,
    )

    with patch(
        "app.recovery.services.recovery_optimization_service.RecoveryOptimizationOrchestrator.optimize_recovery_portfolio",
        return_value=mock_resp,
    ):
        resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["exact_objective_value"] == large_int
        assert data["exact_best_bound"] == large_int
        assert data["conservative_best_bound"] == large_int


def test_13_api_decimal_json_serialization_precision():
    """
    Test 13: Exact Decimal string preservation in costs without float conversion.
    Verifies that high-precision Decimals with many fractional digits serialize as exact
    strings (not IEEE 754 floats) across all top-level and nested response structures.
    """
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()
    payload["candidates"] = [make_single_candidate("PROJ_DEC")]
    exact_cost = Decimal("9876543210.123456789012345678")
    exact_cost_str = "9876543210.123456789012345678"

    mock_resp = RecoveryOptimizationResponse(
        scenario_name="Test_Decimal",
        solver_status="OPTIMAL",
        is_optimal=True,
        exact_objective_value=100,
        exact_best_bound=100,
        conservative_best_bound=100,
        objective_value=1.0,
        best_bound=1.0,
        optimality_gap=0.0,
        solve_time_seconds=0.1,
        selected_project_count=1,
        total_cost_ccu=987654321012,
        total_cost_inr=exact_cost,
        scheduled_projects=[
            ScheduledProjectResult(
                project_id="PROJ_DEC",
                project_code="CODE_PROJ_DEC",
                district_id="DIST_A",
                is_selected=True,
                scheduled_start_period=1,
                scheduled_completion_period=1,
                assigned_funding_source=None,
                cost_ccu=987654321012,
                cost_inr=exact_cost,
                periodic_expenditures_ccu={1: 987654321012},
                periodic_expenditures_inr={1: exact_cost},
                mcpi_score=1.0,
                raw_mcpi_score=0.8,
                quantized_mcpi_coefficient=800,
                is_tier1_mandatory=False,
            )
        ],
        periodic_solvency=[],
        district_equity_allocation_ccu={},
        district_equity_allocation_inr={"DIST_A": exact_cost},
        input_fingerprint_sha256="fake_sha256",
        ortools_version="9.15.6755",
        solver_parameters={},
        infeasibility_diagnostics=None,
    )

    with patch(
        "app.recovery.services.recovery_optimization_service.RecoveryOptimizationOrchestrator.optimize_recovery_portfolio",
        return_value=mock_resp,
    ):
        resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        # 1. Total cost: verify explicit string type and exact value without float loss
        total_val = data["total_cost_inr"]
        assert isinstance(total_val, str), f"Expected str JSON representation for Decimal, got {type(total_val)}"
        assert total_val == exact_cost_str
        assert Decimal(total_val) == exact_cost

        # 2. Nested scheduled-project cost: verify explicit string type and exact value
        proj_val = data["scheduled_projects"][0]["cost_inr"]
        assert isinstance(proj_val, str), f"Expected str JSON representation for Decimal, got {type(proj_val)}"
        assert proj_val == exact_cost_str
        assert Decimal(proj_val) == exact_cost

        # 3. Nested periodic expenditure: verify explicit string type and exact value
        period_exp = data["scheduled_projects"][0]["periodic_expenditures_inr"]["1"]
        assert isinstance(period_exp, str), f"Expected str JSON representation for Decimal, got {type(period_exp)}"
        assert period_exp == exact_cost_str
        assert Decimal(period_exp) == exact_cost

        # 4. District equity allocation cost: verify explicit string type and exact value
        equity_val = data["district_equity_allocation_inr"]["DIST_A"]
        assert isinstance(equity_val, str), f"Expected str JSON representation for Decimal, got {type(equity_val)}"
        assert equity_val == exact_cost_str
        assert Decimal(equity_val) == exact_cost


# ==============================================================================
# 5. Correlation ID & Exception Information Leakage Prevention
# ==============================================================================

def test_14_api_correlation_uuid_generation_and_propagation(caplog):
    """
    Test 14: Server generates fresh UUID for X-Correlation-ID on every request,
    ignoring any untrusted client-supplied header value.
    """
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()

    # Part A: Untrusted client-supplied correlation ID must be ignored
    untrusted_id = "attacker-supplied-value"
    with caplog.at_level("INFO"):
        resp_attacker = client.post(
            "/api/v1/recovery/optimization/evaluate",
            json=payload,
            headers={"X-Correlation-ID": untrusted_id},
        )
    assert resp_attacker.status_code == 200
    server_cid = resp_attacker.headers.get("X-Correlation-ID")
    assert server_cid is not None
    # 1. Assert response contains a valid server-generated UUID v4
    parsed_uuid = uuid.UUID(server_cid)
    assert parsed_uuid.version == 4
    # 2. Assert returned ID is NOT equal to client-supplied value
    assert server_cid != untrusted_id
    # 3. Verify server-generated UUID is used consistently in server telemetry logs
    log_records = [r for r in caplog.records if server_cid in r.getMessage()]
    assert len(log_records) > 0, f"Expected server correlation ID {server_cid} in telemetry logs"
    for r in caplog.records:
        assert untrusted_id not in r.getMessage()

    # Part B: Untrusted client-supplied correlation ID on unexpected 500 exception
    sensitive_msg = "Database failure simulation"
    with patch(
        "app.recovery.services.recovery_optimization_service.RecoveryOptimizationOrchestrator.optimize_recovery_portfolio",
        side_effect=RuntimeError(sensitive_msg),
    ):
        resp_err = client.post(
            "/api/v1/recovery/optimization/evaluate",
            json=payload,
            headers={"X-Correlation-ID": untrusted_id},
        )
        assert resp_err.status_code == 500
        err_cid = resp_err.headers.get("X-Correlation-ID")
        assert err_cid is not None
        assert uuid.UUID(err_cid).version == 4
        assert err_cid != untrusted_id
        # Diagnostic code in error payload matches server-generated header and not attacker value
        err_data = resp_err.json()
        assert err_data["diagnostic_code"] == err_cid
        assert err_data["diagnostic_code"] != untrusted_id

    # Part C: Existing fresh-UUID-per-request tests continue to pass
    resp1 = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    resp2 = client.post("/api/v1/recovery/optimization/evaluate", json=payload)

    cid1 = resp1.headers.get("X-Correlation-ID")
    cid2 = resp2.headers.get("X-Correlation-ID")

    assert cid1 is not None
    assert cid2 is not None
    uuid.UUID(cid1)
    uuid.UUID(cid2)
    assert cid1 != cid2
    assert cid1 != server_cid
    assert cid2 != server_cid


def test_15_api_unexpected_orchestrator_exception_sanitized_500():
    """Test 15: Unexpected internal exception produces sanitized HTTP 500 without leaking secrets."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()

    sensitive_internal_message = "CRITICAL: Database connection failed at postgresql://user:Secret123@internal.db:5432"

    with patch(
        "app.recovery.services.recovery_optimization_service.RecoveryOptimizationOrchestrator.optimize_recovery_portfolio",
        side_effect=RuntimeError(sensitive_internal_message),
    ):
        resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
        assert resp.status_code == 500
        data = resp.json()

        # Validate structured error DTO conformance
        assert data["error_type"] == "INTERNAL_EXECUTION_FAILURE"
        assert data["message"] == "An unexpected internal error occurred during scenario optimization execution."
        assert "X-Correlation-ID" in resp.headers
        assert data["diagnostic_code"] == resp.headers["X-Correlation-ID"]
        assert data["validation_failures"] == []

        # CRITICAL SECURITY CHECK: Secret internal string must NOT be present in response
        assert "Secret123" not in resp.text
        assert "postgresql://" not in resp.text


# ==============================================================================
# 6. Authentication & Role-Based Access Control Tests
# ==============================================================================

def test_16_api_auth_missing_or_invalid_produces_401():
    """Test 16: Request without Authorization header or with garbage token -> HTTP 401."""
    payload = make_valid_minimal_payload()

    # Case A: No token
    resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp.status_code == 401

    # Case B: Garbage token
    resp = client.post(
        "/api/v1/recovery/optimization/evaluate",
        json=payload,
        headers={"Authorization": "Bearer not-a-valid-jwt-token"},
    )
    assert resp.status_code == 401


def test_17_api_auth_unauthorized_role_produces_403():
    """Test 17: Valid authenticated user with CITIZEN or VOLUNTEER role -> HTTP 403."""
    payload = make_valid_minimal_payload()

    # Case A: CITIZEN
    override_auth_user("CITIZEN")
    resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp.status_code == 403
    assert "Operation not permitted" in resp.text

    # Case B: VOLUNTEER
    override_auth_user("VOLUNTEER")
    resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp.status_code == 403


def test_18_api_auth_authorized_govt_and_admin_produces_200():
    """Test 18: GOVT and ADMIN roles permitted to evaluate optimization scenarios."""
    payload = make_valid_minimal_payload()

    # Case A: GOVT
    override_auth_user("GOVT")
    resp_govt = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp_govt.status_code == 200

    # Case B: ADMIN
    override_auth_user("ADMIN")
    resp_admin = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp_admin.status_code == 200


# ==============================================================================
# 7. Database Safety & Persistence Invariant Tests
# ==============================================================================

def test_19_api_zero_application_data_writes():
    """
    Test 19: Pure in-memory computation: Zero DB writes or mutations.
    Monitors all SQLAlchemy engine statements during real JWT-authenticated scenario evaluations:
    - Real JWT authentication path: Uses actual JWT token and real get_current_user dependency (no overrides).
    - Detects INSERT, UPDATE, DELETE, MERGE, DROP, ALTER, and TRUNCATE statements against application tables.
    - Permits expected read-only SELECT statements required for authentication / user lookup.
    - Verifies that the optimization service and solver produce zero database DML.
    - Preserves exact before/after row-count comparison across all 8 application tables.
    - Robust cleanup: Ensures event listeners are removed, database sessions closed, and FastAPI dependency overrides restored in finally blocks.
    """
    # 1. Dependency overrides snapshot for strict test isolation
    original_overrides = app.dependency_overrides.copy()
    try:
        # Clear overrides for real JWT authentication path (un-mocked get_current_user)
        app.dependency_overrides.clear()

        db = SessionLocal()
        try:
            # Retrieve existing active GOVT user from database (before monitored interval)
            govt_user = db.query(User).filter(User.role == "GOVT", User.is_active == True).first()
            if not govt_user:
                govt_user = User(
                    id=str(uuid.uuid4()),
                    email=f"test_govt_{uuid.uuid4().hex[:6]}@dirs.gov.in",
                    hashed_password="fake_hashed_pw",
                    full_name="GOVT Test Officer",
                    role="GOVT",
                    is_active=True,
                )
                db.add(govt_user)
                db.commit()
                db.refresh(govt_user)

            # Generate actual JWT access token using the project's canonical mechanism
            token = create_access_token(subject=govt_user.id)
            auth_headers = {"Authorization": f"Bearer {token}"}

            # 2. Baseline row-count snapshot across all 8 application tables
            table_names = [
                "users",
                "recovery_projects",
                "recovery_assessments",
                "recovery_needs",
                "project_dependencies",
                "recovery_resources",
                "community_recovery_metrics",
                "recovery_override_logs",
            ]
            before_counts = {t: db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() for t in table_names}

            # 3. Setup SQLAlchemy engine statement listener immediately prior to monitored requests
            captured_statements = []

            def statement_monitor(conn, cursor, statement, parameters, context, executemany):
                captured_statements.append(statement)

            event.listen(engine, "before_cursor_execute", statement_monitor)
            try:
                # Explicit assertion: get_current_user is NOT mocked or overridden
                assert get_current_user not in app.dependency_overrides, (
                    "Real authentication path requires un-mocked get_current_user dependency"
                )

                payload = make_valid_minimal_payload()
                payload["candidates"] = [make_single_candidate("PROJ_REAL_JWT_DML_1")]

                # 4. Execute real JWT-authenticated scenario evaluation request
                res_real = client.post(
                    "/api/v1/recovery/optimization/evaluate",
                    json=payload,
                    headers=auth_headers,
                )
                assert res_real.status_code == 200, res_real.text
                real_data = res_real.json()
                assert real_data["solver_status"] in ("OPTIMAL", "FEASIBLE")
                assert "exact_objective_value" in real_data
                assert "scheduled_projects" in real_data
                assert "X-Correlation-ID" in res_real.headers

                # 5. Execute 4 additional scenario evaluations to verify repeated execution safety
                for _ in range(4):
                    res_rep = client.post(
                        "/api/v1/recovery/optimization/evaluate",
                        json=payload,
                        headers=auth_headers,
                    )
                    assert res_rep.status_code == 200

                # 6. Verify that authentication executed its expected read-only database query
                auth_selects = [
                    s for s in captured_statements
                    if "SELECT" in s.upper() and ("users" in s.lower() or "user" in s.lower())
                ]
                assert len(auth_selects) >= 1, (
                    "Expected database-backed user lookup SELECT query during real JWT authentication"
                )

                # 7. Intercept and classify prohibited DML statements
                dml_keywords = ("INSERT", "UPDATE", "DELETE", "MERGE", "DROP", "ALTER", "TRUNCATE")
                dml_statements = []
                for s in captured_statements:
                    cleaned = s.strip().upper()
                    while cleaned.startswith("/*") and "*/" in cleaned:
                        cleaned = cleaned[cleaned.find("*/") + 2:].strip()
                    while cleaned.startswith("--"):
                        cleaned = cleaned.split("\n", 1)[-1].strip() if "\n" in cleaned else ""
                    if cleaned.startswith(dml_keywords):
                        dml_statements.append(s)

                # Assert strictly zero DML statements executed
                assert len(dml_statements) == 0, (
                    f"Prohibited database DML detected during optimization evaluation: {dml_statements}"
                )

                # 8. Post-execution row count snapshot verification
                after_counts = {t: db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() for t in table_names}
                assert before_counts == after_counts, (
                    f"DB counts changed: before={before_counts}, after={after_counts}"
                )
            finally:
                # Guaranteed event listener cleanup even if any assertion fails
                event.remove(engine, "before_cursor_execute", statement_monitor)
        finally:
            # Guaranteed database session closure
            db.close()
    finally:
        # Guaranteed restoration of original dependency overrides even on failure
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)

    # 9. Explicit assertion verifying dependency overrides are restored to original state
    assert app.dependency_overrides == original_overrides, (
        f"Dependency overrides not restored: expected {original_overrides}, got {app.dependency_overrides}"
    )


# ==============================================================================
# 8. Concurrency & Event Loop Responsiveness Tests (Deterministic Synchronization)
# ==============================================================================

def test_20_api_event_loop_responsiveness_controlled_blocking():
    """
    Test 20: Controlled blocking solver executed in worker thread does NOT block async event loop.
    Uses deterministic threading.Event synchronization instead of brittle wall-clock thresholds.
    """
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()

    solver_started = threading.Event()
    health_handled = threading.Event()

    def controlled_blocking_solver(engine_req):
        # 1. Signal that worker thread has entered solver execution
        solver_started.set()
        # 2. Wait until event loop has successfully processed concurrent health check
        # If the event loop were blocked, health_handled would never be set, timing out after 4.0s
        if not health_handled.wait(timeout=4.0):
            raise RuntimeError("EVENT LOOP BLOCKED: Health check was never processed!")
        return RecoveryOptimizationResponse(
            scenario_name=engine_req.scenario_name,
            solver_status="OPTIMAL",
            is_optimal=True,
            exact_objective_value=10,
            exact_best_bound=10,
            conservative_best_bound=10,
            objective_value=1.0,
            best_bound=1.0,
            optimality_gap=0.0,
            solve_time_seconds=0.1,
            selected_project_count=0,
            total_cost_ccu=0,
            total_cost_inr=Decimal("0"),
            scheduled_projects=[],
            periodic_solvency=[],
            district_equity_allocation_ccu={},
            district_equity_allocation_inr={},
            input_fingerprint_sha256="fake_sha256",
            ortools_version="9.15.6755",
            solver_parameters={},
            infeasibility_diagnostics=None,
        )

    import httpx

    async def run_deterministic_concurrency():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            with patch(
                "app.recovery.services.recovery_optimization_service.RecoveryOptimizationOrchestrator.optimize_recovery_portfolio",
                side_effect=controlled_blocking_solver,
            ):
                # Launch optimization request in worker threadpool
                opt_task = asyncio.create_task(
                    ac.post("/api/v1/recovery/optimization/evaluate", json=payload)
                )

                # Poll until solver thread has started
                while not solver_started.is_set():
                    await asyncio.sleep(0.01)

                # Concurrently execute health check on event loop while solver is blocked
                health_resp = await ac.get("/api/v1/health")
                assert health_resp.status_code == 200

                # Signal solver to release
                health_handled.set()

                # Await optimization completion
                opt_resp = await opt_task
                assert opt_resp.status_code == 200

    asyncio.run(run_deterministic_concurrency())


# ==============================================================================
# 9. API Execution Timeout Cap Tests (Owner Decision B)
# ==============================================================================

def test_21_api_timeout_cap_default_120():
    """Test 21: Verify default API timeout cap is 120.0s when environment variable is unset."""
    os.environ.pop("DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS", None)
    assert get_api_timeout_cap_seconds() == 120.0


def test_22_api_timeout_cap_env_override():
    """Test 22: Verify environment variable override is respected."""
    os.environ["DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS"] = "45.0"
    assert get_api_timeout_cap_seconds() == 45.0


def test_23_api_timeout_cap_at_cap_accepted():
    """Test 23: Request with max_solve_time_seconds equal to the cap is accepted."""
    override_auth_user("GOVT")
    os.environ["DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS"] = "30.0"
    payload = make_valid_minimal_payload()
    payload["max_solve_time_seconds"] = 30.0

    resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
    assert resp.status_code == 200


def test_24_api_timeout_cap_above_cap_rejected():
    """Test 24: Request with max_solve_time_seconds above the cap is rejected with HTTP 422 before orchestrator."""
    override_auth_user("GOVT")
    os.environ["DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS"] = "30.0"
    payload = make_valid_minimal_payload()
    payload["max_solve_time_seconds"] = 30.1

    with patch(
        "app.recovery.services.recovery_optimization_service.RecoveryOptimizationOrchestrator.optimize_recovery_portfolio"
    ) as mock_orch:
        resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
        assert resp.status_code == 422
        assert "exceeds server API timeout cap of 30.0 seconds" in resp.text
        assert mock_orch.called is False


def test_25_api_timeout_cap_invalid_config_rejection():
    """Test 25: Non-numeric, non-finite, or negative cap causes controlled internal 500 error."""
    override_auth_user("GOVT")
    payload = make_valid_minimal_payload()

    invalid_configs = ["not_a_number", "-10.0", "nan", "inf", "0.0"]
    for bad_cfg in invalid_configs:
        os.environ["DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS"] = bad_cfg
        resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
        assert resp.status_code == 500
        data = resp.json()
        assert data["error_type"] == "INTERNAL_EXECUTION_FAILURE"
        assert "server configuration error" in data["message"].lower()


def test_26_api_timeout_cap_no_silent_clamping():
    """Test 26: Requested solve time is passed directly to engine request without silent clamping."""
    override_auth_user("GOVT")
    os.environ["DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS"] = "90.0"
    payload = make_valid_minimal_payload()
    payload["max_solve_time_seconds"] = 45.0  # Under 90.0 cap

    captured_requests = []

    def capture_engine_req(engine_req):
        captured_requests.append(engine_req)
        return RecoveryOptimizationResponse(
            scenario_name=engine_req.scenario_name,
            solver_status="OPTIMAL",
            is_optimal=True,
            exact_objective_value=0,
            exact_best_bound=0,
            conservative_best_bound=0,
            objective_value=0.0,
            best_bound=0.0,
            optimality_gap=0.0,
            solve_time_seconds=0.01,
            selected_project_count=0,
            total_cost_ccu=0,
            total_cost_inr=Decimal("0"),
            scheduled_projects=[],
            periodic_solvency=[],
            district_equity_allocation_ccu={},
            district_equity_allocation_inr={},
            input_fingerprint_sha256="fake_sha256",
            ortools_version="9.15.6755",
            solver_parameters={},
            infeasibility_diagnostics=None,
        )

    with patch(
        "app.recovery.services.recovery_optimization_service.RecoveryOptimizationOrchestrator.optimize_recovery_portfolio",
        side_effect=capture_engine_req,
    ):
        resp = client.post("/api/v1/recovery/optimization/evaluate", json=payload)
        assert resp.status_code == 200
        assert len(captured_requests) == 1
        assert captured_requests[0].max_solve_time_seconds == 45.0
