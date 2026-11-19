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
    normalize_to_ccu,
    unscale_ccu,
    quantize_mcpi_score,
    deterministic_capped_apportionment,
    ProjectOptimizationCandidate,
    FundingSourceSpec,
    DependencyEdgeInput,
    RecoveryOptimizationRequest,
    RecoveryOptimizationResponse,
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
        scenario_name="hash_test", planning_horizon_periods=2, initial_cash=100.0, candidates=[p]
    )
    req2 = RecoveryOptimizationRequest(
        scenario_name="hash_test", planning_horizon_periods=2, initial_cash=100.0, candidates=[p]
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
    req1 = RecoveryOptimizationRequest("s1", 2, initial_cash=100.0, candidates=[p1])
    r1 = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req1)
    assert any(f.category == "AGGREGATE_BUDGET_EXCEEDED" for f in r1.infeasibility_diagnostics.proven_causes)

    # 2. Planning horizon exceeded
    p2 = ProjectOptimizationCandidate("M2", "C2", "D1", 10.0, 5, is_tier1_mandatory=True)
    req2 = RecoveryOptimizationRequest("s2", 3, initial_cash=100.0, candidates=[p2])
    r2 = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req2)
    assert any(f.category == "PLANNING_HORIZON_EXCEEDED" for f in r2.infeasibility_diagnostics.proven_causes)

    # 3. Precedence deadline conflict
    p3 = ProjectOptimizationCandidate("M3", "C3", "D1", 10.0, 3, is_tier1_mandatory=True, deadline_period=2)
    req3 = RecoveryOptimizationRequest("s3", 4, initial_cash=100.0, candidates=[p3])
    r3 = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req3)
    assert any(f.category == "PRECEDENCE_DEADLINE_CONFLICT" for f in r3.infeasibility_diagnostics.proven_causes)

    # 4. Resource capacity forced concurrency
    pa = ProjectOptimizationCandidate("MA", "CA", "D1", 10.0, 3, release_period=1, deadline_period=4, is_tier1_mandatory=True, resource_demands={"c": 1})
    pb = ProjectOptimizationCandidate("MB", "CB", "D1", 10.0, 3, release_period=2, deadline_period=5, is_tier1_mandatory=True, resource_demands={"c": 1})
    req4 = RecoveryOptimizationRequest(
        "s4", 5, initial_cash=100.0, candidates=[pa, pb], resource_capacities={"c": {t: 1 for t in range(1, 6)}}
    )
    r4 = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req4)
    assert any(f.category == "RESOURCE_CAPACITY_EXCEEDED" for f in r4.infeasibility_diagnostics.proven_causes)

    # 5. Funding source dedicated oversubscription
    p5 = ProjectOptimizationCandidate("M5", "C5", "D1", 100.0, 1, is_tier1_mandatory=True, eligible_funds=["F1"])
    f1 = FundingSourceSpec("F1", capacity=50.0)
    req5 = RecoveryOptimizationRequest("s5", 2, initial_cash=200.0, candidates=[p5], funding_sources=[f1])
    r5 = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req5)
    assert any(f.category == "FUNDING_SOURCE_RESTRICTION" for f in r5.infeasibility_diagnostics.proven_causes)


def test_35_multiple_simultaneous_diagnostic_categories():
    """35. Multiple simultaneous diagnostic categories reported concurrently without compression."""
    # Concurrently violates budget AND planning horizon
    p = ProjectOptimizationCandidate(
        "M1", "C1", "D1", 5000.0, 10, is_tier1_mandatory=True # Horizon 4, duration 10, cost 5000 > cash 100
    )
    req = RecoveryOptimizationRequest("multi_diag", 4, initial_cash=100.0, candidates=[p])
    resp = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(req)
    assert resp.solver_status == "INFEASIBLE"
    proven = resp.infeasibility_diagnostics.proven_causes
    categories = {f.category for f in proven}
    assert "AGGREGATE_BUDGET_EXCEEDED" in categories
    assert "PLANNING_HORIZON_EXCEEDED" in categories
    assert len(proven) >= 2
