"""
Pydantic v2 API Data Transfer Objects for Recovery Optimization Scenarios.

Phase 6D-B Milestone 3 Gate 1 Implementation.
Exposes strict request, response, and error schemas wrapping the accepted Milestone 2B
engine contracts with full decimal preservation, integer bound safety, non-finite rejection,
and RSK-M2-07 Caller-Mandatory Safety Deadline validation.
"""

from decimal import Decimal
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Union
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.recovery.optimization.schemas import (
    CurrencyUnit,
    DependencyEdgeInput,
    FundingSourceSpec,
    InfeasibilityFinding,
    InfeasibilityDiagnosticReport,
    PeriodSolvencyResult,
    ProjectOptimizationCandidate,
    RecoveryOptimizationRequest,
    RecoveryOptimizationResponse,
    ScheduledProjectResult,
)


# ==============================================================================
# Helper Validators
# ==============================================================================

def _check_finite_number(v: Any, field_name: str) -> None:
    """Rejects NaN and infinite numeric values."""
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"NON_FINITE_VALUE: Field '{field_name}' cannot be NaN or infinite, got {v}")
    elif isinstance(v, Decimal):
        if v.is_nan() or v.is_infinite():
            raise ValueError(f"NON_FINITE_VALUE: Field '{field_name}' cannot be NaN or infinite, got {v}")


# ==============================================================================
# Nested Request DTOs
# ==============================================================================

