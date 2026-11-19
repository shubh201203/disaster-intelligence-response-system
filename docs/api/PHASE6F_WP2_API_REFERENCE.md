# DIRS Phase 6F / Accelerated Programme WP2: API Reference

**Document Version:** 1.0.0  
**Base Path:** `/api/v1/recovery`  
**Authentication:** HTTP Bearer JWT (`Authorization: Bearer <token>`)  

---

## 1. Community Recovery Metrics Summary

### `GET /api/v1/recovery/monitoring/community-metrics/summary`

Aggregates longitudinal recovery indicators across all wards or filtered by administrative area. Evaluates real-time exponential confidence decay based on elapsed time since verification.

#### Query Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `ward_code` | `string` | Optional | Filter by specific administrative ward code |
| `district` | `string` | Optional | Filter by administrative district |

#### Access Control
- Allowed Roles: `GOVT`, `ADMIN`, `NGO`, `VOLUNTEER`, `CITIZEN`

#### Response Schema (`200 OK`)
```json
{
  "total_wards_monitored": 4,
  "reporting_date_range": {
    "earliest": "2026-11-10T00:00:00Z",
    "latest": "2026-11-18T00:00:00Z"
  },
  "average_recovery_score": 74.25,
  "average_confidence": 88.5,
  "sector_restoration_averages": {
    "power": 80.0,
    "water": 85.0,
    "health": 72.0,
    "schools": 68.0,
    "livelihoods": 65.0
  },
  "total_active_shelters": 6,
  "total_remaining_displaced": 380,
  "freshness_distribution": {
    "FRESH": 3,
    "MODERATE": 1,
    "STALE_AMBER": 0,
    "EXPIRED_RED": 0
  },
  "wards": [
    {
      "ward_code": "WARD-01",
      "district": "Central District",
      "metric_date": "2026-11-18T00:00:00Z",
      "active_shelter_count": 2,
      "remaining_displaced_persons": 120,
      "power_grid_restoration_pct": 85.0,
      "potable_water_access_pct": 90.0,
      "healthcare_facility_operational_pct": 75.0,
      "schools_open_pct": 80.0,
      "livelihoods_resumed_pct": 60.0,
      "overall_recovery_score": 79.25,
      "initial_confidence": 100.0,
      "current_confidence": 94.5,
      "freshness_status": "FRESH",
      "days_since_verification": 1.1,
      "last_verified_at": "2026-11-17T00:00:00Z",
      "verified_by_id": "usr-001"
    }
  ]
}
```

---

## 2. Dynamic Vulnerability Rescoring

### `POST /api/v1/recovery/monitoring/vulnerability-rescore`

Evaluates transparent vulnerability rescoring fusing pure demographic baselines with operational infrastructure restoration deficits, displacement pressure, and observation confidence decay.

#### Access Control
- Allowed Roles: `GOVT`, `ADMIN`, `NGO`, `VOLUNTEER`, `CITIZEN`

#### Request Payload
```json
{
  "ward_code": "WARD-NORTH-04",
  "district": "North District",
  "total_affected_population": 1200,
  "n_accessible_needs": 40,
  "n_chronic_medical": 30,
  "n_intersectional": 10,
  "n_general": null,
  "census_baseline_population": 10000,
  "power_grid_restoration_pct": 60.0,
  "potable_water_access_pct": 70.0,
  "healthcare_facility_operational_pct": 80.0,
  "schools_open_pct": 50.0,
  "livelihoods_resumed_pct": 40.0,
  "remaining_displaced_persons": 150,
  "last_verified_at": "2026-11-17T00:00:00Z"
}
```

#### Response Schema (`200 OK`)
```json
{
  "ward_code": "WARD-NORTH-04",
  "district": "North District",
  "base_demographic_vulnerability": 0.650000,
  "rescored_vulnerability": 0.472500,
  "vulnerability_delta": -0.177500,
  "raw_headcount_index_psi": 1300.0,
  "baseline_status": "BASELINE_KNOWN",
  "effective_denominator": 2000.0,
  "infrastructure_deficit_score": 0.3800,
  "displacement_pressure_score": 0.1000,
  "data_confidence": 94.5,
  "freshness_status": "FRESH",
  "days_elapsed": 1.1,
  "uncertainty_flag": false,
  "audit_trail": {
    "formula": "phi_rescored = min(1.0, 0.50*eff_base + 0.35*I_def*eff_base + 0.15*D_press)",
    "infrastructure_deficit_score": 0.38,
    "displacement_pressure_score": 0.10,
    "headcount_psi": 1300.0
  }
}
```

---

## 3. What-If Forward Simulation Engine

### `POST /api/v1/recovery/simulation/what-if`

Executes deterministic, non-mutating forward simulation evaluating policy decisions, budget shifts, resource supply bottlenecks, and secondary hazard recurrence events over planning horizon $T$.

#### Access Control
- Allowed Roles: `GOVT`, `ADMIN` (HTTP 403 Forbidden for unauthorized roles)

#### Request Payload
```json
{
  "scenario_name": "Coastal Inundation Perturbation Analysis",
  "planning_horizon_periods": 12,
  "period_length_days": 30.0,
  "initial_budget": 15000000.0,
  "periodic_budget_inflow": 2000000.0,
  "perturbation": {
    "budget_multiplier": 1.2,
    "material_supply_factor": 0.7,
    "disaster_recurrence_shock": true,
    "shock_period": 4,
    "shock_damage_factor": 0.25,
    "sector_priorities": {
      "WASH": 1.5,
      "HEALTH": 1.3
    }
  }
}
```

#### Response Schema (`200 OK`)
```json
{
  "scenario_name": "Coastal Inundation Perturbation Analysis",
  "planning_horizon_periods": 12,
  "period_length_days": 30.0,
  "is_non_mutating": true,
  "baseline_completion_period": 6,
  "simulated_completion_period": 7,
  "baseline_final_recovery_score": 100.0,
  "simulated_final_recovery_score": 95.0,
  "recovery_score_delta": -5.0,
  "periods_to_target_80pct": 5,
  "total_budget_allocated": 46800000.0,
  "total_budget_utilized": 12800000.0,
  "unmet_budget_deficit": 0.0,
  "bottleneck_resources": [
    {
      "material_category": "STRUCTURAL_STEEL",
      "demand_quantity": 130.0,
      "available_supply": 91.0,
      "deficit_quantity": 39.0,
      "impact_level": "MODERATE"
    }
  ],
  "trajectory": [
    {
      "period": 1,
      "calendar_day": 30.0,
      "capital_spent_period": 2400000.0,
      "cumulative_capital_spent": 2400000.0,
      "remaining_cash_balance": 18000000.0,
      "projects_in_progress: 3,
      "projects_completed_cumulative": 0,
      "displaced_persons_remaining": 1200,
      "projected_recovery_score": 12.5,
      "unmet_needs_score": 87.5,
      "shock_occurred": false
    }
  ],
  "simulation_provenance": {
    "is_non_mutating": true,
    "candidate_count": 5,
    "source": "STANDARDIZED_PROTOTYPES"
  }
}
```
