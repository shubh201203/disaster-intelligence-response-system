"""
DIRS Phase 5F-D — Volunteer Assignment Optimization Engine
Core CP-SAT mathematical optimization solver for emergency volunteer and first-responder dispatch.
Classification: DECISION-SUPPORT OPTIMIZATION ENGINE (HUMAN-IN-THE-LOOP REQUIRED)
"""
import time
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from ortools.sat.python import cp_model

from app.ai.optimization.graph import RoadGraphEngine, haversine_distance

# --- 1. Constants & Configurations ---

SKILL_CATEGORIES = ["MEDICAL", "RESCUE", "LOGISTICS", "GENERAL"]

SEVERITY_MULTIPLIERS = {
    "CRITICAL": 5.0,
    "HIGH": 3.0,
    "MEDIUM": 2.0,
    "LOW": 1.0
}

# Approved Phase 5F-D Objective Weights
OBJECTIVE_WEIGHTS = {
    "lambda_1": 1000.0,  # Unmet task demand penalty
    "lambda_2": 1500.0,  # Medical unmet surcharge (effective medical penalty = 1000 + 1500 = 2500)
    "lambda_3": 10.0,    # Transit time penalty (per minute)
    "lambda_4": 1.0,     # Transit distance penalty (per km)
    "lambda_5": 50.0     # Volunteer deployment overhead (per deployed volunteer-shift)
}

OBJECTIVE_SCALE = 100  # Integer scale factor for CP-SAT fractional terms
IMPASSABLE_THRESHOLD = 10000.0  # Phase 5C graph threshold for severed/unreachable arcs


# --- 2. Input / Output Dataclasses ---

@dataclass
class VolunteerInput:
    volunteer_id: str
    name: str
    latitude: float
    longitude: float
    skill_category: str = "GENERAL"  # MEDICAL, RESCUE, LOGISTICS, GENERAL
    skills: List[str] = field(default_factory=list)  # e.g. ["First Aid", "Water Rescue"]
    medical_certified: bool = False
    verification_status: str = "VERIFIED"  # VERIFIED, PENDING, REJECTED
    is_available: bool = True
    assignment_status: str = "UNASSIGNED"  # UNASSIGNED, ASSIGNED, ON_MISSION
    max_shift_hours: float = 8.0  # W_v^max
    max_travel_time_mins: float = 45.0  # tau_v^max
    shift_availability: List[str] = field(default_factory=list)  # e.g. ["SHIFT_1"], empty = all shifts


@dataclass
class IncidentTaskInput:
    incident_id: str
    title: str
    latitude: float
    longitude: float
    priority_score: float = 50.0  # 0.0 to 100.0
    severity_level: str = "MEDIUM"  # CRITICAL, HIGH, MEDIUM, LOW
    required_skills: Dict[str, int] = field(default_factory=dict)
    # e.g. {"MEDICAL": 2, "RESCUE": 1, "GENERAL": 3, "LOGISTICS": 1} (d_ikt)
    shifts: List[str] = field(default_factory=lambda: ["SHIFT_1"])
    task_durations: Dict[str, float] = field(default_factory=lambda: {"SHIFT_1": 4.0})
    # mission duration in hours (h_ikt)


@dataclass
class VolunteerAssignmentItem:
    volunteer_id: str
    volunteer_name: str
    incident_id: str
    skill_category: str
    shift_id: str
    transit_time_minutes: float
    transit_distance_km: float
    task_duration_hours: float
    objective_contribution: float
    status: str = "PROPOSED"


@dataclass
class VolunteerUnmetItem:
    incident_id: str
    skill_category: str
    shift_id: str
    unmet_quantity: int
    penalty_contribution: float


@dataclass
class VolunteerAssignmentResult:
    solver_status: str  # OPTIMAL, FEASIBLE, INFEASIBLE
    operational_feasibility: str  # FULLY_FEASIBLE, PARTIALLY_FEASIBLE, INFEASIBLE
    assignments: List[VolunteerAssignmentItem]
    unmet_items: List[VolunteerUnmetItem]
    total_tasks_demanded: int
    total_tasks_assigned: int
    total_tasks_unmet: int
    unmet_percentage: float
    skill_unmet_counts: Dict[str, int]
    deployed_volunteers_count: int
    mean_transit_time_mins: float
    total_transit_minutes: float
    total_transit_km: float
    objective_value: float
    objective_breakdown: Dict[str, float]
    solver_runtime_ms: float
    optimality_gap: float
    graph_version: str
    explanation_summary: str


# --- 3. Feasibility Helpers ---

def is_volunteer_operationally_eligible(v: VolunteerInput) -> bool:
    """
    Checks whether a volunteer satisfies basic verification and operational status:
    - verification_status == 'VERIFIED' (E_v = 1)
    - is_available == True
    - assignment_status == 'UNASSIGNED'
    """
    if v.verification_status.upper() != "VERIFIED":
        return False
    if not v.is_available:
        return False
    if v.assignment_status.upper() != "UNASSIGNED":
        return False
    return True


