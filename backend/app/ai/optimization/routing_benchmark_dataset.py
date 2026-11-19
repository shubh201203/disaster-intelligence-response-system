"""
DIRS Phase 5E - Calibrated Vehicle Routing Benchmark Dataset Generator
Benchmark: DIRS-ROUTE-25 (25 incidents, 10 vehicles, multiple depots, commodities, time windows)
Classification: SYNTHETIC CALIBRATED ROUTING BENCHMARK
"""
import random
from typing import List, Tuple, Dict
from app.ai.optimization.routing import (
    VehicleInput,
    ShipmentInput,
    COMMODITY_WEIGHT_KG_PER_UNIT,
    COMMODITY_VOLUME_M3_PER_UNIT,
    DEFAULT_SERVICE_TIME_MIN,
)

def generate_dirs_route_benchmark(
    num_incidents: int = 25,
    num_vehicles: int = 10,
    num_depots: int = 4,
    seed: int = 42
) -> Tuple[List[ShipmentInput], List[VehicleInput]]:
    """
    Generates deterministic, reproducible benchmark data for Phase 5E routing optimization.
    Coverage: Coastal Chennai corridor (Lat: 12.70 - 13.10, Lng: 80.00 - 80.28).
    Classification: SYNTHETIC CALIBRATED ROUTING BENCHMARK.
    """
    rng = random.Random(seed)

    depot_configs = [
        ("DEPOT_001", "MGR Central Storage Depot", 13.0827, 80.2707),
        ("DEPOT_002", "Guindy Emergency Logistics Center", 13.0067, 80.2020),
        ("DEPOT_003", "Tambaram Relief Stockpile", 12.9249, 80.1000),
        ("DEPOT_004", "Marina Beach Relief Station", 13.0500, 80.2800),
        ("DEPOT_005", "Velachery Supply Hub", 12.9780, 80.2180),
    ]

    depots = depot_configs[:min(num_depots, len(depot_configs))]
    while len(depots) < num_depots:
        idx = len(depots) + 1
        depots.append((f"DEPOT_{idx:03d}", f"Regional Depot {idx}", rng.uniform(12.75, 13.10), rng.uniform(80.05, 80.25)))

    # 1. Generate Vehicles
    vehicles: List[VehicleInput] = []
    veh_types = [
        ("TRUCK", 3000.0, 15.0),
        ("VAN", 1200.0, 6.0),
        ("AMBULANCE", 500.0, 2.5),
        ("TRUCK", 4000.0, 20.0),
    ]

    for v_i in range(num_vehicles):
        v_code = f"VEH_{v_i+1:03d}"
        depot_id, depot_name, dep_lat, dep_lng = depots[v_i % len(depots)]
        v_type, cap_w, cap_v = veh_types[v_i % len(veh_types)]

        vehicles.append(VehicleInput(
            vehicle_id=f"veh_id_{v_i+1:03d}",
            vehicle_code=v_code,
            vehicle_type=v_type,
            capacity_weight_kg=cap_w,
            capacity_volume_m3=cap_v,
            depot_id=depot_id,
            depot_lat=dep_lat,
            depot_lng=dep_lng,
            status="AVAILABLE"
        ))

    # 2. Generate Shipments (representing approved Phase 5D allocations)
    shipments: List[ShipmentInput] = []
    severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    for i_i in range(num_incidents):
        inc_id = f"INC_{i_i+1:03d}"
        inc_title = f"Disaster Site {i_i+1}"
        lat = rng.uniform(12.75, 13.10)
        lng = rng.uniform(80.05, 80.28)

        # Priority & Severity
        p_score = round(rng.uniform(20.0, 95.0), 1)
        if p_score >= 80.0:
            sev = "CRITICAL"
        elif p_score >= 60.0:
            sev = "HIGH"
        elif p_score >= 40.0:
            sev = "MEDIUM"
        else:
            sev = "LOW"

        # Assign origin depot
        origin_depot = depots[i_i % len(depots)]
        depot_id, _, dep_lat, dep_lng = origin_depot

        # Commodities (calibrated humanitarian quantities)
        commodities = {
            "WATER": round(rng.uniform(100, 500), 0),
            "FOOD": round(rng.uniform(50, 200), 0),
            "MEDICAL_KITS": round(rng.uniform(5, 25), 0),
        }

        total_w = sum(COMMODITY_WEIGHT_KG_PER_UNIT.get(c, 1.0) * q for c, q in commodities.items())
        total_v = sum(COMMODITY_VOLUME_M3_PER_UNIT.get(c, 0.001) * q for c, q in commodities.items())

        # Time windows (minutes from dispatch start)
        # CRITICAL incidents get tighter latest arrival targets
        if sev == "CRITICAL":
            earliest = 0.0
            latest = round(rng.uniform(60.0, 180.0), 1)
        elif sev == "HIGH":
            earliest = 0.0
            latest = round(rng.uniform(120.0, 240.0), 1)
        else:
            earliest = 0.0
            latest = round(rng.uniform(180.0, 480.0), 1)

        shipments.append(ShipmentInput(
            shipment_id=f"SHP_{depot_id}_{inc_id}",
            origin_depot_id=depot_id,
            origin_depot_lat=dep_lat,
            origin_depot_lng=dep_lng,
            incident_id=inc_id,
            incident_lat=lat,
            incident_lng=lng,
            incident_title=inc_title,
            priority_score=p_score,
            severity_level=sev,
            commodities=commodities,
            total_weight_kg=total_w,
            total_volume_m3=total_v,
            earliest_arrival_min=earliest,
            latest_arrival_min=latest,
            service_time_min=DEFAULT_SERVICE_TIME_MIN,
        ))

    return shipments, vehicles
