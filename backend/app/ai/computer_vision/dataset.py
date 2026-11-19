import numpy as np
import pandas as pd
from typing import Tuple
from app.ai.computer_vision.features import FEATURE_NAMES, DAMAGE_CLASSES

def generate_synthetic_cv_dataset(
    n_samples_per_class: int = 200,
    random_seed: int = 42
) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """
    Generates a deterministic synthetic dataset of visual image features for 5 damage classes:
    NO_DAMAGE, LOW_DAMAGE, MODERATE_DAMAGE, SEVERE_DAMAGE, DESTROYED.
    200 samples per class = 1,000 total samples.
    """
    np.random.seed(random_seed)
    data = []

    for cls_idx, damage_cls in enumerate(DAMAGE_CLASSES):
        for _ in range(n_samples_per_class):
            # Feature distributions shift systematically with damage severity
            edge_density = np.random.uniform(0.1 + (cls_idx * 0.15), 0.3 + (cls_idx * 0.15))
            entropy = np.random.uniform(0.2 + (cls_idx * 0.12), 0.4 + (cls_idx * 0.12))
            color_var = np.random.uniform(0.05 + (cls_idx * 0.08), 0.15 + (cls_idx * 0.08))
            darkness = np.random.uniform(0.05 + (cls_idx * 0.12), 0.20 + (cls_idx * 0.12))
            asymmetry = np.random.uniform(0.08 + (cls_idx * 0.14), 0.22 + (cls_idx * 0.14))
            roughness = np.random.uniform(0.10 + (cls_idx * 0.13), 0.25 + (cls_idx * 0.13))

            feat = [edge_density, entropy, color_var, darkness, asymmetry, roughness]
            data.append((feat, damage_cls))

    # Shuffle deterministically
    indices = np.arange(len(data))
    np.random.shuffle(indices)

    X = np.array([data[i][0] for i in indices], dtype=float)
    y = np.array([data[i][1] for i in indices])

    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    df["damage_class"] = y

    return X, y, df