def can_volunteer_satisfy_skill(v: VolunteerInput, skill: str) -> bool:
    """
    Evaluates skill qualification S_vk:
    - MEDICAL: Requires medical_certified == True (hard prerequisite)
    - RESCUE: Requires skill_category == 'RESCUE' or documented rescue skill
    - LOGISTICS: Requires skill_category == 'LOGISTICS' or documented logistics skill
    - GENERAL: Any verified volunteer is qualified
    """
    skill_upper = skill.upper()
    v_cat = v.skill_category.upper()
    skills_lower = [s.lower() for s in v.skills]

    if skill_upper == "MEDICAL":
        # Strictly requires medical_certified == True
        return bool(v.medical_certified)

    if skill_upper == "RESCUE":
        if v_cat == "RESCUE":
            return True
        return any("rescue" in s for s in skills_lower)

    if skill_upper == "LOGISTICS":
        if v_cat == "LOGISTICS":
            return True
        return any("logistic" in s or "supply" in s or "driver" in s for s in skills_lower)

    if skill_upper == "GENERAL":
        # General relief is open to all qualified volunteers
        return True

    return False


def is_volunteer_available_for_shift(v: VolunteerInput, shift_id: str) -> bool:
    """
    Checks shift availability A_vt:
    - If shift_availability is empty, default available for all shifts.
    - Otherwise, shift_id must be in shift_availability.
    """
    if not v.shift_availability:
        return True
    return shift_id in v.shift_availability


def _resolve_volunteer_network_matrices(
    graph_engine: RoadGraphEngine,
    volunteers: List[VolunteerInput],
    incidents: List[IncidentTaskInput]
) -> Tuple[Dict[Tuple[str, str], bool], Dict[Tuple[str, str], float], Dict[Tuple[str, str], float]]:
    """
    Computes shortest-path network reachability, travel times (mins), and distances (km)
    between all volunteer locations and incident locations via Phase 5C graph engine.
    """
    reachability: Dict[Tuple[str, str], bool] = {}
    travel_times: Dict[Tuple[str, str], float] = {}
    distances: Dict[Tuple[str, str], float] = {}

    v_nodes = {}
    for v in volunteers:
        if graph_engine.graph.has_node(v.volunteer_id):
            v_nodes[v.volunteer_id] = v.volunteer_id
        else:
            v_nodes[v.volunteer_id] = graph_engine.find_nearest_node(v.latitude, v.longitude)

    i_nodes = {}
    for inc in incidents:
        if graph_engine.graph.has_node(inc.incident_id):
            i_nodes[inc.incident_id] = inc.incident_id
        else:
            i_nodes[inc.incident_id] = graph_engine.find_nearest_node(inc.latitude, inc.longitude)

    node_pair_cache: Dict[Tuple[int, int], Any] = {}

    for v in volunteers:
        u_node = v_nodes[v.volunteer_id]
        for inc in incidents:
            v_node = i_nodes[inc.incident_id]
            pair = (v.volunteer_id, inc.incident_id)

            if u_node is None or v_node is None:
                reachability[pair] = False
                travel_times[pair] = IMPASSABLE_THRESHOLD
                distances[pair] = 999.0
                continue

            if u_node == v_node:
                reachability[pair] = True
                travel_times[pair] = 1.0
                distances[pair] = 0.1
                continue

            node_pair = (u_node, v_node)
            if node_pair not in node_pair_cache:
                node_pair_cache[node_pair] = graph_engine.compute_shortest_path(u_node, v_node, algorithm="DIJKSTRA")
            route = node_pair_cache[node_pair]

            if route.status == "FEASIBLE" and route.travel_time_minutes < IMPASSABLE_THRESHOLD:
                reachability[pair] = True
                travel_times[pair] = max(0.5, round(route.travel_time_minutes, 2))
                distances[pair] = max(0.1, round(route.distance_km, 2))
            else:
                reachability[pair] = False
                travel_times[pair] = IMPASSABLE_THRESHOLD
                distances[pair] = 999.0

    return reachability, travel_times, distances


# --- 4. CP-SAT Volunteer Assignment Engine ---

