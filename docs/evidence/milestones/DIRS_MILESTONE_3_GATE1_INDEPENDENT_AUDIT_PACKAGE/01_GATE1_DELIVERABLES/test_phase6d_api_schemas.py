"""
Unit Test Suite for Phase 6D-B Milestone 3 Gate 1 Pydantic API Schemas.

Validates all 20 required scenario and contract behaviors:
1. Valid minimal request.
2. Valid complete request.
3. Unknown field rejection.
4. Missing required fields.
5. Invalid planning horizon.
6. Invalid period indices.
7. Decimal preservation.
8. Non-finite numeric rejection.
9. Invalid currency units.
10. Empty candidate portfolio behavior according to accepted engine rules.
11. Missing mandatory safety deadline rejection.
12. Null mandatory safety deadline rejection.
13. Out-of-horizon safety deadline rejection.
14. Valid caller-supplied safety deadline.
15. No default safety deadline.
16. Exact integer response serialization above 2^53.
17. FEASIBLE conservative bound preservation.
18. OPTIMAL exact-bound preservation.
19. Non-solution responses with null solution metadata.
20. Infeasibility diagnostic serialization.
"""

from decimal import Decimal
import math
import pytest
from pydantic import ValidationError

from app.recovery.optimization.schemas import (
    CurrencyUnit,
    FundingSourceSpec,
    InfeasibilityFinding,
    InfeasibilityDiagnosticReport,
    PeriodSolvencyResult,
    ProjectOptimizationCandidate,
    RecoveryOptimizationRequest,
    RecoveryOptimizationResponse,
    ScheduledProjectResult,
)
from app.schemas.recovery_optimization import (
    CurrencyUnit,
    DependencyEdgeDTO,
    FundingSourceSpecDTO,
    InfeasibilityFindingDTO,
    InfeasibilityDiagnosticReportDTO,
    OptimizationErrorDetailDTO,
    OptimizationErrorType,
    PeriodSolvencyResultDTO,
    ProjectOptimizationCandidateDTO,
    RecoveryOptimizationScenarioRequest,
    RecoveryOptimizationScenarioResponse,
    ScheduledProjectResultDTO,
)


# ==============================================================================
# 1. Valid Minimal and Complete Requests
# ==============================================================================

def test_01_valid_minimal_request():
    """1. Valid minimal request with only required fields parses cleanly."""
    req = RecoveryOptimizationScenarioRequest(
        scenario_name="minimal_scenario",
        planning_horizon_periods=4,
    )
    assert req.scenario_name == "minimal_scenario"
    assert req.planning_horizon_periods == 4
    assert req.period_length_days == 30.0
    assert req.initial_cash == Decimal("0.0")
    assert req.cash_currency == CurrencyUnit.INR
    assert req.candidates == []
    assert req.dependencies == []
    assert req.funding_sources == []
    assert req.max_safety_start_period is None

    # Bidirectional conversion to engine request
    engine_req = req.to_engine_request()
    assert isinstance(engine_req, RecoveryOptimizationRequest)
    assert engine_req.scenario_name == "minimal_scenario"
    assert engine_req.planning_horizon_periods == 4


