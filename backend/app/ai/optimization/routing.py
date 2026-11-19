"""
DIRS Phase 5E - Vehicle Routing and Dynamic Emergency Dispatch Optimization Engine
Algorithm: Google OR-Tools RoutingModel (pywrapcp.RoutingModel / Routing Library)
OR-Tools Version: 9.15.6755

Classification: DECISION-SUPPORT ROUTING SYSTEM
Data label: SYNTHETIC CALIBRATED ROUTING BENCHMARK
Deployment assumption: Government HITL approval required before any operational use.

Architecture:
    Phase 5D AllocationResult (approved shipments)
        -> Phase 5C RoadGraphEngine (travel-time matrix + blockage semantics)
        -> VehicleRoutingEngine (OR-Tools RoutingModel)
            |-- IMPASSABLE arcs -> HARD-FORBIDDEN (routing.solver().Add(NextVar(i) != j))
            |-- capacity dimension: weight_kg + volume_m3 (two-dimensional)
            |-- time dimension: travel + service time, soft time windows
            |-- depot compatibility: SetAllowedVehiclesForIndex per delivery task
            |-- vehicle return policy: Option A - return to starting depot
            `-- multi-objective: beta_1*late + beta_2*time + beta_3*dist + beta_4*vehicles
        -> RoutingResult (routes + unrouted shipments + metrics)

Phase 5D Conservation Invariant:
    For every (incident x commodity):
        Phase 5D allocated_qty == routed_qty + unrouted_qty
"""

import math
import time
import uuid
import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from itertools import permutations

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from app.ai.optimization.graph import RoadGraphEngine, haversine_distance
from app.ai.optimization.allocation import CommodityAllocationItem, AllocationResult


# -- COMMODITY PHYSICAL CONVERSION TABLE --
# Classification: SYNTHETIC-CALIBRATED
# Source: Not from real vehicle manifests or humanitarian logistics databases.
# Reference standard applied: SPHERE Handbook physical packaging estimates.
COMMODITY_WEIGHT_KG_PER_UNIT: Dict[str, float] = {
    "WATER":                       1.000,   # kg per litre
    "FOOD":                        0.500,   # kg per unit-pack
    "MEDICAL_KITS":                2.000,   # kg per kit
    "RESCUE_EQUIPMENT":           10.000,   # kg per unit
    "SANITATION_KITS":             1.500,   # kg per kit
    "TEMPORARY_SHELTER_SUPPLIES":  5.000,   # kg per unit
}
COMMODITY_VOLUME_M3_PER_UNIT: Dict[str, float] = {
    "WATER":                       0.0010,  # m3 per litre
    "FOOD":                        0.0008,  # m3 per unit-pack
    "MEDICAL_KITS":                0.0050,  # m3 per kit
    "RESCUE_EQUIPMENT":            0.0500,  # m3 per unit
    "SANITATION_KITS":             0.0030,  # m3 per kit
    "TEMPORARY_SHELTER_SUPPLIES":  0.0200,  # m3 per unit
}

# -- ROUTING CONSTANTS --
DEFAULT_SERVICE_TIME_MIN: float = 15.0   # SYNTHETIC-CALIBRATED unloading time
DEFAULT_TIME_WINDOW_OPEN_MIN: float = 0.0
DEFAULT_TIME_WINDOW_CLOSE_MIN: float = 480.0  # 8-hour operational window

ROUTE_SCALE: int = 100          # Float-to-integer scaling for OR-Tools arithmetic
CRITICAL_MULTIPLIER: int = 3    # CRITICAL incidents receive 3x late/response penalty

# Routing objective beta-weights
DEFAULT_ROUTE_WEIGHTS: Dict[str, int] = {
    "beta_1": 1000,   # per-minute late-arrival penalty
    "beta_2": 10,     # per-minute response-time penalty
    "beta_3": 1,      # per-km distance penalty
    "beta_4": 100,    # fixed vehicle activation cost
}

# -- DATA STRUCTURES --

@dataclass
class VehicleInput:
    """Represents one AVAILABLE vehicle eligible for routing assignment."""
    vehicle_id: str
    vehicle_code: str
    vehicle_type: str          # TRUCK, AMBULANCE, VAN, BOAT, HELICOPTER
    capacity_weight_kg: float
    capacity_volume_m3: float
    depot_id: str
    depot_lat: float
    depot_lng: float
    status: str = "AVAILABLE"


@dataclass
class ShipmentInput:
    """One delivery task: all Phase 5D commodities from ONE depot to ONE incident."""
    shipment_id: str
    origin_depot_id: str
    origin_depot_lat: float
    origin_depot_lng: float
    incident_id: str
    incident_lat: float
    incident_lng: float
    incident_title: str
    priority_score: float
    severity_level: str          # CRITICAL, HIGH, MEDIUM, LOW
    commodities: Dict[str, float]  # {commodity: quantity} - Phase 5D allocated values
    total_weight_kg: float         # Derived via COMMODITY_WEIGHT_KG_PER_UNIT
    total_volume_m3: float         # Derived via COMMODITY_VOLUME_M3_PER_UNIT
    earliest_arrival_min: float = DEFAULT_TIME_WINDOW_OPEN_MIN
    latest_arrival_min: float = DEFAULT_TIME_WINDOW_CLOSE_MIN
    service_time_min: float = DEFAULT_SERVICE_TIME_MIN


@dataclass
class RouteStop:
    """One incident stop within a vehicle route."""
    stop_index: int
    incident_id: str
    incident_title: str
    shipment_id: str
    arrival_time_min: float     # Measured from route start time (T=0)
    service_start_min: float
    service_end_min: float
    departure_time_min: float
    commodities: Dict[str, float]  # Delivered at this stop
    lateness_min: float            # max(0, arrival_time - latest_arrival_min)
    priority_score: float
    severity_level: str
    latest_arrival_min: float


@dataclass
class VehicleRoute:
    """Complete route record for one vehicle."""
    route_id: str
    vehicle_id: str
    vehicle_code: str
    vehicle_type: str
    start_depot_id: str
    stops: List[RouteStop]
    total_distance_km: float
    total_travel_time_min: float
    total_service_time_min: float
    total_route_duration_min: float
    weight_used_kg: float
    volume_used_m3: float
    capacity_weight_kg: float
    capacity_volume_m3: float
    weight_utilization_pct: float
    volume_utilization_pct: float
    served_shipment_ids: List[str]
    explanation: str
    graph_version: str


@dataclass
class UnroutedShipment:
    """Explicit record of a Phase 5D shipment that could not be routed."""
    shipment_id: str
    origin_depot_id: str
    incident_id: str
    incident_title: str
    commodities: Dict[str, float]
    total_weight_kg: float
    total_volume_m3: float
    reason: str  # Human-readable explanation