class VolunteerAssignmentEngine:
    """
    Core OR-Tools CP-SAT Volunteer Assignment Optimization Engine.
    Solves for optimal, skill-verified, workload-feasible volunteer assignments.
    Strictly decision-support: outputs candidate PROPOSED assignments.
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        use_incident_priority: bool = False
    ):
        self.weights = weights or dict(OBJECTIVE_WEIGHTS)
        self.use_incident_priority = use_incident_priority

    def solve(
        self,
        volunteers: List[VolunteerInput],
        incidents: List[IncidentTaskInput],
        graph_engine: RoadGraphEngine,
        solver_time_limit_sec: float = 5.0,
        random_seed: int = 42
    ) -> VolunteerAssignmentResult:
        """
        Executes CP-SAT volunteer assignment optimization with exact integer formulation.
        """
        t_total_start = time.perf_counter()

        # Handle empty inputs cleanly
        if not incidents or not any(sum(inc.required_skills.values()) > 0 for inc in incidents):
            return VolunteerAssignmentResult(
                solver_status="OPTIMAL",
                operational_feasibility="FULLY_FEASIBLE",
                assignments=[],
                unmet_items=[],
                total_tasks_demanded=0,
                total_tasks_assigned=0,
                total_tasks_unmet=0,
                unmet_percentage=0.0,
                skill_unmet_counts={k: 0 for k in SKILL_CATEGORIES},
                deployed_volunteers_count=0,
                mean_transit_time_mins=0.0,
                total_transit_minutes=0.0,
                total_transit_km=0.0,
                objective_value=0.0,
                objective_breakdown={
                    "unmet_general": 0.0,
                    "unmet_medical_surcharge": 0.0,
                    "transit_time": 0.0,
                    "transit_distance": 0.0,
                    "deployment": 0.0
                },
                solver_runtime_ms=0.0,
                optimality_gap=0.0,
                graph_version=graph_engine.get_graph_version(),
                explanation_summary="No task demands provided."
            )

        # 1. Input Validation
        total_demands = 0
        all_shifts: Set[str] = set()
        for inc in incidents:
            for shift in inc.shifts:
                all_shifts.add(shift)
            for skill, count in inc.required_skills.items():
                if count < 0:
                    raise ValueError(f"Incident {inc.incident_id} has negative demand for skill {skill}: {count}")
                # Demands apply across configured shifts
                total_demands += count * len(inc.shifts)

        # 2. Phase 5C Network Distance & Reachability Matrix Retrieval
        t_matrix_start = time.perf_counter()
        reachability_mask, travel_times, distances = _resolve_volunteer_network_matrices(
            graph_engine, volunteers, incidents
        )
        t_matrix_end = time.perf_counter()

        # 3. Model Construction
        t_model_start = time.perf_counter()
        model = cp_model.CpModel()
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = solver_time_limit_sec
        solver.parameters.random_seed = random_seed
        solver.parameters.num_search_workers = 1  # Single-threaded deterministic solve

        # Decision Variables:
        # y_vikt: volunteer v assigned to task k at incident i during shift t
        y_vars: Dict[Tuple[str, str, str, str], cp_model.IntVar] = {}
        # u_ikt: unmet demand for task k at incident i during shift t
        u_vars: Dict[Tuple[str, str, str], cp_model.IntVar] = {}
        # z_vt: volunteer v deployed during shift t
        z_vars: Dict[Tuple[str, str], cp_model.IntVar] = {}

        # Pre-filter eligible volunteers
        eligible_volunteers = [v for v in volunteers if is_volunteer_operationally_eligible(v)]

        # Determine all candidate (v, i, k, t) assignments
        v_shift_assignments: Dict[Tuple[str, str], List[cp_model.IntVar]] = {}

        for v in eligible_volunteers:
            for t in all_shifts:
                if not is_volunteer_available_for_shift(v, t):
                    continue
                v_shift_assignments[(v.volunteer_id, t)] = []

        for inc in incidents:
            for t in inc.shifts:
                duration_h = inc.task_durations.get(t, 4.0)
                for skill, count in inc.required_skills.items():
                    if count <= 0:
                        continue

                    # Create unmet variable u_ikt in [0, d_ikt]
                    u_key = (inc.incident_id, skill, t)
                    u_var = model.NewIntVar(0, count, f"u_{inc.incident_id}_{skill}_{t}")
                    u_vars[u_key] = u_var

                    candidate_y = []
                    for v in eligible_volunteers:
                        pair = (v.volunteer_id, inc.incident_id)
                        # Check shift availability
                        if not is_volunteer_available_for_shift(v, t):
                            continue
                        # Check workload ceiling
                        if duration_h > v.max_shift_hours:
                            continue
                        # Check reachability and travel cutoff
                        if not reachability_mask.get(pair, False):
                            continue
                        t_min = travel_times.get(pair, IMPASSABLE_THRESHOLD)
                        if t_min > v.max_travel_time_mins:
                            continue
                        # Check skill compatibility
                        if not can_volunteer_satisfy_skill(v, skill):
                            continue

                        # Create binary variable y_vikt
                        y_key = (v.volunteer_id, inc.incident_id, skill, t)
                        y_var = model.NewBoolVar(f"y_{v.volunteer_id}_{inc.incident_id}_{skill}_{t}")
                        y_vars[y_key] = y_var
                        candidate_y.append(y_var)
                        v_shift_assignments[(v.volunteer_id, t)].append(y_var)

                    # TASK CONSERVATION LAW: sum_v y_vikt + u_ikt == d_ikt
                    if candidate_y:
                        model.Add(sum(candidate_y) + u_var == count)
                    else:
                        model.Add(u_var == count)

        # MUTUAL EXCLUSIVITY & DEPLOYMENT REIFICATION per volunteer and shift
        for (v_id, t), y_list in v_shift_assignments.items():
            if not y_list:
                continue

            z_var = model.NewBoolVar(f"z_{v_id}_{t}")
            z_vars[(v_id, t)] = z_var

            # Mutual exclusivity: at most one task per volunteer during shift t
            model.Add(sum(y_list) <= 1)

            # Deployment linking: y_vikt <= z_vt and z_vt <= sum y_vikt
            for y_var in y_list:
                model.Add(y_var <= z_var)
            model.Add(z_var <= sum(y_list))

        # 4. Objective Formulation
        objective_terms = []

        lambda_1 = self.weights["lambda_1"]
        lambda_2 = self.weights["lambda_2"]
        lambda_3 = self.weights["lambda_3"]
        lambda_4 = self.weights["lambda_4"]
        lambda_5 = self.weights["lambda_5"]

        # 4a. Unmet Demand Penalties
        for (inc_id, skill, t), u_var in u_vars.items():
            inc = next(i for i in incidents if i.incident_id == inc_id)
            priority_factor = 1.0
            if self.use_incident_priority:
                sev_mult = SEVERITY_MULTIPLIERS.get(inc.severity_level.upper(), 2.0)
                priority_score = max(1.0, inc.priority_score)
                priority_factor = (sev_mult * priority_score) / 100.0

            # General unmet penalty for all tasks (lambda_1)
            coeff_1 = int(round(lambda_1 * priority_factor * OBJECTIVE_SCALE))
            objective_terms.append(coeff_1 * u_var)

            # Medical unmet surcharge (lambda_2)
            if skill.upper() == "MEDICAL":
                coeff_2 = int(round(lambda_2 * priority_factor * OBJECTIVE_SCALE))
                objective_terms.append(coeff_2 * u_var)

        # 4b. Transit Time & Distance Penalties
        for (v_id, inc_id, skill, t), y_var in y_vars.items():
            pair = (v_id, inc_id)
            t_min = travel_times.get(pair, 0.0)
            d_km = distances.get(pair, 0.0)

            transit_cost = (lambda_3 * t_min) + (lambda_4 * d_km)
            scaled_transit = int(round(transit_cost * OBJECTIVE_SCALE))
            objective_terms.append(scaled_transit * y_var)

        # 4c. Volunteer Deployment Overhead
        for (v_id, t), z_var in z_vars.items():
            scaled_deploy = int(round(lambda_5 * OBJECTIVE_SCALE))
            objective_terms.append(scaled_deploy * z_var)

        model.Minimize(sum(objective_terms))
        t_model_end = time.perf_counter()

        # 5. Solve Model
        t_solve_start = time.perf_counter()
        status_code = solver.Solve(model)
        t_solve_end = time.perf_counter()

        status_map = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "MODEL_INVALID",
            cp_model.UNKNOWN: "UNKNOWN"
        }
        solver_status = status_map.get(status_code, "UNKNOWN")

        # 6. Extract Solution
        assignments: List[VolunteerAssignmentItem] = []
        unmet_items: List[VolunteerUnmetItem] = []
        volunteers_by_id = {v.volunteer_id: v for v in volunteers}
        incidents_by_id = {inc.incident_id: inc for inc in incidents}

        total_assigned = 0
        total_unmet = 0
        total_time_mins = 0.0
        total_dist_km = 0.0
        deployed_volunteers: Set[str] = set()
        skill_unmet_counts = {k: 0 for k in SKILL_CATEGORIES}

        # Breakdown accumulators
        cost_unmet_gen = 0.0
        cost_unmet_med = 0.0
        cost_transit_time = 0.0
        cost_transit_dist = 0.0
        cost_deploy = 0.0

        if solver_status in ["OPTIMAL", "FEASIBLE"]:
            # Extract assignments
            for (v_id, inc_id, skill, t), y_var in y_vars.items():
                val = solver.Value(y_var)
                if val > 0:
                    v = volunteers_by_id[v_id]
                    inc = incidents_by_id[inc_id]
                    pair = (v_id, inc_id)
                    t_min = travel_times.get(pair, 0.0)
                    d_km = distances.get(pair, 0.0)
                    dur_h = inc.task_durations.get(t, 4.0)

                    contrib = (lambda_3 * t_min) + (lambda_4 * d_km)
                    assignments.append(VolunteerAssignmentItem(
                        volunteer_id=v_id,
                        volunteer_name=v.name,
                        incident_id=inc_id,
                        skill_category=skill,
                        shift_id=t,
                        transit_time_minutes=t_min,
                        transit_distance_km=d_km,
                        task_duration_hours=dur_h,
                        objective_contribution=round(contrib, 2),
                        status="PROPOSED"
                    ))
                    total_assigned += 1
                    total_time_mins += t_min
                    total_dist_km += d_km
                    deployed_volunteers.add(v_id)

                    cost_transit_time += lambda_3 * t_min
                    cost_transit_dist += lambda_4 * d_km

            # Extract deployed volunteer overhead
            for (v_id, t), z_var in z_vars.items():
                if solver.Value(z_var) > 0:
                    cost_deploy += lambda_5

            # Extract unmet items
            for (inc_id, skill, t), u_var in u_vars.items():
                u_val = solver.Value(u_var)
                if u_val > 0:
                    inc = incidents_by_id[inc_id]
                    priority_factor = 1.0
                    if self.use_incident_priority:
                        sev_mult = SEVERITY_MULTIPLIERS.get(inc.severity_level.upper(), 2.0)
                        priority_score = max(1.0, inc.priority_score)
                        priority_factor = (sev_mult * priority_score) / 100.0

                    gen_penalty = lambda_1 * priority_factor * u_val
                    med_penalty = (lambda_2 * priority_factor * u_val) if skill.upper() == "MEDICAL" else 0.0
                    total_penalty = gen_penalty + med_penalty

                    unmet_items.append(VolunteerUnmetItem(
                        incident_id=inc_id,
                        skill_category=skill,
                        shift_id=t,
                        unmet_quantity=u_val,
                        penalty_contribution=round(total_penalty, 2)
                    ))
                    total_unmet += u_val
                    cost_unmet_gen += gen_penalty
                    cost_unmet_med += med_penalty
                    skill_unmet_counts[skill] = skill_unmet_counts.get(skill, 0) + u_val

            raw_solver_obj = solver.ObjectiveValue() / float(OBJECTIVE_SCALE)
        else:
            # Infeasible / failure
            raw_solver_obj = 0.0
            for (inc_id, skill, t), u_var in u_vars.items():
                inc = incidents_by_id[inc_id]
                d = inc.required_skills.get(skill, 0)
                if d > 0:
                    total_unmet += d
                    skill_unmet_counts[skill] = skill_unmet_counts.get(skill, 0) + d
                    unmet_items.append(VolunteerUnmetItem(
                        incident_id=inc_id,
                        skill_category=skill,
                        shift_id=t,
                        unmet_quantity=d,
                        penalty_contribution=round((lambda_1 + (lambda_2 if skill == "MEDICAL" else 0.0)) * d, 2)
                    ))

        # 7. Operational Feasibility Classification
        if total_demands == 0 or total_unmet == 0:
            operational_feasibility = "FULLY_FEASIBLE"
        elif total_assigned > 0:
            operational_feasibility = "PARTIALLY_FEASIBLE"
        else:
            operational_feasibility = "INFEASIBLE"

        mean_transit_time = (total_time_mins / total_assigned) if total_assigned > 0 else 0.0
        unmet_pct = (total_unmet / total_demands * 100.0) if total_demands > 0 else 0.0

        objective_breakdown = {
            "unmet_general": round(cost_unmet_gen, 2),
            "unmet_medical_surcharge": round(cost_unmet_med, 2),
            "transit_time": round(cost_transit_time, 2),
            "transit_distance": round(cost_transit_dist, 2),
            "deployment": round(cost_deploy, 2)
        }

        # Optimality gap
        try:
            best_bound = solver.BestObjectiveBound() / float(OBJECTIVE_SCALE)
            gap = abs(raw_solver_obj - best_bound) / max(1.0, abs(raw_solver_obj)) if raw_solver_obj > 0 else 0.0
        except Exception:
            gap = 0.0

        solver_ms = (t_solve_end - t_solve_start) * 1000.0

        summary = (
            f"CP-SAT {solver_status}: {total_assigned}/{total_demands} tasks assigned ({unmet_pct:.1f}% unmet). "
            f"Deployed {len(deployed_volunteers)} volunteers. Mean transit time: {mean_transit_time:.1f} min."
        )

        return VolunteerAssignmentResult(
            solver_status=solver_status,
            operational_feasibility=operational_feasibility,
            assignments=assignments,
            unmet_items=unmet_items,
            total_tasks_demanded=total_demands,
            total_tasks_assigned=total_assigned,
            total_tasks_unmet=total_unmet,
            unmet_percentage=round(unmet_pct, 2),
            skill_unmet_counts=skill_unmet_counts,
            deployed_volunteers_count=len(deployed_volunteers),
            mean_transit_time_mins=round(mean_transit_time, 2),
            total_transit_minutes=round(total_time_mins, 2),
            total_transit_km=round(total_dist_km, 2),
            objective_value=round(raw_solver_obj, 2),
            objective_breakdown=objective_breakdown,
            solver_runtime_ms=round(solver_ms, 2),
            optimality_gap=round(gap, 6),
            graph_version=graph_engine.get_graph_version(),
            explanation_summary=summary
        )


# --- 5. Ground-Truth Reference Solver (Brute-Force) ---

class BruteForceVolunteerSolver:
    """
    Independent ground-truth reference solver for Phase 5F-D.
    Performs exhaustive combinatorial search over all valid volunteer assignments
    for small problem instances to independently verify CP-SAT mathematical optimality.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(OBJECTIVE_WEIGHTS)

    def solve(
        self,
        volunteers: List[VolunteerInput],
        incidents: List[IncidentTaskInput],
        graph_engine: RoadGraphEngine
    ) -> Dict[str, Any]:
        reachability_mask, travel_times, distances = _resolve_volunteer_network_matrices(
            graph_engine, volunteers, incidents
        )

        lambda_1 = self.weights["lambda_1"]
        lambda_2 = self.weights["lambda_2"]
        lambda_3 = self.weights["lambda_3"]
        lambda_4 = self.weights["lambda_4"]
        lambda_5 = self.weights["lambda_5"]

        # Flatten task requirements into individual task slots
        # Each slot: (slot_id, inc_id, skill, shift, duration_h)
        task_slots: List[Tuple[int, str, str, str, float]] = []
        slot_idx = 0
        for inc in incidents:
            for t in inc.shifts:
                dur_h = inc.task_durations.get(t, 4.0)
                for skill, count in inc.required_skills.items():
                    for _ in range(count):
                        task_slots.append((slot_idx, inc.incident_id, skill, t, dur_h))
                        slot_idx += 1

        eligible_volunteers = [v for v in volunteers if is_volunteer_operationally_eligible(v)]
        all_shifts = list(set(slot[3] for slot in task_slots)) if task_slots else ["SHIFT_1"]

        best_objective = float("inf")
        best_assignment: Dict[int, Optional[str]] = {}  # slot_idx -> volunteer_id or None

        # Recursive search over slots
        def search(slot_pos: int, current_slot_assignments: Dict[int, Optional[str]], volunteer_assigned_shifts: Dict[Tuple[str, str], bool]):
            nonlocal best_objective, best_assignment

            if slot_pos == len(task_slots):
                # Evaluate objective
                obj = 0.0
                deployed: Set[Tuple[str, str]] = set()

                for s_id, inc_id, skill, t, dur_h in task_slots:
                    v_id = current_slot_assignments[s_id]
                    if v_id is None:
                        # Unmet
                        obj += lambda_1
                        if skill.upper() == "MEDICAL":
                            obj += lambda_2
                    else:
                        pair = (v_id, inc_id)
                        t_min = travel_times[pair]
                        d_km = distances[pair]
                        obj += (lambda_3 * t_min) + (lambda_4 * d_km)
                        deployed.add((v_id, t))

                # Deployment overhead
                obj += lambda_5 * len(deployed)

                if obj < best_objective:
                    best_objective = obj
                    best_assignment = dict(current_slot_assignments)
                return

            s_id, inc_id, skill, t, dur_h = task_slots[slot_pos]

            # Option 1: Leave slot unmet
            current_slot_assignments[s_id] = None
            search(slot_pos + 1, current_slot_assignments, volunteer_assigned_shifts)

            # Option 2: Try assigning to an eligible, available volunteer
            for v in eligible_volunteers:
                # Check mutual exclusivity (already assigned in this shift)
                if volunteer_assigned_shifts.get((v.volunteer_id, t), False):
                    continue
                # Check shift availability
                if not is_volunteer_available_for_shift(v, t):
                    continue
                # Check workload
                if dur_h > v.max_shift_hours:
                    continue
                # Check skill
                if not can_volunteer_satisfy_skill(v, skill):
                    continue
                # Check reachability and travel cutoff
                pair = (v.volunteer_id, inc_id)
                if not reachability_mask.get(pair, False):
                    continue
                t_min = travel_times.get(pair, IMPASSABLE_THRESHOLD)
                if t_min > v.max_travel_time_mins:
                    continue

                # Feasible assignment
                current_slot_assignments[s_id] = v.volunteer_id
                volunteer_assigned_shifts[(v.volunteer_id, t)] = True

                search(slot_pos + 1, current_slot_assignments, volunteer_assigned_shifts)

                # Backtrack
                current_slot_assignments[s_id] = None
                volunteer_assigned_shifts[(v.volunteer_id, t)] = False

        search(0, {}, {})

        return {
            "optimal_objective": round(best_objective, 2) if best_objective < float("inf") else 0.0,
            "best_assignment": best_assignment,
            "total_slots": len(task_slots)
        }


