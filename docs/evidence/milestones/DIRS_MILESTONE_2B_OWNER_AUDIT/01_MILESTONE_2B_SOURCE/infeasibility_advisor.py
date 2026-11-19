"""
Infeasibility Diagnostic Advisor for Recovery CP-SAT Optimization.

Phase 6D-B Milestone 2B Implementation.
Classifies infeasibility across six formal categories:
1. AGGREGATE_BUDGET_EXCEEDED
2. PERIODIC_SOLVENCY_VIOLATION
3. RESOURCE_CAPACITY_EXCEEDED
4. PRECEDENCE_DEADLINE_CONFLICT
5. PLANNING_HORIZON_EXCEEDED
6. FUNDING_SOURCE_RESTRICTION

Applies the four-tier diagnostic hierarchy:
- PROVEN_INFEASIBILITY
- NECESSARY_CONDITION_VIOLATION
- WARNING
- SOLVER_ASSISTED_HYPOTHESIS

Explicitly disclaims minimality and uniqueness for solver assumption cores.
"""

from collections import defaultdict
from itertools import combinations
from typing import Any, Dict, List, Optional, Set, Tuple

from app.recovery.optimization.schemas import (
    InfeasibilityFinding,
    InfeasibilityDiagnosticReport,
    ProjectOptimizationCandidate,
    RecoveryOptimizationRequest,
    normalize_to_ccu,
)
from app.recovery.services.project_dependency_service import (
    ProjectDependencyService,
    DependencyEdge,
    ProjectActivity,
    CyclicDependencyError,
)


