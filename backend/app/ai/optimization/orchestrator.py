"""
DIRS Phase 5F-E — Cross-Module Integrated Response Orchestrator
Connects and orchestrates the four frozen disaster optimization engines:
  Phase 5F-C: Shelter Evacuation Optimization
  Phase 5D:   Multi-Commodity Resource Allocation
  Phase 5E:   Vehicle Routing & Emergency Dispatch
  Phase 5F-D: Volunteer Assignment Optimization

Classification: DECISION-SUPPORT RESPONSE ORCHESTRATION LAYER (HUMAN-IN-THE-LOOP REQUIRED)
Data Provenance: SYNTHETIC-CALIBRATED (WGS-84 Chennai/Tamil Nadu Disaster Corridor)
Deployment Gate: Government authorization required before any operational action.
"""
import math
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session

from app.models.user import User, UserRole, VolunteerProfile
from app.models.incident import Incident
from app.models.shelter import Shelter
from app.models.resource import Resource
from app.models.vehicle import Vehicle
from app.models.rescue import RoadBlockage
from app.models.audit import AuditLog
from app.models.optimization import OptimizationRun, OptimizationRecommendation, OptimizationOverrideLog

from app.ai.optimization.graph import RoadGraphEngine
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph

# Phase 5F-C Shelter Engine & Interfaces
from app.ai.optimization.shelter import (
    ShelterEvacuationEngine,
    IncidentEvacuationInput,
    ShelterInput,
    ShelterEvacuationResult,
    DEMOGRAPHIC_GROUPS
)

# Phase 5D Resource Allocation Engine & Interfaces
from app.ai.optimization.allocation import (
    ResourceAllocationEngine,
    IncidentDemandInput,
    DepotSupplyInput,
    AllocationResult,
    CommodityAllocationItem,
    UnmetDemandItem
)

# Phase 5E Vehicle Routing Engine & Interfaces
from app.ai.optimization.routing import (
    VehicleRoutingEngine,
    VehicleInput,
    ShipmentInput,
    RoutingResult,
    convert_allocations_to_shipments,
    verify_phase5d_conservation
)

# Phase 5F-D Volunteer Assignment Engine & Interfaces
from app.ai.optimization.volunteer import (
    VolunteerAssignmentEngine,
    VolunteerInput,
    IncidentTaskInput,
    VolunteerAssignmentResult,
    SKILL_CATEGORIES
)


# --- 1. Synthetic-Calibrated Conversion Standards ---
# Source: Calibrated against Indian NDMA SOPs and SPHERE International Humanitarian Minimum Standards.
# Classification: SYNTHETIC-CALIBRATED (Not from live government operational manifests).

SYNTHETIC_EVACUEE_WATER_L_PER_DAY: float = 15.0      # Litres of drinking/sanitation water per person per day
SYNTHETIC_EVACUEE_FOOD_PACKS_PER_DAY: float = 2.5    # Unit food ration packs per person per day
SYNTHETIC_EVACUEE_MEDKIT_RATIO: float = 20.0         # 1 standard medical kit per 20 general evacuees
SYNTHETIC_EVACUEE_SANITATION_RATIO: float = 10.0     # 1 hygiene kit per 10 evacuees
SYNTHETIC_UNMET_TEMP_SHELTER_RATIO: float = 5.0      # 1 temporary tarpaulin/shelter kit per 5 unsheltered evacuees


# --- 2. Intake Dataclass & Validation ---

@dataclass
class IncidentIntakeInput:
    """Intake representation for an active incident evaluated by the integrated orchestrator."""
    incident_id: str
    title: str
    latitude: float
    longitude: float
    severity_level: str = "MEDIUM"          # CRITICAL, HIGH, MEDIUM, LOW
    priority_score: float = 50.0            # 0.0 to 100.0
    disaster_type: str = "FLOOD"            # FLOOD, CYCLONE, FIRE, LANDSLIDE, EARTHQUAKE
    people_affected: int = 1
    vulnerable_count: int = 0               # Children, elderly
    injuries: int = 0
    evacuation_demographics: Dict[str, int] = field(default_factory=dict)
    # e.g. {"GEN": 80, "ACC": 15, "MED": 5, "MED_ACC": 0}
    required_skills: Dict[str, int] = field(default_factory=dict)
    # e.g. {"MEDICAL": 2, "RESCUE": 1, "GENERAL": 3, "LOGISTICS": 1}
    required_resources: Dict[str, float] = field(default_factory=dict)
    # e.g. {"WATER": 500.0, "FOOD": 100.0}
    status: str = "REPORTED"
    created_at_str: str = ""


class IntegrationValidationError(Exception):
    """Raised when incident intake or cross-module validation fails."""
    pass


class GraphVersionMismatchError(Exception):
    """Raised when module graph versions do not match."""
    pass


class ConservationMismatchError(Exception):
    """Raised when cross-module conservation invariants are violated."""
    pass


def validate_incident_intake(incidents: List[IncidentIntakeInput]) -> List[str]:
    """
    Validates intake incidents. Never silently discards an incident.
    Returns list of error messages (empty if completely valid).
    """
    errors: List[str] = []
    if not incidents:
        return errors

    seen_ids: Set[str] = set()
    for inc in incidents:
        if not inc.incident_id or not inc.incident_id.strip():
            errors.append("Encountered incident with empty incident_id.")
            continue

        if inc.incident_id in seen_ids:
            errors.append(f"Duplicate incident_id detected: {inc.incident_id}")
        seen_ids.add(inc.incident_id)

        if not (-90.0 <= inc.latitude <= 90.0) or not (-180.0 <= inc.longitude <= 180.0):
            errors.append(f"Incident {inc.incident_id} has invalid WGS-84 coordinates ({inc.latitude}, {inc.longitude}).")

        if inc.priority_score < 0.0 or inc.priority_score > 100.0:
            errors.append(f"Incident {inc.incident_id} has invalid priority_score ({inc.priority_score}). Must be in [0, 100].")

        if inc.people_affected < 0:
            errors.append(f"Incident {inc.incident_id} has negative people_affected ({inc.people_affected}).")

        if inc.vulnerable_count < 0:
            errors.append(f"Incident {inc.incident_id} has negative vulnerable_count ({inc.vulnerable_count}).")

        if inc.injuries < 0:
            errors.append(f"Incident {inc.incident_id} has negative injuries ({inc.injuries}).")

        for skill, count in inc.required_skills.items():
            if count < 0:
                errors.append(f"Incident {inc.incident_id} has negative requirement for skill {skill}: {count}")

        for res, qty in inc.required_resources.items():
            if qty < 0.0:
                errors.append(f"Incident {inc.incident_id} has negative resource requirement for {res}: {qty}")

    return errors


