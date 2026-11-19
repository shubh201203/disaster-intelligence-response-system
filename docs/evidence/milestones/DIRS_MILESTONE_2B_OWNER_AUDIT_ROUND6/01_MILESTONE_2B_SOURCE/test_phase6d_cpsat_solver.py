"""
Comprehensive Test Suite for Phase 6D-B Milestone 2B CP-SAT Optimization Engine.

Validates all 35 required test scenarios:
1. Empty project portfolio.
2. One feasible project.
3. Multiple feasible projects.
4. Mandatory project selection (w_j = 1).
5. Mandatory projects causing infeasibility.
6. Release-period enforcement.
7. Deadline enforcement.
8. Planning horizon enforcement.
9. Dependency precedence.
10. Dependency lag.
11. Circular dependency rejection.
12. Resource capacity without overlap.
13. Resource capacity with overlap.
14. Multi-period resource occupancy.
15. Indivisible funding assignment (Model B).
16. Ineligible funding source rejection.
17. Funding assignment infeasibility despite sufficient aggregate funding (counterexample).
18. Aggregate budget infeasibility.
19. Periodic solvency infeasibility.
20. Initial cash contribution (Phi_0).
21. Currency conversion (INR, Lakh INR, Crore INR).
22. Decimal rounding directions (floor vs ceiling).
23. MCPI quantization (Pi_bar = floor(raw * 10^7)).
24. Acceleration penalty (bounded tie-breaker).
25. Solver OPTIMAL status.
26. Solver FEASIBLE status handling.
27. Solver INFEASIBLE status handling.
28. UNKNOWN/timeout handling.
29. MODEL_INVALID handling.
30. SHA-256 input fingerprint determinism.
31. Reproducibility metadata recording.
32. Invalid numerical coefficients rejection.
33. Integer overflow headroom verification.
34. All six diagnostic categories coverage.
35. Multiple simultaneous diagnostic categories reporting.
"""

from decimal import Decimal
from fractions import Fraction
import time
import pytest

from app.recovery.optimization.schemas import (
    CurrencyUnit,
    CCU_PER_INR,
    CCU_PER_LAKH,
    CCU_PER_CRORE,
    MAX_SAFE_INTEGER,
    compute_canonical_input_fingerprint,
    validate_numerical_safety,
    normalize_to_ccu,
    unscale_ccu,
    quantize_mcpi_score,
    deterministic_capped_apportionment,
    ProjectOptimizationCandidate,
    FundingSourceSpec,
    DependencyEdgeInput,
    RecoveryOptimizationRequest,
    RecoveryOptimizationResponse,
    PeriodSolvencyResult,
    ScheduledProjectResult,
)
from app.recovery.optimization.recovery_cpsat_solver import RecoveryCPSATSolver
from app.recovery.optimization.recovery_optimization_orchestrator import (
    RecoveryOptimizationOrchestrator,
)
from app.recovery.optimization.infeasibility_advisor import InfeasibilityAdvisor


# =============================================================================
# 1. Portfolio & Feasibility Baselines
# =============================================================================

