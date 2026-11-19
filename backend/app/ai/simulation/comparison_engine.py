"""
DIRS Phase 5G-E: Scenario Comparison & Response Intelligence Engine
Generates factual multi-scenario comparison tables, descriptive response intelligence,
and deterministic critical threshold alerts.
Classification: SYNTHETIC CALIBRATED SIMULATION / DECISION SUPPORT
"""
from typing import List, Dict, Any, Optional

from app.ai.simulation.response_simulator import SimulationResult, ScenarioResponseDelta, ResponseSimulator
from app.schemas.simulation import SimulationAlert, MultiScenarioCompareResponse, ScenarioComparisonItem



class ComparisonAndIntelligenceEngine:
    """
    Analyzes simulation deltas to extract factual, non-prescriptive intelligence observations
    and evaluate deterministic threshold alerts.
    """

    # Deterministic alert threshold parameters
    ALERT_THRESHOLDS = {
        "UNMET_EVACUATION_INCREASE": 0.0,      # Any increase in stranded evacuees
        "RESOURCE_SHORTFALL_INCREASE": 0.0,    # Any increase in unmet commodity demand
        "MEDICAL_TASK_SHORTFALL": 0.0,         # Any increase in unmet medical volunteer tasks
        "ROUTE_DISRUPTION": 0.0,               # Any unrouted shipments
        "SHELTER_UNREACHABILITY": 0.0,         # Any newly isolated shelters
        "FLEET_CAPACITY_PRESSURE": 2.0         # Requirement of >= 2 additional vehicles
    }

    @classmethod
    def generate_intelligence_observations(cls, delta: ScenarioResponseDelta) -> List[str]:
        """
        Produces factual, descriptive statements strictly tied to measured metrics.
        Never outputs unsupported political, prescriptive, or subjective judgments.
        """
        observations: List[str] = []

        # 1. Evacuation observations
        if delta.delta_unmet_evacuation > 0:
            pct_str = f" (+{(delta.delta_unmet_evacuation / max(1, delta.base_unmet_evacuation))*100:.1f}%)" if delta.base_unmet_evacuation > 0 else ""
            observations.append(
                f"Evacuation unmet demand increased by {delta.delta_unmet_evacuation} persons "
                f"(from {delta.base_unmet_evacuation} to {delta.scenario_unmet_evacuation}){pct_str}."
            )
        elif delta.delta_unmet_evacuation < 0:
            observations.append(
                f"Evacuation unmet demand decreased by {abs(delta.delta_unmet_evacuation)} persons."
            )
        else:
            observations.append("Evacuation unmet demand remained unchanged at "
                                f"{delta.base_unmet_evacuation} persons.")

        # 2. Resource allocation observations
        if delta.delta_unmet_resources > 0:
            observations.append(
                f"Unmet resource demand increased by {delta.delta_unmet_resources:.1f} units "
                f"(from {delta.base_unmet_resources:.1f} to {delta.scenario_unmet_resources:.1f})."
            )
        elif delta.delta_resource_allocated != 0:
            observations.append(
                f"Allocated commodity quantity shifted by {delta.delta_resource_allocated:+.1f} units."
            )

        # 3. Vehicle routing observations
        if delta.delta_unrouted_shipments > 0:
            observations.append(
                f"Unrouted shipments increased from {delta.base_unrouted_shipments} to {delta.scenario_unrouted_shipments}."
            )
        if delta.delta_vehicle_count != 0:
            observations.append(
                f"Vehicle requirement changed from {delta.base_vehicle_count} to {delta.scenario_vehicle_count} vehicles "
                f"({delta.delta_vehicle_count:+d} vehicles)."
            )
        if delta.delta_total_route_distance_km != 0:
            observations.append(
                f"Total vehicle route distance changed by {delta.delta_total_route_distance_km:+.2f} km."
            )

        # 4. Volunteer workforce observations
        if delta.delta_medical_unmet_tasks > 0:
            observations.append(
                f"Volunteer medical unmet demand increased by {delta.delta_medical_unmet_tasks} tasks "
                f"(from {delta.base_medical_unmet_tasks} to {delta.scenario_medical_unmet_tasks})."
            )
        if delta.delta_unmet_volunteer_tasks > 0 and delta.delta_unmet_volunteer_tasks != delta.delta_medical_unmet_tasks:
            observations.append(
                f"Total unmet volunteer task slots increased by {delta.delta_unmet_volunteer_tasks}."
            )

        # 5. Spatial isolation observations
        if delta.new_isolated_shelters:
            observations.append(
                f"{len(delta.new_isolated_shelters)} shelter(s) became unreachable due to road blockages: "
                f"{', '.join(delta.new_isolated_shelters)}."
            )
        if delta.new_disrupted_routes:
            observations.append(
                f"{len(delta.new_disrupted_routes)} delivery route(s) were disrupted by scenario constraints (vehicle loss or road network blockages)."
            )

        return observations

    @classmethod
    def evaluate_critical_threshold_alerts(cls, delta: ScenarioResponseDelta) -> List[SimulationAlert]:
        """
        Evaluates deterministic alert rules against base and scenario metrics.
        Returns structured alerts containing metric, baseline, scenario, delta, threshold, and source.
        """
        alerts: List[SimulationAlert] = []

        # Alert 1: Unmet evacuation surge
        if delta.delta_unmet_evacuation > cls.ALERT_THRESHOLDS["UNMET_EVACUATION_INCREASE"]:
            pct = (delta.delta_unmet_evacuation / max(1, delta.base_unmet_evacuation)) * 100.0 if delta.base_unmet_evacuation > 0 else 100.0
            alerts.append(SimulationAlert(
                condition="UNMET_EVACUATION_INCREASE",
                metric="unmet_evacuees_count",
                base_value=float(delta.base_unmet_evacuation),
                scenario_value=float(delta.scenario_unmet_evacuation),
                absolute_change=float(delta.delta_unmet_evacuation),
                percentage_change=round(pct, 1),
                threshold=cls.ALERT_THRESHOLDS["UNMET_EVACUATION_INCREASE"],
                source="Phase 5F-C Shelter Evacuation Module",
                explanation=f"Scenario resulted in {delta.delta_unmet_evacuation} additional unhoused evacuees."
            ))

        # Alert 2: Resource shortfall increase
        if delta.delta_unmet_resources > cls.ALERT_THRESHOLDS["RESOURCE_SHORTFALL_INCREASE"]:
            pct = (delta.delta_unmet_resources / max(1.0, delta.base_unmet_resources)) * 100.0 if delta.base_unmet_resources > 0 else 100.0
            alerts.append(SimulationAlert(
                condition="RESOURCE_SHORTFALL_INCREASE",
                metric="unmet_commodity_quantity",
                base_value=float(delta.base_unmet_resources),
                scenario_value=float(delta.scenario_unmet_resources),
                absolute_change=float(delta.delta_unmet_resources),
                percentage_change=round(pct, 1),
                threshold=cls.ALERT_THRESHOLDS["RESOURCE_SHORTFALL_INCREASE"],
                source="Phase 5D Resource Allocation Module",
                explanation=f"Scenario created {delta.delta_unmet_resources:.1f} units of additional unmet commodity demand."
            ))

        # Alert 3: Medical task shortfall
        if delta.delta_medical_unmet_tasks > cls.ALERT_THRESHOLDS["MEDICAL_TASK_SHORTFALL"]:
            pct = (delta.delta_medical_unmet_tasks / max(1, delta.base_medical_unmet_tasks)) * 100.0 if delta.base_medical_unmet_tasks > 0 else 100.0
            alerts.append(SimulationAlert(
                condition="MEDICAL_TASK_SHORTFALL",
                metric="unmet_medical_tasks_count",
                base_value=float(delta.base_medical_unmet_tasks),
                scenario_value=float(delta.scenario_medical_unmet_tasks),
                absolute_change=float(delta.delta_medical_unmet_tasks),
                percentage_change=round(pct, 1),
                threshold=cls.ALERT_THRESHOLDS["MEDICAL_TASK_SHORTFALL"],
                source="Phase 5F-D Volunteer Assignment Module",
                explanation=f"Medical volunteer shortfall increased by {delta.delta_medical_unmet_tasks} tasks."
            ))

        # Alert 4: Vehicle route disruption
        if delta.delta_unrouted_shipments > cls.ALERT_THRESHOLDS["ROUTE_DISRUPTION"]:
            alerts.append(SimulationAlert(
                condition="ROUTE_DISRUPTION",
                metric="unrouted_shipments_count",
                base_value=float(delta.base_unrouted_shipments),
                scenario_value=float(delta.scenario_unrouted_shipments),
                absolute_change=float(delta.delta_unrouted_shipments),
                percentage_change=100.0,
                threshold=cls.ALERT_THRESHOLDS["ROUTE_DISRUPTION"],
                source="Phase 5E Vehicle Routing Module",
                explanation=f"{delta.delta_unrouted_shipments} shipment delivery stop(s) became unroutable."
            ))

        # Alert 5: Shelter unreachability
        if len(delta.new_isolated_shelters) > int(cls.ALERT_THRESHOLDS["SHELTER_UNREACHABILITY"]):
            alerts.append(SimulationAlert(
                condition="SHELTER_UNREACHABILITY",
                metric="isolated_shelters_count",
                base_value=0.0,
                scenario_value=float(len(delta.new_isolated_shelters)),
                absolute_change=float(len(delta.new_isolated_shelters)),
                percentage_change=100.0,
                threshold=cls.ALERT_THRESHOLDS["SHELTER_UNREACHABILITY"],
                source="Phase 5C Road Graph Module",
                explanation=f"{len(delta.new_isolated_shelters)} shelter location(s) were severed from road network."
            ))

        # Alert 6: Fleet capacity pressure
        if delta.delta_vehicle_count >= cls.ALERT_THRESHOLDS["FLEET_CAPACITY_PRESSURE"]:
            alerts.append(SimulationAlert(
                condition="FLEET_CAPACITY_PRESSURE",
                metric="vehicle_fleet_size_increase",
                base_value=float(delta.base_vehicle_count),
                scenario_value=float(delta.scenario_vehicle_count),
                absolute_change=float(delta.delta_vehicle_count),
                percentage_change=round((delta.delta_vehicle_count / max(1, delta.base_vehicle_count)) * 100.0, 1),
                threshold=cls.ALERT_THRESHOLDS["FLEET_CAPACITY_PRESSURE"],
                source="Phase 5E Vehicle Routing Module",
                explanation=f"Required active vehicle fleet increased by {delta.delta_vehicle_count} vehicles."
            ))

        return alerts

    @classmethod
    def compare_multiple_scenarios(
        cls,
        base_result: SimulationResult,
        scenario_results: List[SimulationResult]
    ) -> Dict[str, Any]:
        """
        Produces a factual multi-scenario comparison table against the common base state.
        Does NOT score, rank, or recommend scenarios. Exposes metrics for government review.
        """
        table_rows = []
        all_observations = []

        for res in scenario_results:
            d = res.delta
            obs = cls.generate_intelligence_observations(d)
            alerts = cls.evaluate_critical_threshold_alerts(d)

            table_rows.append({
                "scenario_id": res.scenario.scenario_id,
                "scenario_name": res.scenario.name,
                "hazard_type": res.scenario.hazard_type,
                "delta_evacuees_sheltered": d.delta_evacuees_sheltered,
                "delta_unmet_evacuation": d.delta_unmet_evacuation,
                "delta_resource_allocated": d.delta_resource_allocated,
                "delta_unmet_resources": d.delta_unmet_resources,
                "delta_vehicle_count": d.delta_vehicle_count,
                "delta_total_route_distance_km": d.delta_total_route_distance_km,
                "delta_total_response_time_min": d.delta_total_response_time_min,
                "delta_unrouted_shipments": d.delta_unrouted_shipments,
                "delta_volunteers_deployed": d.delta_volunteers_deployed,
                "delta_unmet_volunteer_tasks": d.delta_unmet_volunteer_tasks,
                "delta_medical_unmet_tasks": d.delta_medical_unmet_tasks,
                "new_unreachable_locations_count": len(d.new_unreachable_nodes),
                "new_isolated_shelters_count": len(d.new_isolated_shelters),
                "critical_alerts_count": len(alerts)
            })

            for o in obs:
                all_observations.append(f"[{res.scenario.name}] {o}")

        return {
            "base_metrics": {
                "evacuees_sheltered": base_result.base_response.shelter_result.total_evacuees_sheltered if base_result.base_response.shelter_result else 0,
                "unmet_evacuation": base_result.base_response.shelter_result.total_evacuees_unmet if base_result.base_response.shelter_result else 0,
                "resource_allocated": round(sum(a.quantity for a in base_result.base_response.resource_result.allocations), 1) if base_result.base_response.resource_result else 0.0,
                "unmet_resources": base_result.base_response.resource_result.total_unmet_demand_quantity if base_result.base_response.resource_result else 0.0,
                "vehicles_used": len(base_result.base_response.routing_result.routes) if base_result.base_response.routing_result else 0,
                "unrouted_shipments": len(base_result.base_response.routing_result.unrouted_shipments) if base_result.base_response.routing_result else 0,
                "volunteers_deployed": base_result.base_response.volunteer_result.total_tasks_assigned if base_result.base_response.volunteer_result else 0,
                "unmet_volunteer_tasks": base_result.base_response.volunteer_result.total_tasks_unmet if base_result.base_response.volunteer_result else 0
            },
            "scenarios_comparison": table_rows,
            "intelligence_observations": all_observations
        }

    @classmethod
    def compare_scenarios(
        cls,
        base_workload: str,
        scenarios: List[Any],
        seed: int = 42
    ) -> MultiScenarioCompareResponse:
        """
        High-level entry point: loads the base state for the given workload, runs the
        ResponseSimulator on each DisasterScenario, and returns a structured
        MultiScenarioCompareResponse for the router and unit tests.
        """
        # Import here to avoid circular imports at module load time
        from app.ai.optimization.integrated_benchmark_dataset import (
            generate_dirs_integrated_10,
            generate_dirs_integrated_25,
            generate_dirs_integrated_50
        )
        from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph
        from app.ai.simulation.scenario_engine import OperationalStateSnapshot

        # Load base state
        if base_workload == "DIRS-GIS-25":
            incidents, shelters, depots, vehicles, volunteers = generate_dirs_integrated_25()
            graph = create_chennai_benchmark_graph(num_nodes=50, seed=seed)
        elif base_workload == "DIRS-GIS-50":
            incidents, shelters, depots, vehicles, volunteers = generate_dirs_integrated_50()
            graph = create_chennai_benchmark_graph(num_nodes=100, seed=seed)
        else:  # DIRS-GIS-10 (default)
            incidents, shelters, depots, vehicles, volunteers = generate_dirs_integrated_10()
            graph = create_chennai_benchmark_graph(num_nodes=50, seed=seed)

        base_state = OperationalStateSnapshot(
            incidents=incidents,
            shelters=shelters,
            depots=depots,
            vehicles=vehicles,
            volunteers=volunteers,
            graph_engine=graph
        )

        simulator = ResponseSimulator()

        # Run base simulation (no-op scenario) to get base metrics
        from app.ai.simulation.scenario_engine import DisasterScenario
        noop_scenario = DisasterScenario(scenario_id="NOOP_BASE", name="No-Op Base", seed=seed)
        base_result = simulator.simulate_scenario(base_state, noop_scenario)

        # Collect base metrics
        br = base_result.base_response
        base_metrics = {
            "evacuees_sheltered": br.shelter_result.total_evacuees_sheltered if br.shelter_result else 0,
            "unmet_evacuation": br.shelter_result.total_evacuees_unmet if br.shelter_result else 0,
            "resource_allocated": round(sum(a.quantity for a in br.resource_result.allocations), 1) if br.resource_result else 0.0,
            "unmet_resources": br.resource_result.total_unmet_demand_quantity if br.resource_result else 0.0,
            "vehicles_used": len(br.routing_result.routes) if br.routing_result else 0,
            "unrouted_shipments": len(br.routing_result.unrouted_shipments) if br.routing_result else 0,
            "volunteers_deployed": br.volunteer_result.total_tasks_assigned if br.volunteer_result else 0,
            "unmet_volunteer_tasks": br.volunteer_result.total_tasks_unmet if br.volunteer_result else 0
        }

        # Run each scenario and build comparison items
        comparison_items: List[ScenarioComparisonItem] = []
        all_observations: List[str] = []

        for scen in scenarios:
            sim_result = simulator.simulate_scenario(base_state, scen)
            d = sim_result.delta
            obs = cls.generate_intelligence_observations(d)
            alerts = cls.evaluate_critical_threshold_alerts(d)

            comparison_items.append(ScenarioComparisonItem(
                scenario_id=scen.scenario_id,
                scenario_name=scen.name,
                delta_evacuees_sheltered=d.delta_evacuees_sheltered,
                delta_unmet_evacuation=d.delta_unmet_evacuation,
                delta_resource_allocated=d.delta_resource_allocated,
                delta_unmet_resources=d.delta_unmet_resources,
                delta_vehicle_count=d.delta_vehicle_count,
                delta_total_route_distance_km=d.delta_total_route_distance_km,
                delta_total_response_time_min=d.delta_total_response_time_min,
                delta_unrouted_shipments=d.delta_unrouted_shipments,
                delta_volunteers_deployed=d.delta_volunteers_deployed,
                delta_unmet_volunteer_tasks=d.delta_unmet_volunteer_tasks,
                delta_medical_unmet_tasks=d.delta_medical_unmet_tasks,
                new_unreachable_locations_count=len(d.new_unreachable_nodes),
                new_isolated_shelters_count=len(d.new_isolated_shelters),
                critical_alerts_count=len(alerts)
            ))
            for o in obs:
                all_observations.append(f"[{scen.name}] {o}")

        return MultiScenarioCompareResponse(
            base_workload=base_workload,
            base_metrics=base_metrics,
            comparisons=comparison_items,
            factual_observations=all_observations
        )

