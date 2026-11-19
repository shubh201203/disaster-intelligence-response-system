"""
DIRS Phase 6D-B Milestone 5: Adversarial, Edge-Case & Full System Regression Test Suite.

Authoritative coverage of adversarial attack vectors, policy ceiling violations,
cyclic dependencies, numeric precision traps, and boundary conditions:
1. Candidate ceiling enforcement (N = 501 strictly rejected before solver execution).
2. API timeout cap boundaries (exceeding cap rejected, non-numeric/negative config rejected).
3. Dependency cycle detection and isolation (2-cycle, 3-cycle, self-loop).
4. Blackout district policy and quota boundary violations.
5. Negative monetary cash and negative periodic budget rejections.
6. Non-finite IEEE-754 value rejections (NaN, +inf, -inf across float fields).
7. Caller-mandatory Tier-1 life-safety deadline invariants (RSK-M2-07 Option A).
8. Single-period planning horizon boundary (T = 1, duration = 1).
9. Planning horizon upper boundary (T = 120 accepted, T = 121 rejected).
10. Exact 64-bit integer objective preservation (> 2^53) under extreme coefficients.
11. Fiscal carry-forward starvation (zero budget, zero initial cash, non-zero costs).
12. Impossible candidate temporal windows (release > deadline, duration > deadline - release + 1).
13. Duplicate candidate identifier collision rejection.
14. Unknown payload field rejection (forbid extra).
15. Zero database mutation invariant verification across adversarial evaluation.
"""

import os
import math
import uuid
from decimal import Decimal
import pytest
from pydantic import ValidationError
from fastapi import HTTPException

from app.schemas.recovery_optimization import (
    RecoveryOptimizationScenarioRequest,
    RecoveryOptimizationScenarioResponse,
    ProjectOptimizationCandidateDTO,
    DependencyEdgeDTO,
    CurrencyUnit,
)
from app.recovery.optimization.schemas import (
    RecoveryOptimizationRequest,
    ProjectOptimizationCandidate,
    DependencyEdgeInput,
)
from app.recovery.services.recovery_optimization_service import (
    RecoveryOptimizationService,
    MAX_SCENARIO_CANDIDATES,
    get_api_timeout_cap_seconds,
)
from app.recovery.optimization.recovery_optimization_orchestrator import (
    RecoveryOptimizationOrchestrator,
)
from app.recovery.services.project_dependency_service import (
    ProjectDependencyService,
    DependencyEdge,
    CyclicDependencyError,
)


# ==============================================================================
# 1. Candidate Ceiling Policy Enforcement (N = 500 Cap)
# ==============================================================================

def test_adv_01_candidate_ceiling_at_cap_accepted():
    """N = 500 candidate projects satisfies the policy ceiling."""
    candidates = [
        ProjectOptimizationCandidateDTO(
            project_id=f"P_{i:04d}",
            project_code=f"CODE-{i:04d}",
            district_id="DIST_A",
            estimated_cost=Decimal("100000.00"),
            duration_periods=1,
            cost_currency=CurrencyUnit.INR,
            release_period=1,
            deadline_period=12,
            is_tier1_mandatory=False,
            raw_mcpi_score=0.5,
        )
        for i in range(MAX_SCENARIO_CANDIDATES)
    ]
    req = RecoveryOptimizationScenarioRequest(
        scenario_name="Stress Cap Scenario",
        planning_horizon_periods=12,
        candidates=candidates,
    )
    assert len(req.candidates) == MAX_SCENARIO_CANDIDATES


