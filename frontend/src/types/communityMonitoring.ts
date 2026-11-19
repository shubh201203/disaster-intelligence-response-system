export interface WardRecoveryIndicatorDTO {
  ward_code: string;
  district: string;
  metric_date: string;
  active_shelter_count: number;
  remaining_displaced_persons: number;
  power_grid_restoration_pct: number;
  potable_water_access_pct: number;
  healthcare_facility_operational_pct: number;
  schools_open_pct: number;
  livelihoods_resumed_pct: number;
  overall_recovery_score: number;
  initial_confidence: number;
  current_confidence: number;
  freshness_status: 'FRESH' | 'MODERATE' | 'STALE_AMBER' | 'EXPIRED_RED';
  days_since_verification: number;
  last_verified_at: string;
  verified_by_id?: string | null;
}

export interface CommunityMetricSummaryResponse {
  total_wards_monitored: number;
  reporting_date_range: {
    earliest: string | null;
    latest: string | null;
  };
  average_recovery_score: number;
  average_confidence: number;
  sector_restoration_averages: {
    power: number;
    water: number;
    health: number;
    schools: number;
    livelihoods: number;
  };
  total_active_shelters: number;
  total_remaining_displaced: number;
  freshness_distribution: {
    FRESH: number;
    MODERATE: number;
    STALE_AMBER: number;
    EXPIRED_RED: number;
  };
  wards: WardRecoveryIndicatorDTO[];
}

export interface VulnerabilityRescoreRequest {
  ward_code: string;
  district: string;
  total_affected_population: number;
  n_accessible_needs?: number;
  n_chronic_medical?: number;
  n_intersectional?: number;
  n_general?: number;
  census_baseline_population?: number;
  power_grid_restoration_pct?: number;
  potable_water_access_pct?: number;
  healthcare_facility_operational_pct?: number;
  schools_open_pct?: number;
  livelihoods_resumed_pct?: number;
  remaining_displaced_persons?: number;
  last_verified_at?: string;
}

export interface VulnerabilityRescoreResponse {
  ward_code: string;
  district: string;
  base_demographic_vulnerability: number;
  rescored_vulnerability: number;
  vulnerability_delta: number;
  raw_headcount_index_psi: number;
  baseline_status: 'BASELINE_KNOWN' | 'BASELINE_UNKNOWN';
  effective_denominator: number;
  infrastructure_deficit_score: number;
  displacement_pressure_score: number;
  data_confidence: number;
  freshness_status: 'FRESH' | 'MODERATE' | 'STALE_AMBER' | 'EXPIRED_RED';
  days_elapsed: number;
  uncertainty_flag: boolean;
  audit_trail: Record<string, any>;
}

export interface SimulationPerturbationParams {
  budget_multiplier: number;
  material_supply_factor: number;
  disaster_recurrence_shock: boolean;
  shock_period: number;
  shock_damage_factor: number;
  sector_priorities: Record<string, number>;
}

export interface RecoveryWhatIfSimulationRequest {
  scenario_name: string;
  planning_horizon_periods: number;
  period_length_days: number;
  initial_budget: number;
  periodic_budget_inflow: number;
  target_ward_codes?: string[];
  perturbation: SimulationPerturbationParams;
  candidate_project_ids?: string[];
}

export interface SimulationPeriodSnapshot {
  period: number;
  calendar_day: number;
  capital_spent_period: number;
  cumulative_capital_spent: number;
  remaining_cash_balance: number;
  projects_in_progress: number;
  projects_completed_cumulative: number;
  displaced_persons_remaining: number;
  projected_recovery_score: number;
  unmet_needs_score: number;
  shock_occurred: boolean;
}

export interface BottleneckResourceItem {
  material_category: string;
  demand_quantity: number;
  available_supply: number;
  deficit_quantity: number;
  impact_level: 'HIGH' | 'MODERATE' | 'LOW';
}

export interface RecoveryWhatIfSimulationResponse {
  scenario_name: string;
  planning_horizon_periods: number;
  period_length_days: number;
  is_non_mutating: boolean;
  baseline_completion_period: number | null;
  simulated_completion_period: number | null;
  baseline_final_recovery_score: number;
  simulated_final_recovery_score: number;
  recovery_score_delta: number;
  periods_to_target_80pct: number | null;
  total_budget_allocated: number;
  total_budget_utilized: number;
  unmet_budget_deficit: number;
  bottleneck_resources: BottleneckResourceItem[];
  trajectory: SimulationPeriodSnapshot[];
  simulation_provenance: Record<string, any>;
}
