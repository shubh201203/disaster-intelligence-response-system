"""
DIRS Phase 5G-B: Disaster Scenario / What-If Engine
Manages what-if scenarios, strict state isolation, deep copy cloning, and deterministic execution.
Classification: SYNTHETIC CALIBRATED SIMULATION / DECISION SUPPORT
"""
import copy
import hashlib
import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from app.ai.optimization.orchestrator import IncidentIntakeInput
from app.ai.optimization.shelter import ShelterInput
from app.ai.optimization.allocation import DepotSupplyInput
from app.ai.optimization.routing import VehicleInput
from enum import Enum
from app.ai.optimization.orchestrator import IncidentIntakeInput
from app.ai.optimization.shelter import ShelterInput
from app.ai.optimization.allocation import DepotSupplyInput
from app.ai.optimization.routing import VehicleInput
from app.ai.optimization.volunteer import VolunteerInput
from app.ai.optimization.graph import RoadGraphEngine


class ScenarioArchetype(str, Enum):
    SCENARIO_A_NEW_INCIDENT = "SCENARIO_A"
    SCENARIO_B_ROAD_CLOSURE = "SCENARIO_B"
    SCENARIO_C_SHELTER_LOSS = "SCENARIO_C"
    SCENARIO_D_DEPOT_DISRUPTION = "SCENARIO_D"
    SCENARIO_E_VEHICLE_LOSS = "SCENARIO_E"
    SCENARIO_F_VOLUNTEER_SHORTFALL = "SCENARIO_F"
    SCENARIO_G_COMBINED_ESCALATION = "SCENARIO_G"


@dataclass
class DisasterScenario:
    """Represents an isolated what-if disaster simulation scenario."""
    scenario_id: str = field(default_factory=lambda: f"SCEN_{uuid.uuid4().hex[:8]}")
    name: str = "Disaster Scenario"
    description: str = ""
    archetype: Optional[ScenarioArchetype] = None
    hazard_type: str = "FLOOD"
    severity_multiplier: float = 1.0
    affected_area_multiplier: float = 1.0
    volunteer_reduction_pct: float = 0.0
    new_incidents: List[Any] = field(default_factory=list)
    additional_blockages: List[Dict[str, Any]] = field(default_factory=list) # [{"u": "N1", "v": "N2", "status": "IMPASSABLE"}]
    shelter_capacity_changes: Dict[str, float] = field(default_factory=dict) # shelter_id -> capacity multiplier or delta
    depot_supply_changes: Dict[str, Dict[str, float]] = field(default_factory=dict) # depot_id -> commodity -> multiplier
    vehicle_availability_changes: List[str] = field(default_factory=list) # vehicle_ids to mark UNAVAILABLE
    volunteer_availability_changes: List[str] = field(default_factory=list) # volunteer_ids to mark unavailable
    seed: int = 42
    created_by: str = "GOVT_OFFICER"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "archetype": self.archetype.value if self.archetype else None,
            "hazard_type": self.hazard_type,
            "severity_multiplier": self.severity_multiplier,
            "affected_area_multiplier": self.affected_area_multiplier,
            "volunteer_reduction_pct": self.volunteer_reduction_pct,
            "new_incidents": self.new_incidents,
            "additional_blockages": self.additional_blockages,
            "shelter_capacity_changes": self.shelter_capacity_changes,
            "depot_supply_changes": self.depot_supply_changes,
            "vehicle_availability_changes": self.vehicle_availability_changes,
            "volunteer_availability_changes": self.volunteer_availability_changes,
            "seed": self.seed,
            "created_by": self.created_by,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DisasterScenario':
        archetype_val = data.get("archetype")
        archetype = None
        if archetype_val:
            try:
                archetype = ScenarioArchetype(archetype_val)
            except Exception:
                pass
        return cls(
            scenario_id=data.get("scenario_id", f"SCEN_{uuid.uuid4().hex[:8]}"),
            name=data.get("name", "Disaster Scenario"),
            description=data.get("description", ""),
            archetype=archetype,
            hazard_type=data.get("hazard_type", "FLOOD"),
            severity_multiplier=float(data.get("severity_multiplier", 1.0)),
            affected_area_multiplier=float(data.get("affected_area_multiplier", 1.0)),
            volunteer_reduction_pct=float(data.get("volunteer_reduction_pct", 0.0)),
            new_incidents=data.get("new_incidents", []),
            additional_blockages=data.get("additional_blockages", []),
            shelter_capacity_changes=data.get("shelter_capacity_changes", {}),
            depot_supply_changes=data.get("depot_supply_changes", {}),
            vehicle_availability_changes=data.get("vehicle_availability_changes", []),
            volunteer_availability_changes=data.get("volunteer_availability_changes", []),
            seed=int(data.get("seed", 42)),
            created_by=data.get("created_by", "GOVT_OFFICER"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat())
        )


