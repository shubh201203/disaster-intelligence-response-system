import { test, expect } from '@playwright/test';
import axios, { AxiosAdapter, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { apiClient } from '../../src/api/client';
import {
  evaluateRecoveryOptimizationScenario,
  normalizeOptimizationError,
} from '../../src/api/recoveryOptimization';
import { minimalValidScenarioRequestFixture } from '../../src/fixtures/recoveryOptimizationFixtures';
import { RecoveryOptimizationScenarioResponse } from '../../src/types/recoveryOptimization';

test.describe('Axios API Client Contract & Integration Suite', () => {
  let originalAdapter: AxiosAdapter | undefined;
  let originalLocalStorage: any;
  let mockDirsToken: string | null = null;

  test.beforeEach(() => {
    originalAdapter = apiClient.defaults.adapter;
    originalLocalStorage = (globalThis as any).localStorage;
    // Provide isolated in-memory localStorage for Node test runner
    (globalThis as any).localStorage = {
      getItem: (key: string) => (key === 'dirs_token' ? mockDirsToken : null),
      setItem: (key: string, val: string) => {
        if (key === 'dirs_token') mockDirsToken = val;
      },
      removeItem: (key: string) => {
        if (key === 'dirs_token') mockDirsToken = null;
      },
    };
  });

  test.afterEach(() => {
    apiClient.defaults.adapter = originalAdapter;
    (globalThis as any).localStorage = originalLocalStorage;
    mockDirsToken = null;
  });

  // ============================================================================
  // 1. Request Configuration & Invariant Tests
  // ============================================================================
  test('1. Dispatches POST to /recovery/optimization/evaluate with correct payload', async () => {
    let capturedConfig: InternalAxiosRequestConfig | null = null;

    apiClient.defaults.adapter = async (config: InternalAxiosRequestConfig): Promise<AxiosResponse> => {
      capturedConfig = config;
      const mockResponse: Partial<RecoveryOptimizationScenarioResponse> = {
        scenario_name: 'Minimal Valid Recovery Scenario',
        solver_status: 'OPTIMAL',
        is_optimal: true,
        exact_objective_value: '850000000000',
        total_cost_ccu: '500000000',
        total_cost_inr: '5000000.00',
        selected_project_count: 1,
        solve_time_seconds: 0.1,
        scheduled_projects: [],
        periodic_solvency: [],
        district_equity_allocation_ccu: {},
        district_equity_allocation_inr: {},
        input_fingerprint_sha256: 'a'.repeat(64),
        ortools_version: '9.8.3296',
        solver_parameters: {},
        infeasibility_diagnostics: null,
      };

      return {
        data: JSON.stringify(mockResponse),
        status: 200,
        statusText: 'OK',
        headers: { 'x-correlation-id': 'req-corr-uuid-1111' },
        config,
      };
    };

    const result = await evaluateRecoveryOptimizationScenario(minimalValidScenarioRequestFixture);

    expect(capturedConfig).not.toBeNull();
    expect(capturedConfig!.method?.toLowerCase()).toBe('post');
    expect(capturedConfig!.url).toBe('/recovery/optimization/evaluate');

    // Request payload passed through
    const sentData = typeof capturedConfig!.data === 'string'
      ? JSON.parse(capturedConfig!.data)
      : capturedConfig!.data;
    expect(sentData.scenario_name).toBe(minimalValidScenarioRequestFixture.scenario_name);
    expect(sentData.planning_horizon_periods).toBe(minimalValidScenarioRequestFixture.planning_horizon_periods);

    // Response evaluation
    expect(result.data.solver_status).toBe('OPTIMAL');
    expect(result.data.exact_objective_value).toBe('850000000000');
    expect(result.correlationId).toBe('req-corr-uuid-1111');
  });

  test('2. Enforces responseType: "text" and timeout: 130000 ms per request', async () => {
    let capturedConfig: InternalAxiosRequestConfig | null = null;

    apiClient.defaults.adapter = async (config: InternalAxiosRequestConfig): Promise<AxiosResponse> => {
      capturedConfig = config;
      return {
        data: JSON.stringify({
          scenario_name: 'Test',
          solver_status: 'OPTIMAL',
          is_optimal: true,
          exact_objective_value: '100',
          total_cost_ccu: '100',
          total_cost_inr: '1.00',
          selected_project_count: 0,
          solve_time_seconds: 0.1,
          scheduled_projects: [],
          periodic_solvency: [],
          district_equity_allocation_ccu: {},
          district_equity_allocation_inr: {},
          input_fingerprint_sha256: 'a'.repeat(64),
          ortools_version: '9.8.3296',
          solver_parameters: {},
          infeasibility_diagnostics: null,
        }),
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      };
    };

    await evaluateRecoveryOptimizationScenario(minimalValidScenarioRequestFixture);

    expect(capturedConfig).not.toBeNull();
    expect(capturedConfig!.timeout).toBe(130000);
    expect(capturedConfig!.responseType).toBe('text');
  });

  test('3. Isolation verification: does not mutate global apiClient defaults', async () => {
    apiClient.defaults.adapter = async (config: InternalAxiosRequestConfig): Promise<AxiosResponse> => {
      return {
        data: JSON.stringify({
          scenario_name: 'Test',
          solver_status: 'OPTIMAL',
          is_optimal: true,
          exact_objective_value: '100',
          total_cost_ccu: '100',
          total_cost_inr: '1.00',
          selected_project_count: 0,
          solve_time_seconds: 0.1,
          scheduled_projects: [],
          periodic_solvency: [],
          district_equity_allocation_ccu: {},
          district_equity_allocation_inr: {},
          input_fingerprint_sha256: 'a'.repeat(64),
          ortools_version: '9.8.3296',
          solver_parameters: {},
          infeasibility_diagnostics: null,
        }),
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      };
    };

    const initialDefaultTimeout = apiClient.defaults.timeout;
    const initialDefaultResponseType = apiClient.defaults.responseType;

    await evaluateRecoveryOptimizationScenario(minimalValidScenarioRequestFixture);

    // Assert global defaults remained unmodified
    expect(apiClient.defaults.timeout).toBe(initialDefaultTimeout);
    expect(apiClient.defaults.responseType).toBe(initialDefaultResponseType);
  });

  // ============================================================================
  // 2. Correlation ID Extraction & Header Variations
  // ============================================================================
  test('4. Extracts X-Correlation-ID case-insensitively from headers', async () => {
    // Upper case variation
    apiClient.defaults.adapter = async (config: InternalAxiosRequestConfig): Promise<AxiosResponse> => {
      return {
        data: JSON.stringify({
          scenario_name: 'Test',
          solver_status: 'OPTIMAL',
          is_optimal: true,
          exact_objective_value: null,
          total_cost_ccu: '0',
          total_cost_inr: '0.00',
          selected_project_count: 0,
          solve_time_seconds: 0.1,
          scheduled_projects: [],
          periodic_solvency: [],
          district_equity_allocation_ccu: {},
          district_equity_allocation_inr: {},
          input_fingerprint_sha256: 'a'.repeat(64),
          ortools_version: '9.8.3296',
          solver_parameters: {},
          infeasibility_diagnostics: null,
        }),
        status: 200,
        statusText: 'OK',
        headers: { 'X-Correlation-ID': 'UPPER-CASE-CORR-UUID' },
        config,
      };
    };

    const result = await evaluateRecoveryOptimizationScenario(minimalValidScenarioRequestFixture);
    expect(result.correlationId).toBe('UPPER-CASE-CORR-UUID');
  });

  test('5. Returns correlationId: null when header is absent', async () => {
    apiClient.defaults.adapter = async (config: InternalAxiosRequestConfig): Promise<AxiosResponse> => {
      return {
        data: JSON.stringify({
          scenario_name: 'Test',
          solver_status: 'OPTIMAL',
          is_optimal: true,
          exact_objective_value: null,
          total_cost_ccu: '0',
          total_cost_inr: '0.00',
          selected_project_count: 0,
          solve_time_seconds: 0.1,
          scheduled_projects: [],
          periodic_solvency: [],
          district_equity_allocation_ccu: {},
          district_equity_allocation_inr: {},
          input_fingerprint_sha256: 'a'.repeat(64),
          ortools_version: '9.8.3296',
          solver_parameters: {},
          infeasibility_diagnostics: null,
        }),
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      };
    };

    const result = await evaluateRecoveryOptimizationScenario(minimalValidScenarioRequestFixture);
    expect(result.correlationId).toBeNull();
  });

  // ============================================================================
  // 3. Error Normalization & Preservation of Diagnostic Reports
  // ============================================================================
  test('6. Normalizes structured backend 422 validation failure with diagnostic code', async () => {
    apiClient.defaults.adapter = async (config: InternalAxiosRequestConfig): Promise<AxiosResponse> => {
      const err = new axios.AxiosError(
        'Request failed with status code 422',
        'ERR_BAD_REQUEST',
        config,
        {},
        {
          data: {
            detail: {
              error_type: 'INVALID_REQUEST',
              message: 'Invalid planning horizon periods',
              diagnostic_code: 'val-diag-code-999',
              validation_failures: ['planning_horizon_periods must be between 1 and 120'],
              input_fingerprint_sha256: 'b'.repeat(64),
              infeasibility_diagnostics: null,
            },
          },
          status: 422,
          statusText: 'Unprocessable Entity',
          headers: { 'x-correlation-id': 'val-diag-code-999' },
          config,
        }
      );
      throw err;
    };

    await expect(evaluateRecoveryOptimizationScenario(minimalValidScenarioRequestFixture)).rejects.toMatchObject({
      isOptimizationError: true,
      status: 422,
      correlationId: 'val-diag-code-999',
      detail: {
        error_type: 'INVALID_REQUEST',
        message: 'Invalid planning horizon periods',
        diagnostic_code: 'val-diag-code-999',
        validation_failures: ['planning_horizon_periods must be between 1 and 120'],
      },
    });
  });

  test('7. Normalizes network / solver timeout to SOLVER_TIMEOUT', async () => {
    apiClient.defaults.adapter = async (config: InternalAxiosRequestConfig): Promise<AxiosResponse> => {
      const err = new axios.AxiosError(
        'timeout of 130000ms exceeded',
        'ECONNABORTED',
        config
      );
      throw err;
    };

    await expect(evaluateRecoveryOptimizationScenario(minimalValidScenarioRequestFixture)).rejects.toMatchObject({
      isOptimizationError: true,
      status: 0,
      detail: {
        error_type: 'SOLVER_TIMEOUT',
      },
    });
  });

  // ============================================================================
  // 4. JWT Interceptor Integration
  // ============================================================================
  test('8. Reuses apiClient JWT interceptor when dirs_token is present in storage', async () => {
    mockDirsToken = 'mock-jwt-token-xyz';
    let capturedHeaders: any = null;

    apiClient.defaults.adapter = async (config: InternalAxiosRequestConfig): Promise<AxiosResponse> => {
      capturedHeaders = config.headers;
      return {
        data: JSON.stringify({
          scenario_name: 'Test',
          solver_status: 'OPTIMAL',
          is_optimal: true,
          exact_objective_value: null,
          total_cost_ccu: '0',
          total_cost_inr: '0.00',
          selected_project_count: 0,
          solve_time_seconds: 0.1,
          scheduled_projects: [],
          periodic_solvency: [],
          district_equity_allocation_ccu: {},
          district_equity_allocation_inr: {},
          input_fingerprint_sha256: 'a'.repeat(64),
          ortools_version: '9.8.3296',
          solver_parameters: {},
          infeasibility_diagnostics: null,
        }),
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      };
    };

    await evaluateRecoveryOptimizationScenario(minimalValidScenarioRequestFixture);
    expect(capturedHeaders).not.toBeNull();
    expect(capturedHeaders.Authorization).toBe('Bearer mock-jwt-token-xyz');
  });
});