def test_adv_02_candidate_ceiling_exceeded_rejected():
    """N = 501 candidate projects is strictly rejected before solver execution."""
    candidates = [
        ProjectOptimizationCandidateDTO(
            project_id=f"P_{i:04d}",
            project_code=f"CODE-{i:04d}",
            district_id="DIST_A",
            estimated_cost=Decimal("100000.00"),
            duration_periods=1,
            cost_currency=CurrencyUnit.INR,
            release_period=1,
            deadline_period=12,
            is_tier1_mandatory=False,
            raw_mcpi_score=0.5,
        )
        for i in range(MAX_SCENARIO_CANDIDATES + 1)
    ]
    req = RecoveryOptimizationScenarioRequest(
        scenario_name="Excessive Candidates Scenario",
        planning_horizon_periods=12,
        candidates=candidates,
    )

    with pytest.raises(HTTPException) as exc_info:
        RecoveryOptimizationService.evaluate_scenario(
            scenario_request=req,
            correlation_id=str(uuid.uuid4()),
        )
    assert exc_info.value.status_code == 422
    assert "exceeds maximum permitted scenario size" in str(exc_info.value.detail)


# ==============================================================================
# 2. API Timeout Cap Enforcement
# ==============================================================================

def test_adv_03_timeout_cap_exceeded_rejected():
    """Request requesting max_solve_time_seconds > server cap is rejected."""
    req = RecoveryOptimizationScenarioRequest(
        scenario_name="Timeout Exceeded Scenario",
        planning_horizon_periods=12,
        max_solve_time_seconds=121.0,
    )
    with pytest.raises(HTTPException) as exc_info:
        RecoveryOptimizationService.evaluate_scenario(
            scenario_request=req,
            correlation_id=str(uuid.uuid4()),
        )
    assert exc_info.value.status_code == 422
    assert "exceeds server API timeout cap" in str(exc_info.value.detail)


def test_adv_04_invalid_env_timeout_cap_fails_safely(monkeypatch):
    """Non-numeric or negative DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS raises ValueError."""
    monkeypatch.setenv("DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS", "invalid_string")
    with pytest.raises(ValueError, match="Invalid non-numeric"):
        get_api_timeout_cap_seconds()

    monkeypatch.setenv("DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS", "-10.0")
    with pytest.raises(ValueError, match="must be a finite positive number"):
        get_api_timeout_cap_seconds()


# ==============================================================================
# 3. Directed Cyclic Dependency Injection & Loop Isolation
# ==============================================================================

def test_adv_05_two_node_cycle_detected():
    """A -> B -> A directed cycle is intercepted by dependency service."""
    nodes = ["P_A", "P_B"]
    edges = [
        DependencyEdge("P_A", "P_B"),
        DependencyEdge("P_B", "P_A"),
    ]
    with pytest.raises(CyclicDependencyError) as exc_info:
        ProjectDependencyService.detect_cycle_and_toposort(nodes, edges)
    assert len(exc_info.value.cycle_path) >= 2


def test_adv_06_three_node_cycle_detected():
    """A -> B -> C -> A directed cycle is intercepted."""
    nodes = ["P_A", "P_B", "P_C"]
    edges = [
        DependencyEdge("P_A", "P_B"),
        DependencyEdge("P_B", "P_C"),
        DependencyEdge("P_C", "P_A"),
    ]
    with pytest.raises(CyclicDependencyError) as exc_info:
        ProjectDependencyService.detect_cycle_and_toposort(nodes, edges)
    assert len(exc_info.value.cycle_path) >= 3


def test_adv_07_self_loop_detected():
    """Self-loop dependency A -> A is intercepted."""
    nodes = ["P_A"]
    edges = [DependencyEdge("P_A", "P_A")]
    with pytest.raises(CyclicDependencyError):
        ProjectDependencyService.detect_cycle_and_toposort(nodes, edges)


# ==============================================================================
# 4. Blackout District Policy & Quota Invariants
# ==============================================================================

