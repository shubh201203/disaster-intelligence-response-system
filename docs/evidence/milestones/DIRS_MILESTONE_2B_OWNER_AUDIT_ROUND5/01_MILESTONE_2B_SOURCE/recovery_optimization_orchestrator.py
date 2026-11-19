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
from fractions import Fraction
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
    deterministic_capped_apportionment,
    normalize_to_ccu,
    quantize_mcpi_score,
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

        # Mandatory Life-Safety Deadline Authorization Check (RSK-M2-01, RSK-M2-07)
        has_mandatory = any(c.is_tier1_mandatory for c in request.candidates)
        if has_mandatory:
            if request.max_safety_start_period is None:
                errors.append(
                    "Request contains mandatory life-safety projects but max_safety_start_period (T_safety_max) is None. An explicit authorized safety deadline is required."
                )
            elif request.max_safety_start_period < 1 or request.max_safety_start_period > request.planning_horizon_periods:
                errors.append(
                    f"max_safety_start_period ({request.max_safety_start_period}) must be between 1 and planning_horizon_periods ({request.planning_horizon_periods})."
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
                exact_objective_value=0,
                exact_best_bound=0,
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
        Independent post-solve mathematical reconciliation of solution invariants.
        All checks recompute quantities from raw request inputs independently.
        Returns (is_valid, audit_failures).
        """
        failures: List[str] = []
        h = request.planning_horizon_periods
        candidate_by_id = {c.project_id: c for c in request.candidates}

        # =====================================================================
        # Stage 0: Solver Status & Metadata Consistency Audit
        # =====================================================================
        # 1. Non-solution statuses must not be treated as valid scheduled solutions
        if response.solver_status not in ("OPTIMAL", "FEASIBLE"):
            if any(p.is_selected for p in response.scheduled_projects) or response.selected_project_count > 0:
                failures.append(
                    f"Non-solution status '{response.solver_status}' cannot contain selected projects (found {response.selected_project_count} selected)"
                )
            if response.is_optimal:
                failures.append(
                    f"Non-solution status '{response.solver_status}' must have is_optimal=False"
                )
            if response.objective_value is not None:
                failures.append(
                    f"Non-solution status '{response.solver_status}' must have null objective_value"
                )
            if response.best_bound is not None:
                failures.append(
                    f"Non-solution status '{response.solver_status}' must have null best_bound"
                )
            if response.optimality_gap is not None:
                failures.append(
                    f"Non-solution status '{response.solver_status}' must have null optimality_gap"
                )
            if response.exact_objective_value is not None:
                failures.append(
                    f"Non-solution status '{response.solver_status}' must have null exact_objective_value"
                )
            if response.exact_best_bound is not None:
                failures.append(
                    f"Non-solution status '{response.solver_status}' must have null exact_best_bound"
                )

        # 2. Status-specific flag and presence consistency
        if response.solver_status == "OPTIMAL":
            if not response.is_optimal:
                failures.append("Solver status OPTIMAL must have is_optimal=True, got False")
            if response.objective_value is None:
                failures.append("Solver status OPTIMAL must have non-null objective_value")
            if response.best_bound is None:
                failures.append("Solver status OPTIMAL must have non-null best_bound")
            if response.optimality_gap is None:
                failures.append("Solver status OPTIMAL must have non-null optimality_gap")
            elif response.optimality_gap != 0.0:
                failures.append(f"Solver status OPTIMAL must have optimality_gap=0.0, got {response.optimality_gap}")

        elif response.solver_status == "FEASIBLE":
            if response.is_optimal:
                failures.append("Solver status FEASIBLE must have is_optimal=False, got True")
            if response.objective_value is None:
                failures.append("Solver status FEASIBLE must have non-null objective_value")
            if response.best_bound is None:
                failures.append("Solver status FEASIBLE must have non-null best_bound")
            if response.optimality_gap is None:
                failures.append("Solver status FEASIBLE must have non-null optimality_gap")

        # 3. Reject NaN, infinity on metadata fields
        for val, name in [
            (response.objective_value, "objective_value"),
            (response.best_bound, "best_bound"),
            (response.optimality_gap, "optimality_gap"),
        ]:
            if val is not None:
                if not isinstance(val, (int, float)):
                    failures.append(f"Metadata '{name}' must be numeric, got {type(val)}")
                elif math.isnan(val) or math.isinf(val):
                    failures.append(f"Metadata '{name}' cannot be NaN or infinite, got {val}")

        # 4. Bound relationship & gap consistency for solution statuses
        if response.solver_status in ("OPTIMAL", "FEASIBLE"):
            obj_f = response.objective_value
            bnd_f = response.best_bound
            gap_f = response.optimality_gap

            if obj_f is not None and bnd_f is not None and not (math.isnan(obj_f) or math.isinf(obj_f) or math.isnan(bnd_f) or math.isinf(bnd_f)):
                if response.solver_status == "OPTIMAL":
                    # Exact representation check: objective and best bound must agree
                    if obj_f != bnd_f:
                        failures.append(f"OPTIMAL objective_value {obj_f} != best_bound {bnd_f}")
                    if response.exact_objective_value is not None and response.exact_best_bound is not None:
                        if response.exact_objective_value != response.exact_best_bound:
                            failures.append(
                                f"OPTIMAL exact_objective_value ({response.exact_objective_value}) != exact_best_bound ({response.exact_best_bound})"
                            )
                elif response.solver_status == "FEASIBLE":
                    # For maximization: upper bound must be >= objective
                    if bnd_f < obj_f - 1e-6:
                        failures.append(f"FEASIBLE best_bound ({bnd_f}) < objective_value ({obj_f}) for maximization")
                    if gap_f is not None and not (math.isnan(gap_f) or math.isinf(gap_f)):
                        expected_gap = abs(bnd_f - obj_f) / bnd_f if bnd_f > 0 else 0.0
                        if abs(gap_f - expected_gap) > 1e-4:
                            failures.append(
                                f"FEASIBLE optimality_gap calculation mismatch: record {gap_f} != expected {expected_gap}"
                            )

        # =====================================================================
        # Stage 1: Returned Schedule Integrity
        # =====================================================================
        # 1. Reject duplicate project IDs in returned scheduled projects
        seen_pids = set()
        dup_pids = set()
        for p in response.scheduled_projects:
            if p.project_id in seen_pids:
                dup_pids.add(p.project_id)
            seen_pids.add(p.project_id)
        if dup_pids:
            failures.append(
                f"Duplicate project IDs in scheduled_projects: {sorted(list(dup_pids))}"
            )

        # 2. Reject unknown project IDs
        for p in response.scheduled_projects:
            if p.project_id not in candidate_by_id:
                failures.append(
                    f"Unknown project ID '{p.project_id}' in scheduled_projects: not present in candidate request"
                )

        # 3. Verify every selected project corresponds to exactly one candidate
        selected_projects = [p for p in response.scheduled_projects if p.is_selected]
        for p in selected_projects:
            if p.project_id not in candidate_by_id:
                failures.append(
                    f"Selected project '{p.project_id}' does not correspond to any request candidate"
                )

        # 4. Verify all selected projects have complete schedule records
        for p in selected_projects:
            if p.scheduled_start_period is None:
                failures.append(f"Selected project '{p.project_id}' has missing scheduled_start_period")
            if p.scheduled_completion_period is None:
                failures.append(f"Selected project '{p.project_id}' has missing scheduled_completion_period")
            if not p.periodic_expenditures_ccu:
                failures.append(f"Selected project '{p.project_id}' has empty periodic_expenditures_ccu")
            if request.funding_sources and not p.assigned_funding_source:
                failures.append(f"Selected project '{p.project_id}' has missing assigned_funding_source")

        # 5. Ensure unselected candidates are not incorrectly represented as selected
        for p in response.scheduled_projects:
            if not p.is_selected:
                if p.scheduled_start_period is not None or p.scheduled_completion_period is not None:
                    failures.append(
                        f"Unselected project '{p.project_id}' has active schedule start ({p.scheduled_start_period}) or completion ({p.scheduled_completion_period})"
                    )
                if any(exp != 0 for exp in p.periodic_expenditures_ccu.values()):
                    failures.append(
                        f"Unselected project '{p.project_id}' has non-zero periodic expenditures"
                    )

        # Selected project count consistency
        if response.selected_project_count != len(selected_projects):
            failures.append(
                f"Selected project count mismatch: response {response.selected_project_count} != actual {len(selected_projects)}"
            )

        selected_by_id = {p.project_id: p for p in selected_projects}

        # =====================================================================
        # Stage 2: Independent Cost Reconstruction
        # =====================================================================
        # For every selected project:
        # - Independently convert original candidate estimated_cost using original cost_currency
        # - Apply approved CCU conversion and ceiling rounding
        # - Compare with returned ScheduledProjectResult.cost_ccu
        # - Compare returned project INR cost with independently reconstructed CCU amount
        reconstructed_project_costs_ccu: Dict[str, int] = {}
        for p in selected_projects:
            cand = candidate_by_id.get(p.project_id)
            if cand is not None:
                recon_ccu = normalize_to_ccu(cand.estimated_cost, cand.cost_currency, rounding_mode="ceiling")
                reconstructed_project_costs_ccu[p.project_id] = recon_ccu
                if p.cost_ccu != recon_ccu:
                    failures.append(
                        f"Project '{p.project_id}' cost CCU mismatch: returned {p.cost_ccu} != independently reconstructed {recon_ccu}"
                    )
                expected_p_inr = unscale_ccu(recon_ccu, CurrencyUnit.INR)
                if p.cost_inr != expected_p_inr:
                    failures.append(
                        f"Project '{p.project_id}' cost INR mismatch: returned {p.cost_inr} != independently reconstructed {expected_p_inr}"
                    )
            else:
                reconstructed_project_costs_ccu[p.project_id] = p.cost_ccu

        # Total portfolio cost from independently reconstructed costs
        reconstructed_total_cost_ccu = sum(reconstructed_project_costs_ccu.values())
        if response.total_cost_ccu != reconstructed_total_cost_ccu:
            failures.append(
                f"Total cost mismatch: response total {response.total_cost_ccu} != sum of reconstructed {reconstructed_total_cost_ccu}"
            )
        expected_total_inr = unscale_ccu(reconstructed_total_cost_ccu, CurrencyUnit.INR)
        if response.total_cost_inr != expected_total_inr:
            failures.append(
                f"Total cost INR mismatch: response {response.total_cost_inr} != unscaled {expected_total_inr}"
            )

        # =====================================================================
        # Stage 3: Solvency Record Completeness & Recurrence
        # =====================================================================
        # Require exactly one PeriodicSolvencyRecord for every period from 1 through h
        solvency_periods = [s.period for s in response.periodic_solvency]
        seen_s_periods = set()
        dup_s_periods = set()
        for t in solvency_periods:
            if t in seen_s_periods:
                dup_s_periods.add(t)
            seen_s_periods.add(t)
        if dup_s_periods:
            failures.append(
                f"Duplicate solvency records for periods: {sorted(list(dup_s_periods))}"
            )

        # Out-of-horizon period records
        for t in solvency_periods:
            if t < 1 or t > h:
                failures.append(
                    f"Out-of-horizon solvency record: period {t} outside planning horizon [1, {h}]"
                )

        # Missing period records
        for t in range(1, h + 1):
            if t not in seen_s_periods:
                failures.append(f"Missing solvency record for period {t}")

        # Check total record count
        if len(response.periodic_solvency) != h:
            failures.append(
                f"Solvency record count mismatch: expected {h} records, got {len(response.periodic_solvency)}"
            )

        # Recompute recurrence from independently normalized initial cash, periodic budgets, and reconstructed expenditures
        recon_init_cash_ccu = normalize_to_ccu(request.initial_cash, request.cash_currency, rounding_mode="floor")
        recon_periodic_budgets_ccu = {
            t: normalize_to_ccu(request.periodic_budgets.get(t, 0), request.budget_currency, rounding_mode="floor")
            for t in range(1, h + 1)
        }

        solvency_by_period = {s.period: s for s in response.periodic_solvency}
        running_cash = recon_init_cash_ccu
        for t in range(1, h + 1):
            t_rev = recon_periodic_budgets_ccu.get(t, 0)
            t_spend = sum(p.periodic_expenditures_ccu.get(t, 0) for p in selected_projects)
            running_cash = running_cash + t_rev - t_spend

            s_rec = solvency_by_period.get(t)
            if s_rec is not None:
                if s_rec.revenue_receipt_ccu != t_rev:
                    failures.append(
                        f"Period {t} revenue mismatch: record {s_rec.revenue_receipt_ccu} != expected {t_rev}"
                    )
                if s_rec.expenditure_ccu != t_spend:
                    failures.append(
                        f"Period {t} aggregate expenditure mismatch: record {s_rec.expenditure_ccu} != expected {t_spend}"
                    )
                if s_rec.cash_balance_ccu != running_cash:
                    failures.append(
                        f"Period {t} cash balance recurrence failed: record {s_rec.cash_balance_ccu} != expected {running_cash}"
                    )
                exp_s_inr = unscale_ccu(running_cash, CurrencyUnit.INR)
                if s_rec.cash_balance_inr != exp_s_inr:
                    failures.append(
                        f"Period {t} cash balance INR mismatch: record {s_rec.cash_balance_inr} != expected {exp_s_inr}"
                    )
                if s_rec.is_solvent != (running_cash >= 0):
                    failures.append(
                        f"Period {t} solvency flag mismatch: record {s_rec.is_solvent} != expected {running_cash >= 0}"
                    )

            if running_cash < 0:
                failures.append(f"Negative reconstructed cash balance at period {t}: balance {running_cash} < 0")

        # =====================================================================
        # Stage 4: Schedule Validity & Timing Constraints
        # =====================================================================
        for p in selected_projects:
            cand = candidate_by_id.get(p.project_id)
            if cand is None:
                continue

            s = p.scheduled_start_period
            c = p.scheduled_completion_period

            if s is not None and s < cand.release_period:
                failures.append(
                    f"Release period violation: project {p.project_id} start {s} < release {cand.release_period}"
                )

            if s is not None and c is not None:
                expected_completion = s + cand.duration_periods - 1
                if c != expected_completion:
                    failures.append(
                        f"Completion period mismatch: project {p.project_id} completion {c} != expected {expected_completion} (start {s} + duration {cand.duration_periods} - 1)"
                    )
                if s < 1 or c > h or s > c:
                    failures.append(
                        f"Project {p.project_id} execution [{s}, {c}] extends outside horizon [1, {h}]"
                    )
                if cand.deadline_period is not None and c > cand.deadline_period:
                    failures.append(
                        f"Project {p.project_id} completion {c} > deadline {cand.deadline_period}"
                    )

        # =====================================================================
        # Stage 5: Expenditure Profile & Conservation using Reconstructed Cost
        # =====================================================================
        for p in selected_projects:
            cand = candidate_by_id.get(p.project_id)
            if cand is None:
                continue

            recon_cost = reconstructed_project_costs_ccu[p.project_id]
            dur = cand.duration_periods
            s = p.scheduled_start_period
            c = p.scheduled_completion_period

            # Outside [s, c], expenditures must be 0
            for t, exp in p.periodic_expenditures_ccu.items():
                if s is not None and c is not None:
                    if (t < s or t > c) and exp != 0:
                        failures.append(
                            f"Expenditure profile violation: project {p.project_id} has non-zero spend {exp} at period {t} outside execution [{s}, {c}]"
                        )

            # Reconstruct expected profile using deterministic_capped_apportionment with reconstructed cost
            if cand.expenditure_weights is not None:
                weights = [Fraction(Decimal(str(w))) for w in cand.expenditure_weights]
            elif request.allow_uniform_weight_fallback:
                weights = [Fraction(1, dur)] * dur
            else:
                weights = None

            if weights is not None and s is not None:
                expected_profile = deterministic_capped_apportionment(
                    cost_c=recon_cost,
                    weights_w=weights,
                    caps_e_bar=[recon_cost] * dur,
                    eligible_periods=set(range(1, dur + 1)),
                    allow_uniform_fallback=request.allow_uniform_weight_fallback,
                )
                for k in range(dur):
                    period_t = s + k
                    actual_exp = p.periodic_expenditures_ccu.get(period_t, 0)
                    expected_exp = expected_profile[k]
                    if actual_exp != expected_exp:
                        failures.append(
                            f"Expenditure profile mismatch for project {p.project_id} at period {period_t}: actual {actual_exp} != expected {expected_exp}"
                        )

            # Conservation of project cost against independently reconstructed cost
            sum_periodic_exp = sum(p.periodic_expenditures_ccu.values())
            if sum_periodic_exp != recon_cost:
                failures.append(
                    f"Project {p.project_id} expenditure conservation failed: sum {sum_periodic_exp} != cost {recon_cost}"
                )

        # =====================================================================
        # Stage 6: Mandatory Safety Deadline
        # =====================================================================
        for cand in request.candidates:
            if cand.is_tier1_mandatory:
                if cand.project_id not in selected_by_id:
                    failures.append(f"Mandatory life-safety project {cand.project_id} was not selected")
                else:
                    p = selected_by_id[cand.project_id]
                    if request.max_safety_start_period is not None:
                        t_safety = request.max_safety_start_period
                        if p.scheduled_start_period is not None and p.scheduled_start_period > t_safety:
                            failures.append(
                                f"Mandatory project {cand.project_id} start {p.scheduled_start_period} > safety deadline {t_safety}"
                            )

        # =====================================================================
        # Stage 7: Dependencies & Precedence Lags
        # =====================================================================
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
                    if pred_p.scheduled_start_period is not None and succ_p.scheduled_start_period is not None:
                        min_succ_start = pred_p.scheduled_start_period + pred_dur + lag
                        if succ_p.scheduled_start_period < min_succ_start:
                            failures.append(
                                f"Timing precedence violation: {succ_id} start {succ_p.scheduled_start_period} < required {min_succ_start} ({pred_id} start {pred_p.scheduled_start_period} + dur {pred_dur} + lag {lag})"
                            )

        # =====================================================================
        # Stage 8: Indivisible Funding Assignment (Model B) with Reconstructed Costs
        # =====================================================================
        if request.funding_sources:
            fund_caps_ccu = {
                f.fund_id: normalize_to_ccu(f.capacity, f.currency, rounding_mode="floor")
                for f in request.funding_sources
            }
            fund_assigned_spend: Dict[str, int] = defaultdict(int)
            for p in selected_projects:
                cand = candidate_by_id.get(p.project_id)
                if cand is None:
                    continue
                if not p.assigned_funding_source:
                    failures.append(f"Project {p.project_id} selected without assigned funding source")
                elif p.assigned_funding_source not in cand.eligible_funds:
                    failures.append(
                        f"Project {p.project_id} assigned to ineligible fund {p.assigned_funding_source}"
                    )
                else:
                    recon_c = reconstructed_project_costs_ccu[p.project_id]
                    fund_assigned_spend[p.assigned_funding_source] += recon_c

            for f in request.funding_sources:
                f_cap = fund_caps_ccu.get(f.fund_id, 0)
                assigned = fund_assigned_spend[f.fund_id]
                if assigned > f_cap:
                    failures.append(
                        f"Fund {f.fund_id} capacity exceeded: assigned {assigned} > capacity {f_cap}"
                    )

        # =====================================================================
        # Stage 9: Resource Capacities
        # =====================================================================
        for r_id, caps_by_t in request.resource_capacities.items():
            for t in range(1, h + 1):
                r_cap = caps_by_t.get(t, 0)
                active_demand = 0
                for p in selected_projects:
                    cand = candidate_by_id.get(p.project_id)
                    if cand is None:
                        continue
                    u = cand.resource_demands.get(r_id, 0)
                    if u > 0:
                        s = p.scheduled_start_period
                        c = p.scheduled_completion_period
                        if s is not None and c is not None and s <= t <= c:
                            active_demand += u
                if active_demand > r_cap:
                    failures.append(
                        f"Resource {r_id} capacity exceeded at period {t}: active demand {active_demand} > capacity {r_cap}"
                    )

        # =====================================================================
        # Stage 10: District Equity Floors & Blackout Reserves with Reconstructed Costs
        # =====================================================================
        recon_total_budget_ccu = recon_init_cash_ccu + sum(recon_periodic_budgets_ccu.values())
        for d_id, theta in request.district_equity_targets.items():
            district_cands = [c for c in request.candidates if c.district_id == d_id]
            if district_cands:
                district_demand = sum(
                    normalize_to_ccu(c.estimated_cost, c.cost_currency, rounding_mode="ceiling")
                    for c in district_cands
                )
                target = int(math.ceil(Decimal(str(theta)) * Decimal(str(recon_total_budget_ccu))))
                clamped_floor = min(target, district_demand)
                actual_district_spend = sum(
                    reconstructed_project_costs_ccu[p.project_id]
                    for p in selected_projects
                    if p.district_id == d_id
                )
                if actual_district_spend < clamped_floor:
                    failures.append(
                        f"District {d_id} equity floor violated: actual {actual_district_spend} < clamped floor {clamped_floor}"
                    )

        if request.blackout_districts:
            blackout_reserve = 0
            for d_id in request.blackout_districts:
                theta = request.district_equity_targets.get(d_id, 0.0)
                if theta > 0:
                    r_d = int(math.ceil(Decimal(str(theta)) * Decimal(str(recon_total_budget_ccu))))
                    blackout_reserve += r_d
            if blackout_reserve > 0:
                allocable_cap = recon_total_budget_ccu - blackout_reserve
                if reconstructed_total_cost_ccu > allocable_cap:
                    failures.append(
                        f"Blackout ring-fence violated: total spend {reconstructed_total_cost_ccu} > cap {allocable_cap}"
                    )

        # =====================================================================
        # Stage 11: Reproducibility & Metadata Integrity
        # =====================================================================
        expected_fingerprint = compute_canonical_input_fingerprint(request)
        if response.input_fingerprint_sha256 != expected_fingerprint:
            failures.append(
                f"Fingerprint mismatch: response {response.input_fingerprint_sha256} != recomputed {expected_fingerprint}"
            )

        # =====================================================================
        # Stage 12: Independent Exact Integer Objective Recomputation
        # =====================================================================
        if response.solver_status in ("OPTIMAL", "FEASIBLE"):
            n_candidates = len(request.candidates)
            if request.enable_early_start_bonus and h > 1 and n_candidates > 0:
                m_accel = n_candidates * (h - 1) + 1
            else:
                m_accel = 1

            recomputed_exact_objective = 0
            for p in selected_projects:
                cand = candidate_by_id.get(p.project_id)
                if cand is not None:
                    pi_bar = quantize_mcpi_score(cand.raw_mcpi_score)
                    recomputed_exact_objective += m_accel * pi_bar
                    if request.enable_early_start_bonus and h > 1:
                        s = p.scheduled_start_period
                        if s is not None:
                            recomputed_exact_objective += (h - s)

            # Exact integer objective equality check
            if response.exact_objective_value is not None:
                if response.exact_objective_value != recomputed_exact_objective:
                    failures.append(
                        f"Exact integer objective mismatch: response {response.exact_objective_value} != independently recomputed {recomputed_exact_objective}"
                    )

            # Floating-point representation check
            if response.objective_value is not None and not (math.isnan(response.objective_value) or math.isinf(response.objective_value)):
                expected_float_obj = float(recomputed_exact_objective)
                if response.objective_value != expected_float_obj:
                    failures.append(
                        f"Objective value mismatch: response objective {response.objective_value} != recomputed {expected_float_obj}"
                    )

            # For OPTIMAL, exact_best_bound must also match recomputed exact objective
            if response.solver_status == "OPTIMAL":
                if response.exact_best_bound is not None:
                    if response.exact_best_bound != recomputed_exact_objective:
                        failures.append(
                            f"Exact best bound mismatch for OPTIMAL: response {response.exact_best_bound} != independently recomputed {recomputed_exact_objective}"
                        )
                if response.best_bound is not None and not (math.isnan(response.best_bound) or math.isinf(response.best_bound)):
                    expected_float_bnd = float(recomputed_exact_objective)
                    if response.best_bound != expected_float_bnd:
                        failures.append(
                            f"Best bound mismatch for OPTIMAL: response best_bound {response.best_bound} != recomputed {expected_float_bnd}"
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
            exact_objective_value=None,
            exact_best_bound=None,
        )

