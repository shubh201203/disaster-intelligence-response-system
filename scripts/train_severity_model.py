import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.ai.severity.model import train_and_evaluate_models

def main():
    print("=== DIRS Phase 3A: Training Incident Severity Classifier ===")
    results = train_and_evaluate_models()
    print("\n--- Training & Evaluation Results ---")
    print(f"Selected Model: {results['selected_model']}")
    print("\nLogistic Regression Baseline:")
    for k, v in results['logistic_regression'].items():
        print(f"  {k}: {v}")
    print("\nRandom Forest Candidate Model:")
    for k, v in results['random_forest'].items():
        print(f"  {k}: {v}")
    print("\nModel saved successfully to backend/app/ai/models/severity_model.pkl")

if __name__ == "__main__":
    main()
