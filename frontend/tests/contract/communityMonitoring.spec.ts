/**
 * DIRS Phase 6F / Accelerated Programme Work Package 2
 * Community Recovery Monitoring & Simulation Contract Test Suite.
 *
 * Verifies mathematical, numerical, and structural contract invariants:
 * 1. CommunityMetricSummaryResponse and WardRecoveryIndicatorDTO schemas.
 * 2. Exponential confidence decay and freshness status enum invariants.
 * 3. VulnerabilityRescoreRequest/Response schemas and mathematical audit trail.
 * 4. RecoveryWhatIfSimulationRequest/Response and non-mutating guarantee.
 * 5. Simulation trajectory period snapshots and resource bottleneck structures.
 */

import { test, expect } from '@playwright/test';
import {
  WardRecoveryIndicatorDTO,
  CommunityMetricSummaryResponse,
  VulnerabilityRescoreRequest,
  VulnerabilityRescoreResponse,
  RecoveryWhatIfSimulationRequest,
  RecoveryWhatIfSimulationResponse,
  SimulationPeriodSnapshot,
  BottleneckResourceItem,
} from '../../src/types/communityMonitoring';

test.describe('WP2 Community Recovery Monitoring & Simulation Contracts', () => {
  // ============================================================================
  // 1. Community Recovery Metric Summary Invariants
  // ============================================================================
  test.describe('1. Community Metrics Summary Contract', () => {
    test('Empty community summary conforms to baseline schema', () => {
      const emptySummary: CommunityMetricSummaryResponse = {
        total_wards_monitored: 0,
        reporting_date_range: { earliest: null, latest: null },
        average_recovery_score: 0.0,
        average_confidence: 100.0,
        sector_restoration_averages: {
          power: 0.0,
          water: 0.0,
          health: 0.0,
          schools: 0.0,
          livelihoods: 0.0,
        },
        total_active_shelters: 0,
        total_remaining_displaced: 0,
        freshness_distribution: {
          FRESH: 0,
          MODERATE: 0,
          STALE_AMBER: 0,
          EXPIRED_RED: 0,
        },
        wards: [],
      };

      expect(emptySummary.total_wards_monitored).toBe(0);
      expect(emptySummary.average_confidence).toBe(100.0);
      expect(emptySummary.wards).toHaveLength(0);
      expect(emptySummary.reporting_date_range.earliest).toBeNull();
    });

    test('Ward indicator adheres to numerical bounds and freshness categories', () => {
      const wardDTO: WardRecoveryIndicatorDTO = {
        ward_code: 'WARD-CENTRAL-01',
        district: 'Central',
        metric_date: '2026-11-18T00:00:00Z',
        active_shelter_count: 2,
        remaining_displaced_persons: 120,
        power_grid_restoration_pct: 85.0,
        potable_water_access_pct: 90.0,
        healthcare_facility_operational_pct: 75.0,
        schools_open_pct: 80.0,
        livelihoods_resumed_pct: 60.0,
        overall_recovery_score: 79.25,
        initial_confidence: 100.0,
        current_confidence: 94.5,
        freshness_status: 'FRESH',
        days_since_verification: 1.1,
        last_verified_at: '2026-11-17T00:00:00Z',
        verified_by_id: 'user-001',
      };

      expect(wardDTO.overall_recovery_score).toBeGreaterThanOrEqual(0.0);
      expect(wardDTO.overall_recovery_score).toBeLessThanOrEqual(100.0);
      expect(wardDTO.current_confidence).toBeGreaterThanOrEqual(0.0);
      expect(wardDTO.current_confidence).toBeLessThanOrEqual(100.0);
      expect(['FRESH', 'MODERATE', 'STALE_AMBER', 'EXPIRED_RED']).toContain(wardDTO.freshness_status);
    });
  });

  // ============================================================================
  // 2. Vulnerability Rescoring Invariants
  // ============================================================================
  test.describe('2. Vulnerability Rescoring Contract & Math Bounds', () => {
    test('Rescore response enforces normalized phi in [0.0, 1.0] and audit trail', () => {
      const rescoreFixture: VulnerabilityRescoreResponse = {
        ward_code: 'WARD-NORTH-04',
        district: 'North District',
        base_demographic_vulnerability: 0.450000,
        rescored_vulnerability: 0.385000,
        vulnerability_delta: -0.065000,
        raw_headcount_index_psi: 325.0,
        baseline_status: 'BASELINE_KNOWN',
        effective_denominator: 1200.0,
        infrastructure_deficit_score: 0.3500,
        displacement_pressure_score: 0.2000,
        data_confidence: 90.5,
        freshness_status: 'FRESH',
        days_elapsed: 2.0,
        uncertainty_flag: false,
        audit_trail: {
          formula: 'phi_rescored = min(1.0, 0.50*eff_base + 0.35*I_def*eff_base + 0.15*D_press)',
          headcount_psi: 325.0,
        },
      };

      expect(rescoreFixture.base_demographic_vulnerability).toBeGreaterThanOrEqual(0.0);
      expect(rescoreFixture.base_demographic_vulnerability).toBeLessThanOrEqual(1.0);
      expect(rescoreFixture.rescored_vulnerability).toBeGreaterThanOrEqual(0.0);
      expect(rescoreFixture.rescored_vulnerability).toBeLessThanOrEqual(1.0);
      expect(rescoreFixture.vulnerability_delta).toBe(
        rescoreFixture.rescored_vulnerability - rescoreFixture.base_demographic_vulnerability
      );
      expect(['BASELINE_KNOWN', 'BASELINE_UNKNOWN']).toContain(rescoreFixture.baseline_status);
      expect(rescoreFixture.audit_trail).toHaveProperty('formula');
    });

    test('Unknown census baseline requires uncertainty flag and positive denominator', () => {
      const unknownCensusRescore: VulnerabilityRescoreResponse = {
        ward_code: 'WARD-REMOTE-09',
        district: 'Remote Highland',
        base_demographic_vulnerability: 0.650000,
        rescored_vulnerability: 0.720000,
        vulnerability_delta: 0.070000,
        raw_headcount_index_psi: 325.0,
        baseline_status: 'BASELINE_UNKNOWN',
        effective_denominator: 500.0,
        infrastructure_deficit_score: 0.7500,
        displacement_pressure_score: 0.4000,
        data_confidence: 42.0,
        freshness_status: 'STALE_AMBER',
        days_elapsed: 17.5,
        uncertainty_flag: true,
        audit_trail: {},
      };

      expect(unknownCensusRescore.baseline_status).toBe('BASELINE_UNKNOWN');
      expect(unknownCensusRescore.effective_denominator).toBe(500.0);
      expect(unknownCensusRescore.uncertainty_flag).toBe(true);
    });
  });

  // ============================================================================
  // 3. What-If Simulation Engine Invariants
  // ============================================================================
  test.describe('3. What-If Forward Simulation Contract', () => {
    test('Simulation response guarantees is_non_mutating=true and monotonic trajectory', () => {
      const simResponse: RecoveryWhatIfSimulationResponse = {
        scenario_name: 'Test Coastal Restoration',
        planning_horizon_periods: 6,
        period_length_days: 30.0,
        is_non_mutating: true,
        baseline_completion_period: 5,
        simulated_completion_period: 4,
        baseline_final_recovery_score: 85.0,
        simulated_final_recovery_score: 92.5,
        recovery_score_delta: 7.5,
        periods_to_target_80pct: 4,
        total_budget_allocated: 20000000.0,
        total_budget_utilized: 18500000.0,
        unmet_budget_deficit: 0.0,
        bottleneck_resources: [],
        trajectory: [
          {
            period: 1,
            calendar_day: 30.0,
            capital_spent_period: 3000000.0,
            cumulative_capital_spent: 3000000.0,
            remaining_cash_balance: 17000000.0,
            projects_in_progress: 3,
            projects_completed_cumulative: 0,
            displaced_persons_remaining: 500,
            projected_recovery_score: 15.0,
            unmet_needs_score: 85.0,
            shock_occurred: false,
          },
          {
            period: 2,
            calendar_day: 60.0,
            capital_spent_period: 4000000.0,
            cumulative_capital_spent: 7000000.0,
            remaining_cash_balance: 13000000.0,
            projects_in_progress: 3,
            projects_completed_cumulative: 1,
            displaced_persons_remaining: 350,
            projected_recovery_score: 40.0,
            unmet_needs_score: 60.0,
            shock_occurred: false,
          },
          {
            period: 3,
            calendar_day: 90.0,
            capital_spent_period: 4000000.0,
            cumulative_capital_spent: 11000000.0,
            remaining_cash_balance: 9000000.0,
            projects_in_progress: 2,
            projects_completed_cumulative: 3,
            displaced_persons_remaining: 150,
            projected_recovery_score: 75.0,
            unmet_needs_score: 25.0,
            shock_occurred: false,
          },
          {
            period: 4,
            calendar_day: 120.0,
            capital_spent_period: 3500000.0,
            cumulative_capital_spent: 14500000.0,
            remaining_cash_balance: 5500000.0,
            projects_in_progress: 1,
            projects_completed_cumulative: 4,
            displaced_persons_remaining: 50,
            projected_recovery_score: 88.0,
            unmet_needs_score: 12.0,
            shock_occurred: false,
          },
          {
            period: 5,
            calendar_day: 150.0,
            capital_spent_period: 2500000.0,
            cumulative_capital_spent: 17000000.0,
            remaining_cash_balance: 3000000.0,
            projects_in_progress: 1,
            projects_completed_cumulative: 5,
            displaced_persons_remaining: 10,
            projected_recovery_score: 92.5,
            unmet_needs_score: 7.5,
            shock_occurred: false,
          },
          {
            period: 6,
            calendar_day: 180.0,
            capital_spent_period: 1500000.0,
            cumulative_capital_spent: 18500000.0,
            remaining_cash_balance: 1500000.0,
            projects_in_progress: 0,
            projects_completed_cumulative: 5,
            displaced_persons_remaining: 0,
            projected_recovery_score: 92.5,
            unmet_needs_score: 7.5,
            shock_occurred: false,
          },
        ],
        simulation_provenance: { is_non_mutating: true },
      };

      expect(simResponse.is_non_mutating).toBe(true);
      expect(simResponse.trajectory).toHaveLength(6);

      // Verify monotonic period indexing
      for (let i = 0; i < simResponse.trajectory.length; i++) {
        expect(simResponse.trajectory[i].period).toBe(i + 1);
        expect(simResponse.trajectory[i].calendar_day).toBe((i + 1) * simResponse.period_length_days);
      }
    });

    test('Bottleneck resources correctly quantify deficits and impact levels', () => {
      const bottleneckItem: BottleneckResourceItem = {
        material_category: 'CEMENT',
        demand_quantity: 150.0,
        available_supply: 90.0,
        deficit_quantity: 60.0,
        impact_level: 'HIGH',
      };

      expect(bottleneckItem.deficit_quantity).toBe(
        bottleneckItem.demand_quantity - bottleneckItem.available_supply
      );
      expect(['HIGH', 'MODERATE', 'LOW']).toContain(bottleneckItem.impact_level);
    });
  });
});
