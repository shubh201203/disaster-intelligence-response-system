from typing import Dict, Any, List
import numpy as np

FEATURE_NAMES = [
    "people_affected",
    "injuries",
    "vulnerable_count",
    "has_infrastructure_damage",
    "disaster_type_code",
    "text_urgency_score"
]

DISASTER_TYPE_MAP = {
    "FLOOD": 1,
    "CYCLONE": 2,
    "FIRE": 3,
    "LANDSLIDE": 4,
    "EARTHQUAKE": 5
}

URGENCY_KEYWORDS = [
    "trapped", "submerged", "collapse", "death", "fatal", "critical",
    "fire", "explosion", "drowning", "urgent", "immediate", "sos",
    "blood", "help", "rescue", "marooned", "rooftop"
]

def compute_text_urgency_score(text: str) -> float:
    if not text:
        return 0.0
    text_lower = text.lower()
    matches = sum(1 for kw in URGENCY_KEYWORDS if kw in text_lower)
    return min(1.0, matches / 3.0)

def extract_features_from_dict(data: Dict[str, Any]) -> np.ndarray:
    """
    Extracts numerical feature vector for severity model.
    """
    people_affected = float(data.get("people_affected", 1))
    injuries = float(data.get("injuries", 0))
    vulnerable_count = float(data.get("vulnerable_count", 0))
    
    infra = data.get("infrastructure_damage")
    has_infra = 1.0 if infra and str(infra).strip() and str(infra).lower() != "none" else 0.0
    
    disaster_type = str(data.get("disaster_type", "FLOOD")).upper()
    disaster_code = float(DISASTER_TYPE_MAP.get(disaster_type, 1))
    
    desc = f"{data.get('title', '')} {data.get('description', '')}"
    urgency_score = compute_text_urgency_score(desc)
    
    return np.array([
        people_affected,
        injuries,
        vulnerable_count,
        has_infra,
        disaster_code,
        urgency_score
    ], dtype=float)