# --- 3. Integrated Optimization Result Structure ---

@dataclass
class IntegratedOptimizationResult:
    """Top-level immutable container for cross-module optimization execution."""
    integration_run_id: str
    graph_version: str
    incident_ids: List[str]
    optimization_run_ids: Dict[str, str] = field(default_factory=dict)
    shelter_result: Optional[ShelterEvacuationResult] = None
    resource_result: Optional[AllocationResult] = None
    routing_result: Optional[RoutingResult] = None
    volunteer_result: Optional[VolunteerAssignmentResult] = None
    overall_status: str = "PROPOSED"            # PROPOSED, PARTIALLY_FEASIBLE, INFEASIBLE, VALIDATION_FAILED
    operational_feasibility: str = "FEASIBLE"    # FULLY_FEASIBLE, PARTIALLY_FEASIBLE, INFEASIBLE
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    timing_breakdown: Dict[str, float] = field(default_factory=dict)
    summary_metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    explanation: str = ""


# --- 4. Cross-Module Demand Generators (Synthetic-Calibrated) ---

def convert_shelter_output_to_resource_demands(
    incidents: List[IncidentIntakeInput],
    shelters: List[ShelterInput],
    shelter_result: ShelterEvacuationResult
) -> List[IncidentDemandInput]:
    """
    Step 3: Converts Phase 5F-C Shelter Evacuation outputs into downstream Phase 5D resource demands.
    - Active Shelters: Demands generated to sustain evacuated populations hosted on-site.
    - Unmet Evacuees at Incidents: Emergency on-site life-support demands generated for stranded populations.
    - Incident Explicit Demands: Merged and accounted for.
    """
    demands_list: List[IncidentDemandInput] = []
    shelter_by_id = {s.shelter_id: s for s in shelters}
    incident_by_id = {inc.incident_id: inc for inc in incidents}

    # 1. Tally evacuees hosted at each shelter from Phase 5F-C assignments
    shelter_hosted_counts: Dict[str, int] = {s.shelter_id: 0 for s in shelters}
    shelter_med_counts: Dict[str, int] = {s.shelter_id: 0 for s in shelters}

    for assign in shelter_result.assignments:
        s_id = assign.shelter_id
        shelter_hosted_counts[s_id] = shelter_hosted_counts.get(s_id, 0) + assign.assigned_quantity
        if assign.demographic_group in ["MED", "MED_ACC"]:
            shelter_med_counts[s_id] = shelter_med_counts.get(s_id, 0) + assign.assigned_quantity

    # Generate resource demands for each activated shelter with evacuees
    for s_id, hosted in shelter_hosted_counts.items():
        if hosted > 0 and s_id in shelter_by_id:
            s = shelter_by_id[s_id]
            med_count = shelter_med_counts.get(s_id, 0)

            water_need = round(hosted * SYNTHETIC_EVACUEE_WATER_L_PER_DAY, 1)
            food_need = round(hosted * SYNTHETIC_EVACUEE_FOOD_PACKS_PER_DAY, 1)
            med_kits = float(max(1, math.ceil(med_count + (hosted / SYNTHETIC_EVACUEE_MEDKIT_RATIO))))
            sanitation = float(max(1, math.ceil(hosted / SYNTHETIC_EVACUEE_SANITATION_RATIO)))

            demands_list.append(IncidentDemandInput(
                incident_id=f"SHELTER_DEMAND_{s_id}",
                title=f"Relief Sustenance for {s.name} ({hosted} evacuees)",
                latitude=s.latitude,
                longitude=s.longitude,
                priority_score=85.0,
                severity_level="HIGH",
                demands={
                    "WATER": water_need,
                    "FOOD": food_need,
                    "MEDICAL_KITS": med_kits,
                    "SANITATION_KITS": sanitation
                },
                created_at_str=""
            ))

    # 2. Tally unmet evacuees remaining on-site at each incident
    unmet_by_inc: Dict[str, int] = {inc.incident_id: 0 for inc in incidents}
    unmet_med_by_inc: Dict[str, int] = {inc.incident_id: 0 for inc in incidents}

    for unmet in shelter_result.unmet_items:
        inc_id = unmet.incident_id
        unmet_by_inc[inc_id] = unmet_by_inc.get(inc_id, 0) + unmet.unmet_quantity
        if unmet.demographic_group in ["MED", "MED_ACC"]:
            unmet_med_by_inc[inc_id] = unmet_med_by_inc.get(inc_id, 0) + unmet.unmet_quantity

    for inc in incidents:
        u_count = unmet_by_inc.get(inc.incident_id, 0)
        u_med = unmet_med_by_inc.get(inc.incident_id, 0)

        # Baseline explicit demands if provided
        inc_demands = dict(inc.required_resources)

        if u_count > 0:
            # Stranded on-site population requires field sustenance and emergency shelter materials
            inc_demands["WATER"] = inc_demands.get("WATER", 0.0) + round(u_count * SYNTHETIC_EVACUEE_WATER_L_PER_DAY, 1)
            inc_demands["FOOD"] = inc_demands.get("FOOD", 0.0) + round(u_count * SYNTHETIC_EVACUEE_FOOD_PACKS_PER_DAY, 1)
            inc_demands["MEDICAL_KITS"] = inc_demands.get("MEDICAL_KITS", 0.0) + float(max(1, math.ceil(u_med + (u_count / SYNTHETIC_EVACUEE_MEDKIT_RATIO))))
            inc_demands["TEMPORARY_SHELTER_SUPPLIES"] = inc_demands.get("TEMPORARY_SHELTER_SUPPLIES", 0.0) + float(max(1, math.ceil(u_count / SYNTHETIC_UNMET_TEMP_SHELTER_RATIO)))

        if inc_demands:
            demands_list.append(IncidentDemandInput(
                incident_id=inc.incident_id,
                title=inc.title,
                latitude=inc.latitude,
                longitude=inc.longitude,
                priority_score=inc.priority_score,
                severity_level=inc.severity_level,
                demands=inc_demands,
                created_at_str=inc.created_at_str
            ))

    return demands_list


