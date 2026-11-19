"""
DIRS Phase 5G-D: Response Simulator
Executes what-if scenarios through the frozen Phase 5F-E integrated response pipeline
and computes mathematically rigorous response deltas against the base operational plan.
Classification: SYNTHETIC CALIBRATED SIMULATION / DECISION SUPPORT
"""
import copy
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from app.ai.optimization.orchestrator import (
    IntegratedResponseOrchestrator,
    IntegratedOptimizationResult,
    IncidentIntakeInput
)
from app.ai.simulation.scenario_engine import (
    DisasterScenario,
    OperationalStateSnapshot,
    ScenarioEngine
)
from app.ai.simulation.impact_propagation import (
    SpatialImpactPropagator,
    SpatialImpactReport
)


@dataclass
class ScenarioResponseDelta:
    """Calculated difference between base response plan and scenario response plan."""
    # Shelter Evacuation Deltas
    delta_evacuees_sheltered: int
    delta_unmet_evacuation: int
    base_evacuees_sheltered: int
    scenario_evacuees_sheltered: int
    base_unmet_evacuation: int
    scenario_unmet_evacuation: int

    # Multi-Commodity Resource Allocation Deltas
    delta_resource_allocated: float
    delta_unmet_resources: float
    base_resource_allocated: float
    scenario_resource_allocated: float
    base_unmet_resources: float
    scenario_unmet_resources: float

    # Vehicle Routing Deltas
    delta_vehicle_count: int
    delta_total_route_distance_km: float
    delta_total_response_time_min: float
    delta_unrouted_shipments: int
    base_vehicle_count: int
    scenario_vehicle_count: int
    base_total_route_distance_km: float
    scenario_total_route_distance_km: float
    base_total_response_time_min: float
    scenario_total_response_time_min: float
    base_unrouted_shipments: int
    scenario_unrouted_shipments: int

    # Volunteer Assignment Deltas
    delta_volunteers_deployed: int
    delta_unmet_volunteer_tasks: int
    delta_medical_unmet_tasks: int
    base_volunteers_deployed: int
    scenario_volunteers_deployed: int
    base_unmet_volunteer_tasks: int
    scenario_unmet_volunteer_tasks: int
    base_medical_unmet_tasks: int
    scenario_medical_unmet_tasks: int

    # Spatial Network Impacts
    new_unreachable_nodes: List[str]
    new_isolated_shelters: List[str]
    new_affected_depots: List[str]
    new_disrupted_routes: List[str]
    changed_volunteer_assignments_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shelter": {
                "delta_sheltered": self.delta_evacuees_sheltered,
                "delta_unmet": self.delta_unmet_evacuation,
                "base_sheltered": self.base_evacuees_sheltered,
                "scenario_sheltered": self.scenario_evacuees_sheltered,
                "base_unmet": self.base_unmet_evacuation,
                "scenario_unmet": self.scenario_unmet_evacuation
            },
            "resources": {
                "delta_allocated": self.delta_resource_allocated,
                "delta_unmet": self.delta_unmet_resources,
                "base_allocated": self.base_resource_allocated,
                "scenario_allocated": self.scenario_resource_allocated,
                "base_unmet": self.base_unmet_resources,
                "scenario_unmet": self.scenario_unmet_resources
            },
            "vehicles": {
                "delta_vehicles": self.delta_vehicle_count,
                "delta_distance_km": self.delta_total_route_distance_km,
                "delta_response_time_min": self.delta_total_response_time_min,
                "delta_unrouted": self.delta_unrouted_shipments,
                "base_vehicles": self.base_vehicle_count,
                "scenario_vehicles": self.scenario_vehicle_count,
                "base_distance_km": self.base_total_route_distance_km,
                "scenario_distance_km": self.scenario_total_route_distance_km,
                "base_response_time_min": self.base_total_response_time_min,
                "scenario_response_time_min": self.scenario_total_response_time_min,
                "base_unrouted": self.base_unrouted_shipments,
                "scenario_unrouted": self.scenario_unrouted_shipments
            },
            "volunteers": {
                "delta_deployed": self.delta_volunteers_deployed,
                "delta_unmet_tasks": self.delta_unmet_volunteer_tasks,
                "delta_medical_unmet": self.delta_medical_unmet_tasks,
                "base_deployed": self.base_volunteers_deployed,
                "scenario_deployed": self.scenario_volunteers_deployed,
                "base_unmet_tasks": self.base_unmet_volunteer_tasks,
                "scenario_unmet_tasks": self.scenario_unmet_volunteer_tasks,
                "base_medical_unmet": self.base_medical_unmet_tasks,
                "scenario_medical_unmet": self.scenario_medical_unmet_tasks
            },
            "network": {
                "new_unreachable_nodes": self.new_unreachable_nodes,
                "new_isolated_shelters": self.new_isolated_shelters,
                "new_affected_depots": self.new_affected_depots,
                "new_disrupted_routes": self.new_disrupted_routes,
                "changed_volunteer_assignments_count": self.changed_volunteer_assignments_count
            }
        }


