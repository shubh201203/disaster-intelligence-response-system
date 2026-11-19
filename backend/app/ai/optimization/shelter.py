"""
DIRS Phase 5F-C — Shelter Evacuation Optimization Engine
Core CP-SAT mathematical optimization solver for emergency shelter evacuation assignment.
Classification: DECISION-SUPPORT OPTIMIZATION ENGINE (HUMAN-IN-THE-LOOP REQUIRED)
"""
import time
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from ortools.sat.python import cp_model

from app.ai.optimization.graph import RoadGraphEngine, haversine_distance

# --- 1. Data Structures & Input/Output Interfaces ---

DEMOGRAPHIC_GROUPS = ["GEN", "ACC", "MED", "MED_ACC"]

SEVERITY_MULTIPLIERS = {
    "CRITICAL": 5.0,
    "HIGH": 3.0,
    "MEDIUM": 2.0,
    "LOW": 1.0
}

OBJECTIVE_WEIGHTS = {
    "gamma_1": 1000.0,  # General unmet penalty
    "gamma_2": 2000.0,  # Accessible unmet penalty
    "gamma_3": 2500.0,  # Medical unmet penalty
    "gamma_4": 4000.0,  # Medical + Accessible unmet penalty
    "gamma_5": 10.0,    # Transit time penalty (per person-minute)
    "gamma_6": 1.0,     # Transit distance penalty (per person-km)
    "gamma_7": 500.0    # Shelter activation overhead
}

OBJECTIVE_SCALE = 100  # Scaling factor to preserve integer arithmetic in CP-SAT
IMPASSABLE_THRESHOLD = 10000.0  # Phase 5C reachability threshold in minutes


@dataclass
class IncidentEvacuationInput:
    incident_id: str
    title: str
    latitude: float
    longitude: float
    priority_score: float  # 0.0 to 100.0
    severity_level: str    # CRITICAL, HIGH, MEDIUM, LOW
    disaster_type: str     # FLOOD, CYCLONE, FIRE, LANDSLIDE, EARTHQUAKE
    people_affected: int   # Total affected evacuees
    evacuation_demographics: Dict[str, int] = field(default_factory=dict)
    # e.g. {"GEN": 80, "ACC": 15, "MED": 5, "MED_ACC": 0}


@dataclass
class ShelterInput:
    shelter_id: str
    name: str
    latitude: float
    longitude: float
    total_capacity: int
    current_occupancy: int = 0
    status: str = "OPEN"  # OPEN, FULL, CLOSED
    accessibility_features: bool = False  # Wheelchair / mobility ramps (A_s)
    has_medical: bool = False            # Medical triage station (M_s)
    has_food: bool = True
    has_water: bool = True
    power_available: bool = True          # Continuous electricity / generator (P_s)
    sanitation_available: bool = True     # Operational sanitation (S_s)
    disaster_compatibility: List[str] = field(default_factory=list)  # e.g. ["FLOOD", "CYCLONE"]


@dataclass
class ShelterAssignmentItem:
    incident_id: str
    shelter_id: str
    demographic_group: str
    assigned_quantity: int
    travel_time_minutes: float
    distance_km: float
    objective_contribution: float
    explanation: str


@dataclass
class ShelterUnmetItem:
    incident_id: str
    demographic_group: str
    demanded_quantity: int
    assigned_quantity: int
    unmet_quantity: int
    priority_score: float
    severity_level: str
    penalty_cost: float
    explanation: str


@dataclass
class ShelterEvacuationResult:
    solver_status: str              # OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN
    operational_feasibility: str    # FULLY_FEASIBLE, PARTIALLY_FEASIBLE, INFEASIBLE
    assignments: List[ShelterAssignmentItem]
    unmet_items: List[ShelterUnmetItem]
    total_evacuees_displaced: int
    total_evacuees_sheltered: int
    total_evacuees_unmet: int
    unmet_percentage: float
    demographic_unmet_counts: Dict[str, int]
    active_shelters_count: int
    shelter_occupancy_breakdown: Dict[str, Dict[str, Any]]
    mean_evacuation_time_mins: float
    total_evacuation_person_minutes: float
    total_evacuation_person_km: float
    objective_value: float
    objective_breakdown: Dict[str, float]
    solver_runtime_ms: float
    optimality_gap: float
    graph_version: str
    timing_breakdown: Dict[str, float] = field(default_factory=dict)
    explanation_summary: str = ""


# --- 2. Network Distance & Reachability Resolver ---

def _resolve_shelter_network_matrices(
    graph_engine: RoadGraphEngine,
    incidents: List[IncidentEvacuationInput],
    shelters: List[ShelterInput]
) -> Tuple[Dict[Tuple[str, str], bool], Dict[Tuple[str, str], float], Dict[Tuple[str, str], float]]:
    """
    Computes shortest path metrics from incidents to shelters using Phase 5C RoadGraphEngine.
    Returns: (reachability_map, travel_times_map, distances_map)
    """
    # 1. Map incidents and shelters to nearest graph nodes
    inc_nodes = {}
    for inc in incidents:
        if graph_engine.graph.has_node(inc.incident_id):
            inc_nodes[inc.incident_id] = inc.incident_id
        else:
            inc_nodes[inc.incident_id] = graph_engine.find_nearest_node(inc.latitude, inc.longitude)

    shelter_nodes = {}
    for s in shelters:
        if graph_engine.graph.has_node(s.shelter_id):
            shelter_nodes[s.shelter_id] = s.shelter_id
        else:
            shelter_nodes[s.shelter_id] = graph_engine.find_nearest_node(s.latitude, s.longitude)

    reachability: Dict[Tuple[str, str], bool] = {}
    travel_times: Dict[Tuple[str, str], float] = {}
    distances: Dict[Tuple[str, str], float] = {}

    for inc in incidents:
        u_node = inc_nodes[inc.incident_id]
        for s in shelters:
            pair = (inc.incident_id, s.shelter_id)
            v_node = shelter_nodes[s.shelter_id]

            if u_node == v_node:
                # Same location
                reachability[pair] = True
                travel_times[pair] = 1.0  # Minimum 1 minute transit
                distances[pair] = 0.1
                continue

            route = graph_engine.compute_shortest_path(u_node, v_node, algorithm="DIJKSTRA")
            if route.status == "FEASIBLE" and route.travel_time_minutes < IMPASSABLE_THRESHOLD:
                reachability[pair] = True
                travel_times[pair] = max(0.5, route.travel_time_minutes)
                distances[pair] = max(0.1, route.distance_km)
            else:
                reachability[pair] = False
                travel_times[pair] = IMPASSABLE_THRESHOLD
                distances[pair] = 999.0

    return reachability, travel_times, distances