@dataclass
class RoutingResult:
    """Complete output of the Phase 5E routing engine."""
    routing_run_id: str
    solver_status: str       # OPTIMAL | FEASIBLE | TIME_LIMIT | INFEASIBLE
    operational_status: str  # FULLY_FEASIBLE | PARTIALLY_FEASIBLE | UNROUTABLE
    routes: List[VehicleRoute]
    unrouted_shipments: List[UnroutedShipment]
    # Aggregate metrics
    total_distance_km: float
    total_travel_time_min: float
    total_service_time_min: float
    mean_response_time_min: float          # Mean arrival time across all routed stops
    critical_mean_response_time_min: float  # Mean arrival time for CRITICAL stops only
    sla_compliance_pct: float              # % of stops arriving within latest_arrival_min
    total_late_minutes: float              # Sum of lateness_min across all stops
    vehicle_utilization_pct: float        # vehicles_used / vehicles_available * 100
    mean_weight_utilization_pct: float
    mean_volume_utilization_pct: float
    unrouted_shipment_count: int
    unrouted_shipment_pct: float          # unrouted_qty / total_allocated_qty * 100
    objective_value: float
    solver_runtime_ms: float
    graph_version: str
    algorithm: str
    timing_breakdown: Dict[str, float] = field(default_factory=dict)


# -- HELPER: PHASE 5D ALLOCATION -> SHIPMENT INPUTS --

def convert_allocations_to_shipments(
    allocation_result: AllocationResult,
    depot_info: Dict[str, Tuple[float, float]],        # depot_id -> (lat, lng)
    incident_info: Dict[str, Tuple[float, float, str, float, str]],  # id -> (lat, lng, title, p_score, severity)
    time_windows: Optional[Dict[str, Tuple[float, float]]] = None,   # incident_id -> (earliest, latest)
    service_times: Optional[Dict[str, float]] = None,                # incident_id -> service_min
) -> List[ShipmentInput]:
    """
    Converts Phase 5D AllocationResult into ShipmentInput list.
    Groups CommodityAllocationItems by (origin_depot_id, incident_id) ->
    one ShipmentInput per group (ONE physical stop per depot-incident pair).
    """
    grouped: Dict[Tuple[str, str], List[CommodityAllocationItem]] = {}
    for alloc in allocation_result.allocations:
        key = (alloc.depot_id, alloc.incident_id)
        grouped.setdefault(key, []).append(alloc)

    shipments: List[ShipmentInput] = []
    for (depot_id, incident_id), items in sorted(grouped.items()):
        dep_lat, dep_lng = depot_info.get(depot_id, (13.0, 80.0))
        inc_lat, inc_lng, inc_title, p_score, severity = incident_info.get(
            incident_id, (13.0, 80.1, incident_id, 50.0, "MEDIUM")
        )

        commodities = {}
        total_w = 0.0
        total_v = 0.0
        for item in items:
            commodities[item.commodity] = commodities.get(item.commodity, 0.0) + item.quantity
            w = COMMODITY_WEIGHT_KG_PER_UNIT.get(item.commodity, 1.0) * item.quantity
            v = COMMODITY_VOLUME_M3_PER_UNIT.get(item.commodity, 0.001) * item.quantity
            total_w += w
            total_v += v

        tw = time_windows.get(incident_id, (DEFAULT_TIME_WINDOW_OPEN_MIN, DEFAULT_TIME_WINDOW_CLOSE_MIN)) if time_windows else (DEFAULT_TIME_WINDOW_OPEN_MIN, DEFAULT_TIME_WINDOW_CLOSE_MIN)
        svc = service_times.get(incident_id, DEFAULT_SERVICE_TIME_MIN) if service_times else DEFAULT_SERVICE_TIME_MIN

        shipments.append(ShipmentInput(
            shipment_id=f"SHP_{depot_id}_{incident_id}",
            origin_depot_id=depot_id,
            origin_depot_lat=dep_lat,
            origin_depot_lng=dep_lng,
            incident_id=incident_id,
            incident_lat=inc_lat,
            incident_lng=inc_lng,
            incident_title=inc_title,
            priority_score=p_score,
            severity_level=severity,
            commodities=commodities,
            total_weight_kg=total_w,
            total_volume_m3=total_v,
            earliest_arrival_min=tw[0],
            latest_arrival_min=tw[1],
            service_time_min=svc,
        ))

    return shipments


# -- ROUTING MATRIX BUILDER --

def _build_routing_matrix(
    graph_engine: RoadGraphEngine,
    node_coords: List[Tuple[float, float]],   # list of (lat, lng) for each node index
    node_labels: List[str],                   # parallel list of location IDs
) -> Tuple[List[List[int]], List[List[int]], List[List[bool]]]:
    """
    Builds integer time-cost and distance matrices and an IMPASSABLE reachability mask for OR-Tools.

    IMPASSABLE arc strategy:
        Phase 5C graph status IMPASSABLE -> reachable=False in this mask.
        The VehicleRoutingEngine adds HARD-FORBIDDEN arc constraints for each such pair
        via routing.solver().Add(routing.NextVar(i) != j).
        The transit callback returns 999999 as belt-and-suspenders.

    Returns:
        time_matrix: List[List[int]] - travel time in minutes x ROUTE_SCALE
        dist_matrix: List[List[int]] - distance in km x ROUTE_SCALE
        reachable:   List[List[bool]] - True iff path is FEASIBLE
    """
    n = len(node_coords)
    time_matrix: List[List[int]] = []
    dist_matrix: List[List[int]] = []
    reachable: List[List[bool]] = []

    graph_node_map: Dict[int, Optional[str]] = {}
    for idx, (lat, lng) in enumerate(node_coords):
        graph_node_map[idx] = graph_engine.find_nearest_node(lat, lng)

    route_cache: Dict[Tuple[str, str], Tuple[bool, float, float]] = {}

    for i in range(n):
        t_row: List[int] = []
        d_row: List[int] = []
        r_row: List[bool] = []

        orig_node = graph_node_map[i]
        for j in range(n):
            if i == j:
                t_row.append(0)
                d_row.append(0)
                r_row.append(True)
                continue

            dest_node = graph_node_map[j]
            if orig_node is None or dest_node is None:
                t_row.append(ROUTE_SCALE * 99999)
                d_row.append(ROUTE_SCALE * 99999)
                r_row.append(False)
                continue

            cache_key = (orig_node, dest_node)
            if cache_key not in route_cache:
                route = graph_engine.compute_shortest_path(orig_node, dest_node)
                if route.status == "FEASIBLE":
                    route_cache[cache_key] = (True, route.travel_time_minutes, route.distance_km)
                else:
                    route_cache[cache_key] = (False, 999999.0, 999999.0)

            is_r, t_val, d_val = route_cache[cache_key]
            if is_r:
                t_row.append(int(math.ceil(t_val * ROUTE_SCALE)))
                d_row.append(int(math.ceil(d_val * ROUTE_SCALE)))
                r_row.append(True)
            else:
                t_row.append(ROUTE_SCALE * 99999)
                d_row.append(ROUTE_SCALE * 99999)
                r_row.append(False)

        time_matrix.append(t_row)
        dist_matrix.append(d_row)
        reachable.append(r_row)

    return time_matrix, dist_matrix, reachable


