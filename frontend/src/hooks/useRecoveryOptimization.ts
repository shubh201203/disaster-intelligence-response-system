/**
 * DIRS Phase 6D-B Milestone 4 Gate 2 Stage 3: Synchronous Solver Evaluation Hook
 *
 * Orchestrates synchronous optimization evaluation requests against the accepted Gate 1 API client.
 * Uses TanStack React Query useMutation to expose typed result, normalized error, and pending state.
 *
 * Constraints:
 * - Transport strictly through evaluateRecoveryOptimizationScenario.
 * - Zero second clients, zero raw axios/fetch calls, zero fabricated responses.
 * - In-flight guard prevents duplicate concurrent executions.
 * - Preserves correlation IDs and RFC 8259 lossless numerical strings.
 */

import { useMutation, UseMutationResult } from '@tanstack/react-query';
import { evaluateRecoveryOptimizationScenario } from '../api/recoveryOptimization';
import {
  RecoveryOptimizationScenarioRequest,
  EvaluatedScenarioResult,
  OptimizationApiError,
} from '../types/recoveryOptimization';

export interface UseRecoveryOptimizationReturn {
  /** Dispatches synchronous evaluation request with concurrency guard */
  evaluateScenario: (request: RecoveryOptimizationScenarioRequest) => Promise<EvaluatedScenarioResult>;
  /** Complete typed response and correlation ID on success */
  result: EvaluatedScenarioResult | null;
  /** Normalized error envelope on failure */
  error: OptimizationApiError | null;
  /** True while the synchronous backend solver execution is in progress */
  isPending: boolean;
  /** True if the last execution completed successfully */
  isSuccess: boolean;
  /** True if the last execution failed */
  isError: boolean;
  /** Resets mutation state to idle */
  reset: () => void;
  /** Direct mutation reference for advanced query inspection */
  mutation: UseMutationResult<EvaluatedScenarioResult, OptimizationApiError, RecoveryOptimizationScenarioRequest>;
}

export function useRecoveryOptimization(): UseRecoveryOptimizationReturn {
  const mutation = useMutation<EvaluatedScenarioResult, OptimizationApiError, RecoveryOptimizationScenarioRequest>({
    mutationFn: async (request: RecoveryOptimizationScenarioRequest): Promise<EvaluatedScenarioResult> => {
      // Sole authorized transport: Gate 1 evaluateRecoveryOptimizationScenario
      return await evaluateRecoveryOptimizationScenario(request);
    },
  });

  const evaluateScenario = async (
    request: RecoveryOptimizationScenarioRequest
  ): Promise<EvaluatedScenarioResult> => {
    // Concurrency guard: reject concurrent execution attempts
    if (mutation.isPending) {
      throw new Error('An optimization evaluation is already in progress.');
    }
    return await mutation.mutateAsync(request);
  };

  return {
    evaluateScenario,
    result: mutation.data ?? null,
    error: (mutation.error as OptimizationApiError) ?? null,
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
    reset: mutation.reset,
    mutation,
  };
}