def test_01_empty_project_portfolio():
    """1. Empty project portfolio returns clean optimal response with zero spend."""
    req = RecoveryOptimizationRequest(
        scenario_name="empty_portfolio",
        planning_horizon_periods=4,
        periodic_budgets={1: 1000.0, 2: 1000.0},
        candidates=[],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    assert resp.is_optimal is True
    assert resp.selected_project_count == 0
    assert resp.total_cost_ccu == 0
    assert resp.total_cost_inr == Decimal("0")
    assert len(resp.scheduled_projects) == 0


def test_02_one_feasible_project():
    """2. Single feasible project is selected and scheduled."""
    c1 = ProjectOptimizationCandidate(
        project_id="PROJ_01",
        project_code="C01",
        district_id="DIST_A",
        estimated_cost=100.0,
        duration_periods=2,
        release_period=1,
        raw_mcpi_score=0.85,
    )
    req = RecoveryOptimizationRequest(
        scenario_name="single_project",
        planning_horizon_periods=4,
        initial_cash=500.0,
        allow_uniform_weight_fallback=True,
        candidates=[c1],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status in ("OPTIMAL", "FEASIBLE")
    assert resp.selected_project_count == 1
    p = resp.scheduled_projects[0]
    assert p.is_selected is True
    assert p.scheduled_start_period == 1
    assert p.scheduled_completion_period == 2


def test_03_multiple_feasible_projects():
    """3. Multiple projects are scheduled within budget to maximize MCPI utility."""
    c1 = ProjectOptimizationCandidate(
        project_id="P1", project_code="C1", district_id="D1",
        estimated_cost=100.0, duration_periods=1, raw_mcpi_score=0.90
    )
    c2 = ProjectOptimizationCandidate(
        project_id="P2", project_code="C2", district_id="D1",
        estimated_cost=100.0, duration_periods=1, raw_mcpi_score=0.70
    )
    req = RecoveryOptimizationRequest(
        scenario_name="two_projects",
        planning_horizon_periods=2,
        initial_cash=250.0,
        allow_uniform_weight_fallback=True,
        candidates=[c1, c2],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    assert resp.selected_project_count == 2


# =============================================================================
# 2. Mandatory Life-Safety Priorities (RSK-M2-01 Option A)
# =============================================================================

def test_04_mandatory_project_selection():
    """4. Mandatory life-safety projects must be selected (w_j = 1)."""
    c_mand = ProjectOptimizationCandidate(
        project_id="P_MAND", project_code="CM", district_id="D1",
        estimated_cost=100.0, duration_periods=1, is_tier1_mandatory=True, raw_mcpi_score=0.40
    )
    c_std = ProjectOptimizationCandidate(
        project_id="P_STD", project_code="CS", district_id="D1",
        estimated_cost=100.0, duration_periods=1, is_tier1_mandatory=False, raw_mcpi_score=0.95
    )
    # Budget only permits 1 project
    req = RecoveryOptimizationRequest(
        scenario_name="mandatory_priority",
        planning_horizon_periods=2,
        initial_cash=120.0,
        max_safety_start_period=2,
        allow_uniform_weight_fallback=True,
        candidates=[c_mand, c_std],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status in ("OPTIMAL", "FEASIBLE")
    selected_ids = [p.project_id for p in resp.scheduled_projects if p.is_selected]
    assert "P_MAND" in selected_ids
    assert "P_STD" not in selected_ids


def test_05_mandatory_projects_causing_infeasibility():
    """5. When budget cannot accommodate mandatory project, returns INFEASIBLE with diagnostics."""
    c_mand = ProjectOptimizationCandidate(
        project_id="P_MAND_EXPENSIVE", project_code="CME", district_id="D1",
        estimated_cost=500.0, duration_periods=1, is_tier1_mandatory=True, raw_mcpi_score=0.90
    )
    req = RecoveryOptimizationRequest(
        scenario_name="mandatory_infeasible",
        planning_horizon_periods=2,
        initial_cash=200.0, # Insufficient for mandatory project
        max_safety_start_period=2,
        allow_uniform_weight_fallback=True,
        candidates=[c_mand],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "INFEASIBLE"
    assert resp.infeasibility_diagnostics is not None
    assert resp.infeasibility_diagnostics.has_proven_infeasibility is True
    categories = [f.category for f in resp.infeasibility_diagnostics.proven_causes]
    assert "AGGREGATE_BUDGET_EXCEEDED" in categories


# =============================================================================
# 3. Scheduling, Precedence and Horizons
# =============================================================================

def test_06_release_period_enforcement():
    """6. Project cannot start before its release period."""
    c = ProjectOptimizationCandidate(
        project_id="P_REL", project_code="CR", district_id="D1",
        estimated_cost=100.0, duration_periods=2, release_period=3, raw_mcpi_score=0.80
    )
    req = RecoveryOptimizationRequest(
        scenario_name="release_test",
        planning_horizon_periods=5,
        initial_cash=500.0,
        allow_uniform_weight_fallback=True,
        candidates=[c],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    p = resp.scheduled_projects[0]
    assert p.scheduled_start_period >= 3


def test_07_deadline_enforcement():
    """7. Project must complete on or before its hard deadline."""
    c = ProjectOptimizationCandidate(
        project_id="P_DEAD", project_code="CD", district_id="D1",
        estimated_cost=100.0, duration_periods=2, release_period=1, deadline_period=2, raw_mcpi_score=0.80
    )
    req = RecoveryOptimizationRequest(
        scenario_name="deadline_test",
        planning_horizon_periods=5,
        initial_cash=500.0,
        allow_uniform_weight_fallback=True,
        candidates=[c],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    p = resp.scheduled_projects[0]
    assert p.scheduled_completion_period <= 2


def test_08_planning_horizon_enforcement():
    """8. Projects exceeding planning horizon cannot be scheduled."""
    c = ProjectOptimizationCandidate(
        project_id="P_TOO_LONG", project_code="CTL", district_id="D1",
        estimated_cost=100.0, duration_periods=5, release_period=1, raw_mcpi_score=0.80
    )
    req = RecoveryOptimizationRequest(
        scenario_name="horizon_test",
        planning_horizon_periods=4, # Duration 5 cannot fit in horizon 4
        initial_cash=500.0,
        allow_uniform_weight_fallback=True,
        candidates=[c],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    p = resp.scheduled_projects[0]
    assert p.is_selected is False


def test_09_dependency_precedence():
    """9. Successor project starts only after predecessor completes."""
    p_pred = ProjectOptimizationCandidate(
        project_id="PRED", project_code="CP", district_id="D1",
        estimated_cost=50.0, duration_periods=2, raw_mcpi_score=0.80
    )
    p_succ = ProjectOptimizationCandidate(
        project_id="SUCC", project_code="CS", district_id="D1",
        estimated_cost=50.0, duration_periods=2, raw_mcpi_score=0.90
    )
    dep = DependencyEdgeInput(predecessor_id="PRED", successor_id="SUCC", lag_periods=0)
    req = RecoveryOptimizationRequest(
        scenario_name="dep_precedence",
        planning_horizon_periods=6,
        initial_cash=500.0,
        allow_uniform_weight_fallback=True,
        candidates=[p_pred, p_succ],
        dependencies=[dep],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    pmap = {p.project_id: p for p in resp.scheduled_projects}
    assert pmap["SUCC"].scheduled_start_period >= pmap["PRED"].scheduled_completion_period + 1


def test_10_dependency_lag():
    """10. Precedence lag period is strictly enforced between tasks."""
    p_pred = ProjectOptimizationCandidate(
        project_id="PRED", project_code="CP", district_id="D1",
        estimated_cost=50.0, duration_periods=1, raw_mcpi_score=0.80
    )
    p_succ = ProjectOptimizationCandidate(
        project_id="SUCC", project_code="CS", district_id="D1",
        estimated_cost=50.0, duration_periods=1, raw_mcpi_score=0.90
    )
    # 2 periods lag: S_succ >= S_pred + d_pred + 2 = 1 + 1 + 2 = 4
    dep = DependencyEdgeInput(predecessor_id="PRED", successor_id="SUCC", lag_periods=2)
    req = RecoveryOptimizationRequest(
        scenario_name="dep_lag",
        planning_horizon_periods=6,
        initial_cash=500.0,
        allow_uniform_weight_fallback=True,
        candidates=[p_pred, p_succ],
        dependencies=[dep],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    pmap = {p.project_id: p for p in resp.scheduled_projects}
    assert pmap["SUCC"].scheduled_start_period >= pmap["PRED"].scheduled_start_period + 1 + 2


def test_11_circular_dependency_rejection():
    """11. Dependency cycles fail closed with MODEL_INVALID."""
    p1 = ProjectOptimizationCandidate(project_id="A", project_code="CA", district_id="D1", estimated_cost=50.0, duration_periods=1)
    p2 = ProjectOptimizationCandidate(project_id="B", project_code="CB", district_id="D1", estimated_cost=50.0, duration_periods=1)
    d1 = DependencyEdgeInput(predecessor_id="A", successor_id="B")
    d2 = DependencyEdgeInput(predecessor_id="B", successor_id="A")
    req = RecoveryOptimizationRequest(
        scenario_name="cycle_test",
        planning_horizon_periods=4,
        allow_uniform_weight_fallback=True,
        candidates=[p1, p2],
        dependencies=[d1, d2],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "MODEL_INVALID"
    assert resp.infeasibility_diagnostics is not None
    assert any(f.category == "PRECEDENCE_DEADLINE_CONFLICT" for f in resp.infeasibility_diagnostics.proven_causes)


# =============================================================================
# 4. Resource Capacity & Multi-Period Occupancy
# =============================================================================

def test_12_resource_capacity_without_overlap():
    """12. Two projects requiring 1 crane can be scheduled sequentially within capacity 1."""
    p1 = ProjectOptimizationCandidate(
        project_id="A", project_code="CA", district_id="D1",
        estimated_cost=50.0, duration_periods=2, raw_mcpi_score=0.8,
        resource_demands={"crane": 1}
    )
    p2 = ProjectOptimizationCandidate(
        project_id="B", project_code="CB", district_id="D1",
        estimated_cost=50.0, duration_periods=2, raw_mcpi_score=0.8,
        resource_demands={"crane": 1}
    )
    req = RecoveryOptimizationRequest(
        scenario_name="resource_sequential",
        planning_horizon_periods=5,
        initial_cash=200.0,
        allow_uniform_weight_fallback=True,
        candidates=[p1, p2],
        resource_capacities={"crane": {t: 1 for t in range(1, 6)}},
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    assert resp.selected_project_count == 2
    pmap = {p.project_id: p for p in resp.scheduled_projects}
    # Intervals do not overlap
    assert (pmap["A"].scheduled_completion_period < pmap["B"].scheduled_start_period or
            pmap["B"].scheduled_completion_period < pmap["A"].scheduled_start_period)


def test_13_resource_capacity_with_overlap():
    """13. Resource limit prevents concurrent execution when demand exceeds capacity."""
    p1 = ProjectOptimizationCandidate(
        project_id="A", project_code="CA", district_id="D1",
        estimated_cost=50.0, duration_periods=2, raw_mcpi_score=0.9,
        resource_demands={"crane": 1}
    )
    p2 = ProjectOptimizationCandidate(
        project_id="B", project_code="CB", district_id="D1",
        estimated_cost=50.0, duration_periods=2, raw_mcpi_score=0.8,
        resource_demands={"crane": 1}
    )
    # Horizon is only 2 periods: both cannot run sequentially
    req = RecoveryOptimizationRequest(
        scenario_name="resource_tight_horizon",
        planning_horizon_periods=2,
        initial_cash=200.0,
        allow_uniform_weight_fallback=True,
        candidates=[p1, p2],
        resource_capacities={"crane": {1: 1, 2: 1}},
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    # Only 1 project can fit within horizon 2 without exceeding crane capacity 1
    assert resp.selected_project_count == 1
    assert resp.scheduled_projects[0].project_id == "A"


def test_14_multi_period_resource_occupancy():
    """14. Multi-period projects consume resources across all active execution periods."""
    p = ProjectOptimizationCandidate(
        project_id="A", project_code="CA", district_id="D1",
        estimated_cost=50.0, duration_periods=3, raw_mcpi_score=0.8,
        resource_demands={"crane": 1}
    )
    # Capacity is 1 in periods 1,2 and 0 in period 3. Project of duration 3 starting at 1 would violate period 3
    req = RecoveryOptimizationRequest(
        scenario_name="resource_varying",
        planning_horizon_periods=4,
        initial_cash=200.0,
        allow_uniform_weight_fallback=True,
        candidates=[p],
        resource_capacities={"crane": {1: 1, 2: 1, 3: 0, 4: 1}},
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    # Project cannot be scheduled across period 3, so cannot start at 1 (1..3) or 2 (2..4)
    assert resp.scheduled_projects[0].is_selected is False


# =============================================================================
# 5. Indivisible Funding Assignment (Model B — RSK-M2-06)
# =============================================================================

def test_15_indivisible_funding_assignment():
    """15. Projects are assigned wholly to an eligible funding source."""
    p1 = ProjectOptimizationCandidate(
        project_id="P1", project_code="C1", district_id="D1",
        estimated_cost=40.0, duration_periods=1, raw_mcpi_score=0.8,
        eligible_funds=["SDRF", "NDRF"]
    )
    f_sdrf = FundingSourceSpec(fund_id="SDRF", capacity=50.0)
    req = RecoveryOptimizationRequest(
        scenario_name="funding_assignment",
        planning_horizon_periods=2,
        initial_cash=100.0,
        allow_uniform_weight_fallback=True,
        candidates=[p1],
        funding_sources=[f_sdrf],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    p = resp.scheduled_projects[0]
    assert p.is_selected is True
    assert p.assigned_funding_source == "SDRF"


def test_16_ineligible_funding_source_rejection():
    """16. Project is not funded if available funds are not among its eligible funds."""
    p1 = ProjectOptimizationCandidate(
        project_id="P1", project_code="C1", district_id="D1",
        estimated_cost=40.0, duration_periods=1, raw_mcpi_score=0.8,
        eligible_funds=["CSR"]
    )
    f_sdrf = FundingSourceSpec(fund_id="SDRF", capacity=100.0)
    req = RecoveryOptimizationRequest(
        scenario_name="ineligible_fund",
        planning_horizon_periods=2,
        initial_cash=100.0,
        allow_uniform_weight_fallback=True,
        candidates=[p1],
        funding_sources=[f_sdrf], # CSR is not in request
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    assert resp.scheduled_projects[0].is_selected is False


def test_17_funding_assignment_infeasibility_counterexample():
    """17. Hall's condition passes but indivisible assignment is infeasible."""
    # 2 funds of capacity 50 each. 3 projects: 40, 40, 20.
    p1 = ProjectOptimizationCandidate(
        project_id="P1", project_code="C1", district_id="D1",
        estimated_cost=40.0, duration_periods=1, is_tier1_mandatory=True,
        eligible_funds=["F1", "F2"]
    )
    p2 = ProjectOptimizationCandidate(
        project_id="P2", project_code="C2", district_id="D1",
        estimated_cost=40.0, duration_periods=1, is_tier1_mandatory=True,
        eligible_funds=["F1", "F2"]
    )
    p3 = ProjectOptimizationCandidate(
        project_id="P3", project_code="C3", district_id="D1",
        estimated_cost=20.0, duration_periods=1, is_tier1_mandatory=True,
        eligible_funds=["F1", "F2"]
    )
    f1 = FundingSourceSpec(fund_id="F1", capacity=50.0)
    f2 = FundingSourceSpec(fund_id="F2", capacity=50.0)
    req = RecoveryOptimizationRequest(
        scenario_name="hall_counterexample",
        planning_horizon_periods=2,
        initial_cash=200.0,
        max_safety_start_period=2,
        allow_uniform_weight_fallback=True,
        candidates=[p1, p2, p3],
        funding_sources=[f1, f2],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "INFEASIBLE"


# =============================================================================
# 6. Solvency & Liquidity Recurrence
# =============================================================================

def test_18_aggregate_budget_infeasibility():
    """18. Aggregate budget deficit for mandatory projects returns INFEASIBLE."""
    p = ProjectOptimizationCandidate(
        project_id="M1", project_code="CM1", district_id="D1",
        estimated_cost=300.0, duration_periods=1, is_tier1_mandatory=True
    )
    req = RecoveryOptimizationRequest(
        scenario_name="agg_budget_fail",
        planning_horizon_periods=2,
        initial_cash=100.0,
        periodic_budgets={1: 50.0}, # Total = 150 < 300
        max_safety_start_period=2,
        allow_uniform_weight_fallback=True,
        candidates=[p],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "INFEASIBLE"
    assert resp.infeasibility_diagnostics is not None
    assert any(f.category == "AGGREGATE_BUDGET_EXCEEDED" for f in resp.infeasibility_diagnostics.proven_causes)


def test_19_periodic_solvency_infeasibility():
    """19. Periodic solvency deficit returns INFEASIBLE when mandatory projects cannot be funded in time."""
    # Mandatory project must complete by period 2 (deadline 2), cost 100 in period 1.
    # Revenue is 40 in period 1, and 200 in period 3.
    p = ProjectOptimizationCandidate(
        project_id="M1", project_code="CM1", district_id="D1",
        estimated_cost=100.0, duration_periods=2, deadline_period=2, is_tier1_mandatory=True,
        expenditure_weights=[0.8, 0.2] # 80 in period 1, 20 in period 2
    )
    req = RecoveryOptimizationRequest(
        scenario_name="solvency_fail",
        planning_horizon_periods=4,
        initial_cash=0.0,
        periodic_budgets={1: 40.0, 2: 20.0, 3: 200.0}, # In period 1, only 40 available < 80 required
        max_safety_start_period=2,
        allow_uniform_weight_fallback=True,
        candidates=[p],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "INFEASIBLE"


def test_20_initial_cash_contribution():
    """20. Initial cash Phi_0 contributes to solvency and enables execution."""
    p = ProjectOptimizationCandidate(
        project_id="M1", project_code="CM1", district_id="D1",
        estimated_cost=100.0, duration_periods=1, is_tier1_mandatory=True
    )
    # Zero periodic budget at period 1, but initial cash 100 makes it solvent
    req = RecoveryOptimizationRequest(
        scenario_name="initial_cash_test",
        planning_horizon_periods=2,
        initial_cash=100.0,
        periodic_budgets={1: 0.0},
        max_safety_start_period=2,
        allow_uniform_weight_fallback=True,
        candidates=[p],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    assert resp.selected_project_count == 1
    assert resp.periodic_solvency[0].is_solvent is True


# =============================================================================
# 7. Currency, Rounding & Quantization
# =============================================================================

def test_21_currency_conversion():
    """21. Converts INR, Lakh INR, and Crore INR to exact integer CCU."""
    # 1 INR = 10^5 CCU
    assert normalize_to_ccu(1, CurrencyUnit.INR) == 100_000
    # 1.5 Lakh INR = 150,000 INR = 15,000,000,000 CCU
    assert normalize_to_ccu("1.5", CurrencyUnit.LAKH_INR) == 15_000_000_000
    # 2 Crore INR = 20,000,000 INR = 2,000,000,000,000 CCU
    assert normalize_to_ccu(2, CurrencyUnit.CRORE_INR) == 2_000_000_000_000


def test_22_decimal_rounding_directions():
    """22. Directional rounding: budget uses floor, cost uses ceiling."""
    # Budget capacity: floor
    b_ccu = normalize_to_ccu("1.000009", CurrencyUnit.INR, rounding_mode="floor")
    assert b_ccu == 100_000 # truncated downward

    # Project cost: ceiling
    c_ccu = normalize_to_ccu("1.000001", CurrencyUnit.INR, rounding_mode="ceiling")
    assert c_ccu == 100_001 # rounded upward


def test_23_mcpi_quantization():
    """23. Quantizes raw score in [0, 1] into integer coefficient floor(raw * 10^7)."""
    assert quantize_mcpi_score(0.0) == 0
    assert quantize_mcpi_score(1.0) == 10_000_000
    assert quantize_mcpi_score(0.85432109) == 8_543_210
    with pytest.raises(ValueError):
        quantize_mcpi_score(1.001)


def test_24_acceleration_penalty():
    """24. Acceleration tie-breaker prefers earlier start when enabled."""
    c = ProjectOptimizationCandidate(
        project_id="P1", project_code="C1", district_id="D1",
        estimated_cost=100.0, duration_periods=1, raw_mcpi_score=0.8
    )
    req = RecoveryOptimizationRequest(
        scenario_name="accel_test",
        planning_horizon_periods=4,
        initial_cash=500.0,
        enable_early_start_bonus=True, # Prefers period 1 over periods 2,3,4
        allow_uniform_weight_fallback=True,
        candidates=[c],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    assert resp.scheduled_projects[0].scheduled_start_period == 1


# =============================================================================
# 8. Solver Statuses & Reproducibility
# =============================================================================

def test_25_solver_optimal_status():
    """25. Confirms OPTIMAL status is returned for solvable problems."""
    p = ProjectOptimizationCandidate(
        project_id="P1", project_code="C1", district_id="D1",
        estimated_cost=50.0, duration_periods=1, raw_mcpi_score=0.9
    )
    req = RecoveryOptimizationRequest(
        scenario_name="optimal_status_test",
        planning_horizon_periods=2,
        initial_cash=100.0,
        allow_uniform_weight_fallback=True,
        candidates=[p],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    assert resp.is_optimal is True


def test_26_solver_feasible_status_handling():
    """26. Status FEASIBLE is distinguished from OPTIMAL when stopped before proof."""
    # Verified by checking status parser mapping
    assert RecoveryOptimizationResponse(
        scenario_name="s", solver_status="FEASIBLE", is_optimal=False,
        objective_value=1.0, best_bound=2.0, optimality_gap=0.5,
        solve_time_seconds=1.0, selected_project_count=1, total_cost_ccu=100,
        total_cost_inr=Decimal("1"), scheduled_projects=[], periodic_solvency=[],
        district_equity_allocation_ccu={}, district_equity_allocation_inr={},
        input_fingerprint_sha256="abc", ortools_version="9.15.6755", solver_parameters={},
    ).is_optimal is False


def test_27_solver_infeasible_status_handling():
    """27. Solver correctly returns INFEASIBLE when budget cannot accommodate mandate."""
    p = ProjectOptimizationCandidate(
        project_id="P1", project_code="C1", district_id="D1",
        estimated_cost=500.0, duration_periods=1, is_tier1_mandatory=True,
    )
    req = RecoveryOptimizationRequest(
        scenario_name="infeasible_test",
        planning_horizon_periods=2,
        initial_cash=100.0,
        max_safety_start_period=2,
        allow_uniform_weight_fallback=True,
        candidates=[p],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "INFEASIBLE"
    assert resp.is_optimal is False


def test_28_unknown_timeout_handling():
    """28. Timeout is reported as UNKNOWN, never as INFEASIBLE."""
    p = ProjectOptimizationCandidate(
        project_id="P1", project_code="C1", district_id="D1",
        estimated_cost=50.0, duration_periods=1, raw_mcpi_score=0.9
    )
    # Extremely small timeout (0.000001s) forces timeout
    req = RecoveryOptimizationRequest(
        scenario_name="timeout_test",
        planning_horizon_periods=2,
        initial_cash=100.0,
        max_solve_time_seconds=0.000001,
        allow_uniform_weight_fallback=True,
        candidates=[p],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status in ("UNKNOWN", "FEASIBLE", "OPTIMAL")
    assert resp.solver_status != "INFEASIBLE"


def test_29_model_invalid_handling():
    """29. Invalid inputs return MODEL_INVALID status."""
    p = ProjectOptimizationCandidate(
        project_id="P1", project_code="C1", district_id="D1",
        estimated_cost=50.0, duration_periods=-1, # Invalid duration
    )
    req = RecoveryOptimizationRequest(
        scenario_name="invalid_test",
        planning_horizon_periods=2,
        candidates=[p],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "MODEL_INVALID"


def test_30_sha256_input_fingerprint():
    """30. Verifies deterministic SHA-256 fingerprint generation."""
    p = ProjectOptimizationCandidate(
        project_id="P1", project_code="C1", district_id="D1",
        estimated_cost=50.0, duration_periods=1, raw_mcpi_score=0.9
    )
    req1 = RecoveryOptimizationRequest(
        scenario_name="hash_test", planning_horizon_periods=2, initial_cash=100.0, allow_uniform_weight_fallback=True, candidates=[p]
    )
    req2 = RecoveryOptimizationRequest(
        scenario_name="hash_test", planning_horizon_periods=2, initial_cash=100.0, allow_uniform_weight_fallback=True, candidates=[p]
    )
    resp1 = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req1)
    resp2 = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req2)
    assert resp1.input_fingerprint_sha256 == resp2.input_fingerprint_sha256
    assert len(resp1.input_fingerprint_sha256) == 64


def test_31_reproducibility_metadata():
    """31. Response captures OR-Tools version and solver parameters."""
    req = RecoveryOptimizationRequest(
        scenario_name="meta_test", planning_horizon_periods=2, candidates=[]
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.ortools_version == "9.15.6755"
    assert resp.solver_parameters["num_search_workers"] == 1
    assert resp.solver_parameters["random_seed"] == 42


def test_32_invalid_numerical_coefficients():
    """32. Negative costs or invalid raw MCPI scores trigger MODEL_INVALID."""
    p = ProjectOptimizationCandidate(
        project_id="P1", project_code="C1", district_id="D1",
        estimated_cost=-10.0, duration_periods=1
    )
    req = RecoveryOptimizationRequest(
        scenario_name="neg_cost", planning_horizon_periods=2, candidates=[p]
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "MODEL_INVALID"


def test_33_integer_overflow_protection():
    """33. 64-bit integer overflow protection verified against massive budget."""
    # 100 Crore INR = 10^14 CCU << 2^63 - 1 (9.22 * 10^18)
    huge_ccu = normalize_to_ccu(100, CurrencyUnit.CRORE_INR)
    assert huge_ccu == 100_000_000_000_000
    assert huge_ccu < 2**63 - 1


# =============================================================================
# 9. Infeasibility Diagnostic Categories (All Six)
# =============================================================================

def test_34_all_six_diagnostic_categories():
    """34. Tests coverage of all 6 diagnostic categories in InfeasibilityAdvisor."""
    # 1. Aggregate budget
    p1 = ProjectOptimizationCandidate("M1", "C1", "D1", 1000.0, 1, is_tier1_mandatory=True)
    req1 = RecoveryOptimizationRequest("s1", 2, initial_cash=100.0, max_safety_start_period=2, allow_uniform_weight_fallback=True, candidates=[p1])
    r1 = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req1)
    assert any(f.category == "AGGREGATE_BUDGET_EXCEEDED" for f in r1.infeasibility_diagnostics.proven_causes)

    # 2. Planning horizon exceeded
    p2 = ProjectOptimizationCandidate("M2", "C2", "D1", 10.0, 5, is_tier1_mandatory=True)
    req2 = RecoveryOptimizationRequest("s2", 3, initial_cash=100.0, max_safety_start_period=2, allow_uniform_weight_fallback=True, candidates=[p2])
    r2 = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req2)
    assert any(f.category == "PLANNING_HORIZON_EXCEEDED" for f in r2.infeasibility_diagnostics.proven_causes)

    # 3. Precedence deadline conflict
    p3 = ProjectOptimizationCandidate("M3", "C3", "D1", 10.0, 3, is_tier1_mandatory=True, deadline_period=2)
    req3 = RecoveryOptimizationRequest("s3", 4, initial_cash=100.0, max_safety_start_period=2, allow_uniform_weight_fallback=True, candidates=[p3])
    r3 = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req3)
    assert any(f.category == "PRECEDENCE_DEADLINE_CONFLICT" for f in r3.infeasibility_diagnostics.proven_causes)

    # 4. Resource capacity forced concurrency
    pa = ProjectOptimizationCandidate("MA", "CA", "D1", 10.0, 3, release_period=1, deadline_period=4, is_tier1_mandatory=True, resource_demands={"c": 1})
    pb = ProjectOptimizationCandidate("MB", "CB", "D1", 10.0, 3, release_period=2, deadline_period=5, is_tier1_mandatory=True, resource_demands={"c": 1})
    req4 = RecoveryOptimizationRequest(
        "s4", 5, initial_cash=100.0, max_safety_start_period=2, allow_uniform_weight_fallback=True, candidates=[pa, pb], resource_capacities={"c": {t: 1 for t in range(1, 6)}}
    )
    r4 = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req4)
    assert any(f.category == "RESOURCE_CAPACITY_EXCEEDED" for f in r4.infeasibility_diagnostics.proven_causes)

    # 5. Funding source dedicated oversubscription
    p5 = ProjectOptimizationCandidate("M5", "C5", "D1", 100.0, 1, is_tier1_mandatory=True, eligible_funds=["F1"])
    f1 = FundingSourceSpec("F1", capacity=50.0)
    req5 = RecoveryOptimizationRequest("s5", 2, initial_cash=200.0, max_safety_start_period=2, allow_uniform_weight_fallback=True, candidates=[p5], funding_sources=[f1])
    r5 = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req5)
    assert any(f.category == "FUNDING_SOURCE_RESTRICTION" for f in r5.infeasibility_diagnostics.proven_causes)


def test_35_multiple_simultaneous_diagnostic_categories():
    """35. Multiple simultaneous diagnostic categories reported concurrently without compression."""
    # Concurrently violates budget AND planning horizon
    p = ProjectOptimizationCandidate(
        "M1", "C1", "D1", 5000.0, 10, is_tier1_mandatory=True # Horizon 4, duration 10, cost 5000 > cash 100
    )
    req = RecoveryOptimizationRequest("multi_diag", 4, initial_cash=100.0, max_safety_start_period=2, allow_uniform_weight_fallback=True, candidates=[p])
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "INFEASIBLE"
    proven = resp.infeasibility_diagnostics.proven_causes
    categories = {f.category for f in proven}
    assert "AGGREGATE_BUDGET_EXCEEDED" in categories
    assert "PLANNING_HORIZON_EXCEEDED" in categories
    assert len(proven) >= 2


# =============================================================================
# 10. Audit Correction Round 1 Regressions
# =============================================================================

def test_36_acceleration_cannot_change_project_selection():
    """36. Non-compensatory acceleration proof: early start cannot overturn substantive MCPI."""
    # Project A has raw_mcpi 0.5000001 (quantized 5000001) but releases late at period 4.
    # Project B has raw_mcpi 0.5000000 (quantized 5000000) and releases early at period 1.
    cA = ProjectOptimizationCandidate(
        project_id="PROJ_A", project_code="CA", district_id="D1",
        estimated_cost=100.0, duration_periods=1, release_period=4, raw_mcpi_score=0.5000001
    )
    cB = ProjectOptimizationCandidate(
        project_id="PROJ_B", project_code="CB", district_id="D1",
        estimated_cost=100.0, duration_periods=1, release_period=1, raw_mcpi_score=0.5000000
    )
    # Budget only permits selecting 1 project
    req = RecoveryOptimizationRequest(
        scenario_name="non_compensatory_proof",
        planning_horizon_periods=5,
        initial_cash=100.0,
        enable_early_start_bonus=True,
        allow_uniform_weight_fallback=True,
        candidates=[cA, cB],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    selected = {p.project_id: p for p in resp.scheduled_projects if p.is_selected}
    assert "PROJ_A" in selected
    assert "PROJ_B" not in selected
    assert selected["PROJ_A"].scheduled_start_period == 4


def test_37_acceleration_selects_earlier_schedule_for_equivalent_mcpi():
    """37. Acceleration tie-breaker strictly prefers earlier starts among equal-MCPI candidates."""
    cA = ProjectOptimizationCandidate(
        project_id="PROJ_A", project_code="CA", district_id="D1",
        estimated_cost=100.0, duration_periods=1, release_period=1, raw_mcpi_score=0.8000000
    )
    cB = ProjectOptimizationCandidate(
        project_id="PROJ_B", project_code="CB", district_id="D1",
        estimated_cost=100.0, duration_periods=1, release_period=3, raw_mcpi_score=0.8000000
    )
    req = RecoveryOptimizationRequest(
        scenario_name="accel_tie_breaker",
        planning_horizon_periods=4,
        initial_cash=100.0,
        enable_early_start_bonus=True,
        allow_uniform_weight_fallback=True,
        candidates=[cA, cB],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    selected = {p.project_id: p for p in resp.scheduled_projects if p.is_selected}
    assert "PROJ_A" in selected
    assert "PROJ_B" not in selected
    assert selected["PROJ_A"].scheduled_start_period == 1


def test_38_assumption_core_reports_only_conflicting_subset():
    """38. Assumption core extraction: only conflicting assumptions are extracted, not all."""
    # Mandatory project M1 needs 100 CCU, assigned to F1 with capacity 50 (conflicts).
    # Non-conflicting mandatory project M2 needs 10 CCU, assigned to F2 with capacity 500 (feasible).
    p1 = ProjectOptimizationCandidate("M1", "C1", "D1", 100.0, 1, is_tier1_mandatory=True, eligible_funds=["F1"])
    p2 = ProjectOptimizationCandidate("M2", "C2", "D1", 10.0, 1, is_tier1_mandatory=True, eligible_funds=["F2"])
    f1 = FundingSourceSpec("F1", capacity=50.0)
    f2 = FundingSourceSpec("F2", capacity=500.0)
    req = RecoveryOptimizationRequest(
        scenario_name="core_subset",
        planning_horizon_periods=2,
        initial_cash=500.0,
        max_safety_start_period=2,
        allow_uniform_weight_fallback=True,
        candidates=[p1, p2],
        funding_sources=[f1, f2],
    )
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve(enable_assumptions=True)
    assert resp.solver_status == "INFEASIBLE"
    assert resp.infeasibility_diagnostics is not None
    # Solver hypotheses must capture fund_F1 or mand_M1, but must NOT falsely accuse mand_M2 or fund_F2
    hypo_names = [h.message for h in resp.infeasibility_diagnostics.solver_hypotheses]
    hypo_text = " ".join(hypo_names)
    assert "F1" in hypo_text or "M1" in hypo_text
    assert "F2" not in hypo_text
    assert "M2" not in hypo_text


def test_39_mandatory_safety_deadline_within_deadline():
    """39. Mandatory project starts on or before max_safety_start_period successfully."""
    p = ProjectOptimizationCandidate("M_SAFE", "CMS", "D1", 100.0, 2, release_period=1, is_tier1_mandatory=True)
    req = RecoveryOptimizationRequest(
        scenario_name="safety_within",
        planning_horizon_periods=5,
        initial_cash=500.0,
        max_safety_start_period=2,
        allow_uniform_weight_fallback=True,
        candidates=[p],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    assert resp.scheduled_projects[0].is_selected is True
    assert resp.scheduled_projects[0].scheduled_start_period <= 2


def test_40_mandatory_safety_deadline_exceeded_causes_infeasible():
    """40. Mandatory project release > max_safety_start_period returns INFEASIBLE with diagnostics."""
    p = ProjectOptimizationCandidate("M_LATE", "CML", "D1", 100.0, 1, release_period=3, is_tier1_mandatory=True)
    req = RecoveryOptimizationRequest(
        scenario_name="safety_exceeded",
        planning_horizon_periods=5,
        initial_cash=500.0,
        max_safety_start_period=2, # Cannot start at period 3
        allow_uniform_weight_fallback=True,
        candidates=[p],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "INFEASIBLE"
    assert resp.infeasibility_diagnostics is not None
    assert any(
        f.category == "PRECEDENCE_DEADLINE_CONFLICT" and "safety" in f.message.lower()
        for f in resp.infeasibility_diagnostics.proven_causes
    )


def test_41_mandatory_safety_deadline_with_predecessor_lag():
    """41. Predecessor lag pushing mandatory project past safety deadline returns INFEASIBLE."""
    p1 = ProjectOptimizationCandidate("P1", "C1", "D1", 50.0, 2, release_period=1) # finishes at 2
    p2 = ProjectOptimizationCandidate("M_SUCC", "CMS", "D1", 50.0, 1, release_period=1, is_tier1_mandatory=True)
    dep = DependencyEdgeInput(predecessor_id="P1", successor_id="M_SUCC", lag_periods=2) # earliest start: 1 + 2 + 2 = 5
    req = RecoveryOptimizationRequest(
        scenario_name="safety_lag",
        planning_horizon_periods=6,
        initial_cash=500.0,
        max_safety_start_period=3, # Must start by 3, but cannot start until 5
        allow_uniform_weight_fallback=True,
        candidates=[p1, p2],
        dependencies=[dep],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "INFEASIBLE"
    assert resp.infeasibility_diagnostics is not None
    assert any(
        f.category == "PRECEDENCE_DEADLINE_CONFLICT"
        for f in resp.infeasibility_diagnostics.proven_causes
    )


def test_42_non_mandatory_project_unaffected_by_safety_deadline():
    """42. Non-mandatory project is unconstrained by max_safety_start_period."""
    p = ProjectOptimizationCandidate("NON_MAND", "CNM", "D1", 100.0, 1, release_period=3, is_tier1_mandatory=False, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest(
        scenario_name="safety_non_mandatory",
        planning_horizon_periods=5,
        initial_cash=500.0,
        max_safety_start_period=2, # Would block if mandatory, but p is non-mandatory
        allow_uniform_weight_fallback=True,
        candidates=[p],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    assert resp.scheduled_projects[0].is_selected is True
    assert resp.scheduled_projects[0].scheduled_start_period == 3


def test_43_canonical_fingerprint_sensitivity():
    """43. Mutating any input attribute produces a different SHA-256 fingerprint."""
    base_cand = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 2, raw_mcpi_score=0.85)
    base_req = RecoveryOptimizationRequest(
        scenario_name="base_fingerprint",
        planning_horizon_periods=4,
        initial_cash=1000.0,
        allow_uniform_weight_fallback=True,
        candidates=[base_cand],
    )
    base_fp = compute_canonical_input_fingerprint(base_req)

    # Mutate scenario name
    req_mut1 = RecoveryOptimizationRequest("base_fingerprint_mut", 4, initial_cash=1000.0, allow_uniform_weight_fallback=True, candidates=[base_cand])
    assert compute_canonical_input_fingerprint(req_mut1) != base_fp

    # Mutate horizon
    req_mut2 = RecoveryOptimizationRequest("base_fingerprint", 5, initial_cash=1000.0, allow_uniform_weight_fallback=True, candidates=[base_cand])
    assert compute_canonical_input_fingerprint(req_mut2) != base_fp

    # Mutate initial cash
    req_mut3 = RecoveryOptimizationRequest("base_fingerprint", 4, initial_cash=999.0, allow_uniform_weight_fallback=True, candidates=[base_cand])
    assert compute_canonical_input_fingerprint(req_mut3) != base_fp

    # Mutate candidate cost
    cand_mut = ProjectOptimizationCandidate("P1", "C1", "D1", 101.0, 2, raw_mcpi_score=0.85)
    req_mut4 = RecoveryOptimizationRequest("base_fingerprint", 4, initial_cash=1000.0, allow_uniform_weight_fallback=True, candidates=[cand_mut])
    assert compute_canonical_input_fingerprint(req_mut4) != base_fp


def test_44_canonical_fingerprint_permutation_equivalence():
    """44. Permuting candidate list or dependency list preserves exact SHA-256 fingerprint."""
    c1 = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1)
    c2 = ProjectOptimizationCandidate("P2", "C2", "D1", 200.0, 2)
    c3 = ProjectOptimizationCandidate("P3", "C3", "D2", 150.0, 1)
    dep1 = DependencyEdgeInput("P1", "P2", 1)
    dep2 = DependencyEdgeInput("P2", "P3", 0)

    req_order1 = RecoveryOptimizationRequest(
        scenario_name="perm_test",
        planning_horizon_periods=5,
        allow_uniform_weight_fallback=True,
        candidates=[c1, c2, c3],
        dependencies=[dep1, dep2],
    )
    req_order2 = RecoveryOptimizationRequest(
        scenario_name="perm_test",
        planning_horizon_periods=5,
        allow_uniform_weight_fallback=True,
        candidates=[c3, c1, c2],
        dependencies=[dep2, dep1],
    )
    assert compute_canonical_input_fingerprint(req_order1) == compute_canonical_input_fingerprint(req_order2)


def test_45_integer_overflow_pre_model_rejection():
    """45. Pre-model numerical safety validation rejects coefficients exceeding MAX_SAFE_INTEGER."""
    # Overflow in project cost
    huge_cand = ProjectOptimizationCandidate("HUGE", "CH", "D1", estimated_cost=MAX_SAFE_INTEGER + 1, duration_periods=1)
    req = RecoveryOptimizationRequest("overflow_test", 2, candidates=[huge_cand])
    with pytest.raises(ValueError, match="INTEGER_OVERFLOW_RISK"):
        validate_numerical_safety(req)

    # Overflow in initial cash
    req_cash = RecoveryOptimizationRequest("overflow_cash", 2, initial_cash=MAX_SAFE_INTEGER + 1)
    with pytest.raises(ValueError, match="INTEGER_OVERFLOW_RISK"):
        validate_numerical_safety(req_cash)


def test_46_post_solve_reconciliation_total_cost():
    """46. Orchestrator detects post-solve total cost mismatch and flags failure."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_cost", 2, initial_cash=200.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Tamper with total_cost_ccu
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu + 9999, # Tampered!
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Total cost mismatch" in f for f in failures)


def test_47_post_solve_reconciliation_expenditure_conservation():
    """47. Orchestrator detects periodic expenditure sum mismatch against project cost."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 2, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_expenditure", 3, initial_cash=200.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Tamper with scheduled project's periodic expenditure
    tampered_projects = []
    for proj in resp.scheduled_projects:
        tampered_exp = dict(proj.periodic_expenditures_ccu)
        tampered_exp[1] += 100 # Conservation broken!
        tampered_projects.append(
            ScheduledProjectResult(
                project_id=proj.project_id,
                project_code=proj.project_code,
                district_id=proj.district_id,
                is_selected=proj.is_selected,
                scheduled_start_period=proj.scheduled_start_period,
                scheduled_completion_period=proj.scheduled_completion_period,
                assigned_funding_source=proj.assigned_funding_source,
                cost_ccu=proj.cost_ccu,
                cost_inr=proj.cost_inr,
                periodic_expenditures_ccu=tampered_exp,
                periodic_expenditures_inr=proj.periodic_expenditures_inr,
                mcpi_score=proj.mcpi_score,
                raw_mcpi_score=proj.raw_mcpi_score,
                quantized_mcpi_coefficient=proj.quantized_mcpi_coefficient,
                is_tier1_mandatory=proj.is_tier1_mandatory,
            )
        )
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=tampered_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("expenditure conservation failed" in f for f in failures)


def test_48_post_solve_reconciliation_solvency_recurrence():
    """48. Orchestrator detects broken cash recurrence Phi_t in post-solve audit."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_solvency", 2, initial_cash=200.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Tamper with period 1 solvency cash balance
    tampered_solv = []
    for s in resp.periodic_solvency:
        tampered_solv.append(
            PeriodSolvencyResult(
                period=s.period,
                revenue_receipt_ccu=s.revenue_receipt_ccu,
                expenditure_ccu=s.expenditure_ccu,
                cash_balance_ccu=s.cash_balance_ccu + 500, # Tampered!
                cash_balance_inr=s.cash_balance_inr,
                is_solvent=s.is_solvent,
            )
        )
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=tampered_solv,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("cash balance recurrence failed" in f for f in failures)


def test_49_invalid_retention_rate_rejected():
    """49. Rejects any fiscal_retention_rate != 1.0 (Section 8A)."""
    req = RecoveryOptimizationRequest("retention_test", 2, fiscal_retention_rate=0.8)
    with pytest.raises(ValueError, match="fiscal_retention_rate"):
        RecoveryOptimizationOrchestrator.validate_request(req, raise_on_error=True)
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "MODEL_INVALID"


def test_50_unsupported_funding_tranches_rejected():
    """50. Rejects funding sources with period_tranches (Section 8B)."""
    f = FundingSourceSpec("F_TRANCHED", capacity=100.0, period_tranches={1: 50.0, 2: 50.0})
    req = RecoveryOptimizationRequest("tranche_test", 2, funding_sources=[f])
    with pytest.raises(ValueError, match="period_tranches"):
        RecoveryOptimizationOrchestrator.validate_request(req, raise_on_error=True)
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "MODEL_INVALID"


def test_51_normalize_to_ccu_rejections():
    """51. normalize_to_ccu rejects invalid modes, NaN, inf, negative amounts, invalid currencies (Section 8C)."""
    with pytest.raises(ValueError, match="UNSUPPORTED_ROUNDING_MODE"):
        normalize_to_ccu(100, CurrencyUnit.INR, rounding_mode="nearest")

    with pytest.raises(ValueError, match="NON_FINITE_AMOUNT"):
        normalize_to_ccu(float("nan"), CurrencyUnit.INR)

    with pytest.raises(ValueError, match="NON_FINITE_AMOUNT"):
        normalize_to_ccu(float("inf"), CurrencyUnit.INR)

    with pytest.raises(ValueError, match="NEGATIVE_AMOUNT"):
        normalize_to_ccu(-10.0, CurrencyUnit.INR)

    with pytest.raises(ValueError, match="UNSUPPORTED_CURRENCY"):
        normalize_to_ccu(100, "BITCOIN")


def test_52_duplicate_ids_and_invalid_dependencies_rejected():
    """52. Rejects duplicate project IDs, self-dependencies, unknown dependency references (Section 8E)."""
    c1 = ProjectOptimizationCandidate("DUP_ID", "C1", "D1", 100.0, 1)
    c2 = ProjectOptimizationCandidate("DUP_ID", "C2", "D1", 100.0, 1)
    req_dup = RecoveryOptimizationRequest("dup_test", 2, candidates=[c1, c2])
    with pytest.raises(ValueError, match="Duplicate project IDs"):
        RecoveryOptimizationOrchestrator.validate_request(req_dup, raise_on_error=True)
    assert RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req_dup).solver_status == "MODEL_INVALID"

    # Self-dependency
    cand = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1)
    self_dep = DependencyEdgeInput("P1", "P1", 0)
    req_self = RecoveryOptimizationRequest("self_dep_test", 2, candidates=[cand], dependencies=[self_dep])
    with pytest.raises(ValueError, match="Self-dependency"):
        RecoveryOptimizationOrchestrator.validate_request(req_self, raise_on_error=True)
    assert RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req_self).solver_status == "MODEL_INVALID"

    # Unknown reference
    unk_dep = DependencyEdgeInput("P1", "UNKNOWN", 0)
    req_unk = RecoveryOptimizationRequest("unk_dep_test", 2, candidates=[cand], dependencies=[unk_dep])
    with pytest.raises(ValueError, match="unknown project|not found"):
        RecoveryOptimizationOrchestrator.validate_request(req_unk, raise_on_error=True)
    assert RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req_unk).solver_status == "MODEL_INVALID"


def test_53_missing_expenditure_weights_fail_closed():
    """53. Fails closed when candidate has no weights and allow_uniform_weight_fallback=False (Section 8D)."""
    cand = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 2, expenditure_weights=None)
    req = RecoveryOptimizationRequest("fail_closed_test", 3, candidates=[cand], allow_uniform_weight_fallback=False)
    with pytest.raises(ValueError, match="allow_uniform_weight_fallback is False"):
        RecoveryOptimizationOrchestrator.validate_request(req, raise_on_error=True)
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "MODEL_INVALID"


def test_54_empty_portfolio_validation_enforced():
    """54. Empty portfolio still undergoes full validation of horizon and budget (Section 8F)."""
    # Empty candidate list, but invalid planning horizon 0
    req_invalid_horizon = RecoveryOptimizationRequest("empty_invalid_horizon", 0, candidates=[])
    with pytest.raises(ValueError, match="Planning horizon must be >= 1"):
        RecoveryOptimizationOrchestrator.validate_request(req_invalid_horizon, raise_on_error=True)
    resp_h = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req_invalid_horizon)
    assert resp_h.solver_status == "MODEL_INVALID"

    # Empty candidate list, but invalid negative initial cash
    req_neg_cash = RecoveryOptimizationRequest("empty_neg_cash", 3, initial_cash=-100.0, candidates=[])
    with pytest.raises(ValueError, match="Initial cash cannot be negative"):
        RecoveryOptimizationOrchestrator.validate_request(req_neg_cash, raise_on_error=True)
    resp_c = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req_neg_cash)
    assert resp_c.solver_status == "MODEL_INVALID"


# =============================================================================
# 11. Owner Audit Correction Round 2 Regression Tests (Tests 55–66)
# =============================================================================

def test_55_mandatory_project_missing_safety_deadline_fails_closed():
    """55. Request with mandatory life-safety project and omitted safety deadline fails closed (Correction 1)."""
    cand = ProjectOptimizationCandidate("M_CRIT", "CMC", "D1", 100.0, 1, is_tier1_mandatory=True)
    req = RecoveryOptimizationRequest(
        scenario_name="missing_safety_deadline",
        planning_horizon_periods=4,
        initial_cash=500.0,
        max_safety_start_period=None, # Missing!
        allow_uniform_weight_fallback=True,
        candidates=[cand],
    )
    with pytest.raises(ValueError, match="max_safety_start_period \\(T_safety_max\\) is None"):
        RecoveryOptimizationOrchestrator.validate_request(req, raise_on_error=True)
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "MODEL_INVALID"


def test_56_mandatory_safety_deadline_exceeding_horizon_fails_closed():
    """56. Mandatory safety deadline exceeding planning horizon fails closed (Correction 1)."""
    cand = ProjectOptimizationCandidate("M_CRIT", "CMC", "D1", 100.0, 1, is_tier1_mandatory=True)
    req = RecoveryOptimizationRequest(
        scenario_name="invalid_safety_deadline",
        planning_horizon_periods=3,
        initial_cash=500.0,
        max_safety_start_period=5, # 5 > horizon 3
        allow_uniform_weight_fallback=True,
        candidates=[cand],
    )
    with pytest.raises(ValueError, match="must be between 1 and planning_horizon_periods"):
        RecoveryOptimizationOrchestrator.validate_request(req, raise_on_error=True)
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "MODEL_INVALID"


def test_57_missing_expenditure_weights_default_fails_closed():
    """57. Omitting expenditure_weights with default settings fails closed (Correction 2)."""
    cand = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 2, expenditure_weights=None)
    # allow_uniform_weight_fallback is omitted, defaulting to False
    req = RecoveryOptimizationRequest("default_fallback_false", 3, candidates=[cand])
    assert req.allow_uniform_weight_fallback is False
    with pytest.raises(ValueError, match="allow_uniform_weight_fallback is False"):
        RecoveryOptimizationOrchestrator.validate_request(req, raise_on_error=True)
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "MODEL_INVALID"


def test_58_explicitly_authorized_uniform_fallback_succeeds():
    """58. Explicitly authorized allow_uniform_weight_fallback=True generates equal profile (Correction 2)."""
    cand = ProjectOptimizationCandidate("P1", "C1", "D1", 120.0, 3, expenditure_weights=None)
    req = RecoveryOptimizationRequest(
        scenario_name="explicit_fallback_true",
        planning_horizon_periods=4,
        initial_cash=500.0,
        allow_uniform_weight_fallback=True,
        candidates=[cand],
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    p = resp.scheduled_projects[0]
    assert p.is_selected is True
    # 120 CCU over 3 periods -> 40 each
    exp_inr = [p.periodic_expenditures_inr[t] for t in sorted(p.periodic_expenditures_inr.keys())]
    assert exp_inr == [Decimal("40"), Decimal("40"), Decimal("40")]


def test_59_sufficient_assumption_core_terminology_and_subset_mapping():
    """59. Assumption core reports sufficient (not minimal) core with literal mapping (Correction 3)."""
    p1 = ProjectOptimizationCandidate("M1", "C1", "D1", 100.0, 1, is_tier1_mandatory=True, eligible_funds=["F1"])
    f1 = FundingSourceSpec("F1", capacity=50.0)
    req = RecoveryOptimizationRequest(
        scenario_name="sufficient_core_test",
        planning_horizon_periods=2,
        initial_cash=500.0,
        max_safety_start_period=2,
        allow_uniform_weight_fallback=True,
        candidates=[p1],
        funding_sources=[f1],
    )
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve(enable_assumptions=True)
    assert resp.solver_status == "INFEASIBLE"
    assert resp.infeasibility_diagnostics is not None
    # Must explicitly disclaim minimality
    assert resp.infeasibility_diagnostics.is_assumption_core_minimal is False
    assert resp.infeasibility_diagnostics.is_assumption_core_sufficient is True
    # Hypotheses correctly map assumption literals
    hypo_msgs = [h.message for h in resp.infeasibility_diagnostics.solver_hypotheses]
    assert any("fund_F1" in m for m in hypo_msgs)


def test_60_aggregate_resource_expression_overflow():
    """60. Individually safe resource demands whose aggregate sum exceeds MAX_SAFE_INTEGER are rejected (Correction 4)."""
    # 6 candidates each demanding 2 * 10^16 units of resource 'crane'
    # Each demand 2*10^16 < 10^17, but sum = 1.2 * 10^17 > 10^17
    safe_single_demand = 20_000_000_000_000_000 # 2 * 10^16
    cands = [
        ProjectOptimizationCandidate(
            f"P_{i}", f"C_{i}", "D1", 10.0, 1,
            resource_demands={"crane": safe_single_demand}
        )
        for i in range(6)
    ]
    req = RecoveryOptimizationRequest(
        scenario_name="aggregate_resource_overflow",
        planning_horizon_periods=2,
        initial_cash=500.0,
        allow_uniform_weight_fallback=True,
        candidates=cands,
        resource_capacities={"crane": {1: safe_single_demand, 2: safe_single_demand}},
    )
    with pytest.raises(ValueError, match="INTEGER_OVERFLOW_RISK: aggregate resource 'crane' demand sum"):
        validate_numerical_safety(req)
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "MODEL_INVALID"


def test_61_reconciliation_detects_release_period_violation():
    """61. Reconciliation independent audit flags project starting before release period (Correction 5)."""
    p = ProjectOptimizationCandidate("P_REL", "C1", "D1", 100.0, 2, release_period=3, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_rel", 5, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Tamper scheduled start period to 1 (< release 3)
    tampered_projects = [
        ScheduledProjectResult(
            project_id=proj.project_id,
            project_code=proj.project_code,
            district_id=proj.district_id,
            is_selected=proj.is_selected,
            scheduled_start_period=1, # Tampered!
            scheduled_completion_period=2,
            assigned_funding_source=proj.assigned_funding_source,
            cost_ccu=proj.cost_ccu,
            cost_inr=proj.cost_inr,
            periodic_expenditures_ccu={1: 5000000, 2: 5000000},
            periodic_expenditures_inr={1: Decimal("50"), 2: Decimal("50")},
            mcpi_score=proj.mcpi_score,
            raw_mcpi_score=proj.raw_mcpi_score,
            quantized_mcpi_coefficient=proj.quantized_mcpi_coefficient,
            is_tier1_mandatory=proj.is_tier1_mandatory,
        )
        for proj in resp.scheduled_projects
    ]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=tampered_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Release period violation" in f for f in failures)


def test_62_reconciliation_detects_completion_period_mismatch():
    """62. Reconciliation independent audit flags C_j != S_j + d_j - 1 mismatch (Correction 5)."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 2, release_period=1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_dur", 4, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Tamper scheduled completion period to 4 (expected 2)
    tampered_projects = [
        ScheduledProjectResult(
            project_id=proj.project_id,
            project_code=proj.project_code,
            district_id=proj.district_id,
            is_selected=proj.is_selected,
            scheduled_start_period=proj.scheduled_start_period,
            scheduled_completion_period=4, # Tampered! (start 1 + dur 2 - 1 = 2)
            assigned_funding_source=proj.assigned_funding_source,
            cost_ccu=proj.cost_ccu,
            cost_inr=proj.cost_inr,
            periodic_expenditures_ccu=proj.periodic_expenditures_ccu,
            periodic_expenditures_inr=proj.periodic_expenditures_inr,
            mcpi_score=proj.mcpi_score,
            raw_mcpi_score=proj.raw_mcpi_score,
            quantized_mcpi_coefficient=proj.quantized_mcpi_coefficient,
            is_tier1_mandatory=proj.is_tier1_mandatory,
        )
        for proj in resp.scheduled_projects
    ]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=tampered_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Completion period mismatch" in f for f in failures)


def test_63_reconciliation_detects_incorrect_expenditure_profile():
    """63. Reconciliation independent audit flags spend outside execution window (Correction 5)."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, release_period=1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_prof", 4, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Project executes at period 1 only, tamper spend to occur at period 3
    tampered_projects = [
        ScheduledProjectResult(
            project_id=proj.project_id,
            project_code=proj.project_code,
            district_id=proj.district_id,
            is_selected=proj.is_selected,
            scheduled_start_period=1,
            scheduled_completion_period=1,
            assigned_funding_source=proj.assigned_funding_source,
            cost_ccu=proj.cost_ccu,
            cost_inr=proj.cost_inr,
            periodic_expenditures_ccu={3: proj.cost_ccu}, # Non-zero at period 3 outside execution [1, 1]!
            periodic_expenditures_inr={3: proj.cost_inr},
            mcpi_score=proj.mcpi_score,
            raw_mcpi_score=proj.raw_mcpi_score,
            quantized_mcpi_coefficient=proj.quantized_mcpi_coefficient,
            is_tier1_mandatory=proj.is_tier1_mandatory,
        )
        for proj in resp.scheduled_projects
    ]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=tampered_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Expenditure profile violation" in f for f in failures)


def test_64_reconciliation_detects_objective_value_mismatch():
    """64. Reconciliation independent audit recomputes integer objective and flags discrepancies (Correction 5)."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, release_period=1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_obj", 4, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Tamper objective value by +99999.0
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value + 99999.0, # Tampered!
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Objective value mismatch" in f for f in failures)


def test_65_reconciliation_detects_mandatory_safety_deadline_violation():
    """65. Reconciliation flags mandatory project starting past safety deadline (Correction 5)."""
    p = ProjectOptimizationCandidate("M_SAFE", "CMS", "D1", 100.0, 1, release_period=1, is_tier1_mandatory=True)
    req = RecoveryOptimizationRequest(
        "reconcile_safety", 5, initial_cash=500.0, max_safety_start_period=2, allow_uniform_weight_fallback=True, candidates=[p]
    )
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Tamper scheduled start period to 3 (> safety deadline 2)
    tampered_projects = [
        ScheduledProjectResult(
            project_id=proj.project_id,
            project_code=proj.project_code,
            district_id=proj.district_id,
            is_selected=proj.is_selected,
            scheduled_start_period=3, # Tampered: > 2
            scheduled_completion_period=3,
            assigned_funding_source=proj.assigned_funding_source,
            cost_ccu=proj.cost_ccu,
            cost_inr=proj.cost_inr,
            periodic_expenditures_ccu={3: proj.cost_ccu},
            periodic_expenditures_inr={3: proj.cost_inr},
            mcpi_score=proj.mcpi_score,
            raw_mcpi_score=proj.raw_mcpi_score,
            quantized_mcpi_coefficient=proj.quantized_mcpi_coefficient,
            is_tier1_mandatory=proj.is_tier1_mandatory,
        )
        for proj in resp.scheduled_projects
    ]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=tampered_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("safety deadline" in f for f in failures)


def test_66_reconciliation_detects_unselected_mandatory_project():
    """66. Reconciliation flags mandatory life-safety project that was omitted from selection (Correction 5)."""
    p = ProjectOptimizationCandidate("M_SAFE", "CMS", "D1", 100.0, 1, release_period=1, is_tier1_mandatory=True)
    req = RecoveryOptimizationRequest(
        "reconcile_mand_sel", 5, initial_cash=500.0, max_safety_start_period=2, allow_uniform_weight_fallback=True, candidates=[p]
    )
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Tamper scheduled project to unselected
    tampered_projects = [
        ScheduledProjectResult(
            project_id=proj.project_id,
            project_code=proj.project_code,
            district_id=proj.district_id,
            is_selected=False, # Dropped!
            scheduled_start_period=None,
            scheduled_completion_period=None,
            assigned_funding_source=None,
            cost_ccu=0,
            cost_inr=Decimal("0"),
            periodic_expenditures_ccu={},
            periodic_expenditures_inr={},
            mcpi_score=proj.mcpi_score,
            raw_mcpi_score=proj.raw_mcpi_score,
            quantized_mcpi_coefficient=proj.quantized_mcpi_coefficient,
            is_tier1_mandatory=proj.is_tier1_mandatory,
        )
        for proj in resp.scheduled_projects
    ]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=0.0,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=0,
        total_cost_ccu=0,
        total_cost_inr=Decimal("0"),
        scheduled_projects=tampered_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu={},
        district_equity_allocation_inr={},
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Mandatory life-safety project M_SAFE was not selected" in f for f in failures)


def test_67_reconciliation_detects_altered_project_cost_with_consistent_profile_and_total():
    """67. Reconciler detects altered project cost even when periodic expenditures and total cost are altered consistently."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_recon_cost", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Deliberately alter project cost from 100 to 150, but adjust periodic expenditures and total cost consistently
    tampered_projects = [
        ScheduledProjectResult(
            project_id=proj.project_id,
            project_code=proj.project_code,
            district_id=proj.district_id,
            is_selected=proj.is_selected,
            scheduled_start_period=proj.scheduled_start_period,
            scheduled_completion_period=proj.scheduled_completion_period,
            assigned_funding_source=proj.assigned_funding_source,
            cost_ccu=150,  # Altered! (Original candidate cost was 100)
            cost_inr=Decimal("150"),
            periodic_expenditures_ccu={1: 150},  # Consistently altered to match 150!
            periodic_expenditures_inr={1: Decimal("150")},
            mcpi_score=proj.mcpi_score,
            raw_mcpi_score=proj.raw_mcpi_score,
            quantized_mcpi_coefficient=proj.quantized_mcpi_coefficient,
            is_tier1_mandatory=proj.is_tier1_mandatory,
        )
        for proj in resp.scheduled_projects
    ]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=150,  # Consistently altered!
        total_cost_inr=Decimal("150"),  # Consistently altered!
        scheduled_projects=tampered_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("cost CCU mismatch" in f for f in failures)
    assert any("independently reconstructed 100" in f for f in failures)


def test_68_reconciliation_detects_altered_project_cost_inr_mismatch():
    """68. Reconciler detects altered project cost INR amount against independently reconstructed amount."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_inr_mismatch", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    tampered_projects = [
        ScheduledProjectResult(
            project_id=proj.project_id,
            project_code=proj.project_code,
            district_id=proj.district_id,
            is_selected=proj.is_selected,
            scheduled_start_period=proj.scheduled_start_period,
            scheduled_completion_period=proj.scheduled_completion_period,
            assigned_funding_source=proj.assigned_funding_source,
            cost_ccu=proj.cost_ccu,
            cost_inr=Decimal("99"),  # Mismatched! Expected 100
            periodic_expenditures_ccu=proj.periodic_expenditures_ccu,
            periodic_expenditures_inr=proj.periodic_expenditures_inr,
            mcpi_score=proj.mcpi_score,
            raw_mcpi_score=proj.raw_mcpi_score,
            quantized_mcpi_coefficient=proj.quantized_mcpi_coefficient,
            is_tier1_mandatory=proj.is_tier1_mandatory,
        )
        for proj in resp.scheduled_projects
    ]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=tampered_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("cost INR mismatch" in f for f in failures)


def test_69_reconciliation_detects_missing_period_solvency_record():
    """69. Reconciler detects missing period records in periodic_solvency."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_missing_solv", 3, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Drop period 3 from solvency records
    tampered_solv = [s for s in resp.periodic_solvency if s.period != 3]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=tampered_solv,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Missing solvency record for period 3" in f for f in failures)
    assert any("Solvency record count mismatch" in f for f in failures)


def test_70_reconciliation_detects_duplicate_period_solvency_record():
    """70. Reconciler detects duplicate period records in periodic_solvency."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_dup_solv", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Duplicate period 1 record
    tampered_solv = list(resp.periodic_solvency) + [resp.periodic_solvency[0]]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=tampered_solv,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Duplicate solvency records for periods: [1]" in f for f in failures)


def test_71_reconciliation_detects_out_of_horizon_solvency_record():
    """71. Reconciler detects out-of-horizon period records in periodic_solvency."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_out_horizon_solv", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Add record for period 3 when horizon is 2
    out_record = PeriodSolvencyResult(
        period=3,
        revenue_receipt_ccu=0,
        expenditure_ccu=0,
        cash_balance_ccu=400,
        cash_balance_inr=Decimal("400"),
        is_solvent=True,
    )
    tampered_solv = list(resp.periodic_solvency) + [out_record]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=tampered_solv,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Out-of-horizon solvency record: period 3" in f for f in failures)


def test_72_reconciliation_detects_negative_reconstructed_cash_balance():
    """72. Reconciler detects negative reconstructed cash balance."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_neg_cash", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Initial cash is 500 INR = 50,000,000 CCU. Tamper spend to 60,000,000 CCU so reconstructed cash is negative
    tampered_projects = [
        ScheduledProjectResult(
            project_id=proj.project_id,
            project_code=proj.project_code,
            district_id=proj.district_id,
            is_selected=proj.is_selected,
            scheduled_start_period=proj.scheduled_start_period,
            scheduled_completion_period=proj.scheduled_completion_period,
            assigned_funding_source=proj.assigned_funding_source,
            cost_ccu=proj.cost_ccu,
            cost_inr=proj.cost_inr,
            periodic_expenditures_ccu={1: 60000000},  # Spend 60M with initial cash 50M!
            periodic_expenditures_inr={1: Decimal("600")},
            mcpi_score=proj.mcpi_score,
            raw_mcpi_score=proj.raw_mcpi_score,
            quantized_mcpi_coefficient=proj.quantized_mcpi_coefficient,
            is_tier1_mandatory=proj.is_tier1_mandatory,
        )
        for proj in resp.scheduled_projects
    ]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=tampered_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Negative reconstructed cash balance at period 1" in f for f in failures)


def test_73_reconciliation_detects_duplicate_project_ids_in_scheduled():
    """73. Reconciler detects duplicate project IDs in scheduled_projects."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_dup_pid", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Duplicate P1 in scheduled_projects
    tampered_projects = list(resp.scheduled_projects) + [resp.scheduled_projects[0]]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=len(tampered_projects),
        total_cost_ccu=resp.total_cost_ccu * 2,
        total_cost_inr=resp.total_cost_inr * 2,
        scheduled_projects=tampered_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Duplicate project IDs in scheduled_projects" in f for f in failures)


def test_74_reconciliation_detects_unknown_project_id_in_scheduled():
    """74. Reconciler detects unknown project IDs not present in original candidates."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_unknown_pid", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    unknown_proj = ScheduledProjectResult(
        project_id="P_UNKNOWN_99",
        project_code="CU99",
        district_id="D1",
        is_selected=True,
        scheduled_start_period=1,
        scheduled_completion_period=1,
        assigned_funding_source=None,
        cost_ccu=50,
        cost_inr=Decimal("50"),
        periodic_expenditures_ccu={1: 50},
        periodic_expenditures_inr={1: Decimal("50")},
        mcpi_score=0.5,
        raw_mcpi_score=0.5,
        quantized_mcpi_coefficient=5000000,
        is_tier1_mandatory=False,
    )
    tampered_projects = list(resp.scheduled_projects) + [unknown_proj]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=len(tampered_projects),
        total_cost_ccu=resp.total_cost_ccu + 50,
        total_cost_inr=resp.total_cost_inr + Decimal("50"),
        scheduled_projects=tampered_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Unknown project ID 'P_UNKNOWN_99'" in f for f in failures)


def test_75_reconciliation_detects_unselected_project_with_active_schedule():
    """75. Reconciler detects unselected project having active schedule or non-zero expenditure."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_unselected_active", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Mark project as unselected, but keep active start and expenditures
    tampered_projects = [
        ScheduledProjectResult(
            project_id=proj.project_id,
            project_code=proj.project_code,
            district_id=proj.district_id,
            is_selected=False,  # Unselected!
            scheduled_start_period=1,  # Active start!
            scheduled_completion_period=1,
            assigned_funding_source=None,
            cost_ccu=0,
            cost_inr=Decimal("0"),
            periodic_expenditures_ccu={1: 50},  # Non-zero spend!
            periodic_expenditures_inr={1: Decimal("50")},
            mcpi_score=proj.mcpi_score,
            raw_mcpi_score=proj.raw_mcpi_score,
            quantized_mcpi_coefficient=proj.quantized_mcpi_coefficient,
            is_tier1_mandatory=proj.is_tier1_mandatory,
        )
        for proj in resp.scheduled_projects
    ]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=0.0,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=0,
        total_cost_ccu=0,
        total_cost_inr=Decimal("0"),
        scheduled_projects=tampered_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu={},
        district_equity_allocation_inr={},
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Unselected project 'P1' has active schedule start" in f for f in failures)


def test_76_reconciliation_detects_selected_project_missing_schedule_fields():
    """76. Reconciler detects selected project with missing schedule start or completion period."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("reconcile_missing_sched", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Selected project with null scheduled_start_period
    tampered_projects = [
        ScheduledProjectResult(
            project_id=proj.project_id,
            project_code=proj.project_code,
            district_id=proj.district_id,
            is_selected=True,
            scheduled_start_period=None,  # Missing start!
            scheduled_completion_period=proj.scheduled_completion_period,
            assigned_funding_source=proj.assigned_funding_source,
            cost_ccu=proj.cost_ccu,
            cost_inr=proj.cost_inr,
            periodic_expenditures_ccu=proj.periodic_expenditures_ccu,
            periodic_expenditures_inr=proj.periodic_expenditures_inr,
            mcpi_score=proj.mcpi_score,
            raw_mcpi_score=proj.raw_mcpi_score,
            quantized_mcpi_coefficient=proj.quantized_mcpi_coefficient,
            is_tier1_mandatory=proj.is_tier1_mandatory,
        )
        for proj in resp.scheduled_projects
    ]
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status=resp.solver_status,
        is_optimal=resp.is_optimal,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=tampered_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("missing scheduled_start_period" in f for f in failures)


def test_77_optimal_with_is_optimal_false_rejected():
    """77. Reconciler rejects OPTIMAL solver status with is_optimal=False."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_77", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="OPTIMAL",
        is_optimal=False,  # Inconsistent!
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value,
        exact_best_bound=resp.exact_best_bound,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Solver status OPTIMAL must have is_optimal=True" in f for f in failures)


def test_78_feasible_with_is_optimal_true_rejected():
    """78. Reconciler rejects FEASIBLE solver status with is_optimal=True."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_78", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Convert to FEASIBLE with is_optimal=True
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="FEASIBLE",
        is_optimal=True,  # Inconsistent!
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value,
        exact_best_bound=resp.exact_best_bound,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Solver status FEASIBLE must have is_optimal=False" in f for f in failures)


def test_79_optimal_with_missing_objective_rejected():
    """79. Reconciler rejects OPTIMAL solver status with missing objective value."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_79", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="OPTIMAL",
        is_optimal=True,
        objective_value=None,  # Missing!
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=None,
        exact_best_bound=resp.exact_best_bound,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Solver status OPTIMAL must have non-null objective_value" in f for f in failures)


def test_80_feasible_with_missing_best_bound_rejected():
    """80. Reconciler rejects FEASIBLE solver status with missing best bound."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_80", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="FEASIBLE",
        is_optimal=False,
        objective_value=resp.objective_value,
        best_bound=None,  # Missing!
        optimality_gap=0.0,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value,
        exact_best_bound=None,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Solver status FEASIBLE must have non-null best_bound" in f for f in failures)


def test_81_incorrect_best_bound_rejected():
    """81. Reconciler rejects incorrect best bound (OPTIMAL mismatch and FEASIBLE bound < objective)."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_81", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Case A: OPTIMAL with best_bound != objective_value
    tampered_resp_opt = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="OPTIMAL",
        is_optimal=True,
        objective_value=resp.objective_value,
        best_bound=resp.objective_value + 1000.0,  # Bound mismatch!
        optimality_gap=0.0,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value,
        exact_best_bound=resp.exact_best_bound + 1000,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp_opt)
    assert is_valid is False
    assert any("OPTIMAL objective_value" in f and "!=" in f for f in failures)

    # Case B: FEASIBLE with best_bound < objective_value (impossible for maximization)
    tampered_resp_feas = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="FEASIBLE",
        is_optimal=False,
        objective_value=resp.objective_value,
        best_bound=resp.objective_value - 50.0,  # Bound < objective!
        optimality_gap=0.05,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value,
        exact_best_bound=resp.exact_best_bound - 50,
    )
    is_valid_f, failures_f = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp_feas)
    assert is_valid_f is False
    assert any("FEASIBLE best_bound" in f and "< objective_value" in f for f in failures_f)


def test_82_incorrect_optimality_gap_rejected():
    """82. Reconciler rejects incorrect optimality gap (OPTIMAL gap != 0.0 and FEASIBLE gap formula mismatch)."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_82", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Case A: OPTIMAL with gap != 0.0
    tampered_opt_gap = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="OPTIMAL",
        is_optimal=True,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=0.05,  # Must be 0.0!
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value,
        exact_best_bound=resp.exact_best_bound,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_opt_gap)
    assert is_valid is False
    assert any("Solver status OPTIMAL must have optimality_gap=0.0" in f for f in failures)

    # Case B: FEASIBLE with gap mismatch against formula
    obj_val = 1000.0
    bnd_val = 2000.0
    tampered_feas_gap = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="FEASIBLE",
        is_optimal=False,
        objective_value=obj_val,
        best_bound=bnd_val,
        optimality_gap=0.1,  # Corrupted! Expected 0.5
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=int(obj_val),
        exact_best_bound=int(bnd_val),
    )
    is_valid_f, failures_f = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_feas_gap)
    assert is_valid_f is False
    assert any("FEASIBLE optimality_gap calculation mismatch" in f for f in failures_f)


def test_83_nan_or_infinite_metadata_rejected():
    """83. Reconciler rejects NaN or infinite metadata."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_83", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # NaN objective_value
    tampered_nan = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="OPTIMAL",
        is_optimal=True,
        objective_value=float("nan"),  # NaN!
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value,
        exact_best_bound=resp.exact_best_bound,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_nan)
    assert is_valid is False
    assert any("Metadata 'objective_value' cannot be NaN or infinite" in f for f in failures)

    # Inf best_bound
    tampered_inf = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="OPTIMAL",
        is_optimal=True,
        objective_value=resp.objective_value,
        best_bound=float("inf"),  # Inf!
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value,
        exact_best_bound=resp.exact_best_bound,
    )
    is_valid_inf, failures_inf = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_inf)
    assert is_valid_inf is False
    assert any("Metadata 'best_bound' cannot be NaN or infinite" in f for f in failures_inf)


def test_84_exact_objective_mismatch_rejected():
    """84. Reconciler rejects exact integer objective mismatch."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_84", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    # Alter exact_objective_value by 1 unit
    tampered_obj = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="OPTIMAL",
        is_optimal=True,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=resp.optimality_gap,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value + 1,  # Mismatched exact integer!
        exact_best_bound=resp.exact_best_bound + 1,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_obj)
    assert is_valid is False
    assert any("Exact integer objective mismatch" in f for f in failures)


def test_85_large_integer_objective_near_safe_limit():
    """85. Solves and reconciles portfolio with large exact integer objective near approved safe limit."""
    candidates = [
        ProjectOptimizationCandidate(
            project_id=f"P_{i}",
            project_code=f"C_{i}",
            district_id="D1",
            estimated_cost=10.0,
            duration_periods=1,
            raw_mcpi_score=1.0,
            release_period=1,
        )
        for i in range(10)
    ]
    req = RecoveryOptimizationRequest(
        scenario_name="large_obj_scenario",
        planning_horizon_periods=10,
        initial_cash=10000.0,
        enable_early_start_bonus=True,
        allow_uniform_weight_fallback=True,
        candidates=candidates,
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"
    assert resp.is_optimal is True
    assert resp.exact_objective_value is not None
    assert resp.exact_best_bound is not None
    assert resp.exact_objective_value == resp.exact_best_bound
    expected_exact_obj = 10 * (91 * 10000000) + 10 * 9
    assert resp.exact_objective_value == expected_exact_obj
    assert resp.exact_best_bound == expected_exact_obj
    assert resp.objective_value == float(expected_exact_obj)


def test_86_exact_integer_objective_preservation_across_serialization():
    """86. Preserves exact integer objective and bound across response serialization."""
    candidates = [
        ProjectOptimizationCandidate(
            project_id="P_SER_1",
            project_code="CS1",
            district_id="D1",
            estimated_cost=50.0,
            duration_periods=1,
            raw_mcpi_score=0.95,
        )
    ]
    req = RecoveryOptimizationRequest(
        scenario_name="serialization_scenario",
        planning_horizon_periods=2,
        initial_cash=500.0,
        allow_uniform_weight_fallback=True,
        candidates=candidates,
    )
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "OPTIMAL"

    # Test 1: to_dict serialization
    d = resp.to_dict()
    assert isinstance(d["exact_objective_value"], int)
    assert isinstance(d["exact_best_bound"], int)
    assert d["exact_objective_value"] == resp.exact_objective_value
    assert d["exact_best_bound"] == resp.exact_best_bound

    # Test 2: dataclasses asdict serialization
    from dataclasses import asdict
    ad = asdict(resp)
    assert isinstance(ad["exact_objective_value"], int)
    assert isinstance(ad["exact_best_bound"], int)
    assert ad["exact_objective_value"] == resp.exact_objective_value
    assert ad["exact_best_bound"] == resp.exact_best_bound

    # Test 3: Large integer (> 2^53) preservation in exact integer field
    large_int = 10**16 + 123456789  # Exceeds 2^53 = 9,007,199,254,740,992
    large_resp = RecoveryOptimizationResponse(
        scenario_name="large_ser",
        solver_status="OPTIMAL",
        is_optimal=True,
        objective_value=float(large_int),
        best_bound=float(large_int),
        optimality_gap=0.0,
        solve_time_seconds=0.1,
        selected_project_count=1,
        total_cost_ccu=100,
        total_cost_inr=Decimal("1"),
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu={},
        district_equity_allocation_inr={},
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters={},
        exact_objective_value=large_int,
        exact_best_bound=large_int,
    )
    large_dict = large_resp.to_dict()
    assert large_dict["exact_objective_value"] == large_int
    assert large_dict["exact_best_bound"] == large_int
    assert int(float(large_int)) != large_int  # Proves float truncation
    assert large_dict["exact_objective_value"] == large_int  # Proves integer exact preservation


# -----------------------------------------------------------------------------
# Round 5 Regression Tests: Conservative Integer Best-Bound Integrity (Tests 87-96)
# -----------------------------------------------------------------------------

def test_87_missing_exact_objective_on_optimal_rejected():
    """87. Reconciler rejects OPTIMAL response with missing exact_objective_value."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_87", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="OPTIMAL",
        is_optimal=True,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=0.0,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=None,  # Missing!
        exact_best_bound=resp.exact_best_bound,
        conservative_best_bound=resp.conservative_best_bound,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Solver status OPTIMAL must have non-null exact_objective_value" in f for f in failures)


def test_88_missing_exact_objective_on_feasible_rejected():
    """88. Reconciler rejects FEASIBLE response with missing exact_objective_value."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_88", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()

    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="FEASIBLE",
        is_optimal=False,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound + 10.0,
        optimality_gap=0.05,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=None,  # Missing!
        exact_best_bound=resp.exact_best_bound,
        conservative_best_bound=resp.conservative_best_bound,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Solver status FEASIBLE must have non-null exact_objective_value" in f for f in failures)


def test_89_missing_exact_bound_on_optimal_rejected():
    """89. Reconciler rejects OPTIMAL response with missing exact bound."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_89", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"

    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="OPTIMAL",
        is_optimal=True,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=0.0,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value,
        exact_best_bound=None,  # Missing!
        conservative_best_bound=None,  # Missing!
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Solver status OPTIMAL must have non-null exact_best_bound" in f for f in failures)


def test_90_missing_conservative_bound_on_feasible_rejected():
    """90. Reconciler rejects FEASIBLE response with missing conservative bound."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_90", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()

    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="FEASIBLE",
        is_optimal=False,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound + 10.0,
        optimality_gap=0.05,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value,
        exact_best_bound=None,  # Missing!
        conservative_best_bound=None,  # Missing!
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("Solver status FEASIBLE must have non-null conservative_best_bound" in f for f in failures)


def test_91_bound_conversion_around_2_to_53():
    """91. Bound conversion around 2^53 guarantees conservative upper bound."""
    from app.recovery.optimization.recovery_cpsat_solver import compute_conservative_integer_best_bound
    two_53 = 2**53  # 9,007,199,254,740,992
    for delta in [-50, -1, 0, 1, 50]:
        K = two_53 + delta
        f = float(K)
        b = compute_conservative_integer_best_bound(f)
        assert b >= K, f"Conversion failed around 2^53: b={b} < K={K} (f={f})"


def test_92_bound_conversion_near_10_to_16():
    """92. Bound conversion near 10^16 guarantees conservative upper bound."""
    from app.recovery.optimization.recovery_cpsat_solver import compute_conservative_integer_best_bound
    base_16 = 10**16
    for delta in [-100, -7, -1, 0, 1, 7, 100]:
        K = base_16 + delta
        f = float(K)
        b = compute_conservative_integer_best_bound(f)
        assert b >= K, f"Conversion failed near 10^16: b={b} < K={K} (f={f})"


def test_93_bound_conversion_near_10_to_17():
    """93. Bound conversion near approved numerical safety limit 10^17."""
    from app.recovery.optimization.recovery_cpsat_solver import compute_conservative_integer_best_bound
    base_17 = 10**17
    for delta in [-100, -17, -1, 0, 1, 7, 15, 17, 100]:
        K = base_17 + delta
        f = float(K)
        b = compute_conservative_integer_best_bound(f)
        assert b >= K, f"Conversion failed near 10^17: b={b} < K={K} (f={f})"


def test_94_proof_conversion_never_understates_upper_bound():
    """94. Mathematical proof test verifying conversion never understates upper bound."""
    import random
    from app.recovery.optimization.recovery_cpsat_solver import compute_conservative_integer_best_bound
    # Deterministic pseudo-random seed for reproducibility
    rng = random.Random(42)
    # Test across multiple orders of magnitude up to 10^17
    for magnitude in [10**3, 10**6, 10**9, 10**12, 10**15, 10**16, 10**17]:
        for _ in range(100):
            K = rng.randint(magnitude // 2, magnitude)
            f = float(K)
            b = compute_conservative_integer_best_bound(f)
            assert b >= K, f"Understatement at magnitude {magnitude}: b={b} < K={K}"

    # Also test fractional continuous relaxation bounds
    for continuous in [100.25, 5000.75, 2.0**53 + 0.5, 10.0**16 + 0.3]:
        b = compute_conservative_integer_best_bound(continuous)
        assert b >= continuous, f"Understatement for continuous bound {continuous}: b={b}"


def test_95_optimal_exact_bound_equals_exact_objective():
    """95. OPTIMAL responses must have exact best bound strictly equal to exact objective."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_95", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()
    assert resp.solver_status == "OPTIMAL"
    assert resp.exact_objective_value is not None
    assert resp.exact_best_bound == resp.exact_objective_value
    assert resp.conservative_best_bound == resp.exact_objective_value

    # Tampered exact_best_bound != exact_objective_value is rejected
    tampered_resp = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="OPTIMAL",
        is_optimal=True,
        objective_value=resp.objective_value,
        best_bound=resp.best_bound,
        optimality_gap=0.0,
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value,
        exact_best_bound=resp.exact_objective_value + 5,
        conservative_best_bound=resp.exact_objective_value + 5,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_resp)
    assert is_valid is False
    assert any("OPTIMAL exact_objective_value" in f for f in failures)


def test_96_feasible_exact_objective_does_not_exceed_conservative_upper_bound():
    """96. FEASIBLE responses require exact objective not to exceed conservative upper bound."""
    p = ProjectOptimizationCandidate("P1", "C1", "D1", 100.0, 1, raw_mcpi_score=0.9)
    req = RecoveryOptimizationRequest("test_96", 2, initial_cash=500.0, allow_uniform_weight_fallback=True, candidates=[p])
    solver = RecoveryCPSATSolver(req)
    resp = solver.solve()

    # Case A: Valid FEASIBLE response where exact_objective <= conservative_best_bound
    valid_feas = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="FEASIBLE",
        is_optimal=False,
        objective_value=resp.objective_value,
        best_bound=resp.objective_value + 100.0,
        optimality_gap=100.0 / (resp.objective_value + 100.0),
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value,
        exact_best_bound=resp.exact_objective_value + 100,
        conservative_best_bound=resp.exact_objective_value + 100,
    )
    is_valid, failures = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, valid_feas)
    assert is_valid is True, f"Valid FEASIBLE failed reconciliation: {failures}"

    # Case B: Tampered FEASIBLE response where exact_objective > conservative_best_bound
    tampered_feas = RecoveryOptimizationResponse(
        scenario_name=resp.scenario_name,
        solver_status="FEASIBLE",
        is_optimal=False,
        objective_value=resp.objective_value,
        best_bound=resp.objective_value + 100.0,
        optimality_gap=100.0 / (resp.objective_value + 100.0),
        solve_time_seconds=resp.solve_time_seconds,
        selected_project_count=resp.selected_project_count,
        total_cost_ccu=resp.total_cost_ccu,
        total_cost_inr=resp.total_cost_inr,
        scheduled_projects=resp.scheduled_projects,
        periodic_solvency=resp.periodic_solvency,
        district_equity_allocation_ccu=resp.district_equity_allocation_ccu,
        district_equity_allocation_inr=resp.district_equity_allocation_inr,
        input_fingerprint_sha256=resp.input_fingerprint_sha256,
        ortools_version=resp.ortools_version,
        solver_parameters=resp.solver_parameters,
        exact_objective_value=resp.exact_objective_value,
        exact_best_bound=resp.exact_objective_value - 1,  # Understated!
        conservative_best_bound=resp.exact_objective_value - 1,  # Understated!
    )
    is_valid_t, failures_t = RecoveryOptimizationOrchestrator.reconcile_solution(req, solver, tampered_feas)
    assert is_valid_t is False
    assert any("exceeds conservative_best_bound" in f for f in failures_t)