# -- PRIMARY ENGINE: OR-TOOLS ROUTINGMODEL --

class VehicleRoutingEngine:
    """
    Phase 5E Vehicle Routing Optimization using Google OR-Tools RoutingModel.
    """

    def __init__(self, weights: Optional[Dict[str, int]] = None):
        self.weights = weights or dict(DEFAULT_ROUTE_WEIGHTS)

    def solve(
        self,
        shipments: List[ShipmentInput],
        vehicles: List[VehicleInput],
        graph_engine: RoadGraphEngine,
        solver_time_limit_sec: float = 10.0,
    ) -> RoutingResult:
        t_total_start = time.perf_counter()
        run_id = str(uuid.uuid4())
        graph_version = graph_engine.get_graph_version()

        eligible_vehicles = [v for v in vehicles if v.status == "AVAILABLE"]

        if not shipments or not eligible_vehicles:
            return self._empty_result(run_id, shipments, graph_version, t_total_start,
                                      "No shipments or no eligible vehicles.")

        t_matrix_start = time.perf_counter()

        depot_ids_ordered: List[str] = []
        depot_id_to_idx: Dict[str, int] = {}
        for v in eligible_vehicles:
            if v.depot_id not in depot_id_to_idx:
                depot_id_to_idx[v.depot_id] = len(depot_ids_ordered)
                depot_ids_ordered.append(v.depot_id)

        node_coords: List[Tuple[float, float]] = []
        node_labels: List[str] = []

        depot_coords: Dict[str, Tuple[float, float]] = {}
        for v in eligible_vehicles:
            if v.depot_id not in depot_coords:
                depot_coords[v.depot_id] = (v.depot_lat, v.depot_lng)
        for d_id in depot_ids_ordered:
            node_coords.append(depot_coords[d_id])
            node_labels.append(f"DEPOT:{d_id}")

        task_node_idx: Dict[str, int] = {}
        for ship in shipments:
            idx = len(node_coords)
            node_coords.append((ship.incident_lat, ship.incident_lng))
            node_labels.append(f"INCIDENT:{ship.incident_id}@{ship.origin_depot_id}")
            task_node_idx[ship.shipment_id] = idx

        num_nodes = len(node_coords)

        time_matrix, dist_matrix, reachable = _build_routing_matrix(
            graph_engine, node_coords, node_labels
        )
        t_matrix_end = time.perf_counter()

        vehicle_starts = [depot_id_to_idx[v.depot_id] for v in eligible_vehicles]
        vehicle_ends = vehicle_starts[:]  # Option A: return to starting depot

        t_model_start = time.perf_counter()
        num_vehicles = len(eligible_vehicles)
        manager = pywrapcp.RoutingIndexManager(num_nodes, num_vehicles, vehicle_starts, vehicle_ends)
        routing = pywrapcp.RoutingModel(manager)

        def time_callback(from_idx: int, to_idx: int) -> int:
            from_node = manager.IndexToNode(from_idx)
            to_node = manager.IndexToNode(to_idx)
            return time_matrix[from_node][to_node]

        transit_callback_idx = routing.RegisterTransitCallback(time_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_idx)

        def dist_callback(from_idx: int, to_idx: int) -> int:
            from_node = manager.IndexToNode(from_idx)
            to_node = manager.IndexToNode(to_idx)
            return dist_matrix[from_node][to_node]

        dist_callback_idx = routing.RegisterTransitCallback(dist_callback)

        # HARD-FORBIDDEN ARC CONSTRAINTS (IMPASSABLE)
        # Phase 5C IMPASSABLE semantics: edge CANNOT be traversed.
        # Enforced via routing.solver().Add(NextVar(i) != j).
        cp_solver = routing.solver()
        forbidden_arcs = []
        for from_node in range(num_nodes):
            for to_node in range(num_nodes):
                if from_node == to_node:
                    continue
                if not reachable[from_node][to_node]:
                    from_idx = manager.NodeToIndex(from_node)
                    to_idx = manager.NodeToIndex(to_node)
                    if from_idx >= 0 and to_idx >= 0:
                        cp_solver.Add(routing.NextVar(from_idx) != to_idx)
                        forbidden_arcs.append((from_node, to_node))

        # Weight capacity dimension
        weight_cap_scaled = [int(v.capacity_weight_kg * ROUTE_SCALE) for v in eligible_vehicles]
        weight_demands: List[int] = [0] * num_nodes
        for ship in shipments:
            node_idx = task_node_idx[ship.shipment_id]
            weight_demands[node_idx] = int(math.ceil(ship.total_weight_kg * ROUTE_SCALE))

        def weight_demand_callback(from_idx: int) -> int:
            node = manager.IndexToNode(from_idx)
            return weight_demands[node]

        weight_cb_idx = routing.RegisterUnaryTransitCallback(weight_demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            weight_cb_idx, 0, weight_cap_scaled, True, "Weight"
        )

        # Volume capacity dimension
        volume_cap_scaled = [int(v.capacity_volume_m3 * ROUTE_SCALE * 1000) for v in eligible_vehicles]
        volume_demands: List[int] = [0] * num_nodes
        for ship in shipments:
            node_idx = task_node_idx[ship.shipment_id]
            volume_demands[node_idx] = int(math.ceil(ship.total_volume_m3 * ROUTE_SCALE * 1000))

        def volume_demand_callback(from_idx: int) -> int:
            node = manager.IndexToNode(from_idx)
            return volume_demands[node]

        volume_cb_idx = routing.RegisterUnaryTransitCallback(volume_demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            volume_cb_idx, 0, volume_cap_scaled, True, "Volume"
        )

        # Time dimension (travel + service time)
        service_time_scaled: List[int] = [0] * num_nodes
        for ship in shipments:
            node_idx = task_node_idx[ship.shipment_id]
            service_time_scaled[node_idx] = int(math.ceil(ship.service_time_min * ROUTE_SCALE))

        def time_with_service_callback(from_idx: int, to_idx: int) -> int:
            from_node = manager.IndexToNode(from_idx)
            to_node = manager.IndexToNode(to_idx)
            travel = time_matrix[from_node][to_node]
            service = service_time_scaled[from_node]
            return travel + service

        time_service_cb_idx = routing.RegisterTransitCallback(time_with_service_callback)
        max_time_horizon = int(DEFAULT_TIME_WINDOW_CLOSE_MIN * 2 * ROUTE_SCALE)
        routing.AddDimension(
            time_service_cb_idx,
            int(DEFAULT_TIME_WINDOW_CLOSE_MIN * ROUTE_SCALE),
            max_time_horizon,
            False,
            "Time"
        )
        time_dim = routing.GetDimensionOrDie("Time")

        # Allow dropping shipments via AddDisjunction with large unrouted penalty
        # Priority-weighted drop penalty: CRITICAL gets 3x penalty
        for ship in shipments:
            node_idx = task_node_idx[ship.shipment_id]
            or_idx = manager.NodeToIndex(node_idx)
            priority_mult = CRITICAL_MULTIPLIER if ship.severity_level == "CRITICAL" else 1
            drop_penalty = int(100_000 * ROUTE_SCALE * priority_mult)
            routing.AddDisjunction([or_idx], drop_penalty)

            earliest_s = int(ship.earliest_arrival_min * ROUTE_SCALE)
            latest_s = int(ship.latest_arrival_min * ROUTE_SCALE)
            time_dim.CumulVar(or_idx).SetMin(earliest_s)
            late_penalty = self.weights["beta_1"] * priority_mult
            time_dim.SetCumulVarSoftUpperBound(or_idx, latest_s, late_penalty)

            # Depot compatibility: only vehicles with matching depot can serve this shipment
            allowed = [
                v_idx for v_idx, v in enumerate(eligible_vehicles)
                if v.depot_id == ship.origin_depot_id
            ]
            veh_var = routing.VehicleVar(or_idx)
            if allowed:
                # Node can be performed by any allowed vehicle, or unperformed (-1)
                cp_solver.Add(veh_var.Member([-1] + allowed))
            else:
                # No compatible vehicle exists at origin depot - must remain unperformed
                cp_solver.Add(veh_var == -1)

        # Multi-objective parameters
        time_dim.SetSpanCostCoefficientForAllVehicles(self.weights["beta_2"])

        for v_idx in range(num_vehicles):
            routing.SetFixedCostOfVehicle(self.weights["beta_4"] * ROUTE_SCALE, v_idx)

        dist_dim_name = "Distance"
        routing.AddDimension(dist_callback_idx, 0, 10_000_000, True, dist_dim_name)
        dist_dim = routing.GetDimensionOrDie(dist_dim_name)
        dist_dim.SetGlobalSpanCostCoefficient(self.weights["beta_3"])

        t_model_end = time.perf_counter()

        t_solve_start = time.perf_counter()
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_params.time_limit.seconds = int(solver_time_limit_sec)
        search_params.solution_limit = 100

        solution = routing.SolveWithParameters(search_params)
        t_solve_end = time.perf_counter()

        t_extract_start = time.perf_counter()

        status_val = routing.status()
        RSS = routing_enums_pb2.RoutingSearchStatus
        if status_val == RSS.ROUTING_OPTIMAL:
            solver_status = "OPTIMAL"
        elif status_val == RSS.ROUTING_SUCCESS:
            solver_status = "FEASIBLE"
        elif status_val in (RSS.ROUTING_PARTIAL_SUCCESS_LOCAL_OPTIMUM_NOT_REACHED, RSS.ROUTING_FAIL_TIMEOUT):
            solver_status = "TIME_LIMIT"
        else:
            solver_status = "INFEASIBLE"

        if solution is None or status_val in (RSS.ROUTING_INFEASIBLE, RSS.ROUTING_NOT_SOLVED, RSS.ROUTING_FAIL, RSS.ROUTING_INVALID):
            unrouted = [
                UnroutedShipment(
                    shipment_id=s.shipment_id,
                    origin_depot_id=s.origin_depot_id,
                    incident_id=s.incident_id,
                    incident_title=s.incident_title,
                    commodities=dict(s.commodities),
                    total_weight_kg=s.total_weight_kg,
                    total_volume_m3=s.total_volume_m3,
                    reason="OR-Tools RoutingModel returned INFEASIBLE: no feasible route assignment exists."
                )
                for s in shipments
            ]
            return self._build_result(
                run_id, "INFEASIBLE", "UNROUTABLE", [], unrouted,
                shipments, eligible_vehicles, graph_version, "OR-Tools RoutingModel",
                t_total_start, t_matrix_start, t_matrix_end, t_model_start, t_model_end,
                t_solve_start, t_solve_end, time.perf_counter(), time.perf_counter()
            )

        routes: List[VehicleRoute] = []
        served_shipment_ids: set = set()

        for v_idx in range(num_vehicles):
            vehicle = eligible_vehicles[v_idx]
            index = routing.Start(v_idx)
            if routing.IsEnd(solution.Value(routing.NextVar(index))):
                continue  # Vehicle unused

            stops: List[RouteStop] = []
            stop_count = 0
            total_dist_v = 0.0
            total_travel_v = 0.0
            total_service_v = 0.0
            weight_used = 0.0
            volume_used = 0.0
            served_ids_v: List[str] = []

            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                next_index = solution.Value(routing.NextVar(index))

                from_node = node
                to_node = manager.IndexToNode(next_index)
                t_arc = time_matrix[from_node][to_node] / ROUTE_SCALE
                d_arc = dist_matrix[from_node][to_node] / ROUTE_SCALE
                total_travel_v += t_arc
                total_dist_v += d_arc

                matched_ship = next(
                    (s for s in shipments if task_node_idx[s.shipment_id] == node),
                    None
                )
                if matched_ship is not None:
                    arrive_t = solution.Value(time_dim.CumulVar(index)) / ROUTE_SCALE
                    svc_end = arrive_t + matched_ship.service_time_min
                    lateness = max(0.0, arrive_t - matched_ship.latest_arrival_min)
                    weight_used += matched_ship.total_weight_kg
                    volume_used += matched_ship.total_volume_m3
                    total_service_v += matched_ship.service_time_min
                    served_ids_v.append(matched_ship.shipment_id)
                    served_shipment_ids.add(matched_ship.shipment_id)

                    stops.append(RouteStop(
                        stop_index=stop_count,
                        incident_id=matched_ship.incident_id,
                        incident_title=matched_ship.incident_title,
                        shipment_id=matched_ship.shipment_id,
                        arrival_time_min=arrive_t,
                        service_start_min=arrive_t,
                        service_end_min=svc_end,
                        departure_time_min=svc_end,
                        commodities=dict(matched_ship.commodities),
                        lateness_min=lateness,
                        priority_score=matched_ship.priority_score,
                        severity_level=matched_ship.severity_level,
                        latest_arrival_min=matched_ship.latest_arrival_min,
                    ))
                    stop_count += 1

                index = next_index

            if stops:
                w_util = (weight_used / vehicle.capacity_weight_kg * 100.0) if vehicle.capacity_weight_kg > 0 else 0.0
                v_util = (volume_used / vehicle.capacity_volume_m3 * 100.0) if vehicle.capacity_volume_m3 > 0 else 0.0
                explanation = self._explain_route(vehicle, stops, total_dist_v, total_travel_v + total_service_v)
                routes.append(VehicleRoute(
                    route_id=str(uuid.uuid4()),
                    vehicle_id=vehicle.vehicle_id,
                    vehicle_code=vehicle.vehicle_code,
                    vehicle_type=vehicle.vehicle_type,
                    start_depot_id=vehicle.depot_id,
                    stops=stops,
                    total_distance_km=total_dist_v,
                    total_travel_time_min=total_travel_v,
                    total_service_time_min=total_service_v,
                    total_route_duration_min=total_travel_v + total_service_v,
                    weight_used_kg=weight_used,
                    volume_used_m3=volume_used,
                    capacity_weight_kg=vehicle.capacity_weight_kg,
                    capacity_volume_m3=vehicle.capacity_volume_m3,
                    weight_utilization_pct=w_util,
                    volume_utilization_pct=v_util,
                    served_shipment_ids=served_ids_v,
                    explanation=explanation,
                    graph_version=graph_version,
                ))

        unrouted: List[UnroutedShipment] = []
        for ship in shipments:
            if ship.shipment_id not in served_shipment_ids:
                reason = self._diagnose_unrouted(ship, eligible_vehicles)
                unrouted.append(UnroutedShipment(
                    shipment_id=ship.shipment_id,
                    origin_depot_id=ship.origin_depot_id,
                    incident_id=ship.incident_id,
                    incident_title=ship.incident_title,
                    commodities=dict(ship.commodities),
                    total_weight_kg=ship.total_weight_kg,
                    total_volume_m3=ship.total_volume_m3,
                    reason=reason,
                ))

        t_extract_end = time.perf_counter()

        return self._build_result(
            run_id, solver_status,
            "FULLY_FEASIBLE" if not unrouted else ("PARTIALLY_FEASIBLE" if routes else "UNROUTABLE"),
            routes, unrouted, shipments, eligible_vehicles, graph_version, "OR-Tools RoutingModel",
            t_total_start, t_matrix_start, t_matrix_end, t_model_start, t_model_end,
            t_solve_start, t_solve_end, t_extract_start, t_extract_end
        )

    def _explain_route(self, vehicle: VehicleInput, stops: List[RouteStop],
                       dist_km: float, duration_min: float) -> str:
        critical = [s for s in stops if s.severity_level == "CRITICAL"]
        stop_seq = " -> ".join(f"{s.incident_title}({s.severity_level})" for s in stops)
        crit_str = f" Serves {len(critical)} CRITICAL incident(s)." if critical else ""
        return (
            f"Vehicle {vehicle.vehicle_code} ({vehicle.vehicle_type}) assigned to: {stop_seq}. "
            f"Total route distance: {dist_km:.1f} km. Route duration: {duration_min:.1f} min."
            f"{crit_str} Depot: {vehicle.depot_id}. "
            f"Reason: depot compatibility + capacity feasibility + routing objective minimization."
        )

    def _diagnose_unrouted(self, ship: ShipmentInput, vehicles: List[VehicleInput]) -> str:
        eligible = [v for v in vehicles if v.depot_id == ship.origin_depot_id]
        if not eligible:
            return f"No AVAILABLE vehicle is based at origin depot {ship.origin_depot_id}."
        max_w = max(v.capacity_weight_kg for v in eligible)
        max_v = max(v.capacity_volume_m3 for v in eligible)
        if ship.total_weight_kg > max_w:
            return (f"Shipment weight {ship.total_weight_kg:.1f} kg exceeds all eligible vehicle "
                    f"capacities (max {max_w:.1f} kg) from depot {ship.origin_depot_id}.")
        if ship.total_volume_m3 > max_v:
            return (f"Shipment volume {ship.total_volume_m3:.4f} m3 exceeds all eligible vehicle "
                    f"capacities (max {max_v:.4f} m3) from depot {ship.origin_depot_id}.")
        return (f"No feasible route assignment found by OR-Tools RoutingModel for shipment "
                f"{ship.shipment_id} (depot {ship.origin_depot_id} -> incident {ship.incident_id}). "
                f"Possible causes: capacity conflicts with co-assigned shipments, unreachable road network, or time-window infeasibility.")

    def _empty_result(self, run_id: str, shipments: List[ShipmentInput],
                      graph_version: str, t_start: float, reason: str) -> RoutingResult:
        unrouted = [
            UnroutedShipment(s.shipment_id, s.origin_depot_id, s.incident_id,
                             s.incident_title, dict(s.commodities),
                             s.total_weight_kg, s.total_volume_m3, reason)
            for s in shipments
        ]
        return RoutingResult(
            routing_run_id=run_id, solver_status="INFEASIBLE",
            operational_status="UNROUTABLE", routes=[], unrouted_shipments=unrouted,
            total_distance_km=0.0, total_travel_time_min=0.0, total_service_time_min=0.0,
            mean_response_time_min=0.0, critical_mean_response_time_min=0.0,
            sla_compliance_pct=0.0, total_late_minutes=0.0,
            vehicle_utilization_pct=0.0, mean_weight_utilization_pct=0.0,
            mean_volume_utilization_pct=0.0,
            unrouted_shipment_count=len(unrouted), unrouted_shipment_pct=100.0,
            objective_value=0.0, solver_runtime_ms=round((time.perf_counter() - t_start) * 1000, 3),
            graph_version=graph_version, algorithm="OR-Tools RoutingModel",
        )

    def _build_result(
        self, run_id, solver_status, operational_status, routes, unrouted,
        shipments, vehicles, graph_version, algorithm,
        t_total, t_mx0, t_mx1, t_md0, t_md1, t_sv0, t_sv1, t_ex0, t_ex1
    ) -> RoutingResult:
        t_end = time.perf_counter()
        all_stops = [s for r in routes for s in r.stops]
        crit_stops = [s for s in all_stops if s.severity_level == "CRITICAL"]
        sla_stops = [s for s in all_stops if s.lateness_min == 0.0]

        total_qty = sum(sum(s.commodities.values()) for s in shipments)
        unrouted_qty = sum(sum(u.commodities.values()) for u in unrouted)
        unrouted_pct = (unrouted_qty / total_qty * 100.0) if total_qty > 0 else 0.0

        used_veh = len(routes)
        avail_veh = len(vehicles)
        v_util = (used_veh / avail_veh * 100.0) if avail_veh > 0 else 0.0

        mean_w_util = (sum(r.weight_utilization_pct for r in routes) / len(routes)) if routes else 0.0
        mean_v_util = (sum(r.volume_utilization_pct for r in routes) / len(routes)) if routes else 0.0

        # Primary routing objective
        # Z = beta_1 * sum(late) + beta_2 * sum(travel_time) + beta_3 * sum(dist) + beta_4 * num_vehicles
        tot_late = sum(s.lateness_min for s in all_stops)
        tot_time = sum(r.total_travel_time_min for r in routes)
        tot_dist = sum(r.total_distance_km for r in routes)
        obj_val = (
            self.weights["beta_1"] * tot_late +
            self.weights["beta_2"] * tot_time +
            self.weights["beta_3"] * tot_dist +
            self.weights["beta_4"] * used_veh
        )

        return RoutingResult(
            routing_run_id=run_id,
            solver_status=solver_status,
            operational_status=operational_status,
            routes=routes,
            unrouted_shipments=unrouted,
            total_distance_km=tot_dist,
            total_travel_time_min=tot_time,
            total_service_time_min=sum(r.total_service_time_min for r in routes),
            mean_response_time_min=(sum(s.arrival_time_min for s in all_stops) / len(all_stops)) if all_stops else 0.0,
            critical_mean_response_time_min=(sum(s.arrival_time_min for s in crit_stops) / len(crit_stops)) if crit_stops else 0.0,
            sla_compliance_pct=(len(sla_stops) / len(all_stops) * 100.0) if all_stops else 100.0,
            total_late_minutes=tot_late,
            vehicle_utilization_pct=v_util,
            mean_weight_utilization_pct=mean_w_util,
            mean_volume_utilization_pct=mean_v_util,
            unrouted_shipment_count=len(unrouted),
            unrouted_shipment_pct=unrouted_pct,
            objective_value=obj_val,
            solver_runtime_ms=round((t_sv1 - t_sv0) * 1000, 3),
            graph_version=graph_version,
            algorithm=algorithm,
            timing_breakdown={
                "matrix_build_ms": round((t_mx1 - t_mx0) * 1000, 3),
                "model_construction_ms": round((t_md1 - t_md0) * 1000, 3),
                "solver_search_ms": round((t_sv1 - t_sv0) * 1000, 3),
                "solution_extraction_ms": round((t_ex1 - t_ex0) * 1000, 3),
                "orchestration_overhead_ms": round(max(0.0, (t_end - t_total) - ((t_mx1 - t_mx0) + (t_md1 - t_md0) + (t_sv1 - t_sv0) + (t_ex1 - t_ex0))) * 1000, 3),
                "total_routing_ms": round((t_end - t_total) * 1000, 3),
            }
        )


