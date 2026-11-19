import numpy as np
import pandas as pd
from typing import Tuple
from app.ai.severity.features import FEATURE_NAMES, DISASTER_TYPE_MAP

def generate_synthetic_severity_dataset(n_samples_per_class: int = 500, random_seed: int = 42) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """
    Generates a balanced, realistic synthetic dataset for 4 severity classes (LOW, MEDIUM, HIGH, CRITICAL).
    Ensures equal class support (500 samples per class = 2,000 total) with deterministic random seed.
    """
    np.random.seed(random_seed)
    
    classes_data = []
    
    # 1. LOW Class (500 samples)
    for _ in range(n_samples_per_class):
        p_aff = np.random.randint(1, 6)
        inj = 0
        vul = np.random.choice([0, 1], p=[0.8, 0.2])
        inf = np.random.choice([0, 1], p=[0.95, 0.05])
        d_code = np.random.choice([1, 2, 4]) # FLOOD, CYCLONE, LANDSLIDE
        urg = round(np.random.uniform(0.0, 0.25), 2)
        classes_data.append(([p_aff, inj, vul, inf, d_code, urg], "LOW"))
        
    # 2. MEDIUM Class (500 samples)
    for _ in range(n_samples_per_class):
        p_aff = np.random.randint(6, 26)
        inj = np.random.randint(0, 3)
        vul = np.random.randint(1, 4)
        inf = np.random.choice([0, 1], p=[0.75, 0.25])
        d_code = np.random.choice([1, 2, 3, 4])
        urg = round(np.random.uniform(0.25, 0.50), 2)
        classes_data.append(([p_aff, inj, vul, inf, d_code, urg], "MEDIUM"))
        
    # 3. HIGH Class (500 samples)
    for _ in range(n_samples_per_class):
        p_aff = np.random.randint(26, 76)
        inj = np.random.randint(3, 9)
        vul = np.random.randint(3, 9)
        inf = np.random.choice([0, 1], p=[0.30, 0.70])
        d_code = np.random.choice([1, 2, 3, 4, 5])
        urg = round(np.random.uniform(0.50, 0.80), 2)
        classes_data.append(([p_aff, inj, vul, inf, d_code, urg], "HIGH"))
        
    # 4. CRITICAL Class (500 samples)
    for _ in range(n_samples_per_class):
        p_aff = np.random.randint(76, 250)
        inj = np.random.randint(9, 35)
        vul = np.random.randint(9, 25)
        inf = np.random.choice([0, 1], p=[0.05, 0.95])
        d_code = np.random.choice([2, 3, 5]) # CYCLONE, FIRE, EARTHQUAKE
        urg = round(np.random.uniform(0.80, 1.00), 2)
        classes_data.append(([p_aff, inj, vul, inf, d_code, urg], "CRITICAL"))

    # Shuffle deterministically
    indices = np.arange(len(classes_data))
    np.random.shuffle(indices)
    
    X = np.array([classes_data[i][0] for i in indices], dtype=float)
    y = np.array([classes_data[i][1] for i in indices])
    
    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    df["severity_class"] = y
    
    return X, y, df
