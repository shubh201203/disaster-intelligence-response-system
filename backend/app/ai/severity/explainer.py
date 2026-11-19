from typing import List, Dict, Any
import numpy as np
from app.ai.severity.features import FEATURE_NAMES
from app.ai.common.schemas import FactorContribution

FEATURE_LABELS = {
    "people_affected": "Affected Population",
    "injuries": "Injured Victims",
    "vulnerable_count": "Vulnerable Demographics (Children / Elderly)",
    "has_infrastructure_damage": "Infrastructure Damage",
    "disaster_type_code": "Disaster Hazard Type",
    "text_urgency_score": "Text Distress Urgency Keywords"
}

def generate_severity_explanation(features: np.ndarray, prediction: str, confidence: float) -> List[FactorContribution]:
    """
    Computes feature contribution weights based on actual input values and baseline feature importances.
    Provides human-readable explainable AI factors for government dashboard inspection.
    """
    p_aff, inj, vul, inf, d_code, urg = features
    
    # Baseline impact multipliers derived from model weights
    impacts = [
        (p_aff * 0.4, "people_affected", f"+{int(p_aff)} people affected"),
        (inj * 4.0, "injuries", f"+{int(inj)} injured victims requiring emergency care"),
        (vul * 3.0, "vulnerable_count", f"+{int(vul)} vulnerable children/elderly count"),
        (inf * 15.0, "has_infrastructure_damage", "Critical infrastructure/power/bridge damage present" if inf > 0 else "No structural damage reported"),
        (d_code * 2.5, "disaster_type_code", f"Disaster classification severity factor ({d_code})"),
        (urg * 25.0, "text_urgency_score", f"High urgency distress keywords detected (Score: {urg:.2f})")
    ]
    
    # Sort by absolute impact descending
    impacts.sort(key=lambda x: abs(x[0]), reverse=True)
    
    factors: List[FactorContribution] = []
    for impact_val, feature_key, desc in impacts:
        if impact_val > 0.1:
            factors.append(
                FactorContribution(
                    feature=FEATURE_LABELS.get(feature_key, feature_key),
                    impact=round(float(impact_val), 2),
                    direction="increases",
                    description=desc
                )
            )
            
    return factors