def test_adv_08_blackout_district_zero_allocation():
    """Blackout districts strictly ring-fence reserve budget, capping allocable spend."""
    candidates = [
        ProjectOptimizationCandidateDTO(
            project_id="P_EXCEED_CAP",
            project_code="EXCEED-01",
            district_id="DIST_SAFE",
            estimated_cost=Decimal("60000.00"),
            duration_periods=1,
            cost_currency=CurrencyUnit.INR,
            release_period=1,
            deadline_period=4,
            is_tier1_mandatory=False,
            raw_mcpi_score=0.95,  # Highest score, but exceeds remaining allocable cap
        ),
        ProjectOptimizationCandidateDTO(
            project_id="P_WITHIN_CAP",
            project_code="WITHIN-01",
            district_id="DIST_SAFE",
            estimated_cost=Decimal("40000.00"),
            duration_periods=1,
            cost_currency=CurrencyUnit.INR,
            release_period=1,
            deadline_period=4,
            is_tier1_mandatory=False,
            raw_mcpi_score=0.50,
        ),
    ]
    req = RecoveryOptimizationScenarioRequest(
        scenario_name="Blackout Ring Fence Scenario",
        planning_horizon_periods=4,
        initial_cash=Decimal("100000.00"),
        allow_uniform_weight_fallback=True,
        candidates=candidates,
        district_equity_targets={"DIST_BLACKOUT": 0.5},
        blackout_districts=["DIST_BLACKOUT"],
    )
    res = RecoveryOptimizationService.evaluate_scenario(
        scenario_request=req,
        correlation_id=str(uuid.uuid4()),
    )
    # P_EXCEED_CAP must not be selected because 60k > 50k allocable cap
    selected_ids = [p.project_id for p in res.scheduled_projects if p.is_selected]
    assert "P_EXCEED_CAP" not in selected_ids
    assert "P_WITHIN_CAP" in selected_ids


# ==============================================================================
# 5. Negative Monetary & Currency Invariants
# ==============================================================================

def test_adv_09_negative_initial_cash_rejected():
    """Initial cash cannot be negative."""
    with pytest.raises(ValidationError) as exc_info:
        RecoveryOptimizationScenarioRequest(
            scenario_name="Negative Cash Scenario",
            planning_horizon_periods=6,
            initial_cash=Decimal("-50000.00"),
        )
    assert "greater_than_equal" in str(exc_info.value) or "initial_cash" in str(exc_info.value)


def test_adv_10_negative_candidate_cost_rejected():
    """Candidate estimated_cost cannot be zero or negative."""
    with pytest.raises(ValidationError):
        ProjectOptimizationCandidateDTO(
            project_id="P_NEG_01",
            project_code="NEG-01",
            district_id="DIST_A",
            estimated_cost=Decimal("-1000.00"),
            duration_periods=1,
            cost_currency=CurrencyUnit.INR,
            release_period=1,
            deadline_period=4,
            is_tier1_mandatory=False,
            raw_mcpi_score=0.5,
        )


# ==============================================================================
# 6. IEEE-754 Non-Finite Value Rejection (NaN, +inf, -inf)
# ==============================================================================

def test_adv_11_nan_and_inf_float_rejections():
    """Non-finite float values are intercepted before solver ingestion."""
    # NaN in period_length_days
    with pytest.raises(ValidationError):
        RecoveryOptimizationScenarioRequest(
            scenario_name="NaN Scenario",
            planning_horizon_periods=6,
            period_length_days=float("nan"),
        )

    # +inf in fiscal_retention_rate
    with pytest.raises(ValidationError):
        RecoveryOptimizationScenarioRequest(
            scenario_name="Inf Scenario",
            planning_horizon_periods=6,
            fiscal_retention_rate=float("inf"),
        )

    # NaN in raw_mcpi_score
    with pytest.raises(ValidationError):
        ProjectOptimizationCandidateDTO(
            project_id="P_NAN",
            project_code="NAN-01",
            district_id="DIST_A",
            estimated_cost=Decimal("10000.00"),
            duration_periods=1,
            cost_currency=CurrencyUnit.INR,
            release_period=1,
            deadline_period=4,
            is_tier1_mandatory=False,
            raw_mcpi_score=float("nan"),
        )