# -- BASELINE A: NEAREST-FEASIBLE VEHICLE --

class NearestFeasibleRoutingEngine:
    """
    Baseline A: Nearest-Feasible Vehicle Assignment.
    For each shipment (ordered by priority desc), assign the nearest AVAILABLE vehicle
    whose depot matches the shipment origin and that has sufficient remaining capacity.
    """

    def solve(
        self,
        shipments: List[ShipmentInput],
        vehicles: List[VehicleInput],
        graph_engine: RoadGraphEngine,
    ) -> RoutingResult:
        t_start = time.perf_counter()
        run_id = str(uuid.uuid4())
        graph_version = graph_engine.get_graph_version()

        eligible = [v for v in vehicles if v.status == "AVAILABLE"]
        if not shipments or not eligible:
            return VehicleRoutingEngine()._empty_result(run_id, shipments, graph_version, t_start,
                                                        "No shipments or no eligible vehicles (Baseline A).")

        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        ordered = sorted(shipments, key=lambda s: (priority_order.get(s.severity_level, 4), -s.priority_score, s.shipment_id))

        veh_remaining_w: Dict[str, float] = {v.vehicle_id: v.capacity_weight_kg for v in eligible}
        veh_remaining_v: Dict[str, float] = {v.vehicle_id: v.capacity_volume_m3 for v in eligible}
        veh_stops: Dict[str, List[RouteStop]] = {v.vehicle_id: [] for v in eligible}
        veh_current_time: Dict[str, float] = {v.vehicle_id: 0.0 for v in eligible}
        veh_current_loc: Dict[str, Tuple[float, float]] = {v.vehicle_id: (v.depot_lat, v.depot_lng) for v in eligible}
        veh_dist: Dict[str, float] = {v.vehicle_id: 0.0 for v in eligible}
        veh_travel: Dict[str, float] = {v.vehicle_id: 0.0 for v in eligible}

        routes: List[VehicleRoute] = []
        unrouted: List[UnroutedShipment] = []
        served_ids: set = set()

        for ship in ordered:
            compatible = [
                v for v in eligible
                if v.depot_id == ship.origin_depot_id
                and veh_remaining_w[v.vehicle_id] >= ship.total_weight_kg
                and veh_remaining_v[v.vehicle_id] >= ship.total_volume_m3
            ]
            if not compatible:
                reason = VehicleRoutingEngine()._diagnose_unrouted(ship, eligible)
                unrouted.append(UnroutedShipment(
                    ship.shipment_id, ship.origin_depot_id, ship.incident_id, ship.incident_title,
                    dict(ship.commodities), ship.total_weight_kg, ship.total_volume_m3,
                    f"Baseline A: {reason}"
                ))
                continue

            compatible_sorted = sorted(
                compatible,
                key=lambda v: (
                    haversine_distance(veh_current_loc[v.vehicle_id][0], veh_current_loc[v.vehicle_id][1],
                                      ship.incident_lat, ship.incident_lng),
                    v.vehicle_code
                )
            )
            chosen = compatible_sorted[0]
            vid = chosen.vehicle_id

            curr_lat, curr_lng = veh_current_loc[vid]
            orig_node = graph_engine.find_nearest_node(curr_lat, curr_lng)
            dest_node = graph_engine.find_nearest_node(ship.incident_lat, ship.incident_lng)
            
            if orig_node and dest_node:
                route_r = graph_engine.compute_shortest_path(orig_node, dest_node)
                if route_r.status == "FEASIBLE":
                    t_mins = route_r.travel_time_minutes
                    d_km = route_r.distance_km
                else:
                    unrouted.append(UnroutedShipment(
                        ship.shipment_id, ship.origin_depot_id, ship.incident_id, ship.incident_title,
                        dict(ship.commodities), ship.total_weight_kg, ship.total_volume_m3,
                        "Baseline A: No feasible Phase 5C path from current location to incident."
                    ))
                    continue
            else:
                d_km = haversine_distance(curr_lat, curr_lng, ship.incident_lat, ship.incident_lng)
                t_mins = (d_km / 50.0) * 60.0

            arrive = veh_current_time[vid] + t_mins
            lateness = max(0.0, arrive - ship.latest_arrival_min)

            stop_idx = len(veh_stops[vid])
            veh_stops[vid].append(RouteStop(
                stop_index=stop_idx,
                incident_id=ship.incident_id,
                incident_title=ship.incident_title,
                shipment_id=ship.shipment_id,
                arrival_time_min=arrive,
                service_start_min=arrive,
                service_end_min=arrive + ship.service_time_min,
                departure_time_min=arrive + ship.service_time_min,
                commodities=dict(ship.commodities),
                lateness_min=lateness,
                priority_score=ship.priority_score,
                severity_level=ship.severity_level,
                latest_arrival_min=ship.latest_arrival_min,
            ))

            veh_remaining_w[vid] -= ship.total_weight_kg
            veh_remaining_v[vid] -= ship.total_volume_m3
            veh_current_time[vid] = arrive + ship.service_time_min
            veh_current_loc[vid] = (ship.incident_lat, ship.incident_lng)
            veh_dist[vid] += d_km
            veh_travel[vid] += t_mins
            served_ids.add(ship.shipment_id)

        for v in eligible:
            vid = v.vehicle_id
            stops = veh_stops[vid]
            if not stops:
                continue
            
            # Return to starting depot
            curr_lat, curr_lng = veh_current_loc[vid]
            dest_node = graph_engine.find_nearest_node(v.depot_lat, v.depot_lng)
            orig_node = graph_engine.find_nearest_node(curr_lat, curr_lng)
            if orig_node and dest_node:
                r_ret = graph_engine.compute_shortest_path(orig_node, dest_node)
                if r_ret.status == "FEASIBLE":
                    veh_travel[vid] += r_ret.travel_time_minutes
                    veh_dist[vid] += r_ret.distance_km

            w_used = v.capacity_weight_kg - veh_remaining_w[vid]
            vol_used = v.capacity_volume_m3 - veh_remaining_v[vid]
            svc_total = sum(s.service_end_min - s.service_start_min for s in stops)
            routes.append(VehicleRoute(
                route_id=str(uuid.uuid4()),
                vehicle_id=v.vehicle_id, vehicle_code=v.vehicle_code, vehicle_type=v.vehicle_type,
                start_depot_id=v.depot_id, stops=stops,
                total_distance_km=veh_dist[vid], total_travel_time_min=veh_travel[vid],
                total_service_time_min=svc_total,
                total_route_duration_min=veh_travel[vid] + svc_total,
                weight_used_kg=w_used, volume_used_m3=vol_used,
                capacity_weight_kg=v.capacity_weight_kg, capacity_volume_m3=v.capacity_volume_m3,
                weight_utilization_pct=(w_used / v.capacity_weight_kg * 100.0) if v.capacity_weight_kg > 0 else 0.0,
                volume_utilization_pct=(vol_used / v.capacity_volume_m3 * 100.0) if v.capacity_volume_m3 > 0 else 0.0,
                served_shipment_ids=[s.shipment_id for s in stops],
                explanation=f"Baseline A (Nearest-Feasible): {v.vehicle_code} assigned {len(stops)} stops.",
                graph_version=graph_version,
            ))

        return VehicleRoutingEngine()._build_result(
            run_id, "FEASIBLE",
            "FULLY_FEASIBLE" if not unrouted else ("PARTIALLY_FEASIBLE" if routes else "UNROUTABLE"),
            routes, unrouted, shipments, eligible, graph_version, "Baseline-A-NearestFeasible",
            t_start, t_start, t_start, t_start, t_start, t_start, time.perf_counter(),
            time.perf_counter(), time.perf_counter()
        )


