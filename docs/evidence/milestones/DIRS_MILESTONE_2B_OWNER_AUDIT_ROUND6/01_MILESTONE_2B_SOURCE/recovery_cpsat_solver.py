"""
Google OR-Tools CP-SAT Recovery Optimization Engine.

Phase 6D-B Milestone 2B Implementation.
Builds and solves the equity-constrained, multi-period, multi-resource
recovery prioritization and scheduling integer programming model.
"""

from collections import defaultdict
from decimal import Decimal
import hashlib
import json
import logging
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import ortools
from ortools.sat.python import cp_model

from app.recovery.optimization.schemas import (
    CurrencyUnit,
    InfeasibilityFinding,
    InfeasibilityDiagnosticReport,
    PeriodSolvencyResult,
    ProjectOptimizationCandidate,
    RecoveryOptimizationRequest,
    RecoveryOptimizationResponse,
    ScheduledProjectResult,
    compute_canonical_input_fingerprint,
    deterministic_capped_apportionment,
    normalize_to_ccu,
    quantize_mcpi_score,
    unscale_ccu,
    validate_numerical_safety,
)
from app.recovery.optimization.infeasibility_advisor import InfeasibilityAdvisor
from app.recovery.services.calendar_cost_service import (
    CalendarCostService,
    DisbursementCurveType,
)

logger = logging.getLogger(__name__)


def compute_conservative_integer_best_bound(raw_best_bound: float) -> int:
    """Derive a mathematically conservative integer upper bound from raw BestObjectiveBound().

    Mathematical justification:
    For a maximization problem with integral objective coefficients and decision variables,
    the optimal objective is an integer Z* <= B*, where B* is the true dual bound.
    The solver exposes B* as an IEEE-754 binary64 float b = float(B*).

    1. Range |b| <= 2^53 (ulp(b) <= 1.0):
       Every integer in [-2^53, 2^53] is represented exactly in binary64 without rounding error.
       If b is continuous (e.g. fractional LP relaxation cut), math.ceil(b) safely bounds B*.
       Therefore, math.ceil(b) >= B* >= Z*.

    2. Range |b| > 2^53 (ulp(b) > 1.0):
       The spacing between representable floats is ulp(b) >= 2.
       If an integer B* was rounded down during conversion to float, B* - b <= ulp(b).
       Therefore, int(b) + math.ceil(ulp(b)) >= B* >= Z*.

    This guarantees that the derived integer bound never falls below the true mathematical bound,
    even up to the approved safety limit of 10^17 (where ulp = 16).
    """
    if math.isnan(raw_best_bound) or math.isinf(raw_best_bound):
        raise ValueError(f"Non-finite raw_best_bound: {raw_best_bound}")
    ulp = math.ulp(raw_best_bound)
    if ulp <= 1.0:
        return int(math.ceil(raw_best_bound))
    else:
        return int(raw_best_bound) + int(math.ceil(ulp))