class ProjectOptimizationCandidateDTO(BaseModel):
    """Candidate recovery project input DTO for portfolio optimization."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    project_id: str = Field(..., min_length=1, max_length=100, description="Unique candidate project identifier")
    project_code: str = Field(..., min_length=1, max_length=100, description="Human-readable project code")
    district_id: str = Field(..., min_length=1, max_length=100, description="Administrative district code")
    estimated_cost: Decimal = Field(..., ge=0, description="Total capital reconstruction cost")
    duration_periods: int = Field(..., ge=1, description="Execution duration in discrete planning periods")
    cost_currency: CurrencyUnit = Field(default=CurrencyUnit.INR, description="Currency denomination of estimated cost")
    release_period: int = Field(default=1, ge=1, description="Earliest discrete calendar period project may start")
    deadline_period: Optional[int] = Field(default=None, ge=1, description="Latest discrete calendar period project must complete")
    is_tier1_mandatory: bool = Field(default=False, description="Life-safety priority flag requiring selection and early start")
    raw_mcpi_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized Multi-Criteria Priority Index in [0.0, 1.0]")
    expenditure_weights: Optional[List[float]] = Field(default=None, description="Disbursement profile weights summing to 1.0")
    resource_demands: Dict[str, int] = Field(default_factory=dict, description="Resource type -> integer demand per active period")
    eligible_funds: List[str] = Field(default_factory=list, description="List of eligible funding source identifiers")

    @field_validator("estimated_cost", mode="before")
    @classmethod
    def validate_cost_finite(cls, v: Any) -> Any:
        _check_finite_number(v, "estimated_cost")
        return v

    @field_validator("raw_mcpi_score", mode="before")
    @classmethod
    def validate_mcpi_finite(cls, v: Any) -> Any:
        _check_finite_number(v, "raw_mcpi_score")
        return v

    @field_validator("expenditure_weights")
    @classmethod
    def validate_weights(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("expenditure_weights list cannot be empty when provided")
            for idx, w in enumerate(v):
                _check_finite_number(w, f"expenditure_weights[{idx}]")
                if w < 0.0:
                    raise ValueError(f"Expenditure weight at index {idx} must be non-negative, got {w}")
            if sum(v) <= 0.0:
                raise ValueError("Sum of expenditure weights must be strictly positive")
        return v

    @field_validator("resource_demands")
    @classmethod
    def validate_resource_demands(cls, v: Dict[str, int]) -> Dict[str, int]:
        for r_id, dem in v.items():
            if dem < 0:
                raise ValueError(f"Resource demand for '{r_id}' cannot be negative, got {dem}")
        return v

    @model_validator(mode="after")
    def validate_candidate_consistency(self) -> "ProjectOptimizationCandidateDTO":
        if self.deadline_period is not None:
            min_completion = self.release_period + self.duration_periods - 1
            if self.deadline_period < min_completion:
                raise ValueError(
                    f"Candidate '{self.project_id}' deadline {self.deadline_period} is infeasible: "
                    f"earliest possible completion is release ({self.release_period}) + duration ({self.duration_periods}) - 1 = {min_completion}"
                )
        if self.expenditure_weights is not None:
            if len(self.expenditure_weights) != self.duration_periods:
                raise ValueError(
                    f"Candidate '{self.project_id}' expenditure weights length ({len(self.expenditure_weights)}) "
                    f"does not match duration ({self.duration_periods})"
                )
        return self

    def to_engine_candidate(self) -> ProjectOptimizationCandidate:
        """Converts to accepted Milestone 2B ProjectOptimizationCandidate dataclass."""
        return ProjectOptimizationCandidate(
            project_id=self.project_id,
            project_code=self.project_code,
            district_id=self.district_id,
            estimated_cost=self.estimated_cost,
            duration_periods=self.duration_periods,
            cost_currency=self.cost_currency,
            release_period=self.release_period,
            deadline_period=self.deadline_period,
            is_tier1_mandatory=self.is_tier1_mandatory,
            raw_mcpi_score=self.raw_mcpi_score,
            expenditure_weights=list(self.expenditure_weights) if self.expenditure_weights is not None else None,
            resource_demands=dict(self.resource_demands),
            eligible_funds=list(self.eligible_funds),
        )

    @classmethod
    def from_engine_candidate(cls, cand: ProjectOptimizationCandidate) -> "ProjectOptimizationCandidateDTO":
        """Constructs DTO from accepted Milestone 2B ProjectOptimizationCandidate."""
        return cls(
            project_id=cand.project_id,
            project_code=cand.project_code,
            district_id=cand.district_id,
            estimated_cost=Decimal(str(cand.estimated_cost)) if not isinstance(cand.estimated_cost, Decimal) else cand.estimated_cost,
            duration_periods=cand.duration_periods,
            cost_currency=cand.cost_currency,
            release_period=cand.release_period,
            deadline_period=cand.deadline_period,
            is_tier1_mandatory=cand.is_tier1_mandatory,
            raw_mcpi_score=cand.raw_mcpi_score,
            expenditure_weights=list(cand.expenditure_weights) if cand.expenditure_weights is not None else None,
            resource_demands=dict(cand.resource_demands),
            eligible_funds=list(cand.eligible_funds),
        )


class FundingSourceSpecDTO(BaseModel):
    """Funding source specification DTO under Model B indivisible assignment."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    fund_id: str = Field(..., min_length=1, max_length=100, description="Funding source unique code")
    capacity: Decimal = Field(..., ge=0, description="Total capital capacity of the funding source")
    currency: CurrencyUnit = Field(default=CurrencyUnit.INR, description="Denomination of funding capacity")
    period_tranches: Optional[Dict[int, Decimal]] = Field(
        default=None, description="Optional period-specific cash injection limits"
    )

    @field_validator("capacity", mode="before")
    @classmethod
    def validate_capacity_finite(cls, v: Any) -> Any:
        _check_finite_number(v, "capacity")
        return v

    @field_validator("period_tranches")
    @classmethod
    def validate_period_tranches(cls, v: Optional[Dict[int, Decimal]]) -> Optional[Dict[int, Decimal]]:
        if v is not None:
            for p, val in v.items():
                if p < 1:
                    raise ValueError(f"Period tranche index must be >= 1, got {p}")
                _check_finite_number(val, f"period_tranches[{p}]")
                if val < 0:
                    raise ValueError(f"Period tranche capacity for period {p} cannot be negative, got {val}")
        return v

    def to_engine_spec(self) -> FundingSourceSpec:
        """Converts to accepted Milestone 2B FundingSourceSpec dataclass."""
        return FundingSourceSpec(
            fund_id=self.fund_id,
            capacity=self.capacity,
            currency=self.currency,
            period_tranches=dict(self.period_tranches) if self.period_tranches is not None else None,
        )

    @classmethod
    def from_engine_spec(cls, spec: FundingSourceSpec) -> "FundingSourceSpecDTO":
        """Constructs DTO from accepted Milestone 2B FundingSourceSpec."""
        tranches = None
        if spec.period_tranches:
            tranches = {
                int(k): (Decimal(str(v)) if not isinstance(v, Decimal) else v)
                for k, v in spec.period_tranches.items()
            }
        cap = Decimal(str(spec.capacity)) if not isinstance(spec.capacity, Decimal) else spec.capacity
        return cls(
            fund_id=spec.fund_id,
            capacity=cap,
            currency=spec.currency,
            period_tranches=tranches,
        )


