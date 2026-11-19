import time
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from ortools.sat.python import cp_model

from app.ai.optimization.graph import RoadGraphEngine, haversine_distance

# --- 1. Data Structures & Pydantic/Dataclass Interfaces ---

@dataclass
class IncidentDemandInput:
    incident_id: str
    title: str
    latitude: float
    longitude: float
    priority_score: float  # 0.0 to 100.0
    severity_level: str    # CRITICAL, HIGH, MEDIUM, LOW
    demands: Dict[str, float]  # e.g. {"WATER": 1000.0, "FOOD": 500.0, "MEDICAL_KITS": 50.0}
    created_at_str: str = ""

@dataclass
class DepotSupplyInput:
    depot_id: str
    name: str
    latitude: float
    longitude: float
    supplies: Dict[str, float]  # e.g. {"WATER": 5000.0, "FOOD": 2500.0, "MEDICAL_KITS": 200.0}

@dataclass
class CommodityAllocationItem:
    depot_id: str
    incident_id: str
    commodity: str
    quantity: float
    travel_time_minutes: float
    distance_km: float
    explanation: str

@dataclass
class UnmetDemandItem:
    incident_id: str
    commodity: str
    demanded_quantity: float
    allocated_quantity: float
    unmet_quantity: float
    priority_score: float
    explanation: str

@dataclass
class AllocationResult:
    solver_status: str              # OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN
    operational_feasibility: str    # FEASIBLE, PARTIALLY_FEASIBLE, INFEASIBLE
    allocations: List[CommodityAllocationItem]
    unmet_demands: List[UnmetDemandItem]
    total_unmet_demand_quantity: float
    unmet_demand_percentage: float
    priority_weighted_unmet_demand: float
    critical_fulfillment_percentage: float
    mean_shipment_travel_time_mins: float
    total_travel_distance_km: float
    resource_utilization_percentage: float
    solver_runtime_ms: float
    optimality_gap: float
    objective_value: float
    graph_version: str
    explanation_summary: str
    timing_breakdown: Dict[str, float] = field(default_factory=dict)


def _resolve_network_matrices(
    graph_engine: RoadGraphEngine,
    depots: List[DepotSupplyInput],
    incidents: List[IncidentDemandInput]
) -> Tuple[Dict[Tuple[str, str], bool], Dict[Tuple[str, str], float], Dict[Tuple[str, str], float]]:
    """Pre-maps spatial coordinates to graph nodes once and caches pathfinding metrics."""
    depot_nodes = {
        d.depot_id: d.depot_id if graph_engine.graph.has_node(d.depot_id) else graph_engine.find_nearest_node(d.latitude, d.longitude)
        for d in depots
    }
    incident_nodes = {
        i.incident_id: i.incident_id if graph_engine.graph.has_node(i.incident_id) else graph_engine.find_nearest_node(i.latitude, i.longitude)
        for i in incidents
    }

    route_cache: Dict[Tuple[str, str], Tuple[bool, float, float]] = {}

    reachability_mask: Dict[Tuple[str, str], bool] = {}
    travel_times: Dict[Tuple[str, str], float] = {}
    distances: Dict[Tuple[str, str], float] = {}

    for dep in depots:
        orig_node = depot_nodes[dep.depot_id]
        for inc in incidents:
            dest_node = incident_nodes[inc.incident_id]
            pair = (dep.depot_id, inc.incident_id)

            if orig_node is not None and dest_node is not None:
                cache_key = (orig_node, dest_node)
                if cache_key not in route_cache:
                    route = graph_engine.compute_shortest_path(orig_node, dest_node)
                    if route.status == "FEASIBLE":
                        route_cache[cache_key] = (True, route.travel_time_minutes, route.distance_km)
                    else:
                        route_cache[cache_key] = (False, 999999.0, 999999.0)
                is_r, t_val, d_val = route_cache[cache_key]
            else:
                d_km = haversine_distance(dep.latitude, dep.longitude, inc.latitude, inc.longitude)
                t_min = (d_km / graph_engine.default_speed_kmh) * 60.0 if graph_engine.default_speed_kmh > 0 else 0.0
                is_r, t_val, d_val = True, t_min, d_km

            reachability_mask[pair] = is_r
            travel_times[pair] = t_val
            distances[pair] = d_val

    return reachability_mask, travel_times, distances


