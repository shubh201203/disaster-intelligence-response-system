"""
Recovery Optimization Orchestrator Service.

Phase 6D-B Milestone 2B Implementation.
Coordinates the end-to-end recovery optimization pipeline:
1. Input validation & pre-solve graph cycle detection.
2. Pre-model numerical safety validation.
3. Google OR-Tools CP-SAT solver invocation.
4. Independent post-solve mathematical reconciliation (10-point audit).
5. Structured reporting and deterministic reproducibility metadata.
"""

from collections import defaultdict
from decimal import Decimal
import logging
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from app.recovery.optimization.schemas import (
    CurrencyUnit,
    InfeasibilityDiagnosticReport,
    InfeasibilityFinding,
    PeriodSolvencyResult,
    RecoveryOptimizationRequest,
    RecoveryOptimizationResponse,
    ScheduledProjectResult,
    compute_canonical_input_fingerprint,
    normalize_to_ccu,
    unscale_ccu,
    validate_numerical_safety,
)
from app.recovery.optimization.recovery_cpsat_solver import RecoveryCPSATSolver
from app.recovery.optimization.infeasibility_advisor import InfeasibilityAdvisor
from app.recovery.services.project_dependency_service import (
    ProjectDependencyService,
    DependencyEdge,
    ProjectActivity,
    CyclicDependencyError,
)

logger = logging.getLogger(__name__)


