"""
DIRS Phase 5G: Disaster Simulation API Router
Manages what-if scenario creation, response simulation runs, multi-scenario comparisons, and audit records.
Classification: SYNTHETIC CALIBRATED SIMULATION / DECISION SUPPORT
"""
import uuid
import copy
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.deps import get_current_user, require_role
from app.models.simulation import SimulationScenario, SimulationRun
from app.ai.simulation.scenario_engine import (
    DisasterScenario,
    OperationalStateSnapshot,
    ScenarioEngine
)
from app.ai.simulation.response_simulator import ResponseSimulator
from app.ai.simulation.comparison_engine import ComparisonAndIntelligenceEngine
from app.ai.simulation.gis_situation import GISSituationLayerBuilder
from app.ai.optimization.orchestrator import IncidentIntakeInput
from app.ai.optimization.integrated_benchmark_dataset import (
    generate_dirs_integrated_10,
    generate_dirs_integrated_25,
    generate_dirs_integrated_50
)
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph
from app.schemas.simulation import (
    ScenarioCreateRequest,
    ScenarioResponse,
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationAlert,
    MultiScenarioCompareRequest,
    MultiScenarioCompareResponse,
    ScenarioComparisonItem
)

router = APIRouter(prefix="/simulation", tags=["Disaster Simulation & Intelligence"])

# In-memory simulator registry for scenario execution
_SIMULATOR = ResponseSimulator()


def _to_incident_input(item: Any) -> IncidentIntakeInput:
    """Safely converts dict or object to IncidentIntakeInput."""
    if isinstance(item, IncidentIntakeInput):
        return item
    if hasattr(item, "model_dump"):
        data = item.model_dump()
    elif hasattr(item, "dict"):
        data = item.dict()
    elif isinstance(item, dict):
        data = item
    else:
        data = {
            "id": getattr(item, "id", None),
            "title": getattr(item, "title", None),
            "latitude": getattr(item, "latitude", 13.0827),
            "longitude": getattr(item, "longitude", 80.2707),
            "disaster_type": getattr(item, "disaster_type", "FLOOD"),
            "severity_level": getattr(item, "severity_level", getattr(item, "severity", "CRITICAL")),
            "priority_score": getattr(item, "priority_score", 80.0),
            "people_affected": getattr(item, "people_affected", getattr(item, "evacuees", 50)),
            "vulnerable_count": getattr(item, "vulnerable_count", 10),
            "injuries": getattr(item, "injuries", 5),
            "status": getattr(item, "status", "REPORTED")
        }

    inc_id = str(data.get("incident_id") or data.get("id") or f"INC-{uuid.uuid4().hex[:6]}")
    title = str(data.get("title") or "Simulated Incident")
    lat = float(data.get("latitude", 13.0827))
    lng = float(data.get("longitude", 80.2707))
    disaster_type = str(data.get("disaster_type", "FLOOD"))
    severity = str(data.get("severity_level") or data.get("severity", "CRITICAL"))
    priority = float(data.get("priority_score", 80.0))
    people = max(0, int(data.get("people_affected") if data.get("people_affected") is not None else data.get("evacuees", 50)))
    raw_vuln = int(data.get("vulnerable_count", int(people * 0.2)))
    raw_injuries = int(data.get("injuries", int(people * 0.1)))
    status_str = str(data.get("status", "REPORTED"))

    demo = data.get("evacuation_demographics")
    if isinstance(demo, dict) and sum(demo.values()) <= people and sum(demo.values()) > 0:
        v = int(demo.get("ACC", 0))
        inj = int(demo.get("MED", 0))
        med_acc = int(demo.get("MED_ACC", 0))
        gen = max(0, people - v - inj - med_acc)
        evac_demo = {"GEN": gen, "ACC": v, "MED": inj, "MED_ACC": med_acc}
        vuln = v + med_acc
        injuries = inj + med_acc
    else:
        vuln = min(people, max(0, raw_vuln))
        rem = max(0, people - vuln)
        injuries = min(rem, max(0, raw_injuries))
        gen = max(0, rem - injuries)
        evac_demo = {"GEN": gen, "ACC": vuln, "MED": injuries, "MED_ACC": 0}

    return IncidentIntakeInput(
        incident_id=inc_id,
        title=title,
        latitude=lat,
        longitude=lng,
        disaster_type=disaster_type,
        severity_level=severity,
        priority_score=priority,
        people_affected=people,
        vulnerable_count=vuln,
        injuries=injuries,
        evacuation_demographics=evac_demo,
        status=status_str
    )