# --- 2. Google OR-Tools CP-SAT Resource Allocation Engine ---

class ResourceAllocationEngine:
    """
    Phase 5D Multi-Commodity Resource Allocation Solver Engine using Google OR-Tools CP-SAT.
    Calculates optimal distribution of disaster response commodities from depots to incidents.
    Consumes Phase 5C RoadGraphEngine travel distance and travel-time matrices.
    """
    INTEGER_SCALE = 1000  # Scaling factor for float-to-integer CP-SAT coefficient translation

    def __init__(self, default_weights: Optional[Dict[str, float]] = None):
        # Multi-objective weights (Phase 5A formulation)
        self.weights = default_weights or {
            "alpha_1": 10.0,  # Unmet demand penalty
            "alpha_2": 5.0,   # High-severity delay penalty
            "alpha_3": 1.0,   # Shipment travel time
            "alpha_4": 0.2    # Travel distance
        }

    def solve(
        self,
        incidents: List[IncidentDemandInput],
        depots: List[DepotSupplyInput],
        graph_engine: RoadGraphEngine,
        solver_time_limit_sec: float = 2.0
    ) -> AllocationResult:
        t_start = time.perf_counter()

        if not incidents or not depots:
            return AllocationResult(
                solver_status="FEASIBLE",
                operational_feasibility="FEASIBLE",
                allocations=[],
                unmet_demands=[],
                total_unmet_demand_quantity=0.0,
                unmet_demand_percentage=0.0,
                priority_weighted_unmet_demand=0.0,
                critical_fulfillment_percentage=100.0,
                mean_shipment_travel_time_mins=0.0,
                total_travel_distance_km=0.0,
                resource_utilization_percentage=0.0,
                solver_runtime_ms=0.0,
                optimality_gap=0.0,
                objective_value=0.0,
                graph_version=graph_engine.get_graph_version(),
                explanation_summary="No active incidents or depots provided."
            )

        # 1. Validate inputs for invalid negative values
        for inc in incidents:
            if inc.priority_score < 0:
                raise ValueError(f"Invalid negative priority score for incident {inc.incident_id}")
            for commodity, qty in inc.demands.items():
                if qty < 0:
                    raise ValueError(f"Invalid negative demand quantity for incident {inc.incident_id}, commodity {commodity}")

        for dep in depots:
            for commodity, qty in dep.supplies.items():
                if qty < 0:
                    raise ValueError(f"Invalid negative supply quantity for depot {dep.depot_id}, commodity {commodity}")

        # 2. Extract Commodity Categories & Build Identifiers
        commodities = sorted(list(set(c for inc in incidents for c in inc.demands.keys()) |
                                   set(c for dep in depots for c in dep.supplies.keys())))

        # 3. Ingest Phase 5C Travel Matrix & Feasibility Masking
        t_matrix_start = time.perf_counter()
        reachability_mask, travel_times, distances = _resolve_network_matrices(graph_engine, depots, incidents)
        t_matrix_end = time.perf_counter()

        # 4. Construct CP-SAT Model
        t_model_start = time.perf_counter()
        model = cp_model.CpModel()
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = solver_time_limit_sec
        solver.parameters.random_seed = 42  # Enforce deterministic solver configuration
        solver.parameters.num_search_workers = 1  # Enforce single-threaded deterministic solve

        # Decision Variables:
        x_vars: Dict[Tuple[str, str, str], cp_model.IntVar] = {}
        y_vars: Dict[Tuple[str, str], cp_model.IntVar] = {}
        u_vars: Dict[Tuple[str, str], cp_model.IntVar] = {}

        for dep in depots:
            for inc in incidents:
                pair = (dep.depot_id, inc.incident_id)
                if not reachability_mask[pair]:
                    continue

                active_pair_has_cap = False
                for r in commodities:
                    max_cap = int(math.ceil(min(dep.supplies.get(r, 0.0), inc.demands.get(r, 0.0))))
                    if max_cap > 0:
                        var_key = (dep.depot_id, inc.incident_id, r)
                        x_vars[var_key] = model.NewIntVar(0, max_cap, f"x_{var_key[0]}_{var_key[1]}_{var_key[2]}")
                        active_pair_has_cap = True

                if active_pair_has_cap:
                    y_vars[pair] = model.NewBoolVar(f"y_{dep.depot_id}_{inc.incident_id}")
                    for r in commodities:
                        var_key = (dep.depot_id, inc.incident_id, r)
                        if var_key in x_vars:
                            max_cap = int(math.ceil(min(dep.supplies.get(r, 0.0), inc.demands.get(r, 0.0))))
                            model.Add(x_vars[var_key] <= max_cap * y_vars[pair])

        # Unmet Demand Variables u[i, r]
        for inc in incidents:
            for r in commodities:
                demand_qty = int(math.ceil(inc.demands.get(r, 0.0)))
                u_key = (inc.incident_id, r)
                if demand_qty > 0:
                    u_vars[u_key] = model.NewIntVar(0, demand_qty, f"u_{inc.incident_id}_{r}")
                    active_x = [x_vars[(dep.depot_id, inc.incident_id, r)] for dep in depots if (dep.depot_id, inc.incident_id, r) in x_vars]
                    model.Add(u_vars[u_key] == demand_qty - sum(active_x))

        # HARD CONSTRAINT 1: Supply Inventory Bounds
        for dep in depots:
            for r in commodities:
                supply_qty = int(math.floor(dep.supplies.get(r, 0.0)))
                active_x = [x_vars[(dep.depot_id, inc.incident_id, r)] for inc in incidents if (dep.depot_id, inc.incident_id, r) in x_vars]
                if active_x:
                    model.Add(sum(active_x) <= supply_qty)

        # 5. Multi-Objective Cost Function Construction
        obj_terms = []

        for inc in incidents:
            p_score = inc.priority_score
            p_weight = max(1.0, p_score)
            
            # Severity multiplier boost
            sev_boost = 1.0
            if inc.severity_level == "CRITICAL":
                sev_boost = 3.0
            elif inc.severity_level == "HIGH":
                sev_boost = 2.0

            for r in commodities:
                u_key = (inc.incident_id, r)
                if u_key in u_vars:
                    # Term 1: Unmet demand cost weighted by priority & severity
                    unmet_cost_weight = int(math.ceil(self.weights["alpha_1"] * p_weight * sev_boost * self.INTEGER_SCALE))
                    obj_terms.append(unmet_cost_weight * u_vars[u_key])
                    
                    # Term 2: Priority squared penalty for high severity
                    p_sq_weight = int(math.ceil(self.weights["alpha_2"] * (p_score ** 2 / 10.0) * sev_boost * self.INTEGER_SCALE))
                    obj_terms.append(p_sq_weight * u_vars[u_key])

        for dep in depots:
            for inc in incidents:
                pair = (dep.depot_id, inc.incident_id)
                if pair in y_vars:
                    t_mins = travel_times[pair]
                    d_km = distances[pair]
                    
                    # Term 3: Travel time penalty for active shipment y[d,i]
                    t_cost = int(math.ceil(self.weights["alpha_3"] * t_mins * self.INTEGER_SCALE))
                    obj_terms.append(t_cost * y_vars[pair])
                    
                    # Term 4: Distance penalty for active shipment y[d,i]
                    d_cost = int(math.ceil(self.weights["alpha_4"] * d_km * self.INTEGER_SCALE))
                    obj_terms.append(d_cost * y_vars[pair])

        if obj_terms:
            model.Minimize(sum(obj_terms))
        t_model_end = time.perf_counter()

        # 6. Solve Model
        t_solve_start = time.perf_counter()
        status = solver.Solve(model)
        t_solve_end = time.perf_counter()

        status_map = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.UNKNOWN: "UNKNOWN"
        }
        solver_status_str = status_map.get(status, "UNKNOWN")

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            t_total_end = time.perf_counter()
            return AllocationResult(
                solver_status=solver_status_str,
                operational_feasibility="INFEASIBLE",
                allocations=[],
                unmet_demands=[],
                total_unmet_demand_quantity=sum(sum(inc.demands.values()) for inc in incidents),
                unmet_demand_percentage=100.0,
                priority_weighted_unmet_demand=100.0,
                critical_fulfillment_percentage=0.0,
                mean_shipment_travel_time_mins=0.0,
                total_travel_distance_km=0.0,
                resource_utilization_percentage=0.0,
                solver_runtime_ms=round((t_total_end - t_start) * 1000.0, 3),
                optimality_gap=100.0,
                objective_value=float('inf'),
                graph_version=graph_engine.get_graph_version(),
                explanation_summary="Solver returned INFEASIBLE or UNKNOWN.",
                timing_breakdown={
                    "matrix_retrieval_ms": round((t_matrix_end - t_matrix_start) * 1000.0, 3),
                    "model_construction_ms": round((t_model_end - t_model_start) * 1000.0, 3),
                    "cpsat_solve_ms": round((t_solve_end - t_solve_start) * 1000.0, 3),
                    "solution_extraction_ms": 0.0,
                    "explanation_generation_ms": 0.0,
                    "total_execution_ms": round((t_total_end - t_start) * 1000.0, 3)
                }
            )

        # 7. Extract Solution Allocations & Metrics
        t_extract_start = time.perf_counter()
        allocations: List[CommodityAllocationItem] = []
        unmet_items: List[UnmetDemandItem] = []

        total_demanded = 0.0
        total_allocated = 0.0
        total_unmet = 0.0
        total_p_weighted_unmet = 0.0
        
        crit_demanded = 0.0
        crit_allocated = 0.0

        total_usable_supply = sum(sum(dep.supplies.values()) for dep in depots)
        active_shipment_times = []
        active_shipment_distances = []

        t_exp_start = time.perf_counter()
        for dep in depots:
            for inc in incidents:
                pair = (dep.depot_id, inc.incident_id)
                if pair in y_vars and solver.Value(y_vars[pair]) > 0:
                    active_shipment_times.append(travel_times[pair])
                    active_shipment_distances.append(distances[pair])

                for r in commodities:
                    var_key = (dep.depot_id, inc.incident_id, r)
                    if var_key in x_vars:
                        qty = float(solver.Value(x_vars[var_key]))
                        if qty > 0:
                            total_allocated += qty
                            if inc.severity_level == "CRITICAL":
                                crit_allocated += qty

                            exp = (f"Allocated {qty:.0f} units of {r} from {dep.name} to {inc.title}. "
                                   f"Priority Score: {inc.priority_score:.1f}, Travel Time: {travel_times[pair]:.1f} mins.")

                            allocations.append(CommodityAllocationItem(
                                depot_id=dep.depot_id,
                                incident_id=inc.incident_id,
                                commodity=r,
                                quantity=qty,
                                travel_time_minutes=round(travel_times[pair], 1),
                                distance_km=round(distances[pair], 1),
                                explanation=exp
                            ))

        for inc in incidents:
            for r in commodities:
                dem_qty = inc.demands.get(r, 0.0)
                if dem_qty > 0:
                    total_demanded += dem_qty
                    if inc.severity_level == "CRITICAL":
                        crit_demanded += dem_qty

                    u_key = (inc.incident_id, r)
                    u_val = float(solver.Value(u_vars[u_key])) if u_key in u_vars else 0.0
                    if u_val > 0:
                        total_unmet += u_val
                        total_p_weighted_unmet += u_val * inc.priority_score
                        
                        # Generate human-readable shortage explanation
                        reason = "Reachable inventory was insufficient or prioritized for higher-severity sites."
                        if all(not reachability_mask.get((dep.depot_id, inc.incident_id), False) for dep in depots if dep.supplies.get(r, 0) > 0):
                            reason = "All depots with available inventory were unreachable due to road blockages."

                        exp = (f"Incident {inc.title}: {r} demand = {dem_qty:.0f}, Allocated = {dem_qty - u_val:.0f}, "
                               f"Unmet = {u_val:.0f}. Reason: {reason}")

                        unmet_items.append(UnmetDemandItem(
                            incident_id=inc.incident_id,
                            commodity=r,
                            demanded_quantity=dem_qty,
                            allocated_quantity=dem_qty - u_val,
                            unmet_quantity=u_val,
                            priority_score=inc.priority_score,
                            explanation=exp
                        ))

        t_exp_end = time.perf_counter()
        t_extract_end = time.perf_counter()

        unmet_pct = round((total_unmet / total_demanded * 100.0) if total_demanded > 0 else 0.0, 2)
        crit_fulfillment_pct = round((crit_allocated / crit_demanded * 100.0) if crit_demanded > 0 else 100.0, 2)
        utilization_pct = round((total_allocated / total_usable_supply * 100.0) if total_usable_supply > 0 else 0.0, 2)
        mean_travel_time = round(sum(active_shipment_times) / len(active_shipment_times), 1) if active_shipment_times else 0.0
        total_distance = round(sum(active_shipment_distances), 1)

        # Operational Feasibility Classification
        if total_unmet == 0.0:
            op_feasibility = "FEASIBLE"
        elif total_allocated > 0.0:
            op_feasibility = "PARTIALLY_FEASIBLE"
        else:
            op_feasibility = "INFEASIBLE"

        t_end = time.perf_counter()
        total_runtime_ms = round((t_end - t_start) * 1000.0, 3)

        return AllocationResult(
            solver_status=solver_status_str,
            operational_feasibility=op_feasibility,
            allocations=allocations,
            unmet_demands=unmet_items,
            total_unmet_demand_quantity=total_unmet,
            unmet_demand_percentage=unmet_pct,
            priority_weighted_unmet_demand=round(total_p_weighted_unmet, 1),
            critical_fulfillment_percentage=crit_fulfillment_pct,
            mean_shipment_travel_time_mins=mean_travel_time,
            total_travel_distance_km=total_distance,
            resource_utilization_percentage=utilization_pct,
            solver_runtime_ms=total_runtime_ms,
            optimality_gap=0.0,
            objective_value=float(solver.ObjectiveValue() / self.INTEGER_SCALE),
            graph_version=graph_engine.get_graph_version(),
            explanation_summary=f"CP-SAT {solver_status_str} solution. Operational Status: {op_feasibility}. Unmet Demand: {unmet_pct}%.",
            timing_breakdown={
                "matrix_retrieval_ms": round((t_matrix_end - t_matrix_start) * 1000.0, 3),
                "model_construction_ms": round((t_model_end - t_model_start) * 1000.0, 3),
                "cpsat_solve_ms": round((t_solve_end - t_solve_start) * 1000.0, 3),
                "solution_extraction_ms": round((t_extract_end - t_extract_start) * 1000.0, 3),
                "explanation_generation_ms": round((t_exp_end - t_exp_start) * 1000.0, 3),
                "total_execution_ms": total_runtime_ms
            }
        )