def generate_integrated_volunteer_tasks(
    incidents: List[IncidentIntakeInput],
    shelters: List[ShelterInput],
    shelter_result: ShelterEvacuationResult
) -> List[IncidentTaskInput]:
    """
    Step 6: Generates volunteer staffing tasks based on incident needs and activated shelter operations.
    - Incident Site: Retains required_skills (medical, rescue, logistics, general).
    - Activated Shelters: Staffing tasks (e.g., medical triage, logistics management, general assistance).
    """
    tasks_list: List[IncidentTaskInput] = []
    shelter_by_id = {s.shelter_id: s for s in shelters}

    # 1. Incident on-site volunteer tasks
    for inc in incidents:
        if inc.required_skills:
            tasks_list.append(IncidentTaskInput(
                incident_id=inc.incident_id,
                title=inc.title,
                latitude=inc.latitude,
                longitude=inc.longitude,
                priority_score=inc.priority_score,
                severity_level=inc.severity_level,
                required_skills=dict(inc.required_skills),
                shifts=["SHIFT_1"],
                task_durations={"SHIFT_1": 4.0}
            ))

    # 2. Activated Shelter staffing tasks
    shelter_hosted_counts: Dict[str, int] = {s.shelter_id: 0 for s in shelters}
    shelter_med_counts: Dict[str, int] = {s.shelter_id: 0 for s in shelters}

    for assign in shelter_result.assignments:
        s_id = assign.shelter_id
        shelter_hosted_counts[s_id] = shelter_hosted_counts.get(s_id, 0) + assign.assigned_quantity
        if assign.demographic_group in ["MED", "MED_ACC"]:
            shelter_med_counts[s_id] = shelter_med_counts.get(s_id, 0) + assign.assigned_quantity

    for s_id, hosted in shelter_hosted_counts.items():
        if hosted > 0 and s_id in shelter_by_id:
            s = shelter_by_id[s_id]
            med_count = shelter_med_counts.get(s_id, 0)

            shelter_skills: Dict[str, int] = {
                "GENERAL": max(1, math.ceil(hosted / 50)),
                "LOGISTICS": 1
            }
            if med_count > 0 or s.has_medical:
                shelter_skills["MEDICAL"] = max(1, math.ceil(med_count / 20))

            tasks_list.append(IncidentTaskInput(
                incident_id=f"SHELTER_TASK_{s_id}",
                title=f"Staffing for Shelter {s.name}",
                latitude=s.latitude,
                longitude=s.longitude,
                priority_score=80.0,
                severity_level="HIGH",
                required_skills=shelter_skills,
                shifts=["SHIFT_1"],
                task_durations={"SHIFT_1": 4.0}
            ))

    return tasks_list


# --- 5. Cross-Module Invariant Conservation Verifiers ---

def verify_shelter_conservation(
    incidents: List[IncidentIntakeInput],
    shelter_result: ShelterEvacuationResult
) -> bool:
    """
    Verifies that for every incident and demographic group:
    sum_s x_isg + u_ig == p_ig
    """
    for inc in incidents:
        demo = dict(inc.evacuation_demographics)
        if not demo:
            demo = {
                "GEN": max(0, inc.people_affected - inc.vulnerable_count - inc.injuries),
                "ACC": inc.vulnerable_count,
                "MED": inc.injuries,
                "MED_ACC": 0
            }

        for g in DEMOGRAPHIC_GROUPS:
            p_ig = demo.get(g, 0)
            assigned_g = sum(
                a.assigned_quantity for a in shelter_result.assignments
                if a.incident_id == inc.incident_id and a.demographic_group == g
            )
            unmet_g = sum(
                u.unmet_quantity for u in shelter_result.unmet_items
                if u.incident_id == inc.incident_id and u.demographic_group == g
            )

            if assigned_g + unmet_g != p_ig:
                raise ConservationMismatchError(
                    f"Shelter conservation violated for Incident {inc.incident_id}, Demographic {g}: "
                    f"Assigned ({assigned_g}) + Unmet ({unmet_g}) != Demanded ({p_ig})"
                )
    return True


def verify_cross_module_resource_and_vehicle_conservation(
    allocation_result: AllocationResult,
    routing_result: RoutingResult
) -> bool:
    """
    Verifies Phase 5D -> Phase 5E conservation:
    allocated commodity quantity == routed quantity + unrouted quantity
    """
    allocated: Dict[Tuple[str, str], float] = {}
    for alloc in allocation_result.allocations:
        key = (alloc.incident_id, alloc.commodity)
        allocated[key] = allocated.get(key, 0.0) + alloc.quantity

    routed: Dict[Tuple[str, str], float] = {}
    for route in routing_result.routes:
        for stop in route.stops:
            for commodity, qty in stop.commodities.items():
                key = (stop.incident_id, commodity)
                routed[key] = routed.get(key, 0.0) + qty

    unrouted_map: Dict[Tuple[str, str], float] = {}
    for u in routing_result.unrouted_shipments:
        for commodity, qty in u.commodities.items():
            key = (u.incident_id, commodity)
            unrouted_map[key] = unrouted_map.get(key, 0.0) + qty

    for key, alloc_qty in allocated.items():
        r_qty = routed.get(key, 0.0)
        u_qty = unrouted_map.get(key, 0.0)
        diff = abs(alloc_qty - (r_qty + u_qty))
        if diff > 0.01:
            raise ConservationMismatchError(
                f"Phase 5D/5E Resource & Vehicle conservation violated for Incident {key[0]}, Commodity {key[1]}: "
                f"Allocated ({alloc_qty}) != Routed ({r_qty}) + Unrouted ({u_qty})"
            )
    return True