class RecoveryCPSATSolver:
    """
    CP-SAT Optimization Engine for Post-Disaster Recovery Prioritization.
    """

    def __init__(self, request: RecoveryOptimizationRequest):
        self.request = request
        self.horizon = request.planning_horizon_periods
        self.ortools_version = getattr(ortools, "__version__", "9.15.6755")
        
        # Currency normalized caches (CCU integers)
        try:
            self.initial_cash_ccu = normalize_to_ccu(
                request.initial_cash, request.cash_currency, rounding_mode="floor"
            )
        except ValueError:
            self.initial_cash_ccu = -1

        self.periodic_budgets_ccu: Dict[int, int] = {}
        for t, b in request.periodic_budgets.items():
            try:
                self.periodic_budgets_ccu[t] = normalize_to_ccu(
                    b, request.budget_currency, rounding_mode="floor"
                )
            except ValueError:
                self.periodic_budgets_ccu[t] = -1

        if self.initial_cash_ccu >= 0 and all(v >= 0 for v in self.periodic_budgets_ccu.values()):
            self.total_budget_ccu = self.initial_cash_ccu + sum(self.periodic_budgets_ccu.values())
        else:
            self.total_budget_ccu = -1
        
        self.candidates_ccu: List[Tuple[ProjectOptimizationCandidate, int]] = []
        for c in request.candidates:
            try:
                c_cost = normalize_to_ccu(c.estimated_cost, c.cost_currency, rounding_mode="ceiling")
            except ValueError:
                c_cost = -1
            self.candidates_ccu.append((c, c_cost))
            
        self.funding_capacities_ccu: Dict[str, int] = {}
        for f in request.funding_sources:
            try:
                self.funding_capacities_ccu[f.fund_id] = normalize_to_ccu(
                    f.capacity, f.currency, rounding_mode="floor"
                )
            except ValueError:
                self.funding_capacities_ccu[f.fund_id] = -1

    def solve(self, enable_assumptions: bool = True) -> RecoveryOptimizationResponse:
        """
        Builds and solves the CP-SAT optimization model.
        Returns a structured RecoveryOptimizationResponse.
        """
        start_time = time.perf_counter()
        
        # 1. Pre-Model Numerical Safety Validation (Section 5)
        try:
            validate_numerical_safety(self.request)
        except ValueError as ex:
            return self._build_invalid_response(
                f"Numerical safety violation: {ex}",
                start_time
            )

        # 2. Input Sanity Pre-Checks
        if self.horizon < 1 or self.request.period_length_days <= 0:
            return self._build_invalid_response(
                "Planning horizon must be >= 1 and period length must be > 0.",
                start_time
            )

        if self.initial_cash_ccu < 0:
            return self._build_invalid_response(
                f"Initial cash cannot be negative, got {self.request.initial_cash}.",
                start_time
            )

        for t, b in self.periodic_budgets_ccu.items():
            if t < 1 or t > self.horizon:
                return self._build_invalid_response(
                    f"Periodic budget period {t} outside planning horizon [1, {self.horizon}].",
                    start_time
                )
            if b < 0:
                return self._build_invalid_response(
                    f"Periodic budget at period {t} cannot be negative, got {b}.",
                    start_time
                )

        if self.request.fiscal_retention_rate != 1.0:
            return self._build_invalid_response(
                f"Unsupported fiscal_retention_rate {self.request.fiscal_retention_rate}. Only 1.0 supported in Model B.",
                start_time
            )

        for f in self.request.funding_sources:
            if f.period_tranches:
                return self._build_invalid_response(
                    f"Funding source '{f.fund_id}' has unsupported period_tranches. Model B only supports static capacity.",
                    start_time
                )
            if self.funding_capacities_ccu.get(f.fund_id, 0) < 0:
                return self._build_invalid_response(
                    f"Funding source '{f.fund_id}' capacity cannot be negative.",
                    start_time
                )

        if self.request.max_safety_start_period is not None:
            if self.request.max_safety_start_period < 1 or self.request.max_safety_start_period > self.horizon:
                return self._build_invalid_response(
                    f"max_safety_start_period {self.request.max_safety_start_period} outside planning horizon [1, {self.horizon}].",
                    start_time
                )

        cand_ids = [c.project_id for c in self.request.candidates]
        if len(cand_ids) != len(set(cand_ids)):
            return self._build_invalid_response(
                "Duplicate project IDs detected in candidates.",
                start_time
            )

        fund_ids = [f.fund_id for f in self.request.funding_sources]
        if len(fund_ids) != len(set(fund_ids)):
            return self._build_invalid_response(
                "Duplicate fund IDs detected in funding sources.",
                start_time
            )

        cand_id_set = set(cand_ids)
        for dep in self.request.dependencies:
            if dep.predecessor_id == dep.successor_id:
                return self._build_invalid_response(
                    f"Self-dependency detected: {dep.predecessor_id} -> {dep.successor_id}.",
                    start_time
                )
            if dep.predecessor_id not in cand_id_set or dep.successor_id not in cand_id_set:
                return self._build_invalid_response(
                    f"Dependency references unknown project: {dep.predecessor_id} -> {dep.successor_id}.",
                    start_time
                )

        for c, cost in self.candidates_ccu:
            if c.duration_periods < 1:
                return self._build_invalid_response(
                    f"Project {c.project_id} duration must be >= 1, got {c.duration_periods}.",
                    start_time
                )
            if cost < 0:
                return self._build_invalid_response(
                    f"Project {c.project_id} cost cannot be negative, got {cost}.",
                    start_time
                )
            if c.raw_mcpi_score < 0.0 or c.raw_mcpi_score > 1.0:
                return self._build_invalid_response(
                    f"Project {c.project_id} raw MCPI score must be in [0, 1], got {c.raw_mcpi_score}.",
                    start_time
                )
            if c.release_period < 1:
                return self._build_invalid_response(
                    f"Project {c.project_id} release period must be >= 1, got {c.release_period}.",
                    start_time
                )
            if c.deadline_period is not None and c.deadline_period < 1:
                return self._build_invalid_response(
                    f"Project {c.project_id} deadline must be >= 1, got {c.deadline_period}.",
                    start_time
                )
            for r_id, r_dem in c.resource_demands.items():
                if r_dem < 0:
                    return self._build_invalid_response(
                        f"Project {c.project_id} has negative resource demand for {r_id}: {r_dem}.",
                        start_time
                    )
            if c.expenditure_weights is not None:
                if len(c.expenditure_weights) != c.duration_periods:
                    return self._build_invalid_response(
                        f"Project {c.project_id} expenditure weights length {len(c.expenditure_weights)} != duration {c.duration_periods}.",
                        start_time
                    )
                if any(w < 0 for w in c.expenditure_weights) or sum(c.expenditure_weights) <= 0:
                    return self._build_invalid_response(
                        f"Project {c.project_id} expenditure weights must be non-negative with positive sum.",
                        start_time
                    )
            elif not self.request.allow_uniform_weight_fallback:
                return self._build_invalid_response(
                    f"Project '{c.project_id}' has no expenditure weights and allow_uniform_weight_fallback is False.",
                    start_time
                )

        # Mandatory Life-Safety Deadline Authorization Check (RSK-M2-01, RSK-M2-07)
        has_mandatory = any(c.is_tier1_mandatory for c, _ in self.candidates_ccu)
        if has_mandatory:
            if self.request.max_safety_start_period is None:
                return self._build_invalid_response(
                    "Request contains mandatory life-safety projects but max_safety_start_period (T_safety_max) is None. An explicit authorized safety deadline is required.",
                    start_time,
                )
            if self.request.max_safety_start_period < 1 or self.request.max_safety_start_period > self.horizon:
                return self._build_invalid_response(
                    f"max_safety_start_period ({self.request.max_safety_start_period}) must be between 1 and planning_horizon_periods ({self.horizon}).",
                    start_time,
                )

        # 3. Pre-Solve Diagnostic Screening
        presolve_diagnostics = InfeasibilityAdvisor.analyze_presolve(
            request=self.request,
            candidates_ccu=self.candidates_ccu,
            budgets_ccu=self.periodic_budgets_ccu,
            initial_cash_ccu=self.initial_cash_ccu,
        )

        model = cp_model.CpModel()
        assumptions: Dict[str, cp_model.IntVar] = {}

        # 3. Decision Variables
        w: Dict[str, cp_model.IntVar] = {}              # Selection boolean w_j
        x: Dict[Tuple[str, int], cp_model.IntVar] = {}  # Start indicator x_{j, t}
        start_var: Dict[str, cp_model.IntVar] = {}      # S_j
        end_var: Dict[str, cp_model.IntVar] = {}        # C_j^end
        interval_var: Dict[str, cp_model.IntervalVar] = {} # I_j optional interval
        z: Dict[Tuple[str, str], cp_model.IntVar] = {}  # Funding assignment z_{j, f}

        candidate_map = {c.project_id: (c, cost) for c, cost in self.candidates_ccu}

        for c, cost in self.candidates_ccu:
            pid = c.project_id
            dur = c.duration_periods
            w[pid] = model.NewBoolVar(f"w_{pid}")
            
            # Start domain: t in [release_period, min(deadline - dur + 1, horizon - dur + 1)]
            latest_permitted_start = self.horizon - dur + 1
            if c.deadline_period is not None:
                latest_permitted_start = min(latest_permitted_start, c.deadline_period - dur + 1)

            earliest_permitted_start = max(1, c.release_period)

            # Feasible start domain
            feasible_starts = [
                t for t in range(earliest_permitted_start, latest_permitted_start + 1)
            ]

            start_var[pid] = model.NewIntVar(1, self.horizon, f"start_{pid}")
            end_var[pid] = model.NewIntVar(1, self.horizon + 1, f"end_{pid}")
            interval_var[pid] = model.NewOptionalIntervalVar(
                start_var[pid], dur, end_var[pid], w[pid], f"interval_{pid}"
            )

            if feasible_starts:
                for t in feasible_starts:
                    x[(pid, t)] = model.NewBoolVar(f"x_{pid}_{t}")
                # Start uniqueness: sum_t x_{j, t} == w_j
                model.Add(sum(x[(pid, t)] for t in feasible_starts) == w[pid])
                # Start period linking: S_j == sum_t (t * x_{j, t}) when w_j == 1
                model.Add(start_var[pid] == sum(t * x[(pid, t)] for t in feasible_starts)).OnlyEnforceIf(w[pid])
                model.Add(start_var[pid] == 1).OnlyEnforceIf(w[pid].Not())
            else:
                # If no feasible start periods exist within horizon/deadline, w[pid] must be 0
                model.Add(w[pid] == 0)
                model.Add(start_var[pid] == 1)

            # Mandatory Life-Safety Hard Mandate (RSK-M2-01 Option A, Inviolable)
            if c.is_tier1_mandatory:
                # Unconditional hard constraint: cannot be relaxed by solver assumptions
                model.Add(w[pid] == 1)

                # Mandatory Life-Safety Start Deadline Constraint (Constraint 11, RSK-M2-01)
                # Hard constraint: S_j <= T_safety_max (cannot be relaxed by solver assumptions)
                if self.request.max_safety_start_period is not None:
                    t_safety = self.request.max_safety_start_period
                    model.Add(start_var[pid] <= t_safety).OnlyEnforceIf(w[pid])

            # Indivisible Funding Assignment (RSK-M2-06 Model B)
            if self.request.funding_sources:
                eligible = [fid for fid in c.eligible_funds if fid in self.funding_capacities_ccu]
                if eligible:
                    for fid in eligible:
                        z[(pid, fid)] = model.NewBoolVar(f"z_{pid}_{fid}")
                    # Sum of eligible fund assignments == w[pid]
                    model.Add(sum(z[(pid, fid)] for fid in eligible) == w[pid])
                else:
                    # If project has no eligible funds configured, it cannot be funded
                    model.Add(w[pid] == 0)

        # Funding Source Capacity Limits (Model B)
        if self.request.funding_sources:
            for f in self.request.funding_sources:
                fid = f.fund_id
                f_cap = self.funding_capacities_ccu[fid]
                assigned_costs = [
                    cost * z[(c.project_id, fid)]
                    for c, cost in self.candidates_ccu
                    if (c.project_id, fid) in z
                ]
                if assigned_costs:
                    if enable_assumptions:
                        fund_lit = model.NewBoolVar(f"fund_{fid}")
                        assumptions[f"fund_{fid}"] = fund_lit
                        model.Add(sum(assigned_costs) <= f_cap).OnlyEnforceIf(fund_lit)
                    else:
                        model.Add(sum(assigned_costs) <= f_cap)

        # 4. Dependency Precedence & Lags
        for dep in self.request.dependencies:
            pred_id = dep.predecessor_id
            succ_id = dep.successor_id
            lag = dep.lag_periods
            if pred_id in w and succ_id in w:
                # Selection Precedence: w_succ <= w_pred
                model.Add(w[succ_id] <= w[pred_id])
                
                # Timing Precedence: S_succ >= S_pred + d_pred + lag
                pred_c, _ = candidate_map[pred_id]
                d_pred = pred_c.duration_periods
                if enable_assumptions:
                    prec_lit = model.NewBoolVar(f"prec_{pred_id}_{succ_id}")
                    assumptions[f"prec_{pred_id}_{succ_id}"] = prec_lit
                    model.Add(start_var[succ_id] >= start_var[pred_id] + d_pred + lag).OnlyEnforceIf(
                        [w[succ_id], prec_lit]
                    )
                else:
                    model.Add(start_var[succ_id] >= start_var[pred_id] + d_pred + lag).OnlyEnforceIf(w[succ_id])

        # 5. Project Expenditure Profiles & Periodic Convolution
        project_profiles: Dict[str, List[int]] = {}
        for c, cost in self.candidates_ccu:
            dur = c.duration_periods
            if c.expenditure_weights is not None:
                weights = c.expenditure_weights
            elif self.request.allow_uniform_weight_fallback:
                weights = CalendarCostService.generate_gamma_profile(
                    dur, DisbursementCurveType.UNIFORM
                )
            else:
                return self._build_invalid_response(
                    f"Project '{c.project_id}' has no expenditure weights and allow_uniform_weight_fallback is False.",
                    start_time,
                )
            # Apportion integer CCUs across duration periods using capped apportionment
            profile_allocs = deterministic_capped_apportionment(
                cost_c=cost,
                weights_w=weights,
                caps_e_bar=[cost] * dur,  # unbounded by external period caps for unconstrained baseline
                eligible_periods=set(range(1, dur + 1)),
                allow_uniform_fallback=self.request.allow_uniform_weight_fallback,
            )
            project_profiles[c.project_id] = profile_allocs

        # Convolution: E_{j, t} expressions
        # Period expenditure for each project at calendar period t
        period_project_spend: Dict[Tuple[str, int], Any] = {}
        for c, cost in self.candidates_ccu:
            pid = c.project_id
            dur = c.duration_periods
            prof = project_profiles[pid]
            for t in range(1, self.horizon + 1):
                # Terms where s in [max(1, t - dur + 1), t]
                terms = []
                for s in range(max(1, t - dur + 1), t + 1):
                    if (pid, s) in x:
                        tau = t - s + 1 # 1-based index in profile
                        alloc_ccu = prof[tau - 1]
                        if alloc_ccu > 0:
                            terms.append(alloc_ccu * x[(pid, s)])
                if terms:
                    period_project_spend[(pid, t)] = sum(terms)

        # 6. Periodic Solvency Recurrence (Full Retention eta = 1.0)
        # Cumulative spend up to period t <= Phi_0 + sum_{s=1}^t B_s
        cumulative_budget_up_to_t: Dict[int, int] = {}
        running_b = self.initial_cash_ccu
        for t in range(1, self.horizon + 1):
            running_b += self.periodic_budgets_ccu.get(t, 0)
            cumulative_budget_up_to_t[t] = running_b

        for t in range(1, self.horizon + 1):
            cum_spend_terms = []
            for s in range(1, t + 1):
                for c, _ in self.candidates_ccu:
                    if (c.project_id, s) in period_project_spend:
                        cum_spend_terms.append(period_project_spend[(c.project_id, s)])
            
            if cum_spend_terms:
                b_limit = cumulative_budget_up_to_t[t]
                if enable_assumptions:
                    solv_lit = model.NewBoolVar(f"solv_{t}")
                    assumptions[f"solv_{t}"] = solv_lit
                    model.Add(sum(cum_spend_terms) <= b_limit).OnlyEnforceIf(solv_lit)
                else:
                    model.Add(sum(cum_spend_terms) <= b_limit)

        # 7. District Policy Equity Floors
        for d_id, quota_theta in self.request.district_equity_targets.items():
            district_candidates = [
                (c, cost) for c, cost in self.candidates_ccu if c.district_id == d_id
            ]
            if district_candidates:
                district_demand = sum(cost for _, cost in district_candidates)
                quota_target = int(math.ceil(Decimal(str(quota_theta)) * Decimal(str(self.total_budget_ccu))))
                clamped_floor = min(quota_target, district_demand)
                
                if clamped_floor > 0:
                    district_costs = [cost * w[c.project_id] for c, cost in district_candidates]
                    if enable_assumptions:
                        eq_lit = model.NewBoolVar(f"eq_{d_id}")
                        assumptions[f"eq_{d_id}"] = eq_lit
                        model.Add(sum(district_costs) >= clamped_floor).OnlyEnforceIf(eq_lit)
                    else:
                        model.Add(sum(district_costs) >= clamped_floor)

        # 8. Uncontacted Blackout District Ring-Fencing
        if self.request.blackout_districts:
            blackout_reserve = 0
            for d_id in self.request.blackout_districts:
                theta = self.request.district_equity_targets.get(d_id, 0.0)
                if theta > 0:
                    r_d = int(math.ceil(Decimal(str(theta)) * Decimal(str(self.total_budget_ccu))))
                    blackout_reserve += r_d
            if blackout_reserve > 0:
                allocable_cap = self.total_budget_ccu - blackout_reserve
                all_project_costs = [cost * w[c.project_id] for c, cost in self.candidates_ccu]
                model.Add(sum(all_project_costs) <= allocable_cap)

        # 9. Renewable Resource Capacity Limits
        for r_id, cap_by_period in self.request.resource_capacities.items():
            for t in range(1, self.horizon + 1):
                r_cap = cap_by_period.get(t, 0)
                demands_at_t = []
                for c, _ in self.candidates_ccu:
                    u_demand = c.resource_demands.get(r_id, 0)
                    if u_demand > 0:
                        dur = c.duration_periods
                        # Active starts: s in [max(1, t - dur + 1), t]
                        active_starts = [
                            x[(c.project_id, s)]
                            for s in range(max(1, t - dur + 1), t + 1)
                            if (c.project_id, s) in x
                        ]
                        if active_starts:
                            demands_at_t.append(u_demand * sum(active_starts))
                if demands_at_t:
                    if enable_assumptions:
                        res_lit = model.NewBoolVar(f"res_{r_id}_{t}")
                        assumptions[f"res_{r_id}_{t}"] = res_lit
                        model.Add(sum(demands_at_t) <= r_cap).OnlyEnforceIf(res_lit)
                    else:
                        model.Add(sum(demands_at_t) <= r_cap)

        # 10. Multi-Objective Function Assembly
        # Scale: Pi_bar_j = floor(raw_mcpi_score * 10^7)
        # Non-compensatory acceleration scaling: M_accel = N * (T - 1) + 1
        num_candidates = len(self.candidates_ccu)
        if self.request.enable_early_start_bonus and self.horizon > 1 and num_candidates > 0:
            m_accel = num_candidates * (self.horizon - 1) + 1
        else:
            m_accel = 1

        objective_terms = []
        for c, _ in self.candidates_ccu:
            pid = c.project_id
            pi_bar = quantize_mcpi_score(c.raw_mcpi_score)

            # Substantive MCPI contribution: (M_accel * Pi_bar_j) * w_j
            substantive_coeff = m_accel * pi_bar
            objective_terms.append(substantive_coeff * w[pid])

            if self.request.enable_early_start_bonus and self.horizon > 1:
                dur = c.duration_periods
                latest_s = self.horizon - dur + 1
                if c.deadline_period is not None:
                    latest_s = min(latest_s, c.deadline_period - dur + 1)
                for s in range(max(1, c.release_period), latest_s + 1):
                    if (pid, s) in x:
                        # Acceleration weight: T - s
                        accel_bonus = self.horizon - s
                        objective_terms.append(accel_bonus * x[(pid, s)])

        model.Maximize(sum(objective_terms))

        # 11. Configure CP-SAT Solver & Reproducibility Parameters
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = self.request.num_workers
        solver.parameters.random_seed = self.request.deterministic_seed
        solver.parameters.max_time_in_seconds = self.request.max_solve_time_seconds

        # Track assumptions if enabled
        literal_index_to_name: Dict[int, str] = {}
        if enable_assumptions and assumptions:
            for name, lit in assumptions.items():
                model.AddAssumption(lit)
                idx = lit.Index()
                literal_index_to_name[idx] = name
                literal_index_to_name[lit.Not().Index()] = name
                literal_index_to_name[~idx] = name

        solve_status = solver.Solve(model)
        solve_duration = time.perf_counter() - start_time

        # 12. Parse Solution Status & Extract Forensic Metadata
        status_str_map = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "MODEL_INVALID",
            cp_model.UNKNOWN: "UNKNOWN",
        }
        status_name = status_str_map.get(solve_status, "UNKNOWN")

        # Infeasibility diagnostics
        final_diagnostics = None
        if status_name == "INFEASIBLE":
            failed_literals = []
            if enable_assumptions:
                try:
                    # Clear objective on cloned pure-feasibility model for sufficient assumption core extraction (sufficient subset, not claimed minimal or unique)
                    diag_model = model.Clone()
                    diag_model.ClearObjective()
                    diag_solver = cp_model.CpSolver()
                    diag_solver.parameters.num_search_workers = 1
                    diag_solver.parameters.random_seed = self.request.deterministic_seed
                    diag_solver.parameters.max_time_in_seconds = min(5.0, self.request.max_solve_time_seconds)
                    diag_status = diag_solver.Solve(diag_model)
                    if diag_status == cp_model.INFEASIBLE:
                        core_indices = diag_solver.SufficientAssumptionsForInfeasibility()
                    else:
                        core_indices = solver.SufficientAssumptionsForInfeasibility()

                    for item in core_indices:
                        idx = item.Index() if hasattr(item, "Index") else int(item)
                        name = literal_index_to_name.get(idx)
                        if name and name not in failed_literals:
                            failed_literals.append(name)
                except Exception as ex:
                    logger.warning(f"Failed to extract sufficient assumptions: {ex}")
                    try:
                        for item in solver.SufficientAssumptionsForInfeasibility():
                            idx = item.Index() if hasattr(item, "Index") else int(item)
                            name = literal_index_to_name.get(idx)
                            if name and name not in failed_literals:
                                failed_literals.append(name)
                    except Exception:
                        pass
            final_diagnostics = InfeasibilityAdvisor.analyze_solver_assumptions(
                failed_assumption_names=failed_literals,
                presolve_report=presolve_diagnostics,
            )

        # Build Scheduled Results
        scheduled_projects: List[ScheduledProjectResult] = []
        periodic_solvency: List[PeriodSolvencyResult] = []
        equity_allocations_ccu: Dict[str, int] = defaultdict(int)

        total_selected_cost_ccu = 0
        obj_val = None
        best_bnd = None
        opt_gap = None
        exact_obj_val = None
        exact_best_bnd = None
        conservative_best_bnd = None

        if status_name in ("OPTIMAL", "FEASIBLE"):
            exact_obj_val = 0
            for c, _ in self.candidates_ccu:
                pid = c.project_id
                if solver.Value(w[pid]) == 1:
                    pi_bar = quantize_mcpi_score(c.raw_mcpi_score)
                    exact_obj_val += m_accel * pi_bar
                    if self.request.enable_early_start_bonus and self.horizon > 1:
                        s_val = int(solver.Value(start_var[pid]))
                        exact_obj_val += (self.horizon - s_val)

            obj_val = float(exact_obj_val)
            if status_name == "OPTIMAL":
                exact_best_bnd = exact_obj_val
                conservative_best_bnd = exact_obj_val
                best_bnd = float(exact_obj_val)
                opt_gap = 0.0
            else:
                raw_best_bnd = solver.BestObjectiveBound()
                best_bnd = float(raw_best_bnd)
                try:
                    conservative_best_bnd = compute_conservative_integer_best_bound(raw_best_bnd)
                except (ValueError, OverflowError):
                    conservative_best_bnd = None
                exact_best_bnd = conservative_best_bnd
                if best_bnd > 0:
                    opt_gap = abs(best_bnd - obj_val) / best_bnd
                else:
                    opt_gap = 0.0

            for c, cost in self.candidates_ccu:
                pid = c.project_id
                is_sel = bool(solver.Value(w[pid]) == 1)
                s_period = None
                c_period = None
                assigned_fund = None

                project_expenditures_ccu: Dict[int, int] = defaultdict(int)

                if is_sel:
                    total_selected_cost_ccu += cost
                    equity_allocations_ccu[c.district_id] += cost
                    
                    dur = c.duration_periods
                    s_period = int(solver.Value(start_var[pid]))
                    c_period = s_period + dur - 1

                    prof = project_profiles[pid]
                    for tau, p_val in enumerate(prof, start=1):
                        cal_t = s_period + tau - 1
                        project_expenditures_ccu[cal_t] = p_val

                    # Assigned fund
                    if self.request.funding_sources:
                        for fid in c.eligible_funds:
                            if (pid, fid) in z and solver.Value(z[(pid, fid)]) == 1:
                                assigned_fund = fid
                                break

                project_expenditures_inr = {
                    t: unscale_ccu(v, CurrencyUnit.INR)
                    for t, v in project_expenditures_ccu.items()
                }

                scheduled_projects.append(
                    ScheduledProjectResult(
                        project_id=pid,
                        project_code=c.project_code,
                        district_id=c.district_id,
                        is_selected=is_sel,
                        scheduled_start_period=s_period,
                        scheduled_completion_period=c_period,
                        assigned_funding_source=assigned_fund,
                        cost_ccu=cost if is_sel else 0,
                        cost_inr=unscale_ccu(cost, CurrencyUnit.INR) if is_sel else Decimal("0"),
                        periodic_expenditures_ccu=dict(project_expenditures_ccu),
                        periodic_expenditures_inr=project_expenditures_inr,
                        mcpi_score=round(c.raw_mcpi_score * 100.0, 4),
                        raw_mcpi_score=c.raw_mcpi_score,
                        quantized_mcpi_coefficient=quantize_mcpi_score(c.raw_mcpi_score),
                        is_tier1_mandatory=c.is_tier1_mandatory,
                    )
                )

            # Evaluate Periodic Cash Balances
            running_cash = self.initial_cash_ccu
            for t in range(1, self.horizon + 1):
                t_rev = self.periodic_budgets_ccu.get(t, 0)
                t_spend = sum(
                    p.periodic_expenditures_ccu.get(t, 0) for p in scheduled_projects
                )
                running_cash = running_cash + t_rev - t_spend
                periodic_solvency.append(
                    PeriodSolvencyResult(
                        period=t,
                        revenue_receipt_ccu=t_rev,
                        expenditure_ccu=t_spend,
                        cash_balance_ccu=running_cash,
                        cash_balance_inr=unscale_ccu(running_cash, CurrencyUnit.INR),
                        is_solvent=running_cash >= 0,
                    )
                )

        equity_allocations_inr = {
            d: unscale_ccu(v, CurrencyUnit.INR)
            for d, v in equity_allocations_ccu.items()
        }

        fingerprint = self._compute_input_fingerprint()

        return RecoveryOptimizationResponse(
            scenario_name=self.request.scenario_name,
            solver_status=status_name,
            is_optimal=(status_name == "OPTIMAL"),
            objective_value=obj_val,
            best_bound=best_bnd,
            optimality_gap=opt_gap,
            solve_time_seconds=round(solve_duration, 4),
            selected_project_count=sum(1 for p in scheduled_projects if p.is_selected),
            total_cost_ccu=total_selected_cost_ccu,
            total_cost_inr=unscale_ccu(total_selected_cost_ccu, CurrencyUnit.INR),
            scheduled_projects=scheduled_projects,
            periodic_solvency=periodic_solvency,
            district_equity_allocation_ccu=dict(equity_allocations_ccu),
            district_equity_allocation_inr=equity_allocations_inr,
            input_fingerprint_sha256=fingerprint,
            ortools_version=self.ortools_version,
            solver_parameters={
                "num_search_workers": self.request.num_workers,
                "random_seed": self.request.deterministic_seed,
                "max_time_in_seconds": self.request.max_solve_time_seconds,
            },
            infeasibility_diagnostics=final_diagnostics,
            exact_objective_value=exact_obj_val,
            exact_best_bound=exact_best_bnd,
            conservative_best_bound=conservative_best_bnd,
        )

    def _build_invalid_response(self, error_msg: str, start_time: float) -> RecoveryOptimizationResponse:
        """Returns structured MODEL_INVALID response."""
        return RecoveryOptimizationResponse(
            scenario_name=self.request.scenario_name,
            solver_status="MODEL_INVALID",
            is_optimal=False,
            objective_value=None,
            best_bound=None,
            optimality_gap=None,
            exact_objective_value=None,
            exact_best_bound=None,
            conservative_best_bound=None,
            solve_time_seconds=round(time.perf_counter() - start_time, 4),
            selected_project_count=0,
            total_cost_ccu=0,
            total_cost_inr=Decimal("0"),
            scheduled_projects=[],
            periodic_solvency=[],
            district_equity_allocation_ccu={},
            district_equity_allocation_inr={},
            input_fingerprint_sha256=self._compute_input_fingerprint(),
            ortools_version=self.ortools_version,
            solver_parameters={},
            infeasibility_diagnostics=InfeasibilityDiagnosticReport(
                has_proven_infeasibility=True,
                proven_causes=[
                    InfeasibilityFinding(
                        category="MODEL_INVALID",
                        classification="PROVEN_INFEASIBILITY",
                        message=error_msg,
                        mathematical_condition="Input domain validation check failed",
                        affected_projects=[],
                    )
                ],
                necessary_condition_violations=[],
                solver_hypotheses=[],
                warnings=[],
            ),
        )

    def _compute_input_fingerprint(self) -> str:
        """Computes deterministic SHA-256 hash of canonical input attributes."""
        return compute_canonical_input_fingerprint(self.request)