@dataclass
class OperationalStateSnapshot:
    """An immutable operational state snapshot container."""
    incidents: List[Any]
    shelters: List[Any]
    depots: List[Any]
    vehicles: List[Any]
    volunteers: List[Any]
    graph_engine: RoadGraphEngine
    road_blockages: List[Any] = field(default_factory=list)

    def compute_state_hash(self) -> str:
        """Computes a deterministic SHA-256 fingerprint of the operational state."""
        hasher = hashlib.sha256()

        # Incident signature — supports ORM Incident (.id) and DTO IncidentIntakeInput (.incident_id)
        def _inc_id(x):
            return str(getattr(x, 'incident_id', None) or getattr(x, 'id', ''))
        def _inc_people(x):
            v = getattr(x, 'people_affected', None)
            return int(v) if v is not None else 50
        def _inc_score(x):
            v = getattr(x, 'priority_score', None)
            return float(v) if v is not None else 80.0
        for inc in sorted(self.incidents, key=_inc_id):
            hasher.update(f"{_inc_id(inc)}:{_inc_people(inc)}:{_inc_score(inc)}".encode("utf-8"))

        # Shelter signature — supports ORM Shelter (.id) and DTO ShelterInput (.shelter_id)
        def _sh_id(x):
            return str(getattr(x, 'shelter_id', None) or getattr(x, 'id', ''))
        def _sh_cap(x):
            v = getattr(x, 'total_capacity', None)
            return int(v) if v is not None else 0
        def _sh_occ(x):
            v = getattr(x, 'current_occupancy', None)
            return int(v) if v is not None else 0
        for s in sorted(self.shelters, key=_sh_id):
            hasher.update(f"{_sh_id(s)}:{_sh_cap(s)}:{_sh_occ(s)}".encode("utf-8"))

        # Depot signature — supports dict and DTO
        def _dep_id(x):
            if isinstance(x, dict):
                return str(x.get('id', x.get('depot_id', '')))
            return str(getattr(x, 'depot_id', getattr(x, 'id', '')))
        for d in sorted(self.depots, key=_dep_id):
            if isinstance(d, dict):
                dep_id = d.get('id', d.get('depot_id', ''))
                supplies = sorted(d.get('supplies', {}).items())
            else:
                dep_id = getattr(d, 'depot_id', '')
                supplies = sorted(d.supplies.items())
            hasher.update(f"{dep_id}:{supplies}".encode("utf-8"))

        # Vehicle signature — supports dict and DTO
        def _veh_id(x):
            if isinstance(x, dict):
                return str(x.get('id', x.get('vehicle_id', '')))
            return str(getattr(x, 'vehicle_id', getattr(x, 'id', '')))
        for v in sorted(self.vehicles, key=_veh_id):
            v_id = v.get('id', '') if isinstance(v, dict) else getattr(v, 'vehicle_id', '')
            v_status = v.get('status', '') if isinstance(v, dict) else getattr(v, 'status', '')
            hasher.update(f"{v_id}:{v_status}".encode("utf-8"))

        # Volunteer signature — normalize availability to bool so dict and DTO produce same hash
        def _vol_id(x):
            if isinstance(x, dict):
                return str(x.get('id', x.get('volunteer_id', '')))
            return str(getattr(x, 'volunteer_id', getattr(x, 'id', '')))
        def _vol_avail(x):
            if isinstance(x, dict):
                # dict uses 'status': 'AVAILABLE'/'UNAVAILABLE'
                return x.get('status', 'AVAILABLE') not in ('UNAVAILABLE', 'INACTIVE')
            # DTO VolunteerInput uses is_available bool
            return bool(getattr(x, 'is_available', True))
        for vol in sorted(self.volunteers, key=_vol_id):
            hasher.update(f"{_vol_id(vol)}:{_vol_avail(vol)}".encode("utf-8"))

        # Graph version signature
        hasher.update(self.graph_engine.get_graph_version().encode("utf-8"))
        return hasher.hexdigest()




def scale_demographics_proportionally(
    orig_demo: Dict[str, int],
    orig_people: int,
    new_people: int
) -> Dict[str, int]:
    """
    Scales demographic partitions proportionally using the Largest Remainder Method (Hare-Niemeyer).
    Guarantees:
      1. sum(demo.values()) == new_people exactly.
      2. demo[g] >= 0 for all g in {'GEN', 'ACC', 'MED', 'MED_ACC'}.
      3. Demographic proportions are preserved with minimal integer rounding distortion.
    """
    if new_people <= 0:
        return {"GEN": 0, "ACC": 0, "MED": 0, "MED_ACC": 0}

    groups = ["GEN", "ACC", "MED", "MED_ACC"]
    counts = {g: max(0, int(orig_demo.get(g, 0))) for g in groups}
    total_orig = sum(counts.values())

    if total_orig == 0:
        return {"GEN": new_people, "ACC": 0, "MED": 0, "MED_ACC": 0}

    # Hare-Niemeyer Quota Calculation
    quotas = {g: (counts[g] / total_orig) * new_people for g in groups}
    floors = {g: int(math.floor(quotas[g])) for g in groups}
    remainders = {g: quotas[g] - floors[g] for g in groups}

    remainder_units = new_people - sum(floors.values())
    # Deterministic tie-breaking priority: MED_ACC > MED > ACC > GEN
    priority = {"MED_ACC": 4, "MED": 3, "ACC": 2, "GEN": 1}
    sorted_groups = sorted(groups, key=lambda g: (remainders[g], priority[g]), reverse=True)

    for i in range(remainder_units):
        floors[sorted_groups[i % len(sorted_groups)]] += 1

    return floors