# --- 3. Demographic & Capability Compatibility Matrix ---

def is_demographic_compatible(shelter: ShelterInput, demographic_group: str) -> bool:
    """
    Evaluates physical & medical compatibility matrix Omega_sg:
    - GEN: Any functional shelter
    - ACC: Requires accessibility_features == True (A_s)
    - MED: Requires has_medical == True and power_available == True (M_s * P_s)
    - MED_ACC: Requires accessibility_features == True and has_medical == True and power_available == True
    """
    if demographic_group == "GEN":
        return True
    elif demographic_group == "ACC":
        return bool(shelter.accessibility_features)
    elif demographic_group == "MED":
        return bool(shelter.has_medical and shelter.power_available)
    elif demographic_group == "MED_ACC":
        return bool(shelter.accessibility_features and shelter.has_medical and shelter.power_available)
    return False


def is_disaster_compatible(shelter: ShelterInput, disaster_type: str) -> bool:
    """
    Evaluates shelter hazard compatibility:
    - If shelter specifies disaster_compatibility list: incident disaster_type must be in list.
    - If shelter has empty disaster_compatibility list: accepts all disasters as safe fallback.
    """
    if not shelter.disaster_compatibility:
        return True
    return disaster_type.upper() in [d.upper() for d in shelter.disaster_compatibility]


def calculate_available_capacity(shelter: ShelterInput) -> int:
    """
    Calculates effective available capacity C_s:
    - OPEN: max(0, total_capacity - current_occupancy)
    - FULL / CLOSED: 0
    """
    if shelter.status.upper() != "OPEN":
        return 0
    return max(0, shelter.total_capacity - shelter.current_occupancy)


# --- 4. CP-SAT Shelter Evacuation Optimization Engine ---