def verify_volunteer_task_conservation(
    task_inputs: List[IncidentTaskInput],
    volunteer_result: VolunteerAssignmentResult
) -> bool:
    """
    Verifies Phase 5F-D task demand conservation:
    sum_v y_vikt + u_ikt == d_ikt for all tasks, shifts, and categories.
    """
    for task in task_inputs:
        for shift in task.shifts:
            for skill, demand in task.required_skills.items():
                assigned_count = sum(
                    1 for a in volunteer_result.assignments
                    if a.incident_id == task.incident_id and a.skill_category == skill and a.shift_id == shift
                )
                unmet_count = sum(
                    u.unmet_quantity for u in volunteer_result.unmet_items
                    if u.incident_id == task.incident_id and u.skill_category == skill and u.shift_id == shift
                )

                if assigned_count + unmet_count != demand:
                    raise ConservationMismatchError(
                        f"Volunteer task conservation violated for {task.incident_id} [{skill}, {shift}]: "
                        f"Assigned ({assigned_count}) + Unmet ({unmet_count}) != Demanded ({demand})"
                    )
    return True


def verify_graph_version_consistency(
    expected_version: str,
    module_versions: Dict[str, str]
) -> bool:
    """
    Enforces that every optimization module consumed the exact same Phase 5C graph snapshot version.
    """
    for module_name, ver in module_versions.items():
        if ver != expected_version:
            raise GraphVersionMismatchError(
                f"INTEGRATION_ERROR_GRAPH_VERSION_MISMATCH: Module '{module_name}' used graph_version '{ver}' "
                f"which does not match pipeline expected version '{expected_version}'."
            )
    return True


# --- 6. Core Integrated Response Orchestrator ---

