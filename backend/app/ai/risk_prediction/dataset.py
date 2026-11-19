import numpy as np
import pandas as pd
from typing import Tuple
from app.ai.risk_prediction.features import FEATURE_NAMES, RISK_LEVELS

def generate_synthetic_risk_dataset(
    n_samples_per_class: int = 500,
    random_seed: int = 42
) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """
    Generates a deterministic synthetic dataset of 2,000 meteorological and environmental samples
    equally distributed across 4 risk levels (LOW, MODERATE, HIGH, EXTREME).
    """
    np.random.seed(random_seed)
    data = []

    # 1. LOW Risk (500 samples)
    for _ in range(n_samples_per_class):
        temp = np.random.uniform(22.0, 30.0)
        rain = np.random.uniform(0.0, 20.0)
        wind = np.random.uniform(5.0, 20.0)
        humidity = np.random.uniform(40.0, 65.0)
        pressure = np.random.uniform(1012.0, 1020.0)
        river = np.random.uniform(0.2, 1.0)
        hist_freq = np.random.randint(0, 2)
        pop_exp = np.random.uniform(100.0, 500.0)
        elevation = np.random.uniform(50.0, 200.0)
        infra_prox = np.random.uniform(500.0, 2000.0)
        d_code = np.random.choice([1, 3, 4])
        data.append(([temp, rain, wind, humidity, pressure, river, hist_freq, pop_exp, elevation, infra_prox, d_code], "LOW"))

    # 2. MODERATE Risk (500 samples)
    for _ in range(n_samples_per_class):
        temp = np.random.uniform(28.0, 34.0)
        rain = np.random.uniform(20.0, 60.0)
        wind = np.random.uniform(20.0, 45.0)
        humidity = np.random.uniform(65.0, 80.0)
        pressure = np.random.uniform(1005.0, 1012.0)
        river = np.random.uniform(1.0, 2.2)
        hist_freq = np.random.randint(2, 5)
        pop_exp = np.random.uniform(500.0, 1500.0)
        elevation = np.random.uniform(20.0, 80.0)
        infra_prox = np.random.uniform(200.0, 800.0)
        d_code = np.random.choice([1, 2, 3, 4])
        data.append(([temp, rain, wind, humidity, pressure, river, hist_freq, pop_exp, elevation, infra_prox, d_code], "MODERATE"))

    # 3. HIGH Risk (500 samples)
    for _ in range(n_samples_per_class):
        temp = np.random.uniform(32.0, 38.0)
        rain = np.random.uniform(60.0, 150.0)
        wind = np.random.uniform(45.0, 85.0)
        humidity = np.random.uniform(80.0, 92.0)
        pressure = np.random.uniform(995.0, 1005.0)
        river = np.random.uniform(2.2, 4.0)
        hist_freq = np.random.randint(5, 10)
        pop_exp = np.random.uniform(1500.0, 4000.0)
        elevation = np.random.uniform(5.0, 30.0)
        infra_prox = np.random.uniform(50.0, 300.0)
        d_code = np.random.choice([1, 2, 4, 5])
        data.append(([temp, rain, wind, humidity, pressure, river, hist_freq, pop_exp, elevation, infra_prox, d_code], "HIGH"))

    # 4. EXTREME Risk (500 samples)
    for _ in range(n_samples_per_class):
        temp = np.random.uniform(35.0, 42.0)
        rain = np.random.uniform(150.0, 350.0)
        wind = np.random.uniform(85.0, 160.0)
        humidity = np.random.uniform(90.0, 99.0)
        pressure = np.random.uniform(970.0, 995.0)
        river = np.random.uniform(4.0, 8.5)
        hist_freq = np.random.randint(10, 25)
        pop_exp = np.random.uniform(4000.0, 10000.0)
        elevation = np.random.uniform(1.0, 15.0)
        infra_prox = np.random.uniform(10.0, 100.0)
        d_code = np.random.choice([1, 2, 5])
        data.append(([temp, rain, wind, humidity, pressure, river, hist_freq, pop_exp, elevation, infra_prox, d_code], "EXTREME"))

    # Shuffle deterministically
    indices = np.arange(len(data))
    np.random.shuffle(indices)

    X = np.array([data[i][0] for i in indices], dtype=float)
    y = np.array([data[i][1] for i in indices])

    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    df["risk_level"] = y

    return X, y, df