class InfeasibilityAdvisor:
    """
    Forensic diagnostic advisor isolating root causes and hypotheses
    when recovery optimization portfolios are infeasible.
    """

    @classmethod
    def analyze_presolve(
        cls,
        request: RecoveryOptimizationRequest,
        candidates_ccu: List[Tuple[ProjectOptimizationCandidate, int]], # (candidate, cost_ccu)
        budgets_ccu: Dict[int, int],
        initial_cash_ccu: int,
        cpm_results: Optional[Dict[str, Any]] = None,
    ) -> InfeasibilityDiagnosticReport:
        """
        Executes deterministic pre-solve checks across all 6 diagnostic categories.
        Identifies PROVEN_INFEASIBILITY, NECESSARY_CONDITION_VIOLATION, and WARNINGs.
        """
        proven: List[InfeasibilityFinding] = []
        necessary: List[InfeasibilityFinding] = []
        warnings: List[InfeasibilityFinding] = []

        mandatory_candidates = [
            (c, cost) for c, cost in candidates_ccu if c.is_tier1_mandatory
        ]
        horizon = request.planning_horizon_periods

        # =====================================================================
        # Category 1: AGGREGATE_BUDGET_EXCEEDED
        # =====================================================================
        total_mandatory_cost = sum(cost for _, cost in mandatory_candidates)
        total_available_budget = initial_cash_ccu + sum(budgets_ccu.values())

        if total_mandatory_cost > total_available_budget:
            proven.append(
                InfeasibilityFinding(
                    category="AGGREGATE_BUDGET_EXCEEDED",
                    classification="PROVEN_INFEASIBILITY",
                    message=(
                        f"Mandatory life-safety projects require {total_mandatory_cost} CCU, "
                        f"which exceeds total available budget of {total_available_budget} CCU."
                    ),
                    mathematical_condition=r"\sum_{j \in J_{mandatory}} c_j > \Phi_0 + \sum B_t",
                    affected_projects=[c.project_id for c, _ in mandatory_candidates],
                    details={
                        "mandatory_cost_ccu": total_mandatory_cost,
                        "available_budget_ccu": total_available_budget,
                        "deficit_ccu": total_mandatory_cost - total_available_budget,
                    },
                )
            )

        # =====================================================================
        # Category 4 & 5: PRECEDENCE, DEADLINE & PLANNING HORIZON CONFLICTS
        # =====================================================================
        # Topological cycle pre-check via Kahn's algorithm
        activities = [
            ProjectActivity(
                project_id=c.project_id,
                duration_days=float(c.duration_periods * request.period_length_days),
                duration_periods=c.duration_periods,
            )
            for c, _ in candidates_ccu
        ]
        edges = [
            DependencyEdge(
                predecessor_id=d.predecessor_id,
                successor_id=d.successor_id,
                lag_days=d.lag_periods * request.period_length_days,
            )
            for d in request.dependencies
        ]

        dag_analysis = None
        try:
            dag_analysis = ProjectDependencyService.analyze_network(
                activities=activities,
                edges=edges,
                period_days=request.period_length_days,
            )
        except CyclicDependencyError as e:
            proven.append(
                InfeasibilityFinding(
                    category="PRECEDENCE_DEADLINE_CONFLICT",
                    classification="PROVEN_INFEASIBILITY",
                    message=f"Cyclic dependency detected in project graph: {e.cycle_path}",
                    mathematical_condition=r"\exists \text{cycle} \in \mathcal{E}",
                    affected_projects=e.cycle_path,
                    details={"cycle_path": e.cycle_path},
                )
            )

        # Compute earliest starts (E_j) and latest starts (L_j)
        cand_map = {c.project_id: c for c, _ in candidates_ccu}
        earliest_starts: Dict[str, int] = {}
        latest_starts: Dict[str, int] = {}

        if dag_analysis and dag_analysis.cpm_results:
            # Map CPM topological results
            for c, _ in candidates_ccu:
                cpm = dag_analysis.cpm_results.get(c.project_id)
                cpm_start = (cpm.early_start + 1) if cpm else 1
                e_start = max(c.release_period, cpm_start)
                earliest_starts[c.project_id] = e_start

                # Initial deadline from candidate or horizon
                d_end = c.deadline_period if c.deadline_period is not None else horizon
                l_start = d_end - c.duration_periods + 1
                latest_starts[c.project_id] = l_start

            # Backward pass on latest starts using dependency lags
            topo_order = dag_analysis.topological_order
            pred_to_succs = defaultdict(list)
            for d in request.dependencies:
                pred_to_succs[d.predecessor_id].append((d.successor_id, d.lag_periods))

            for pid in reversed(topo_order):
                for succ_id, lag in pred_to_succs[pid]:
                    if succ_id in latest_starts and pid in cand_map:
                        c_pred = cand_map[pid]
                        bound = latest_starts[succ_id] - c_pred.duration_periods - lag
                        if bound < latest_starts[pid]:
                            latest_starts[pid] = bound
        else:
            for c, _ in candidates_ccu:
                earliest_starts[c.project_id] = c.release_period
                d_end = c.deadline_period if c.deadline_period is not None else horizon
                latest_starts[c.project_id] = d_end - c.duration_periods + 1

        # Check horizon and deadline violations for mandatory projects
        for c, _ in mandatory_candidates:
            e_start = earliest_starts.get(c.project_id, c.release_period)
            dur = c.duration_periods
            earliest_finish = e_start + dur - 1

            # Planning Horizon Exceeded
            if earliest_finish > horizon:
                proven.append(
                    InfeasibilityFinding(
                        category="PLANNING_HORIZON_EXCEEDED",
                        classification="PROVEN_INFEASIBILITY",
                        message=(
                            f"Mandatory project {c.project_id} earliest completion ({earliest_finish}) "
                            f"exceeds planning horizon {horizon}."
                        ),
                        mathematical_condition=r"E_j + d_j - 1 > T",
                        affected_projects=[c.project_id],
                        details={"earliest_finish": earliest_finish, "horizon": horizon},
                    )
                )

            # Deadline Conflict
            if c.deadline_period is not None and earliest_finish > c.deadline_period:
                proven.append(
                    InfeasibilityFinding(
                        category="PRECEDENCE_DEADLINE_CONFLICT",
                        classification="PROVEN_INFEASIBILITY",
                        message=(
                            f"Mandatory project {c.project_id} earliest completion ({earliest_finish}) "
                            f"exceeds hard deadline {c.deadline_period}."
                        ),
                        mathematical_condition=r"E_j + d_j - 1 > D_j",
                        affected_projects=[c.project_id],
                        details={"earliest_finish": earliest_finish, "deadline": c.deadline_period},
                    )
                )

        # =====================================================================
        # Category 2: PERIODIC_SOLVENCY_VIOLATION
        # =====================================================================
        # Build cumulative revenue trajectory: F_cum(t) = Phi_0 + sum_{s=1}^t B_s
        cumulative_revenue: Dict[int, int] = {}
        running_rev = initial_cash_ccu
        for t in range(1, horizon + 1):
            running_rev += budgets_ccu.get(t, 0)
            cumulative_revenue[t] = running_rev

        # Build periodic expenditure vectors for mandatory projects
        # profile e_{j, tau}
        mandatory_profiles: Dict[str, List[int]] = {}
        for c, cost in mandatory_candidates:
            dur = c.duration_periods
            weights = c.expenditure_weights if c.expenditure_weights else [1.0 / dur] * dur
            # Clamped base apportionment without per-period caps for lower bound
            total_w = sum(weights)
            allocs = [int((cost * w) / total_w) for w in weights]
            deficit = cost - sum(allocs)
            for i in range(deficit):
                allocs[i % dur] += 1
            mandatory_profiles[c.project_id] = allocs

        # 1. Latest-Start Cumulative Spend (Relaxation Lower Bound)
        k_late: Dict[int, int] = defaultdict(int)
        for c, cost in mandatory_candidates:
            l_start = latest_starts.get(c.project_id, horizon - c.duration_periods + 1)
            prof = mandatory_profiles[c.project_id]
            for tau, val in enumerate(prof, start=1):
                cal_t = l_start + tau - 1
                if 1 <= cal_t <= horizon:
                    k_late[cal_t] += val
                elif cal_t > horizon:
                    # Over horizon spend
                    pass

        # Cumulative k_late
        cum_k_late: Dict[int, int] = {}
        run_late = 0
        for t in range(1, horizon + 1):
            run_late += k_late[t]
            cum_k_late[t] = run_late

        solvency_failed_periods = [
            t for t in range(1, horizon + 1) if cum_k_late[t] > cumulative_revenue[t]
        ]
        if solvency_failed_periods:
            necessary.append(
                InfeasibilityFinding(
                    category="PERIODIC_SOLVENCY_VIOLATION",
                    classification="NECESSARY_CONDITION_VIOLATION",
                    message=(
                        f"Cumulative mandatory latest-start expenditure exceeds cumulative cash revenue "
                        f"in period(s) {solvency_failed_periods}."
                    ),
                    mathematical_condition=r"\exists t: \Phi_0 + \sum_{s=1}^t B_s < K_{late}(t)",
                    affected_projects=[c.project_id for c, _ in mandatory_candidates],
                    conflicting_periods=solvency_failed_periods,
                    details={
                        "failed_periods": solvency_failed_periods,
                        "deficits_ccu": {
                            t: cum_k_late[t] - cumulative_revenue[t] for t in solvency_failed_periods
                        },
                    },
                )
            )

        # 2. Earliest-Start Cumulative Spend (Warning)
        k_early: Dict[int, int] = defaultdict(int)
        for c, cost in mandatory_candidates:
            e_start = earliest_starts.get(c.project_id, 1)
            prof = mandatory_profiles[c.project_id]
            for tau, val in enumerate(prof, start=1):
                cal_t = e_start + tau - 1
                if 1 <= cal_t <= horizon:
                    k_early[cal_t] += val

        cum_k_early: Dict[int, int] = {}
        run_early = 0
        for t in range(1, horizon + 1):
            run_early += k_early[t]
            cum_k_early[t] = run_early

        early_deficit_periods = [
            t for t in range(1, horizon + 1)
            if cum_k_early[t] > cumulative_revenue[t] and t not in solvency_failed_periods
        ]
        if early_deficit_periods:
            warnings.append(
                InfeasibilityFinding(
                    category="PERIODIC_SOLVENCY_VIOLATION",
                    classification="WARNING",
                    message=(
                        f"Cash flow deficit occurs under earliest-start schedule in period(s) {early_deficit_periods}. "
                        "Schedule delay may resolve this if adequate slack exists."
                    ),
                    mathematical_condition=r"\exists t: \Phi_0 + \sum_{s=1}^t B_s < K_{early}(t)",
                    affected_projects=[c.project_id for c, _ in mandatory_candidates],
                    conflicting_periods=early_deficit_periods,
                )
            )

        # =====================================================================
        # Category 3: RESOURCE_CAPACITY_EXCEEDED
        # =====================================================================
        for r_id, cap_by_period in request.resource_capacities.items():
            total_r_capacity = sum(cap_by_period.get(t, 0) for t in range(1, horizon + 1))
            total_r_demand = sum(
                c.duration_periods * c.resource_demands.get(r_id, 0)
                for c, _ in mandatory_candidates
            )

            # Necessary condition: total demand across horizon vs total capacity
            if total_r_demand > total_r_capacity:
                necessary.append(
                    InfeasibilityFinding(
                        category="RESOURCE_CAPACITY_EXCEEDED",
                        classification="NECESSARY_CONDITION_VIOLATION",
                        message=(
                            f"Total mandatory demand for resource '{r_id}' ({total_r_demand}) "
                            f"exceeds total horizon capacity ({total_r_capacity})."
                        ),
                        mathematical_condition=r"\sum_{j \in J_{mandatory}} d_j u_{j, r} > \sum_{t=1}^T R_{r, t}",
                        affected_projects=[
                            c.project_id for c, _ in mandatory_candidates if c.resource_demands.get(r_id, 0) > 0
                        ],
                        details={"total_demand": total_r_demand, "total_capacity": total_r_capacity},
                    )
                )

            # Forced Core Concurrency Check:
            # Mandatory project j is guaranteed active in period t if L_j <= t <= E_j + d_j - 1
            core_demand_by_period: Dict[int, int] = defaultdict(int)
            core_projects_by_period: Dict[int, List[str]] = defaultdict(list)

            for c, _ in mandatory_candidates:
                u_demand = c.resource_demands.get(r_id, 0)
                if u_demand <= 0:
                    continue
                e_start = earliest_starts.get(c.project_id, 1)
                l_start = latest_starts.get(c.project_id, horizon - c.duration_periods + 1)
                e_finish = e_start + c.duration_periods - 1

                for t in range(1, horizon + 1):
                    if l_start <= t <= e_finish:
                        core_demand_by_period[t] += u_demand
                        core_projects_by_period[t].append(c.project_id)

            for t in range(1, horizon + 1):
                r_cap = cap_by_period.get(t, 0)
                if core_demand_by_period[t] > r_cap:
                    proven.append(
                        InfeasibilityFinding(
                            category="RESOURCE_CAPACITY_EXCEEDED",
                            classification="PROVEN_INFEASIBILITY",
                            message=(
                                f"Forced mandatory concurrency for resource '{r_id}' in period {t}: "
                                f"guaranteed demand {core_demand_by_period[t]} exceeds capacity {r_cap}."
                            ),
                            mathematical_condition=r"\sum_{j: t \in \mathcal{T}_j^{core}} u_{j, r} > R_{r, t}",
                            affected_projects=core_projects_by_period[t],
                            conflicting_periods=[t],
                            details={
                                "period": t,
                                "guaranteed_demand": core_demand_by_period[t],
                                "capacity": r_cap,
                            },
                        )
                    )

        # =====================================================================
        # Category 6: FUNDING_SOURCE_RESTRICTION (Model B Indivisible)
        # =====================================================================
        if request.funding_sources:
            fund_capacities_ccu: Dict[str, int] = {
                f.fund_id: normalize_to_ccu(f.capacity, f.currency, rounding_mode="floor")
                for f in request.funding_sources
            }

            # 1. Dedicated Funding Oversubscription Check
            dedicated_costs = defaultdict(int)
            dedicated_projects = defaultdict(list)
            for c, cost in mandatory_candidates:
                if len(c.eligible_funds) == 1:
                    fid = c.eligible_funds[0]
                    dedicated_costs[fid] += cost
                    dedicated_projects[fid].append(c.project_id)

            for fid, req_cost in dedicated_costs.items():
                cap = fund_capacities_ccu.get(fid, 0)
                if req_cost > cap:
                    proven.append(
                        InfeasibilityFinding(
                            category="FUNDING_SOURCE_RESTRICTION",
                            classification="PROVEN_INFEASIBILITY",
                            message=(
                                f"Mandatory projects dedicated exclusively to fund '{fid}' require "
                                f"{req_cost} CCU, exceeding fund capacity of {cap} CCU."
                            ),
                            mathematical_condition=r"\sum_{j \in J_{mandatory}: \mathcal{F}_j=\{f\}} c_j > F_f^{max}",
                            affected_projects=dedicated_projects[fid],
                            details={"fund_id": fid, "required_ccu": req_cost, "capacity_ccu": cap},
                        )
                    )

            # 2. Hall's Marriage Screening Condition (Necessary Condition Test)
            # For all subsets of mandatory projects (up to small subsets or small portfolio)
            if len(mandatory_candidates) <= 15:
                for k in range(1, len(mandatory_candidates) + 1):
                    for sub in combinations(mandatory_candidates, k):
                        sub_cost = sum(cost for _, cost in sub)
                        eligible_funds_union = set()
                        for c, _ in sub:
                            eligible_funds_union.update(c.eligible_funds)
                        total_sub_fund_cap = sum(fund_capacities_ccu.get(fid, 0) for fid in eligible_funds_union)
                        if sub_cost > total_sub_fund_cap:
                            necessary.append(
                                InfeasibilityFinding(
                                    category="FUNDING_SOURCE_RESTRICTION",
                                    classification="NECESSARY_CONDITION_VIOLATION",
                                    message=(
                                        f"Subset of {k} mandatory project(s) requires {sub_cost} CCU, "
                                        f"exceeding the aggregate capacity {total_sub_fund_cap} CCU of their eligible funds."
                                    ),
                                    mathematical_condition=r"\sum_{j \in \mathcal{S}} c_j > \sum_{f \in \bigcup \mathcal{F}_j} F_f^{max}",
                                    affected_projects=[c.project_id for c, _ in sub],
                                    details={"subset_cost_ccu": sub_cost, "eligible_capacity_ccu": total_sub_fund_cap},
                                )
                            )
                            break
                    if necessary and necessary[-1].category == "FUNDING_SOURCE_RESTRICTION":
                        break

        has_proven = len(proven) > 0
        return InfeasibilityDiagnosticReport(
            has_proven_infeasibility=has_proven,
            proven_causes=proven,
            necessary_condition_violations=necessary,
            solver_hypotheses=[],
            warnings=warnings,
            is_assumption_core_minimal=False,
        )

    @classmethod
    def analyze_solver_assumptions(
        cls,
        failed_assumption_names: List[str],
        presolve_report: InfeasibilityDiagnosticReport,
    ) -> InfeasibilityDiagnosticReport:
        """
        Extracts SOLVER_ASSISTED_HYPOTHESIS findings from CP-SAT assumption literals.
        Does NOT claim uniqueness or minimality.
        """
        hypotheses: List[InfeasibilityFinding] = []

        category_map = {
            "mand_": ("BUDGET", "Mandatory life-safety selection assumption conflicted."),
            "prec_": ("PRECEDENCE", "Precedence dependency constraint assumption conflicted."),
            "dead_": ("PRECEDENCE", "Project deadline constraint assumption conflicted."),
            "solv_": ("SOLVENCY", "Periodic cash-flow solvency constraint assumption conflicted."),
            "res_": ("RESOURCE", "Resource capacity constraint assumption conflicted."),
            "fund_": ("FUNDING", "Funding source allocation constraint assumption conflicted."),
            "eq_": ("BUDGET", "District equity floor constraint assumption conflicted."),
        }

        for name in failed_assumption_names:
            cat = "SOLVENCY"
            msg = f"Constraint assumption '{name}' contributed to solver conflict."
            for prefix, (c_name, c_msg) in category_map.items():
                if name.startswith(prefix):
                    cat = c_name
                    msg = c_msg
                    break

            hypotheses.append(
                InfeasibilityFinding(
                    category=cat,
                    classification="SOLVER_ASSISTED_HYPOTHESIS",
                    message=msg,
                    mathematical_condition="SufficientAssumptionsForInfeasibility()",
                    affected_projects=[name],
                    details={"assumption_literal": name},
                )
            )

        return InfeasibilityDiagnosticReport(
            has_proven_infeasibility=presolve_report.has_proven_infeasibility,
            proven_causes=presolve_report.proven_causes,
            necessary_condition_violations=presolve_report.necessary_condition_violations,
            solver_hypotheses=hypotheses,
            warnings=presolve_report.warnings,
            is_assumption_core_minimal=False,
        )