def _load_base_state(workload: str) -> OperationalStateSnapshot:
    """Loads operational state snapshot for benchmark workload."""
    if workload == "DIRS-GIS-25":
        incidents, shelters, depots, vehicles, volunteers = generate_dirs_integrated_25()
        graph = create_chennai_benchmark_graph(num_nodes=50, seed=42)
    elif workload == "DIRS-GIS-50":
        incidents, shelters, depots, vehicles, volunteers = generate_dirs_integrated_50()
        graph = create_chennai_benchmark_graph(num_nodes=100, seed=42)
    else: # DIRS-GIS-10
        incidents, shelters, depots, vehicles, volunteers = generate_dirs_integrated_10()
        graph = create_chennai_benchmark_graph(num_nodes=50, seed=42)

    return OperationalStateSnapshot(
        incidents=incidents,
        shelters=shelters,
        depots=depots,
        vehicles=vehicles,
        volunteers=volunteers,
        graph_engine=graph
    )


@router.post("/scenarios", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    req: ScenarioCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
) -> ScenarioResponse:
    """Creates and persists a new disaster what-if scenario."""
    scen_id = f"SCEN_{uuid.uuid4().hex[:8]}"
    params = {
        "new_incidents": req.new_incidents,
        "additional_blockages": req.additional_blockages,
        "shelter_capacity_changes": req.shelter_capacity_changes,
        "depot_supply_changes": req.depot_supply_changes,
        "vehicle_availability_changes": req.vehicle_availability_changes,
        "volunteer_availability_changes": req.volunteer_availability_changes
    }

    scen_record = SimulationScenario(
        id=scen_id,
        name=req.name,
        description=req.description,
        hazard_type=req.hazard_type,
        severity_multiplier=req.severity_multiplier,
        affected_area_multiplier=req.affected_area_multiplier,
        scenario_parameters_json=params,
        seed=req.seed,
        created_by_user_id=current_user.id
    )
    db.add(scen_record)
    db.commit()
    db.refresh(scen_record)

    return ScenarioResponse(
        id=scen_record.id,
        name=scen_record.name,
        description=scen_record.description,
        hazard_type=scen_record.hazard_type,
        severity_multiplier=scen_record.severity_multiplier,
        affected_area_multiplier=scen_record.affected_area_multiplier,
        scenario_parameters=scen_record.scenario_parameters_json,
        seed=scen_record.seed,
        created_at=scen_record.created_at.isoformat() if scen_record.created_at else ""
    )


@router.get("/scenarios", response_model=List[ScenarioResponse])
async def list_scenarios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[ScenarioResponse]:
    """Lists all registered simulation scenarios."""
    records = db.query(SimulationScenario).all()
    return [
        ScenarioResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            hazard_type=r.hazard_type,
            severity_multiplier=r.severity_multiplier,
            affected_area_multiplier=r.affected_area_multiplier,
            scenario_parameters=r.scenario_parameters_json or {},
            seed=r.seed,
            created_at=r.created_at.isoformat() if r.created_at else ""
        )
        for r in records
    ]


