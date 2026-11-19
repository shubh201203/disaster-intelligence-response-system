"""
DIRS Phase 5F-D — Volunteer Assignment Benchmark Dataset Generator
Classification: SYNTHETIC CALIBRATED BENCHMARK DATASET
Geographic bounding box: Coastal Chennai / Tamil Nadu Disaster Corridor (Lat: 12.65 - 13.15, Lng: 79.95 - 80.30)
"""
import random
from typing import List, Tuple
from app.ai.optimization.volunteer import VolunteerInput, IncidentTaskInput

SEVERITY_LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def generate_volunteer_benchmark_dataset(
    num_incidents: int = 25,
    num_volunteers: int = 50,
    num_shifts: int = 1,
    seed: int = 42
) -> Tuple[List[IncidentTaskInput], List[VolunteerInput]]:
    """
    Generates a deterministic reproducible benchmark dataset for Phase 5F-D volunteer assignment optimization.
    Tiers:
    - DIRS-VOL-10: 10 incidents, 25 volunteers, 1 shift
    - DIRS-VOL-25: 25 incidents, 50 volunteers, 1 shift
    - DIRS-VOL-50: 50 incidents, 100 volunteers, 2 shifts
    - DIRS-VOL-100: 100 incidents, 250 volunteers, 3 shifts
    """
    rng = random.Random(seed)

    shifts = [f"SHIFT_{t+1}" for t in range(num_shifts)]

    # 1. Incident Generation
    incident_anchors = [
        ("Saidapet Evacuation Staging Zone", 13.0180, 80.2220, "CRITICAL", 92.0),
        ("Velachery Inundation Command Post", 12.9750, 80.2200, "CRITICAL", 88.0),
        ("Adyar Basin Relief Cluster", 13.0050, 80.2450, "HIGH", 82.0),
        ("Madipakkam Waterlogged Sector", 12.9620, 80.1980, "HIGH", 76.0),
        ("Pallikaranai Relief Depot", 12.9350, 80.2150, "MEDIUM", 65.0),
        ("Tambaram Mudichur Triage Site", 12.9150, 80.0850, "HIGH", 79.0),
        ("Koyambedu Medical Aid Post", 13.0690, 80.1940, "CRITICAL", 95.0),
        ("Perambur Rail Corridor Camp", 13.1110, 80.2420, "MEDIUM", 60.0),
        ("Ennore Creek Response Point", 13.2050, 80.3150, "HIGH", 84.0),
        ("Tondiarpet Logistics Base", 13.1250, 80.2850, "LOW", 45.0),
    ]

    incidents: List[IncidentTaskInput] = []
    for idx in range(num_incidents):
        inc_id = f"INC_VOL_{idx+1:03d}"
        if idx < len(incident_anchors):
            title, lat, lng, sev, prio = incident_anchors[idx]
        else:
            title = f"District Sector {idx+1} Emergency Task Site"
            lat = rng.uniform(12.72, 13.15)
            lng = rng.uniform(80.00, 80.28)
            sev = rng.choice(SEVERITY_LEVELS)
            prio = rng.uniform(40.0, 98.0)

        # Calibrated task demands per incident:
        # e.g. 1-2 medical, 1-2 rescue, 1-3 general, 0-2 logistics
        med_req = rng.choice([0, 1, 1, 2])
        res_req = rng.choice([0, 1, 1, 2])
        gen_req = rng.choice([1, 2, 2, 3])
        log_req = rng.choice([0, 1, 2])

        req_skills = {}
        if med_req > 0:
            req_skills["MEDICAL"] = med_req
        if res_req > 0:
            req_skills["RESCUE"] = res_req
        if gen_req > 0:
            req_skills["GENERAL"] = gen_req
        if log_req > 0:
            req_skills["LOGISTICS"] = log_req

        # Ensure at least one task
        if not req_skills:
            req_skills["GENERAL"] = 1

        durations = {s: rng.choice([4.0, 6.0, 8.0]) for s in shifts}

        incidents.append(IncidentTaskInput(
            incident_id=inc_id,
            title=title,
            latitude=lat,
            longitude=lng,
            priority_score=round(prio, 1),
            severity_level=sev,
            required_skills=req_skills,
            shifts=list(shifts),
            task_durations=durations
        ))

    # 2. Volunteer Generation
    # Skill shares: 50% GENERAL, 20% LOGISTICS, 18% MEDICAL, 12% RESCUE
    volunteers: List[VolunteerInput] = []
    for idx in range(num_volunteers):
        v_id = f"VOL_{idx+1:04d}"
        roll = rng.random()

        if roll < 0.18:
            cat = "MEDICAL"
            certified = True
            skills = ["First Aid", "Triage", "Emergency Trauma Care"]
        elif roll < 0.30:
            cat = "RESCUE"
            certified = False
            skills = ["Swift Water Rescue", "Search and Rescue"]
        elif roll < 0.50:
            cat = "LOGISTICS"
            certified = False
            skills = ["Supply Distribution", "Vehicle Driver", "Inventory"]
        else:
            cat = "GENERAL"
            certified = False
            skills = ["Community Assistance", "Food Distribution"]

        # Geographical distribution across Chennai corridor
        v_lat = rng.uniform(12.70, 13.18)
        v_lng = rng.uniform(79.98, 80.29)

        # Shift availability: 80% available for all shifts, 20% restricted to specific shifts
        if rng.random() < 0.8:
            v_shifts = list(shifts)
        else:
            v_shifts = [rng.choice(shifts)]

        max_hours = rng.choice([6.0, 8.0, 10.0])
        max_transit = rng.choice([35.0, 45.0, 60.0])

        volunteers.append(VolunteerInput(
            volunteer_id=v_id,
            name=f"Responder {idx+1}",
            latitude=v_lat,
            longitude=v_lng,
            skill_category=cat,
            skills=skills,
            medical_certified=certified,
            verification_status="VERIFIED",
            is_available=True,
            assignment_status="UNASSIGNED",
            max_shift_hours=max_hours,
            max_travel_time_mins=max_transit,
            shift_availability=v_shifts
        ))

    return incidents, volunteers
