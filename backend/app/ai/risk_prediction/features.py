import numpy as np
from typing import Dict, Any, List

RISK_LEVELS = ["LOW", "MODERATE", "HIGH", "EXTREME"]

FEATURE_NAMES = [
    "temperature_c",
    "rainfall_mm",
    "wind_speed_kmh",
    "humidity_pct",
    "pressure_hpa",
    "river_level_m",
    "historical_freq",
    "population_exposure",
    "elevation_m",
    "infra_proximity_m",
    "disaster_type_code"
]

DISASTER_TYPE_MAP = {
    "FLOOD": 1,
    "CYCLONE": 2,
    "FIRE": 3,
    "LANDSLIDE": 4,
    "EARTHQUAKE": 5
}

def extract_risk_features(data: Dict[str, Any]) -> np.ndarray:
    """
    Extracts numerical meteorological and environmental features for risk prediction.
    Features: temperature, rainfall, wind speed, humidity, pressure, river level,
    historical frequency, population exposure, elevation, infrastructure proximity, disaster type code.
    """
    temp = float(data.get("temperature_c", 28.0))
    rain = float(data.get("rainfall_mm", 45.0))
    wind = float(data.get("wind_speed_kmh", 25.0))
    humidity = float(data.get("humidity_pct", 75.0))
    pressure = float(data.get("pressure_hpa", 1008.0))
    river = float(data.get("river_level_m", 1.5))
    hist_freq = float(data.get("historical_freq", 3.0))
    pop_exp = float(data.get("population_exposure", 1200.0))
    elevation = float(data.get("elevation_m", 15.0))
    infra_prox = float(data.get("infra_proximity_m", 150.0))
    d_code = float(DISASTER_TYPE_MAP.get(str(data.get("disaster_type", "FLOOD")).upper(), 1))

    return np.array([
        temp, rain, wind, humidity, pressure, river,
        hist_freq, pop_exp, elevation, infra_prox, d_code
    ], dtype=float)
