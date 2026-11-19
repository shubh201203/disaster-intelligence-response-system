"""
Phase 5G Authorized Forensic Remediation Regression Tests
Covers permanent elimination of:
  - BUG 1 (P1): Demographic scaling invariant violation (Largest Remainder Method)
  - BUG 2 (P2): Route disruption detection comparing ephemeral route UUIDs across independent runs
"""
import copy
import pytest
from app.ai.optimization.orchestrator import IntegratedResponseOrchestrator
from app.ai.simulation.scenario_engine import (
    DisasterScenario,
    ScenarioEngine,
    scale_demographics_proportionally,
    OperationalStateSnapshot
)
from app.ai.simulation.response_simulator import ResponseSimulator
from app.ai.simulation.impact_propagation import SpatialImpactPropagator
from app.routers.simulation import _load_base_state, _to_incident_input


# ==============================================================================
# BUG 1 (P1): Demographic Scaling Invariant Regression Tests
# ==============================================================================

def test_retest_bug1_largest_remainder_method_conservation():
    """Verify Largest Remainder Method maintains exact sum across diverse distributions."""
    test_cases = [
        ({"GEN": 60, "ACC": 17, "MED": 8, "MED_ACC": 0}, 85, 102),  # Gate 6I / 6K INC_INT_001
        ({"GEN": 130, "ACC": 34, "MED": 15, "MED_ACC": 0}, 179, 215),
        ({"GEN": 172, "ACC": 59, "MED": 26, "MED_ACC": 0}, 257, 309),
        ({"GEN": 80, "ACC": 15, "MED": 5, "MED_ACC": 0}, 100, 150),
        ({"GEN": 1, "ACC": 1, "MED": 1, "MED_ACC": 1}, 4, 7),
        ({"GEN": 0, "ACC": 0, "MED": 0, "MED_ACC": 0}, 0, 50),
        ({"GEN": 50, "ACC": 10, "MED": 5, "MED_ACC": 0}, 65, 0),    # Total zero
        ({"GEN": 50, "ACC": 10, "MED": 5, "MED_ACC": 0}, 65, 1),    # Single person
    ]

    for orig_demo, orig_p, new_p in test_cases:
        scaled = scale_demographics_proportionally(orig_demo, orig_p, new_p)
        assert sum(scaled.values()) == new_p, f"Failed for {orig_demo} -> {new_p}: sum {sum(scaled.values())} != {new_p}"
        assert all(v >= 0 for v in scaled.values()), f"Negative value in {scaled}"


def test_retest_bug1_gate_6i_monsoonal_inundation_reproduction():
    """
    Gate 6I Reproduction:
    severity_multiplier = 1.2 on DIRS-GIS-10.
    Prior to fix: Phase 5F-C crashed with demographic total > people_affected (103 > 102),
                 returning early in 0.12 ms with all zeroes.
    After fix: Solves completely with status PROPOSED and increased sheltering (1695 -> 2038).
    """
    base_state = _load_base_state("DIRS-GIS-10")
    scenario = DisasterScenario(
        scenario_id="GATE_6I_RETEST",
        name="High Intensity Monsoonal Inundation",
        severity_multiplier=1.2,
        affected_area_multiplier=1.0,
        seed=42
    )

    sim = ResponseSimulator()
    result = sim.simulate_scenario(base_state, scenario)

    assert result.status == "PROPOSED"
    assert result.scenario_response.overall_status == "PROPOSED"
    # Sheltered evacuees should scale up from base 1695 to 2038
    assert result.delta.base_evacuees_sheltered == 1695
    assert result.delta.scenario_evacuees_sheltered == 2038
    assert result.delta.delta_evacuees_sheltered == 343
    assert result.delta.delta_unmet_evacuation == 0
    # Route disruptions must be 0 since no blockages exist
    assert result.delta.new_disrupted_routes == []


def test_retest_bug1_various_multipliers_preserve_demographic_invariant():
    """Verify demographic conservation across multiple multiplier scales."""
    base_state = _load_base_state("DIRS-GIS-10")
    for mult in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
        scenario = DisasterScenario(
            scenario_id=f"SCALE_{int(mult*100)}",
            name="Scaling Test",
            severity_multiplier=mult,
            seed=42
        )
        scen_state = ScenarioEngine.apply_scenario(base_state, scenario)
        for inc in scen_state.incidents:
            demo_sum = sum(inc.evacuation_demographics.values())
            assert demo_sum == inc.people_affected, (
                f"Multiplier {mult}: demographic sum ({demo_sum}) != people_affected ({inc.people_affected}) "
                f"for incident {inc.incident_id}"
            )


def test_retest_bug1_injected_incidents_normalization():
    """Verify injected incidents with raw dictionary payloads are correctly normalized."""
    payload = {
        "incident_id": "NEW_INJECTED_001",
        "title": "Severe Flash Flood Inflow",
        "evacuees": 120,
        "vulnerable_count": 45,
        "injuries": 25,
        "severity": "CRITICAL"
    }
    incident_input = _to_incident_input(payload)
    assert incident_input.people_affected == 120
    demo = incident_input.evacuation_demographics
    assert sum(demo.values()) == 120
    assert demo["ACC"] + demo["MED"] + demo["GEN"] + demo["MED_ACC"] == 120
    assert all(v >= 0 for v in demo.values())


# ==============================================================================
# BUG 2 (P2): Route Disruption Detection Regression Tests
# ==============================================================================