class ShelterEvacuationEngine:
    """
    Core OR-Tools CP-SAT Shelter Evacuation Optimization Engine.
    Converts incident evacuation demands and shelter capabilities into an optimal,
    demographically-conserved evacuation assignment.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(OBJECTIVE_WEIGHTS)

    def solve(
        self,
        incidents: List[IncidentEvacuationInput],
        shelters: List[ShelterInput],
        graph_engine: RoadGraphEngine,
        solver_time_limit_sec: float = 5.0,
        random_seed: int = 42
    ) -> ShelterEvacuationResult:
        """
        Executes CP-SAT evacuation optimization with exact integer formulation.
        """
        t_total_start = time.perf_counter()

        # Handle empty inputs cleanly
        if not incidents:
            return ShelterEvacuationResult(
                solver_status="OPTIMAL",
                operational_feasibility="FULLY_FEASIBLE",
                assignments=[],
                unmet_items=[],
                total_evacuees_displaced=0,
                total_evacuees_sheltered=0,
                total_evacuees_unmet=0,
                unmet_percentage=0.0,
                demographic_unmet_counts={g: 0 for g in DEMOGRAPHIC_GROUPS},
                active_shelters_count=0,
                shelter_occupancy_breakdown={},
                mean_evacuation_time_mins=0.0,
                total_evacuation_person_minutes=0.0,
                total_evacuation_person_km=0.0,
                objective_value=0.0,
                objective_breakdown={k: 0.0 for k in ["unmet_gen", "unmet_acc", "unmet_med", "unmet_med_acc", "transit_time", "transit_dist", "activation"]},
                solver_runtime_ms=0.0,
                optimality_gap=0.0,
                graph_version=graph_engine.get_graph_version(),
                explanation_summary="No incidents provided."
            )

        # 1. Input Validation
        total_displaced = 0
        incident_demographics: Dict[str, Dict[str, int]] = {}

        for inc in incidents:
            if inc.people_affected < 0:
                raise ValueError(f"Incident {inc.incident_id} has negative people_affected ({inc.people_affected})")
            if inc.priority_score < 0:
                raise ValueError(f"Incident {inc.incident_id} has negative priority_score ({inc.priority_score})")

            # Extract demographic partition
            demo = inc.evacuation_demographics or {}
            # Verify no unknown groups or negative counts
            for g, count in demo.items():
                if g not in DEMOGRAPHIC_GROUPS:
                    raise ValueError(f"Unknown demographic group '{g}' for incident {inc.incident_id}")
                if count < 0:
                    raise ValueError(f"Negative count for group '{g}' in incident {inc.incident_id}")

            # If demographic breakdown is provided, use it; otherwise default all to GEN
            if demo:
                demo_sum = sum(demo.values())
                if demo_sum > inc.people_affected:
                    raise ValueError(
                        f"Inconsistent demographic total for incident {inc.incident_id}: "
                        f"sum ({demo_sum}) exceeds people_affected ({inc.people_affected})"
                    )
                # Remainder if any assigned to GEN
                gen_count = demo.get("GEN", 0) + max(0, inc.people_affected - demo_sum)
                parsed_demo = {
                    "GEN": gen_count,
                    "ACC": demo.get("ACC", 0),
                    "MED": demo.get("MED", 0),
                    "MED_ACC": demo.get("MED_ACC", 0)
                }
            else:
                parsed_demo = {
                    "GEN": inc.people_affected,
                    "ACC": 0,
                    "MED": 0,
                    "MED_ACC": 0
                }

            incident_demographics[inc.incident_id] = parsed_demo
            total_displaced += sum(parsed_demo.values())

        for s in shelters:
            if s.total_capacity < 0:
                raise ValueError(f"Shelter {s.shelter_id} has negative total_capacity ({s.total_capacity})")
            if s.current_occupancy < 0:
                raise ValueError(f"Shelter {s.shelter_id} has negative current_occupancy ({s.current_occupancy})")

        # 2. Phase 5C Network Distance & Reachability Matrix Retrieval
        t_matrix_start = time.perf_counter()
        reachability_mask, travel_times, distances = _resolve_shelter_network_matrices(
            graph_engine, incidents, shelters
        )
        t_matrix_end = time.perf_counter()

        # 3. Model Construction
        t_model_start = time.perf_counter()
        model = cp_model.CpModel()
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = solver_time_limit_sec
        solver.parameters.random_seed = random_seed
        solver.parameters.num_search_workers = 1  # Single-threaded deterministic solve

        # Available capacity per shelter
        available_capacities = {s.shelter_id: calculate_available_capacity(s) for s in shelters}

        # Decision Variables:
        # x_isg: integer in [0, min(p_ig, C_s)]
        x_vars: Dict[Tuple[str, str, str], cp_model.IntVar] = {}
        # x_is: total flow between incident i and shelter s
        x_pair_vars: Dict[Tuple[str, str], cp_model.IntVar] = {}
        # u_ig: unmet demand in [0, p_ig]
        u_vars: Dict[Tuple[str, str], cp_model.IntVar] = {}
        # y_s: shelter activation in {0, 1}
        y_vars: Dict[str, cp_model.IntVar] = {}

        for s in shelters:
            cap = available_capacities[s.shelter_id]
            if cap > 0:
                y_vars[s.shelter_id] = model.NewBoolVar(f"y_{s.shelter_id}")

        for inc in incidents:
            for s in shelters:
                pair = (inc.incident_id, s.shelter_id)
                cap = available_capacities[s.shelter_id]
                is_reachable = reachability_mask.get(pair, False)
                disaster_ok = is_disaster_compatible(s, inc.disaster_type)

                if cap <= 0 or not is_reachable or not disaster_ok:
                    continue

                pair_terms = []
                for g in DEMOGRAPHIC_GROUPS:
                    p_ig = incident_demographics[inc.incident_id][g]
                    if p_ig > 0 and is_demographic_compatible(s, g):
                        ub = min(p_ig, cap)
                        var_key = (inc.incident_id, s.shelter_id, g)
                        x_var = model.NewIntVar(0, ub, f"x_{inc.incident_id}_{s.shelter_id}_{g}")
                        x_vars[var_key] = x_var
                        pair_terms.append(x_var)

                if pair_terms:
                    # Aggregate flow x_is
                    x_pair_var = model.NewIntVar(0, cap, f"x_pair_{inc.incident_id}_{s.shelter_id}")
                    x_pair_vars[pair] = x_pair_var
                    model.Add(x_pair_var == sum(pair_terms))

        # Unmet Variables u_ig
        for inc in incidents:
            for g in DEMOGRAPHIC_GROUPS:
                p_ig = incident_demographics[inc.incident_id][g]
                u_key = (inc.incident_id, g)
                u_var = model.NewIntVar(0, p_ig, f"u_{inc.incident_id}_{g}")
                u_vars[u_key] = u_var

                # DEMOGRAPHIC CONSERVATION LAW: sum_s x_isg + u_ig == p_ig
                candidate_x = [
                    x_vars[(inc.incident_id, s.shelter_id, g)]
                    for s in shelters
                    if (inc.incident_id, s.shelter_id, g) in x_vars
                ]
                if candidate_x:
                    model.Add(sum(candidate_x) + u_var == p_ig)
                else:
                    # Incompatible or unreachable: all demand is unmet
                    model.Add(u_var == p_ig)

        # SHELTER CAPACITY CONSTRAINT: sum_{i, g} x_isg <= C_s * y_s
        for s in shelters:
            cap = available_capacities[s.shelter_id]
            if cap > 0 and s.shelter_id in y_vars:
                shelter_x = [
                    x_vars[(inc.incident_id, s.shelter_id, g)]
                    for inc in incidents
                    for g in DEMOGRAPHIC_GROUPS
                    if (inc.incident_id, s.shelter_id, g) in x_vars
                ]
                if shelter_x:
                    model.Add(sum(shelter_x) <= cap * y_vars[s.shelter_id])
                    # Shelter activation reification: y_s <= sum x
                    model.Add(y_vars[s.shelter_id] <= sum(shelter_x))
                else:
                    model.Add(y_vars[s.shelter_id] == 0)

        # 4. Multi-Objective Cost Function Construction
        # Scale all objective coefficients by OBJECTIVE_SCALE (100) for integer CP-SAT
        objective_terms = []

        gamma_1 = self.weights["gamma_1"]
        gamma_2 = self.weights["gamma_2"]
        gamma_3 = self.weights["gamma_3"]
        gamma_4 = self.weights["gamma_4"]
        gamma_5 = self.weights["gamma_5"]
        gamma_6 = self.weights["gamma_6"]
        gamma_7 = self.weights["gamma_7"]

        gamma_map = {
            "GEN": gamma_1,
            "ACC": gamma_2,
            "MED": gamma_3,
            "MED_ACC": gamma_4
        }

        # 4a. Unmet Demand Penalties
        for inc in incidents:
            sev_multiplier = SEVERITY_MULTIPLIERS.get(inc.severity_level.upper(), 2.0)
            priority_weight = max(1.0, inc.priority_score)

            for g in DEMOGRAPHIC_GROUPS:
                u_key = (inc.incident_id, g)
                base_coeff = sev_multiplier * priority_weight * gamma_map[g]
                scaled_coeff = int(round(base_coeff * OBJECTIVE_SCALE))
                objective_terms.append(scaled_coeff * u_vars[u_key])

        # 4b. Transit Time & Distance Penalties
        for pair, x_pair_var in x_pair_vars.items():
            t_min = travel_times.get(pair, 0.0)
            d_km = distances.get(pair, 0.0)
            transit_cost_per_person = (gamma_5 * t_min) + (gamma_6 * d_km)
            scaled_transit_coeff = int(round(transit_cost_per_person * OBJECTIVE_SCALE))
            objective_terms.append(scaled_transit_coeff * x_pair_var)

        # 4c. Shelter Activation Overhead
        for s_id, y_var in y_vars.items():
            scaled_activation_coeff = int(round(gamma_7 * OBJECTIVE_SCALE))
            objective_terms.append(scaled_activation_coeff * y_var)

        model.Minimize(sum(objective_terms))
        t_model_end = time.perf_counter()

        # 5. Solve CP-SAT Model
        t_solve_start = time.perf_counter()
        status_code = solver.Solve(model)
        t_solve_end = time.perf_counter()

        # Map CP-SAT solver status
        status_map = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "UNKNOWN",
            cp_model.UNKNOWN: "UNKNOWN"
        }
        solver_status = status_map.get(status_code, "UNKNOWN")

        # 6. Extract Solution & Metrics
        t_extract_start = time.perf_counter()
        assignments: List[ShelterAssignmentItem] = []
        unmet_items: List[ShelterUnmetItem] = []

        total_sheltered = 0
        total_unmet = 0
        demographic_unmet: Dict[str, int] = {g: 0 for g in DEMOGRAPHIC_GROUPS}
        active_shelters: Set[str] = set()
        shelter_intake: Dict[str, Dict[str, Any]] = {
            s.shelter_id: {
                "name": s.name,
                "total_capacity": s.total_capacity,
                "pre_occupancy": s.current_occupancy,
                "available_capacity": available_capacities[s.shelter_id],
                "assigned_total": 0,
                "demographic_breakdown": {g: 0 for g in DEMOGRAPHIC_GROUPS},
                "remaining_capacity": available_capacities[s.shelter_id],
                "status": s.status
            }
            for s in shelters
        }

        total_person_minutes = 0.0
        total_person_km = 0.0

        if solver_status in ("OPTIMAL", "FEASIBLE"):
            # Extract assignments
            for var_key, x_var in x_vars.items():
                qty = int(solver.Value(x_var))
                if qty > 0:
                    inc_id, s_id, g = var_key
                    t_min = travel_times.get((inc_id, s_id), 0.0)
                    d_km = distances.get((inc_id, s_id), 0.0)
                    pair_cost = (gamma_5 * t_min + gamma_6 * d_km) * qty

                    assignments.append(ShelterAssignmentItem(
                        incident_id=inc_id,
                        shelter_id=s_id,
                        demographic_group=g,
                        assigned_quantity=qty,
                        travel_time_minutes=t_min,
                        distance_km=d_km,
                        objective_contribution=pair_cost,
                        explanation=f"Assigned {qty} {g} evacuees from {inc_id} to {s_id} ({t_min:.1f} min travel)."
                    ))
                    total_sheltered += qty
                    total_person_minutes += qty * t_min
                    total_person_km += qty * d_km
                    active_shelters.add(s_id)
                    shelter_intake[s_id]["assigned_total"] += qty
                    shelter_intake[s_id]["demographic_breakdown"][g] += qty
                    shelter_intake[s_id]["remaining_capacity"] -= qty

            # Extract unmet demands
            for inc in incidents:
                sev_multiplier = SEVERITY_MULTIPLIERS.get(inc.severity_level.upper(), 2.0)
                priority_weight = max(1.0, inc.priority_score)

                for g in DEMOGRAPHIC_GROUPS:
                    u_key = (inc.incident_id, g)
                    unmet_qty = int(solver.Value(u_vars[u_key]))
                    demanded_qty = incident_demographics[inc.incident_id][g]
                    assigned_qty = demanded_qty - unmet_qty

                    if unmet_qty > 0:
                        penalty = sev_multiplier * priority_weight * gamma_map[g] * unmet_qty
                        unmet_items.append(ShelterUnmetItem(
                            incident_id=inc.incident_id,
                            demographic_group=g,
                            demanded_quantity=demanded_qty,
                            assigned_quantity=assigned_qty,
                            unmet_quantity=unmet_qty,
                            priority_score=inc.priority_score,
                            severity_level=inc.severity_level,
                            penalty_cost=round(penalty, 2),
                            explanation=f"{unmet_qty}/{demanded_qty} {g} evacuees unmet at {inc.incident_id} due to regional shelter/reachability constraints."
                        ))
                        total_unmet += unmet_qty
                        demographic_unmet[g] += unmet_qty
        else:
            # All demand unmet if solver fails
            for inc in incidents:
                sev_multiplier = SEVERITY_MULTIPLIERS.get(inc.severity_level.upper(), 2.0)
                priority_weight = max(1.0, inc.priority_score)
                for g in DEMOGRAPHIC_GROUPS:
                    demanded_qty = incident_demographics[inc.incident_id][g]
                    if demanded_qty > 0:
                        penalty = sev_multiplier * priority_weight * gamma_map[g] * demanded_qty
                        unmet_items.append(ShelterUnmetItem(
                            incident_id=inc.incident_id,
                            demographic_group=g,
                            demanded_quantity=demanded_qty,
                            assigned_quantity=0,
                            unmet_quantity=demanded_qty,
                            priority_score=inc.priority_score,
                            severity_level=inc.severity_level,
                            penalty_cost=round(penalty, 2),
                            explanation=f"Solver returned {solver_status}. Complete demand unmet."
                        ))
                        total_unmet += demanded_qty
                        demographic_unmet[g] += demanded_qty

        # Operational Feasibility Classification
        if total_unmet == 0 and total_displaced > 0:
            operational_feasibility = "FULLY_FEASIBLE"
        elif total_sheltered > 0 and total_unmet > 0:
            operational_feasibility = "PARTIALLY_FEASIBLE"
        else:
            operational_feasibility = "INFEASIBLE"

        # Independent Objective Reconstruction & Breakdown
        obj_breakdown = self.reconstruct_objective(
            incidents=incidents,
            incident_demographics=incident_demographics,
            assignments=assignments,
            unmet_items=unmet_items,
            active_shelters=active_shelters
        )
        independent_obj_value = sum(obj_breakdown.values())

        reported_obj = (
            solver.ObjectiveValue() / float(OBJECTIVE_SCALE)
            if solver_status in ("OPTIMAL", "FEASIBLE")
            else independent_obj_value
        )

        unmet_pct = (total_unmet / total_displaced * 100.0) if total_displaced > 0 else 0.0
        mean_time = (total_person_minutes / total_sheltered) if total_sheltered > 0 else 0.0

        t_extract_end = time.perf_counter()
        t_total_end = time.perf_counter()

        timing_breakdown = {
            "matrix_retrieval_ms": round((t_matrix_end - t_matrix_start) * 1000.0, 2),
            "model_construction_ms": round((t_model_end - t_model_start) * 1000.0, 2),
            "solver_ms": round((t_solve_end - t_solve_start) * 1000.0, 2),
            "extraction_ms": round((t_extract_end - t_extract_start) * 1000.0, 2),
            "total_ms": round((t_total_end - t_total_start) * 1000.0, 2)
        }

        explanation_summary = (
            f"Shelter evacuation solve completed in {timing_breakdown['total_ms']:.1f}ms with status {solver_status} "
            f"({operational_feasibility}). Displaced: {total_displaced}, Sheltered: {total_sheltered}, "
            f"Unmet: {total_unmet} ({unmet_pct:.1f}%). Active shelters: {len(active_shelters)}/{len(shelters)}. "
            f"Mean evacuation travel time: {mean_time:.1f} minutes."
        )

        return ShelterEvacuationResult(
            solver_status=solver_status,
            operational_feasibility=operational_feasibility,
            assignments=assignments,
            unmet_items=unmet_items,
            total_evacuees_displaced=total_displaced,
            total_evacuees_sheltered=total_sheltered,
            total_evacuees_unmet=total_unmet,
            unmet_percentage=round(unmet_pct, 2),
            demographic_unmet_counts=demographic_unmet,
            active_shelters_count=len(active_shelters),
            shelter_occupancy_breakdown=shelter_intake,
            mean_evacuation_time_mins=round(mean_time, 2),
            total_evacuation_person_minutes=round(total_person_minutes, 2),
            total_evacuation_person_km=round(total_person_km, 2),
            objective_value=round(reported_obj, 2),
            objective_breakdown={k: round(v, 2) for k, v in obj_breakdown.items()},
            solver_runtime_ms=timing_breakdown["solver_ms"],
            optimality_gap=0.0 if solver_status == "OPTIMAL" else -1.0,
            graph_version=graph_engine.get_graph_version(),
            timing_breakdown=timing_breakdown,
            explanation_summary=explanation_summary
        )

    def reconstruct_objective(
        self,
        incidents: List[IncidentEvacuationInput],
        incident_demographics: Dict[str, Dict[str, int]],
        assignments: List[ShelterAssignmentItem],
        unmet_items: List[ShelterUnmetItem],
        active_shelters: Set[str]
    ) -> Dict[str, float]:
        """
        Independently recomputes each component of the shelter evacuation objective:
        Z = Z_unmet_gen + Z_unmet_acc + Z_unmet_med + Z_unmet_med_acc + Z_transit_time + Z_transit_dist + Z_activation
        """
        gamma_1 = self.weights["gamma_1"]
        gamma_2 = self.weights["gamma_2"]
        gamma_3 = self.weights["gamma_3"]
        gamma_4 = self.weights["gamma_4"]
        gamma_5 = self.weights["gamma_5"]
        gamma_6 = self.weights["gamma_6"]
        gamma_7 = self.weights["gamma_7"]

        gamma_map = {
            "GEN": gamma_1,
            "ACC": gamma_2,
            "MED": gamma_3,
            "MED_ACC": gamma_4
        }

        inc_map = {inc.incident_id: inc for inc in incidents}

        breakdown = {
            "unmet_gen": 0.0,
            "unmet_acc": 0.0,
            "unmet_med": 0.0,
            "unmet_med_acc": 0.0,
            "transit_time": 0.0,
            "transit_dist": 0.0,
            "activation": len(active_shelters) * gamma_7
        }

        # Unmet breakdown
        for u in unmet_items:
            inc = inc_map.get(u.incident_id)
            if inc:
                sev_mult = SEVERITY_MULTIPLIERS.get(inc.severity_level.upper(), 2.0)
                p_wt = max(1.0, inc.priority_score)
                penalty = sev_mult * p_wt * gamma_map[u.demographic_group] * u.unmet_quantity
                if u.demographic_group == "GEN":
                    breakdown["unmet_gen"] += penalty
                elif u.demographic_group == "ACC":
                    breakdown["unmet_acc"] += penalty
                elif u.demographic_group == "MED":
                    breakdown["unmet_med"] += penalty
                elif u.demographic_group == "MED_ACC":
                    breakdown["unmet_med_acc"] += penalty

        # Transit breakdown
        for a in assignments:
            breakdown["transit_time"] += gamma_5 * a.travel_time_minutes * a.assigned_quantity
            breakdown["transit_dist"] += gamma_6 * a.distance_km * a.assigned_quantity

        return breakdown


# --- 5. Baseline Solvers for Benchmark Comparison ---

class GreedyProximityShelterSolver:
    """
    Baseline A: Nearest Feasible Shelter / Greedy Proximity.
    Iterates through incident demographic groups in order of urgency (priority score descending,
    vulnerable groups first), assigning evacuees greedily to the nearest reachable, compatible,
    available shelter.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(OBJECTIVE_WEIGHTS)

    def solve(
        self,
        incidents: List[IncidentEvacuationInput],
        shelters: List[ShelterInput],
        graph_engine: RoadGraphEngine
    ) -> ShelterEvacuationResult:
        reachability_mask, travel_times, distances = _resolve_shelter_network_matrices(
            graph_engine, incidents, shelters
        )

        rem_capacity = {s.shelter_id: calculate_available_capacity(s) for s in shelters}
        active_shelters: Set[str] = set()
        assignments: List[ShelterAssignmentItem] = []
        unmet_items: List[ShelterUnmetItem] = []

        # Sort incidents by urgency: (priority_score * severity) descending
        def urgency_key(inc: IncidentEvacuationInput):
            return inc.priority_score * SEVERITY_MULTIPLIERS.get(inc.severity_level.upper(), 2.0)

        sorted_incidents = sorted(incidents, key=urgency_key, reverse=True)

        total_displaced = 0
        total_sheltered = 0
        total_unmet = 0
        demographic_unmet = {g: 0 for g in DEMOGRAPHIC_GROUPS}
        total_person_minutes = 0.0
        total_person_km = 0.0

        # Demographic priority ordering: MED_ACC -> MED -> ACC -> GEN
        demo_priority = ["MED_ACC", "MED", "ACC", "GEN"]

        incident_demographics = {}

        for inc in sorted_incidents:
            demo = inc.evacuation_demographics or {}
            demo_sum = sum(demo.values())
            gen_count = demo.get("GEN", 0) + max(0, inc.people_affected - demo_sum)
            parsed_demo = {
                "GEN": gen_count,
                "ACC": demo.get("ACC", 0),
                "MED": demo.get("MED", 0),
                "MED_ACC": demo.get("MED_ACC", 0)
            }
            incident_demographics[inc.incident_id] = parsed_demo
            total_displaced += sum(parsed_demo.values())

            # Sort candidate shelters by travel time from this incident
            candidate_shelters = sorted(
                shelters,
                key=lambda s: travel_times.get((inc.incident_id, s.shelter_id), IMPASSABLE_THRESHOLD)
            )

            for g in demo_priority:
                demand_remaining = parsed_demo[g]
                if demand_remaining <= 0:
                    continue

                for s in candidate_shelters:
                    if demand_remaining <= 0:
                        break

                    pair = (inc.incident_id, s.shelter_id)
                    if (
                        rem_capacity[s.shelter_id] > 0
                        and reachability_mask.get(pair, False)
                        and is_disaster_compatible(s, inc.disaster_type)
                        and is_demographic_compatible(s, g)
                    ):
                        assign_qty = min(demand_remaining, rem_capacity[s.shelter_id])
                        rem_capacity[s.shelter_id] -= assign_qty
                        demand_remaining -= assign_qty
                        total_sheltered += assign_qty
                        active_shelters.add(s.shelter_id)

                        t_min = travel_times[pair]
                        d_km = distances[pair]
                        total_person_minutes += assign_qty * t_min
                        total_person_km += assign_qty * d_km

                        cost = (self.weights["gamma_5"] * t_min + self.weights["gamma_6"] * d_km) * assign_qty
                        assignments.append(ShelterAssignmentItem(
                            incident_id=inc.incident_id,
                            shelter_id=s.shelter_id,
                            demographic_group=g,
                            assigned_quantity=assign_qty,
                            travel_time_minutes=round(t_min, 2),
                            distance_km=round(d_km, 2),
                            objective_contribution=round(cost, 2),
                            explanation=f"Greedy proximity assigned {assign_qty} {g} to {s.shelter_id} ({t_min:.1f} min)."
                        ))

                if demand_remaining > 0:
                    total_unmet += demand_remaining
                    demographic_unmet[g] += demand_remaining
                    sev_mult = SEVERITY_MULTIPLIERS.get(inc.severity_level.upper(), 2.0)
                    p_wt = max(1.0, inc.priority_score)
                    gamma_val = self.weights[f"gamma_{demo_priority.index(g)+1}"]
                    # gamma_1=GEN, gamma_2=ACC, gamma_3=MED, gamma_4=MED_ACC
                    g_gamma = {
                        "GEN": self.weights["gamma_1"],
                        "ACC": self.weights["gamma_2"],
                        "MED": self.weights["gamma_3"],
                        "MED_ACC": self.weights["gamma_4"]
                    }[g]
                    penalty = sev_mult * p_wt * g_gamma * demand_remaining
                    unmet_items.append(ShelterUnmetItem(
                        incident_id=inc.incident_id,
                        demographic_group=g,
                        demanded_quantity=parsed_demo[g],
                        assigned_quantity=parsed_demo[g] - demand_remaining,
                        unmet_quantity=demand_remaining,
                        priority_score=inc.priority_score,
                        severity_level=inc.severity_level,
                        penalty_cost=round(penalty, 2),
                        explanation=f"Greedy baseline exhausted compatible capacity for {g} at {inc.incident_id}."
                    ))

        # Operational feasibility
        if total_unmet == 0 and total_displaced > 0:
            op_feas = "FULLY_FEASIBLE"
        elif total_sheltered > 0:
            op_feas = "PARTIALLY_FEASIBLE"
        else:
            op_feas = "INFEASIBLE"

        # Reconstruct objective
        engine = ShelterEvacuationEngine(weights=self.weights)
        obj_breakdown = engine.reconstruct_objective(
            incidents=incidents,
            incident_demographics=incident_demographics,
            assignments=assignments,
            unmet_items=unmet_items,
            active_shelters=active_shelters
        )

        return ShelterEvacuationResult(
            solver_status="OPTIMAL",
            operational_feasibility=op_feas,
            assignments=assignments,
            unmet_items=unmet_items,
            total_evacuees_displaced=total_displaced,
            total_evacuees_sheltered=total_sheltered,
            total_evacuees_unmet=total_unmet,
            unmet_percentage=round((total_unmet / total_displaced * 100.0) if total_displaced > 0 else 0.0, 2),
            demographic_unmet_counts=demographic_unmet,
            active_shelters_count=len(active_shelters),
            shelter_occupancy_breakdown={},
            mean_evacuation_time_mins=round((total_person_minutes / total_sheltered) if total_sheltered > 0 else 0.0, 2),
            total_evacuation_person_minutes=round(total_person_minutes, 2),
            total_evacuation_person_km=round(total_person_km, 2),
            objective_value=round(sum(obj_breakdown.values()), 2),
            objective_breakdown={k: round(v, 2) for k, v in obj_breakdown.items()},
            solver_runtime_ms=0.0,
            optimality_gap=-1.0,
            graph_version=graph_engine.get_graph_version(),
            explanation_summary=f"Greedy proximity completed: sheltered {total_sheltered}/{total_displaced}."
        )