# --- 6. Heuristic Baselines ---

class GreedyFeasibleVolunteerSolver:
    """
    Baseline Heuristic A: Greedy Proximity / Priority Assignment.
    Sorts tasks by medical priority first, then assigns nearest feasible volunteer.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(OBJECTIVE_WEIGHTS)

    def solve(
        self,
        volunteers: List[VolunteerInput],
        incidents: List[IncidentTaskInput],
        graph_engine: RoadGraphEngine
    ) -> VolunteerAssignmentResult:
        t_start = time.perf_counter()
        reachability_mask, travel_times, distances = _resolve_volunteer_network_matrices(
            graph_engine, volunteers, incidents
        )

        lambda_1 = self.weights["lambda_1"]
        lambda_2 = self.weights["lambda_2"]
        lambda_3 = self.weights["lambda_3"]
        lambda_4 = self.weights["lambda_4"]
        lambda_5 = self.weights["lambda_5"]

        # Flatten and sort tasks: MEDICAL first, then by priority_score descending
        task_slots = []
        for inc in incidents:
            for t in inc.shifts:
                dur_h = inc.task_durations.get(t, 4.0)
                for skill, count in inc.required_skills.items():
                    for _ in range(count):
                        is_med = 1 if skill.upper() == "MEDICAL" else 0
                        task_slots.append((is_med, inc.priority_score, inc.incident_id, skill, t, dur_h))

        task_slots.sort(key=lambda x: (x[0], x[1]), reverse=True)

        eligible_volunteers = [v for v in volunteers if is_volunteer_operationally_eligible(v)]
        volunteers_by_id = {v.volunteer_id: v for v in volunteers}
        incidents_by_id = {inc.incident_id: inc for inc in incidents}

        assigned_shifts: Set[Tuple[str, str]] = set()  # (v_id, shift_id)
        assignments: List[VolunteerAssignmentItem] = []
        unmet_items: List[VolunteerUnmetItem] = []

        total_assigned = 0
        total_unmet = 0
        total_time_mins = 0.0
        total_dist_km = 0.0
        skill_unmet_counts = {k: 0 for k in SKILL_CATEGORIES}

        cost_unmet_gen = 0.0
        cost_unmet_med = 0.0
        cost_transit_time = 0.0
        cost_transit_dist = 0.0
        cost_deploy = 0.0
        deployed_volunteers: Set[Tuple[str, str]] = set()

        for _, _, inc_id, skill, t, dur_h in task_slots:
            best_v = None
            best_cost = float("inf")
            inc = incidents_by_id[inc_id]

            for v in eligible_volunteers:
                if (v.volunteer_id, t) in assigned_shifts:
                    continue
                if not is_volunteer_available_for_shift(v, t):
                    continue
                if dur_h > v.max_shift_hours:
                    continue
                if not can_volunteer_satisfy_skill(v, skill):
                    continue
                pair = (v.volunteer_id, inc_id)
                if not reachability_mask.get(pair, False):
                    continue
                t_min = travel_times.get(pair, IMPASSABLE_THRESHOLD)
                if t_min > v.max_travel_time_mins:
                    continue

                d_km = distances.get(pair, 0.0)
                cost = (lambda_3 * t_min) + (lambda_4 * d_km)
                if cost < best_cost:
                    best_cost = cost
                    best_v = v

            if best_v is not None:
                assigned_shifts.add((best_v.volunteer_id, t))
                pair = (best_v.volunteer_id, inc_id)
                t_min = travel_times[pair]
                d_km = distances[pair]

                assignments.append(VolunteerAssignmentItem(
                    volunteer_id=best_v.volunteer_id,
                    volunteer_name=best_v.name,
                    incident_id=inc_id,
                    skill_category=skill,
                    shift_id=t,
                    transit_time_minutes=t_min,
                    transit_distance_km=d_km,
                    task_duration_hours=dur_h,
                    objective_contribution=round(best_cost, 2),
                    status="PROPOSED"
                ))
                total_assigned += 1
                total_time_mins += t_min
                total_dist_km += d_km
                cost_transit_time += lambda_3 * t_min
                cost_transit_dist += lambda_4 * d_km
                deployed_volunteers.add((best_v.volunteer_id, t))
            else:
                total_unmet += 1
                skill_unmet_counts[skill] = skill_unmet_counts.get(skill, 0) + 1
                gen_p = lambda_1
                med_p = lambda_2 if skill.upper() == "MEDICAL" else 0.0
                cost_unmet_gen += gen_p
                cost_unmet_med += med_p
                unmet_items.append(VolunteerUnmetItem(
                    incident_id=inc_id,
                    skill_category=skill,
                    shift_id=t,
                    unmet_quantity=1,
                    penalty_contribution=round(gen_p + med_p, 2)
                ))

        cost_deploy = lambda_5 * len(deployed_volunteers)
        total_obj = cost_unmet_gen + cost_unmet_med + cost_transit_time + cost_transit_dist + cost_deploy
        runtime_ms = (time.perf_counter() - t_start) * 1000.0

        total_demands = len(task_slots)
        unmet_pct = (total_unmet / total_demands * 100.0) if total_demands > 0 else 0.0
        mean_time = (total_time_mins / total_assigned) if total_assigned > 0 else 0.0

        return VolunteerAssignmentResult(
            solver_status="OPTIMAL" if total_unmet == 0 else "FEASIBLE",
            operational_feasibility="FULLY_FEASIBLE" if total_unmet == 0 else "PARTIALLY_FEASIBLE",
            assignments=assignments,
            unmet_items=unmet_items,
            total_tasks_demanded=total_demands,
            total_tasks_assigned=total_assigned,
            total_tasks_unmet=total_unmet,
            unmet_percentage=round(unmet_pct, 2),
            skill_unmet_counts=skill_unmet_counts,
            deployed_volunteers_count=len(deployed_volunteers),
            mean_transit_time_mins=round(mean_time, 2),
            total_transit_minutes=round(total_time_mins, 2),
            total_transit_km=round(total_dist_km, 2),
            objective_value=round(total_obj, 2),
            objective_breakdown={
                "unmet_general": round(cost_unmet_gen, 2),
                "unmet_medical_surcharge": round(cost_unmet_med, 2),
                "transit_time": round(cost_transit_time, 2),
                "transit_distance": round(cost_transit_dist, 2),
                "deployment": round(cost_deploy, 2)
            },
            solver_runtime_ms=round(runtime_ms, 2),
            optimality_gap=0.0,
            graph_version=graph_engine.get_graph_version(),
            explanation_summary="Greedy Proximity Heuristic Baseline."
        )


class FCFSVolunteerSolver:
    """
    Baseline Heuristic B: First-Come, First-Served (FCFS) Assignment.
    Assigns tasks in arbitrary encounter order to the first eligible volunteer found.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(OBJECTIVE_WEIGHTS)

    def solve(
        self,
        volunteers: List[VolunteerInput],
        incidents: List[IncidentTaskInput],
        graph_engine: RoadGraphEngine
    ) -> VolunteerAssignmentResult:
        t_start = time.perf_counter()
        reachability_mask, travel_times, distances = _resolve_volunteer_network_matrices(
            graph_engine, volunteers, incidents
        )

        lambda_1 = self.weights["lambda_1"]
        lambda_2 = self.weights["lambda_2"]
        lambda_3 = self.weights["lambda_3"]
        lambda_4 = self.weights["lambda_4"]
        lambda_5 = self.weights["lambda_5"]

        eligible_volunteers = [v for v in volunteers if is_volunteer_operationally_eligible(v)]
        assigned_shifts: Set[Tuple[str, str]] = set()

        assignments: List[VolunteerAssignmentItem] = []
        unmet_items: List[VolunteerUnmetItem] = []

        total_demands = 0
        total_assigned = 0
        total_unmet = 0
        total_time_mins = 0.0
        total_dist_km = 0.0
        skill_unmet_counts = {k: 0 for k in SKILL_CATEGORIES}

        cost_unmet_gen = 0.0
        cost_unmet_med = 0.0
        cost_transit_time = 0.0
        cost_transit_dist = 0.0
        cost_deploy = 0.0
        deployed_volunteers: Set[Tuple[str, str]] = set()

        for inc in incidents:
            for t in inc.shifts:
                dur_h = inc.task_durations.get(t, 4.0)
                for skill, count in inc.required_skills.items():
                    for _ in range(count):
                        total_demands += 1
                        matched = False
                        for v in eligible_volunteers:
                            if (v.volunteer_id, t) in assigned_shifts:
                                continue
                            if not is_volunteer_available_for_shift(v, t):
                                continue
                            if dur_h > v.max_shift_hours:
                                continue
                            if not can_volunteer_satisfy_skill(v, skill):
                                continue
                            pair = (v.volunteer_id, inc.incident_id)
                            if not reachability_mask.get(pair, False):
                                continue
                            t_min = travel_times.get(pair, IMPASSABLE_THRESHOLD)
                            if t_min > v.max_travel_time_mins:
                                continue

                            d_km = distances.get(pair, 0.0)
                            assigned_shifts.add((v.volunteer_id, t))
                            cost = (lambda_3 * t_min) + (lambda_4 * d_km)

                            assignments.append(VolunteerAssignmentItem(
                                volunteer_id=v.volunteer_id,
                                volunteer_name=v.name,
                                incident_id=inc.incident_id,
                                skill_category=skill,
                                shift_id=t,
                                transit_time_minutes=t_min,
                                transit_distance_km=d_km,
                                task_duration_hours=dur_h,
                                objective_contribution=round(cost, 2),
                                status="PROPOSED"
                            ))
                            total_assigned += 1
                            total_time_mins += t_min
                            total_dist_km += d_km
                            cost_transit_time += lambda_3 * t_min
                            cost_transit_dist += lambda_4 * d_km
                            deployed_volunteers.add((v.volunteer_id, t))
                            matched = True
                            break

                        if not matched:
                            total_unmet += 1
                            skill_unmet_counts[skill] = skill_unmet_counts.get(skill, 0) + 1
                            gen_p = lambda_1
                            med_p = lambda_2 if skill.upper() == "MEDICAL" else 0.0
                            cost_unmet_gen += gen_p
                            cost_unmet_med += med_p
                            unmet_items.append(VolunteerUnmetItem(
                                incident_id=inc.incident_id,
                                skill_category=skill,
                                shift_id=t,
                                unmet_quantity=1,
                                penalty_contribution=round(gen_p + med_p, 2)
                            ))

        cost_deploy = lambda_5 * len(deployed_volunteers)
        total_obj = cost_unmet_gen + cost_unmet_med + cost_transit_time + cost_transit_dist + cost_deploy
        runtime_ms = (time.perf_counter() - t_start) * 1000.0

        unmet_pct = (total_unmet / total_demands * 100.0) if total_demands > 0 else 0.0
        mean_time = (total_time_mins / total_assigned) if total_assigned > 0 else 0.0

        return VolunteerAssignmentResult(
            solver_status="OPTIMAL" if total_unmet == 0 else "FEASIBLE",
            operational_feasibility="FULLY_FEASIBLE" if total_unmet == 0 else "PARTIALLY_FEASIBLE",
            assignments=assignments,
            unmet_items=unmet_items,
            total_tasks_demanded=total_demands,
            total_tasks_assigned=total_assigned,
            total_tasks_unmet=total_unmet,
            unmet_percentage=round(unmet_pct, 2),
            skill_unmet_counts=skill_unmet_counts,
            deployed_volunteers_count=len(deployed_volunteers),
            mean_transit_time_mins=round(mean_time, 2),
            total_transit_minutes=round(total_time_mins, 2),
            total_transit_km=round(total_dist_km, 2),
            objective_value=round(total_obj, 2),
            objective_breakdown={
                "unmet_general": round(cost_unmet_gen, 2),
                "unmet_medical_surcharge": round(cost_unmet_med, 2),
                "transit_time": round(cost_transit_time, 2),
                "transit_distance": round(cost_transit_dist, 2),
                "deployment": round(cost_deploy, 2)
            },
            solver_runtime_ms=round(runtime_ms, 2),
            optimality_gap=0.0,
            graph_version=graph_engine.get_graph_version(),
            explanation_summary="First-Come First-Served Heuristic Baseline."
        )
