from typing import Dict, Any

def normalize_priority_inputs(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Normalizes raw incident parameters into 0.0-1.0 feature ratios for priority scoring.
    """
    people_aff = float(data.get("people_affected", 1))
    injuries = float(data.get("injuries", 0))
    vulnerable = float(data.get("vulnerable_count", 0))
    infra = data.get("infrastructure_damage")
    has_infra = 1.0 if infra and str(infra).strip() and str(infra).lower() != "none" else 0.0
    corroboration = float(data.get("corroboration_count", 1))
    
    return {
        "affected_ratio": min(1.0, people_aff / 50.0),
        "life_safety_ratio": min(1.0, (injuries * 0.15) + (vulnerable * 0.1)),
        "has_infra": has_infra,
        "corroboration_ratio": min(1.0, corroboration / 5.0)
    }
