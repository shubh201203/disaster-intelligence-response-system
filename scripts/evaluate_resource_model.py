import sys
import os
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.ai.resource_demand.dataset import generate_synthetic_resource_demand_dataset
from app.ai.resource_demand.model import load_trained_resource_model
from app.ai.resource_demand.features import RESOURCE_TYPES

def evaluate_resource():
    print("===============================================================")
    print(" DIRS PHASE 3B — RESOURCE DEMAND REGRESSION EVALUATION")
    print(" NOTE: Multi-Target Demand Regressor Trained on Disaster Dataset")
    print("===============================================================\n")

    X, Y, _ = generate_synthetic_resource_demand_dataset(n_samples=2000, random_seed=99)
    _, X_test, _, Y_test = train_test_split(X, Y, test_size=0.30, random_state=99)

    model = load_trained_resource_model()
    Y_pred = model.predict(X_test)

    mae_total = mean_absolute_error(Y_test, Y_pred)
    r2_total = r2_score(Y_test, Y_pred)

    print(f"Overall Demand MAE: {mae_total:.2f}")
    print(f"Overall Demand R2:  {r2_total:.4f}\n")

    print("--- Per-Resource Regression Metrics ---")
    for idx, res_name in enumerate(RESOURCE_TYPES):
        y_true = Y_test[:, idx]
        y_pred = Y_pred[:, idx]
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        print(f" * {res_name:18s} -> MAE: {mae:6.2f} | RMSE: {rmse:6.2f} | R2: {r2:6.4f}")

if __name__ == "__main__":
    evaluate_resource()
