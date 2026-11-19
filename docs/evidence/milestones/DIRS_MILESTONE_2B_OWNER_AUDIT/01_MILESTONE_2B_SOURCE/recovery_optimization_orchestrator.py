"""
Recovery Optimization Orchestrator Service.

Phase 6D-B Milestone 2B Implementation.
Coordinates the end-to-end recovery optimization pipeline:
1. Input validation & pre-solve graph cycle detection.
2. Forensic infeasibility pre-screening.
3. Google OR-Tools CP-SAT solver invocation.
4. Post-solve mathematical solvency and district equity audits.
5. Structured reporting and deterministic reproducibility metadata.
"""

from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional

from app.recovery.optimization.schemas import (
    CurrencyUnit,
    InfeasibilityDiagnosticReport,
    InfeasibilityFinding,
    PeriodSolvencyResult,
    RecoveryOptimizationRequest,
    RecoveryOptimizationResponse,
    ScheduledProjectResult,
    normalize_to_ccu,
    unscale_ccu,
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
    diagnostic screening, and post-solve audits.
    """

    @classmethod
    def optimize_recovery_portfolio(
        cls,
        request: RecoveryOptimizationRequest,
    ) -> RecoveryOptimizationResponse:
        """
        Executes complete recovery optimization pipeline for a portfolio scenario.
        """
        # Step 1: Handle Empty Portfolio Case
        if not request.candidates:
            solver = RecoveryCPSATSolver(request)
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
                periodic_solvency=[
                    PeriodSolvencyResult(
                        period=t,
                        revenue_receipt_ccu=normalize_to_ccu(
                            request.periodic_budgets.get(t, 0),
                            request.budget_currency,
                            rounding_mode="floor",
                        ),
                        expenditure_ccu=0,
                        cash_balance_ccu=normalize_to_ccu(
                            request.initial_cash,
                            request.cash_currency,
                            rounding_mode="floor",
                        ) + sum(
                            normalize_to_ccu(
                                request.periodic_budgets.get(s, 0),
                                request.budget_currency,
                                rounding_mode="floor",
                            )
                            for s in range(1, t + 1)
                        ),
                        cash_balance_inr=unscale_ccu(
                            normalize_to_ccu(
                                request.initial_cash,
                                request.cash_currency,
                                rounding_mode="floor",
                            ) + sum(
                                normalize_to_ccu(
                                    request.periodic_budgets.get(s, 0),
                                    request.budget_currency,
                                    rounding_mode="floor",
                                )
                                for s in range(1, t + 1)
                            ),
                            CurrencyUnit.INR,
                        ),
                        is_solvent=True,
                    )
                    for t in range(1, request.planning_horizon_periods + 1)
                ],
                district_equity_allocation_ccu={},
                district_equity_allocation_inr={},
                input_fingerprint_sha256=solver._compute_input_fingerprint(),
                ortools_version=solver.ortools_version,
                solver_parameters={
                    "num_search_workers": request.num_workers,
                    "random_seed": request.deterministic_seed,
                    "max_time_in_seconds": request.max_solve_time_seconds,
                },
                infeasibility_diagnostics=None,
            )

        # Step 2: Validate Graph Acyclicity via Milestone 1 Kahn Toposort
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
            # Raise or report MODEL_INVALID immediately
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
                input_fingerprint_sha256=solver._compute_input_fingerprint(),
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

        # Step 3: Instantiate Solver & Execute Search
        solver = RecoveryCPSATSolver(request)
        response = solver.solve(enable_assumptions=True)

        return response
