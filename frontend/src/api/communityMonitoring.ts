import { apiClient } from './client';
import {
  CommunityMetricSummaryResponse,
  VulnerabilityRescoreRequest,
  VulnerabilityRescoreResponse,
  RecoveryWhatIfSimulationRequest,
  RecoveryWhatIfSimulationResponse,
} from '../types/communityMonitoring';

export async function fetchCommunityMetricsSummary(
  wardCode?: string,
  district?: string
): Promise<CommunityMetricSummaryResponse> {
  const params = new URLSearchParams();
  if (wardCode) params.append('ward_code', wardCode);
  if (district) params.append('district', district);

  const url = `/recovery/monitoring/community-metrics/summary${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await apiClient.get<CommunityMetricSummaryResponse>(url);
  return response.data;
}

export async function rescoreVulnerability(
  data: VulnerabilityRescoreRequest
): Promise<VulnerabilityRescoreResponse> {
  const response = await apiClient.post<VulnerabilityRescoreResponse>(
    '/recovery/monitoring/vulnerability-rescore',
    data
  );
  return response.data;
}

export async function simulateRecoveryWhatIf(
  data: RecoveryWhatIfSimulationRequest
): Promise<RecoveryWhatIfSimulationResponse> {
  const response = await apiClient.post<RecoveryWhatIfSimulationResponse>(
    '/recovery/simulation/what-if',
    data
  );
  return response.data;
}