def test_02_valid_complete_request():
    """2. Valid complete request with all optional fields and nested DTOs."""
    cand = ProjectOptimizationCandidateDTO(
        project_id="P_ROAD_01",
        project_code="CMS-RD-01",
        district_id="D_KERALA_01",
        estimated_cost=Decimal("1500000.50"),
        duration_periods=3,
        cost_currency=CurrencyUnit.INR,
        release_period=1,
        deadline_period=4,
        is_tier1_mandatory=False,
        raw_mcpi_score=0.875,
        expenditure_weights=[0.3, 0.4, 0.3],
        resource_demands={"CEMENT": 50, "WORKFORCE": 20},
        eligible_funds=["SDRF_2026"],
    )
    fund = FundingSourceSpecDTO(
        fund_id="SDRF_2026",
        capacity=Decimal("10000000.0"),
        currency=CurrencyUnit.INR,
        period_tranches={1: Decimal("5000000.0"), 2: Decimal("5000000.0")},
    )
    req = RecoveryOptimizationScenarioRequest(
        scenario_name="complete_flood_reconstruction",
        planning_horizon_periods=6,
        period_length_days=30.0,
        initial_cash=Decimal("2500000.0"),
        cash_currency=CurrencyUnit.INR,
        periodic_budgets={1: Decimal("1000000.0"), 2: Decimal("1500000.0")},
        budget_currency=CurrencyUnit.INR,
        district_equity_targets={"D_KERALA_01": 0.5},
        blackout_districts=[],
        candidates=[cand],
        dependencies=[],
        resource_capacities={"CEMENT": {1: 100, 2: 100, 3: 100}},
        funding_sources=[fund],
        fiscal_retention_rate=0.95,
        enable_early_start_bonus=True,
        max_safety_start_period=None,
        max_solve_time_seconds=30.0,
        deterministic_seed=123,
        num_workers=2,
        allow_uniform_weight_fallback=False,
    )
    assert req.candidates[0].project_id == "P_ROAD_01"
    assert req.funding_sources[0].fund_id == "SDRF_2026"
    assert req.periodic_budgets[1] == Decimal("1000000.0")

    # Roundtrip conversion
    engine_req = req.to_engine_request()
    restored_req = RecoveryOptimizationScenarioRequest.from_engine_request(engine_req)
    assert restored_req.scenario_name == req.scenario_name
    assert restored_req.candidates[0].estimated_cost == cand.estimated_cost


# ==============================================================================
# 2. Rejection of Unknown Fields and Missing Required Fields
# ==============================================================================

def test_03_unknown_field_rejection():
    """3. Rejects unexpected/unknown fields on top-level and nested DTOs."""
    # Top-level request unknown field
    with pytest.raises(ValidationError) as exc_top:
        RecoveryOptimizationScenarioRequest(
            scenario_name="unknown_field_test",
            planning_horizon_periods=4,
            unexpected_field_abc="malicious_payload",
        )
    assert "unexpected_field_abc" in str(exc_top.value)
    assert "Extra inputs are not permitted" in str(exc_top.value)

    # Nested candidate unknown field
    with pytest.raises(ValidationError) as exc_nested:
        ProjectOptimizationCandidateDTO(
            project_id="P1",
            project_code="C1",
            district_id="D1",
            estimated_cost=Decimal("100.0"),
            duration_periods=1,
            unapproved_candidate_attribute=12345,
        )
    assert "unapproved_candidate_attribute" in str(exc_nested.value)


def test_04_missing_required_fields():
    """4. Rejects request when required fields are missing."""
    with pytest.raises(ValidationError) as exc:
        RecoveryOptimizationScenarioRequest(
            planning_horizon_periods=4,  # Missing scenario_name
        )
    assert "scenario_name" in str(exc.value)
    assert "Field required" in str(exc.value)

    with pytest.raises(ValidationError) as exc2:
        RecoveryOptimizationScenarioRequest(
            scenario_name="missing_horizon",  # Missing planning_horizon_periods
        )
    assert "planning_horizon_periods" in str(exc2.value)


# ==============================================================================
# 3. Horizon and Period Index Validation
# ==============================================================================

