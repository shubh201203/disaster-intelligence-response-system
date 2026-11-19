/**
 * DIRS Phase 6D-B Milestone 4 Gate 3
 * Synthetic Recovery Portfolio Optimization Mock Fixtures & Route Handlers
 *
 * Provides typed test data and Playwright route interception utilities for:
 * 1. Multi-role authentication & session mock profiles (ADMIN, GOVT, CITIZEN, VOLUNTEER, NGO).
 * 2. Scenario configuration templates (Minimal Valid, Tier-1 Safety).
 * 3. All six (6) solver outcomes: OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN, MODEL_INVALID, POST_SOLVE_RECONCILIATION_FAILED.
 * 4. Operational error scenarios: HTTP 401, 403, 422, 500, timeout, transport disconnect, malformed JSON.
 */

import { Page, Route } from '@playwright/test';
import {
  RecoveryOptimizationScenarioRequest,
  RecoveryOptimizationScenarioResponse,
  SolverOutcomeStatus,
} from '../../../src/types/recoveryOptimization';
import { UserProfile } from '../../../src/context/AuthContext';

// ============================================================================
// 1. AUTHENTICATION & ROLE PROFILES
// ============================================================================

export const MOCK_USERS: Record<string, UserProfile> = {
  ADMIN: {
    id: 'usr-admin-001',
    email: 'admin@dirs.gov',
    full_name: 'System Administrator',
    role: 'ADMIN',
    phone: '+91-9876543210',
  },
  GOVT: {
    id: 'usr-govt-001',
    email: 'commissioner@dirs.gov',
    full_name: 'State Disaster Commissioner',
    role: 'GOVT',
    phone: '+91-9876543211',
  },
  CITIZEN: {
    id: 'usr-citizen-001',
    email: 'citizen@dirs.org',
    full_name: 'Resident Citizen',
    role: 'CITIZEN',
    phone: '+91-9876543212',
  },
  VOLUNTEER: {
    id: 'usr-volunteer-001',
    email: 'volunteer@dirs.org',
    full_name: 'Field Volunteer',
    role: 'VOLUNTEER',
    phone: '+91-9876543213',
  },
  NGO: {
    id: 'usr-ngo-001',
    email: 'ngo-director@relief.org',
    full_name: 'NGO Coordinator',
    role: 'NGO',
    phone: '+91-9876543214',
  },
};

export const MOCK_TOKENS: Record<string, string> = {
  ADMIN: 'mock-jwt-token-admin-dirs-session-auth',
  GOVT: 'mock-jwt-token-govt-dirs-session-auth',
  CITIZEN: 'mock-jwt-token-citizen-dirs-session-auth',
  VOLUNTEER: 'mock-jwt-token-volunteer-dirs-session-auth',
  NGO: 'mock-jwt-token-ngo-dirs-session-auth',
};

/**
 * Configure page-level authentication state for a designated role.
 * Injects token into localStorage and configures /api/v1/auth/me route response.
 */
export async function setupMockAuth(page: Page, role: 'ADMIN' | 'GOVT' | 'CITIZEN' | 'VOLUNTEER' | 'NGO'): Promise<void> {
  const token = MOCK_TOKENS[role];
  const user = MOCK_USERS[role];

  // Intercept auth verification endpoint
  await page.route('**/api/v1/auth/me', async (route) => {
    const authHeader = route.request().headers()['authorization'];
    if (authHeader === `Bearer ${token}`) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(user),
      });
    } else {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid or expired authentication token' }),
      });
    }
  });

  // Pre-populate localStorage with auth token before page load
  await page.addInitScript(
    ({ authToken }) => {
      window.localStorage.setItem('dirs_token', authToken);
    },
    { authToken: token }
  );
}

/**
 * Configure login endpoint route interception.
 */
export async function setupMockLogin(page: Page): Promise<void> {
  await page.route('**/api/v1/auth/login', async (route) => {
    const postData = route.request().postData() || '';
    const params = new URLSearchParams(postData);
    const email = params.get('username') || '';

    // Match user by email
    const matchingRole = Object.keys(MOCK_USERS).find((r) => MOCK_USERS[r].email === email);
    if (matchingRole) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: MOCK_TOKENS[matchingRole],
          token_type: 'bearer',
          user: MOCK_USERS[matchingRole],
        }),
      });
    } else {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Incorrect email or password' }),
      });
    }
  });
}

// ============================================================================
// 2. SCENARIO CONFIGURATION TEMPLATES
// ============================================================================

