"""
DIRS Phase 5F-C — Shelter Evacuation Benchmark Dataset Generator
Classification: SYNTHETIC CALIBRATED BENCHMARK DATASET
Geographic bounding box: Coastal Chennai / Tamil Nadu Disaster Corridor (Lat: 12.65 - 13.15, Lng: 79.95 - 80.30)
"""
import random
from typing import List, Tuple
from app.ai.optimization.shelter import IncidentEvacuationInput, ShelterInput

DISASTER_TYPES = ["FLOOD", "CYCLONE", "FIRE", "LANDSLIDE"]
SEVERITY_LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def generate_shelter_benchmark_dataset(
    num_incidents: int = 25,
    num_shelters: int = 10,
    seed: int = 42,
    capacity_multiplier: float = 1.0
) -> Tuple[List[IncidentEvacuationInput], List[ShelterInput]]:
    """
    Generates a deterministic reproducible benchmark dataset for Phase 5F-C shelter evacuation optimization.
    """
    rng = random.Random(seed)

    # 1. Anchor Locations for Chennai Shelters
    shelter_anchors = [
        ("Anna University Indoor Stadium", 13.0110, 80.2350, 500, True, True),
        ("Jawaharlal Nehru Indoor Stadium", 13.0836, 80.2770, 800, True, True),
        ("Koyambedu Community Center", 13.0690, 80.1940, 400, True, False),
        ("Tambaram Railway Community Hall", 12.9250, 80.1180, 350, False, True),
        ("Adyar Youth Hostel Relief Center", 13.0030, 80.2550, 250, True, False),
        ("Velachery Higher Secondary School", 12.9780, 80.2180, 300, False, False),
        ("Guindy Industrial Welfare Center", 13.0070, 80.2020, 450, True, True),
        ("Mylapore Cultural Auditorium", 13.0330, 80.2680, 200, False, False),
        ("Marina Beach Evacuation Pavilion", 13.0500, 80.2820, 600, True, True),
        ("Chengalpattu District Relief Camp", 12.6850, 79.9830, 500, True, True),
    ]

    shelters: List[ShelterInput] = []
    for idx in range(num_shelters):
        s_id = f"SHELTER_{idx+1:03d}"
        if idx < len(shelter_anchors):
            name, lat, lng, base_cap, acc, med = shelter_anchors[idx]
        else:
            name = f"Regional Relief Shelter {idx+1}"
            lat = rng.uniform(12.70, 13.12)
            lng = rng.uniform(80.00, 80.27)
            base_cap = rng.choice([200, 300, 450, 600])
            acc = rng.random() > 0.4  # 60% accessible
            med = rng.random() > 0.4  # 60% medical capable

        total_cap = int(round(base_cap * capacity_multiplier))
        # 10% chance of pre-occupancy
        pre_occ = int(round(rng.uniform(0, total_cap * 0.3))) if rng.random() > 0.5 else 0

        shelters.append(ShelterInput(
            shelter_id=s_id,
            name=name,
            latitude=lat,
            longitude=lng,
            total_capacity=total_cap,
            current_occupancy=pre_occ,
            status="OPEN",
            accessibility_features=acc,
            has_medical=med,
            has_food=True,
            has_water=True,
            power_available=True,
            sanitation_available=True,
            disaster_compatibility=["FLOOD", "CYCLONE"]  # Compatible with major regional hazards
        ))

    # 2. Anchor Locations for Chennai Incidents
    incident_anchors = [
        ("Saidapet Riverbank Flooding", 13.0180, 80.2220, "CRITICAL", 92.0, "FLOOD", 150),
        ("Velachery Lake Overflow", 12.9750, 80.2200, "CRITICAL", 88.0, "FLOOD", 220),
        ("Adyar Basin Inundation", 13.0050, 80.2450, "HIGH", 82.0, "FLOOD", 180),
        ("Madipakkam Lowland Breach", 12.9620, 80.1980, "HIGH", 76.0, "FLOOD", 120),
        ("Pallikaranai Wetland Submergence", 12.9350, 80.2150, "MEDIUM", 65.0, "FLOOD", 90),
        ("Tambaram Mudichur Flood Zone", 12.9150, 80.0850, "HIGH", 79.0, "FLOOD", 140),
        ("Kotturpuram Slum Inundation", 13.0230, 80.2400, "CRITICAL", 94.0, "FLOOD", 200),
        ("Taramani IT Park Waterlogging", 12.9850, 80.2420, "LOW", 45.0, "FLOOD", 60),
        ("Sholinganallur Junction Flooding", 12.9010, 80.2280, "MEDIUM", 68.0, "FLOOD", 110),
        ("Perungudi Canal Overflow", 12.9640, 80.2480, "MEDIUM", 60.0, "FLOOD", 85)
    ]

    incidents: List[IncidentEvacuationInput] = []
    for idx in range(num_incidents):
        inc_id = f"INC_{idx+1:03d}"
        if idx < len(incident_anchors):
            title, lat, lng, sev, pri, d_type, pop = incident_anchors[idx]
        else:
            title = f"Disaster Evacuation Sector {idx+1}"
            lat = rng.uniform(12.72, 13.10)
            lng = rng.uniform(80.02, 80.26)
            sev = rng.choice(SEVERITY_LEVELS)
            pri = round(rng.uniform(40.0, 95.0), 1)
            d_type = rng.choice(["FLOOD", "CYCLONE"])
            pop = rng.randint(40, 250)

        # Generate demographic partition:
        # ~70% GEN, ~15% ACC, ~10% MED, ~5% MED_ACC
        med_acc = int(round(pop * rng.uniform(0.02, 0.08)))
        acc = int(round(pop * rng.uniform(0.10, 0.20)))
        med = int(round(pop * rng.uniform(0.08, 0.15)))
        gen = max(0, pop - (med_acc + acc + med))
        # Ensure exact conservation
        total_p = gen + acc + med + med_acc

        incidents.append(IncidentEvacuationInput(
            incident_id=inc_id,
            title=title,
            latitude=lat,
            longitude=lng,
            priority_score=pri,
            severity_level=sev,
            disaster_type=d_type,
            people_affected=total_p,
            evacuation_demographics={
                "GEN": gen,
                "ACC": acc,
                "MED": med,
                "MED_ACC": med_acc
            }
        ))

    return incidents, shelters
