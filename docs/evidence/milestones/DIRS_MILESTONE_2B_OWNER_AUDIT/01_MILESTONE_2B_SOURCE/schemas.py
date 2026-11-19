"""
Recovery CP-SAT Optimization Engine Schemas and Dataclasses.

Phase 6D-B Milestone 2B Domain Contracts.
Establishes canonical currency scaling, integer conversion rules,
deterministic capped expenditure apportionment, input candidates,
and structured optimization responses.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from enum import Enum
from fractions import Fraction
import math
from typing import Any, Dict, List, Optional, Set, Union


class CurrencyUnit(str, Enum):
    """Explicit currency units supported by the optimization engine."""
    INR = "INR"
    LAKH_INR = "LAKH_INR"
    CRORE_INR = "CRORE_INR"


# Canonical Currency Unit: 1 CCU = 10^-5 INR (0.00001 INR)
CCU_PER_INR = Decimal("100000")          # 10^5 CCU per 1 INR
CCU_PER_LAKH = Decimal("10000000000")    # 10^10 CCU per 1 Lakh INR
CCU_PER_CRORE = Decimal("1000000000000") # 10^12 CCU per 1 Crore INR


def normalize_to_ccu(
    val: Union[Decimal, float, str, int],
    unit: Union[CurrencyUnit, str],
    rounding_mode: str = "floor",
) -> int:
    """
    Converts a source currency amount into exact integer Canonical Currency Units (CCU).
    1 CCU = 10^-5 INR.

    Directional Rounding Guarantee:
    - 'floor': ROUND_FLOOR (conservative for budget capacities, caps)
    - 'ceiling': ROUND_CEIL (conservative for project costs, equity floors)

    Uses decimal.Decimal to eliminate IEEE 754 binary floating-point representation artifacts.
    """
    if isinstance(val, (int, float, str)):
        d_val = Decimal(str(val))
    elif isinstance(val, Decimal):
        d_val = val
    else:
        raise TypeError(f"Unsupported value type for currency conversion: {type(val)}")

    if isinstance(unit, str):
        unit = CurrencyUnit(unit)

    if unit == CurrencyUnit.INR:
        multiplier = CCU_PER_INR
    elif unit == CurrencyUnit.LAKH_INR:
        multiplier = CCU_PER_LAKH
    elif unit == CurrencyUnit.CRORE_INR:
        multiplier = CCU_PER_CRORE
    else:
        raise ValueError(f"Unknown currency unit: {unit}")

    ccu_decimal = d_val * multiplier
    round_rule = ROUND_FLOOR if rounding_mode.lower() == "floor" else ROUND_CEILING
    return int(ccu_decimal.to_integral_value(rounding=round_rule))


def unscale_ccu(ccu: int, target_unit: Union[CurrencyUnit, str] = CurrencyUnit.INR) -> Decimal:
    """Unscales integer CCU back to target currency Decimal."""
    if isinstance(target_unit, str):
        target_unit = CurrencyUnit(target_unit)

    d_ccu = Decimal(ccu)
    if target_unit == CurrencyUnit.INR:
        return d_ccu / CCU_PER_INR
    elif target_unit == CurrencyUnit.LAKH_INR:
        return d_ccu / CCU_PER_LAKH
    elif target_unit == CurrencyUnit.CRORE_INR:
        return d_ccu / CCU_PER_CRORE
    else:
        raise ValueError(f"Unknown target currency unit: {target_unit}")


def quantize_mcpi_score(raw_score: float) -> int:
    """
    Quantizes raw continuous score in [0.0, 1.0] into integer CP-SAT objective coefficient:
    Pi_bar = floor(raw_score * 10^7).
    Guarantees strict error bound < 10^-7 and distinguishes raw differences >= 10^-7.
    """
    if raw_score < 0.0 or raw_score > 1.0:
        raise ValueError(f"Raw MCPI score must be in [0.0, 1.0], got {raw_score}")
    return int(math.floor(raw_score * 10_000_000))


def deterministic_capped_apportionment(
    cost_c: int,
    weights_w: List[Union[Fraction, float]],
    caps_e_bar: List[int],
    eligible_periods: Optional[Set[int]] = None,
    allow_uniform_fallback: bool = False,
) -> List[int]:
    """
    Apportions total integer capital cost_c (in CCU) across periods while strictly
    enforcing individual period expenditure caps caps_e_bar.

    Guarantees:
    1. Bounds: 0 <= e[tau] <= caps_e_bar[tau] for all tau in {0, ..., d-1}.
    2. Eligibility: e[tau] == 0 for all tau not in eligible_periods.
    3. Conservation: sum(e) == cost_c (if feasible).
    4. Deterministic Tie-Breaking: primary key is remainder descending,
       secondary deterministic key is ascending period index.
    5. Fail-Closed: Raises ValueError immediately if cost_c > sum(eligible caps)
       or if all eligible weights are zero (without allow_uniform_fallback=True).
    """
    d = len(weights_w)
    if len(caps_e_bar) != d:
        raise ValueError("Dimension mismatch between weights and period caps.")
    if cost_c < 0:
        raise ValueError("Project cost cannot be negative.")
    if any(c < 0 for c in caps_e_bar):
        raise ValueError("Period caps cannot be negative.")

    if eligible_periods is None:
        eligible_periods = set(range(1, d + 1))

    # Mask caps for ineligible periods to 0
    effective_caps = [
        caps_e_bar[i] if (i + 1) in eligible_periods else 0 for i in range(d)
    ]
    total_eligible_capacity = sum(effective_caps)

    # Fail-closed feasibility check (Theorem 1)
    if cost_c > total_eligible_capacity:
        raise ValueError(
            f"CAP_CAPACITY_EXCEEDED: required {cost_c} CCU exceeds aggregate "
            f"eligible capacity {total_eligible_capacity} CCU"
        )

    if cost_c == 0:
        return [0] * d

    # Convert weights to exact fractions
    frac_weights: List[Fraction] = []
    for w in weights_w:
        if isinstance(w, Fraction):
            frac_weights.append(w)
        else:
            frac_weights.append(Fraction(str(w)))

    sum_eligible_weights = sum(frac_weights[i] for i in range(d) if (i + 1) in eligible_periods)

    # Zero-weight governance
    if sum_eligible_weights == 0:
        if not allow_uniform_fallback:
            raise ValueError(
                "ZERO_ELIGIBLE_WEIGHTS: Cannot apportion non-zero capital cost "
                "when all eligible period weights are zero."
            )
        # Separately authorized uniform fallback
        frac_weights = [
            Fraction(1, 1) if (i + 1) in eligible_periods else Fraction(0, 1)
            for i in range(d)
        ]
        sum_eligible_weights = sum(frac_weights[i] for i in range(d) if (i + 1) in eligible_periods)

    # Exact rational targets
    targets = [
        (Fraction(cost_c * frac_weights[i], sum_eligible_weights) if (i + 1) in eligible_periods else Fraction(0, 1))
        for i in range(d)
    ]

    # Clamped integer base allocation: e_tau^(0) = min(floor(y_tau), cap_tau)
    e = [min(int(targets[i]), effective_caps[i]) for i in range(d)]

    slacks = [effective_caps[i] - e[i] for i in range(d)]
    deficit = cost_c - sum(e)

    # Candidate indices with positive slack
    candidate_indices = [
        i for i in range(d) if (i + 1) in eligible_periods and slacks[i] > 0
    ]

    # Deterministic priority ranking: (-remainder, period_index)
    candidate_indices.sort(
        key=lambda i: (-(targets[i] - Fraction(int(targets[i]), 1)), i)
    )

    # Water-filling redistribution
    while deficit > 0:
        progress = False
        for idx in list(candidate_indices):
            if deficit == 0:
                break
            if slacks[idx] > 0:
                e[idx] += 1
                slacks[idx] -= 1
                deficit -= 1
                progress = True
                if slacks[idx] == 0:
                    candidate_indices.remove(idx)
        if not progress:
            raise RuntimeError(f"Internal apportionment failure: unallocated deficit {deficit} CCU.")

    assert sum(e) == cost_c, "Conservation violated."
    assert all(0 <= e[i] <= effective_caps[i] for i in range(d)), "Period cap violated."
    assert all(e[i] == 0 for i in range(d) if (i + 1) not in eligible_periods), "Ineligible period received allocation."
    return e


@dataclass
class ProjectOptimizationCandidate:
    """Candidate recovery project input for CP-SAT optimization."""
    project_id: str
    project_code: str
    district_id: str
    estimated_cost: Union[Decimal, float, int]
    duration_periods: int
    cost_currency: CurrencyUnit = CurrencyUnit.INR
    release_period: int = 1
    deadline_period: Optional[int] = None
    is_tier1_mandatory: bool = False
    raw_mcpi_score: float = 0.0                      # in [0.0, 1.0]
    expenditure_weights: Optional[List[float]] = None # relative period weights sum to 1.0
    resource_demands: Dict[str, int] = field(default_factory=dict) # resource_id -> units/period
    eligible_funds: List[str] = field(default_factory=list)        # list of eligible fund IDs


@dataclass
class FundingSourceSpec:
    """Internal funding-policy source allocation specification (Model B Indivisible)."""
    fund_id: str
    capacity: Union[Decimal, float, int]
    currency: CurrencyUnit = CurrencyUnit.INR
    period_tranches: Optional[Dict[int, Union[Decimal, float, int]]] = None


@dataclass
class DependencyEdgeInput:
    """Directed precedence relationship between two recovery projects."""
    predecessor_id: str
    successor_id: str
    lag_periods: int = 0  # converted discrete period lag


@dataclass
class RecoveryOptimizationRequest:
    """Complete portfolio request contract for recovery optimization."""
    scenario_name: str
    planning_horizon_periods: int
    period_length_days: float = 30.0
    initial_cash: Union[Decimal, float, int] = 0.0
    cash_currency: CurrencyUnit = CurrencyUnit.INR
    periodic_budgets: Dict[int, Union[Decimal, float, int]] = field(default_factory=dict)
    budget_currency: CurrencyUnit = CurrencyUnit.INR
    district_equity_targets: Dict[str, float] = field(default_factory=dict) # district_id -> quota theta in [0, 1]
    blackout_districts: List[str] = field(default_factory=list)             # districts with active blackout
    candidates: List[ProjectOptimizationCandidate] = field(default_factory=list)
    dependencies: List[DependencyEdgeInput] = field(default_factory=list)
    resource_capacities: Dict[str, Dict[int, int]] = field(default_factory=dict) # resource_id -> {period: capacity}
    funding_sources: List[FundingSourceSpec] = field(default_factory=list)
    fiscal_retention_rate: float = 1.0
    enable_early_start_bonus: bool = True
    max_solve_time_seconds: float = 60.0
    deterministic_seed: int = 42
    num_workers: int = 1
    allow_uniform_weight_fallback: bool = False


@dataclass(frozen=True)
class ScheduledProjectResult:
    """Scheduled output specification for a single project candidate."""
    project_id: str
    project_code: str
    district_id: str
    is_selected: bool
    scheduled_start_period: Optional[int]
    scheduled_completion_period: Optional[int]
    assigned_funding_source: Optional[str]
    cost_ccu: int
    cost_inr: Decimal
    periodic_expenditures_ccu: Dict[int, int]
    periodic_expenditures_inr: Dict[int, Decimal]
    mcpi_score: float
    raw_mcpi_score: float
    quantized_mcpi_coefficient: int
    is_tier1_mandatory: bool


@dataclass(frozen=True)
class PeriodSolvencyResult:
    """Solvency status and liquidity balance for a discrete calendar period."""
    period: int
    revenue_receipt_ccu: int
    expenditure_ccu: int
    cash_balance_ccu: int
    cash_balance_inr: Decimal
    is_solvent: bool


@dataclass(frozen=True)
class InfeasibilityFinding:
    """Individual diagnostic finding identifying a constraint conflict."""
    category: str        # BUDGET, SOLVENCY, RESOURCE, PRECEDENCE, HORIZON, FUNDING
    classification: str  # PROVEN_INFEASIBILITY, NECESSARY_CONDITION_VIOLATION, WARNING, SOLVER_ASSISTED_HYPOTHESIS
    message: str
    mathematical_condition: str
    affected_projects: List[str]
    conflicting_periods: List[int] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InfeasibilityDiagnosticReport:
    """Comprehensive multi-category diagnostic report for infeasible portfolios."""
    has_proven_infeasibility: bool
    proven_causes: List[InfeasibilityFinding]
    necessary_condition_violations: List[InfeasibilityFinding]
    solver_hypotheses: List[InfeasibilityFinding]
    warnings: List[InfeasibilityFinding]
    is_assumption_core_minimal: bool = False


@dataclass(frozen=True)
class RecoveryOptimizationResponse:
    """Structured response contract emitted by the optimization engine."""
    scenario_name: str
    solver_status: str  # OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN, MODEL_INVALID
    is_optimal: bool
    objective_value: Optional[float]
    best_bound: Optional[float]
    optimality_gap: Optional[float]
    solve_time_seconds: float
    selected_project_count: int
    total_cost_ccu: int
    total_cost_inr: Decimal
    scheduled_projects: List[ScheduledProjectResult]
    periodic_solvency: List[PeriodSolvencyResult]
    district_equity_allocation_ccu: Dict[str, int]
    district_equity_allocation_inr: Dict[str, Decimal]
    input_fingerprint_sha256: str
    ortools_version: str
    solver_parameters: Dict[str, Any]
    infeasibility_diagnostics: Optional[InfeasibilityDiagnosticReport] = None