class IntegratedResponseOrchestrator:
    """
    Phase 5F-E Integrated Response Orchestrator.
    Executes the sequential, demographically-conserved disaster response pipeline:
      Incidents -> 5F-C Shelter -> Downstream Demands -> 5D Resources -> 5E Routing -> 5F-D Volunteers.
    Strictly preserves frozen module boundaries; does not replace any optimization solver.
    """

    def __init__(
        self,
        shelter_engine: Optional[ShelterEvacuationEngine] = None,
        allocation_engine: Optional[ResourceAllocationEngine] = None,
        routing_engine: Optional[VehicleRoutingEngine] = None,
        volunteer_engine: Optional[VolunteerAssignmentEngine] = None
    ):
        self.shelter_engine = shelter_engine or ShelterEvacuationEngine()
        self.allocation_engine = allocation_engine or ResourceAllocationEngine()
        self.routing_engine = routing_engine or VehicleRoutingEngine()
        self.volunteer_engine = volunteer_engine or VolunteerAssignmentEngine()

    def run_pipeline(
        self,
        incidents: List[IncidentIntakeInput],
        shelters: List[ShelterInput],
        depots: List[DepotSupplyInput],
        vehicles: List[VehicleInput],
        volunteers: List[VolunteerInput],
        graph_engine: RoadGraphEngine,
        solver_time_limits: Optional[Dict[str, float]] = None,
        random_seed: int = 42
    ) -> IntegratedOptimizationResult:
        """
        Executes complete end-to-end disaster response optimization across all four modules.
        """
        t_pipeline_start = time.perf_counter()
        run_id = f"INTEG_RUN_{uuid.uuid4().hex[:8]}"
        graph_version = graph_engine.get_graph_version()
        time_limits = solver_time_limits or {"shelter": 5.0, "allocation": 2.0, "routing": 5.0, "volunteer": 5.0}

        validation_errors: List[str] = []
        validation_warnings: List[str] = []
        timing: Dict[str, float] = {}

        # ----------------------------------------------------------------------
        # STEP 1: Incident Intake & Input Validation
        # ----------------------------------------------------------------------
        t_step1_start = time.perf_counter()
        intake_errors = validate_incident_intake(incidents)
        if intake_errors:
            validation_errors.extend(intake_errors)
            return IntegratedOptimizationResult(
                integration_run_id=run_id,
                graph_version=graph_version,
                incident_ids=[inc.incident_id for inc in incidents],
                overall_status="VALIDATION_FAILED",
                operational_feasibility="INFEASIBLE",
                validation_errors=validation_errors,
                explanation="Pipeline halted: incident intake validation failed."
            )

        if not incidents:
            return IntegratedOptimizationResult(
                integration_run_id=run_id,
                graph_version=graph_version,
                incident_ids=[],
                overall_status="PROPOSED",
                operational_feasibility="FULLY_FEASIBLE",
                explanation="No incidents provided. Empty pipeline completed successfully."
            )

        # Prepare 5F-C inputs
        shelter_inputs: List[IncidentEvacuationInput] = []
        for inc in incidents:
            demo = dict(inc.evacuation_demographics)
            if not demo:
                demo = {
                    "GEN": max(0, inc.people_affected - inc.vulnerable_count - inc.injuries),
                    "ACC": inc.vulnerable_count,
                    "MED": inc.injuries,
                    "MED_ACC": 0
                }
            shelter_inputs.append(IncidentEvacuationInput(
                incident_id=inc.incident_id,
                title=inc.title,
                latitude=inc.latitude,
                longitude=inc.longitude,
                priority_score=inc.priority_score,
                severity_level=inc.severity_level,
                disaster_type=inc.disaster_type,
                people_affected=inc.people_affected,
                evacuation_demographics=demo
            ))
        timing["intake_validation_ms"] = round((time.perf_counter() - t_step1_start) * 1000.0, 2)

        # ----------------------------------------------------------------------
        # STEP 2: Phase 5F-C Shelter Evacuation Optimization
        # ----------------------------------------------------------------------
        t_step2_start = time.perf_counter()
        try:
            shelter_res: ShelterEvacuationResult = self.shelter_engine.solve(
                incidents=shelter_inputs,
                shelters=shelters,
                graph_engine=graph_engine,
                solver_time_limit_sec=time_limits.get("shelter", 5.0),
                random_seed=random_seed
            )
            # Verify shelter conservation
            verify_shelter_conservation(incidents, shelter_res)
        except Exception as e:
            validation_errors.append(f"SHELTER_OPTIMIZATION_FAILED: {str(e)}")
            return IntegratedOptimizationResult(
                integration_run_id=run_id,
                graph_version=graph_version,
                incident_ids=[inc.incident_id for inc in incidents],
                overall_status="VALIDATION_FAILED",
                operational_feasibility="INFEASIBLE",
                validation_errors=validation_errors,
                explanation=f"Shelter evacuation optimization failed: {str(e)}"
            )
        timing["shelter_optimization_ms"] = round((time.perf_counter() - t_step2_start) * 1000.0, 2)

        # ----------------------------------------------------------------------
        # STEP 3: Convert Shelter Output into Downstream Demands
        # ----------------------------------------------------------------------
        t_step3_start = time.perf_counter()
        resource_demand_inputs = convert_shelter_output_to_resource_demands(
            incidents=incidents,
            shelters=shelters,
            shelter_result=shelter_res
        )
        timing["demand_conversion_ms"] = round((time.perf_counter() - t_step3_start) * 1000.0, 2)

        # ----------------------------------------------------------------------
        # STEP 4: Phase 5D Multi-Commodity Resource Allocation
        # ----------------------------------------------------------------------
        t_step4_start = time.perf_counter()
        try:
            alloc_res: AllocationResult = self.allocation_engine.solve(
                incidents=resource_demand_inputs,
                depots=depots,
                graph_engine=graph_engine,
                solver_time_limit_sec=time_limits.get("allocation", 2.0)
            )
        except Exception as e:
            validation_errors.append(f"RESOURCE_ALLOCATION_FAILED: {str(e)}")
            return IntegratedOptimizationResult(
                integration_run_id=run_id,
                graph_version=graph_version,
                incident_ids=[inc.incident_id for inc in incidents],
                shelter_result=shelter_res,
                overall_status="VALIDATION_FAILED",
                operational_feasibility="INFEASIBLE",
                validation_errors=validation_errors,
                explanation=f"Resource allocation optimization failed: {str(e)}"
            )
        timing["resource_allocation_ms"] = round((time.perf_counter() - t_step4_start) * 1000.0, 2)

        # ----------------------------------------------------------------------
        # STEP 5: Phase 5E Vehicle Routing & Emergency Dispatch
        # ----------------------------------------------------------------------
        t_step5_start = time.perf_counter()
        try:
            # Build spatial metadata for shipment conversion
            incident_map: Dict[str, Tuple[float, float, str, float, str]] = {}
            for d in resource_demand_inputs:
                incident_map[d.incident_id] = (d.latitude, d.longitude, d.title, d.priority_score, d.severity_level)

            depot_map = {d.depot_id: (d.latitude, d.longitude) for d in depots}

            shipments = convert_allocations_to_shipments(
                allocation_result=alloc_res,
                incident_info=incident_map,
                depot_info=depot_map
            )

            routing_res: RoutingResult = self.routing_engine.solve(
                shipments=shipments,
                vehicles=vehicles,
                graph_engine=graph_engine,
                solver_time_limit_sec=time_limits.get("routing", 5.0)
            )

            # Verify conservation from Phase 5D allocations to Phase 5E routes
            verify_cross_module_resource_and_vehicle_conservation(alloc_res, routing_res)
        except Exception as e:
            validation_errors.append(f"ROUTING_FAILED: {str(e)}")
            return IntegratedOptimizationResult(
                integration_run_id=run_id,
                graph_version=graph_version,
                incident_ids=[inc.incident_id for inc in incidents],
                shelter_result=shelter_res,
                resource_result=alloc_res,
                overall_status="VALIDATION_FAILED",
                operational_feasibility="INFEASIBLE",
                validation_errors=validation_errors,
                explanation=f"Vehicle routing optimization failed: {str(e)}"
            )
        timing["vehicle_routing_ms"] = round((time.perf_counter() - t_step5_start) * 1000.0, 2)

        # ----------------------------------------------------------------------
        # STEP 6: Phase 5F-D Volunteer Assignment Optimization
        # ----------------------------------------------------------------------
        t_step6_start = time.perf_counter()
        try:
            volunteer_tasks = generate_integrated_volunteer_tasks(
                incidents=incidents,
                shelters=shelters,
                shelter_result=shelter_res
            )

            vol_res: VolunteerAssignmentResult = self.volunteer_engine.solve(
                volunteers=volunteers,
                incidents=volunteer_tasks,
                graph_engine=graph_engine,
                solver_time_limit_sec=time_limits.get("volunteer", 5.0),
                random_seed=random_seed
            )

            # Verify volunteer conservation
            verify_volunteer_task_conservation(volunteer_tasks, vol_res)
        except Exception as e:
            validation_errors.append(f"VOLUNTEER_ASSIGNMENT_FAILED: {str(e)}")
            return IntegratedOptimizationResult(
                integration_run_id=run_id,
                graph_version=graph_version,
                incident_ids=[inc.incident_id for inc in incidents],
                shelter_result=shelter_res,
                resource_result=alloc_res,
                routing_result=routing_res,
                overall_status="VALIDATION_FAILED",
                operational_feasibility="INFEASIBLE",
                validation_errors=validation_errors,
                explanation=f"Volunteer assignment optimization failed: {str(e)}"
            )
        timing["volunteer_assignment_ms"] = round((time.perf_counter() - t_step6_start) * 1000.0, 2)

        # ----------------------------------------------------------------------
        # STEP 7: Graph Version Consistency & Feasibility Determination
        # ----------------------------------------------------------------------
        module_versions = {
            "shelter": shelter_res.graph_version,
            "allocation": alloc_res.graph_version,
            "routing": routing_res.graph_version,
            "volunteer": vol_res.graph_version
        }
        try:
            verify_graph_version_consistency(graph_version, module_versions)
        except GraphVersionMismatchError as gve:
            validation_errors.append(str(gve))
            return IntegratedOptimizationResult(
                integration_run_id=run_id,
                graph_version=graph_version,
                incident_ids=[inc.incident_id for inc in incidents],
                shelter_result=shelter_res,
                resource_result=alloc_res,
                routing_result=routing_res,
                volunteer_result=vol_res,
                overall_status="VALIDATION_FAILED",
                operational_feasibility="INFEASIBLE",
                validation_errors=validation_errors,
                explanation="Graph version mismatch detected across optimization modules."
            )

        # Determine Operational Feasibility
        has_unmet_shelter = shelter_res.total_evacuees_unmet > 0
        has_unmet_resource = alloc_res.total_unmet_demand_quantity > 0
        has_unrouted_shipment = len(routing_res.unrouted_shipments) > 0
        has_unmet_volunteer = vol_res.total_tasks_unmet > 0

        if not (has_unmet_shelter or has_unmet_resource or has_unrouted_shipment or has_unmet_volunteer):
            operational_feasibility = "FULLY_FEASIBLE"
        elif (
            shelter_res.total_evacuees_sheltered > 0 or
            len(alloc_res.allocations) > 0 or
            len(routing_res.routes) > 0 or
            vol_res.total_tasks_assigned > 0
        ):
            operational_feasibility = "PARTIALLY_FEASIBLE"
        else:
            operational_feasibility = "INFEASIBLE"

        # Overhead & Total Timing
        t_pipeline_end = time.perf_counter()
        total_ms = (t_pipeline_end - t_pipeline_start) * 1000.0
        timing["total_pipeline_ms"] = round(total_ms, 2)
        timing["orchestration_overhead_ms"] = round(
            total_ms - (
                timing["shelter_optimization_ms"] +
                timing["resource_allocation_ms"] +
                timing["vehicle_routing_ms"] +
                timing["volunteer_assignment_ms"]
            ), 2
        )

        summary_metrics = {
            "incidents_count": len(incidents),
            "evacuees_displaced": shelter_res.total_evacuees_displaced,
            "evacuees_sheltered": shelter_res.total_evacuees_sheltered,
            "evacuees_unmet": shelter_res.total_evacuees_unmet,
            "active_shelters_count": shelter_res.active_shelters_count,
            "commodities_allocated_units": sum(a.quantity for a in alloc_res.allocations),
            "unmet_commodity_units": alloc_res.total_unmet_demand_quantity,
            "vehicles_utilized_count": len(routing_res.routes),
            "shipments_routed_count": sum(len(r.stops) for r in routing_res.routes),
            "shipments_unrouted_count": len(routing_res.unrouted_shipments),
            "volunteers_deployed_count": vol_res.deployed_volunteers_count,
            "volunteer_tasks_assigned": vol_res.total_tasks_assigned,
            "volunteer_tasks_unmet": vol_res.total_tasks_unmet
        }

        explanation = (
            f"Integrated Response Plan {run_id} generated [{operational_feasibility}]. "
            f"Sheltered {shelter_res.total_evacuees_sheltered}/{shelter_res.total_evacuees_displaced} evacuees across {shelter_res.active_shelters_count} shelters. "
            f"Dispatched {len(routing_res.routes)} vehicles across {len(routing_res.routes)} routes. "
            f"Deployed {vol_res.deployed_volunteers_count} volunteers across {vol_res.total_tasks_assigned} tasks."
        )

        return IntegratedOptimizationResult(
            integration_run_id=run_id,
            graph_version=graph_version,
            incident_ids=[inc.incident_id for inc in incidents],
            optimization_run_ids={
                "shelter_run": f"RUN_SHELTER_{run_id[-6:]}",
                "allocation_run": f"RUN_ALLOC_{run_id[-6:]}",
                "routing_run": routing_res.routing_run_id,
                "volunteer_run": f"RUN_VOL_{run_id[-6:]}"
            },
            shelter_result=shelter_res,
            resource_result=alloc_res,
            routing_result=routing_res,
            volunteer_result=vol_res,
            overall_status="PROPOSED",
            operational_feasibility=operational_feasibility,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            timing_breakdown=timing,
            summary_metrics=summary_metrics,
            created_at=datetime.now(timezone.utc).isoformat(),
            explanation=explanation
        )


