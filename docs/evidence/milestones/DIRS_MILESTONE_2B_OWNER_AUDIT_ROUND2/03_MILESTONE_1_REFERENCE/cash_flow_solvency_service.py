"""
Multi-Period Cash-Flow Solvency Pure Mathematical Service.

Phase 6D-B Milestone 1 Domain Implementation.
Calculates periodic liquidity balances, carry-forward dynamics, shortfall quantification,
and multi-fund ring-fencing constraints:
- Recurrence relation: Phi_t = eta * Phi_{t-1} + B_t - E_t.
- Hard solvency verification: Phi_t >= 0 for all t in {1, ..., T}.
- Quantified deficit identification (earliest deficit period and cumulative shortfalls).
- Multi-fund ring-fencing (prevents cross-subsidization between restricted funds).

Pure mathematical logic: independent of database persistence and API routes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class FundTranchePlan:
    """Inflow tranches and initial reserve for a specific funding source."""
    fund_id: str
    initial_reserve: float = 0.0      # Phi_{f, 0} >= 0
    inflows_by_period: Dict[int, float] = field(default_factory=dict) # t -> B_{f, t}
    carry_forward_factor: float = 1.0 # eta in (0.0, 1.0] (1.0 = 100% rollover)

    def __post_init__(self):
        if self.initial_reserve < 0.0:
            raise ValueError(f"Initial reserve cannot be negative, got {self.initial_reserve}")
        if self.carry_forward_factor <= 0.0 or self.carry_forward_factor > 1.0:
            raise ValueError(f"Carry-forward factor eta must be in (0.0, 1.0], got {self.carry_forward_factor}")
        for t, b in self.inflows_by_period.items():
            if t < 1:
                raise ValueError(f"Period index must be >= 1, got {t}")
            if b < 0.0:
                raise ValueError(f"Tranche inflow at period {t} cannot be negative, got {b}")


@dataclass
class PeriodSolvencyStatus:
    """Solvency state at end of discrete period t."""
    period: int
    beginning_balance: float          # eta * Phi_{t-1}
    inflow: float                     # B_t
    expenditure: float                # E_t
    ending_balance: float             # Phi_t
    is_solvent: bool                  # Phi_t >= 0
    shortfall: float                  # max(0, -Phi_t)


@dataclass
class FundSolvencyTrajectory:
    """Trajectory across all periods for a single fund."""
    fund_id: str
    is_fully_solvent: bool
    earliest_deficit_period: Optional[int]
    maximum_shortfall: float
    total_shortfall_volume: float
    periods: Dict[int, PeriodSolvencyStatus]


@dataclass
class PortfolioSolvencyAudit:
    """Comprehensive portfolio solvency audit across all ring-fenced funds."""
    is_portfolio_solvent: bool
    fund_trajectories: Dict[str, FundSolvencyTrajectory]
    aggregate_ending_balance: Dict[int, float] # t -> sum_f Phi_{f, t}
    violations: List[str]


class CashFlowSolvencyService:
    """
    Pure mathematical engine for multi-period liquidity and carry-forward solvency.
    """

    @classmethod
    def evaluate_fund_trajectory(
        cls,
        fund_plan: FundTranchePlan,
        expenditures_by_period: Dict[int, float],
        planning_horizon_periods: int,
    ) -> FundSolvencyTrajectory:
        """
        Calculates Phi_t = eta * Phi_{t-1} + B_t - E_t for t = 1, ..., T.
        """
        if planning_horizon_periods < 1:
            raise ValueError(f"Planning horizon must be >= 1, got {planning_horizon_periods}")

        statuses: Dict[int, PeriodSolvencyStatus] = {}
        phi_prev = fund_plan.initial_reserve
        is_fully_solvent = True
        earliest_deficit = None
        max_shortfall = 0.0
        total_shortfall = 0.0

        for t in range(1, planning_horizon_periods + 1):
            beginning = round(fund_plan.carry_forward_factor * phi_prev, 4)
            b_t = round(fund_plan.inflows_by_period.get(t, 0.0), 4)
            e_t = round(expenditures_by_period.get(t, 0.0), 4)

            phi_t = round(beginning + b_t - e_t, 4)
            is_solvent = phi_t >= -1e-6
            shortfall = round(max(0.0, -phi_t), 4)

            if not is_solvent:
                is_fully_solvent = False
                if earliest_deficit is None:
                    earliest_deficit = t
                if shortfall > max_shortfall:
                    max_shortfall = shortfall
                total_shortfall = round(total_shortfall + shortfall, 4)

            statuses[t] = PeriodSolvencyStatus(
                period=t,
                beginning_balance=beginning,
                inflow=b_t,
                expenditure=e_t,
                ending_balance=phi_t,
                is_solvent=is_solvent,
                shortfall=shortfall,
            )

            phi_prev = phi_t

        return FundSolvencyTrajectory(
            fund_id=fund_plan.fund_id,
            is_fully_solvent=is_fully_solvent,
            earliest_deficit_period=earliest_deficit,
            maximum_shortfall=max_shortfall,
            total_shortfall_volume=total_shortfall,
            periods=statuses,
        )

    @classmethod
    def audit_multi_fund_portfolio(
        cls,
        fund_plans: List[FundTranchePlan],
        expenditures_by_fund_and_period: Dict[str, Dict[int, float]],
        planning_horizon_periods: int,
    ) -> PortfolioSolvencyAudit:
        """
        Audits multi-fund solvency with ring-fencing.
        Cross-subsidization between funds is disallowed:
        Every individual fund f must satisfy Phi_{f, t} >= 0 for all t.
        """
        trajectories: Dict[str, FundSolvencyTrajectory] = {}
        violations: List[str] = []
        is_portfolio_solvent = True

        for plan in fund_plans:
            exp_map = expenditures_by_fund_and_period.get(plan.fund_id, {})
            traj = cls.evaluate_fund_trajectory(plan, exp_map, planning_horizon_periods)
            trajectories[plan.fund_id] = traj
            if not traj.is_fully_solvent:
                is_portfolio_solvent = False
                violations.append(
                    f"Fund '{plan.fund_id}' violates solvency at period {traj.earliest_deficit_period} "
                    f"(max shortfall: {traj.maximum_shortfall:.2f})"
                )

        # Aggregate ending balances across funds for audit visibility
        agg_balances: Dict[int, float] = {t: 0.0 for t in range(1, planning_horizon_periods + 1)}
        for traj in trajectories.values():
            for t, status in traj.periods.items():
                agg_balances[t] = round(agg_balances[t] + status.ending_balance, 4)

        return PortfolioSolvencyAudit(
            is_portfolio_solvent=is_portfolio_solvent,
            fund_trajectories=trajectories,
            aggregate_ending_balance=agg_balances,
            violations=violations,
        )