class RecoveryOptimizationOrchestrator:
    """
    High-level orchestrator coordinating CP-SAT solver execution,
    diagnostic screening, input contract validation, and post-solve audits.
    """

    @classmethod
    def validate_request(
        cls,
        request: RecoveryOptimizationRequest,
        raise_on_error: bool = False,
    ) -> List[str]:
        """
        Validates request against all mathematical and contract constraints (Section 8).
        Optionally raises ValueError on the first violation.
        """
        errors: List[str] = []

        # 1. Numerical safety check
        try:
            validate_numerical_safety(request)
        except ValueError as ex:
            errors.append(f"NUMERICAL_SAFETY_VIOLATION: {ex}")

        # 2. Planning horizon and period length
        if request.planning_horizon_periods < 1:
            errors.append(f"Planning horizon must be >= 1, got {request.planning_horizon_periods}")
        if request.period_length_days <= 0:
            errors.append(f"Period length must be > 0, got {request.period_length_days}")

        # 3. Fiscal retention rate (Section 8A - Model B requires exactly 1.0)
        if request.fiscal_retention_rate != 1.0:
            errors.append(
                f"Unsupported fiscal_retention_rate {request.fiscal_retention_rate}. "
                f"Model B only supports full retention (1.0)."
            )

        # 4. Cash and budget non-negativity
        try:
            init_cash = normalize_to_ccu(request.initial_cash, request.cash_currency, rounding_mode="floor")
            if init_cash < 0:
                errors.append(f"Initial cash cannot be negative, got {request.initial_cash}")
        except ValueError as ex:
            errors.append(f"Initial cash cannot be negative: {ex}")

        for t, b in request.periodic_budgets.items():
            if t < 1 or t > request.planning_horizon_periods:
                errors.append(
                    f"Periodic budget period {t} outside planning horizon [1, {request.planning_horizon_periods}]"
                )
            try:
                b_ccu = normalize_to_ccu(b, request.budget_currency, rounding_mode="floor")
                if b_ccu < 0:
                    errors.append(f"Periodic budget at period {t} cannot be negative, got {b}")
            except ValueError as ex:
                errors.append(f"Invalid periodic budget at period {t}: {ex}")

        # 5. Funding sources & tranches (Section 8B)
        fund_ids = [f.fund_id for f in request.funding_sources]
        if len(fund_ids) != len(set(fund_ids)):
            errors.append(f"Duplicate fund IDs detected in funding sources: {fund_ids}")

        for f in request.funding_sources:
            if f.period_tranches:
                errors.append(
                    f"Funding source '{f.fund_id}' specifies period_tranches which are unsupported in Model B."
                )
            try:
                cap_ccu = normalize_to_ccu(f.capacity, f.currency, rounding_mode="floor")
                if cap_ccu < 0:
                    errors.append(f"Funding source '{f.fund_id}' capacity cannot be negative, got {f.capacity}")
            except ValueError as ex:
                errors.append(f"Invalid capacity for fund '{f.fund_id}': {ex}")

        # 6. Safety deadline validation
        if request.max_safety_start_period is not None:
            if request.max_safety_start_period < 1 or request.max_safety_start_period > request.planning_horizon_periods:
                errors.append(
                    f"max_safety_start_period {request.max_safety_start_period} outside planning horizon [1, {request.planning_horizon_periods}]"
                )

        # 7. Candidate validations (Section 8E)
        cand_ids = [c.project_id for c in request.candidates]
        if len(cand_ids) != len(set(cand_ids)):
            errors.append(f"Duplicate project IDs detected in candidates: {cand_ids}")

        cand_id_set = set(cand_ids)
        for c in request.candidates:
            if c.duration_periods < 1:
                errors.append(f"Project '{c.project_id}' duration must be >= 1, got {c.duration_periods}")
            try:
                c_cost = normalize_to_ccu(c.estimated_cost, c.cost_currency, rounding_mode="ceiling")
                if c_cost < 0:
                    errors.append(f"Project '{c.project_id}' cost cannot be negative, got {c.estimated_cost}")
            except ValueError as ex:
                errors.append(f"Invalid cost for project '{c.project_id}': {ex}")

            if c.raw_mcpi_score < 0.0 or c.raw_mcpi_score > 1.0:
                errors.append(f"Project '{c.project_id}' raw MCPI score must be in [0, 1], got {c.raw_mcpi_score}")

            if c.release_period < 1:
                errors.append(f"Project '{c.project_id}' release period must be >= 1, got {c.release_period}")

            if c.deadline_period is not None and c.deadline_period < 1:
                errors.append(f"Project '{c.project_id}' deadline must be >= 1, got {c.deadline_period}")

            for r_id, dem in c.resource_demands.items():
                if dem < 0:
                    errors.append(f"Project '{c.project_id}' has negative resource demand for '{r_id}': {dem}")

            # Expenditure weights check (Section 8D)
            if c.expenditure_weights is not None:
                if len(c.expenditure_weights) != c.duration_periods:
                    errors.append(
                        f"Project '{c.project_id}' expenditure weights length {len(c.expenditure_weights)} "
                        f"!= duration {c.duration_periods}"
                    )
                if any(w < 0 for w in c.expenditure_weights) or sum(c.expenditure_weights) <= 0:
                    errors.append(
                        f"Project '{c.project_id}' expenditure weights must be non-negative with sum > 0"
                    )
            elif not request.allow_uniform_weight_fallback:
                errors.append(
                    f"Project '{c.project_id}' has no expenditure weights and allow_uniform_weight_fallback is False."
                )

        # 8. Dependency validations (Section 8E)
        for dep in request.dependencies:
            if dep.predecessor_id == dep.successor_id:
                errors.append(f"Self-dependency detected: {dep.predecessor_id} -> {dep.successor_id}")
            if dep.predecessor_id not in cand_id_set:
                errors.append(f"Dependency predecessor '{dep.predecessor_id}' not found in candidate list")
            if dep.successor_id not in cand_id_set:
                errors.append(f"Dependency successor '{dep.successor_id}' not found in candidate list")
            if dep.lag_periods < 0:
                errors.append(f"Dependency lag cannot be negative, got {dep.lag_periods}")

        # 9. Resource capacity validations
        for r_id, caps in request.resource_capacities.items():
            for t, cap in caps.items():
                if t < 1 or t > request.planning_horizon_periods:
                    errors.append(
                        f"Resource '{r_id}' period key {t} outside planning horizon [1, {request.planning_horizon_periods}]"
                    )
                if cap < 0:
                    errors.append(f"Resource '{r_id}' capacity at period {t} cannot be negative, got {cap}")

        if errors and raise_on_error:
            raise ValueError("; ".join(errors))

        return errors

    @classmethod
    def optimize_recovery_portfolio(
        cls,
        request: RecoveryOptimizationRequest,
    ) -> RecoveryOptimizationResponse:
        """
        Executes complete recovery optimization pipeline for a portfolio scenario.
        """
        # Step 1: Full Input Validation (Section 8E, 8F)
        validation_errors = cls.validate_request(request, raise_on_error=False)
        if validation_errors:
            return cls._build_invalid_response(request, "; ".join(validation_errors))

        # Step 2: Handle Empty Portfolio Case (Section 8F)
        if not request.candidates:
            solver = RecoveryCPSATSolver(request)
            init_cash = normalize_to_ccu(request.initial_cash, request.cash_currency, rounding_mode="floor")
            periodic_budgets = {
                t: normalize_to_ccu(request.periodic_budgets.get(t, 0), request.budget_currency, rounding_mode="floor")
                for t in range(1, request.planning_horizon_periods + 1)
            }
            running_cash = init_cash
            solvency_list = []
            for t in range(1, request.planning_horizon_periods + 1):
                running_cash += periodic_budgets.get(t, 0)
                solvency_list.append(
                    PeriodSolvencyResult(
                        period=t,
                        revenue_receipt_ccu=periodic_budgets.get(t, 0),
                        expenditure_ccu=0,
                        cash_balance_ccu=running_cash,
                        cash_balance_inr=unscale_ccu(running_cash, CurrencyUnit.INR),
                        is_solvent=running_cash >= 0,
                    )
                )

            return RecoveryOptimizationResponse(
                scenario_name=request.scenario_name,
                solver_status="OPTIMAL",
                is_optimal=True,
                objective_value=0.0,
                best_bound=0.0,
                optimality_gap=0.0,
                solve_time_seconds=0.0,
                selected_project_count=0,
                total_cost_ccu=0,
                total_cost_inr=Decimal("0"),
                scheduled_projects=[],
                periodic_solvency=solvency_list,
                district_equity_allocation_ccu={},
                district_equity_allocation_inr={},
                input_fingerprint_sha256=compute_canonical_input_fingerprint(request),
                ortools_version=solver.ortools_version,
                solver_parameters={
                    "num_search_workers": request.num_workers,
                    "random_seed": request.deterministic_seed,
                    "max_time_in_seconds": request.max_solve_time_seconds,
                },
                infeasibility_diagnostics=None,
            )

        # Step 3: Validate Graph Acyclicity via Milestone 1 Kahn Toposort
        nodes = [c.project_id for c in request.candidates]
        edges = [
            DependencyEdge(
                predecessor_id=d.predecessor_id,
                successor_id=d.successor_id,
                lag_days=d.lag_periods * request.period_length_days,
            )
            for d in request.dependencies
        ]

        try:
            ProjectDependencyService.detect_cycle_and_toposort(
                nodes=nodes,
                edges=edges,
            )
        except CyclicDependencyError as e:
            solver = RecoveryCPSATSolver(request)
            return RecoveryOptimizationResponse(
                scenario_name=request.scenario_name,
                solver_status="MODEL_INVALID",
                is_optimal=False,
                objective_value=None,
                best_bound=None,
                optimality_gap=None,
                solve_time_seconds=0.001,
                selected_project_count=0,
                total_cost_ccu=0,
                total_cost_inr=Decimal("0"),
                scheduled_projects=[],
                periodic_solvency=[],
                district_equity_allocation_ccu={},
                district_equity_allocation_inr={},
                input_fingerprint_sha256=compute_canonical_input_fingerprint(request),
                ortools_version=solver.ortools_version,
                solver_parameters={},
                infeasibility_diagnostics=InfeasibilityDiagnosticReport(
                    has_proven_infeasibility=True,
                    proven_causes=[
                        InfeasibilityFinding(
                            category="PRECEDENCE_DEADLINE_CONFLICT",
                            classification="PROVEN_INFEASIBILITY",
                            message=f"Cyclic dependency detected: {e.cycle_path}",
                            mathematical_condition=r"\exists \text{cycle} \in \mathcal{E}",
                            affected_projects=e.cycle_path,
                            details={"cycle_path": e.cycle_path},
                        )
                    ],
                    necessary_condition_violations=[],
                    solver_hypotheses=[],
                    warnings=[],
                ),
            )

        # Step 4: Instantiate Solver & Execute Search
        solver = RecoveryCPSATSolver(request)
        response = solver.solve(enable_assumptions=True)

        # Step 5: Post-Solve Mathematical Reconciliation Audit (Section 6)
        if response.solver_status in ("OPTIMAL", "FEASIBLE"):
            is_valid, audit_failures = cls.reconcile_solution(request, solver, response)
            if not is_valid:
                logger.error(f"Post-solve reconciliation failed: {audit_failures}")
                response.solver_status = "POST_SOLVE_RECONCILIATION_FAILED"
                response.is_optimal = False
                response.infeasibility_diagnostics = InfeasibilityDiagnosticReport(
                    has_proven_infeasibility=True,
                    proven_causes=[
                        InfeasibilityFinding(
                            category="POST_SOLVE_RECONCILIATION_FAILED",
                            classification="PROVEN_INFEASIBILITY",
                            message=failure,
                            mathematical_condition="Post-solve invariant reconciliation check failed",
                            affected_projects=[],
                        )
                        for failure in audit_failures
                    ],
                    necessary_condition_violations=[],
                    solver_hypotheses=[],
                    warnings=[],
                )

        return response

    @classmethod
    def reconcile_solution(
        cls,
        request: RecoveryOptimizationRequest,
        solver: RecoveryCPSATSolver,
        response: RecoveryOptimizationResponse,
    ) -> Tuple[bool, List[str]]:
        """
        Independent post-solve mathematical reconciliation of 10 invariant checks (Section 6).
        Returns (is_valid, audit_failures).
        """
        failures: List[str] = []
        h = request.planning_horizon_periods
        selected_projects = [p for p in response.scheduled_projects if p.is_selected]
        selected_by_id = {p.project_id: p for p in selected_projects}
        candidate_by_id = {c.project_id: c for c in request.candidates}

        # Check 1: Total Cost Conservation
        sum_selected_cost = sum(p.cost_ccu for p in selected_projects)
        if response.total_cost_ccu != sum_selected_cost:
            failures.append(
                f"Total cost mismatch: response total {response.total_cost_ccu} != sum of selected {sum_selected_cost}"
            )

        # Check 2: Project Expenditure Conservation
        for p in selected_projects:
            sum_periodic = sum(p.periodic_expenditures_ccu.values())
            if sum_periodic != p.cost_ccu:
                failures.append(
                    f"Project {p.project_id} expenditure conservation failed: sum {sum_periodic} != cost {p.cost_ccu}"
                )

        # Check 3: Period Aggregate Spend Consistency
        for t in range(1, h + 1):
            expected_spend_t = sum(p.periodic_expenditures_ccu.get(t, 0) for p in selected_projects)
            solvency_record = next((s for s in response.periodic_solvency if s.period == t), None)
            if solvency_record is None:
                failures.append(f"Missing solvency record for period {t}")
            elif solvency_record.expenditure_ccu != expected_spend_t:
                failures.append(
                    f"Period {t} aggregate spend mismatch: record {solvency_record.expenditure_ccu} != calculated {expected_spend_t}"
                )

        # Check 4: Periodic Solvency Recurrence (Phi_t = Phi_{t-1} + B_t - E_t >= 0)
        running_cash = solver.initial_cash_ccu
        for t in range(1, h + 1):
            t_rev = solver.periodic_budgets_ccu.get(t, 0)
            t_spend = sum(p.periodic_expenditures_ccu.get(t, 0) for p in selected_projects)
            running_cash = running_cash + t_rev - t_spend
            solvency_record = next((s for s in response.periodic_solvency if s.period == t), None)
            if solvency_record:
                if solvency_record.cash_balance_ccu != running_cash:
                    failures.append(
                        f"Period {t} cash balance recurrence failed: record {solvency_record.cash_balance_ccu} != expected {running_cash}"
                    )
                if running_cash < 0:
                    failures.append(f"Solvency violation: period {t} cash balance {running_cash} < 0")

        # Check 5: District Equity Floors
        for d_id, theta in request.district_equity_targets.items():
            district_cands = [c for c in request.candidates if c.district_id == d_id]
            if district_cands:
                district_demand = sum(
                    normalize_to_ccu(c.estimated_cost, c.cost_currency, rounding_mode="ceiling")
                    for c in district_cands
                )
                target = int(math.ceil(Decimal(str(theta)) * Decimal(str(solver.total_budget_ccu))))
                clamped_floor = min(target, district_demand)
                actual_district_spend = sum(p.cost_ccu for p in selected_projects if p.district_id == d_id)
                if actual_district_spend < clamped_floor:
                    failures.append(
                        f"District {d_id} equity floor violated: actual {actual_district_spend} < clamped floor {clamped_floor}"
                    )

        # Check 6: Blackout Reserve Ring-Fencing
        if request.blackout_districts:
            blackout_reserve = 0
            for d_id in request.blackout_districts:
                theta = request.district_equity_targets.get(d_id, 0.0)
                if theta > 0:
                    r_d = int(math.ceil(Decimal(str(theta)) * Decimal(str(solver.total_budget_ccu))))
                    blackout_reserve += r_d
            if blackout_reserve > 0:
                allocable_cap = solver.total_budget_ccu - blackout_reserve
                if response.total_cost_ccu > allocable_cap:
                    failures.append(
                        f"Blackout ring-fence violated: total spend {response.total_cost_ccu} > cap {allocable_cap}"
                    )

        # Check 7: Planning Horizon Containment
        for p in selected_projects:
            s = p.scheduled_start_period
            c = p.scheduled_completion_period
            if s is None or c is None:
                failures.append(f"Selected project {p.project_id} has null start or completion period")
            else:
                if s < 1 or c > h:
                    failures.append(
                        f"Project {p.project_id} execution [{s}, {c}] extends outside horizon [1, {h}]"
                    )

        # Check 8: Project Deadlines
        for p in selected_projects:
            cand = candidate_by_id[p.project_id]
            if cand.deadline_period is not None:
                if p.scheduled_completion_period > cand.deadline_period:
                    failures.append(
                        f"Project {p.project_id} completion {p.scheduled_completion_period} > deadline {cand.deadline_period}"
                    )

        # Check 9: Mandatory Life-Safety Hard Start Deadline (T_safety_max)
        if request.max_safety_start_period is not None:
            t_safety = request.max_safety_start_period
            for p in selected_projects:
                cand = candidate_by_id[p.project_id]
                if cand.is_tier1_mandatory:
                    if p.scheduled_start_period > t_safety:
                        failures.append(
                            f"Mandatory project {p.project_id} start {p.scheduled_start_period} > safety deadline {t_safety}"
                        )

        # Check 10: Precedence and Lag Enforcement
        for dep in request.dependencies:
            pred_id = dep.predecessor_id
            succ_id = dep.successor_id
            lag = dep.lag_periods
            if succ_id in selected_by_id:
                if pred_id not in selected_by_id:
                    failures.append(
                        f"Precedence violation: successor {succ_id} selected but predecessor {pred_id} not selected"
                    )
                else:
                    succ_p = selected_by_id[succ_id]
                    pred_p = selected_by_id[pred_id]
                    pred_dur = candidate_by_id[pred_id].duration_periods
                    min_succ_start = pred_p.scheduled_start_period + pred_dur + lag
                    if succ_p.scheduled_start_period < min_succ_start:
                        failures.append(
                            f"Timing precedence violation: {succ_id} start {succ_p.scheduled_start_period} "
                            f"< required {min_succ_start} ({pred_id} start {pred_p.scheduled_start_period} + dur {pred_dur} + lag {lag})"
                        )

        # Check 11: Indivisible Funding Assignment (Model B)
        if request.funding_sources:
            fund_assigned_spend: Dict[str, int] = defaultdict(int)
            for p in selected_projects:
                cand = candidate_by_id[p.project_id]
                if not p.assigned_funding_source:
                    failures.append(f"Project {p.project_id} selected without assigned funding source")
                elif p.assigned_funding_source not in cand.eligible_funds:
                    failures.append(
                        f"Project {p.project_id} assigned to ineligible fund {p.assigned_funding_source}"
                    )
                else:
                    fund_assigned_spend[p.assigned_funding_source] += p.cost_ccu

            for f in request.funding_sources:
                f_cap = solver.funding_capacities_ccu.get(f.fund_id, 0)
                assigned = fund_assigned_spend[f.fund_id]
                if assigned > f_cap:
                    failures.append(
                        f"Fund {f.fund_id} capacity exceeded: assigned {assigned} > capacity {f_cap}"
                    )

        # Check 12: Renewable Resource Capacities
        for r_id, caps_by_t in request.resource_capacities.items():
            for t in range(1, h + 1):
                r_cap = caps_by_t.get(t, 0)
                active_demand = 0
                for p in selected_projects:
                    cand = candidate_by_id[p.project_id]
                    u = cand.resource_demands.get(r_id, 0)
                    if u > 0:
                        s = p.scheduled_start_period
                        c = p.scheduled_completion_period
                        if s <= t <= c:
                            active_demand += u
                if active_demand > r_cap:
                    failures.append(
                        f"Resource {r_id} capacity exceeded at period {t}: active demand {active_demand} > capacity {r_cap}"
                    )

        return (len(failures) == 0, failures)

    @classmethod
    def _build_invalid_response(
        cls,
        request: RecoveryOptimizationRequest,
        error_msg: str,
    ) -> RecoveryOptimizationResponse:
        """Constructs structured MODEL_INVALID response for validation rejections."""
        ortools_ver = getattr(RecoveryCPSATSolver, "ortools_version", "9.15.6755")
        return RecoveryOptimizationResponse(
            scenario_name=request.scenario_name,
            solver_status="MODEL_INVALID",
            is_optimal=False,
            objective_value=None,
            best_bound=None,
            optimality_gap=None,
            solve_time_seconds=0.001,
            selected_project_count=0,
            total_cost_ccu=0,
            total_cost_inr=Decimal("0"),
            scheduled_projects=[],
            periodic_solvency=[],
            district_equity_allocation_ccu={},
            district_equity_allocation_inr={},
            input_fingerprint_sha256=compute_canonical_input_fingerprint(request),
            ortools_version="9.15.6755",
            solver_parameters={},
            infeasibility_diagnostics=InfeasibilityDiagnosticReport(
                has_proven_infeasibility=True,
                proven_causes=[
                    InfeasibilityFinding(
                        category="MODEL_INVALID",
                        classification="PROVEN_INFEASIBILITY",
                        message=error_msg,
                        mathematical_condition="Input contract validation failed",
                        affected_projects=[],
                    )
                ],
                necessary_condition_violations=[],
                solver_hypotheses=[],
                warnings=[],
            ),
        )

