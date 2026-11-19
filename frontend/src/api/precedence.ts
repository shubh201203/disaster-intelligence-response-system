/**
 * DIRS Phase 6E Accelerated Programme: Work Package 1
 * Precedence Graph API Client.
 */

import { apiClient } from './client';
import {
  PrecedenceGraphResponse,
  PrecedenceEdgeValidateRequest,
  PrecedenceEdgeValidateResponse,
} from '../types/precedence';

/**
 * Retrieves the compiled recovery project precedence graph with CPM-PL metrics and critical paths.
 */
export async function getPrecedenceGraph(periodDays: number = 30): Promise<PrecedenceGraphResponse> {
  const response = await apiClient.get<PrecedenceGraphResponse>('/recovery/dependencies/graph', {
    params: { period_days: periodDays },
  });
  return response.data;
}

/**
 * Dry-run validation of a candidate dependency edge to detect cycles and errors without database mutation.
 */
export async function validateDependencyEdge(
  request: PrecedenceEdgeValidateRequest
): Promise<PrecedenceEdgeValidateResponse> {
  const response = await apiClient.post<PrecedenceEdgeValidateResponse>(
    '/recovery/dependencies/validate-edge',
    request
  );
  return response.data;
}

/**
 * Seeds the standard 5-project precedence benchmark network (Phase 5).
 */
export async function seedStandardPrecedenceScenario(): Promise<any> {
  const response = await apiClient.post('/recovery/projects/seed-standard-scenario');
  return response.data;
}