# -- BASELINE B: FCFS VEHICLE ASSIGNMENT --

class FCFSRoutingEngine:
    """
    Baseline B: First-Come-First-Served Vehicle Assignment.
    Process shipments in incident creation order (timestamp string, then incident_id).
    """

    def solve(
        self,
        shipments: List[ShipmentInput],
        vehicles: List[VehicleInput],
        graph_engine: RoadGraphEngine,
        creation_order: Optional[Dict[str, str]] = None,
    ) -> RoutingResult:
        t_start = time.perf_counter()
        run_id = str(uuid.uuid4())
        graph_version = graph_engine.get_graph_version()

        eligible = [v for v in vehicles if v.status == "AVAILABLE"]
        if not shipments or not eligible:
            return VehicleRoutingEngine()._empty_result(run_id, shipments, graph_version, t_start,
                                                        "No shipments or no eligible vehicles (Baseline B).")

        def fcfs_key(s: ShipmentInput) -> Tuple[str, str]:
            ts = (creation_order or {}).get(s.incident_id, "9999")
            return (ts, s.shipment_id)

        ordered = sorted(shipments, key=fcfs_key)

        veh_remaining_w = {v.vehicle_id: v.capacity_weight_kg for v in eligible}
        veh_remaining_v = {v.vehicle_id: v.capacity_volume_m3 for v in eligible}
        veh_stops: Dict[str, List[RouteStop]] = {v.vehicle_id: [] for v in eligible}
        veh_current_time: Dict[str, float] = {v.vehicle_id: 0.0 for v in eligible}
        veh_current_loc: Dict[str, Tuple[float, float]] = {v.vehicle_id: (v.depot_lat, v.depot_lng) for v in eligible}
        veh_dist: Dict[str, float] = {v.vehicle_id: 0.0 for v in eligible}
        veh_travel: Dict[str, float] = {v.vehicle_id: 0.0 for v in eligible}

        routes: List[VehicleRoute] = []
        unrouted: List[UnroutedShipment] = []
        served_ids: set = set()

        eligible_sorted = sorted(eligible, key=lambda v: v.vehicle_code)

        for ship in ordered:
            compatible = [
                v for v in eligible_sorted
                if v.depot_id == ship.origin_depot_id
                and veh_remaining_w[v.vehicle_id] >= ship.total_weight_kg
                and veh_remaining_v[v.vehicle_id] >= ship.total_volume_m3
            ]
            if not compatible:
                unrouted.append(UnroutedShipment(
                    ship.shipment_id, ship.origin_depot_id, ship.incident_id, ship.incident_title,
                    dict(ship.commodities), ship.total_weight_kg, ship.total_volume_m3,
                    f"Baseline B (FCFS): No eligible vehicle with sufficient capacity from depot {ship.origin_depot_id}."
                ))
                continue

            chosen = compatible[0]
            vid = chosen.vehicle_id

            curr_lat, curr_lng = veh_current_loc[vid]
            orig_node = graph_engine.find_nearest_node(curr_lat, curr_lng)
            dest_node = graph_engine.find_nearest_node(ship.incident_lat, ship.incident_lng)
            
            if orig_node and dest_node:
                route_r = graph_engine.compute_shortest_path(orig_node, dest_node)
                if route_r.status == "FEASIBLE":
                    t_mins = route_r.travel_time_minutes
                    d_km = route_r.distance_km
                else:
                    unrouted.append(UnroutedShipment(
                        ship.shipment_id, ship.origin_depot_id, ship.incident_id, ship.incident_title,
                        dict(ship.commodities), ship.total_weight_kg, ship.total_volume_m3,
                        "Baseline B: No Phase 5C feasible path to incident."
                    ))
                    continue
            else:
                d_km = haversine_distance(curr_lat, curr_lng, ship.incident_lat, ship.incident_lng)
                t_mins = (d_km / 50.0) * 60.0

            arrive = veh_current_time[vid] + t_mins
            lateness = max(0.0, arrive - ship.latest_arrival_min)
            stop_idx = len(veh_stops[vid])
            veh_stops[vid].append(RouteStop(
                stop_index=stop_idx, incident_id=ship.incident_id,
                incident_title=ship.incident_title, shipment_id=ship.shipment_id,
                arrival_time_min=arrive, service_start_min=arrive,
                service_end_min=arrive + ship.service_time_min,
                departure_time_min=arrive + ship.service_time_min,
                commodities=dict(ship.commodities), lateness_min=lateness,
                priority_score=ship.priority_score, severity_level=ship.severity_level,
                latest_arrival_min=ship.latest_arrival_min,
            ))
            veh_remaining_w[vid] -= ship.total_weight_kg
            veh_remaining_v[vid] -= ship.total_volume_m3
            veh_current_time[vid] = arrive + ship.service_time_min
            veh_current_loc[vid] = (ship.incident_lat, ship.incident_lng)
            veh_dist[vid] += d_km
            veh_travel[vid] += t_mins
            served_ids.add(ship.shipment_id)

        for v in eligible:
            vid = v.vehicle_id
            stops = veh_stops[vid]
            if not stops:
                continue
                
            # Return to starting depot
            curr_lat, curr_lng = veh_current_loc[vid]
            dest_node = graph_engine.find_nearest_node(v.depot_lat, v.depot_lng)
            orig_node = graph_engine.find_nearest_node(curr_lat, curr_lng)
            if orig_node and dest_node:
                r_ret = graph_engine.compute_shortest_path(orig_node, dest_node)
                if r_ret.status == "FEASIBLE":
                    veh_travel[vid] += r_ret.travel_time_minutes
                    veh_dist[vid] += r_ret.distance_km

            w_used = v.capacity_weight_kg - veh_remaining_w[vid]
            vol_used = v.capacity_volume_m3 - veh_remaining_v[vid]
            svc_total = sum(s.service_end_min - s.service_start_min for s in stops)
            routes.append(VehicleRoute(
                route_id=str(uuid.uuid4()),
                vehicle_id=v.vehicle_id, vehicle_code=v.vehicle_code, vehicle_type=v.vehicle_type,
                start_depot_id=v.depot_id, stops=stops,
                total_distance_km=veh_dist[vid], total_travel_time_min=veh_travel[vid],
                total_service_time_min=svc_total,
                total_route_duration_min=veh_travel[vid] + svc_total,
                weight_used_kg=w_used, volume_used_m3=vol_used,
                capacity_weight_kg=v.capacity_weight_kg, capacity_volume_m3=v.capacity_volume_m3,
                weight_utilization_pct=(w_used / v.capacity_weight_kg * 100.0) if v.capacity_weight_kg > 0 else 0.0,
                volume_utilization_pct=(vol_used / v.capacity_volume_m3 * 100.0) if v.capacity_volume_m3 > 0 else 0.0,
                served_shipment_ids=[s.shipment_id for s in stops],
                explanation=f"Baseline B (FCFS): {v.vehicle_code} assigned {len(stops)} stops in creation order.",
                graph_version=graph_version,
            ))

        return VehicleRoutingEngine()._build_result(
            run_id, "FEASIBLE",
            "FULLY_FEASIBLE" if not unrouted else ("PARTIALLY_FEASIBLE" if routes else "UNROUTABLE"),
            routes, unrouted, shipments, eligible, graph_version, "Baseline-B-FCFS",
            t_start, t_start, t_start, t_start, t_start, t_start, time.perf_counter(),
            time.perf_counter(), time.perf_counter()
        )