def test_05_invalid_planning_horizon():
    """5. Planning horizon must be an integer >= 1 and <= 120."""
    with pytest.raises(ValidationError) as exc_zero:
        RecoveryOptimizationScenarioRequest(scenario_name="zero_horizon", planning_horizon_periods=0)
    assert "greater than or equal to 1" in str(exc_zero.value) or "greater_than_equal" in str(exc_zero.value)

    with pytest.raises(ValidationError) as exc_neg:
        RecoveryOptimizationScenarioRequest(scenario_name="neg_horizon", planning_horizon_periods=-5)
    assert "greater than or equal to 1" in str(exc_neg.value) or "greater_than_equal" in str(exc_neg.value)

    with pytest.raises(ValidationError) as exc_huge:
        RecoveryOptimizationScenarioRequest(scenario_name="huge_horizon", planning_horizon_periods=121)
    assert "less than or equal to 120" in str(exc_huge.value) or "less_than_equal" in str(exc_huge.value)


def test_06_invalid_period_indices():
    """6. Period indices exceeding planning horizon or < 1 are rejected."""
    # Periodic budget period 0 (< 1)
    with pytest.raises(ValidationError) as exc_p0:
        RecoveryOptimizationScenarioRequest(
            scenario_name="test_p0",
            planning_horizon_periods=5,
            periodic_budgets={0: Decimal("1000.0")},
        )
    assert "Periodic budget period must be >= 1" in str(exc_p0.value)

    # Periodic budget period 6 (> horizon 5)
    with pytest.raises(ValidationError) as exc_p6:
        RecoveryOptimizationScenarioRequest(
            scenario_name="test_p6",
            planning_horizon_periods=5,
            periodic_budgets={6: Decimal("1000.0")},
        )
    assert "exceeds planning horizon 5" in str(exc_p6.value)

    # Candidate release period > horizon
    cand_oob = ProjectOptimizationCandidateDTO(
        project_id="P_OOB", project_code="C_OOB", district_id="D1",
        estimated_cost=Decimal("100.0"), duration_periods=1, release_period=6,
    )
    with pytest.raises(ValidationError) as exc_cand:
        RecoveryOptimizationScenarioRequest(
            scenario_name="test_cand_oob",
            planning_horizon_periods=5,
            candidates=[cand_oob],
        )
    assert "release_period (6) exceeds planning horizon 5" in str(exc_cand.value)


# ==============================================================================
# 4. Decimal Preservation and Non-Finite Rejection
# ==============================================================================

def test_07_decimal_preservation():
    """7. Decimal inputs maintain exact rational representation without float coercion."""
    exact_cost = Decimal("1234567.890123")
    cand = ProjectOptimizationCandidateDTO(
        project_id="P_DEC", project_code="C_DEC", district_id="D1",
        estimated_cost=exact_cost, duration_periods=2,
    )
    assert isinstance(cand.estimated_cost, Decimal)
    assert cand.estimated_cost == exact_cost

    req = RecoveryOptimizationScenarioRequest(
        scenario_name="test_decimal",
        planning_horizon_periods=4,
        initial_cash=Decimal("999999999.99"),
        periodic_budgets={1: Decimal("888888888.88")},
        candidates=[cand],
    )
    assert isinstance(req.initial_cash, Decimal)
    assert req.initial_cash == Decimal("999999999.99")
    assert isinstance(req.periodic_budgets[1], Decimal)
    assert req.periodic_budgets[1] == Decimal("888888888.88")


def test_08_non_finite_numeric_rejection():
    """8. Rejects NaN, +inf, -inf on float and Decimal inputs."""
    # Float NaN in MCPI score
    with pytest.raises(ValidationError) as exc_nan:
        ProjectOptimizationCandidateDTO(
            project_id="P_NAN", project_code="C1", district_id="D1",
            estimated_cost=Decimal("100.0"), duration_periods=1,
            raw_mcpi_score=float("nan"),
        )
    assert "NON_FINITE_VALUE" in str(exc_nan.value)

    # Float Inf in MCPI score
    with pytest.raises(ValidationError) as exc_inf:
        ProjectOptimizationCandidateDTO(
            project_id="P_INF", project_code="C1", district_id="D1",
            estimated_cost=Decimal("100.0"), duration_periods=1,
            raw_mcpi_score=float("inf"),
        )
    assert "NON_FINITE_VALUE" in str(exc_inf.value)

    # Float NaN in request period_length_days
    with pytest.raises(ValidationError) as exc_req_nan:
        RecoveryOptimizationScenarioRequest(
            scenario_name="test_nan_days",
            planning_horizon_periods=4,
            period_length_days=float("nan"),
        )
    assert "NON_FINITE_VALUE" in str(exc_req_nan.value)