def test_retest_bug2_zero_blockages_yields_zero_disrupted_routes():
    """
    Bug 2 Root Cause Elimination:
    Comparing ephemeral route UUIDs across runs falsely flagged all baseline routes as disrupted.
    Now, with zero road blockages, new_disrupted_routes MUST be strictly empty ([]).
    """
    base_state = _load_base_state("DIRS-GIS-10")
    scenario = DisasterScenario(
        scenario_id="ZERO_BLOCKAGE_RETEST",
        name="Zero Blockage Baseline Test",
        additional_blockages=[],
        seed=42
    )

    sim = ResponseSimulator()
    result = sim.simulate_scenario(base_state, scenario)
    assert result.delta.new_disrupted_routes == []


def test_retest_bug2_gate_6e_off_route_blockage():
    """
    Gate 6E Reproduction:
    Road closure at (NODE_0012, NODE_0020) in Velachery/Medavakkam is off-route
    relative to VEH_INT_002 and VEH_INT_006.
    new_disrupted_routes MUST be strictly empty ([]).
    """
    base_state = _load_base_state("DIRS-GIS-10")
    scenario = DisasterScenario(
        scenario_id="GATE_6E_RETEST",
        name="Off-Route Closure Retest",
        additional_blockages=[
            {"u": "NODE_0012", "v": "NODE_0020", "status": "IMPASSABLE"}
        ],
        seed=42
    )

    sim = ResponseSimulator()
    result = sim.simulate_scenario(base_state, scenario)
    assert result.delta.new_disrupted_routes == []


def test_retest_bug2_on_route_blockage_detected():
    """
    Directly block an edge traversed by VEH_INT_002 (NODE_0028, NODE_0029).
    VEH_INT_002's route MUST be flagged as disrupted in new_disrupted_routes.
    """
    base_state = _load_base_state("DIRS-GIS-10")
    scenario = DisasterScenario(
        scenario_id="ON_ROUTE_BLOCKAGE_RETEST",
        name="Direct Route Blockage",
        additional_blockages=[
            {"u": "NODE_0028", "v": "NODE_0029", "status": "IMPASSABLE"}
        ],
        seed=42
    )

    sim = ResponseSimulator()
    result = sim.simulate_scenario(base_state, scenario)
    assert len(result.delta.new_disrupted_routes) == 1
    # Verify the disrupted route corresponds to VEH_INT_002
    base_veh_002_route = next(r for r in result.base_response.routing_result.routes if r.vehicle_id == "VEH_INT_002")
    assert result.delta.new_disrupted_routes[0] == base_veh_002_route.route_id


def test_retest_bug2_disabled_vehicle_detected():
    """
    Disabling an active vehicle (VEH_INT_002) in vehicle_availability_changes
    MUST flag its route in new_disrupted_routes.
    """
    base_state = _load_base_state("DIRS-GIS-10")
    scenario = DisasterScenario(
        scenario_id="DISABLED_VEH_RETEST",
        name="Active Vehicle Disabled",
        vehicle_availability_changes=["VEH_INT_002"],
        seed=42
    )

    sim = ResponseSimulator()
    result = sim.simulate_scenario(base_state, scenario)
    assert len(result.delta.new_disrupted_routes) == 1
    base_veh_002_route = next(r for r in result.base_response.routing_result.routes if r.vehicle_id == "VEH_INT_002")
    assert result.delta.new_disrupted_routes[0] == base_veh_002_route.route_id


def test_retest_bug2_inactive_vehicle_disabled_yields_zero_disruptions():
    """
    Finding 3 / 4 Confirmation:
    Disabling VEH_INT_001 (which is already unassigned / idle in DIRS-10 base state)
    must NOT flag any disrupted routes.
    """
    base_state = _load_base_state("DIRS-GIS-10")
    scenario = DisasterScenario(
        scenario_id="INACTIVE_VEH_RETEST",
        name="Inactive Vehicle Disabled",
        vehicle_availability_changes=["VEH_INT_001"],
        seed=42
    )

    sim = ResponseSimulator()
    result = sim.simulate_scenario(base_state, scenario)
    assert result.delta.new_disrupted_routes == []


def test_retest_claim_hygiene_observation_wording():
    """
    Claim-Hygiene Verification:
    Verify that disrupted route intelligence observations accurately generalize to scenario constraints
    (vehicle loss or road network blockages), rather than claiming every disruption is caused by blockages.
    """
    from app.ai.simulation.comparison_engine import ComparisonAndIntelligenceEngine

    base_state = _load_base_state("DIRS-GIS-10")
    scenario = DisasterScenario(
        scenario_id="CLAIM_HYGIENE_RETEST",
        name="Vehicle Loss Only",
        vehicle_availability_changes=["VEH_INT_002"],
        seed=42
    )

    sim = ResponseSimulator()
    result = sim.simulate_scenario(base_state, scenario)
    assert len(result.delta.new_disrupted_routes) == 1

    observations = ComparisonAndIntelligenceEngine.generate_intelligence_observations(result.delta)
    disruption_obs = [obs for obs in observations if "delivery route(s) were disrupted" in obs]
    assert len(disruption_obs) == 1
    # Must NOT claim disruption is solely caused by scenario blockages
    assert "disrupted by scenario blockages" not in disruption_obs[0]
    # Must state scenario constraints (vehicle loss or road network blockages)
    assert disruption_obs[0] == "1 delivery route(s) were disrupted by scenario constraints (vehicle loss or road network blockages)."