# --- 3. Deterministic Baseline Algorithms ---

class GreedyProximityAllocationEngine:
    """
    BASELINE A: Nearest Feasible Resource Allocation.
    For each incident demand, allocates available stock from the nearest reachable depot using Phase 5C travel time matrix.
    """
    def solve(
        self,
        incidents: List[IncidentDemandInput],
        depots: List[DepotSupplyInput],
        graph_engine: RoadGraphEngine,
        sort_by_priority: bool = True
    ) -> AllocationResult:
        t_start = time.perf_counter()
        reachability_mask, travel_times, distances = _resolve_network_matrices(graph_engine, depots, incidents)

        # Deep copy depot inventories
        stock: Dict[str, Dict[str, float]] = {d.depot_id: dict(d.supplies) for d in depots}
        allocations: List[CommodityAllocationItem] = []
        unmet_items: List[UnmetDemandItem] = []

        total_demanded = sum(sum(inc.demands.values()) for inc in incidents)
        total_allocated = 0.0
        total_unmet = 0.0
        total_p_weighted_unmet = 0.0
        crit_demanded = sum(sum(inc.demands.values()) for inc in incidents if inc.severity_level == "CRITICAL")
        crit_allocated = 0.0

        # Sort incidents by priority score descending or preserve ordering
        if sort_by_priority:
            sorted_incidents = sorted(incidents, key=lambda x: x.priority_score, reverse=True)
        else:
            sorted_incidents = list(incidents)

        for inc in sorted_incidents:
            # Find depots ordered by travel time to this incident
            reachable_depots = []
            for dep in depots:
                pair = (dep.depot_id, inc.incident_id)
                if reachability_mask[pair]:
                    reachable_depots.append((travel_times[pair], distances[pair], dep))
            reachable_depots.sort(key=lambda x: x[0])

            for commodity, dem_qty in inc.demands.items():
                rem_demand = dem_qty
                for t_val, d_val, dep in reachable_depots:
                    avail = stock[dep.depot_id].get(commodity, 0.0)
                    if avail > 0 and rem_demand > 0:
                        alloc_qty = min(avail, rem_demand)
                        stock[dep.depot_id][commodity] -= alloc_qty
                        rem_demand -= alloc_qty
                        total_allocated += alloc_qty
                        if inc.severity_level == "CRITICAL":
                            crit_allocated += alloc_qty

                        allocations.append(CommodityAllocationItem(
                            depot_id=dep.depot_id,
                            incident_id=inc.incident_id,
                            commodity=commodity,
                            quantity=alloc_qty,
                            travel_time_minutes=round(t_val, 1),
                            distance_km=round(d_val, 1),
                            explanation=f"Greedy Proximity allocated {alloc_qty:.0f} units of {commodity} from nearest depot {dep.name}."
                        ))

                if rem_demand > 0:
                    total_unmet += rem_demand
                    total_p_weighted_unmet += rem_demand * inc.priority_score
                    unmet_items.append(UnmetDemandItem(
                        incident_id=inc.incident_id,
                        commodity=commodity,
                        demanded_quantity=dem_qty,
                        allocated_quantity=dem_qty - rem_demand,
                        unmet_quantity=rem_demand,
                        priority_score=inc.priority_score,
                        explanation=f"Greedy Proximity could not fulfill {rem_demand:.0f} units of {commodity}."
                    ))

        t_end = time.perf_counter()
        unmet_pct = round((total_unmet / total_demanded * 100.0) if total_demanded > 0 else 0.0, 2)
        total_usable_supply = sum(sum(d.supplies.values()) for d in depots)

        return AllocationResult(
            solver_status="FEASIBLE",
            operational_feasibility="FEASIBLE" if total_unmet == 0 else "PARTIALLY_FEASIBLE",
            allocations=allocations,
            unmet_demands=unmet_items,
            total_unmet_demand_quantity=total_unmet,
            unmet_demand_percentage=unmet_pct,
            priority_weighted_unmet_demand=round(total_p_weighted_unmet, 1),
            critical_fulfillment_percentage=round((crit_allocated / crit_demanded * 100.0) if crit_demanded > 0 else 100.0, 2),
            mean_shipment_travel_time_mins=round(sum(a.travel_time_minutes for a in allocations)/len(allocations), 1) if allocations else 0.0,
            total_travel_distance_km=round(sum(a.distance_km for a in allocations), 1),
            resource_utilization_percentage=round((total_allocated / total_usable_supply * 100.0) if total_usable_supply > 0 else 0.0, 2),
            solver_runtime_ms=round((t_end - t_start) * 1000.0, 3),
            optimality_gap=0.0,
            objective_value=0.0,
            graph_version=graph_engine.get_graph_version(),
            explanation_summary=f"Greedy Proximity baseline result. Unmet Demand: {unmet_pct}%."
        )


class FCFSAllocationEngine:
    """
    BASELINE B: First-Come-First-Served (FCFS) Allocation.
    Processes incidents strictly in chronological creation order, allocating available stock from nearest depot.
    """
    def solve(self, incidents: List[IncidentDemandInput], depots: List[DepotSupplyInput], graph_engine: RoadGraphEngine) -> AllocationResult:
        # Sort incidents strictly by creation string / index
        fcfs_incidents = sorted(incidents, key=lambda x: x.created_at_str or x.incident_id)
        greedy = GreedyProximityAllocationEngine()
        res = greedy.solve(fcfs_incidents, depots, graph_engine, sort_by_priority=False)
        res.explanation_summary = f"FCFS queue baseline result. Unmet Demand: {res.unmet_demand_percentage}%."
        return res