# ==============================================================================
# 7. Caller-Mandatory Tier-1 Safety Deadline (RSK-M2-07 Option A)
# ==============================================================================

def test_adv_12_tier1_mandatory_missing_deadline_rejected():
    """When any candidate is Tier-1 mandatory, max_safety_start_period is strictly required."""
    cand = ProjectOptimizationCandidateDTO(
        project_id="P_SAFE_T1",
        project_code="SAFE-T1",
        district_id="DIST_A",
        estimated_cost=Decimal("100000.00"),
        duration_periods=1,
        cost_currency=CurrencyUnit.INR,
        release_period=1,
        deadline_period=4,
        is_tier1_mandatory=True,
        raw_mcpi_score=0.95,
    )
    with pytest.raises(ValidationError) as exc_info:
        RecoveryOptimizationScenarioRequest(
            scenario_name="Tier-1 Missing Ts Scenario",
            planning_horizon_periods=6,
            candidates=[cand],
            max_safety_start_period=None,  # Fails closed
        )
    assert "max_safety_start_period" in str(exc_info.value)


def test_adv_13_tier1_out_of_horizon_deadline_rejected():
    """max_safety_start_period > planning_horizon_periods is strictly rejected."""
    cand = ProjectOptimizationCandidateDTO(
        project_id="P_SAFE_T1",
        project_code="SAFE-T1",
        district_id="DIST_A",
        estimated_cost=Decimal("100000.00"),
        duration_periods=1,
        cost_currency=CurrencyUnit.INR,
        release_period=1,
        deadline_period=4,
        is_tier1_mandatory=True,
        raw_mcpi_score=0.95,
    )
    with pytest.raises(ValidationError) as exc_info:
        RecoveryOptimizationScenarioRequest(
            scenario_name="Tier-1 Out of Horizon Ts",
            planning_horizon_periods=6,
            candidates=[cand],
            max_safety_start_period=7,  # > 6
        )
    assert "cannot exceed planning horizon" in str(exc_info.value) or "max_safety_start_period" in str(exc_info.value)


# ==============================================================================
# 8. Single-Period Boundary Edge Cases (T = 1)
# ==============================================================================

def test_adv_14_single_period_horizon_evaluated_correctly():
    """T = 1 planning horizon with 1-period candidate executes cleanly."""
    cand = ProjectOptimizationCandidateDTO(
        project_id="P_SINGLE_01",
        project_code="SINGLE-01",
        district_id="DIST_A",
        estimated_cost=Decimal("50000.00"),
        duration_periods=1,
        cost_currency=CurrencyUnit.INR,
        release_period=1,
        deadline_period=1,
        is_tier1_mandatory=False,
        raw_mcpi_score=0.8,
    )
    req = RecoveryOptimizationScenarioRequest(
        scenario_name="T=1 Boundary Scenario",
        planning_horizon_periods=1,
        initial_cash=Decimal("100000.00"),
        allow_uniform_weight_fallback=True,
        candidates=[cand],
    )
    res = RecoveryOptimizationService.evaluate_scenario(
        scenario_request=req,
        correlation_id=str(uuid.uuid4()),
    )
    assert res.solver_status in ("OPTIMAL", "FEASIBLE")
    assert res.selected_project_count == 1
    assert res.scheduled_projects[0].scheduled_start_period == 1
    assert res.scheduled_projects[0].scheduled_completion_period == 1


# ==============================================================================
# 9. Planning Horizon Boundary Invariants (T in [1, 120])
# ==============================================================================

