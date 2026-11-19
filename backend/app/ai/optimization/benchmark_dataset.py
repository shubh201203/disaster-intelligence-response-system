"""
DIRS Phase 5D — Standard DIRS-50 Optimization Benchmark Dataset Generator
Classification: SYNTHETIC CALIBRATED OPTIMIZATION BENCHMARK
"""
import random
from typing import List, Tuple
from app.ai.optimization.allocation import IncidentDemandInput, DepotSupplyInput

COMMODITY_CATEGORIES = [
    "WATER",
    "FOOD",
    "MEDICAL_KITS",
    "RESCUE_EQUIPMENT",
    "SANITATION_KITS",
    "TEMPORARY_SHELTER_SUPPLIES"
]

def generate_dirs50_benchmark_dataset(
    num_incidents: int = 50,
    num_depots: int = 25,
    seed: int = 42,
    supply_multiplier: float = 1.0
) -> Tuple[List[IncidentDemandInput], List[DepotSupplyInput]]:
    """
    Generates a deterministic reproducible benchmark dataset for Phase 5D resource allocation testing.
    Geographic bounding box: Coastal Chennai / Tamil Nadu (Lat: 12.65 - 13.15, Lng: 79.95 - 80.30).
    """
    rng = random.Random(seed)

    # 1. Generate Depots
    depots: List[DepotSupplyInput] = []
    depot_locations = [
        ("MGR Central Storage Depot", 13.0827, 80.2707),
        ("Guindy Emergency Logistics Center", 13.0067, 80.2020),
        ("Tambaram Relief Stockpile", 12.9249, 80.1000),
        ("Kovalam Coastal Reserve Depot", 12.7900, 80.2500),
        ("Kelambakkam Supply Hub", 12.7800, 80.2200),
        ("Chengalpattu Distribution Depot", 12.6800, 79.9800),
        ("Velachery Secondary Stockpile", 12.9780, 80.2180),
        ("Marina Beach Emergency Center", 13.0500, 80.2800)
    ]

    for idx in range(num_depots):
        depot_id = f"DEPOT_{idx+1:03d}"
        if idx < len(depot_locations):
            name, lat, lng = depot_locations[idx]
        else:
            name = f"Regional Storage Depot {idx+1}"
            lat = rng.uniform(12.70, 13.10)
            lng = rng.uniform(80.00, 80.28)

        # Base supplies per commodity
        supplies = {
            "WATER": round(rng.uniform(2000, 8000) * supply_multiplier, 0),
            "FOOD": round(rng.uniform(1000, 4000) * supply_multiplier, 0),
            "MEDICAL_KITS": round(rng.uniform(50, 200) * supply_multiplier, 0),
            "RESCUE_EQUIPMENT": round(rng.uniform(20, 80) * supply_multiplier, 0),
            "SANITATION_KITS": round(rng.uniform(100, 500) * supply_multiplier, 0),
            "TEMPORARY_SHELTER_SUPPLIES": round(rng.uniform(40, 150) * supply_multiplier, 0)
        }

        depots.append(DepotSupplyInput(
            depot_id=depot_id,
            name=name,
            latitude=lat,
            longitude=lng,
            supplies=supplies
        ))

    # 2. Generate Incidents
    incidents: List[IncidentDemandInput] = []
    severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    disasters = ["FLOOD", "CYCLONE", "LANDSLIDE", "FIRE"]

    for idx in range(num_incidents):
        inc_id = f"INC_{idx+1:03d}"
        title = f"Disaster Site {idx+1} ({rng.choice(disasters)})"
        lat = rng.uniform(12.70, 13.10)
        lng = rng.uniform(80.00, 80.28)

        p_score = round(rng.uniform(15.0, 98.0), 1)
        if p_score >= 85.0:
            sev = "CRITICAL"
        elif p_score >= 65.0:
            sev = "HIGH"
        elif p_score >= 40.0:
            sev = "MEDIUM"
        else:
            sev = "LOW"

        # Demands calibrated against Sphere standards
        demands = {
            "WATER": round(rng.uniform(500, 3000), 0),
            "FOOD": round(rng.uniform(200, 1500), 0),
            "MEDICAL_KITS": round(rng.uniform(10, 60), 0),
            "RESCUE_EQUIPMENT": round(rng.uniform(5, 25), 0),
            "SANITATION_KITS": round(rng.uniform(30, 150), 0),
            "TEMPORARY_SHELTER_SUPPLIES": round(rng.uniform(10, 50), 0)
        }

        incidents.append(IncidentDemandInput(
            incident_id=inc_id,
            title=title,
            latitude=lat,
            longitude=lng,
            priority_score=p_score,
            severity_level=sev,
            demands=demands,
            created_at_str=f"2026-09-15T12:{idx%60:02d}:00Z"
        ))

    return incidents, depots
