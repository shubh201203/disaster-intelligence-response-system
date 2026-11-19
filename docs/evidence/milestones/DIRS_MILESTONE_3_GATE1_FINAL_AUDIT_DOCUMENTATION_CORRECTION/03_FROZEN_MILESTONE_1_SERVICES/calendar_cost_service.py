"""
Calendar Cost and Multi-Period Disbursement Pure Mathematical Service.

Phase 6D-B Milestone 1 Domain Implementation.
Provides multi-period calendar expenditure convolution, cash-flow disbursement profiling,
and discrete period <-> calendar date mappings:
- Convolution of project age tau into calendar periods t: C_{j, t} = c_j * gamma_{j, t - s_j + 1}.
- Standard civil engineering expenditure curves: UNIFORM, FRONT_LOADED, BACK_LOADED, S_CURVE.
- Exact lifetime cost reconciliation sum(C_{j, t}) == c_j.
- UTC calendar date to discrete period mapping and boundary conventions.
- Explicit justification for multi-day period duration (e.g., Delta t = 30 days vs. 1 day).

Pure mathematical logic: independent of database persistence and API routes.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import math
from typing import Dict, List, Optional, Tuple, Union


class DisbursementCurveType(str, Enum):
    """Standard infrastructure expenditure profile shapes."""
    UNIFORM = "UNIFORM"
    FRONT_LOADED = "FRONT_LOADED"
    BACK_LOADED = "BACK_LOADED"
    S_CURVE = "S_CURVE"
    CUSTOM = "CUSTOM"


@dataclass
class ProjectDisbursementSpec:
    """Disbursement specification for a single project."""
    project_id: str
    total_cost: float                # c_j >= 0
    duration_periods: int            # D_j >= 1
    start_period: int                # s_j >= 1 (1-indexed calendar period)
    curve_type: DisbursementCurveType = DisbursementCurveType.UNIFORM
    custom_gamma: Optional[List[float]] = None # Optional custom weights of length D_j summing to 1.0


@dataclass
class PeriodBoundary:
    """Calendar date range for a single discrete optimization period."""
    period_index: int                # 1-indexed (1, 2, ..., T)
    start_date: date                 # Inclusive start date (UTC)
    end_date: date                   # Exclusive end date (UTC)
    duration_days: int


@dataclass
class ProjectExpenditureSchedule:
    """Disbursement schedule over planning horizon T."""
    project_id: str
    total_cost: float
    start_period: int
    duration_periods: int
    end_period: int                  # s_j + D_j - 1
    periodic_costs: Dict[int, float] # t -> C_{j, t}
    gamma_profile: List[float]       # tau -> gamma_tau
    is_fully_reconciled: bool        # sum(C_{j, t}) == total_cost


class CalendarCostService:
    """
    Pure mathematical service for multi-period cost distribution and calendar alignment.
    """
    DEFAULT_PERIOD_DAYS: int = 30
    BOUNDARY_JUSTIFICATION: str = (
        "The nominal 30-day planning period (Delta t = 30 days) is an engineering implementation "
        "convention chosen for computational tractability and alignment with monthly fiscal disbursement "
        "cycles; it is NOT a statutory mandate or mathematical requirement of Phase 6A. "
        "The period duration Delta t is fully configurable. UTC boundary conventions are strictly "
        "applied: Period t covers the half-open interval [T_0 + (t-1)*Delta t, T_0 + t*Delta t). "
        "Timestamp conversion evaluates t = floor((D - T_0) / Delta t) + 1. Dependency lags in days "
        "convert to periods using ceiling: ceil(L_days / Delta t). If a project's duration extends beyond "
        "the planning horizon T (s_j + D_j - 1 > T), the partial final period expenditure occurring after "
        "period T is truncated from the planning horizon, and is_fully_reconciled is flagged False."
    )

    @classmethod
    def generate_gamma_profile(
        cls,
        duration_periods: int,
        curve_type: DisbursementCurveType = DisbursementCurveType.UNIFORM,
        custom_gamma: Optional[List[float]] = None,
    ) -> List[float]:
        """
        Generates normalized disbursement weights gamma_tau for tau = 1, ..., D_j.
        Sum of weights strictly equals 1.0.
        """
        if duration_periods < 1:
            raise ValueError(f"Duration periods must be at least 1, got {duration_periods}")

        if duration_periods == 1:
            return [1.0]

        if curve_type == DisbursementCurveType.CUSTOM:
            if custom_gamma is None or len(custom_gamma) != duration_periods:
                raise ValueError(
                    f"Custom gamma must have exactly {duration_periods} elements, got {len(custom_gamma) if custom_gamma else 0}"
                )
            if any(g < 0.0 for g in custom_gamma):
                raise ValueError("Custom gamma weights cannot be negative")
            total = sum(custom_gamma)
            if total <= 0.0:
                raise ValueError("Sum of custom gamma weights must be positive")
            return [g / total for g in custom_gamma]

        if curve_type == DisbursementCurveType.UNIFORM:
            w = 1.0 / duration_periods
            return [w] * duration_periods

        if curve_type == DisbursementCurveType.FRONT_LOADED:
            # Linearly decreasing weights: highest at tau=1, lowest at tau=D
            raw = [duration_periods - tau + 1 for tau in range(1, duration_periods + 1)]
            total = sum(raw)
            return [r / total for r in raw]

        if curve_type == DisbursementCurveType.BACK_LOADED:
            # Linearly increasing weights: lowest at tau=1, highest at tau=D
            raw = [tau for tau in range(1, duration_periods + 1)]
            total = sum(raw)
            return [r / total for r in raw]

        if curve_type == DisbursementCurveType.S_CURVE:
            # Bell/Logistic shape: peak in the middle
            # Uses sine squared function as smooth approximation: sin^2(pi * (tau - 0.5) / D)
            raw = [
                math.sin(math.pi * (tau - 0.5) / duration_periods) ** 2
                for tau in range(1, duration_periods + 1)
            ]
            total = sum(raw)
            return [r / total for r in raw]

        raise ValueError(f"Unsupported curve type: {curve_type}")

    @classmethod
    def convolve_expenditure(
        cls,
        spec: ProjectDisbursementSpec,
        planning_horizon_periods: int,
    ) -> ProjectExpenditureSchedule:
        """
        Convolves project cost into calendar time steps:
        C_{j, t} = c_j * gamma_{j, t - s_j + 1} for s_j <= t <= s_j + D_j - 1.
        """
        if spec.total_cost < 0.0:
            raise ValueError(f"Total cost cannot be negative, got {spec.total_cost}")
        if spec.start_period < 1:
            raise ValueError(f"Start period must be >= 1, got {spec.start_period}")
        if planning_horizon_periods < 1:
            raise ValueError(f"Planning horizon must be >= 1, got {planning_horizon_periods}")

        gamma = cls.generate_gamma_profile(spec.duration_periods, spec.curve_type, spec.custom_gamma)
        end_period = spec.start_period + spec.duration_periods - 1

        periodic_costs: Dict[int, float] = {t: 0.0 for t in range(1, planning_horizon_periods + 1)}

        for tau_idx, g in enumerate(gamma):
            tau = tau_idx + 1 # 1-indexed project age
            t = spec.start_period + tau - 1
            if 1 <= t <= planning_horizon_periods:
                periodic_costs[t] = round(spec.total_cost * g, 4)

        total_disbursed = sum(periodic_costs.values())
        reconciled = (
            abs(total_disbursed - spec.total_cost) < 1e-2
            if end_period <= planning_horizon_periods
            else False # If project extends past planning horizon, full cost is not realized within horizon
        )

        return ProjectExpenditureSchedule(
            project_id=spec.project_id,
            total_cost=spec.total_cost,
            start_period=spec.start_period,
            duration_periods=spec.duration_periods,
            end_period=end_period,
            periodic_costs=periodic_costs,
            gamma_profile=gamma,
            is_fully_reconciled=reconciled,
        )

    @classmethod
    def aggregate_portfolio_expenditure(
        cls,
        specs: List[ProjectDisbursementSpec],
        planning_horizon_periods: int,
    ) -> Dict[int, float]:
        """Calculates total portfolio expenditure E_t = sum_j C_{j, t} for each period t."""
        total_e: Dict[int, float] = {t: 0.0 for t in range(1, planning_horizon_periods + 1)}
        for spec in specs:
            sched = cls.convolve_expenditure(spec, planning_horizon_periods)
            for t, cost in sched.periodic_costs.items():
                total_e[t] = round(total_e[t] + cost, 4)
        return total_e

    @classmethod
    def build_calendar_periods(
        cls,
        anchor_date: Union[date, datetime],
        num_periods: int,
        period_days: Optional[int] = None,
    ) -> List[PeriodBoundary]:
        """
        Builds discrete period boundaries from anchor date (UTC):
        Period t covers [T_0 + (t-1)*delta_t, T_0 + t*delta_t).
        """
        delta_t = period_days if period_days is not None else cls.DEFAULT_PERIOD_DAYS
        if delta_t <= 0:
            raise ValueError(f"Period days must be positive, got {delta_t}")
        if num_periods <= 0:
            raise ValueError(f"Number of periods must be positive, got {num_periods}")

        if isinstance(anchor_date, datetime):
            base_date = anchor_date.astimezone(timezone.utc).date() if anchor_date.tzinfo else anchor_date.date()
        else:
            base_date = anchor_date

        boundaries: List[PeriodBoundary] = []
        for t in range(1, num_periods + 1):
            start = base_date + timedelta(days=(t - 1) * delta_t)
            end = base_date + timedelta(days=t * delta_t)
            boundaries.append(PeriodBoundary(
                period_index=t,
                start_date=start,
                end_date=end,
                duration_days=delta_t,
            ))
        return boundaries

    @classmethod
    def map_date_to_period(
        cls,
        target_date: Union[date, datetime],
        anchor_date: Union[date, datetime],
        period_days: Optional[int] = None,
    ) -> int:
        """
        Maps a calendar date D to 1-indexed period index:
        t = floor((D - T_0) / delta_t) + 1.
        """
        delta_t = period_days if period_days is not None else cls.DEFAULT_PERIOD_DAYS
        
        d_target = target_date.astimezone(timezone.utc).date() if isinstance(target_date, datetime) and target_date.tzinfo else (target_date.date() if isinstance(target_date, datetime) else target_date)
        d_anchor = anchor_date.astimezone(timezone.utc).date() if isinstance(anchor_date, datetime) and anchor_date.tzinfo else (anchor_date.date() if isinstance(anchor_date, datetime) else anchor_date)

        days_diff = (d_target - d_anchor).days
        if days_diff < 0:
            raise ValueError(f"Target date {d_target} precedes anchor date {d_anchor}")

        return (days_diff // delta_t) + 1