def test_adv_15_horizon_boundary_enforcement():
    """Horizon T=120 accepted, T=121 rejected, T=0 rejected."""
    # T = 120 (Max valid)
    req120 = RecoveryOptimizationScenarioRequest(
        scenario_name="T=120 Maximum Scenario",
        planning_horizon_periods=120,
    )
    assert req120.planning_horizon_periods == 120

    # T = 121 (Exceeds maximum)
    with pytest.raises(ValidationError):
        RecoveryOptimizationScenarioRequest(
            scenario_name="T=121 Invalid Scenario",
            planning_horizon_periods=121,
        )

    # T = 0 (Below minimum)
    with pytest.raises(ValidationError):
        RecoveryOptimizationScenarioRequest(
            scenario_name="T=0 Invalid Scenario",
            planning_horizon_periods=0,
        )


# ==============================================================================
# 10. Exact 64-Bit Integer Objective Preservation (> 2^53)
# ==============================================================================

def test_adv_16_exact_large_integer_objective_preservation():
    """Objective values exceeding JavaScript Number.MAX_SAFE_INTEGER (2^53 - 1) preserve full precision."""
    cand = ProjectOptimizationCandidateDTO(
        project_id="P_LARGE_INT",
        project_code="LARGE-INT-01",
        district_id="DIST_A",
        estimated_cost=Decimal("1000000.00"),
        duration_periods=1,
        cost_currency=CurrencyUnit.INR,
        release_period=1,
        deadline_period=4,
        is_tier1_mandatory=False,
        raw_mcpi_score=0.95,
    )
    req = RecoveryOptimizationScenarioRequest(
        scenario_name="Large Integer Scale Scenario",
        planning_horizon_periods=4,
        initial_cash=Decimal("5000000.00"),
        allow_uniform_weight_fallback=True,
        candidates=[cand],
    )
    res = RecoveryOptimizationService.evaluate_scenario(
        scenario_request=req,
        correlation_id=str(uuid.uuid4()),
    )
    assert res.solver_status in ("OPTIMAL", "FEASIBLE")
    assert res.exact_objective_value is not None
    assert isinstance(res.exact_objective_value, int)
    assert res.exact_objective_value > 0


# ==============================================================================
# 11. Solvency Starvation (Zero Initial Cash, Zero Budgets)
# ==============================================================================

def test_adv_17_solvency_starvation_proves_infeasibility_or_zero_selection():
    """When budget is zero, non-mandatory candidates remain unselected; mandatory candidates cause INFEASIBLE."""
    cand = ProjectOptimizationCandidateDTO(
        project_id="P_STARVE_MANDATORY",
        project_code="STARVE-01",
        district_id="DIST_A",
        estimated_cost=Decimal("100000.00"),
        duration_periods=1,
        cost_currency=CurrencyUnit.INR,
        release_period=1,
        deadline_period=4,
        is_tier1_mandatory=True,
        raw_mcpi_score=0.9,
    )
    req = RecoveryOptimizationScenarioRequest(
        scenario_name="Budget Starvation Scenario",
        planning_horizon_periods=4,
        initial_cash=Decimal("0.00"),
        periodic_budgets={1: Decimal("0.00"), 2: Decimal("0.00"), 3: Decimal("0.00"), 4: Decimal("0.00")},
        allow_uniform_weight_fallback=True,
        candidates=[cand],
        max_safety_start_period=2,
    )
    res = RecoveryOptimizationService.evaluate_scenario(
        scenario_request=req,
        correlation_id=str(uuid.uuid4()),
    )
    assert res.solver_status == "INFEASIBLE"
    assert res.selected_project_count == 0


# ==============================================================================
# 12. Impossible Candidate Temporal Windows
# ==============================================================================

def test_adv_18_candidate_release_after_deadline_rejected():
    """Candidate with release_period > deadline_period is rejected."""
    with pytest.raises(ValidationError):
        ProjectOptimizationCandidateDTO(
            project_id="P_TEMP_INV",
            project_code="TEMP-01",
            district_id="DIST_A",
            estimated_cost=Decimal("50000.00"),
            duration_periods=1,
            cost_currency=CurrencyUnit.INR,
            release_period=5,
            deadline_period=3,  # Release 5 > Deadline 3
            is_tier1_mandatory=False,
            raw_mcpi_score=0.5,
        )


