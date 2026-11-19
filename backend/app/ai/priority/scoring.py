from typing import Dict, Any, Tuple, List
from app.ai.priority.config import (
    PRIORITY_WEIGHTS,
    SEVERITY_WEIGHT_MAP,
    DISASTER_TYPE_WEIGHT_MAP
)
from app.ai.priority.features import normalize_priority_inputs
from app.ai.common.schemas import FactorContribution

def compute_priority_score_and_breakdown(data: Dict[str, Any]) -> Tuple[float, str, Dict[str, float], List[FactorContribution]]:
    """
    Computes a transparent, explainable 0-100 priority score based on centralized PRIORITY_WEIGHTS.
    Returns: (score, classification, breakdown_dict, factor_contributions)
    """
    severity = str(data.get("severity_level", "MEDIUM")).upper()
    disaster_type = str(data.get("disaster_type", "FLOOD")).upper()
    
    norm = normalize_priority_inputs(data)
    
    severity_pts = SEVERITY_WEIGHT_MAP.get(severity, 10.0)
    life_safety_pts = norm["life_safety_ratio"] * PRIORITY_WEIGHTS["life_safety"]
    affected_pts = norm["affected_ratio"] * PRIORITY_WEIGHTS["affected_population"]
    infra_pts = norm["has_infra"] * PRIORITY_WEIGHTS["infrastructure"]
    disaster_pts = DISASTER_TYPE_WEIGHT_MAP.get(disaster_type, 5.0)
    corroboration_pts = norm["corroboration_ratio"] * PRIORITY_WEIGHTS["corroboration"]
    
    total_score = min(100.0, max(0.0, (
        severity_pts +
        life_safety_pts +
        affected_pts +
        infra_pts +
        disaster_pts +
        corroboration_pts
    )))
    
    total_score = round(total_score, 1)
    
    if total_score >= 76.0:
        classification = "CRITICAL"
    elif total_score >= 51.0:
        classification = "HIGH"
    elif total_score >= 26.0:
        classification = "MEDIUM"
    else:
        classification = "LOW"
        
    breakdown = {
        "severity_contribution": round(severity_pts, 1),
        "life_safety_contribution": round(life_safety_pts, 1),
        "affected_population_contribution": round(affected_pts, 1),
        "infrastructure_contribution": round(infra_pts, 1),
        "disaster_type_contribution": round(disaster_pts, 1),
        "corroboration_contribution": round(corroboration_pts, 1)
    }
    
    factors = [
        FactorContribution(feature="Severity Level", impact=round(severity_pts, 1), direction="increases", description=f"Predicted severity level: {severity}"),
        FactorContribution(feature="Life Safety Risk", impact=round(life_safety_pts, 1), direction="increases", description=f"Injuries and vulnerable demographics impact"),
        FactorContribution(feature="Affected Population", impact=round(affected_pts, 1), direction="increases", description=f"Total casualties and affected scope"),
        FactorContribution(feature="Infrastructure Hazard", impact=round(infra_pts, 1), direction="increases", description="Bridge/road/powerline damage impact"),
        FactorContribution(feature="Disaster Type Modifier", impact=round(disaster_pts, 1), direction="increases", description=f"Hazard risk classification ({disaster_type})"),
        FactorContribution(feature="Report Corroboration", impact=round(corroboration_pts, 1), direction="increases", description="Citizen report volume verification")
    ]
    
    return total_score, classification, breakdown, factors