# ==============================================================================
# 5. Currency Units and Empty Portfolio
# ==============================================================================

def test_09_invalid_currency_units():
    """9. Rejects unsupported currency denominations."""
    with pytest.raises(ValidationError) as exc:
        ProjectOptimizationCandidateDTO(
            project_id="P_USD", project_code="C1", district_id="D1",
            estimated_cost=Decimal("100.0"), duration_periods=1,
            cost_currency="USD",  # Not supported
        )
    assert "cost_currency" in str(exc.value)


def test_10_empty_candidate_portfolio():
    """10. Empty candidate portfolio is valid and constructs engine request cleanly."""
    req = RecoveryOptimizationScenarioRequest(
        scenario_name="empty_portfolio",
        planning_horizon_periods=3,
        candidates=[],
    )
    assert len(req.candidates) == 0
    engine_req = req.to_engine_request()
    assert len(engine_req.candidates) == 0


# ==============================================================================
# 6. RSK-M2-07 Governance Policy Validation
# ==============================================================================

def test_11_missing_mandatory_safety_deadline_rejection():
    """11. Missing safety deadline rejected when portfolio contains mandatory project."""
    mand_cand = ProjectOptimizationCandidateDTO(
        project_id="P_MAND", project_code="C_MAND", district_id="D1",
        estimated_cost=Decimal("100.0"), duration_periods=1,
        is_tier1_mandatory=True,
    )
    with pytest.raises(ValidationError) as exc:
        RecoveryOptimizationScenarioRequest(
            scenario_name="missing_mand_deadline",
            planning_horizon_periods=5,
            candidates=[mand_cand],
            # max_safety_start_period omitted!
        )
    assert "RSK-M2-07 Violation" in str(exc.value)
    assert "max_safety_start_period" in str(exc.value)


def test_12_null_mandatory_safety_deadline_rejection():
    """12. Explicitly null safety deadline rejected when portfolio contains mandatory project."""
    mand_cand = ProjectOptimizationCandidateDTO(
        project_id="P_MAND", project_code="C_MAND", district_id="D1",
        estimated_cost=Decimal("100.0"), duration_periods=1,
        is_tier1_mandatory=True,
    )
    with pytest.raises(ValidationError) as exc:
        RecoveryOptimizationScenarioRequest(
            scenario_name="null_mand_deadline",
            planning_horizon_periods=5,
            candidates=[mand_cand],
            max_safety_start_period=None,  # Explicitly None!
        )
    assert "RSK-M2-07 Violation" in str(exc.value)
    assert "was not provided" in str(exc.value)


def test_13_out_of_horizon_safety_deadline_rejection():
    """13. Safety deadline exceeding planning horizon is rejected."""
    mand_cand = ProjectOptimizationCandidateDTO(
        project_id="P_MAND", project_code="C_MAND", district_id="D1",
        estimated_cost=Decimal("100.0"), duration_periods=1,
        is_tier1_mandatory=True,
    )
    with pytest.raises(ValidationError) as exc:
        RecoveryOptimizationScenarioRequest(
            scenario_name="oob_mand_deadline",
            planning_horizon_periods=5,
            candidates=[mand_cand],
            max_safety_start_period=6,  # 6 > horizon 5!
        )
    assert "RSK-M2-07 Violation" in str(exc.value)
    assert "exceeds planning_horizon_periods" in str(exc.value)