export const minimalScenarioTemplate: RecoveryOptimizationScenarioRequest = {
  scenario_name: 'Minimal Valid Template',
  planning_horizon_periods: 12,
  period_length_days: 30.0,
  initial_cash: '10000000.00',
  cash_currency: 'INR',
  periodic_budgets: {
    1: '10000000.00',
    2: '5000000.00',
    3: '5000000.00',
    4: '5000000.00',
    5: '5000000.00',
    6: '5000000.00',
    7: '5000000.00',
    8: '5000000.00',
    9: '5000000.00',
    10: '5000000.00',
    11: '5000000.00',
    12: '5000000.00',
  },
  candidate_projects: [
    {
      candidate_id: 'CAND-001',
      name: 'Emergency Bridge Repair',
      category: 'INFRASTRUCTURE',
      priority: 1,
      estimated_cost: '4500000.00',
      duration_periods: 2,
      earliest_start_period: 1,
      latest_completion_period: 4,
      district: 'North Riverine',
      is_selected: true,
    },
  ],
  dependency_edges: [],
  funding_sources: [],
};

// ============================================================================
// 3. SYNTHETIC SOLVER OUTCOME FIXTURES
// ============================================================================

export const mockOptimalSolverResponse: RecoveryOptimizationScenarioResponse = {
  scenario_name: 'Urban Infrastructure Recovery Plan',
  status: 'OPTIMAL',
  objective_value: '94.50000000',
  optimality_gap: '0.00000000',
  solve_time_seconds: 1.42,
  total_cash_allocated: '4500000.00',
  cash_currency: 'INR',
  scheduled_projects: [
    {
      candidate_id: 'CAND-001',
      name: 'Emergency Bridge Repair',
      category: 'INFRASTRUCTURE',
      scheduled_start_period: 1,
      scheduled_completion_period: 2,
      allocated_cash: '4500000.00',
      is_selected: true,
      execution_status: 'SCHEDULED',
    },
  ],
  period_solvency: [
    {
      period: 1,
      cash_spent: '2250000.00',
      cash_remaining: '7750000.00',
      ccu_spent: 450,
      ccu_remaining: 5550,
      is_solvent: true,
    },
    {
      period: 2,
      cash_spent: '2250000.00',
      cash_remaining: '5500000.00',
      ccu_spent: 450,
      ccu_remaining: 5100,
      is_solvent: true,
    },
  ],
  infeasibility_diagnostics: null,
};

export const mockFeasibleSolverResponse: RecoveryOptimizationScenarioResponse = {
  scenario_name: 'Feasible Tier-1 Allocation',
  status: 'FEASIBLE',
  objective_value: '82.00000000',
  optimality_gap: '0.12500000',
  solve_time_seconds: 3.18,
  total_cash_allocated: '4500000.00',
  cash_currency: 'INR',
  scheduled_projects: [
    {
      candidate_id: 'CAND-001',
      name: 'Emergency Bridge Repair',
      category: 'INFRASTRUCTURE',
      scheduled_start_period: 2,
      scheduled_completion_period: 3,
      allocated_cash: '4500000.00',
      is_selected: true,
      execution_status: 'SCHEDULED',
    },
  ],
  period_solvency: [
    {
      period: 1,
      cash_spent: '0.00',
      cash_remaining: '10000000.00',
      ccu_spent: 0,
      ccu_remaining: 6000,
      is_solvent: true,
    },
    {
      period: 2,
      cash_spent: '2250000.00',
      cash_remaining: '7750000.00',
      ccu_spent: 450,
      ccu_remaining: 5550,
      is_solvent: true,
    },
  ],
  infeasibility_diagnostics: null,
};

export const mockInfeasibleSolverResponse: RecoveryOptimizationScenarioResponse = {
  scenario_name: 'Overconstrained Recovery Scenario',
  status: 'INFEASIBLE',
  objective_value: null,
  optimality_gap: null,
  solve_time_seconds: 0.85,
  total_cash_allocated: '0.00',
  cash_currency: 'INR',
  scheduled_projects: [],
  period_solvency: [],
  infeasibility_diagnostics: {
    status: 'INFEASIBLE',
    summary_message: 'Optimization model is mathematically infeasible under current constraints.',
    findings_by_tier: {
      tier1_hard_conflicts: [
        {
          tier: 'TIER_1',
          code: 'BUDGET_EXCEEDED_PERIOD_1',
          message: 'Required initial project cost exceeds period 1 budget.',
          related_candidates: ['CAND-001'],
          related_periods: [1],
        },
      ],
      tier2_dependency_deadlocks: [],
      tier3_capacity_shortfalls: [],
      tier4_policy_violations: [],
    },
    assumption_core_size: 1,
    assumption_core_minimality_verified: true,
    is_sufficient: true,
  },
};