# -- PHASE 5D CONSERVATION VERIFIER --

def verify_phase5d_conservation(
    shipments: List[ShipmentInput],
    result: RoutingResult
) -> Dict[str, Any]:
    """
    Verifies Phase 5D conservation invariant:
        For every (incident x commodity): allocated_qty == routed_qty + unrouted_qty
    """
    allocated: Dict[Tuple[str, str], float] = {}
    for ship in shipments:
        for commodity, qty in ship.commodities.items():
            key = (ship.incident_id, commodity)
            allocated[key] = allocated.get(key, 0.0) + qty

    routed: Dict[Tuple[str, str], float] = {}
    for route in result.routes:
        for stop in route.stops:
            for commodity, qty in stop.commodities.items():
                key = (stop.incident_id, commodity)
                routed[key] = routed.get(key, 0.0) + qty

    unrouted_map: Dict[Tuple[str, str], float] = {}
    for u in result.unrouted_shipments:
        for commodity, qty in u.commodities.items():
            key = (u.incident_id, commodity)
            unrouted_map[key] = unrouted_map.get(key, 0.0) + qty

    violations: List[Dict] = []
    for key, alloc_qty in allocated.items():
        r_qty = routed.get(key, 0.0)
        u_qty = unrouted_map.get(key, 0.0)
        diff = abs(alloc_qty - (r_qty + u_qty))
        if diff > 0.01:
            violations.append({
                "incident_id": key[0], "commodity": key[1],
                "allocated": alloc_qty, "routed": r_qty, "unrouted": u_qty,
                "difference": diff
            })

    return {
        "conservation_holds": len(violations) == 0,
        "violations": violations,
        "total_incident_commodity_pairs": len(allocated),
        "checked_pairs": len(allocated),
    }
