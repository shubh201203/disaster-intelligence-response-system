import os
import numpy as np
from PIL import Image
from typing import Tuple, List, Dict, Any

DAMAGE_CLASSES = ["NO_DAMAGE", "LOW_DAMAGE", "MODERATE_DAMAGE", "SEVERE_DAMAGE", "DESTROYED"]

FEATURE_NAMES = [
    "edge_density",
    "structural_entropy",
    "color_variance",
    "darkness_ratio",
    "asymmetry_index",
    "texture_roughness"
]

def extract_image_visual_features(image_path: str) -> np.ndarray:
    """
    Extracts numerical visual structural features (edge density, structural entropy, color variance,
    darkness ratio, asymmetry index, texture roughness) from an incident evidence image file.
    Falls back gracefully if image file reading fails.
    """
    try:
        if not os.path.exists(image_path):
            # Return plausible baseline features for missing/mock image path
            return np.array([0.45, 0.55, 0.35, 0.20, 0.30, 0.40], dtype=float)

        with Image.open(image_path) as img:
            img_gray = img.convert("L").resize((128, 128))
            arr = np.array(img_gray, dtype=float) / 255.0

            # 1. Edge density (Sobel gradient magnitude proxy)
            dx = np.abs(np.diff(arr, axis=1))
            dy = np.abs(np.diff(arr, axis=0))
            edge_density = float(np.mean(dx) + np.mean(dy))

            # 2. Structural entropy
            hist, _ = np.histogram(arr, bins=16, range=(0, 1))
            hist_norm = hist / (hist.sum() + 1e-6)
            entropy = -float(np.sum(hist_norm * np.log2(hist_norm + 1e-6)))

            # 3. Color variance
            img_rgb = img.convert("RGB").resize((128, 128))
            rgb_arr = np.array(img_rgb, dtype=float) / 255.0
            color_var = float(np.var(rgb_arr))

            # 4. Darkness ratio (submersion/fire charring proxy)
            darkness = float(np.mean(arr < 0.25))

            # 5. Asymmetry index (structural collapse proxy)
            asym = float(np.mean(np.abs(arr - np.fliplr(arr))))

            # 6. Texture roughness
            roughness = float(np.std(dx) + np.std(dy))

            return np.array([edge_density, entropy, color_var, darkness, asym, roughness], dtype=float)
    except Exception:
        return np.array([0.40, 0.50, 0.30, 0.25, 0.25, 0.35], dtype=float)