@dataclass
class SimulationResult:
    """Complete output of an isolated disaster response simulation."""
    simulation_id: str
    scenario: DisasterScenario
    base_state_hash: str
    result_hash: str
    graph_version: str
    seed: int
    base_response: IntegratedOptimizationResult
    scenario_response: IntegratedOptimizationResult
    delta: ScenarioResponseDelta
    impact_report: SpatialImpactReport
    timing_breakdown: Dict[str, float]
    status: str = "PROPOSED"
    disclaimer: str = (
        "SIMULATED IMPACT: Prototype decision-support simulation. "
        "Live operational plan is strictly unmodified."
    )


class ResponseSimulator:
    """
    Coordinates isolated what-if simulation by executing the frozen Phase 5F-E pipeline
    and computing empirical response deltas.
    """

    def __init__(self, orchestrator: Optional[IntegratedResponseOrchestrator] = None):
        self.orchestrator = orchestrator or IntegratedResponseOrchestrator()

    def simulate_scenario(
        self,
        base_state: OperationalStateSnapshot,
        scenario: DisasterScenario,
        base_response: Optional[IntegratedOptimizationResult] = None,
        solver_time_limits: Optional[Dict[str, float]] = None
    ) -> SimulationResult:
        """
        Executes end-to-end what-if response simulation without mutating the base state.
        """
        t_sim_start = time.perf_counter()
        timing: Dict[str, float] = {}

        # 1. Base State Fingerprint
        base_hash = base_state.compute_state_hash()

        # 2. Evaluate Base Response if not provided
        t_base_start = time.perf_counter()
        if not base_response:
            # Normalize entities to DTOs — orchestrator expects IncidentIntakeInput, ShelterInput, etc.
            norm_incidents = ScenarioEngine._normalize_incidents(base_state.incidents)
            norm_shelters = ScenarioEngine._normalize_shelters(base_state.shelters)
            norm_depots = ScenarioEngine._normalize_depots(base_state.depots)
            norm_vehicles = ScenarioEngine._normalize_vehicles(base_state.vehicles)
            norm_volunteers = ScenarioEngine._normalize_volunteers(base_state.volunteers)
            base_response = self.orchestrator.run_pipeline(
                incidents=norm_incidents,
                shelters=norm_shelters,
                depots=norm_depots,
                vehicles=norm_vehicles,
                volunteers=norm_volunteers,
                graph_engine=base_state.graph_engine,
                solver_time_limits=solver_time_limits,
                random_seed=scenario.seed
            )

        timing["base_execution_ms"] = round((time.perf_counter() - t_base_start) * 1000.0, 2)

        # 3. Apply Scenario onto an ISOLATED deep clone
        t_scenario_prep = time.perf_counter()
        scenario_state = ScenarioEngine.apply_scenario(base_state, scenario)
        timing["scenario_construction_ms"] = round((time.perf_counter() - t_scenario_prep) * 1000.0, 2)

        # 4. Propagate Spatial Impact on scenario state
        t_impact_start = time.perf_counter()
        impact_report = SpatialImpactPropagator.propagate_impact(
            incidents=scenario_state.incidents,
            shelters=scenario_state.shelters,
            depots=scenario_state.depots,
            graph_engine=scenario_state.graph_engine,
            area_multiplier=scenario.affected_area_multiplier
        )
        timing["impact_propagation_ms"] = round((time.perf_counter() - t_impact_start) * 1000.0, 2)

        # 5. Execute frozen Phase 5F-E pipeline on the scenario state
        t_opt_start = time.perf_counter()
        scenario_response = self.orchestrator.run_pipeline(
            incidents=scenario_state.incidents,
            shelters=scenario_state.shelters,
            depots=scenario_state.depots,
            vehicles=scenario_state.vehicles,
            volunteers=scenario_state.volunteers,
            graph_engine=scenario_state.graph_engine,
            solver_time_limits=solver_time_limits,
            random_seed=scenario.seed
        )
        timing["scenario_optimization_ms"] = round((time.perf_counter() - t_opt_start) * 1000.0, 2)

        # 6. Compute Response Delta
        t_delta_start = time.perf_counter()
        delta = self.compute_response_delta(
            base=base_response,
            scenario=scenario_response,
            impact=impact_report,
            scenario_spec=scenario,
            base_state=base_state,
            scenario_state=scenario_state,
        )
        timing["delta_computation_ms"] = round((time.perf_counter() - t_delta_start) * 1000.0, 2)

        total_sim_ms = (time.perf_counter() - t_sim_start) * 1000.0
        timing["total_simulation_ms"] = round(total_sim_ms, 2)
        timing["gis_simulation_overhead_ms"] = round(
            total_sim_ms - timing["scenario_optimization_ms"], 2
        )

        # 7. Generate Result Hash
        sim_id = f"SIM_{uuid.uuid4().hex[:8]}"
        res_hash = self._compute_result_hash(delta, scenario_response.graph_version)

        return SimulationResult(
            simulation_id=sim_id,
            scenario=scenario,
            base_state_hash=base_hash,
            result_hash=res_hash,
            graph_version=scenario_response.graph_version,
            seed=scenario.seed,
            base_response=base_response,
            scenario_response=scenario_response,
            delta=delta,
            impact_report=impact_report,
            timing_breakdown=timing,
            status="PROPOSED"
        )

    @classmethod
    def compute_response_delta(
        cls,
        base: IntegratedOptimizationResult,
        scenario: IntegratedOptimizationResult,
        impact: SpatialImpactReport,
        scenario_spec: Optional[DisasterScenario] = None,
        base_state: Optional[OperationalStateSnapshot] = None,
        scenario_state: Optional[OperationalStateSnapshot] = None,
    ) -> ScenarioResponseDelta:
        """
        Calculates exact mathematical deltas between base and scenario outputs.
        All deltas are (Scenario - Base).
        """
        # Shelter metrics
        base_sheltered = base.shelter_result.total_evacuees_sheltered if base.shelter_result else 0
        scen_sheltered = scenario.shelter_result.total_evacuees_sheltered if scenario.shelter_result else 0
        base_unmet_evac = base.shelter_result.total_evacuees_unmet if base.shelter_result else 0
        scen_unmet_evac = scenario.shelter_result.total_evacuees_unmet if scenario.shelter_result else 0

        # Resource metrics
        base_alloc = round(sum(a.quantity for a in base.resource_result.allocations), 1) if base.resource_result else 0.0
        scen_alloc = round(sum(a.quantity for a in scenario.resource_result.allocations), 1) if scenario.resource_result else 0.0
        base_unmet_res = base.resource_result.total_unmet_demand_quantity if base.resource_result else 0.0
        scen_unmet_res = scenario.resource_result.total_unmet_demand_quantity if scenario.resource_result else 0.0

        # Vehicle metrics
        base_veh_count = len(base.routing_result.routes) if base.routing_result else 0
        scen_veh_count = len(scenario.routing_result.routes) if scenario.routing_result else 0
        base_dist = base.routing_result.total_distance_km if base.routing_result else 0.0
        scen_dist = scenario.routing_result.total_distance_km if scenario.routing_result else 0.0
        base_resp_time = base.routing_result.total_travel_time_min if base.routing_result else 0.0
        scen_resp_time = scenario.routing_result.total_travel_time_min if scenario.routing_result else 0.0
        base_unrouted = len(base.routing_result.unrouted_shipments) if base.routing_result else 0
        scen_unrouted = len(scenario.routing_result.unrouted_shipments) if scenario.routing_result else 0

        # Volunteer metrics
        base_vol_dep = base.volunteer_result.total_tasks_assigned if base.volunteer_result else 0
        scen_vol_dep = scenario.volunteer_result.total_tasks_assigned if scenario.volunteer_result else 0
        base_unmet_vol = base.volunteer_result.total_tasks_unmet if base.volunteer_result else 0
        scen_unmet_vol = scenario.volunteer_result.total_tasks_unmet if scenario.volunteer_result else 0

        base_med_unmet = 0
        scen_med_unmet = 0
        if base.volunteer_result:
            base_med_unmet = sum(u.unmet_quantity for u in base.volunteer_result.unmet_items if u.skill_category == "MEDICAL")
        if scenario.volunteer_result:
            scen_med_unmet = sum(u.unmet_quantity for u in scenario.volunteer_result.unmet_items if u.skill_category == "MEDICAL")

        # Disrupted routes check
        disrupted_routes = []
        if base.routing_result and scenario.routing_result:
            base_routes_by_veh = {r.vehicle_id: r for r in base.routing_result.routes}
            scen_routes_by_veh = {r.vehicle_id: r for r in scenario.routing_result.routes}

            has_blockages = False
            blocked_edge_set = set()
            disabled_vehicles = set()

            if scenario_spec:
                if scenario_spec.vehicle_availability_changes:
                    disabled_vehicles = set(scenario_spec.vehicle_availability_changes)
                if scenario_spec.additional_blockages:
                    has_blockages = True
                    for blk in scenario_spec.additional_blockages:
                        u = blk.get("u")
                        v = blk.get("v")
                        status = blk.get("status", "IMPASSABLE")
                        if status in ("IMPASSABLE", "BLOCKED"):
                            if u and v:
                                blocked_edge_set.add((u, v))
                                blocked_edge_set.add((v, u))
            elif base.graph_version != scenario.graph_version:
                has_blockages = True

            # If there are no blockages, no unreachable nodes, and no vehicle changes,
            # zero routes were disrupted by scenario blockages.
            if not has_blockages and not disabled_vehicles and not (impact and impact.unreachable_nodes):
                disrupted_routes = []
            else:
                depot_map = {}
                shelter_map = {}
                inc_map = {}
                if base_state:
                    depot_map = {
                        (d.get("id") if isinstance(d, dict) else getattr(d, "depot_id", "")): (
                            (d.get("lat", d.get("latitude")) if isinstance(d, dict) else getattr(d, "latitude")),
                            (d.get("lng", d.get("longitude")) if isinstance(d, dict) else getattr(d, "longitude"))
                        )
                        for d in base_state.depots
                    }
                    shelter_map = {
                        (s.get("id") if isinstance(s, dict) else getattr(s, "shelter_id", "")): (
                            (s.get("lat", s.get("latitude")) if isinstance(s, dict) else getattr(s, "latitude")),
                            (s.get("lng", s.get("longitude")) if isinstance(s, dict) else getattr(s, "longitude"))
                        )
                        for s in base_state.shelters
                    }
                    inc_map = {
                        (i.get("id") if isinstance(i, dict) else getattr(i, "incident_id", "")): (
                            (i.get("lat", i.get("latitude")) if isinstance(i, dict) else getattr(i, "latitude")),
                            (i.get("lng", i.get("longitude")) if isinstance(i, dict) else getattr(i, "longitude"))
                        )
                        for i in base_state.incidents
                    }

                unreachable_set = set(impact.unreachable_nodes) if impact else set()

                for r in base.routing_result.routes:
                    v_id = r.vehicle_id
                    if v_id in disabled_vehicles:
                        disrupted_routes.append(r.route_id)
                        continue

                    is_disrupted = False
                    if base_state and (blocked_edge_set or unreachable_set):
                        depot_coord = depot_map.get(r.start_depot_id)
                        if depot_coord and depot_coord[0] is not None and depot_coord[1] is not None:
                            curr_node = base_state.graph_engine.find_nearest_node(depot_coord[0], depot_coord[1])
                            for stop in r.stops:
                                inc_id = stop.incident_id
                                if inc_id.startswith("SHELTER_DEMAND_"):
                                    sh_id = inc_id.replace("SHELTER_DEMAND_", "")
                                    s_coord = shelter_map.get(sh_id)
                                    stop_node = base_state.graph_engine.find_nearest_node(s_coord[0], s_coord[1]) if s_coord else None
                                else:
                                    i_coord = inc_map.get(inc_id)
                                    stop_node = base_state.graph_engine.find_nearest_node(i_coord[0], i_coord[1]) if i_coord else None

                                if curr_node and stop_node:
                                    leg = base_state.graph_engine.compute_shortest_path(curr_node, stop_node)
                                    seq = leg.node_sequence
                                    for idx in range(len(seq) - 1):
                                        edge = (seq[idx], seq[idx + 1])
                                        if edge in blocked_edge_set or seq[idx] in unreachable_set or seq[idx + 1] in unreachable_set:
                                            is_disrupted = True
                                            break
                                    if is_disrupted:
                                        break
                                    curr_node = stop_node

                            if not is_disrupted and curr_node:
                                depot_node = base_state.graph_engine.find_nearest_node(depot_coord[0], depot_coord[1])
                                if depot_node:
                                    leg = base_state.graph_engine.compute_shortest_path(curr_node, depot_node)
                                    seq = leg.node_sequence
                                    for idx in range(len(seq) - 1):
                                        edge = (seq[idx], seq[idx + 1])
                                        if edge in blocked_edge_set or seq[idx] in unreachable_set or seq[idx + 1] in unreachable_set:
                                            is_disrupted = True
                                            break
                    elif v_id not in scen_routes_by_veh:
                        is_disrupted = True
                    else:
                        base_stops = [s.incident_id for s in r.stops]
                        scen_stops = [s.incident_id for s in scen_routes_by_veh[v_id].stops]
                        if base_stops != scen_stops:
                            is_disrupted = True

                    if is_disrupted:
                        disrupted_routes.append(r.route_id)

        # Changed volunteer assignments
        changed_volunteers = 0
        if base.volunteer_result and scenario.volunteer_result:
            base_assigns = {(a.volunteer_id, a.incident_id, a.shift_id) for a in base.volunteer_result.assignments}
            scen_assigns = {(a.volunteer_id, a.incident_id, a.shift_id) for a in scenario.volunteer_result.assignments}
            changed_volunteers = len(base_assigns.symmetric_difference(scen_assigns))

        return ScenarioResponseDelta(
            delta_evacuees_sheltered=scen_sheltered - base_sheltered,
            delta_unmet_evacuation=scen_unmet_evac - base_unmet_evac,
            base_evacuees_sheltered=base_sheltered,
            scenario_evacuees_sheltered=scen_sheltered,
            base_unmet_evacuation=base_unmet_evac,
            scenario_unmet_evacuation=scen_unmet_evac,

            delta_resource_allocated=round(scen_alloc - base_alloc, 1),
            delta_unmet_resources=round(scen_unmet_res - base_unmet_res, 1),
            base_resource_allocated=base_alloc,
            scenario_resource_allocated=scen_alloc,
            base_unmet_resources=base_unmet_res,
            scenario_unmet_resources=scen_unmet_res,

            delta_vehicle_count=scen_veh_count - base_veh_count,
            delta_total_route_distance_km=round(scen_dist - base_dist, 2),
            delta_total_response_time_min=round(scen_resp_time - base_resp_time, 2),
            delta_unrouted_shipments=scen_unrouted - base_unrouted,
            base_vehicle_count=base_veh_count,
            scenario_vehicle_count=scen_veh_count,
            base_total_route_distance_km=round(base_dist, 2),
            scenario_total_route_distance_km=round(scen_dist, 2),
            base_total_response_time_min=round(base_resp_time, 2),
            scenario_total_response_time_min=round(scen_resp_time, 2),
            base_unrouted_shipments=base_unrouted,
            scenario_unrouted_shipments=scen_unrouted,

            delta_volunteers_deployed=scen_vol_dep - base_vol_dep,
            delta_unmet_volunteer_tasks=scen_unmet_vol - base_unmet_vol,
            delta_medical_unmet_tasks=scen_med_unmet - base_med_unmet,
            base_volunteers_deployed=base_vol_dep,
            scenario_volunteers_deployed=scen_vol_dep,
            base_unmet_volunteer_tasks=base_unmet_vol,
            scenario_unmet_volunteer_tasks=scen_unmet_vol,
            base_medical_unmet_tasks=base_med_unmet,
            scenario_medical_unmet_tasks=scen_med_unmet,

            new_unreachable_nodes=impact.unreachable_nodes,
            new_isolated_shelters=impact.isolated_shelter_ids,
            new_affected_depots=impact.isolated_depot_ids,
            new_disrupted_routes=disrupted_routes,
            changed_volunteer_assignments_count=changed_volunteers
        )

    @staticmethod
    def _compute_result_hash(delta: ScenarioResponseDelta, graph_ver: str) -> str:
        """Computes a SHA-256 fingerprint of the simulation delta and graph state."""
        h = hashlib.sha256()
        h.update(f"{delta.delta_evacuees_sheltered}:{delta.delta_unmet_evacuation}".encode("utf-8"))
        h.update(f"{delta.delta_resource_allocated}:{delta.delta_unmet_resources}".encode("utf-8"))
        h.update(f"{delta.delta_vehicle_count}:{delta.delta_unrouted_shipments}".encode("utf-8"))
        h.update(f"{delta.delta_volunteers_deployed}:{delta.delta_unmet_volunteer_tasks}".encode("utf-8"))
        h.update(graph_ver.encode("utf-8"))
        return h.hexdigest()