class ScenarioEngine:
    """
    Orchestrates what-if scenario generation, deep-copy state cloning,
    and strict isolation to guarantee base operational state immutability.
    """

    @staticmethod
    def _normalize_incidents(incidents: List[Any]) -> List[IncidentIntakeInput]:
        """Normalize any incident objects/dicts to IncidentIntakeInput DTOs."""
        result = []
        for inc in incidents:
            if isinstance(inc, IncidentIntakeInput):
                result.append(copy.deepcopy(inc))
                continue
            if isinstance(inc, dict):
                inc_id = str(inc.get('incident_id', inc.get('id', f'INC-{uuid.uuid4().hex[:6]}')))
                people = inc.get('people_affected', inc.get('evacuees', 50))
            else:
                inc_id = str(getattr(inc, 'incident_id', None) or getattr(inc, 'id', f'INC-{uuid.uuid4().hex[:6]}'))
                people = getattr(inc, 'people_affected', None)
                if isinstance(inc, dict):
                    people = inc.get('people_affected', 50)
            people = max(0, int(people) if people is not None else 50)
            raw_vuln = int(getattr(inc, 'vulnerable_count', None) or 0) if not isinstance(inc, dict) else int(inc.get('vulnerable_count', 0))
            raw_inj = int(getattr(inc, 'injuries', None) or 0) if not isinstance(inc, dict) else int(inc.get('injuries', 0))

            demo = getattr(inc, 'evacuation_demographics', None) if not isinstance(inc, dict) else inc.get('evacuation_demographics')
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
                injuries = min(rem, max(0, raw_inj))
                gen = max(0, rem - injuries)
                evac_demo = {"GEN": gen, "ACC": vuln, "MED": injuries, "MED_ACC": 0}

            result.append(IncidentIntakeInput(
                incident_id=inc_id,
                title=str(getattr(inc, 'title', None) or (inc.get('title', 'Incident') if isinstance(inc, dict) else 'Incident')),
                latitude=float(getattr(inc, 'latitude', None) or (inc.get('latitude', 13.0827) if isinstance(inc, dict) else 13.0827)),
                longitude=float(getattr(inc, 'longitude', None) or (inc.get('longitude', 80.2707) if isinstance(inc, dict) else 80.2707)),
                disaster_type=str(getattr(inc, 'disaster_type', None) or (inc.get('disaster_type', 'FLOOD') if isinstance(inc, dict) else 'FLOOD')),
                severity_level=str(getattr(inc, 'severity_level', None) or (inc.get('severity_level', 'CRITICAL') if isinstance(inc, dict) else 'CRITICAL')),
                priority_score=float(getattr(inc, 'priority_score', None) or (inc.get('priority_score', 80.0) if isinstance(inc, dict) else 80.0)),
                people_affected=people,
                vulnerable_count=vuln,
                injuries=injuries,
                evacuation_demographics=evac_demo,
                status=str(getattr(inc, 'status', None) or (inc.get('status', 'REPORTED') if isinstance(inc, dict) else 'REPORTED'))
            ))
        return result

    @staticmethod
    def _normalize_shelters(shelters: List[Any]) -> List[ShelterInput]:
        """Normalize any shelter objects/dicts to ShelterInput DTOs."""
        result = []
        for s in shelters:
            if isinstance(s, ShelterInput):
                result.append(copy.deepcopy(s))
                continue
            if isinstance(s, dict):
                s_id = str(s.get('shelter_id', s.get('id', f'SH-{uuid.uuid4().hex[:6]}')))
            else:
                s_id = str(getattr(s, 'shelter_id', None) or getattr(s, 'id', f'SH-{uuid.uuid4().hex[:6]}'))
            cap = getattr(s, 'total_capacity', None) if not isinstance(s, dict) else s.get('total_capacity')
            occ = getattr(s, 'current_occupancy', None) if not isinstance(s, dict) else s.get('current_occupancy')
            result.append(ShelterInput(
                shelter_id=s_id,
                name=str(getattr(s, 'name', None) or (s.get('name', 'Shelter') if isinstance(s, dict) else 'Shelter')),
                latitude=float(getattr(s, 'latitude', None) or (s.get('latitude', 13.08) if isinstance(s, dict) else 13.08)),
                longitude=float(getattr(s, 'longitude', None) or (s.get('longitude', 80.27) if isinstance(s, dict) else 80.27)),
                total_capacity=int(cap) if cap is not None else 200,
                current_occupancy=int(occ) if occ is not None else 0
            ))
        return result

    @staticmethod
    def _normalize_depots(depots: List[Any]) -> List[DepotSupplyInput]:
        """Normalize any depot objects/dicts to DepotSupplyInput DTOs."""
        result = []
        for d in depots:
            if isinstance(d, DepotSupplyInput):
                result.append(copy.deepcopy(d))
                continue
            if isinstance(d, dict):
                d_id = str(d.get('depot_id', d.get('id', f'DEPOT-{uuid.uuid4().hex[:6]}')))
                supplies = dict(d.get('supplies', {}))
                name = str(d.get('name', 'Depot'))
                lat = float(d.get('latitude', 13.085))
                lng = float(d.get('longitude', 80.27))
            else:
                d_id = str(getattr(d, 'depot_id', None) or getattr(d, 'id', f'DEPOT-{uuid.uuid4().hex[:6]}'))
                supplies = dict(getattr(d, 'supplies', {}))
                name = str(getattr(d, 'name', 'Depot'))
                lat = float(getattr(d, 'latitude', 13.085))
                lng = float(getattr(d, 'longitude', 80.27))
            result.append(DepotSupplyInput(
                depot_id=d_id,
                name=name,
                latitude=lat,
                longitude=lng,
                supplies=supplies
            ))
        return result

    @staticmethod
    def _normalize_vehicles(vehicles: List[Any]) -> List[VehicleInput]:
        """Normalize any vehicle objects/dicts to VehicleInput DTOs."""
        result = []
        for v in vehicles:
            if isinstance(v, VehicleInput):
                result.append(copy.deepcopy(v))
                continue
            if isinstance(v, dict):
                v_id = str(v.get('id', v.get('vehicle_id', f'VEH-{uuid.uuid4().hex[:6]}')))
                vtype = str(v.get('vehicle_type', 'TRUCK_HEAVY'))
                dep_id = str(v.get('depot_id', 'depot-1'))
                dep_lat = float(v.get('latitude', v.get('depot_lat', 13.085)))
                dep_lng = float(v.get('longitude', v.get('depot_lng', 80.27)))
                cap_kg = float(v.get('capacity_kg', v.get('capacity_weight_kg', 5000.0)))
                cap_m3 = float(v.get('capacity_volume_m3', 10.0))
                vstatus = str(v.get('status', 'AVAILABLE'))
            else:
                v_id = str(getattr(v, 'vehicle_id', None) or getattr(v, 'id', f'VEH-{uuid.uuid4().hex[:6]}'))
                vtype = str(getattr(v, 'vehicle_type', 'TRUCK_HEAVY'))
                dep_id = str(getattr(v, 'depot_id', 'depot-1'))
                dep_lat = float(getattr(v, 'depot_lat', getattr(v, 'latitude', 13.085)))
                dep_lng = float(getattr(v, 'depot_lng', getattr(v, 'longitude', 80.27)))
                cap_kg = float(getattr(v, 'capacity_kg', getattr(v, 'capacity_weight_kg', 5000.0)))
                cap_m3 = float(getattr(v, 'capacity_volume_m3', 10.0))
                vstatus = str(getattr(v, 'status', 'AVAILABLE'))
            result.append(VehicleInput(
                vehicle_id=v_id,
                vehicle_code=v_id,
                vehicle_type=vtype,
                depot_id=dep_id,
                depot_lat=dep_lat,
                depot_lng=dep_lng,
                capacity_weight_kg=cap_kg,
                capacity_volume_m3=cap_m3,
                status=vstatus
            ))
        return result

    @staticmethod
    def _normalize_volunteers(volunteers: List[Any]) -> List[VolunteerInput]:
        """Normalize any volunteer objects/dicts to VolunteerInput DTOs."""
        result = []
        for vol in volunteers:
            if isinstance(vol, VolunteerInput):
                result.append(copy.deepcopy(vol))
                continue
            if isinstance(vol, dict):
                vol_id = str(vol.get('id', vol.get('volunteer_id', f'VOL-{uuid.uuid4().hex[:6]}')))
                name = str(vol.get('full_name', vol.get('name', 'Volunteer')))
                lat = float(vol.get('latitude', 13.082))
                lng = float(vol.get('longitude', 80.272))
                is_med = bool(vol.get('medical_certified', False))
                is_avail = vol.get('status', 'AVAILABLE') != 'UNAVAILABLE'
                skills = vol.get('skills', ['MEDICAL'] if is_med else ['GENERAL'])
                skill_cat = 'MEDICAL' if is_med else 'GENERAL'
            else:
                vol_id = str(getattr(vol, 'volunteer_id', None) or getattr(vol, 'id', f'VOL-{uuid.uuid4().hex[:6]}'))
                name = str(getattr(vol, 'full_name', getattr(vol, 'name', 'Volunteer')))
                lat = float(getattr(vol, 'latitude', 13.082))
                lng = float(getattr(vol, 'longitude', 80.272))
                is_med = bool(getattr(vol, 'medical_certified', False))
                is_avail = bool(getattr(vol, 'is_available', True))
                skills = getattr(vol, 'skills', ['MEDICAL'] if is_med else ['GENERAL'])
                skill_cat = getattr(vol, 'skill_category', 'MEDICAL' if is_med else 'GENERAL')
            result.append(VolunteerInput(
                volunteer_id=vol_id,
                name=name,
                latitude=lat,
                longitude=lng,
                skill_category=skill_cat,
                skills=list(skills) if not isinstance(skills, list) else skills,
                medical_certified=is_med,
                is_available=is_avail
            ))
        return result


    @staticmethod
    def clone_base_state(state: OperationalStateSnapshot) -> OperationalStateSnapshot:
        """
        Creates a deep-copied, completely independent clone of the operational state snapshot.
        All entities are normalized to DTO types (IncidentIntakeInput, ShelterInput, etc.)
        so that the cloned state is always safe to pass directly to the optimization pipeline.
        The road graph is also cloned to allow isolated blockage applications.
        """
        cloned_incidents = ScenarioEngine._normalize_incidents(state.incidents)
        cloned_shelters = ScenarioEngine._normalize_shelters(state.shelters)
        cloned_depots = ScenarioEngine._normalize_depots(state.depots)
        cloned_vehicles = ScenarioEngine._normalize_vehicles(state.vehicles)
        cloned_volunteers = ScenarioEngine._normalize_volunteers(state.volunteers)
        cloned_graph = copy.deepcopy(state.graph_engine)

        return OperationalStateSnapshot(
            incidents=cloned_incidents,
            shelters=cloned_shelters,
            depots=cloned_depots,
            vehicles=cloned_vehicles,
            volunteers=cloned_volunteers,
            graph_engine=cloned_graph
        )


    @classmethod
    def apply_scenario(
        cls,
        base_state: OperationalStateSnapshot,
        scenario: DisasterScenario
    ) -> OperationalStateSnapshot:
        """
        Applies scenario mutations onto an ISOLATED deep copy of the base state.
        The input base_state is strictly guaranteed to remain untouched.
        """
        # 1. Create completely isolated clone
        scenario_state = cls.clone_base_state(base_state)

        # 2. Apply Severity & Population Multiplier to existing incidents
        if scenario.severity_multiplier != 1.0:
            m = max(0.0, float(scenario.severity_multiplier))
            for inc in scenario_state.incidents:
                if isinstance(inc, IncidentIntakeInput):
                    orig_people = inc.people_affected or 50
                    new_people = max(0, int(math.ceil(orig_people * m)))
                    inc.people_affected = new_people

                    demo = getattr(inc, 'evacuation_demographics', None)
                    if not demo:
                        v = min(orig_people, max(0, inc.vulnerable_count or 0))
                        rem = max(0, orig_people - v)
                        inj = min(rem, max(0, inc.injuries or 0))
                        demo = {"GEN": max(0, rem - inj), "ACC": v, "MED": inj, "MED_ACC": 0}

                    scaled_demo = scale_demographics_proportionally(demo, orig_people, new_people)
                    inc.evacuation_demographics = scaled_demo
                    inc.vulnerable_count = scaled_demo["ACC"] + scaled_demo["MED_ACC"]
                    inc.injuries = scaled_demo["MED"] + scaled_demo["MED_ACC"]

                elif isinstance(inc, dict):
                    curr = inc.get('people_affected', inc.get('evacuees', 50)) or 50
                    new_p = max(0, int(math.ceil(curr * m)))
                    inc['people_affected'] = new_p
                    if 'evacuees' in inc:
                        inc['evacuees'] = new_p

                    demo = inc.get('evacuation_demographics')
                    if not demo:
                        v = min(curr, max(0, inc.get('vulnerable_count', 0)))
                        rem = max(0, curr - v)
                        inj = min(rem, max(0, inc.get('injuries', 0)))
                        demo = {"GEN": max(0, rem - inj), "ACC": v, "MED": inj, "MED_ACC": 0}

                    scaled_demo = scale_demographics_proportionally(demo, curr, new_p)
                    inc['evacuation_demographics'] = scaled_demo
                    inc['vulnerable_count'] = scaled_demo["ACC"] + scaled_demo["MED_ACC"]
                    inc['injuries'] = scaled_demo["MED"] + scaled_demo["MED_ACC"]
                else:
                    # ORM Incident object
                    pa = getattr(inc, 'people_affected', None)
                    if pa is not None:
                        try:
                            inc.people_affected = max(0, int(math.ceil(pa * m)))
                        except Exception:
                            pass

        # 3. Inject New Incidents (Scenario A) — convert dicts to IncidentIntakeInput
        if scenario.new_incidents:
            for new_inc in scenario.new_incidents:
                if isinstance(new_inc, IncidentIntakeInput):
                    injected = copy.deepcopy(new_inc)
                    p = max(0, int(injected.people_affected or 0))
                    demo = injected.evacuation_demographics
                    if not demo or sum(demo.values()) > p or sum(demo.values()) == 0:
                        v = min(p, max(0, injected.vulnerable_count or 0))
                        rem = max(0, p - v)
                        inj = min(rem, max(0, injected.injuries or 0))
                        injected.evacuation_demographics = {
                            "GEN": max(0, rem - inj), "ACC": v, "MED": inj, "MED_ACC": 0
                        }
                    scenario_state.incidents.append(injected)
                elif isinstance(new_inc, dict):
                    inc_id = str(new_inc.get('incident_id', new_inc.get('id', f'SIM-INC-{uuid.uuid4().hex[:6]}')))
                    people = max(0, int(new_inc.get('evacuees', new_inc.get('people_affected', 50)) or 50))
                    raw_vuln = int(new_inc.get('vulnerable_count', max(0, people // 5)))
                    raw_inj = int(new_inc.get('injuries', max(0, people // 10)))

                    demo = new_inc.get('evacuation_demographics')
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
                        injuries = min(rem, max(0, raw_inj))
                        gen = max(0, rem - injuries)
                        evac_demo = {"GEN": gen, "ACC": vuln, "MED": injuries, "MED_ACC": 0}

                    converted = IncidentIntakeInput(
                        incident_id=inc_id,
                        title=str(new_inc.get('title', 'Simulated Incident')),
                        latitude=float(new_inc.get('latitude', 13.0827)),
                        longitude=float(new_inc.get('longitude', 80.2707)),
                        disaster_type=str(new_inc.get('disaster_type', 'FLOOD')),
                        severity_level=str(new_inc.get('severity', new_inc.get('severity_level', 'CRITICAL'))),
                        priority_score=float(new_inc.get('priority_score', 80.0)),
                        people_affected=people,
                        vulnerable_count=vuln,
                        injuries=injuries,
                        evacuation_demographics=evac_demo,
                        status=str(new_inc.get('status', 'REPORTED'))
                    )
                    scenario_state.incidents.append(converted)
                else:
                    scenario_state.incidents.append(copy.deepcopy(new_inc))

        # 4. Apply Road Blockages onto the isolated scenario graph (Scenario B)
        if scenario.additional_blockages:
            for idx, blk in enumerate(scenario.additional_blockages):
                u = blk.get("u")
                v = blk.get("v")
                status = blk.get("status", "IMPASSABLE")
                delay = blk.get("delay_factor", 1.0)
                blk_id = blk.get("blockage_id", f"SCENARIO_BLK_{idx+1}")
                if scenario_state.graph_engine.graph.has_edge(u, v):
                    scenario_state.graph_engine.apply_blockage(
                        blockage_id=blk_id,
                        source_id=u,
                        target_id=v,
                        blockage_status=status,
                        delay_penalty_mins=delay
                    )

        # 5. Apply Shelter Capacity Reductions (Scenario C)
        # Supports both ShelterInput DTOs (.shelter_id) and ORM Shelter objects (.id)
        if scenario.shelter_capacity_changes:
            for s in scenario_state.shelters:
                s_id = str(getattr(s, 'shelter_id', None) or getattr(s, 'id', ''))
                if s_id in scenario.shelter_capacity_changes:
                    change = scenario.shelter_capacity_changes[s_id]
                    current_cap = int(getattr(s, 'total_capacity', 200) or 200)
                    if 0.0 <= change <= 1.0:
                        new_cap = int(math.floor(current_cap * change))
                    else:
                        new_cap = max(0, int(change))
                    try:
                        s.total_capacity = new_cap
                    except AttributeError:
                        pass

        # 6. Apply Depot Supply Reductions (Scenario D)
        # Supports both DepotSupplyInput DTOs and dict depots
        if scenario.depot_supply_changes:
            for d in scenario_state.depots:
                if isinstance(d, dict):
                    d_id = str(d.get('depot_id', d.get('id', '')))
                    if d_id in scenario.depot_supply_changes:
                        comm_changes = scenario.depot_supply_changes[d_id]
                        supplies = d.get('supplies', {})
                        for comm, mult_or_val in comm_changes.items():
                            if comm in supplies:
                                if 0.0 <= mult_or_val <= 1.0:
                                    supplies[comm] = round(supplies[comm] * mult_or_val, 1)
                                else:
                                    supplies[comm] = max(0.0, float(mult_or_val))
                else:
                    d_id = str(getattr(d, 'depot_id', getattr(d, 'id', '')))
                    if d_id in scenario.depot_supply_changes:
                        comm_changes = scenario.depot_supply_changes[d_id]
                        supplies = getattr(d, 'supplies', {})
                        for comm, mult_or_val in comm_changes.items():
                            if comm in supplies:
                                if 0.0 <= mult_or_val <= 1.0:
                                    supplies[comm] = round(supplies[comm] * mult_or_val, 1)
                                else:
                                    supplies[comm] = max(0.0, float(mult_or_val))

        # 7. Apply Vehicle Loss (Scenario E)
        # Supports both VehicleInput DTOs and dict vehicles
        if scenario.vehicle_availability_changes:
            for v in scenario_state.vehicles:
                if isinstance(v, dict):
                    v_id = str(v.get('id', v.get('vehicle_id', '')))
                    if v_id in scenario.vehicle_availability_changes:
                        v['status'] = 'UNAVAILABLE'
                else:
                    v_id = str(getattr(v, 'vehicle_id', getattr(v, 'id', '')))
                    if v_id in scenario.vehicle_availability_changes:
                        try:
                            v.status = 'UNAVAILABLE'
                        except AttributeError:
                            pass

        # 8. Apply Volunteer Reductions (Scenario F)
        # Supports both VolunteerInput DTOs and dict volunteers
        if scenario.volunteer_availability_changes:
            for vol in scenario_state.volunteers:
                if isinstance(vol, dict):
                    vol_id = str(vol.get('id', vol.get('volunteer_id', '')))
                    if vol_id in scenario.volunteer_availability_changes:
                        vol['status'] = 'UNAVAILABLE'
                else:
                    vol_id = str(getattr(vol, 'volunteer_id', getattr(vol, 'id', '')))
                    if vol_id in scenario.volunteer_availability_changes:
                        try:
                            vol.is_available = False
                        except AttributeError:
                            pass

        return scenario_state


    # --------------------------------------------------------------------------
    # 7 Core Deterministic Scenario Factories
    # --------------------------------------------------------------------------

    @classmethod
    def create_scenario_a_additional_incident(
        cls, new_incident: IncidentIntakeInput, seed: int = 42
    ) -> DisasterScenario:
        """Scenario A: Additional flash incident appears in disaster zone."""
        return DisasterScenario(
            scenario_id=f"SCENARIO_A_{uuid.uuid4().hex[:6]}",
            name="Scenario A: Flash Inundation Escalation",
            description="Adds a sudden high-severity flooding incident requiring emergency evacuation and sustenance.",
            hazard_type="FLOOD",
            new_incidents=[new_incident],
            seed=seed
        )

    @classmethod
    def create_scenario_b_road_closure(
        cls, blocked_edges: List[Tuple[str, str]], seed: int = 42
    ) -> DisasterScenario:
        """Scenario B: Key arterial road links marked IMPASSABLE."""
        blockages = [
            {"u": u, "v": v, "status": "IMPASSABLE", "blockage_id": f"SCEN_BLK_{u}_{v}"}
            for u, v in blocked_edges
        ]
        return DisasterScenario(
            scenario_id=f"SCENARIO_B_{uuid.uuid4().hex[:6]}",
            name="Scenario B: Arterial Road Inundation & Closures",
            description="Key transit corridors rendered IMPASSABLE due to flash river overflow.",
            hazard_type="FLOOD",
            additional_blockages=blockages,
            seed=seed
        )

    @classmethod
    def create_scenario_c_shelter_loss(
        cls, affected_shelter_ids: List[str], reduction_ratio: float = 0.5, seed: int = 42
    ) -> DisasterScenario:
        """Scenario C: Structural damage reduces shelter capacity."""
        changes = {s_id: reduction_ratio for s_id in affected_shelter_ids}
        return DisasterScenario(
            scenario_id=f"SCENARIO_C_{uuid.uuid4().hex[:6]}",
            name="Scenario C: Shelter Roof Structural Damage",
            description=f"Reduces available capacity of specified shelters by {int((1-reduction_ratio)*100)}%.",
            hazard_type="CYCLONE",
            shelter_capacity_changes=changes,
            seed=seed
        )

    @classmethod
    def create_scenario_d_depot_supply_reduction(
        cls, depot_id: str, commodity: str, reduction_ratio: float = 0.2, seed: int = 42
    ) -> DisasterScenario:
        """Scenario D: Depot contamination reduces potable water or rations."""
        return DisasterScenario(
            scenario_id=f"SCENARIO_D_{uuid.uuid4().hex[:6]}",
            name="Scenario D: Depot Supply Contamination",
            description=f"Reduces available {commodity} supply at {depot_id} to {int(reduction_ratio*100)}%.",
            hazard_type="FLOOD",
            depot_supply_changes={depot_id: {commodity: reduction_ratio}},
            seed=seed
        )

    @classmethod
    def create_scenario_e_vehicle_loss(
        cls, lost_vehicle_ids: List[str], seed: int = 42
    ) -> DisasterScenario:
        """Scenario E: Emergency vehicles encounter mechanical failure / submersion."""
        return DisasterScenario(
            scenario_id=f"SCENARIO_E_{uuid.uuid4().hex[:6]}",
            name="Scenario E: Fleet Attrition / Vehicle Submersion",
            description=f"Marks {len(lost_vehicle_ids)} response vehicles as UNAVAILABLE.",
            hazard_type="FLOOD",
            vehicle_availability_changes=lost_vehicle_ids,
            seed=seed
        )

    @classmethod
    def create_scenario_f_volunteer_reduction(
        cls, unavailable_volunteer_ids: List[str], seed: int = 42
    ) -> DisasterScenario:
        """Scenario F: Volunteer responders delayed or trapped in transit."""
        return DisasterScenario(
            scenario_id=f"SCENARIO_F_{uuid.uuid4().hex[:6]}",
            name="Scenario F: Volunteer Workforce Shortage",
            description=f"Removes {len(unavailable_volunteer_ids)} volunteer responders from availability roster.",
            hazard_type="CYCLONE",
            volunteer_availability_changes=unavailable_volunteer_ids,
            seed=seed
        )

    @classmethod
    def create_scenario_g_combined_escalation(
        cls,
        new_incident: IncidentIntakeInput,
        blocked_edges: List[Tuple[str, str]],
        affected_shelter_ids: List[str],
        lost_vehicle_ids: List[str],
        seed: int = 42
    ) -> DisasterScenario:
        """Scenario G: Combined disaster escalation (multi-front simultaneous disruption)."""
        blockages = [
            {"u": u, "v": v, "status": "IMPASSABLE", "blockage_id": f"SCEN_COMB_BLK_{u}_{v}"}
            for u, v in blocked_edges
        ]
        shelter_changes = {s_id: 0.5 for s_id in affected_shelter_ids}
        return DisasterScenario(
            scenario_id=f"SCENARIO_G_{uuid.uuid4().hex[:6]}",
            name="Scenario G: Severe Multi-Front Disaster Escalation",
            description="Simultaneous new incident outbreak, arterial road closures, shelter loss, and vehicle attrition.",
            hazard_type="CYCLONE",
            severity_multiplier=1.2,
            affected_area_multiplier=1.3,
            new_incidents=[new_incident],
            additional_blockages=blockages,
            shelter_capacity_changes=shelter_changes,
            vehicle_availability_changes=lost_vehicle_ids,
            seed=seed
        )

    @classmethod
    def apply_scenario_to_state(
        cls,
        scenario: DisasterScenario,
        base_state: OperationalStateSnapshot
    ) -> OperationalStateSnapshot:
        return cls.apply_scenario(base_state, scenario)

    @classmethod
    def create_scenario_a(
        cls,
        name: str = "Scenario A",
        new_incidents: Optional[List[Any]] = None,
        seed: int = 42
    ) -> DisasterScenario:
        clamped_incidents = []
        for inc in (new_incidents or []):
            if isinstance(inc, dict):
                inc_copy = copy.deepcopy(inc)
                if "evacuees" in inc_copy:
                    inc_copy["evacuees"] = max(0, int(inc_copy["evacuees"]))
                clamped_incidents.append(inc_copy)
            else:
                clamped_incidents.append(inc)
        return DisasterScenario(
            name=name,
            archetype=ScenarioArchetype.SCENARIO_A_NEW_INCIDENT,
            new_incidents=clamped_incidents,
            seed=seed
        )

    @classmethod
    def create_scenario_b(
        cls,
        name: str = "Scenario B",
        closed_edges: Optional[List[Tuple[str, str]]] = None,
        seed: int = 42
    ) -> DisasterScenario:
        blockages = [
            {"u": u, "v": v, "status": "IMPASSABLE", "impassable": True, "blockage_id": f"SCEN_BLK_{u}_{v}"}
            for u, v in (closed_edges or [])
        ]
        return DisasterScenario(
            name=name,
            archetype=ScenarioArchetype.SCENARIO_B_ROAD_CLOSURE,
            additional_blockages=blockages,
            seed=seed
        )

    @classmethod
    def create_scenario_c(
        cls,
        name: str = "Scenario C",
        shelter_id: Optional[str] = None,
        capacity_reduction_factor: float = 0.5,
        seed: int = 42
    ) -> DisasterScenario:
        factor = max(0.0, min(1.0, float(capacity_reduction_factor)))
        changes = {shelter_id: factor} if shelter_id else {}
        return DisasterScenario(
            name=name,
            archetype=ScenarioArchetype.SCENARIO_C_SHELTER_LOSS,
            shelter_capacity_changes=changes,
            seed=seed
        )

    @classmethod
    def create_scenario_d(
        cls,
        name: str = "Scenario D",
        depot_id: Optional[str] = None,
        commodity: str = "WATER",
        remaining_factor: float = 0.2,
        seed: int = 42
    ) -> DisasterScenario:
        changes = {depot_id: {commodity: remaining_factor}} if depot_id else {}
        return DisasterScenario(
            name=name,
            archetype=ScenarioArchetype.SCENARIO_D_DEPOT_DISRUPTION,
            depot_supply_changes=changes,
            seed=seed
        )

    @classmethod
    def create_scenario_e(
        cls,
        name: str = "Scenario E",
        disabled_vehicle_ids: Optional[List[str]] = None,
        seed: int = 42
    ) -> DisasterScenario:
        return DisasterScenario(
            name=name,
            archetype=ScenarioArchetype.SCENARIO_E_VEHICLE_LOSS,
            vehicle_availability_changes=disabled_vehicle_ids or [],
            seed=seed
        )

    @classmethod
    def create_scenario_f(
        cls,
        name: str = "Scenario F",
        reduction_percentage: float = 40.0,
        seed: int = 42
    ) -> DisasterScenario:
        clamped_pct = max(0.0, min(100.0, float(reduction_percentage)))
        return DisasterScenario(
            name=name,
            archetype=ScenarioArchetype.SCENARIO_F_VOLUNTEER_SHORTFALL,
            volunteer_reduction_pct=clamped_pct,
            seed=seed
        )

    @classmethod
    def create_scenario_g(
        cls,
        name: str = "Scenario G",
        new_incidents: Optional[List[Any]] = None,
        closed_edges: Optional[List[Tuple[str, str]]] = None,
        disabled_vehicle_ids: Optional[List[str]] = None,
        volunteer_reduction_pct: float = 30.0,
        seed: int = 42
    ) -> DisasterScenario:
        blockages = [
            {"u": u, "v": v, "status": "IMPASSABLE", "impassable": True, "blockage_id": f"SCEN_BLK_{u}_{v}"}
            for u, v in (closed_edges or [])
        ]
        return DisasterScenario(
            name=name,
            archetype=ScenarioArchetype.SCENARIO_G_COMBINED_ESCALATION,
            new_incidents=new_incidents or [],
            additional_blockages=blockages,
            vehicle_availability_changes=disabled_vehicle_ids or [],
            volunteer_reduction_pct=volunteer_reduction_pct,
            seed=seed
        )

