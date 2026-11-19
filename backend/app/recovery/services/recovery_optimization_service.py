"""
DIRS Phase 6D-B Milestone 3 Gate 2: Recovery Portfolio Optimization Service.
Stateless Application Service Layer.

Acts as an adapter between FastAPI API layer and the authoritative Milestone 2B CP-SAT
optimization engine (RecoveryOptimizationOrchestrator).

Stateless Invariants:
1. Pure in-memory execution: zero database session injection, zero DB reads or writes.
2. Candidate count limit enforcement: MAX_SCENARIO_CANDIDATES = 500 (HTTP 422 if exceeded).
3. API execution timeout cap enforcement: DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS (default 120.0s).
4. Full telemetry logging with correlation IDs.
"""

import os
import math
import logging
from typing import Optional

from fastapi import HTTPException, status

from app.schemas.recovery_optimization import (
    RecoveryOptimizationScenarioRequest,
    RecoveryOptimizationScenarioResponse,
)
from app.recovery.optimization.recovery_optimization_orchestrator import (
    RecoveryOptimizationOrchestrator,
)

logger = logging.getLogger(__name__)

# Owner Decision A: Maximum permitted candidate projects per scenario evaluation
MAX_SCENARIO_CANDIDATES: int = 500

# Owner Decision B: Default API solve time cap in seconds
DEFAULT_API_TIMEOUT_CAP_SECONDS: float = 120.0


def get_api_timeout_cap_seconds() -> float:
    """
    Safely reads DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS from environment.
    Defaults to 120.0 if unset or empty.
    Raises ValueError if configured value is non-finite, negative, or non-numeric.
    """
    env_val = os.getenv("DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS")
    if env_val is None or str(env_val).strip() == "":
        return DEFAULT_API_TIMEOUT_CAP_SECONDS

    try:
        val = float(env_val)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid non-numeric DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS: {env_val!r}") from e

    if math.isnan(val) or math.isinf(val) or val <= 0.0:
        raise ValueError(
            f"DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS must be a finite positive number, got {val}"
        )

    return val


class RecoveryOptimizationService:
    """
    Stateless application service executing recovery portfolio scenario evaluation.
    This service is strictly decoupled from the database and database sessions.
    """

    @classmethod
    def evaluate_scenario(
        cls,
        scenario_request: RecoveryOptimizationScenarioRequest,
        correlation_id: str,
        user_id: Optional[str] = None,
    ) -> RecoveryOptimizationScenarioResponse:
        """
        Coordinates stateless scenario evaluation:
        1. Validates API execution timeout cap.
        2. Validates candidate count policy ceiling.
        3. Converts Pydantic DTO to authoritative Milestone 2B request dataclass.
        4. Invokes RecoveryOptimizationOrchestrator.optimize_recovery_portfolio().
        5. Converts engine response to Pydantic DTO and returns.
        """
        # 1. Enforce API execution timeout cap (Owner Decision B)
        try:
            timeout_cap = get_api_timeout_cap_seconds()
        except ValueError as err:
            logger.critical(
                f"Server configuration error: invalid API timeout cap [correlation_id={correlation_id}]: {err}"
            )
            raise RuntimeError(f"Server configuration error: invalid optimization execution timeout cap: {err}") from err

        if scenario_request.max_solve_time_seconds > timeout_cap:
            logger.warning(
                f"Rejected optimization request exceeding API timeout cap [correlation_id={correlation_id}]: "
                f"requested={scenario_request.max_solve_time_seconds}s, cap={timeout_cap}s"
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Requested max_solve_time_seconds ({scenario_request.max_solve_time_seconds}) "
                    f"exceeds server API timeout cap of {timeout_cap} seconds."
                ),
            )

        # 2. Enforce candidate count policy ceiling (Owner Decision A)
        candidate_count = len(scenario_request.candidates)
        if candidate_count > MAX_SCENARIO_CANDIDATES:
            logger.warning(
                f"Rejected optimization request exceeding candidate count limit [correlation_id={correlation_id}]: "
                f"submitted={candidate_count}, maximum={MAX_SCENARIO_CANDIDATES}"
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Candidate count ({candidate_count}) exceeds maximum permitted "
                    f"scenario size of {MAX_SCENARIO_CANDIDATES} projects."
                ),
            )

        # 3. Telemetry log start
        logger.info(
            f"Starting recovery portfolio optimization [correlation_id={correlation_id}, "
            f"user_id={user_id}, scenario='{scenario_request.scenario_name}', "
            f"candidates={candidate_count}, horizon={scenario_request.planning_horizon_periods}, "
            f"max_solve_time={scenario_request.max_solve_time_seconds}s]"
        )

        # 4. Convert DTO to authoritative Milestone 2B dataclass (no clamping or value mutation)
        engine_request = scenario_request.to_engine_request()

        # 5. Invoke authoritative orchestrator
        engine_response = RecoveryOptimizationOrchestrator.optimize_recovery_portfolio(engine_request)

        # 6. Convert engine response dataclass to accepted Gate 1 response DTO
        scenario_response = RecoveryOptimizationScenarioResponse.from_engine_response(engine_response)

        # 7. Telemetry log completion
        logger.info(
            f"Completed recovery portfolio optimization [correlation_id={correlation_id}, "
            f"status={scenario_response.solver_status}, time={scenario_response.solve_time_seconds:.3f}s, "
            f"selected={scenario_response.selected_project_count}]"
        )

        return scenario_response