class FCFSShelterSolver:
    """
    Baseline B: First-Come First-Served (FCFS / Incident Creation Sequence).
    Processes incidents strictly in arrival/input sequence without priority reordering,
    assigning each demographic group to the first available compatible shelter.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(OBJECTIVE_WEIGHTS)

    def solve(
        self,
        incidents: List[IncidentEvacuationInput],
        shelters: List[ShelterInput],
        graph_engine: RoadGraphEngine
    ) -> ShelterEvacuationResult:
        reachability_mask, travel_times, distances = _resolve_shelter_network_matrices(
            graph_engine, incidents, shelters
        )

        rem_capacity = {s.shelter_id: calculate_available_capacity(s) for s in shelters}
        active_shelters: Set[str] = set()
        assignments: List[ShelterAssignmentItem] = []
        unmet_items: List[ShelterUnmetItem] = []

        total_displaced = 0
        total_sheltered = 0
        total_unmet = 0
        demographic_unmet = {g: 0 for g in DEMOGRAPHIC_GROUPS}
        total_person_minutes = 0.0
        total_person_km = 0.0

        incident_demographics = {}

        # Natural arrival sequence
        for inc in incidents:
            demo = inc.evacuation_demographics or {}
            demo_sum = sum(demo.values())
            gen_count = demo.get("GEN", 0) + max(0, inc.people_affected - demo_sum)
            parsed_demo = {
                "GEN": gen_count,
                "ACC": demo.get("ACC", 0),
                "MED": demo.get("MED", 0),
                "MED_ACC": demo.get("MED_ACC", 0)
            }
            incident_demographics[inc.incident_id] = parsed_demo
            total_displaced += sum(parsed_demo.values())

            for g in DEMOGRAPHIC_GROUPS:
                demand_remaining = parsed_demo[g]
                if demand_remaining <= 0:
                    continue

                for s in shelters:
                    if demand_remaining <= 0:
                        break

                    pair = (inc.incident_id, s.shelter_id)
                    if (
                        rem_capacity[s.shelter_id] > 0
                        and reachability_mask.get(pair, False)
                        and is_disaster_compatible(s, inc.disaster_type)
                        and is_demographic_compatible(s, g)
                    ):
                        assign_qty = min(demand_remaining, rem_capacity[s.shelter_id])
                        rem_capacity[s.shelter_id] -= assign_qty
                        demand_remaining -= assign_qty
                        total_sheltered += assign_qty
                        active_shelters.add(s.shelter_id)

                        t_min = travel_times[pair]
                        d_km = distances[pair]
                        total_person_minutes += assign_qty * t_min
                        total_person_km += assign_qty * d_km

                        cost = (self.weights["gamma_5"] * t_min + self.weights["gamma_6"] * d_km) * assign_qty
                        assignments.append(ShelterAssignmentItem(
                            incident_id=inc.incident_id,
                            shelter_id=s.shelter_id,
                            demographic_group=g,
                            assigned_quantity=assign_qty,
                            travel_time_minutes=round(t_min, 2),
                            distance_km=round(d_km, 2),
                            objective_contribution=round(cost, 2),
                            explanation=f"FCFS assigned {assign_qty} {g} to {s.shelter_id}."
                        ))

                if demand_remaining > 0:
                    total_unmet += demand_remaining
                    demographic_unmet[g] += demand_remaining
                    sev_mult = SEVERITY_MULTIPLIERS.get(inc.severity_level.upper(), 2.0)
                    p_wt = max(1.0, inc.priority_score)
                    g_gamma = {
                        "GEN": self.weights["gamma_1"],
                        "ACC": self.weights["gamma_2"],
                        "MED": self.weights["gamma_3"],
                        "MED_ACC": self.weights["gamma_4"]
                    }[g]
                    penalty = sev_mult * p_wt * g_gamma * demand_remaining
                    unmet_items.append(ShelterUnmetItem(
                        incident_id=inc.incident_id,
                        demographic_group=g,
                        demanded_quantity=parsed_demo[g],
                        assigned_quantity=parsed_demo[g] - demand_remaining,
                        unmet_quantity=demand_remaining,
                        priority_score=inc.priority_score,
                        severity_level=inc.severity_level,
                        penalty_cost=round(penalty, 2),
                        explanation=f"FCFS exhausted capacity for {g} at {inc.incident_id}."
                    ))

        # Operational feasibility
        if total_unmet == 0 and total_displaced > 0:
            op_feas = "FULLY_FEASIBLE"
        elif total_sheltered > 0:
            op_feas = "PARTIALLY_FEASIBLE"
        else:
            op_feas = "INFEASIBLE"

        # Reconstruct objective
        engine = ShelterEvacuationEngine(weights=self.weights)
        obj_breakdown = engine.reconstruct_objective(
            incidents=incidents,
            incident_demographics=incident_demographics,
            assignments=assignments,
            unmet_items=unmet_items,
            active_shelters=active_shelters
        )

        return ShelterEvacuationResult(
            solver_status="OPTIMAL",
            operational_feasibility=op_feas,
            assignments=assignments,
            unmet_items=unmet_items,
            total_evacuees_displaced=total_displaced,
            total_evacuees_sheltered=total_sheltered,
            total_evacuees_unmet=total_unmet,
            unmet_percentage=round((total_unmet / total_displaced * 100.0) if total_displaced > 0 else 0.0, 2),
            demographic_unmet_counts=demographic_unmet,
            active_shelters_count=len(active_shelters),
            shelter_occupancy_breakdown={},
            mean_evacuation_time_mins=round((total_person_minutes / total_sheltered) if total_sheltered > 0 else 0.0, 2),
            total_evacuation_person_minutes=round(total_person_minutes, 2),
            total_evacuation_person_km=round(total_person_km, 2),
            objective_value=round(sum(obj_breakdown.values()), 2),
            objective_breakdown={k: round(v, 2) for k, v in obj_breakdown.items()},
            solver_runtime_ms=0.0,
            optimality_gap=-1.0,
            graph_version=graph_engine.get_graph_version(),
            explanation_summary=f"FCFS completed: sheltered {total_sheltered}/{total_displaced}."
        )


# --- 6. Brute-Force Independent Reference Solver ---

class BruteForceShelterSolver:
    """
    Exhaustive brute-force search solver for small benchmark instances.
    Independently verifies the global optimality of CP-SAT without reproducing solver logic.
    Only applicable for small test instances (<= 40 evacuees, <= 3 shelters).
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(OBJECTIVE_WEIGHTS)

    def solve(
        self,
        incidents: List[IncidentEvacuationInput],
        shelters: List[ShelterInput],
        graph_engine: RoadGraphEngine
    ) -> Tuple[float, Dict[Tuple[str, str, str], int]]:
        """
        Exhaustively iterates over all feasible integer assignment combinations,
        evaluates the exact mathematical objective, and returns (best_objective, best_assignment_map).
        """
        reachability_mask, travel_times, distances = _resolve_shelter_network_matrices(
            graph_engine, incidents, shelters
        )

        available_capacities = {s.shelter_id: calculate_available_capacity(s) for s in shelters}

        # Build list of demand units to allocate
        # Each item is (incident_id, demographic_group, unit_index, priority_weight, sev_multiplier)
        demand_items = []
        for inc in incidents:
            sev_mult = SEVERITY_MULTIPLIERS.get(inc.severity_level.upper(), 2.0)
            p_wt = max(1.0, inc.priority_score)
            demo = inc.evacuation_demographics or {}
            demo_sum = sum(demo.values())
            gen_count = demo.get("GEN", 0) + max(0, inc.people_affected - demo_sum)
            parsed_demo = {
                "GEN": gen_count,
                "ACC": demo.get("ACC", 0),
                "MED": demo.get("MED", 0),
                "MED_ACC": demo.get("MED_ACC", 0)
            }
            for g, count in parsed_demo.items():
                for idx in range(count):
                    demand_items.append((inc.incident_id, g, p_wt, sev_mult, inc.disaster_type))

        shelter_ids = [s.shelter_id for s in shelters]
        # Option per demand item: assign to shelter_id, or "UNMET"
        best_cost = float("inf")
        best_allocations: Dict[Tuple[str, str, str], int] = {}

        gamma_map = {
            "GEN": self.weights["gamma_1"],
            "ACC": self.weights["gamma_2"],
            "MED": self.weights["gamma_3"],
            "MED_ACC": self.weights["gamma_4"]
        }
        gamma_5 = self.weights["gamma_5"]
        gamma_6 = self.weights["gamma_6"]
        gamma_7 = self.weights["gamma_7"]

        shelter_map = {s.shelter_id: s for s in shelters}

        # Recursive search over demand items
        def backtrack(item_idx: int, current_caps: Dict[str, int], current_allocs: Dict[Tuple[str, str, str], int]):
            nonlocal best_cost, best_allocations

            if item_idx == len(demand_items):
                # Evaluate full objective
                active_s = {s_id for (inc_id, s_id, g), qty in current_allocs.items() if qty > 0 and s_id != "UNMET"}
                cost = len(active_s) * gamma_7

                for (inc_id, s_id, g), qty in current_allocs.items():
                    if qty <= 0:
                        continue
                    if s_id == "UNMET":
                        # Find priority and severity
                        inc = next(i for i in incidents if i.incident_id == inc_id)
                        sev_mult = SEVERITY_MULTIPLIERS.get(inc.severity_level.upper(), 2.0)
                        p_wt = max(1.0, inc.priority_score)
                        cost += sev_mult * p_wt * gamma_map[g] * qty
                    else:
                        t_min = travel_times.get((inc_id, s_id), 0.0)
                        d_km = distances.get((inc_id, s_id), 0.0)
                        cost += (gamma_5 * t_min + gamma_6 * d_km) * qty

                if cost < best_cost:
                    best_cost = cost
                    best_allocations = dict(current_allocs)
                return

            inc_id, g, p_wt, sev_mult, disaster_type = demand_items[item_idx]

            # Try candidate shelters
            for s_id in shelter_ids:
                s = shelter_map[s_id]
                pair = (inc_id, s_id)
                if (
                    current_caps[s_id] > 0
                    and reachability_mask.get(pair, False)
                    and is_disaster_compatible(s, disaster_type)
                    and is_demographic_compatible(s, g)
                ):
                    current_caps[s_id] -= 1
                    key = (inc_id, s_id, g)
                    current_allocs[key] = current_allocs.get(key, 0) + 1

                    backtrack(item_idx + 1, current_caps, current_allocs)

                    current_allocs[key] -= 1
                    current_caps[s_id] += 1

            # Try leaving unmet
            unmet_key = (inc_id, "UNMET", g)
            current_allocs[unmet_key] = current_allocs.get(unmet_key, 0) + 1
            backtrack(item_idx + 1, current_caps, current_allocs)
            current_allocs[unmet_key] -= 1

        initial_caps = dict(available_capacities)
        backtrack(0, initial_caps, {})

        return round(best_cost, 2), best_allocations