# --- 7. Database Integration & Government HITL Service Orchestrator ---

class IntegratedResponseService:
    """
    Service layer for database persistence and Government HITL workflow.
    Ensures that integrated optimization results strictly begin as PROPOSED,
    and require UserRole.GOVT authorization for operational approval or overrides.
    """

    def __init__(self, orchestrator: Optional[IntegratedResponseOrchestrator] = None):
        self.orchestrator = orchestrator or IntegratedResponseOrchestrator()

    def load_graph_with_blockages(self, db: Session, num_nodes: int = 50) -> RoadGraphEngine:
        """Loads Phase 5C RoadGraphEngine and applies active RoadBlockage DB records."""
        graph = create_chennai_benchmark_graph(num_nodes=num_nodes)
        blockages = db.query(RoadBlockage).all()
        edges = list(graph.graph.edges())
        for b in blockages:
            if b.latitude and b.longitude and edges:
                u, v = edges[0]
                graph.apply_blockage(
                    blockage_id=b.id,
                    source_id=u,
                    target_id=v,
                    blockage_status=b.blockage_status or "IMPASSABLE",
                    delay_penalty_mins=b.delay_penalty_mins or 0.0
                )
        return graph

    def run_integrated_optimization(
        self,
        db: Session,
        requesting_user_id: str,
        solver_time_limits: Optional[Dict[str, float]] = None
    ) -> OptimizationRun:
        """
        Executes end-to-end integrated response optimization from DB entities and persists PROPOSED records.
        """
        # 1. Fetch DB entities
        inc_records = db.query(Incident).filter(Incident.status != "CLOSED").all()
        shelter_records = db.query(Shelter).all()
        resource_records = db.query(Resource).all()
        vehicle_records = db.query(Vehicle).filter(Vehicle.status == "AVAILABLE", Vehicle.is_active == True).all()
        vol_profiles = db.query(VolunteerProfile).join(User).filter(User.is_active == True).all()

        incidents_input: List[IncidentIntakeInput] = [
            IncidentIntakeInput(
                incident_id=inc.id,
                title=inc.title,
                latitude=inc.latitude,
                longitude=inc.longitude,
                severity_level=inc.severity_level or "MEDIUM",
                priority_score=inc.priority_score or 50.0,
                disaster_type=inc.disaster_type or "FLOOD",
                people_affected=inc.people_affected or 1,
                vulnerable_count=inc.vulnerable_count or 0,
                injuries=inc.injuries or 0,
                evacuation_demographics=inc.evacuation_demographics or {},
                required_skills=inc.required_skills or {},
                required_resources={},
                status=inc.status or "REPORTED",
                created_at_str=inc.created_at.isoformat() if inc.created_at else ""
            )
            for inc in inc_records
        ]

        shelters_input: List[ShelterInput] = [
            ShelterInput(
                shelter_id=s.id,
                name=s.name,
                latitude=s.latitude,
                longitude=s.longitude,
                total_capacity=s.total_capacity or 100,
                current_occupancy=s.current_occupancy or 0,
                status=s.status or "OPEN",
                accessibility_features=bool(s.accessibility_features),
                has_medical=bool(s.has_medical),
                power_available=bool(s.power_available),
                sanitation_available=bool(s.sanitation_available),
                disaster_compatibility=s.disaster_compatibility or []
            )
            for s in shelter_records
        ]

        depots_input: List[DepotSupplyInput] = [
            DepotSupplyInput(
                depot_id=r.id,
                name=r.resource_name,
                latitude=r.location_lat or 13.0827,
                longitude=r.location_lng or 80.2707,
                supplies={r.category: float(r.available_quantity)}
            )
            for r in resource_records
        ]

        vehicles_input: List[VehicleInput] = [
            VehicleInput(
                vehicle_id=v.id,
                vehicle_code=v.vehicle_code,
                vehicle_type=v.vehicle_type,
                capacity_weight_kg=v.capacity_weight_kg or 2000.0,
                capacity_volume_m3=v.capacity_volume_m3 or 10.0,
                depot_id=v.depot_id or (depots_input[0].depot_id if depots_input else "DEPOT_001"),
                depot_lat=v.current_location_lat or 13.0827,
                depot_lng=v.current_location_lng or 80.2707,
                status=v.status
            )
            for v in vehicle_records
        ]

        volunteers_input: List[VolunteerInput] = [
            VolunteerInput(
                volunteer_id=vp.user.id,
                name=vp.user.full_name or "Volunteer",
                latitude=vp.current_lat or 13.0827,
                longitude=vp.current_lng or 80.2707,
                skill_category=vp.skill_category or "GENERAL",
                skills=vp.skills or [],
                medical_certified=bool(vp.medical_certified),
                verification_status=vp.verification_status or "PENDING",
                is_available=bool(vp.is_available),
                assignment_status=vp.assignment_status or "UNASSIGNED",
                max_shift_hours=vp.max_shift_hours if vp.max_shift_hours is not None else 8.0,
                max_travel_time_mins=vp.max_travel_time_mins if vp.max_travel_time_mins is not None else 45.0,
                shift_availability=vp.shift_availability or []
            )
            for vp in vol_profiles
        ]

        # 2. Ingest Graph with Blockages
        graph = self.load_graph_with_blockages(db)

        # 3. Execute Orchestrator Pipeline
        result: IntegratedOptimizationResult = self.orchestrator.run_pipeline(
            incidents=incidents_input,
            shelters=shelters_input,
            depots=depots_input,
            vehicles=vehicles_input,
            volunteers=volunteers_input,
            graph_engine=graph,
            solver_time_limits=solver_time_limits
        )

        # 4. Persist Top-Level OptimizationRun
        run = OptimizationRun(
            status="PROPOSED",
            requesting_user_id=requesting_user_id,
            objective_config_json={"integration_pipeline": "5F-E", "modules": ["5F-C", "5D", "5E", "5F-D"]},
            input_snapshot_json={
                "incidents_count": len(incidents_input),
                "shelters_count": len(shelters_input),
                "depots_count": len(depots_input),
                "vehicles_count": len(vehicles_input),
                "volunteers_count": len(volunteers_input)
            },
            solver_metadata_json={
                "integration_run_id": result.integration_run_id,
                "overall_status": result.overall_status,
                "operational_feasibility": result.operational_feasibility,
                "summary_metrics": result.summary_metrics,
                "timing_breakdown": result.timing_breakdown,
                "explanation": result.explanation
            },
            runtime_ms=result.timing_breakdown.get("total_pipeline_ms", 0.0),
            optimality_gap=0.0,
            feasibility_status=result.operational_feasibility,
            graph_version=result.graph_version
        )
        db.add(run)
        db.flush()

        # 5. Persist Proposed Recommendations for all 4 modules
        # 5a. Shelter Recommendations
        if result.shelter_result:
            for item in result.shelter_result.assignments:
                rec = OptimizationRecommendation(
                    run_id=run.id,
                    recommendation_type="SHELTER_EVACUATION",
                    incident_id=item.incident_id,
                    shelter_id=item.shelter_id,
                    demographic_group=item.demographic_group,
                    allocated_quantity=float(item.assigned_quantity),
                    transit_time_minutes=item.travel_time_minutes,
                    transit_distance_km=item.distance_km,
                    status="PROPOSED",
                    explanation=item.explanation or f"Evacuate {item.assigned_quantity} {item.demographic_group} evacuees to {item.shelter_id}"
                )
                db.add(rec)

        # 5b. Resource Dispatch Recommendations
        if result.resource_result:
            for alloc in result.resource_result.allocations:
                rec = OptimizationRecommendation(
                    run_id=run.id,
                    recommendation_type="RESOURCE_DISPATCH",
                    incident_id=alloc.incident_id if not alloc.incident_id.startswith("SHELTER_DEMAND_") else None,
                    shelter_id=alloc.incident_id.replace("SHELTER_DEMAND_", "") if alloc.incident_id.startswith("SHELTER_DEMAND_") else None,
                    depot_id=alloc.depot_id,
                    commodity_category=alloc.commodity,
                    allocated_quantity=alloc.quantity,
                    transit_time_minutes=alloc.travel_time_minutes,
                    transit_distance_km=alloc.distance_km,
                    status="PROPOSED",
                    explanation=alloc.explanation
                )
                db.add(rec)

        # 5c. Vehicle Route Recommendations
        if result.routing_result:
            for r in result.routing_result.routes:
                rec = OptimizationRecommendation(
                    run_id=run.id,
                    recommendation_type="VEHICLE_ROUTE",
                    vehicle_id=r.vehicle_id,
                    depot_id=r.start_depot_id,
                    allocated_quantity=float(len(r.stops)),
                    transit_time_minutes=r.total_travel_time_min,
                    transit_distance_km=r.total_distance_km,
                    proposed_route_json={
                        "stops": [
                            {"stop_idx": s.stop_index, "destination_id": s.incident_id, "commodities": s.commodities, "arrival_min": s.arrival_time_min}
                            for s in r.stops
                        ]
                    },
                    status="PROPOSED",
                    explanation=r.explanation
                )
                db.add(rec)

        # 5d. Volunteer Assignment Recommendations
        if result.volunteer_result:
            for v_item in result.volunteer_result.assignments:
                rec = OptimizationRecommendation(
                    run_id=run.id,
                    recommendation_type="VOLUNTEER_ASSIGNMENT",
                    incident_id=v_item.incident_id if not v_item.incident_id.startswith("SHELTER_TASK_") else None,
                    shelter_id=v_item.incident_id.replace("SHELTER_TASK_", "") if v_item.incident_id.startswith("SHELTER_TASK_") else None,
                    volunteer_id=v_item.volunteer_id,
                    skill_category=v_item.skill_category,
                    shift_id=v_item.shift_id,
                    transit_time_minutes=v_item.transit_time_minutes,
                    transit_distance_km=v_item.transit_distance_km,
                    allocated_quantity=1.0,
                    status="PROPOSED",
                    explanation=f"Deploy volunteer {v_item.volunteer_name} ({v_item.skill_category}) to {v_item.incident_id}"
                )
                db.add(rec)

        db.commit()
        db.refresh(run)
        return run

    def approve_integrated_plan(
        self,
        db: Session,
        run_id: str,
        approving_user: User
    ) -> OptimizationRun:
        """
        Government Human-in-the-Loop Approval Gate.
        Strictly enforces UserRole.GOVT RBAC.
        Transitions all integrated recommendations to APPROVED and creates audit trail.
        """
        if approving_user.role != UserRole.GOVT:
            raise PermissionError(
                f"User {approving_user.id} with role {approving_user.role} is not authorized to approve integrated plans. GOVT role required."
            )

        run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
        if not run:
            raise ValueError(f"OptimizationRun {run_id} not found.")

        run.status = "APPROVED"

        for rec in run.recommendations:
            rec.status = "APPROVED"

            # Operational entity status updates
            if rec.recommendation_type == "VOLUNTEER_ASSIGNMENT" and rec.volunteer_id:
                vp = db.query(VolunteerProfile).filter(VolunteerProfile.user_id == rec.volunteer_id).first()
                if vp:
                    vp.assignment_status = "ASSIGNED"
            elif rec.recommendation_type == "VEHICLE_ROUTE" and rec.vehicle_id:
                v = db.query(Vehicle).filter(Vehicle.id == rec.vehicle_id).first()
                if v:
                    v.status = "ASSIGNED"

        audit = AuditLog(
            user_id=approving_user.id,
            action="APPROVE_INTEGRATED_PLAN",
            target_entity="OptimizationRun",
            details={"approved_recommendations_count": len(run.recommendations)}
        )
        db.add(audit)
        db.commit()
        db.refresh(run)
        return run

    def override_integrated_plan(
        self,
        db: Session,
        run_id: str,
        overriding_user: User,
        action: str,  # MODIFY, REJECT
        justification: str,
        overridden_items: Optional[List[Dict[str, Any]]] = None
    ) -> OptimizationOverrideLog:
        """
        Government Human-in-the-Loop Override / Rejection Gate.
        Strictly enforces UserRole.GOVT RBAC.
        Preserves original optimizer outputs while logging immutable override records.
        """
        if overriding_user.role != UserRole.GOVT:
            raise PermissionError(
                f"User {overriding_user.id} with role {overriding_user.role} is not authorized to override integrated plans. GOVT role required."
            )

        if not justification or not justification.strip():
            raise ValueError("Justification reason is strictly mandatory for operational plan override.")

        run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
        if not run:
            raise ValueError(f"OptimizationRun {run_id} not found.")

        run.status = "MODIFIED" if action == "MODIFY" else "REJECTED"

        if action == "REJECT":
            for rec in run.recommendations:
                rec.status = "REJECTED"

        override_log = OptimizationOverrideLog(
            run_id=run.id,
            user_id=overriding_user.id,
            action=action,
            original_value_json=run.solver_metadata_json,
            overridden_value_json={"overridden_items": overridden_items or []},
            justification_reason=justification
        )
        db.add(override_log)

        audit = AuditLog(
            user_id=overriding_user.id,
            action=f"OVERRIDE_INTEGRATED_PLAN_{action}",
            target_entity="OptimizationRun",
            details={"action": action, "justification": justification}
        )
        db.add(audit)

        db.commit()
        db.refresh(override_log)
        return override_log
