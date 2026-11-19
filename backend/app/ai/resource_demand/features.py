import numpy as np
from typing import Dict, Any, List

RESOURCE_TYPES = [
    "water_packs",
    "food_packets",
    "medical_kits",
    "shelter_beds",
    "rescue_personnel"
]

FEATURE_NAMES = [
    "people_affected",
    "injuries",
    "vulnerable_count",
    "has_infra_damage",
    "severity_code",
    "disaster_type_code"
]

SEVERITY_CODE_MAP = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
DISASTER_CODE_MAP = {"FLOOD": 1, "CYCLONE": 2, "FIRE": 3, "LANDSLIDE": 4, "EARTHQUAKE": 5}

def extract_resource_demand_features(data: Dict[str, Any]) -> np.ndarray:
    """
    Extracts numerical features from incident data for multi-target resource demand regression.
    Features: people_affected, injuries, vulnerable_count, has_infra_damage, severity_code, disaster_type_code.
    """
    p_aff = float(data.get("people_affected", 10))
    inj = float(data.get("injuries", 0))
    vul = float(data.get("vulnerable_count", 0))

    infra = data.get("infrastructure_damage")
    has_infra = 1.0 if (infra and str(infra).strip().lower() not in ["none", ""]) else 0.0

    sev_code = float(SEVERITY_CODE_MAP.get(str(data.get("severity_level", "MEDIUM")).upper(), 2))
    dis_code = float(DISASTER_CODE_MAP.get(str(data.get("disaster_type", "FLOOD")).upper(), 1))

    return np.array([p_aff, inj, vul, has_infra, sev_code, dis_code], dtype=float)
