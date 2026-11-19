"""
Internal Policy District Equity Pure Mathematical Service.

Phase 6D-B Milestone 1 Domain Implementation (DEF-M1-03 Remediation).
Calculates internal policy district equity floors, configurable district allocation
targets, unabsorbed policy reserve escrows, and uncontacted blackout reserves:
- Internal policy district equity floor: E_d = theta_d * B.
- Configurable district allocation target (dynamic capacity bound):
    E_d^target = min(theta_d * B, sum_{j in J_d} c_j).
- Unabsorbed policy reserve escrow: Delta R_d = max(0, theta_d * B - sum_{j in J_d} c_j).
- Uncontacted blackout reserve: R_blackout = sum_{d in D_blackout} rho_d * B.
- Rigorous separation of policy reserves from spendable cash liquidity.
- Unabsorbed reserves are NOT automatically released or converted into spendable cash.

Pure mathematical logic: independent of database persistence and API routes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class DistrictEquitySpec:
    """Internal administrative policy equity floor specification for a district."""
    district_id: str
    district_name: str
    policy_floor_ratio: float         # theta_d (e.g. 0.15 for 15% internal policy allocation target)
    is_blackout: bool = False         # True if district is under communication/recon blackout
    blackout_reserve_ratio: float = 0.0 # rho_d: portion of budget held in reserve if blackout


@dataclass
class DistrictProjectPipeline:
    """Project pipeline in a district."""
    district_id: str
    total_pipeline_cost: float        # sum_{j in J_d} c_j
    project_ids: List[str] = field(default_factory=list)


@dataclass
class DistrictEquityTarget:
    """Computed internal policy target and dynamic capacity for a district."""
    district_id: str
    policy_nominal_floor: float        # theta_d * B (internal policy equity floor)
    pipeline_capacity: float           # sum_{j in J_d} c_j (eligible project absorption capacity)
    effective_allocation_target: float # min(policy_nominal_floor, pipeline_capacity)
    unabsorbed_policy_reserve: float   # max(0, policy_nominal_floor - pipeline_capacity)
    is_capacity_constrained: bool      # pipeline < policy_nominal_floor
    blackout_reserve_amount: float     # rho_d * B if blackout else 0.0
    policy_disclosure: str             # Explains administrative status and non-spendability


@dataclass
class PortfolioEquityAudit:
    """Audit result verifying portfolio allocations against configurable district policy targets."""
    total_budget: float
    total_blackout_reserve: float
    net_allocatable_budget: float
    district_targets: Dict[str, DistrictEquityTarget]
    district_allocated: Dict[str, float]
    district_feasible: Dict[str, bool]
    is_equity_feasible: bool           # True if all districts meet effective allocation target
    violations: List[str]
    liquidity_separation_note: str     # Explicit disclosure on equity reserve vs spendable liquidity


class EquityCalculationService:
    """
    Pure mathematical engine for internal policy district equity floors and capacity balancing.
    """
    POLICY_DISCLOSURE_TEXT: str = (
        "District equity targets are internal administrative policy allocation constraints, "
        "NOT statutory mandates. Unabsorbed policy reserves represent policy ring-fencing and are "
        "NOT actual financial escrow accounts, bank deposits, fund transfers, or cash restrictions. "
        "They are mathematical allocation boundaries within optimization models; no financial persistence "
        "or transaction integration exists in Milestone 1."
    )

    LIQUIDITY_SEPARATION_NOTE: str = (
        "Strict accounting separation of concepts: "
        "(1) District policy reserve requirement: mathematical allocation floor (theta_d * B); "
        "(2) Eligible project absorption: total verified pipeline cost in district (sum c_j); "
        "(3) Unabsorbed policy reserve: ring-fenced mathematical difference max(0, theta_d * B - sum c_j); "
        "(4) Actual period expenditure: time-indexed capital disbursements (sum C_{j, t}); "
        "(5) Available cash liquidity: periodic liquid balance from cash-flow carry-forward (Phi_t); "
        "(6) Contingency funds: discretionary unallocated reserves. "
        "An unabsorbed policy reserve is NOT automatically spendable cash liquidity."
    )

    @classmethod
    def calculate_district_targets(
        cls,
        total_budget: float,
        districts: List[DistrictEquitySpec],
        pipelines: Dict[str, DistrictProjectPipeline],
    ) -> Tuple[Dict[str, DistrictEquityTarget], float]:
        """
        Calculates configurable district allocation targets, dynamic capacity bounds,
        unabsorbed policy reserves, and uncontacted blackout reserves.
        """
        if total_budget < 0.0:
            raise ValueError(f"Total budget cannot be negative, got {total_budget}")

        targets: Dict[str, DistrictEquityTarget] = {}
        total_blackout_reserve = 0.0

        for dist in districts:
            if dist.policy_floor_ratio < 0.0 or dist.policy_floor_ratio > 1.0:
                raise ValueError(
                    f"District {dist.district_id} policy floor ratio must be in [0.0, 1.0], got {dist.policy_floor_ratio}"
                )

            nominal_floor = round(total_budget * dist.policy_floor_ratio, 4)
            pipeline = pipelines.get(dist.district_id)
            pipeline_cost = pipeline.total_pipeline_cost if pipeline else 0.0

            effective_target = round(min(nominal_floor, pipeline_cost), 4)
            unabsorbed_reserve = round(max(0.0, nominal_floor - pipeline_cost), 4)
            is_cap_constrained = pipeline_cost < nominal_floor

            blackout_amt = 0.0
            if dist.is_blackout:
                if dist.blackout_reserve_ratio <= 0.0:
                    ratio = dist.policy_floor_ratio
                else:
                    ratio = dist.blackout_reserve_ratio
                blackout_amt = round(total_budget * ratio, 4)
                total_blackout_reserve = round(total_blackout_reserve + blackout_amt, 4)

            targets[dist.district_id] = DistrictEquityTarget(
                district_id=dist.district_id,
                policy_nominal_floor=nominal_floor,
                pipeline_capacity=pipeline_cost,
                effective_allocation_target=effective_target,
                unabsorbed_policy_reserve=unabsorbed_reserve,
                is_capacity_constrained=is_cap_constrained,
                blackout_reserve_amount=blackout_amt,
                policy_disclosure=cls.POLICY_DISCLOSURE_TEXT,
            )

        return targets, total_blackout_reserve

    @classmethod
    def audit_equity_feasibility(
        cls,
        total_budget: float,
        districts: List[DistrictEquitySpec],
        pipelines: Dict[str, DistrictProjectPipeline],
        allocated_by_district: Dict[str, float],
    ) -> PortfolioEquityAudit:
        """
        Verifies whether an allocation portfolio satisfies internal policy district equity floors:
        allocated_d >= effective_allocation_target_d for all districts.
        """
        targets, total_blackout = cls.calculate_district_targets(total_budget, districts, pipelines)
        net_budget = round(total_budget - total_blackout, 4)

        district_feasible: Dict[str, bool] = {}
        violations: List[str] = []

        for dist_id, target in targets.items():
            alloc = allocated_by_district.get(dist_id, 0.0)
            if alloc >= (target.effective_allocation_target - 1e-4):
                district_feasible[dist_id] = True
            else:
                district_feasible[dist_id] = False
                shortfall = round(target.effective_allocation_target - alloc, 4)
                violations.append(
                    f"District '{dist_id}' allocated {alloc:.2f} < policy target {target.effective_allocation_target:.2f} "
                    f"(shortfall: {shortfall:.2f})"
                )

        is_feasible = (len(violations) == 0)

        return PortfolioEquityAudit(
            total_budget=total_budget,
            total_blackout_reserve=total_blackout,
            net_allocatable_budget=net_budget,
            district_targets=targets,
            district_allocated=allocated_by_district,
            district_feasible=district_feasible,
            is_equity_feasible=is_feasible,
            violations=violations,
            liquidity_separation_note=cls.LIQUIDITY_SEPARATION_NOTE,
        )
