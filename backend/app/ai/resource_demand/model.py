import os
import joblib
import numpy as np
from typing import Dict, Any
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from app.ai.resource_demand.dataset import generate_synthetic_resource_demand_dataset
from app.ai.resource_demand.features import RESOURCE_TYPES

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
RESOURCE_MODEL_PATH = os.path.join(MODEL_DIR, "resource_demand_models.pkl")

def train_and_evaluate_resource_models() -> Dict[str, Any]:
    """
    Trains Ridge and RandomForestRegressor multi-output regression models for resource demand.
    Evaluates MAE, RMSE, and R2 metrics for each target resource type and persists best models.
    """
    X, Y, _ = generate_synthetic_resource_demand_dataset(n_samples=2000, random_seed=42)
    X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.25, random_state=42)

    # 1. Ridge Regression Baseline
    ridge = Ridge(alpha=1.0, random_state=42)
    ridge.fit(X_train, Y_train)
    Y_pred_ridge = ridge.predict(X_test)
    mae_ridge = mean_absolute_error(Y_test, Y_pred_ridge)
    r2_ridge = r2_score(Y_test, Y_pred_ridge)

    # 2. Random Forest Regressor Candidate Model
    rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    rf.fit(X_train, Y_train)
    Y_pred_rf = rf.predict(X_test)
    mae_rf = mean_absolute_error(Y_test, Y_pred_rf)
    r2_rf = r2_score(Y_test, Y_pred_rf)

    os.makedirs(MODEL_DIR, exist_ok=True)
    best_model = rf if r2_rf >= r2_ridge else ridge
    joblib.dump(best_model, RESOURCE_MODEL_PATH)

    per_resource_metrics = {}
    for idx, res_name in enumerate(RESOURCE_TYPES):
        y_true = Y_test[:, idx]
        y_pred = Y_pred_rf[:, idx]
        per_resource_metrics[res_name] = {
            "mae": round(float(mean_absolute_error(y_true, y_pred)), 2),
            "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2),
            "r2": round(float(r2_score(y_true, y_pred)), 4)
        }

    results = {
        "selected_model": "RandomForestRegressor" if best_model == rf else "Ridge",
        "ridge_baseline": {
            "mae_overall": round(float(mae_ridge), 2),
            "r2_overall": round(float(r2_ridge), 4)
        },
        "random_forest": {
            "mae_overall": round(float(mae_rf), 2),
            "r2_overall": round(float(r2_rf), 4),
            "per_resource": per_resource_metrics
        }
    }
    return results

def load_trained_resource_model() -> Any:
    """
    Loads persisted resource demand regressor from disk. Trains on demand if missing.
    """
    if not os.path.exists(RESOURCE_MODEL_PATH):
        train_and_evaluate_resource_models()
    return joblib.load(RESOURCE_MODEL_PATH)