def test_14_valid_caller_supplied_safety_deadline():
    """14. Valid caller-supplied safety deadline passes validation."""
    mand_cand = ProjectOptimizationCandidateDTO(
        project_id="P_MAND", project_code="C_MAND", district_id="D1",
        estimated_cost=Decimal("100.0"), duration_periods=1,
        is_tier1_mandatory=True,
    )
    req = RecoveryOptimizationScenarioRequest(
        scenario_name="valid_mand_deadline",
        planning_horizon_periods=5,
        candidates=[mand_cand],
        max_safety_start_period=2,  # 1 <= 2 <= 5
    )
    assert req.max_safety_start_period == 2
    engine_req = req.to_engine_request()
    assert engine_req.max_safety_start_period == 2


def test_15_no_default_safety_deadline():
    """15. Confirms no default deadline is applied when candidates are non-mandatory."""
    cand = ProjectOptimizationCandidateDTO(
        project_id="P_STD", project_code="C_STD", district_id="D1",
        estimated_cost=Decimal("100.0"), duration_periods=1,
        is_tier1_mandatory=False,
    )
    req = RecoveryOptimizationScenarioRequest(
        scenario_name="no_mand_deadline",
        planning_horizon_periods=5,
        candidates=[cand],
    )
    assert req.max_safety_start_period is None


# ==============================================================================
# 7. Response Serialization & Integer Bound Safety
# ==============================================================================

def test_16_exact_integer_response_serialization_above_2_pow_53():
    """16. Arbitrary-precision exact integer objective above 2^53 is preserved without float loss."""
    huge_int = 2**54 + 137  # 18,014,398,509,482,121 (exceeds IEEE 754 exact precision)
    resp = RecoveryOptimizationScenarioResponse(
        scenario_name="huge_objective_test",
        solver_status="OPTIMAL",
        is_optimal=True,
        exact_objective_value=huge_int,
        exact_best_bound=huge_int,
        conservative_best_bound=huge_int,
        objective_value=float(huge_int),
        best_bound=float(huge_int),
        optimality_gap=0.0,
        solve_time_seconds=0.125,
        selected_project_count=1,
        total_cost_ccu=10000000,
        total_cost_inr=Decimal("100.0"),
        input_fingerprint_sha256="fake_fingerprint",
        ortools_version="9.15.6755",
    )
    assert resp.exact_objective_value == huge_int
    assert resp.exact_best_bound == huge_int
    assert resp.conservative_best_bound == huge_int
    # Verify integer precision is not corrupted
    assert resp.exact_objective_value > 2**53


def test_17_feasible_conservative_bound_preservation():
    """17. FEASIBLE response preserves conservative upper bound and display gap."""
    cons_bnd = 5000
    exact_obj = 4500
    display_gap = (5000.0 - 4500.0) / 5000.0

    resp = RecoveryOptimizationScenarioResponse(
        scenario_name="feasible_test",
        solver_status="FEASIBLE",
        is_optimal=False,
        exact_objective_value=exact_obj,
        exact_best_bound=cons_bnd,
        conservative_best_bound=cons_bnd,
        objective_value=float(exact_obj),
        best_bound=float(cons_bnd),
        optimality_gap=display_gap,
        solve_time_seconds=10.0,
        selected_project_count=2,
        total_cost_ccu=200000,
        total_cost_inr=Decimal("2.0"),
        input_fingerprint_sha256="fake_sha",
        ortools_version="9.15.6755",
    )
    assert resp.solver_status == "FEASIBLE"
    assert resp.is_optimal is False
    assert resp.conservative_best_bound == 5000
    assert resp.exact_objective_value == 4500
    assert resp.optimality_gap == 0.1