export const mockUnknownSolverResponse: RecoveryOptimizationScenarioResponse = {
  scenario_name: 'Indeterminate Solver Outcome',
  status: 'UNKNOWN',
  objective_value: null,
  optimality_gap: null,
  solve_time_seconds: 0.12,
  total_cash_allocated: '0.00',
  cash_currency: 'INR',
  scheduled_projects: [],
  period_solvency: [],
  infeasibility_diagnostics: null,
};

export const mockModelInvalidSolverResponse: RecoveryOptimizationScenarioResponse = {
  scenario_name: 'Malformed Constraint Model',
  status: 'MODEL_INVALID',
  objective_value: null,
  optimality_gap: null,
  solve_time_seconds: 0.05,
  total_cash_allocated: '0.00',
  cash_currency: 'INR',
  scheduled_projects: [],
  period_solvency: [],
  infeasibility_diagnostics: {
    status: 'MODEL_INVALID',
    summary_message: 'Scenario specification violates mathematical model formulation rules.',
    findings_by_tier: {
      tier1_hard_conflicts: [
        {
          tier: 'TIER_1',
          code: 'CIRCULAR_DEPENDENCY_DETECTED',
          message: 'Project candidate dependency graph contains directed cycle.',
          related_candidates: ['CAND-001', 'CAND-002'],
          related_periods: [],
        },
      ],
      tier2_dependency_deadlocks: [],
      tier3_capacity_shortfalls: [],
      tier4_policy_violations: [],
    },
    assumption_core_size: 2,
    assumption_core_minimality_verified: false,
    is_sufficient: false,
  },
};

export const mockReconciliationFailedSolverResponse: RecoveryOptimizationScenarioResponse = {
  scenario_name: 'Post-Solve Invariant Mismatch',
  status: 'POST_SOLVE_RECONCILIATION_FAILED',
  objective_value: null,
  optimality_gap: null,
  solve_time_seconds: 1.15,
  total_cash_allocated: '0.00',
  cash_currency: 'INR',
  scheduled_projects: [],
  period_solvency: [],
  infeasibility_diagnostics: {
    status: 'POST_SOLVE_RECONCILIATION_FAILED',
    summary_message: 'Solver produced schedule that violates physical project duration invariants.',
    findings_by_tier: {
      tier1_hard_conflicts: [
        {
          tier: 'TIER_1',
          code: 'DURATION_INTEGRITY_MISMATCH',
          message: 'Calculated project span does not equal declared duration periods.',
          related_candidates: ['CAND-001'],
          related_periods: [1, 2],
        },
      ],
      tier2_dependency_deadlocks: [],
      tier3_capacity_shortfalls: [],
      tier4_policy_violations: [],
    },
    assumption_core_size: 1,
    assumption_core_minimality_verified: true,
    is_sufficient: true,
  },
};

// ============================================================================
// 4. ROUTE INTERCEPTION UTILITIES
// ============================================================================

/**
 * Intercept solver evaluate endpoint and return synthetic solver response.
 */
export async function mockSolverOutcome(
  page: Page,
  response: RecoveryOptimizationScenarioResponse,
  delayMs: number = 0
): Promise<void> {
  await page.route('**/api/v1/recovery/optimization/evaluate', async (route) => {
    if (delayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response),
    });
  });
}

/**
 * Intercept solver evaluate endpoint and return an HTTP error status.
 */
export async function mockSolverHttpError(
  page: Page,
  status: number,
  body: any,
  headers: Record<string, string> = {}
): Promise<void> {
  await page.route('**/api/v1/recovery/optimization/evaluate', async (route) => {
    await route.fulfill({
      status,
      contentType: 'application/json',
      headers: {
        'x-correlation-id': 'corr-e2e-err-7890',
        ...headers,
      },
      body: typeof body === 'string' ? body : JSON.stringify(body),
    });
  });
}

/**
 * Intercept solver evaluate endpoint and abort with network transport drop.
 */
export async function mockSolverNetworkDrop(page: Page): Promise<void> {
  await page.route('**/api/v1/recovery/optimization/evaluate', async (route) => {
    await route.abort('failed');
  });
}