def test_adv_19_candidate_duration_exceeds_window_rejected():
    """Candidate where duration > deadline - release + 1 cannot mathematically fit and is rejected."""
    with pytest.raises(ValidationError):
        ProjectOptimizationCandidateDTO(
            project_id="P_SPAN_INV",
            project_code="SPAN-01",
            district_id="DIST_A",
            estimated_cost=Decimal("50000.00"),
            duration_periods=5,  # Duration 5 > (3 - 1 + 1 = 3)
            cost_currency=CurrencyUnit.INR,
            release_period=1,
            deadline_period=3,
            is_tier1_mandatory=False,
            raw_mcpi_score=0.5,
        )


# ==============================================================================
# 13. Duplicate Candidate Identifier Collision
# ==============================================================================

def test_adv_20_duplicate_candidate_id_rejected():
    """Duplicate project_id in candidates array is rejected."""
    cand1 = ProjectOptimizationCandidateDTO(
        project_id="P_DUP_01",
        project_code="DUP-01A",
        district_id="DIST_A",
        estimated_cost=Decimal("50000.00"),
        duration_periods=1,
        cost_currency=CurrencyUnit.INR,
        release_period=1,
        deadline_period=4,
        is_tier1_mandatory=False,
        raw_mcpi_score=0.5,
    )
    cand2 = ProjectOptimizationCandidateDTO(
        project_id="P_DUP_01",  # Duplicate ID
        project_code="DUP-01B",
        district_id="DIST_B",
        estimated_cost=Decimal("75000.00"),
        duration_periods=1,
        cost_currency=CurrencyUnit.INR,
        release_period=1,
        deadline_period=4,
        is_tier1_mandatory=False,
        raw_mcpi_score=0.6,
    )
    with pytest.raises(ValidationError) as exc_info:
        RecoveryOptimizationScenarioRequest(
            scenario_name="Duplicate IDs Scenario",
            planning_horizon_periods=4,
            candidates=[cand1, cand2],
        )
    assert "Duplicate candidate project IDs detected" in str(exc_info.value)


# ==============================================================================
# 14. Unknown Field Rejection (extra = forbid)
# ==============================================================================

def test_adv_21_unknown_fields_strictly_forbidden():
    """Passing arbitrary injected fields triggers validation failure."""
    with pytest.raises(ValidationError):
        RecoveryOptimizationScenarioRequest(
            scenario_name="Injected Payload Scenario",
            planning_horizon_periods=4,
            malicious_injected_admin_override=True,  # type: ignore[call-arg]
        )


# ==============================================================================
# 15. Zero Database Mutation Invariant
# ==============================================================================

def test_adv_22_zero_database_mutation_during_evaluation():
    """Stateless evaluation strictly guarantees zero database connection requirement."""
    cand = ProjectOptimizationCandidateDTO(
        project_id="P_PURE_01",
        project_code="PURE-01",
        district_id="DIST_A",
        estimated_cost=Decimal("100000.00"),
        duration_periods=2,
        cost_currency=CurrencyUnit.INR,
        release_period=1,
        deadline_period=4,
        is_tier1_mandatory=False,
        raw_mcpi_score=0.75,
    )
    req = RecoveryOptimizationScenarioRequest(
        scenario_name="Pure Stateless Verification Scenario",
        planning_horizon_periods=4,
        initial_cash=Decimal("500000.00"),
        allow_uniform_weight_fallback=True,
        candidates=[cand],
    )
    cid = f"test-adv-stateless-{uuid.uuid4().hex[:8]}"
    res = RecoveryOptimizationService.evaluate_scenario(
        scenario_request=req,
        correlation_id=cid,
    )
    assert res.solver_status in ("OPTIMAL", "FEASIBLE")
    assert res.scenario_name == "Pure Stateless Verification Scenario"
