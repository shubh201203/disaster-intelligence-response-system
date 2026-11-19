import sys
import os
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_recall_fscore_support

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.ai.computer_vision.dataset import generate_synthetic_cv_dataset
from app.ai.computer_vision.model import load_trained_cv_model
from app.ai.computer_vision.features import DAMAGE_CLASSES

def evaluate_cv():
    print("===============================================================")
    print(" DIRS PHASE 3B — COMPUTER VISION DAMAGE MODEL EVALUATION")
    print(" NOTE: Demonstration Proxy Model Trained on Visual Feature Dataset")
    print("===============================================================\n")

    X, y, _ = generate_synthetic_cv_dataset(n_samples_per_class=200, random_seed=99)
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.30, random_state=99, stratify=y)

    model = load_trained_cv_model()
    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec_macro, rec_macro, f1_macro, _ = precision_recall_fscore_support(y_test, y_pred, average='macro')
    cm = confusion_matrix(y_test, y_pred, labels=DAMAGE_CLASSES)
    report_text = classification_report(y_test, y_pred, labels=DAMAGE_CLASSES)

    print(f"Overall CV Accuracy:  {acc * 100:.2f}%")
    print(f"Macro Precision:      {prec_macro * 100:.2f}%")
    print(f"Macro Recall:         {rec_macro * 100:.2f}%")
    print(f"Macro F1 Score:       {f1_macro * 100:.2f}%")
    print("\n--- Detailed Classification Report ---")
    print(report_text)
    print("--- Confusion Matrix ---")
    print(f"Labels Order: {DAMAGE_CLASSES}")
    print(cm)

if __name__ == "__main__":
    evaluate_cv()