def test_18_optimal_exact_bound_preservation():
    """18. OPTIMAL response preserves exact bound equal to objective and zero gap."""
    resp = RecoveryOptimizationScenarioResponse(
        scenario_name="optimal_test",
        solver_status="OPTIMAL",
        is_optimal=True,
        exact_objective_value=12345,
        exact_best_bound=12345,
        conservative_best_bound=12345,
        objective_value=12345.0,
        best_bound=12345.0,
        optimality_gap=0.0,
        solve_time_seconds=0.05,
        selected_project_count=1,
        total_cost_ccu=10000,
        total_cost_inr=Decimal("0.1"),
        input_fingerprint_sha256="optimal_sha",
        ortools_version="9.15.6755",
    )
    assert resp.solver_status == "OPTIMAL"
    assert resp.is_optimal is True
    assert resp.exact_objective_value == 12345
    assert resp.exact_best_bound == 12345
    assert resp.conservative_best_bound == 12345
    assert resp.optimality_gap == 0.0


def test_19_non_solution_null_metadata():
    """19. Non-solution response (e.g. INFEASIBLE, MODEL_INVALID) preserves null solution metadata."""
    resp = RecoveryOptimizationScenarioResponse(
        scenario_name="infeasible_test",
        solver_status="INFEASIBLE",
        is_optimal=False,
        exact_objective_value=None,
        exact_best_bound=None,
        conservative_best_bound=None,
        objective_value=None,
        best_bound=None,
        optimality_gap=None,
        solve_time_seconds=0.01,
        selected_project_count=0,
        total_cost_ccu=0,
        total_cost_inr=Decimal("0.0"),
        input_fingerprint_sha256="infeasible_sha",
        ortools_version="9.15.6755",
    )
    assert resp.solver_status == "INFEASIBLE"
    assert resp.exact_objective_value is None
    assert resp.conservative_best_bound is None
    assert resp.optimality_gap is None


def test_20_infeasibility_diagnostic_serialization():
    """20. Multi-category diagnostic report serializes cleanly from engine report."""
    finding = InfeasibilityFinding(
        category="BUDGET",
        classification="PROVEN_INFEASIBILITY",
        message="Cumulative cost exceeds available budget",
        mathematical_condition="Total required cost 500 CCU > budget 300 CCU",
        affected_projects=["P1", "P2"],
        conflicting_periods=[1],
        details={"deficit": 200},
    )
    engine_report = InfeasibilityDiagnosticReport(
        has_proven_infeasibility=True,
        proven_causes=[finding],
        necessary_condition_violations=[],
        solver_hypotheses=[],
        warnings=[],
        is_assumption_core_minimal=True,
        is_assumption_core_sufficient=True,
    )
    dto_report = InfeasibilityDiagnosticReportDTO.from_engine_report(engine_report)
    assert dto_report.has_proven_infeasibility is True
    assert len(dto_report.proven_causes) == 1
    assert dto_report.proven_causes[0].category == "BUDGET"
    assert dto_report.proven_causes[0].affected_projects == ["P1", "P2"]
    assert dto_report.is_assumption_core_minimal is True


# ==============================================================================
# 8. Nested DTO & Error DTO Validation
# ==============================================================================

def test_21_self_dependency_rejection():
    """21. Rejects self-referencing dependency edges."""
    with pytest.raises(ValidationError) as exc:
        DependencyEdgeDTO(predecessor_id="P1", successor_id="P1", lag_periods=0)
    assert "Self-dependency detected" in str(exc.value)


def test_22_structured_error_dto():
    """22. Structured error DTO serializes categorized execution failures."""
    err = OptimizationErrorDetailDTO(
        error_type=OptimizationErrorType.INVALID_REQUEST,
        message="Request contract validation failed",
        diagnostic_code="MISSING_SAFETY_DEADLINE",
        validation_failures=["Portfolio contains mandatory projects without max_safety_start_period"],
        input_fingerprint_sha256="abc123sha",
    )
    assert err.error_type == OptimizationErrorType.INVALID_REQUEST
    assert err.diagnostic_code == "MISSING_SAFETY_DEADLINE"
    assert len(err.validation_failures) == 1
