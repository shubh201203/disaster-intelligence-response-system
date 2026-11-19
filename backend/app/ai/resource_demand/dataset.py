import numpy as np
import pandas as pd
from typing import Tuple, Dict
from app.ai.resource_demand.features import FEATURE_NAMES, RESOURCE_TYPES

def generate_synthetic_resource_demand_dataset(
    n_samples: int = 2000,
    random_seed: int = 42
) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """
    Generates a deterministic synthetic dataset of 2,000 incident samples mapping incident parameters
    to 5 required resource demand targets (water_packs, food_packets, medical_kits, shelter_beds, rescue_personnel).
    """
    np.random.seed(random_seed)

    X_list = []
    Y_list = []

    for _ in range(n_samples):
        p_aff = int(np.random.exponential(scale=35.0)) + 1
        inj = int(np.random.binomial(n=p_aff, p=0.20))
        vul = int(np.random.binomial(n=p_aff, p=0.25))
        has_infra = np.random.choice([0.0, 1.0], p=[0.60, 0.40])
        sev_code = np.random.choice([1.0, 2.0, 3.0, 4.0], p=[0.30, 0.35, 0.25, 0.10])
        dis_code = np.random.choice([1.0, 2.0, 3.0, 4.0, 5.0])

        # Realistic domain formula relationships with noise
        water = (p_aff * 15.0) + (vul * 5.0) + np.random.normal(0, 10)
        food = (p_aff * 12.0) + (vul * 4.0) + np.random.normal(0, 8)
        med_kits = (inj * 1.5) + (vul * 0.8) + (sev_code * 2.0) + np.random.normal(0, 2)
        shelter_beds = (p_aff * 0.70) + (has_infra * 15.0) + np.random.normal(0, 5)
        personnel = (p_aff * 0.15) + (inj * 0.4) + (has_infra * 4.0) + (sev_code * 2.0) + np.random.normal(0, 1)

        x_feat = [p_aff, inj, vul, has_infra, sev_code, dis_code]
        y_targets = [
            max(5.0, round(water, 1)),
            max(4.0, round(food, 1)),
            max(1.0, round(med_kits, 1)),
            max(0.0, round(shelter_beds, 1)),
            max(1.0, round(personnel, 1))
        ]

        X_list.append(x_feat)
        Y_list.append(y_targets)

    X = np.array(X_list, dtype=float)
    Y = np.array(Y_list, dtype=float)

    df_x = pd.DataFrame(X, columns=FEATURE_NAMES)
    df_y = pd.DataFrame(Y, columns=RESOURCE_TYPES)
    df = pd.concat([df_x, df_y], axis=1)

    return X, Y, df
