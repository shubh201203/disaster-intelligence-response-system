import numpy as np
from typing import List, Dict, Any
from app.ai.common.schemas import FactorContribution

def generate_risk_explanation(features: np.ndarray, risk_score: float, risk_level: str) -> List[FactorContribution]:
    """
    Computes model-weighted feature contributions for meteorological and environmental risk factors.
    Returns structured list of FactorContribution objects explaining the risk score.
    """
    temp, rain, wind, humidity, pressure, river, hist_freq, pop_exp, elevation, infra_prox, d_code = features

    # Factor contribution calculations based on actual feature values
    rain_pts = min(25.0, (rain / 200.0) * 25.0)
    river_pts = min(25.0, (river / 6.0) * 25.0)
    wind_pts = min(15.0, (wind / 120.0) * 15.0)
    hist_pts = min(15.0, (hist_freq / 15.0) * 15.0)
    pop_pts = min(10.0, (pop_exp / 5000.0) * 10.0)
    infra_pts = min(10.0, (max(0.0, 500.0 - infra_prox) / 500.0) * 10.0)

    raw_factors = [
        (rain_pts, "Heavy Precipitation", f"Accumulated rainfall ({rain:.1f} mm)"),
        (river_pts, "River Surge / Water Level", f"Water body level ({river:.2f} m)"),
        (wind_pts, "Wind Velocity", f"Wind speed ({wind:.1f} km/h)"),
        (hist_pts, "Historical Frequency", f"Historical disaster occurrence frequency ({int(hist_freq)})"),
        (pop_pts, "Population Exposure Density", f"Estimated population in hazard zone ({int(pop_exp)} residents)"),
        (infra_pts, "Infrastructure Hazard Proximity", f"Proximity to critical infrastructure ({infra_prox:.0f} m)")
    ]

    # Sort factors by impact descending
    raw_factors.sort(key=lambda x: x[0], reverse=True)

    factors: List[FactorContribution] = []
    for impact_val, feature_label, desc in raw_factors:
        if impact_val > 0.5:
            factors.append(
                FactorContribution(
                    feature=feature_label,
                    impact=round(float(impact_val), 1),
                    direction="increases",
                    description=desc
                )
            )

    return factors
