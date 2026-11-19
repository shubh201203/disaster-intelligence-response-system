"""
DIRS Phase 6D-B Milestone 3 Gate 2: Recovery Portfolio Optimization Router.
Exposes stateless REST endpoint for portfolio optimization scenario evaluation.

Route: POST /api/v1/recovery/optimization/evaluate
Authorization: Requires GOVT or ADMIN role.
Database Invariant: Route does NOT declare or receive a SQLAlchemy Session.
"""

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse

from app.models.user import User
from app.core.deps import require_any_role
from app.schemas.recovery_optimization import (
    RecoveryOptimizationScenarioRequest,
    RecoveryOptimizationScenarioResponse,
    OptimizationErrorDetailDTO,
    OptimizationErrorType,
)
from app.recovery.services.recovery_optimization_service import RecoveryOptimizationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recovery/optimization", tags=["Post-Disaster Recovery Portfolio Optimization"])


@router.post(
    "/evaluate",
    response_model=RecoveryOptimizationScenarioResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "model": RecoveryOptimizationScenarioResponse,
            "description": (
                "Optimization scenario evaluated successfully across any solver outcome "
                "(OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN, MODEL_INVALID, POST_SOLVE_RECONCILIATION_FAILED)."
            ),
        },
        401: {"description": "Unauthenticated: Missing, invalid, or expired JWT bearer token."},
        403: {"description": "Forbidden: User role is not GOVT or ADMIN."},
        422: {"description": "Unprocessable Entity: Contract validation failure, candidate limit (>500), or solve time exceeding cap."},
        500: {"model": OptimizationErrorDetailDTO, "description": "Unexpected internal execution failure."},
    },
)
def evaluate_recovery_optimization_scenario(
    request: RecoveryOptimizationScenarioRequest,
    response: Response,
    current_user: User = Depends(require_any_role(["GOVT", "ADMIN"])),
):
    """
    Evaluates a stateless post-disaster recovery optimization scenario using Google OR-Tools CP-SAT.

    Guarantees:
    - Pure in-memory computation: zero application database records written or modified.
    - Zero persistence: optimization schedules, trajectories, and solver outputs are not saved to database.
    - Role-based security: strictly restricted to GOVT emergency managers and ADMIN users.
    - Correlation tracking: unique X-Correlation-ID emitted on every request for telemetry traceability.
    """
    correlation_id = str(uuid.uuid4())
    response.headers["X-Correlation-ID"] = correlation_id

    try:
        return RecoveryOptimizationService.evaluate_scenario(
            scenario_request=request,
            correlation_id=correlation_id,
            user_id=getattr(current_user, "id", None),
        )
    except HTTPException:
        # Expected policy/validation HTTP exceptions pass through with original status code
        raise
    except Exception as ex:
        # Unexpected internal error: log complete traceback server-side and return sanitized payload
        logger.exception(
            f"Unexpected internal failure during recovery optimization [correlation_id={correlation_id}]: {ex}"
        )
        is_config_err = "Server configuration error" in str(ex)
        message = (
            "Server configuration error: invalid optimization execution timeout cap."
            if is_config_err
            else "An unexpected internal error occurred during scenario optimization execution."
        )
        error_dto = OptimizationErrorDetailDTO(
            error_type=OptimizationErrorType.INTERNAL_EXECUTION_FAILURE,
            message=message,
            diagnostic_code=correlation_id,
            validation_failures=[],
            input_fingerprint_sha256=None,
            infeasibility_diagnostics=None,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_dto.model_dump(mode="json"),
            headers={"X-Correlation-ID": correlation_id},
        )