@router.post("/run", response_model=SimulationRunResponse)
async def run_simulation(
    req: SimulationRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
) -> SimulationRunResponse:
    """
    Executes a response simulation for a scenario against the specified base operational state.
    Strictly isolated: does NOT mutate live operational plans or trigger dispatches.
    """
    base_state = _load_base_state(req.base_workload)

    # 1. Resolve Scenario
    scenario_obj: Optional[DisasterScenario] = None

    if req.scenario_id:
        record = db.query(SimulationScenario).filter(SimulationScenario.id == req.scenario_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Scenario not found")
        p = record.scenario_parameters_json or {}
        new_incs = [_to_incident_input(item) for item in p.get("new_incidents", [])]
        scenario_obj = DisasterScenario(
            scenario_id=record.id,
            name=record.name,
            description=record.description or "",
            hazard_type=record.hazard_type,
            severity_multiplier=record.severity_multiplier,
            affected_area_multiplier=record.affected_area_multiplier,
            new_incidents=new_incs,
            additional_blockages=p.get("additional_blockages", []),
            shelter_capacity_changes=p.get("shelter_capacity_changes", {}),
            depot_supply_changes=p.get("depot_supply_changes", {}),
            vehicle_availability_changes=p.get("vehicle_availability_changes", []),
            volunteer_availability_changes=p.get("volunteer_availability_changes", []),
            seed=req.seed or record.seed
        )
    elif req.inline_scenario:
        p = req.inline_scenario
        new_incs = [_to_incident_input(item) for item in p.new_incidents]
        scenario_obj = DisasterScenario(
            scenario_id=f"INLINE_{uuid.uuid4().hex[:6]}",
            name=p.name,
            description=p.description or "",
            hazard_type=p.hazard_type,
            severity_multiplier=p.severity_multiplier,
            affected_area_multiplier=p.affected_area_multiplier,
            new_incidents=new_incs,
            additional_blockages=p.additional_blockages,
            shelter_capacity_changes=p.shelter_capacity_changes,
            depot_supply_changes=p.depot_supply_changes,
            vehicle_availability_changes=p.vehicle_availability_changes,
            volunteer_availability_changes=p.volunteer_availability_changes,
            seed=req.seed or p.seed
        )
    else:
        # Default No-op baseline simulation
        scenario_obj = DisasterScenario(
            scenario_id="SCEN_NOOP",
            name="No-Op Baseline Scenario",
            description="Zero scenario modifications.",
            seed=req.seed
        )

    # 2. Execute Isolated Simulation
    sim_result = _SIMULATOR.simulate_scenario(base_state, scenario_obj)

    # 3. Intelligence Observations & Threshold Alerts
    observations = ComparisonAndIntelligenceEngine.generate_intelligence_observations(sim_result.delta)
    alerts = ComparisonAndIntelligenceEngine.evaluate_critical_threshold_alerts(sim_result.delta)

    # 4. Persist Audit Record
    run_record = SimulationRun(
        id=sim_result.simulation_id,
        scenario_id=req.scenario_id,
        scenario_name=scenario_obj.name,
        status="PROPOSED",
        disclaimer="SIMULATED IMPACT: This is a decision-support simulation. Live operational state is unmodified.",
        base_state_hash=sim_result.base_state_hash,
        result_hash=sim_result.result_hash,
        graph_version=sim_result.graph_version,
        seed=sim_result.seed,
        delta_metrics_json=sim_result.delta.to_dict(),
        intelligence_observations_json=observations,
        critical_alerts_json=[a.model_dump() if hasattr(a, 'model_dump') else a.dict() for a in alerts],
        audit_trail_json={
            "scenario_name": scenario_obj.name,
            "hazard_type": scenario_obj.hazard_type,
            "timing_ms": sim_result.timing_breakdown,
            "executed_at": datetime.now(timezone.utc).isoformat()
        },
        created_by_user_id=current_user.id
    )
    db.add(run_record)
    db.commit()

    return SimulationRunResponse(
        simulation_id=sim_result.simulation_id,
        scenario_id=req.scenario_id,
        scenario_name=scenario_obj.name,
        status="PROPOSED",
        disclaimer="SIMULATED IMPACT: This is a decision-support simulation. Live operational state is unmodified.",
        base_state_hash=sim_result.base_state_hash,
        result_hash=sim_result.result_hash,
        graph_version=sim_result.graph_version,
        seed=sim_result.seed,
        delta=sim_result.delta.to_dict(),
        intelligence_observations=observations,
        critical_alerts=alerts,
        timing_breakdown=sim_result.timing_breakdown,
        created_at=datetime.now(timezone.utc).isoformat()
    )


@router.post("/compare", response_model=MultiScenarioCompareResponse)
@router.post("/scenarios/compare", response_model=MultiScenarioCompareResponse)
async def compare_scenarios(
    req: MultiScenarioCompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
) -> MultiScenarioCompareResponse:
    """Compares multiple simulation scenarios side-by-side against a base operational state."""
    scenarios_to_compare: List[DisasterScenario] = []

    for s_id in req.scenario_ids:
        record = db.query(SimulationScenario).filter(SimulationScenario.id == s_id).first()
        if not record:
            continue
        p = record.scenario_parameters_json or {}
        new_incs = [_to_incident_input(item) for item in p.get("new_incidents", [])]
        scenarios_to_compare.append(DisasterScenario(
            scenario_id=record.id,
            name=record.name,
            description=record.description or "",
            hazard_type=record.hazard_type,
            severity_multiplier=record.severity_multiplier,
            affected_area_multiplier=record.affected_area_multiplier,
            new_incidents=new_incs,
            additional_blockages=p.get("additional_blockages", []),
            shelter_capacity_changes=p.get("shelter_capacity_changes", {}),
            depot_supply_changes=p.get("depot_supply_changes", {}),
            vehicle_availability_changes=p.get("vehicle_availability_changes", []),
            volunteer_availability_changes=p.get("volunteer_availability_changes", []),
            seed=req.seed or record.seed
        ))

    if not scenarios_to_compare:
        raise HTTPException(status_code=400, detail="No valid scenarios found to compare")

    return ComparisonAndIntelligenceEngine.compare_scenarios(
        base_workload=req.base_workload,
        scenarios=scenarios_to_compare,
        seed=req.seed
    )


@router.get("/audit/{simulation_id}", response_model=Dict[str, Any])
async def get_simulation_audit(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
) -> Dict[str, Any]:
    """Retrieves full reproducibility audit trail for a simulated response run."""
    run = db.query(SimulationRun).filter(SimulationRun.id == simulation_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found")

    return {
        "id": run.id,
        "scenario_id": run.scenario_id,
        "status": run.status,
        "disclaimer": run.disclaimer,
        "base_state_hash": run.base_state_hash,
        "result_hash": run.result_hash,
        "graph_version": run.graph_version,
        "seed": run.seed,
        "delta_metrics": run.delta_metrics_json,
        "intelligence_observations": run.intelligence_observations_json,
        "critical_alerts": run.critical_alerts_json,
        "audit_trail": run.audit_trail_json,
        "created_at": run.created_at.isoformat() if run.created_at else None
    }