class DependencyEdgeDTO(BaseModel):
    """Directed project dependency relationship DTO."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    predecessor_id: str = Field(..., min_length=1, max_length=100, description="Predecessor project ID")
    successor_id: str = Field(..., min_length=1, max_length=100, description="Successor project ID")
    lag_periods: int = Field(default=0, ge=0, description="Discrete period lag between finish and start")

    @model_validator(mode="after")
    def validate_not_self_dependent(self) -> "DependencyEdgeDTO":
        if self.predecessor_id == self.successor_id:
            raise ValueError(f"Self-dependency detected: project '{self.predecessor_id}' cannot depend on itself")
        return self

    def to_engine_edge(self) -> DependencyEdgeInput:
        """Converts to accepted Milestone 2B DependencyEdgeInput dataclass."""
        return DependencyEdgeInput(
            predecessor_id=self.predecessor_id,
            successor_id=self.successor_id,
            lag_periods=self.lag_periods,
        )

    @classmethod
    def from_engine_edge(cls, edge: DependencyEdgeInput) -> "DependencyEdgeDTO":
        """Constructs DTO from accepted Milestone 2B DependencyEdgeInput."""
        return cls(
            predecessor_id=edge.predecessor_id,
            successor_id=edge.successor_id,
            lag_periods=edge.lag_periods,
        )


# ==============================================================================
# Top-Level Request DTO
# ==============================================================================

class RecoveryOptimizationScenarioRequest(BaseModel):
    """
    Complete caller-supplied recovery optimization scenario request contract.
    Strictly wraps accepted Milestone 2B RecoveryOptimizationRequest.
    """
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    scenario_name: str = Field(..., min_length=1, max_length=100, description="Scenario identifier")
    planning_horizon_periods: int = Field(..., ge=1, le=120, description="Total discrete time periods (T)")
    period_length_days: float = Field(default=30.0, gt=0.0, description="Calendar days per discrete period")
    initial_cash: Decimal = Field(default=Decimal("0.0"), ge=0, description="Initial available liquidity at period 0")
    cash_currency: CurrencyUnit = Field(default=CurrencyUnit.INR, description="Denomination of initial cash")
    periodic_budgets: Dict[int, Decimal] = Field(
        default_factory=dict, description="Discrete period budget inflows: period -> amount"
    )
    budget_currency: CurrencyUnit = Field(default=CurrencyUnit.INR, description="Denomination of periodic budgets")
    district_equity_targets: Dict[str, float] = Field(
        default_factory=dict, description="District equity quota theta_d in [0.0, 1.0]"
    )
    blackout_districts: List[str] = Field(
        default_factory=list, description="Districts with active blackout (zero allocation permitted)"
    )
    candidates: List[ProjectOptimizationCandidateDTO] = Field(
        default_factory=list, description="Candidate recovery projects submitted for scheduling"
    )
    dependencies: List[DependencyEdgeDTO] = Field(
        default_factory=list, description="Directed precedence edges among candidate projects"
    )
    resource_capacities: Dict[str, Dict[int, int]] = Field(
        default_factory=dict, description="Resource type -> {period -> integer capacity}"
    )
    funding_sources: List[FundingSourceSpecDTO] = Field(
        default_factory=list, description="Available funding sources under Model B indivisible assignment"
    )
    fiscal_retention_rate: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Fraction of unused periodic cash retained into subsequent period"
    )
    enable_early_start_bonus: bool = Field(
        default=True, description="Enables secondary acceleration incentive for earlier project starts"
    )
    max_safety_start_period: Optional[int] = Field(
        default=None, ge=1, description="Caller-mandatory start deadline for Tier-1 mandatory projects (RSK-M2-07)"
    )
    max_solve_time_seconds: float = Field(
        default=60.0, gt=0.0, le=600.0, description="Maximum wall-clock time allocated to CP-SAT solver"
    )
    deterministic_seed: int = Field(default=42, ge=0, description="Solver random seed for reproducible solutions")
    num_workers: int = Field(default=1, ge=1, le=16, description="Parallel worker search threads")
    allow_uniform_weight_fallback: bool = Field(
        default=False, description="Explicit opt-in to generate uniform expenditure weights when omitted"
    )

    @field_validator("initial_cash", mode="before")
    @classmethod
    def validate_initial_cash_finite(cls, v: Any) -> Any:
        _check_finite_number(v, "initial_cash")
        return v

    @field_validator("period_length_days", mode="before")
    @classmethod
    def validate_period_length_finite(cls, v: Any) -> Any:
        _check_finite_number(v, "period_length_days")
        return v

    @field_validator("fiscal_retention_rate", mode="before")
    @classmethod
    def validate_retention_finite(cls, v: Any) -> Any:
        _check_finite_number(v, "fiscal_retention_rate")
        return v

    @field_validator("max_solve_time_seconds", mode="before")
    @classmethod
    def validate_time_finite(cls, v: Any) -> Any:
        _check_finite_number(v, "max_solve_time_seconds")
        return v

    @field_validator("periodic_budgets")
    @classmethod
    def validate_periodic_budgets(cls, v: Dict[int, Decimal]) -> Dict[int, Decimal]:
        for p, b in v.items():
            if p < 1:
                raise ValueError(f"Periodic budget period must be >= 1, got {p}")
            _check_finite_number(b, f"periodic_budgets[{p}]")
            if b < 0:
                raise ValueError(f"Periodic budget for period {p} cannot be negative, got {b}")
        return v

    @field_validator("district_equity_targets")
    @classmethod
    def validate_equity_targets(cls, v: Dict[str, float]) -> Dict[str, float]:
        for d, quota in v.items():
            _check_finite_number(quota, f"district_equity_targets[{d}]")
            if quota < 0.0 or quota > 1.0:
                raise ValueError(f"District equity quota for '{d}' must be in [0.0, 1.0], got {quota}")
        if sum(v.values()) > 1.000001:
            raise ValueError(f"Sum of district equity quotas exceeds 1.0: {sum(v.values()):.6f}")
        return v

    @field_validator("resource_capacities")
    @classmethod
    def validate_resource_capacities(cls, v: Dict[str, Dict[int, int]]) -> Dict[str, Dict[int, int]]:
        for r_id, p_caps in v.items():
            for p, cap in p_caps.items():
                if p < 1:
                    raise ValueError(f"Resource '{r_id}' period index must be >= 1, got {p}")
                if cap < 0:
                    raise ValueError(f"Resource '{r_id}' capacity at period {p} cannot be negative, got {cap}")
        return v

    @model_validator(mode="after")
    def validate_rsk_m2_07_caller_mandatory_deadline(self) -> "RecoveryOptimizationScenarioRequest":
        """
        Enforces approved governance policy RSK-M2-07 (Option A — Caller-Mandatory Safety Deadline).
        When any project candidate has is_tier1_mandatory=True:
        1. max_safety_start_period must be explicitly supplied (cannot be None).
        2. Must be within planning horizon [1, planning_horizon_periods].
        3. No default, inferred deadline, or fallback is permitted.
        """
        has_mandatory = any(c.is_tier1_mandatory for c in self.candidates)
        if has_mandatory:
            if self.max_safety_start_period is None:
                raise ValueError(
                    "RSK-M2-07 Violation: Portfolio contains Tier-1 mandatory life-safety projects, "
                    "but 'max_safety_start_period' was not provided. An explicit caller-supplied deadline is required."
                )
            if self.max_safety_start_period > self.planning_horizon_periods:
                raise ValueError(
                    f"RSK-M2-07 Violation: max_safety_start_period ({self.max_safety_start_period}) "
                    f"exceeds planning_horizon_periods ({self.planning_horizon_periods})."
                )
        else:
            if self.max_safety_start_period is not None:
                if self.max_safety_start_period > self.planning_horizon_periods:
                    raise ValueError(
                        f"max_safety_start_period ({self.max_safety_start_period}) "
                        f"exceeds planning_horizon_periods ({self.planning_horizon_periods})."
                    )

        # Validate period indices against planning horizon
        h = self.planning_horizon_periods
        for t in self.periodic_budgets:
            if t > h:
                raise ValueError(f"Periodic budget period {t} exceeds planning horizon {h}")

        for c in self.candidates:
            if c.release_period > h:
                raise ValueError(f"Candidate '{c.project_id}' release_period ({c.release_period}) exceeds planning horizon {h}")
            if c.deadline_period is not None and c.deadline_period > h:
                raise ValueError(f"Candidate '{c.project_id}' deadline_period ({c.deadline_period}) exceeds planning horizon {h}")
            if c.duration_periods > h:
                raise ValueError(f"Candidate '{c.project_id}' duration_periods ({c.duration_periods}) exceeds planning horizon {h}")

        for r_id, p_caps in self.resource_capacities.items():
            for p in p_caps:
                if p > h:
                    raise ValueError(f"Resource '{r_id}' period {p} exceeds planning horizon {h}")

        # Validate candidate IDs uniqueness
        c_ids = [c.project_id for c in self.candidates]
        if len(c_ids) != len(set(c_ids)):
            seen = set()
            dups = set()
            for pid in c_ids:
                if pid in seen:
                    dups.add(pid)
                seen.add(pid)
            raise ValueError(f"Duplicate candidate project IDs detected: {sorted(list(dups))}")

        # Validate dependency endpoints exist in candidates
        cand_id_set = set(c_ids)
        for dep in self.dependencies:
            if dep.predecessor_id not in cand_id_set:
                raise ValueError(f"Dependency predecessor '{dep.predecessor_id}' not found in candidate list")
            if dep.successor_id not in cand_id_set:
                raise ValueError(f"Dependency successor '{dep.successor_id}' not found in candidate list")

        # Validate funding source references in candidates
        if self.funding_sources:
            fund_id_set = {f.fund_id for f in self.funding_sources}
            for c in self.candidates:
                for fid in c.eligible_funds:
                    if fid not in fund_id_set:
                        raise ValueError(f"Candidate '{c.project_id}' references unknown eligible fund '{fid}'")

        return self

    def to_engine_request(self) -> RecoveryOptimizationRequest:
        """Constructs accepted Milestone 2B RecoveryOptimizationRequest dataclass."""
        return RecoveryOptimizationRequest(
            scenario_name=self.scenario_name,
            planning_horizon_periods=self.planning_horizon_periods,
            period_length_days=self.period_length_days,
            initial_cash=self.initial_cash,
            cash_currency=self.cash_currency,
            periodic_budgets=dict(self.periodic_budgets),
            budget_currency=self.budget_currency,
            district_equity_targets=dict(self.district_equity_targets),
            blackout_districts=list(self.blackout_districts),
            candidates=[c.to_engine_candidate() for c in self.candidates],
            dependencies=[d.to_engine_edge() for d in self.dependencies],
            resource_capacities={r: dict(p) for r, p in self.resource_capacities.items()},
            funding_sources=[f.to_engine_spec() for f in self.funding_sources],
            fiscal_retention_rate=self.fiscal_retention_rate,
            enable_early_start_bonus=self.enable_early_start_bonus,
            max_safety_start_period=self.max_safety_start_period,
            max_solve_time_seconds=self.max_solve_time_seconds,
            deterministic_seed=self.deterministic_seed,
            num_workers=self.num_workers,
            allow_uniform_weight_fallback=self.allow_uniform_weight_fallback,
        )

    @classmethod
    def from_engine_request(cls, req: RecoveryOptimizationRequest) -> "RecoveryOptimizationScenarioRequest":
        """Constructs DTO from accepted Milestone 2B RecoveryOptimizationRequest dataclass."""
        init_cash = Decimal(str(req.initial_cash)) if not isinstance(req.initial_cash, Decimal) else req.initial_cash
        p_budgets = {
            int(k): (Decimal(str(v)) if not isinstance(v, Decimal) else v)
            for k, v in req.periodic_budgets.items()
        }
        return cls(
            scenario_name=req.scenario_name,
            planning_horizon_periods=req.planning_horizon_periods,
            period_length_days=req.period_length_days,
            initial_cash=init_cash,
            cash_currency=req.cash_currency,
            periodic_budgets=p_budgets,
            budget_currency=req.budget_currency,
            district_equity_targets=dict(req.district_equity_targets),
            blackout_districts=list(req.blackout_districts),
            candidates=[ProjectOptimizationCandidateDTO.from_engine_candidate(c) for c in req.candidates],
            dependencies=[DependencyEdgeDTO.from_engine_edge(d) for d in req.dependencies],
            resource_capacities={r: dict(p) for r, p in req.resource_capacities.items()},
            funding_sources=[FundingSourceSpecDTO.from_engine_spec(f) for f in req.funding_sources],
            fiscal_retention_rate=req.fiscal_retention_rate,
            enable_early_start_bonus=req.enable_early_start_bonus,
            max_safety_start_period=req.max_safety_start_period,
            max_solve_time_seconds=req.max_solve_time_seconds,
            deterministic_seed=req.deterministic_seed,
            num_workers=req.num_workers,
            allow_uniform_weight_fallback=req.allow_uniform_weight_fallback,
        )


# ==============================================================================
# Nested Response DTOs
# ==============================================================================

class ScheduledProjectResultDTO(BaseModel):
    """Scheduled output specification DTO for a single recovery project candidate."""
    model_config = ConfigDict(extra="forbid")

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

    @classmethod
    def from_engine_result(cls, res: ScheduledProjectResult) -> "ScheduledProjectResultDTO":
        inr_exp = {
            int(k): (Decimal(str(v)) if not isinstance(v, Decimal) else v)
            for k, v in res.periodic_expenditures_inr.items()
        }
        c_inr = Decimal(str(res.cost_inr)) if not isinstance(res.cost_inr, Decimal) else res.cost_inr
        return cls(
            project_id=res.project_id,
            project_code=res.project_code,
            district_id=res.district_id,
            is_selected=res.is_selected,
            scheduled_start_period=res.scheduled_start_period,
            scheduled_completion_period=res.scheduled_completion_period,
            assigned_funding_source=res.assigned_funding_source,
            cost_ccu=res.cost_ccu,
            cost_inr=c_inr,
            periodic_expenditures_ccu={int(k): int(v) for k, v in res.periodic_expenditures_ccu.items()},
            periodic_expenditures_inr=inr_exp,
            mcpi_score=res.mcpi_score,
            raw_mcpi_score=res.raw_mcpi_score,
            quantized_mcpi_coefficient=res.quantized_mcpi_coefficient,
            is_tier1_mandatory=res.is_tier1_mandatory,
        )


class PeriodSolvencyResultDTO(BaseModel):
    """Periodic solvency balance DTO."""
    model_config = ConfigDict(extra="forbid")

    period: int
    revenue_receipt_ccu: int
    expenditure_ccu: int
    cash_balance_ccu: int
    cash_balance_inr: Decimal
    is_solvent: bool

    @classmethod
    def from_engine_result(cls, sol: PeriodSolvencyResult) -> "PeriodSolvencyResultDTO":
        c_inr = Decimal(str(sol.cash_balance_inr)) if not isinstance(sol.cash_balance_inr, Decimal) else sol.cash_balance_inr
        return cls(
            period=sol.period,
            revenue_receipt_ccu=sol.revenue_receipt_ccu,
            expenditure_ccu=sol.expenditure_ccu,
            cash_balance_ccu=sol.cash_balance_ccu,
            cash_balance_inr=c_inr,
            is_solvent=sol.is_solvent,
        )


class InfeasibilityFindingDTO(BaseModel):
    """Diagnostic conflict finding DTO."""
    model_config = ConfigDict(extra="forbid")

    category: str
    classification: str
    message: str
    mathematical_condition: str
    affected_projects: List[str]
    conflicting_periods: List[int] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_engine_finding(cls, f: InfeasibilityFinding) -> "InfeasibilityFindingDTO":
        return cls(
            category=f.category,
            classification=f.classification,
            message=f.message,
            mathematical_condition=f.mathematical_condition,
            affected_projects=list(f.affected_projects),
            conflicting_periods=list(f.conflicting_periods),
            details=dict(f.details),
        )


class InfeasibilityDiagnosticReportDTO(BaseModel):
    """Multi-category diagnostic report DTO for infeasible portfolios."""
    model_config = ConfigDict(extra="forbid")

    has_proven_infeasibility: bool
    proven_causes: List[InfeasibilityFindingDTO]
    necessary_condition_violations: List[InfeasibilityFindingDTO]
    solver_hypotheses: List[InfeasibilityFindingDTO]
    warnings: List[InfeasibilityFindingDTO]
    is_assumption_core_minimal: bool = False
    is_assumption_core_sufficient: bool = True

    @classmethod
    def from_engine_report(cls, rep: InfeasibilityDiagnosticReport) -> "InfeasibilityDiagnosticReportDTO":
        return cls(
            has_proven_infeasibility=rep.has_proven_infeasibility,
            proven_causes=[InfeasibilityFindingDTO.from_engine_finding(f) for f in rep.proven_causes],
            necessary_condition_violations=[InfeasibilityFindingDTO.from_engine_finding(f) for f in rep.necessary_condition_violations],
            solver_hypotheses=[InfeasibilityFindingDTO.from_engine_finding(f) for f in rep.solver_hypotheses],
            warnings=[InfeasibilityFindingDTO.from_engine_finding(f) for f in rep.warnings],
            is_assumption_core_minimal=rep.is_assumption_core_minimal,
            is_assumption_core_sufficient=rep.is_assumption_core_sufficient,
        )


# ==============================================================================
# Top-Level Response DTO
# ==============================================================================

class RecoveryOptimizationScenarioResponse(BaseModel):
    """
    Structured API response contract for recovery optimization scenarios.
    Strictly serializes the accepted Milestone 2B RecoveryOptimizationResponse.
    Preserves exact integer objective and conservative best bound without float truncation.
    """
    model_config = ConfigDict(extra="forbid")

    scenario_name: str
    solver_status: str  # OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN, MODEL_INVALID
    is_optimal: bool
    exact_objective_value: Optional[int] = None
    exact_best_bound: Optional[int] = None
    conservative_best_bound: Optional[int] = None
    objective_value: Optional[float] = None
    best_bound: Optional[float] = None
    optimality_gap: Optional[float] = None
    solve_time_seconds: float
    selected_project_count: int
    total_cost_ccu: int
    total_cost_inr: Decimal
    scheduled_projects: List[ScheduledProjectResultDTO] = Field(default_factory=list)
    periodic_solvency: List[PeriodSolvencyResultDTO] = Field(default_factory=list)
    district_equity_allocation_ccu: Dict[str, int] = Field(default_factory=dict)
    district_equity_allocation_inr: Dict[str, Decimal] = Field(default_factory=dict)
    input_fingerprint_sha256: str
    ortools_version: str
    solver_parameters: Dict[str, Any] = Field(default_factory=dict)
    infeasibility_diagnostics: Optional[InfeasibilityDiagnosticReportDTO] = None

    @classmethod
    def from_engine_response(cls, resp: RecoveryOptimizationResponse) -> "RecoveryOptimizationScenarioResponse":
        """Constructs DTO from accepted Milestone 2B RecoveryOptimizationResponse dataclass."""
        c_inr = Decimal(str(resp.total_cost_inr)) if not isinstance(resp.total_cost_inr, Decimal) else resp.total_cost_inr
        eq_inr = {
            k: (Decimal(str(v)) if not isinstance(v, Decimal) else v)
            for k, v in resp.district_equity_allocation_inr.items()
        }
        diag = None
        if resp.infeasibility_diagnostics:
            diag = InfeasibilityDiagnosticReportDTO.from_engine_report(resp.infeasibility_diagnostics)

        return cls(
            scenario_name=resp.scenario_name,
            solver_status=resp.solver_status,
            is_optimal=resp.is_optimal,
            exact_objective_value=resp.exact_objective_value,
            exact_best_bound=resp.exact_best_bound,
            conservative_best_bound=resp.conservative_best_bound,
            objective_value=resp.objective_value,
            best_bound=resp.best_bound,
            optimality_gap=resp.optimality_gap,
            solve_time_seconds=resp.solve_time_seconds,
            selected_project_count=resp.selected_project_count,
            total_cost_ccu=resp.total_cost_ccu,
            total_cost_inr=c_inr,
            scheduled_projects=[ScheduledProjectResultDTO.from_engine_result(p) for p in resp.scheduled_projects],
            periodic_solvency=[PeriodSolvencyResultDTO.from_engine_result(s) for s in resp.periodic_solvency],
            district_equity_allocation_ccu={k: int(v) for k, v in resp.district_equity_allocation_ccu.items()},
            district_equity_allocation_inr=eq_inr,
            input_fingerprint_sha256=resp.input_fingerprint_sha256,
            ortools_version=resp.ortools_version,
            solver_parameters=dict(resp.solver_parameters),
            infeasibility_diagnostics=diag,
        )


# ==============================================================================
# Structured Error DTOs
# ==============================================================================

class OptimizationErrorType(str, Enum):
    """Categorized failure types for recovery optimization API requests."""
    INVALID_REQUEST = "INVALID_REQUEST"
    PROVEN_INFEASIBILITY = "PROVEN_INFEASIBILITY"
    SOLVER_TIMEOUT = "SOLVER_TIMEOUT"
    FEASIBLE_SUBOPTIMAL = "FEASIBLE_SUBOPTIMAL"
    INTERNAL_EXECUTION_FAILURE = "INTERNAL_EXECUTION_FAILURE"


class OptimizationErrorDetailDTO(BaseModel):
    """Structured error response DTO for API validation and execution failures."""
    model_config = ConfigDict(extra="forbid")

    error_type: OptimizationErrorType
    message: str
    diagnostic_code: Optional[str] = None
    validation_failures: List[str] = Field(default_factory=list)
    input_fingerprint_sha256: Optional[str] = None
    infeasibility_diagnostics: Optional[InfeasibilityDiagnosticReportDTO] = None
