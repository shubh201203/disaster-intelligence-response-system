"""
Recovery CP-SAT Optimization Engine Schemas and Dataclasses.

Phase 6D-B Milestone 2B Domain Contracts.
Establishes canonical currency scaling, integer conversion rules,
deterministic capped expenditure apportionment, input candidates,
and structured optimization responses.
"""

from dataclasses import dataclass, field, asdict
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from enum import Enum
from fractions import Fraction
import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class CurrencyUnit(str, Enum):
    """Explicit currency units supported by the optimization engine."""
    INR = "INR"
    LAKH_INR = "LAKH_INR"
    CRORE_INR = "CRORE_INR"


# Canonical Currency Unit: 1 CCU = 10^-5 INR (0.00001 INR)
CCU_PER_INR = Decimal("100000")          # 10^5 CCU per 1 INR
CCU_PER_LAKH = Decimal("10000000000")    # 10^10 CCU per 1 Lakh INR
CCU_PER_CRORE = Decimal("1000000000000") # 10^12 CCU per 1 Crore INR

# Maximum safe integer threshold for signed 64-bit integer headroom (2^63 - 1 ≈ 9.22e18)
MAX_SAFE_INTEGER = 10**17


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
    - 'ceiling': ROUND_CEILING (conservative for project costs, equity floors)

    Uses decimal.Decimal to eliminate IEEE 754 binary floating-point representation artifacts.
    Rejects NaN, infinity, negative amounts, invalid currency units, and unsupported rounding modes.
    """
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"NON_FINITE_AMOUNT: Invalid floating-point value for currency conversion: {val}")

    if isinstance(val, (int, float, str)):
        try:
            d_val = Decimal(str(val))
        except Exception as e:
            raise ValueError(f"Cannot parse value as Decimal: {val} ({e})")
    elif isinstance(val, Decimal):
        if val.is_nan() or val.is_infinite():
            raise ValueError(f"NON_FINITE_AMOUNT: Invalid Decimal value for currency conversion: {val}")
        d_val = val
    else:
        raise TypeError(f"Unsupported value type for currency conversion: {type(val)}")

    if d_val < 0:
        raise ValueError(f"NEGATIVE_AMOUNT: Currency amount cannot be negative, got {d_val}")

    if isinstance(unit, str):
        try:
            unit = CurrencyUnit(unit)
        except ValueError:
            raise ValueError(f"UNSUPPORTED_CURRENCY: Unknown currency unit '{unit}'")
    elif not isinstance(unit, CurrencyUnit):
        raise ValueError(f"UNSUPPORTED_CURRENCY: Invalid currency unit type: {type(unit)}")

    if unit == CurrencyUnit.INR:
        multiplier = CCU_PER_INR
    elif unit == CurrencyUnit.LAKH_INR:
        multiplier = CCU_PER_LAKH
    elif unit == CurrencyUnit.CRORE_INR:
        multiplier = CCU_PER_CRORE
    else:
        raise ValueError(f"UNSUPPORTED_CURRENCY: Unknown currency unit: {unit}")

    mode_lower = rounding_mode.lower()
    if mode_lower == "floor":
        round_rule = ROUND_FLOOR
    elif mode_lower in ("ceiling", "ceil"):
        round_rule = ROUND_CEILING
    else:
        raise ValueError(f"UNSUPPORTED_ROUNDING_MODE: '{rounding_mode}'. Must be 'floor' or 'ceiling'")

    ccu_decimal = d_val * multiplier
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
    if isinstance(raw_score, float) and (math.isnan(raw_score) or math.isinf(raw_score)):
        raise ValueError(f"Invalid MCPI score: {raw_score}")
    if raw_score < 0.0 or raw_score > 1.0:
        raise ValueError(f"Raw MCPI score must be in [0.0, 1.0], got {raw_score}")
    d_score = Decimal(str(raw_score))
    return int(math.floor(d_score * Decimal("10000000")))


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
    max_safety_start_period: Optional[int] = None                           # Inviolable hard start deadline for mandatory life safety (RSK-M2-01)
    max_solve_time_seconds: float = 60.0
    deterministic_seed: int = 42
    num_workers: int = 1
    allow_uniform_weight_fallback: bool = False

    @property
    def safety_max_period(self) -> Optional[int]:
        """Authoritative alias for max_safety_start_period (T_safety_max)."""
        return self.max_safety_start_period


def compute_canonical_input_fingerprint(request: RecoveryOptimizationRequest) -> str:
    """
    Computes a canonical SHA-256 fingerprint over all optimization-affecting inputs.
    Guarantees:
    - Deterministic key ordering and semantic list sorting (candidates by ID, dependencies by (pred, succ), etc.).
    - Complete inclusion of all scenario, policy, candidate, fund, dependency, and solver parameters.
    - Stable UTF-8 JSON serialization.
    """
    canonical_dict = {
        "scenario_name": str(request.scenario_name),
        "planning_horizon_periods": int(request.planning_horizon_periods),
        "period_length_days": float(request.period_length_days),
        "initial_cash": str(request.initial_cash),
        "cash_currency": str(request.cash_currency.value if isinstance(request.cash_currency, CurrencyUnit) else request.cash_currency),
        "periodic_budgets": {str(k): str(v) for k, v in sorted(request.periodic_budgets.items(), key=lambda x: int(x[0]))},
        "budget_currency": str(request.budget_currency.value if isinstance(request.budget_currency, CurrencyUnit) else request.budget_currency),
        "district_equity_targets": {str(k): float(v) for k, v in sorted(request.district_equity_targets.items())},
        "blackout_districts": sorted(list(request.blackout_districts)),
        "max_safety_start_period": request.max_safety_start_period,
        "fiscal_retention_rate": float(request.fiscal_retention_rate),
        "enable_early_start_bonus": bool(request.enable_early_start_bonus),
        "allow_uniform_weight_fallback": bool(request.allow_uniform_weight_fallback),
        "max_solve_time_seconds": float(request.max_solve_time_seconds),
        "deterministic_seed": int(request.deterministic_seed),
        "num_workers": int(request.num_workers),
        "candidates": [
            {
                "project_id": str(c.project_id),
                "project_code": str(c.project_code),
                "district_id": str(c.district_id),
                "estimated_cost": str(c.estimated_cost),
                "cost_currency": str(c.cost_currency.value if isinstance(c.cost_currency, CurrencyUnit) else c.cost_currency),
                "duration_periods": int(c.duration_periods),
                "release_period": int(c.release_period),
                "deadline_period": c.deadline_period,
                "is_tier1_mandatory": bool(c.is_tier1_mandatory),
                "raw_mcpi_score": float(c.raw_mcpi_score),
                "expenditure_weights": [float(w) for w in c.expenditure_weights] if c.expenditure_weights is not None else None,
                "resource_demands": {str(r): int(q) for r, q in sorted(c.resource_demands.items())},
                "eligible_funds": sorted(list(c.eligible_funds)),
            }
            for c in sorted(request.candidates, key=lambda x: str(x.project_id))
        ],
        "dependencies": [
            {
                "predecessor_id": str(d.predecessor_id),
                "successor_id": str(d.successor_id),
                "lag_periods": int(d.lag_periods),
            }
            for d in sorted(request.dependencies, key=lambda x: (str(x.predecessor_id), str(x.successor_id)))
        ],
        "resource_capacities": {
            str(r_id): {str(p): int(cap) for p, cap in sorted(p_caps.items(), key=lambda x: int(x[0]))}
            for r_id, p_caps in sorted(request.resource_capacities.items())
        },
        "funding_sources": [
            {
                "fund_id": str(f.fund_id),
                "capacity": str(f.capacity),
                "currency": str(f.currency.value if isinstance(f.currency, CurrencyUnit) else f.currency),
                "period_tranches": {str(p): str(v) for p, v in sorted(f.period_tranches.items(), key=lambda x: int(x[0]))} if f.period_tranches else None,
            }
            for f in sorted(request.funding_sources, key=lambda x: str(x.fund_id))
        ],
    }
    raw_json = json.dumps(canonical_dict, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(raw_json.encode('utf-8')).hexdigest()


def validate_numerical_safety(
    request_or_candidates: Union[RecoveryOptimizationRequest, List[Tuple[ProjectOptimizationCandidate, int]]],
    budgets_ccu: Optional[Dict[int, int]] = None,
    initial_cash_ccu: Optional[int] = None,
    funding_capacities_ccu: Optional[Dict[str, int]] = None,
    horizon: Optional[int] = None,
) -> None:
    """
    Validates that all integer coefficients, expressions, and objective bounds
    fit safely within signed 64-bit integer limits before model construction.
    Supports being called either with a single RecoveryOptimizationRequest or
    with pre-computed CCU data. Raises ValueError if overflow risk is detected.
    """
    if isinstance(request_or_candidates, RecoveryOptimizationRequest):
        req = request_or_candidates
        horizon = req.planning_horizon_periods
        
        # Check raw numbers before conversion if they already exceed MAX_SAFE_INTEGER
        try:
            init_cash = normalize_to_ccu(req.initial_cash, req.cash_currency, rounding_mode="floor")
        except ValueError:
            init_cash = 0
            
        b_ccu: Dict[int, int] = {}
        for t, b in req.periodic_budgets.items():
            try:
                b_ccu[t] = normalize_to_ccu(b, req.budget_currency, rounding_mode="floor")
            except ValueError:
                b_ccu[t] = 0
                
        c_ccu: List[Tuple[ProjectOptimizationCandidate, int]] = []
        for c in req.candidates:
            try:
                cost = normalize_to_ccu(c.estimated_cost, c.cost_currency, rounding_mode="ceiling")
            except ValueError:
                cost = 0
            c_ccu.append((c, cost))
            
        f_ccu: Dict[str, int] = {}
        for f in req.funding_sources:
            try:
                f_ccu[f.fund_id] = normalize_to_ccu(f.capacity, f.currency, rounding_mode="floor")
            except ValueError:
                f_ccu[f.fund_id] = 0

        # Validate individual and aggregate resource demands and capacities
        agg_resource_demands: Dict[str, int] = {}
        for c in req.candidates:
            for r_id, dem in c.resource_demands.items():
                int_dem = int(dem)
                if int_dem > MAX_SAFE_INTEGER:
                    raise ValueError(f"INTEGER_OVERFLOW_RISK: project '{c.project_id}' resource '{r_id}' demand ({dem}) exceeds safe bound {MAX_SAFE_INTEGER}")
                agg_resource_demands[r_id] = agg_resource_demands.get(r_id, 0) + int_dem
                if agg_resource_demands[r_id] > MAX_SAFE_INTEGER:
                    raise ValueError(f"INTEGER_OVERFLOW_RISK: aggregate resource '{r_id}' demand sum ({agg_resource_demands[r_id]}) exceeds safe bound {MAX_SAFE_INTEGER}")

        for r_id, caps in req.resource_capacities.items():
            for t, cap in caps.items():
                if int(cap) > MAX_SAFE_INTEGER:
                    raise ValueError(f"INTEGER_OVERFLOW_RISK: resource '{r_id}' capacity at period {t} ({cap}) exceeds safe bound {MAX_SAFE_INTEGER}")

        # Validate aggregate funding demands per fund
        agg_fund_demands: Dict[str, int] = {}
        for c, cost in c_ccu:
            int_cost = int(cost)
            for fid in c.eligible_funds:
                agg_fund_demands[fid] = agg_fund_demands.get(fid, 0) + int_cost
                if agg_fund_demands[fid] > MAX_SAFE_INTEGER:
                    raise ValueError(f"INTEGER_OVERFLOW_RISK: aggregate funding demand for fund '{fid}' ({agg_fund_demands[fid]}) exceeds safe bound {MAX_SAFE_INTEGER}")

        # Validate aggregate district demands
        agg_district_demands: Dict[str, int] = {}
        for c, cost in c_ccu:
            int_cost = int(cost)
            d_id = c.district_id
            agg_district_demands[d_id] = agg_district_demands.get(d_id, 0) + int_cost
            if agg_district_demands[d_id] > MAX_SAFE_INTEGER:
                raise ValueError(f"INTEGER_OVERFLOW_RISK: aggregate district demand for '{d_id}' ({agg_district_demands[d_id]}) exceeds safe bound {MAX_SAFE_INTEGER}")

        _validate_numerical_safety_core(c_ccu, b_ccu, init_cash, f_ccu, horizon)
    else:
        _validate_numerical_safety_core(
            request_or_candidates,
            budgets_ccu or {},
            initial_cash_ccu or 0,
            funding_capacities_ccu or {},
            horizon or 1,
        )


def _validate_numerical_safety_core(
    candidates_ccu: List[Tuple[ProjectOptimizationCandidate, int]],
    budgets_ccu: Dict[int, int],
    initial_cash_ccu: int,
    funding_capacities_ccu: Dict[str, int],
    horizon: int,
) -> None:
    if initial_cash_ccu > MAX_SAFE_INTEGER:
        raise ValueError(f"INTEGER_OVERFLOW_RISK: initial_cash_ccu ({initial_cash_ccu}) exceeds safe bound {MAX_SAFE_INTEGER}")

    for t, b in budgets_ccu.items():
        if b > MAX_SAFE_INTEGER:
            raise ValueError(f"INTEGER_OVERFLOW_RISK: budget for period {t} ({b}) exceeds safe bound {MAX_SAFE_INTEGER}")

    total_budget = initial_cash_ccu + sum(budgets_ccu.values())
    if total_budget > MAX_SAFE_INTEGER:
        raise ValueError(f"INTEGER_OVERFLOW_RISK: total_budget ({total_budget}) exceeds safe bound {MAX_SAFE_INTEGER}")

    total_project_cost = 0
    for c, cost in candidates_ccu:
        if cost > MAX_SAFE_INTEGER:
            raise ValueError(f"INTEGER_OVERFLOW_RISK: cost for project {c.project_id} ({cost}) exceeds safe bound {MAX_SAFE_INTEGER}")
        total_project_cost += cost
        if total_project_cost > MAX_SAFE_INTEGER:
            raise ValueError(f"INTEGER_OVERFLOW_RISK: cumulative project cost ({total_project_cost}) exceeds safe bound {MAX_SAFE_INTEGER}")

    for fid, cap in funding_capacities_ccu.items():
        if cap > MAX_SAFE_INTEGER:
            raise ValueError(f"INTEGER_OVERFLOW_RISK: funding source {fid} capacity ({cap}) exceeds safe bound {MAX_SAFE_INTEGER}")

    # Resource aggregate demand validation if candidates carry demands
    agg_res_demands: Dict[str, int] = {}
    for c, _ in candidates_ccu:
        for r_id, dem in c.resource_demands.items():
            int_dem = int(dem)
            if int_dem > MAX_SAFE_INTEGER:
                raise ValueError(f"INTEGER_OVERFLOW_RISK: project '{c.project_id}' resource '{r_id}' demand ({dem}) exceeds safe bound {MAX_SAFE_INTEGER}")
            agg_res_demands[r_id] = agg_res_demands.get(r_id, 0) + int_dem
            if agg_res_demands[r_id] > MAX_SAFE_INTEGER:
                raise ValueError(f"INTEGER_OVERFLOW_RISK: aggregate resource '{r_id}' demand sum ({agg_res_demands[r_id]}) exceeds safe bound {MAX_SAFE_INTEGER}")

    # Objective bounds validation
    n_candidates = len(candidates_ccu)
    m_accel = n_candidates * max(0, horizon - 1) + 1
    max_mcpi_term = 10_000_000 * m_accel
    if max_mcpi_term > MAX_SAFE_INTEGER:
        raise ValueError(f"INTEGER_OVERFLOW_RISK: objective multiplier M_accel ({m_accel}) causes MCPI term ({max_mcpi_term}) to exceed safe bound {MAX_SAFE_INTEGER}")

    max_possible_objective = n_candidates * (max_mcpi_term + max(0, horizon - 1))
    if max_possible_objective > MAX_SAFE_INTEGER:
        raise ValueError(f"INTEGER_OVERFLOW_RISK: maximum possible objective ({max_possible_objective}) exceeds safe bound {MAX_SAFE_INTEGER}")


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
    is_assumption_core_sufficient: bool = True


@dataclass(frozen=True)
class RecoveryOptimizationResponse:
    """Structured response contract emitted by the optimization engine.

    Objective and Bound Value Representations:
    - exact_objective_value (Optional[int]):
        Exact integer objective value independently evaluated using arbitrary-precision Python
        integers from scheduled candidate assignments. Mandatory for OPTIMAL and FEASIBLE responses.
    - objective_value (Optional[float]):
        Approximate floating-point objective value for UI/display purposes (float(exact_objective_value)).
    - best_bound (Optional[float]):
        Raw floating-point solver dual bound as returned directly by OR-Tools CP-SAT BestObjectiveBound().
        For display and optimality gap computation.
    - conservative_best_bound (Optional[int]):
        Conservative integer upper bound derived from raw BestObjectiveBound() accounting for IEEE-754
        precision limits (ulp). Guaranteed to never fall below the true mathematical upper bound even
        up to the approved numerical safety limit of 10^17. Mandatory for OPTIMAL and FEASIBLE responses.
        For OPTIMAL, equals exact_objective_value.
    - exact_best_bound (Optional[int]):
        Exact integer best bound. For OPTIMAL, this is exact and equals exact_objective_value.
        For FEASIBLE, retained as an alias to conservative_best_bound for backward compatibility,
        representing a conservative integer upper bound rather than an exact dual bound.
    """
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
    exact_objective_value: Optional[int] = None
    exact_best_bound: Optional[int] = None
    conservative_best_bound: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes response to dictionary, strictly preserving exact integer objective and bound."""
        return {
            "scenario_name": self.scenario_name,
            "solver_status": self.solver_status,
            "is_optimal": self.is_optimal,
            "objective_value": self.objective_value,
            "best_bound": self.best_bound,
            "optimality_gap": self.optimality_gap,
            "exact_objective_value": self.exact_objective_value,
            "exact_best_bound": self.exact_best_bound,
            "conservative_best_bound": self.conservative_best_bound,
            "solve_time_seconds": self.solve_time_seconds,
            "selected_project_count": self.selected_project_count,
            "total_cost_ccu": self.total_cost_ccu,
            "total_cost_inr": str(self.total_cost_inr),
            "scheduled_projects": [asdict(p) for p in self.scheduled_projects],
            "periodic_solvency": [asdict(s) for s in self.periodic_solvency],
            "district_equity_allocation_ccu": dict(self.district_equity_allocation_ccu),
            "district_equity_allocation_inr": {k: str(v) for k, v in self.district_equity_allocation_inr.items()},
            "input_fingerprint_sha256": self.input_fingerprint_sha256,
            "ortools_version": self.ortools_version,
            "solver_parameters": dict(self.solver_parameters),
            "infeasibility_diagnostics": asdict(self.infeasibility_diagnostics) if self.infeasibility_diagnostics else None,
        }
