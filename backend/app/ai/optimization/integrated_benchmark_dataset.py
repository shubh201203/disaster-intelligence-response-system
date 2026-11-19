"""
DIRS Phase 5F-E — Integrated Optimization Benchmark Dataset Generator
Generates coordinated problem instances for evaluating the end-to-end disaster response pipeline:
  Incidents -> Shelters -> Resource Depots -> Vehicles -> Volunteers
Classification: SYNTHETIC CALIBRATED BENCHMARK DATASET
Geographic Bounding Box: Coastal Chennai / Tamil Nadu Disaster Corridor (Lat: 12.65 - 13.15, Lng: 79.95 - 80.30)
"""
import random
from typing import List, Tuple, Dict, Any

from app.ai.optimization.orchestrator import IncidentIntakeInput
from app.ai.optimization.shelter import ShelterInput
from app.ai.optimization.allocation import DepotSupplyInput
from app.ai.optimization.routing import VehicleInput
from app.ai.optimization.volunteer import VolunteerInput

SEVERITY_LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
DISASTER_TYPES = ["FLOOD", "CYCLONE", "FIRE", "LANDSLIDE"]


def generate_integrated_benchmark_dataset(
    num_incidents: int = 10,
    num_shelters: int = 5,
    num_depots: int = 3,
    num_vehicles: int = 10,
    num_volunteers: int = 25,
    seed: int = 42
) -> Tuple[
    List[IncidentIntakeInput],
    List[ShelterInput],
    List[DepotSupplyInput],
    List[VehicleInput],
    List[VolunteerInput]
]:
    """
    Generates a deterministic coordinated problem instance for Phase 5F-E cross-module benchmarks.
    Tiers:
      - DIRS-INTEGRATED-10: 10 inc, 5 shelters, 3 depots, 10 vehicles, 25 volunteers
      - DIRS-INTEGRATED-25: 25 inc, 10 shelters, 5 depots, 20 vehicles, 50 volunteers
      - DIRS-INTEGRATED-50: 50 inc, 20 shelters, 8 depots, 35 vehicles, 100 volunteers
    """
    rng = random.Random(seed)

    # 1. Incidents
    incidents: List[IncidentIntakeInput] = []
    for idx in range(num_incidents):
        inc_id = f"INC_INT_{idx+1:03d}"
        lat = rng.uniform(12.75, 13.12)
        lng = rng.uniform(80.02, 80.26)
        sev = rng.choice(SEVERITY_LEVELS)
        prio = rng.uniform(50.0, 95.0)
        pop = rng.randint(50, 300)
        vuln = int(pop * rng.uniform(0.1, 0.25))
        inj = int(pop * rng.uniform(0.05, 0.12))
        gen = max(0, pop - vuln - inj)

        demo = {
            "GEN": gen,
            "ACC": vuln,
            "MED": inj,
            "MED_ACC": 0
        }

        # Skills required on site
        skills = {
            "GENERAL": rng.choice([1, 2, 3]),
            "MEDICAL": 1 if inj > 0 else 0,
            "RESCUE": rng.choice([0, 1, 2])
        }

        incidents.append(IncidentIntakeInput(
            incident_id=inc_id,
            title=f"Emergency Sector {idx+1}",
            latitude=lat,
            longitude=lng,
            severity_level=sev,
            priority_score=round(prio, 1),
            disaster_type="FLOOD",
            people_affected=pop,
            vulnerable_count=vuln,
            injuries=inj,
            evacuation_demographics=demo,
            required_skills=skills,
            required_resources={},
            status="REPORTED"
        ))

    # 2. Shelters
    shelters: List[ShelterInput] = []
    for idx in range(num_shelters):
        s_id = f"SHELTER_INT_{idx+1:03d}"
        lat = rng.uniform(12.72, 13.15)
        lng = rng.uniform(80.00, 80.28)
        cap = rng.choice([300, 500, 800, 1200])

        shelters.append(ShelterInput(
            shelter_id=s_id,
            name=f"Relief Facility {idx+1}",
            latitude=lat,
            longitude=lng,
            total_capacity=cap,
            current_occupancy=0,
            status="OPEN",
            accessibility_features=rng.random() > 0.3,
            has_medical=rng.random() > 0.3,
            has_food=True,
            has_water=True,
            power_available=True,
            sanitation_available=True,
            disaster_compatibility=["FLOOD", "CYCLONE"]
        ))

    # 3. Resource Depots
    depots: List[DepotSupplyInput] = []
    for idx in range(num_depots):
        d_id = f"DEPOT_INT_{idx+1:03d}"
        lat = rng.uniform(12.70, 13.10)
        lng = rng.uniform(80.05, 80.25)

        supplies = {
            "WATER": float(rng.randint(20000, 50000)),
            "FOOD": float(rng.randint(5000, 15000)),
            "MEDICAL_KITS": float(rng.randint(200, 500)),
            "SANITATION_KITS": float(rng.randint(500, 1000)),
            "TEMPORARY_SHELTER_SUPPLIES": float(rng.randint(100, 400)),
            "RESCUE_EQUIPMENT": float(rng.randint(50, 150))
        }

        depots.append(DepotSupplyInput(
            depot_id=d_id,
            name=f"Central Logistics Hub {idx+1}",
            latitude=lat,
            longitude=lng,
            supplies=supplies
        ))

    # 4. Vehicles
    vehicles: List[VehicleInput] = []
    for idx in range(num_vehicles):
        v_id = f"VEH_INT_{idx+1:03d}"
        d_assigned = depots[idx % len(depots)]
        v_type = rng.choice(["TRUCK", "VAN", "AMBULANCE"])

        if v_type == "TRUCK":
            w_cap = 5000.0
            v_cap = 25.0
        elif v_type == "VAN":
            w_cap = 2000.0
            v_cap = 10.0
        else:
            w_cap = 1000.0
            v_cap = 5.0

        vehicles.append(VehicleInput(
            vehicle_id=v_id,
            vehicle_code=f"DISP-{idx+1:03d}",
            vehicle_type=v_type,
            capacity_weight_kg=w_cap,
            capacity_volume_m3=v_cap,
            depot_id=d_assigned.depot_id,
            depot_lat=d_assigned.latitude,
            depot_lng=d_assigned.longitude,
            status="AVAILABLE"
        ))

    # 5. Volunteers
    volunteers: List[VolunteerInput] = []
    for idx in range(num_volunteers):
        vol_id = f"VOL_INT_{idx+1:04d}"
        lat = rng.uniform(12.72, 13.16)
        lng = rng.uniform(80.00, 80.28)

        roll = rng.random()
        if roll < 0.20:
            cat = "MEDICAL"
            cert = True
            skills = ["Emergency First Aid", "Triage"]
        elif roll < 0.35:
            cat = "RESCUE"
            cert = False
            skills = ["Swift Water Rescue"]
        elif roll < 0.55:
            cat = "LOGISTICS"
            cert = False
            skills = ["Warehouse Logistics", "Driving"]
        else:
            cat = "GENERAL"
            cert = False
            skills = ["Community Assistance"]

        volunteers.append(VolunteerInput(
            volunteer_id=vol_id,
            name=f"Volunteer Responder {idx+1}",
            latitude=lat,
            longitude=lng,
            skill_category=cat,
            skills=skills,
            medical_certified=cert,
            verification_status="VERIFIED",
            is_available=True,
            assignment_status="UNASSIGNED",
            max_shift_hours=8.0,
            max_travel_time_mins=45.0,
            shift_availability=["SHIFT_1"]
        ))

    return incidents, shelters, depots, vehicles, volunteers


def generate_dirs_integrated_10(seed: int = 42):
    return generate_integrated_benchmark_dataset(
        num_incidents=10, num_shelters=5, num_depots=3, num_vehicles=10, num_volunteers=25, seed=seed
    )


def generate_dirs_integrated_25(seed: int = 42):
    return generate_integrated_benchmark_dataset(
        num_incidents=25, num_shelters=10, num_depots=5, num_vehicles=20, num_volunteers=50, seed=seed
    )


def generate_dirs_integrated_50(seed: int = 42):
    return generate_integrated_benchmark_dataset(
        num_incidents=50, num_shelters=20, num_depots=8, num_vehicles=35, num_volunteers=100, seed=seed
    )
