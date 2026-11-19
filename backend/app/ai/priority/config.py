from typing import Dict, Any

# Centralized Priority Weight Configuration (Sum of weights = 100.0)
PRIORITY_WEIGHTS: Dict[str, float] = {
    "severity": 30.0,            # Severity classification (CRITICAL=30, HIGH=20, MEDIUM=10, LOW=5)
    "life_safety": 25.0,         # Injuries & vulnerable population count
    "affected_population": 15.0,  # Total population affected scale
    "infrastructure": 15.0,       # Infrastructure damage
    "disaster_type": 10.0,        # Hazard type risk modifier
    "corroboration": 5.0          # Report corroboration & duplicate report count
}

SEVERITY_WEIGHT_MAP: Dict[str, float] = {
    "CRITICAL": 30.0,
    "HIGH": 20.0,
    "MEDIUM": 10.0,
    "LOW": 5.0
}

DISASTER_TYPE_WEIGHT_MAP: Dict[str, float] = {
    "EARTHQUAKE": 10.0,
    "CYCLONE": 8.0,
    "FIRE": 8.0,
    "FLOOD": 6.0,
    "LANDSLIDE": 6.0
}

def validate_weights() -> bool:
    total = sum(PRIORITY_WEIGHTS.values())
    return abs(total - 100.0) < 1e-5
